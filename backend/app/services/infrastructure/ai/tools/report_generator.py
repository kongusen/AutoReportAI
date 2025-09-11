"""
智能报告生成器 v2.0
===============================================

基于优化提示词系统的报告生成工具：
- 集成ReportGenerationPrompts
- 智能内容组织和结构化
- 数据驱动的洞察生成
- 多格式输出支持
"""

import json
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator

from .base import BaseTool, ToolContext, ToolResult, ToolResultType
from ..core.prompts import get_report_content_prompt, PromptComplexity

logger = logging.getLogger(__name__)


class IntelligentReportGenerator(BaseTool):
    """智能报告生成器"""
    
    def __init__(self):
        super().__init__(
            tool_name="intelligent_report_generator",
            tool_category="report_generation"
        )
    
    async def execute(
        self,
        context: ToolContext,
        report_type: str = "analysis_report",
        data_summary: Optional[Dict[str, Any]] = None,
        business_context: str = "",
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """
        执行报告生成任务
        
        Args:
            context: 工具执行上下文
            report_type: 报告类型 (analysis_report|executive_summary|technical_report|custom)
            data_summary: 数据摘要信息
            business_context: 业务背景描述
        """
        
        yield self.create_progress_result("📄 启动智能报告生成器")
        
        # 验证输入
        if not await self.validate_input(
            context, 
            report_type=report_type,
            data_summary=data_summary,
            business_context=business_context
        ):
            yield self.create_error_result("输入验证失败")
            return
        
        # 准备数据摘要
        if not data_summary:
            data_summary = await self._prepare_data_summary(context)
        
        yield self.create_progress_result(f"📊 数据摘要准备完成: {len(data_summary)} 项")
        
        # 根据报告类型选择生成策略
        if report_type == "analysis_report":
            async for result in self._generate_analysis_report(
                context, data_summary, business_context, **kwargs
            ):
                yield result
        elif report_type == "executive_summary":
            async for result in self._generate_executive_summary(
                context, data_summary, business_context, **kwargs
            ):
                yield result
        elif report_type == "technical_report":
            async for result in self._generate_technical_report(
                context, data_summary, business_context, **kwargs
            ):
                yield result
        elif report_type == "custom":
            async for result in self._generate_custom_report(
                context, data_summary, business_context, **kwargs
            ):
                yield result
        else:
            yield self.create_error_result(f"不支持的报告类型: {report_type}")
    
    async def _validate_specific_input(
        self,
        context: ToolContext,
        report_type: str = None,
        data_summary: Dict[str, Any] = None,
        business_context: str = None,
        **kwargs
    ) -> bool:
        """验证报告生成特定输入"""
        
        valid_types = ["analysis_report", "executive_summary", "technical_report", "custom"]
        if report_type and report_type not in valid_types:
            self.logger.error(f"无效的报告类型: {report_type}")
            return False
        
        # 检查是否有足够的上下文信息
        if not business_context and not context.template_content:
            self.logger.warning("缺少业务背景或模板内容，报告质量可能受影响")
        
        return True
    
    async def _prepare_data_summary(self, context: ToolContext) -> Dict[str, Any]:
        """准备数据摘要"""
        
        data_summary = {}
        
        # 从上下文中提取数据源信息
        if context.data_source_info:
            data_summary["data_source"] = {
                "name": context.data_source_info.get("name", "Unknown"),
                "type": context.data_source_info.get("type", "Unknown"),
                "database": context.data_source_info.get("database", "Unknown"),
                "tables_count": len(context.data_source_info.get("tables", []))
            }
        
        # 从占位符中提取关键指标
        if context.placeholders:
            data_summary["key_metrics"] = []
            for placeholder in context.placeholders:
                data_summary["key_metrics"].append({
                    "name": placeholder.get("name", ""),
                    "description": placeholder.get("description", ""),
                    "type": placeholder.get("type", "")
                })
        
        # 从执行历史中提取结果
        if context.iteration_history:
            data_summary["execution_results"] = []
            for history in context.iteration_history[-5:]:  # 最近5次结果
                if history.get("success"):
                    data_summary["execution_results"].append(history.get("result", {}))
        
        return data_summary
    
    async def _generate_analysis_report(
        self,
        context: ToolContext,
        data_summary: Dict[str, Any],
        business_context: str,
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """生成分析报告"""
        
        yield self.create_progress_result("📈 开始生成分析报告")
        
        try:
            # 获取复杂度级别
            complexity = self.get_complexity_level(context)
            
            # 生成报告内容提示词
            report_prompt = get_report_content_prompt(
                report_type="analysis_report",
                data_summary=data_summary,
                business_context=business_context,
                complexity=complexity
            )
            
            yield self.create_progress_result("🤖 AI生成报告内容")
            
            # 调用LLM生成报告
            report_response = await self.ask_llm(
                prompt=report_prompt,
                context=context,
                agent_type="report_writer",
                task_type="report_generation"
            )
            
            # 后处理报告内容
            processed_report = await self._post_process_report(
                report_response, "analysis_report", context
            )
            
            yield self.create_success_result(
                data={
                    "report_type": "analysis_report",
                    "content": processed_report,
                    "metadata": {
                        "data_sources": data_summary.get("data_source", {}),
                        "metrics_count": len(data_summary.get("key_metrics", [])),
                        "complexity": complexity.value,
                        "word_count": len(processed_report.split()) if isinstance(processed_report, str) else 0
                    },
                    "business_context": business_context
                },
                confidence=0.85,
                insights=[
                    "分析报告生成完成",
                    f"包含 {len(data_summary.get('key_metrics', []))} 个关键指标",
                    "基于数据驱动的洞察分析"
                ]
            )
            
        except Exception as e:
            self.logger.error(f"分析报告生成异常: {e}")
            yield self.create_error_result(f"分析报告生成失败: {str(e)}")
    
    async def _generate_executive_summary(
        self,
        context: ToolContext,
        data_summary: Dict[str, Any],
        business_context: str,
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """生成管理摘要"""
        
        yield self.create_progress_result("📋 开始生成管理摘要")
        
        try:
            # 使用简化复杂度用于摘要
            complexity = PromptComplexity.SIMPLE
            
            # 生成摘要提示词
            summary_prompt = get_report_content_prompt(
                report_type="executive_summary",
                data_summary=data_summary,
                business_context=business_context,
                complexity=complexity
            )
            
            yield self.create_progress_result("🤖 AI生成管理摘要")
            
            # 调用LLM生成摘要
            summary_response = await self.ask_llm(
                prompt=summary_prompt,
                context=context,
                agent_type="executive_writer",
                task_type="summary_generation"
            )
            
            # 后处理摘要内容
            processed_summary = await self._post_process_report(
                summary_response, "executive_summary", context
            )
            
            yield self.create_success_result(
                data={
                    "report_type": "executive_summary",
                    "content": processed_summary,
                    "metadata": {
                        "summary_length": len(processed_summary.split()) if isinstance(processed_summary, str) else 0,
                        "key_points": self._extract_key_points(processed_summary),
                        "complexity": complexity.value
                    },
                    "business_context": business_context
                },
                confidence=0.9,
                insights=[
                    "管理摘要生成完成",
                    "突出关键发现和建议",
                    "适合高层决策者阅读"
                ]
            )
            
        except Exception as e:
            self.logger.error(f"管理摘要生成异常: {e}")
            yield self.create_error_result(f"管理摘要生成失败: {str(e)}")
    
    async def _generate_technical_report(
        self,
        context: ToolContext,
        data_summary: Dict[str, Any],
        business_context: str,
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """生成技术报告"""
        
        yield self.create_progress_result("🔧 开始生成技术报告")
        
        try:
            # 使用高复杂度用于技术报告
            complexity = PromptComplexity.HIGH
            
            # 生成技术报告提示词
            technical_prompt = get_report_content_prompt(
                report_type="technical_report",
                data_summary=data_summary,
                business_context=business_context,
                complexity=complexity
            )
            
            yield self.create_progress_result("🤖 AI生成技术报告")
            
            # 调用LLM生成技术报告
            technical_response = await self.ask_llm(
                prompt=technical_prompt,
                context=context,
                agent_type="technical_writer",
                task_type="technical_documentation"
            )
            
            # 后处理技术报告内容
            processed_report = await self._post_process_report(
                technical_response, "technical_report", context
            )
            
            # 添加技术附录
            technical_appendix = await self._generate_technical_appendix(context, data_summary)
            
            yield self.create_success_result(
                data={
                    "report_type": "technical_report",
                    "content": processed_report,
                    "appendix": technical_appendix,
                    "metadata": {
                        "technical_depth": "high",
                        "includes_sql": self._contains_sql(processed_report),
                        "includes_data_schema": self._contains_schema_info(processed_report),
                        "complexity": complexity.value
                    },
                    "business_context": business_context
                },
                confidence=0.8,
                insights=[
                    "技术报告生成完成",
                    "包含详细的技术实现细节",
                    "适合技术团队参考"
                ]
            )
            
        except Exception as e:
            self.logger.error(f"技术报告生成异常: {e}")
            yield self.create_error_result(f"技术报告生成失败: {str(e)}")
    
    async def _generate_custom_report(
        self,
        context: ToolContext,
        data_summary: Dict[str, Any],
        business_context: str,
        custom_requirements: str = "",
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """生成自定义报告"""
        
        yield self.create_progress_result("🎨 开始生成自定义报告")
        
        try:
            # 构建自定义提示词
            custom_prompt = self._build_custom_report_prompt(
                data_summary, business_context, custom_requirements, context
            )
            
            yield self.create_progress_result("🤖 AI生成自定义报告")
            
            # 调用LLM生成自定义报告
            custom_response = await self.ask_llm(
                prompt=custom_prompt,
                context=context,
                agent_type="custom_writer",
                task_type="custom_report_generation"
            )
            
            # 后处理自定义报告内容
            processed_report = await self._post_process_report(
                custom_response, "custom_report", context
            )
            
            yield self.create_success_result(
                data={
                    "report_type": "custom_report",
                    "content": processed_report,
                    "custom_requirements": custom_requirements,
                    "metadata": {
                        "customization_level": "high",
                        "requirements_met": self._validate_custom_requirements(
                            processed_report, custom_requirements
                        ),
                        "word_count": len(processed_report.split()) if isinstance(processed_report, str) else 0
                    },
                    "business_context": business_context
                },
                confidence=0.75,
                insights=[
                    "自定义报告生成完成",
                    "根据特定需求定制内容",
                    "满足个性化报告要求"
                ]
            )
            
        except Exception as e:
            self.logger.error(f"自定义报告生成异常: {e}")
            yield self.create_error_result(f"自定义报告生成失败: {str(e)}")
    
    async def _post_process_report(
        self,
        raw_content: str,
        report_type: str,
        context: ToolContext
    ) -> str:
        """后处理报告内容"""
        
        try:
            # 清理内容
            content = raw_content.strip()
            
            # 移除markdown代码块标记（如果存在）
            if content.startswith('```') and content.endswith('```'):
                lines = content.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content = '\n'.join(lines)
            
            # 添加报告头部信息
            header = self._generate_report_header(report_type, context)
            
            # 添加报告尾部信息
            footer = self._generate_report_footer(report_type, context)
            
            # 组合最终报告
            final_report = f"{header}\n\n{content}\n\n{footer}"
            
            return final_report
            
        except Exception as e:
            self.logger.error(f"报告后处理异常: {e}")
            return raw_content
    
    def _generate_report_header(self, report_type: str, context: ToolContext) -> str:
        """生成报告头部"""
        
        from datetime import datetime
        
        type_names = {
            "analysis_report": "数据分析报告",
            "executive_summary": "管理摘要",
            "technical_report": "技术报告",
            "custom_report": "自定义报告"
        }
        
        report_name = type_names.get(report_type, "报告")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        header_parts = [
            f"# {report_name}",
            "",
            f"**生成时间**: {current_time}",
            f"**报告类型**: {report_name}"
        ]
        
        # 添加数据源信息
        if context.data_source_info:
            data_source = context.data_source_info
            header_parts.extend([
                f"**数据源**: {data_source.get('name', 'Unknown')}",
                f"**数据库**: {data_source.get('database', 'Unknown')}"
            ])
        
        # 添加任务信息
        if context.task_id:
            header_parts.append(f"**任务ID**: {context.task_id}")
        
        header_parts.append("---")
        
        return "\n".join(header_parts)
    
    def _generate_report_footer(self, report_type: str, context: ToolContext) -> str:
        """生成报告尾部"""
        
        footer_parts = [
            "---",
            "",
            "## 报告说明",
            "",
            "本报告由AutoReportAI智能生成系统自动生成。",
            "报告内容基于提供的数据源和业务需求进行分析。",
            ""
        ]
        
        # 添加技术信息
        if context.learned_insights:
            footer_parts.extend([
                "### 分析洞察",
                ""
            ])
            for insight in context.learned_insights[-3:]:  # 最近3个洞察
                footer_parts.append(f"- {insight}")
            footer_parts.append("")
        
        footer_parts.extend([
            "*本报告由AutoReportAI生成 - 智能、准确、高效*"
        ])
        
        return "\n".join(footer_parts)
    
    def _build_custom_report_prompt(
        self,
        data_summary: Dict[str, Any],
        business_context: str,
        custom_requirements: str,
        context: ToolContext
    ) -> str:
        """构建自定义报告提示词"""
        
        prompt_parts = [
            "请根据以下要求生成自定义报告：",
            "",
            f"业务背景: {business_context}",
            "",
            f"自定义要求: {custom_requirements}",
            "",
            "数据摘要:"
        ]
        
        # 添加数据摘要信息
        if data_summary:
            prompt_parts.append(json.dumps(data_summary, ensure_ascii=False, indent=2))
        
        prompt_parts.extend([
            "",
            "报告要求：",
            "1. 严格按照自定义要求组织内容",
            "2. 确保所有结论都有数据支撑",
            "3. 使用清晰的Markdown格式",
            "4. 包含适当的标题层级",
            "5. 提供可执行的建议",
            "",
            "请生成符合要求的报告内容："
        ])
        
        return "\n".join(prompt_parts)
    
    def _extract_key_points(self, content: str) -> List[str]:
        """提取关键要点"""
        
        key_points = []
        
        if not isinstance(content, str):
            return key_points
        
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # 查找标题行（Markdown格式）
            if line.startswith('#') and len(line) > 1:
                # 移除#号，获取标题内容
                title = line.lstrip('#').strip()
                if title and len(title) > 3:  # 过滤太短的标题
                    key_points.append(title)
            
            # 查找列表项
            elif line.startswith('-') or line.startswith('*'):
                item = line[1:].strip()
                if item and len(item) > 5:  # 过滤太短的列表项
                    key_points.append(item)
        
        return key_points[:10]  # 最多返回10个要点
    
    def _contains_sql(self, content: str) -> bool:
        """检查是否包含SQL代码"""
        if not isinstance(content, str):
            return False
        
        sql_keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY']
        content_upper = content.upper()
        
        return any(keyword in content_upper for keyword in sql_keywords)
    
    def _contains_schema_info(self, content: str) -> bool:
        """检查是否包含数据库架构信息"""
        if not isinstance(content, str):
            return False
        
        schema_keywords = ['表结构', '字段', 'TABLE', 'COLUMN', '数据库', '表名']
        
        return any(keyword in content for keyword in schema_keywords)
    
    def _validate_custom_requirements(
        self,
        content: str,
        requirements: str
    ) -> bool:
        """验证是否满足自定义要求"""
        
        if not requirements or not isinstance(content, str):
            return True
        
        # 简单的关键词匹配验证
        # 可以根据需要扩展更复杂的验证逻辑
        requirement_keywords = requirements.lower().split()
        content_lower = content.lower()
        
        matched_keywords = sum(1 for keyword in requirement_keywords if keyword in content_lower)
        match_ratio = matched_keywords / len(requirement_keywords) if requirement_keywords else 1
        
        return match_ratio >= 0.5  # 至少50%的要求关键词被满足
    
    async def _generate_technical_appendix(
        self,
        context: ToolContext,
        data_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成技术附录"""
        
        appendix = {
            "data_source_details": {},
            "sql_queries": [],
            "schema_information": {},
            "technical_notes": []
        }
        
        try:
            # 数据源详情
            if context.data_source_info:
                appendix["data_source_details"] = context.data_source_info
            
            # SQL查询（从执行历史中提取）
            if context.iteration_history:
                for history in context.iteration_history:
                    result = history.get("result", {})
                    if isinstance(result, dict) and "sql" in result:
                        appendix["sql_queries"].append({
                            "query": result["sql"],
                            "timestamp": history.get("timestamp", "")
                        })
            
            # 技术说明
            appendix["technical_notes"].extend([
                "本报告使用AutoReportAI v2.0生成",
                "采用基于ReAct机制的智能分析",
                "集成了优化的提示词系统"
            ])
            
            if context.learned_insights:
                appendix["technical_notes"].extend(context.learned_insights)
            
        except Exception as e:
            self.logger.error(f"生成技术附录异常: {e}")
        
        return appendix