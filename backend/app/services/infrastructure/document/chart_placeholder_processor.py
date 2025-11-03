"""
图表占位符处理器

专门处理文档中的图表占位符，在ETL数据已经准备好的情况下生成图表
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChartPlaceholderProcessor:
    """
    图表占位符处理器

    在文档生成阶段处理图表占位符，调用ChartGenerationTool生成图表
    """

    def __init__(self, user_id: str = "system", agent_adapter: Optional[Any] = None):
        self.user_id = user_id
        self.agent_adapter = agent_adapter
        self.logger = logging.getLogger(self.__class__.__name__)
        # 从 agent_adapter 获取 container（如果可用）
        self.container = getattr(agent_adapter, 'container', None) if agent_adapter else None
        # 如果没有 container，尝试从全局导入
        if self.container is None:
            try:
                from app.core.container import container as global_container
                self.container = global_container
            except ImportError:
                self.logger.warning("无法获取 container，图表工具可能无法正常工作")
                self.container = None

    async def process_chart_placeholder(
        self,
        placeholder_text: str,
        data: Any,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理单个图表占位符

        Args:
            placeholder_text: 占位符文本，如 "图表：州市退货申请量由高到低排列并显示对应申请量的柱状图"
            data: ETL返回的数据
            output_dir: 图表输出目录（可选）

        Returns:
            {
                "success": bool,
                "chart_path": str,  # 图表文件路径
                "chart_type": str,
                "error": str (if failed)
            }
        """
        try:
            # 1. 从占位符文本中提取图表意图
            chart_intent = self._extract_chart_intent(placeholder_text)

            self.logger.info(f"处理图表占位符: {placeholder_text}")
            self.logger.info(f"  提取的意图: {chart_intent}")
            self.logger.info(f"  数据类型: {type(data)}, 数据量: {len(data) if isinstance(data, list) else 'N/A'}")

            # 2. 验证数据
            if not data:
                return {
                    "success": False,
                    "error": "没有数据可用于生成图表"
                }

            stage_aware_metadata: Dict[str, Any] = {}
            agent_chart_config: Dict[str, Any] = {}

            agent_plan = await self._maybe_generate_with_stage_aware(
                placeholder_text=placeholder_text,
                data=data,
                output_dir=output_dir,
            )

            if agent_plan and agent_plan.get("success"):
                stage_aware_metadata = {
                    "analysis": agent_plan.get("analysis"),
                    "recommendations": agent_plan.get("recommendations"),
                    "execution_time_ms": agent_plan.get("execution_time_ms"),
                }

                config_from_agent = self._extract_chart_config(
                    agent_plan.get("chart_config")
                ) or self._extract_chart_config(agent_plan.get("result"))
                if config_from_agent:
                    agent_chart_config = config_from_agent

                chart_path = agent_plan.get("chart_path")
                if chart_path and os.path.exists(chart_path):
                    self.logger.info("StageAware 已生成图表，直接复用现有文件")
                    return {
                        "success": True,
                        "chart_path": chart_path,
                        "chart_type": agent_chart_config.get("chart_type", chart_intent.get("chart_type", "bar")),
                        "title": agent_chart_config.get("title", chart_intent["title"]),
                        "metadata": {
                            "stage_aware": stage_aware_metadata,
                            "chart_config": agent_chart_config,
                        },
                        "generation_time_ms": agent_plan.get("execution_time_ms", 0),
                    }

            # 3. 调用图表生成工具（若 StageAware 未直接生成）
            ChartGeneratorTool = None
            ChartAnalyzerTool = None
            try:
                from app.services.infrastructure.agents.tools.chart import (
                    ChartGeneratorTool,
                    ChartAnalyzerTool,
                )
            except ModuleNotFoundError:
                try:
                    from app.services.infrastructure.agents.tools.chart_tools import (
                        ChartGenerationTool as ChartGeneratorTool,
                        ChartDataAnalyzerTool as ChartAnalyzerTool,
                    )
                except ModuleNotFoundError as import_err:
                    self.logger.error("图表工具模块缺失，无法生成图表: %s", import_err)
                    return {
                        "success": False,
                        "error": "图表工具模块缺失",
                    }

            # Step 1: 分析数据并推荐图表类型
            if self.container is None:
                self.logger.error("Container 不可用，无法使用图表分析工具")
                recommended_chart_type = chart_intent.get("chart_type", "bar")
            else:
                analyzer = ChartAnalyzerTool(self.container)
                # 🔧 修复：使用关键字参数调用，并使用正确的参数名
                analysis_result = await analyzer.execute(
                    chart_data=data,
                    chart_config=None,
                    analysis_focus=["patterns", "trends"],
                    include_recommendations=True
                )

                if not analysis_result.get("success"):
                    self.logger.warning(f"数据分析失败，使用默认图表类型: {analysis_result.get('error')}")
                    recommended_chart_type = agent_chart_config.get("chart_type", chart_intent.get("chart_type", "bar"))
                else:
                    recommended_chart_type = agent_chart_config.get(
                        "chart_type",
                        analysis_result.get("recommended_chart_type", chart_intent.get("chart_type", "bar"))
                    )
                    self.logger.info(f"推荐图表类型: {recommended_chart_type}")
                    self.logger.info(f"推荐理由: {analysis_result.get('reasoning')}")

            # Step 2: 生成图表
            if self.container is None:
                self.logger.error("Container 不可用，无法使用图表生成工具")
                return {
                    "success": False,
                    "error": "Container 不可用，无法生成图表"
                }
            
            chart_tool = ChartGeneratorTool(self.container)

            # 准备图表生成参数
            chart_params = {
                "chart_type": recommended_chart_type,
                "data": data,
                "title": agent_chart_config.get("title", chart_intent["title"]),
                "user_id": self.user_id
            }

            # 如果 StageAware 或分析结果包含列信息，优先使用
            if agent_chart_config.get("x_axis"):
                chart_params["x_axis"] = agent_chart_config["x_axis"]
            if agent_chart_config.get("y_axis"):
                chart_params["y_axis"] = agent_chart_config["y_axis"]
            if agent_chart_config.get("color_column"):
                chart_params["color_column"] = agent_chart_config["color_column"]
            if agent_chart_config.get("size_column"):
                chart_params["size_column"] = agent_chart_config["size_column"]

            if analysis_result.get("success"):
                if "x_axis" not in chart_params and analysis_result.get("x_column"):
                    chart_params["x_axis"] = analysis_result["x_column"]
                if "y_axis" not in chart_params and analysis_result.get("y_column"):
                    chart_params["y_axis"] = analysis_result["y_column"]

            # 调用图表生成工具
            chart_result = await chart_tool.execute(chart_params)

            if chart_result.get("success"):
                self.logger.info(f"✅ 图表生成成功: {chart_result['chart_path']}")
                self.logger.info(f"   生成时间: {chart_result.get('generation_time_ms')}ms")

                metadata = chart_result.get("metadata", {}) or {}
                metadata.setdefault("stage_aware", stage_aware_metadata)
                if agent_chart_config:
                    metadata["stage_aware"]["chart_config"] = agent_chart_config

                return {
                    "success": True,
                    "chart_path": chart_result["chart_path"],
                    "chart_type": chart_result["chart_type"],
                    "title": chart_result["title"],
                    "metadata": metadata,
                    "generation_time_ms": chart_result.get("generation_time_ms", 0)
                }
            else:
                return {
                    "success": False,
                    "error": chart_result.get("error", "图表生成失败")
                }

        except Exception as e:
            self.logger.error(f"处理图表占位符时发生异常: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"图表处理异常: {str(e)}"
            }

    async def _maybe_generate_with_stage_aware(
        self,
        *,
        placeholder_text: str,
        data: Any,
        output_dir: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """尝试通过 StageAware Agent 获取图表规划。"""
        if not self.agent_adapter:
            return None

        try:
            result = await self.agent_adapter.generate_chart(
                chart_placeholder=placeholder_text,
                etl_data=data if isinstance(data, dict) else {"data": data},
                user_id=self.user_id,
                task_context={"output_dir": output_dir} if output_dir else {},
            )
            if not result.get("success"):
                self.logger.warning(
                    "StageAware 图表阶段失败: %s", result.get("error", "unknown error")
                )
                return None
            return result
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.warning("StageAware 图表阶段异常: %s", exc, exc_info=True)
            return None

    @staticmethod
    def _extract_chart_config(config: Any) -> Dict[str, Any]:
        """解析 StageAware 返回的 chart_config。"""
        if isinstance(config, dict):
            return config

        if isinstance(config, str):
            text = config.strip()
            if text.startswith("```"):
                parts = text.split("\n", 1)
                text = parts[1] if len(parts) == 2 else text
                if text.endswith("```"):
                    text = text[: -3]
                text = text.strip()
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {}

        return {}

    def _extract_chart_intent(self, placeholder_text: str) -> Dict[str, Any]:
        """
        从占位符文本中提取图表意图

        Args:
            placeholder_text: 如 "图表：州市退货申请量由高到低排列并显示对应申请量的柱状图"

        Returns:
            {
                "chart_type": "bar",  # 图表类型
                "title": "州市退货申请量",  # 图表标题
                "description": "州市退货申请量由高到低排列"  # 完整描述
            }
        """
        # 移除"图表："前缀和花括号
        clean_text = placeholder_text.replace("{{", "").replace("}}", "")
        if clean_text.startswith("图表："):
            clean_text = clean_text[3:]  # 移除"图表："

        # 提取图表类型
        chart_type = "bar"  # 默认柱状图
        chart_type_keywords = {
            "柱状图": "bar",
            "条形图": "bar",
            "折线图": "line",
            "线图": "line",
            "饼图": "pie",
            "散点图": "scatter",
            "面积图": "area"
        }

        for keyword, ctype in chart_type_keywords.items():
            if keyword in clean_text:
                chart_type = ctype
                break

        # 提取标题（通常是前面的描述部分）
        # 例如："州市退货申请量由高到低排列并显示对应申请量的柱状图"
        # 标题可能是第一个实体名词或整个描述
        title_parts = []
        for part in clean_text.split("并"):
            if "显示" not in part and not any(kw in part for kw in chart_type_keywords.keys()):
                title_parts.append(part.strip())

        title = title_parts[0] if title_parts else clean_text.split("的")[0]

        return {
            "chart_type": chart_type,
            "title": title,
            "description": clean_text
        }

    def identify_chart_placeholders(self, template_content: str) -> List[str]:
        """
        识别模板中的所有图表占位符

        Args:
            template_content: 模板内容

        Returns:
            图表占位符列表
        """
        import re

        # 匹配 {{图表：xxx}} 格式的占位符
        pattern = r'\{\{图表：([^}]+)\}\}'
        matches = re.findall(pattern, template_content)

        chart_placeholders = [f"图表：{match}" for match in matches]

        self.logger.info(f"识别到 {len(chart_placeholders)} 个图表占位符")
        for ph in chart_placeholders:
            self.logger.info(f"  - {ph}")

        return chart_placeholders
