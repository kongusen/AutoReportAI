"""
智能报告生成Agent系统

基于完全Agent驱动的智能文本生成与条件渲染
让Agent自主理解数据语义，生成符合人类表达习惯的自然文本
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .facade import AgentFacade
from .tools.text_rendering_tools import create_conditional_text_tool
from .tools.chart_tools import ChartRenderTool

logger = logging.getLogger(__name__)


class DataUnderstandingAgent:
    """数据理解Agent - 第一层"""

    def __init__(self, agent_facade: AgentFacade, container=None):
        self.agent_facade = agent_facade
        self.container = container

    async def analyze(self, raw_data: Dict[str, Any], business_context: str = "") -> Dict[str, Any]:
        """
        分析数据特征，识别关键模式

        Args:
            raw_data: ETL处理后的原始数据
            business_context: 业务上下文信息

        Returns:
            数据分析结果
        """

        analysis_prompt = f"""
你是专业的数据分析师，请深度分析以下数据特征：

## 业务上下文
{business_context}

## 数据内容
{json.dumps(raw_data, ensure_ascii=False, indent=2)}

## 分析任务
请从以下维度分析数据：

### 1. 数据状态识别
- 识别哪些指标为零值、空值、缺失值
- 分析这些零值/空值的业务含义（是正常状态还是异常情况）
- 判断数据的完整性和可信度

### 2. 核心信息提取
- 识别最重要的关键指标
- 找出值得关注的数据模式或异常
- 确定哪些信息对用户最有价值

### 3. 展示策略建议
- 建议哪些信息应该重点展示
- 建议哪些信息应该简化表达
- 建议哪些信息可以省略不表达
- 对于零值/空值，建议最合适的表达方式

### 4. 文本生成指导
- 为每个关键发现提供表达建议
- 确保不会产生语义不完整的句子
- 建议合适的叙述逻辑和结构

请以JSON格式输出分析结果，包含以上四个维度的详细分析。
"""

        try:
            # 使用现有的Agent系统
            from .context_prompt_controller import ContextPromptController
            from ..data_model import AgentInput, TaskContext

            agent_input = AgentInput(
                user_prompt=analysis_prompt,
                context=TaskContext(
                    task_time=int(datetime.now().timestamp()),
                    timezone="Asia/Shanghai"
                ),
                task_driven_context={
                    "task_type": "data_understanding",
                    "business_context": business_context,
                    "data_size": len(str(raw_data))
                }
            )

            result = await self.agent_facade.execute_analysis(agent_input)

            if result.success:
                # 解析Agent返回的JSON分析结果
                try:
                    analysis_result = json.loads(result.content)
                except:
                    # 如果不是JSON格式，构造标准格式
                    analysis_result = {
                        "data_status": {"analysis": result.content},
                        "core_insights": {"summary": "Agent分析完成"},
                        "display_strategy": {"recommendation": "基于Agent建议"},
                        "text_guidance": {"approach": result.content}
                    }

                return {
                    "success": True,
                    "analysis": analysis_result,
                    "metadata": {
                        "analyzed_at": datetime.now().isoformat(),
                        "agent_confidence": result.metadata.get("confidence", 0.8),
                        "analysis_method": "agent_driven"
                    }
                }
            else:
                logger.warning(f"数据理解Agent分析失败: {result.error}")
                return {"success": False, "error": result.error}

        except Exception as e:
            logger.error(f"数据理解Agent执行异常: {e}")
            return {"success": False, "error": str(e)}


class SemanticGenerationAgent:
    """语义生成Agent - 第二层"""

    def __init__(self, agent_facade: AgentFacade, container=None):
        self.agent_facade = agent_facade
        self.container = container

    async def generate_narrative(
        self,
        data_analysis: Dict[str, Any],
        original_data: Dict[str, Any],
        user_query: str = ""
    ) -> Dict[str, Any]:
        """
        基于数据分析生成自然文本叙事

        Args:
            data_analysis: 数据理解Agent的分析结果
            original_data: 原始数据
            user_query: 用户查询意图

        Returns:
            生成的文本内容
        """

        generation_prompt = f"""
你是专业的报告撰写专家，擅长将数据分析结果转化为清晰、自然、有洞察力的文本。

## 用户查询意图
{user_query}

## 数据分析结果
{json.dumps(data_analysis, ensure_ascii=False, indent=2)}

## 原始数据
{json.dumps(original_data, ensure_ascii=False, indent=2)}

## 文本生成要求

### 核心原则
1. **语义完整性**: 每句话都要语义完整，不要有悬空表达
2. **自然表达**: 符合人类表达习惯，避免机械感
3. **信息密度**: 有价值信息详展，无价值信息简化或省略
4. **用户视角**: 站在用户角度，提供真正有用的信息

### 具体要求
1. 根据数据分析结果，为每个关键发现生成自然的文本描述
2. 对于零值/空值情况，采用简洁直接的表达，不要强行展开
3. 对于有明细数据的情况，适当展开但避免冗余
4. 确保逻辑连贯，结构清晰
5. 在合适的地方添加洞察和建议

### 禁止的表达方式
❌ "为："后面没有内容
❌ "包括："后面是空列表
❌ 为空数据强行制造内容
❌ 语义不完整的句子

### 推荐的表达方式
✅ "本期XX指标为零，表现稳定"
✅ "暂无相关数据记录"
✅ "共X项，主要包括..."(仅在有实际内容时使用)

请生成结构化的报告内容，包含标题、主要发现、详细分析等部分。
"""

        try:
            from .context_prompt_controller import ContextPromptController
            from ..data_model import AgentInput, TaskContext

            agent_input = AgentInput(
                user_prompt=generation_prompt,
                context=TaskContext(
                    task_time=int(datetime.now().timestamp()),
                    timezone="Asia/Shanghai"
                ),
                task_driven_context={
                    "task_type": "semantic_generation",
                    "user_query": user_query,
                    "has_data_analysis": bool(data_analysis.get("success"))
                }
            )

            result = await self.agent_facade.execute_generation(agent_input)

            if result.success:
                return {
                    "success": True,
                    "content": result.content,
                    "metadata": {
                        "generated_at": datetime.now().isoformat(),
                        "generation_method": "agent_semantic",
                        "content_length": len(result.content),
                        "agent_confidence": result.metadata.get("confidence", 0.8)
                    }
                }
            else:
                # 降级到工具支撑
                logger.warning(f"语义生成Agent失败，降级到工具处理: {result.error}")
                return await self._fallback_to_tools(data_analysis, original_data)

        except Exception as e:
            logger.error(f"语义生成Agent执行异常: {e}")
            return await self._fallback_to_tools(data_analysis, original_data)

    async def _fallback_to_tools(self, data_analysis: Dict[str, Any], original_data: Dict[str, Any]) -> Dict[str, Any]:
        """降级到工具处理"""
        try:
            text_tool = create_conditional_text_tool(self.container)

            # 对每个数据项进行工具处理
            processed_content = []

            for key, value in original_data.items():
                tool_result = await text_tool.execute({
                    "data": value,
                    "context": key,
                    "render_type": "summary"
                })

                if tool_result["success"]:
                    processed_content.append(f"{key}: {tool_result['result']}")

            return {
                "success": True,
                "content": "\n".join(processed_content),
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "generation_method": "tool_fallback",
                    "processed_items": len(processed_content)
                }
            }

        except Exception as e:
            logger.error(f"工具降级处理也失败: {e}")
            return {
                "success": False,
                "error": f"语义生成失败: {str(e)}",
                "content": ""
            }


class ContentOptimizationAgent:
    """内容优化Agent - 第三层"""

    def __init__(self, agent_facade: AgentFacade, container=None):
        self.agent_facade = agent_facade
        self.container = container

    async def optimize(self, draft_content: str, optimization_focus: List[str] = None) -> Dict[str, Any]:
        """
        优化报告内容

        Args:
            draft_content: 草稿内容
            optimization_focus: 优化重点 (可选)

        Returns:
            优化后的内容
        """

        focus_areas = optimization_focus or [
            "语义完整性", "逻辑连贯性", "表达自然性", "信息密度", "用户友好性"
        ]

        optimization_prompt = f"""
你是资深的文档编辑专家，请优化以下报告草稿。

## 草稿内容
{draft_content}

## 优化重点
{', '.join(focus_areas)}

## 优化任务

### 检查项目
1. **语义完整性检查**
   - 是否有语义不完整的句子？
   - 是否有"为："、"包括："后面没内容的情况？
   - 每个句子是否都能独立理解？

2. **逻辑连贯性检查**
   - 段落之间的逻辑关系是否清晰？
   - 是否有突兀的跳跃或重复？
   - 整体结构是否合理？

3. **表达自然性检查**
   - 是否符合人类自然表达习惯？
   - 是否有机械化的模板痕迹？
   - 语言是否流畅易读？

4. **信息密度检查**
   - 是否有冗余的表达？
   - 重要信息是否突出？
   - 无价值信息是否已简化？

### 优化原则
- 保持原意不变的前提下改进表达
- 删除冗余和无效信息
- 增强可读性和专业度
- 确保每句话都有价值

请输出优化后的最终内容，并简要说明主要改进点。
"""

        try:
            from .context_prompt_controller import ContextPromptController
            from ..data_model import AgentInput, TaskContext

            agent_input = AgentInput(
                user_prompt=optimization_prompt,
                context=TaskContext(
                    task_time=int(datetime.now().timestamp()),
                    timezone="Asia/Shanghai"
                ),
                task_driven_context={
                    "task_type": "content_optimization",
                    "content_length": len(draft_content),
                    "optimization_focus": focus_areas
                }
            )

            result = await self.agent_facade.execute_optimization(agent_input)

            if result.success:
                return {
                    "success": True,
                    "optimized_content": result.content,
                    "improvements": result.metadata.get("improvements", []),
                    "metadata": {
                        "optimized_at": datetime.now().isoformat(),
                        "optimization_method": "agent_driven",
                        "original_length": len(draft_content),
                        "optimized_length": len(result.content)
                    }
                }
            else:
                logger.warning(f"内容优化Agent失败: {result.error}")
                return {
                    "success": True,  # 即使优化失败，也返回原内容
                    "optimized_content": draft_content,
                    "improvements": ["优化Agent不可用，保持原内容"],
                    "metadata": {
                        "optimized_at": datetime.now().isoformat(),
                        "optimization_method": "passthrough",
                        "error": result.error
                    }
                }

        except Exception as e:
            logger.error(f"内容优化Agent执行异常: {e}")
            return {
                "success": True,
                "optimized_content": draft_content,
                "improvements": [f"优化异常: {str(e)}"],
                "metadata": {
                    "optimized_at": datetime.now().isoformat(),
                    "optimization_method": "error_fallback"
                }
            }


class IntelligentReportGenerator:
    """智能报告生成器 - 总控制器"""

    def __init__(self, container):
        self.container = container

        # 获取Agent门面
        try:
            self.agent_facade = container.get_agent_facade()
        except:
            # 创建Agent门面的降级实现
            from .facade import AgentFacade
            self.agent_facade = AgentFacade()

        # 初始化各层Agent
        self.understanding_agent = DataUnderstandingAgent(self.agent_facade, container)
        self.generation_agent = SemanticGenerationAgent(self.agent_facade, container)
        self.optimization_agent = ContentOptimizationAgent(self.agent_facade, container)

        # 初始化可视化工具
        self.chart_tool = ChartRenderTool(container)

    async def generate_intelligent_report(
        self,
        etl_data: Dict[str, Any],
        user_query: str = "",
        business_context: str = "",
        optimization_focus: List[str] = None
    ) -> Dict[str, Any]:
        """
        完整的智能报告生成流程

        这是后置阶段的核心入口，处理ETL获取的数据

        Args:
            etl_data: ETL阶段获取的数据
            user_query: 用户查询意图
            business_context: 业务上下文
            optimization_focus: 优化重点

        Returns:
            完整的智能报告
        """

        logger.info(f"开始智能报告生成: 用户查询='{user_query}', 业务上下文='{business_context}'")

        try:
            # 阶段1: 数据理解
            logger.info("阶段1: 数据理解分析")
            understanding_result = await self.understanding_agent.analyze(
                raw_data=etl_data,
                business_context=business_context
            )

            if not understanding_result.get("success"):
                return {
                    "success": False,
                    "error": f"数据理解失败: {understanding_result.get('error')}",
                    "stage": "data_understanding"
                }

            # 阶段2: 语义生成
            logger.info("阶段2: 智能语义生成")
            generation_result = await self.generation_agent.generate_narrative(
                data_analysis=understanding_result["analysis"],
                original_data=etl_data,
                user_query=user_query
            )

            if not generation_result.get("success"):
                return {
                    "success": False,
                    "error": f"语义生成失败: {generation_result.get('error')}",
                    "stage": "semantic_generation"
                }

            # 阶段3: 内容优化
            logger.info("阶段3: 内容优化处理")
            optimization_result = await self.optimization_agent.optimize(
                draft_content=generation_result["content"],
                optimization_focus=optimization_focus
            )

            # 阶段4: 可视化建议
            logger.info("阶段4: 生成可视化建议")
            chart_suggestions = await self._generate_chart_suggestions(
                etl_data,
                understanding_result["analysis"]
            )

            # 阶段5: 组装最终报告
            final_report = {
                "success": True,
                "content": optimization_result["optimized_content"],
                "visualizations": chart_suggestions,
                "metadata": {
                    "user_query": user_query,
                    "business_context": business_context,
                    "generated_at": datetime.now().isoformat(),
                    "processing_stages": {
                        "data_understanding": understanding_result["metadata"],
                        "semantic_generation": generation_result["metadata"],
                        "content_optimization": optimization_result["metadata"]
                    },
                    "data_insights": understanding_result["analysis"],
                    "improvements": optimization_result.get("improvements", [])
                }
            }

            logger.info("智能报告生成完成")
            return final_report

        except Exception as e:
            logger.error(f"智能报告生成异常: {e}")
            return {
                "success": False,
                "error": f"报告生成异常: {str(e)}",
                "stage": "general_error"
            }

    async def _generate_chart_suggestions(
        self,
        data: Dict[str, Any],
        insights: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成图表建议"""

        chart_suggestions = []

        try:
            # 基于数据特征生成图表建议
            for key, value in data.items():
                if isinstance(value, (list, tuple)) and len(value) > 0:
                    # 列表数据适合图表展示
                    chart_spec = {
                        "type": "bar",  # 默认柱状图
                        "title": f"{key}分布图",
                        "data": value,
                        "placeholder": {"id": f"chart_{key}"}
                    }

                    # 使用图表工具生成
                    chart_result = await self.chart_tool.execute({
                        "chart_spec": chart_spec,
                        "placeholder": {"id": f"chart_{key}"}
                    })

                    if chart_result.get("success"):
                        chart_suggestions.append({
                            "type": "chart",
                            "title": f"{key}可视化",
                            "chart_path": chart_result.get("chart_path"),
                            "description": f"展示{key}的分布情况"
                        })

                elif isinstance(value, (int, float)) and value > 0:
                    # 数值型数据可以做指标卡片
                    chart_suggestions.append({
                        "type": "metric_card",
                        "title": key,
                        "value": value,
                        "description": f"{key}的当前数值"
                    })

            return chart_suggestions

        except Exception as e:
            logger.error(f"图表建议生成失败: {e}")
            return []


# 快速创建实例的工厂函数
def create_intelligent_report_generator(container) -> IntelligentReportGenerator:
    """创建智能报告生成器"""
    return IntelligentReportGenerator(container)


# 模块导出
__all__ = [
    "DataUnderstandingAgent",
    "SemanticGenerationAgent",
    "ContentOptimizationAgent",
    "IntelligentReportGenerator",
    "create_intelligent_report_generator"
]