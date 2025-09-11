"""
提示词感知编排器 v2.0
===============================================

基于优化提示词系统的智能编排器：
- 深度集成prompts.py
- 智能工具选择和协作
- 自适应复杂度管理
- 端到端任务编排
"""

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator

from .base import BaseTool, ToolContext, ToolResult, ToolResultType
from .sql_generator import AdvancedSQLGenerator
from .data_analyzer import SmartDataAnalyzer
from .report_generator import IntelligentReportGenerator

logger = logging.getLogger(__name__)


class PromptAwareOrchestrator(BaseTool):
    """提示词感知编排器"""
    
    def __init__(self):
        super().__init__(
            tool_name="prompt_aware_orchestrator",
            tool_category="orchestration"
        )
        
        # 初始化子工具
        self.sql_generator = AdvancedSQLGenerator()
        self.data_analyzer = SmartDataAnalyzer()
        self.report_generator = IntelligentReportGenerator()
        
        # 工具映射
        self.available_tools = {
            "sql_generation": self.sql_generator,
            "data_analysis": self.data_analyzer,
            "report_generation": self.report_generator
        }
    
    async def execute(
        self,
        context: ToolContext,
        task_type: str = "comprehensive",
        workflow_steps: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """
        执行智能编排任务
        
        Args:
            context: 工具执行上下文
            task_type: 任务类型 (sql_only|analysis_only|report_only|comprehensive)
            workflow_steps: 自定义工作流步骤
        """
        
        yield self.create_progress_result("🎯 启动提示词感知编排器")
        
        # 验证输入
        if not await self.validate_input(context, task_type=task_type):
            yield self.create_error_result("输入验证失败")
            return
        
        # 根据任务类型选择编排策略
        if task_type == "sql_only":
            async for result in self._orchestrate_sql_generation(context, **kwargs):
                yield result
        elif task_type == "analysis_only":
            async for result in self._orchestrate_data_analysis(context, **kwargs):
                yield result
        elif task_type == "report_only":
            async for result in self._orchestrate_report_generation(context, **kwargs):
                yield result
        elif task_type == "comprehensive":
            async for result in self._orchestrate_comprehensive_workflow(context, **kwargs):
                yield result
        elif task_type == "custom" and workflow_steps:
            async for result in self._orchestrate_custom_workflow(context, workflow_steps, **kwargs):
                yield result
        else:
            yield self.create_error_result(f"不支持的任务类型: {task_type}")
    
    async def _validate_specific_input(
        self,
        context: ToolContext,
        task_type: str = None,
        **kwargs
    ) -> bool:
        """验证编排器特定输入"""
        
        valid_types = ["sql_only", "analysis_only", "report_only", "comprehensive", "custom"]
        if task_type and task_type not in valid_types:
            self.logger.error(f"无效的任务类型: {task_type}")
            return False
        
        return True
    
    async def _orchestrate_sql_generation(
        self,
        context: ToolContext,
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """编排SQL生成任务"""
        
        yield self.create_progress_result("💽 开始SQL生成编排")
        
        try:
            # 验证SQL生成前提条件
            if not context.placeholders:
                yield self.create_error_result("缺少占位符信息，无法生成SQL")
                return
            
            if not context.data_source_info:
                yield self.create_error_result("缺少数据源信息，无法生成SQL")
                return
            
            # 为每个占位符生成SQL
            sql_results = {}
            total_placeholders = len(context.placeholders)
            
            for i, placeholder in enumerate(context.placeholders):
                placeholder_name = placeholder.get("name", f"placeholder_{i}")
                placeholder_analysis = placeholder.get("description", "")
                
                yield self.create_progress_result(
                    f"生成SQL {i+1}/{total_placeholders}: {placeholder_name}"
                )
                
                # 调用SQL生成器
                sql_tool_results = []
                async for result in self.sql_generator.execute(
                    context=context,
                    placeholder_name=placeholder_name,
                    placeholder_analysis=placeholder_analysis,
                    **kwargs
                ):
                    sql_tool_results.append(result)
                    if result.type == ToolResultType.PROGRESS:
                        yield result
                
                # 收集SQL生成结果
                if sql_tool_results and sql_tool_results[-1].type == ToolResultType.RESULT:
                    sql_results[placeholder_name] = sql_tool_results[-1].data
                else:
                    sql_results[placeholder_name] = {"error": "SQL生成失败"}
            
            # 生成编排结果
            orchestration_result = {
                "task_type": "sql_generation",
                "placeholders_processed": total_placeholders,
                "sql_results": sql_results,
                "success_count": sum(1 for r in sql_results.values() if "error" not in r),
                "metadata": {
                    "data_source": context.data_source_info.get("name", "Unknown"),
                    "complexity": self.get_complexity_level(context).value
                }
            }
            
            success_rate = orchestration_result["success_count"] / total_placeholders
            
            yield self.create_success_result(
                data=orchestration_result,
                confidence=success_rate,
                insights=[
                    f"成功生成 {orchestration_result['success_count']}/{total_placeholders} 个SQL",
                    f"成功率: {success_rate:.1%}",
                    "SQL生成编排完成"
                ]
            )
            
        except Exception as e:
            self.logger.error(f"SQL生成编排异常: {e}")
            yield self.create_error_result(f"SQL生成编排失败: {str(e)}")
    
    async def _orchestrate_data_analysis(
        self,
        context: ToolContext,
        analysis_type: str = "comprehensive",
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """编排数据分析任务"""
        
        yield self.create_progress_result("📊 开始数据分析编排")
        
        try:
            # 调用数据分析器
            analysis_results = []
            async for result in self.data_analyzer.execute(
                context=context,
                analysis_type=analysis_type,
                **kwargs
            ):
                analysis_results.append(result)
                if result.type in [ToolResultType.PROGRESS, ToolResultType.INFO]:
                    yield result
            
            # 处理分析结果
            if analysis_results and analysis_results[-1].type == ToolResultType.RESULT:
                final_result = analysis_results[-1].data
                
                yield self.create_success_result(
                    data={
                        "task_type": "data_analysis",
                        "analysis_type": analysis_type,
                        "analysis_result": final_result,
                        "metadata": {
                            "tool_used": "smart_data_analyzer",
                            "analysis_depth": analysis_type
                        }
                    },
                    confidence=analysis_results[-1].confidence or 0.8,
                    insights=analysis_results[-1].insights or ["数据分析编排完成"]
                )
            else:
                yield self.create_error_result("数据分析未返回有效结果")
                
        except Exception as e:
            self.logger.error(f"数据分析编排异常: {e}")
            yield self.create_error_result(f"数据分析编排失败: {str(e)}")
    
    async def _orchestrate_report_generation(
        self,
        context: ToolContext,
        report_type: str = "analysis_report",
        data_summary: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """编排报告生成任务"""
        
        yield self.create_progress_result("📄 开始报告生成编排")
        
        try:
            # 如果没有提供数据摘要，尝试从上下文生成
            if not data_summary and context.iteration_history:
                data_summary = self._extract_data_summary_from_history(context)
            
            # 调用报告生成器
            report_results = []
            async for result in self.report_generator.execute(
                context=context,
                report_type=report_type,
                data_summary=data_summary,
                **kwargs
            ):
                report_results.append(result)
                if result.type in [ToolResultType.PROGRESS, ToolResultType.INFO]:
                    yield result
            
            # 处理报告结果
            if report_results and report_results[-1].type == ToolResultType.RESULT:
                final_result = report_results[-1].data
                
                yield self.create_success_result(
                    data={
                        "task_type": "report_generation",
                        "report_type": report_type,
                        "report_result": final_result,
                        "metadata": {
                            "tool_used": "intelligent_report_generator",
                            "content_length": len(final_result.get("content", ""))
                        }
                    },
                    confidence=report_results[-1].confidence or 0.8,
                    insights=report_results[-1].insights or ["报告生成编排完成"]
                )
            else:
                yield self.create_error_result("报告生成未返回有效结果")
                
        except Exception as e:
            self.logger.error(f"报告生成编排异常: {e}")
            yield self.create_error_result(f"报告生成编排失败: {str(e)}")
    
    async def _orchestrate_comprehensive_workflow(
        self,
        context: ToolContext,
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """编排综合工作流"""
        
        yield self.create_progress_result("🚀 开始综合工作流编排")
        
        comprehensive_result = {
            "task_type": "comprehensive",
            "workflow_steps": [],
            "results": {}
        }
        
        try:
            # 步骤1: 数据分析
            yield self.create_progress_result("步骤1/3: 数据源分析")
            
            analysis_results = []
            async for result in self._orchestrate_data_analysis(context, **kwargs):
                analysis_results.append(result)
                if result.type == ToolResultType.PROGRESS:
                    yield result
            
            if analysis_results and analysis_results[-1].type == ToolResultType.RESULT:
                comprehensive_result["results"]["data_analysis"] = analysis_results[-1].data
                comprehensive_result["workflow_steps"].append("data_analysis_completed")
                self.add_insight(context, "数据分析阶段完成")
            
            # 步骤2: SQL生成（如果有占位符）
            if context.placeholders:
                yield self.create_progress_result("步骤2/3: SQL生成")
                
                sql_results = []
                async for result in self._orchestrate_sql_generation(context, **kwargs):
                    sql_results.append(result)
                    if result.type == ToolResultType.PROGRESS:
                        yield result
                
                if sql_results and sql_results[-1].type == ToolResultType.RESULT:
                    comprehensive_result["results"]["sql_generation"] = sql_results[-1].data
                    comprehensive_result["workflow_steps"].append("sql_generation_completed")
                    self.add_insight(context, "SQL生成阶段完成")
            else:
                comprehensive_result["workflow_steps"].append("sql_generation_skipped")
                self.add_insight(context, "无占位符，跳过SQL生成")
            
            # 步骤3: 报告生成
            yield self.create_progress_result("步骤3/3: 报告生成")
            
            # 准备报告数据摘要
            report_data_summary = self._prepare_comprehensive_data_summary(comprehensive_result)
            
            report_results = []
            async for result in self._orchestrate_report_generation(
                context,
                report_type="analysis_report",
                data_summary=report_data_summary,
                **kwargs
            ):
                report_results.append(result)
                if result.type == ToolResultType.PROGRESS:
                    yield result
            
            if report_results and report_results[-1].type == ToolResultType.RESULT:
                comprehensive_result["results"]["report_generation"] = report_results[-1].data
                comprehensive_result["workflow_steps"].append("report_generation_completed")
                self.add_insight(context, "报告生成阶段完成")
            
            # 计算综合成功率
            completed_steps = len([step for step in comprehensive_result["workflow_steps"] if "completed" in step])
            total_planned_steps = 3
            success_rate = completed_steps / total_planned_steps
            
            # 生成综合洞察
            comprehensive_insights = [
                f"综合工作流完成 {completed_steps}/{total_planned_steps} 个步骤",
                f"成功率: {success_rate:.1%}",
                "端到端任务编排完成"
            ]
            
            if context.learned_insights:
                comprehensive_insights.extend(context.learned_insights[-3:])
            
            yield self.create_success_result(
                data=comprehensive_result,
                confidence=success_rate,
                insights=comprehensive_insights
            )
            
        except Exception as e:
            self.logger.error(f"综合工作流编排异常: {e}")
            yield self.create_error_result(f"综合工作流编排失败: {str(e)}")
    
    async def _orchestrate_custom_workflow(
        self,
        context: ToolContext,
        workflow_steps: List[str],
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """编排自定义工作流"""
        
        yield self.create_progress_result("🎨 开始自定义工作流编排")
        
        custom_result = {
            "task_type": "custom",
            "planned_steps": workflow_steps,
            "executed_steps": [],
            "results": {}
        }
        
        try:
            for i, step in enumerate(workflow_steps):
                yield self.create_progress_result(f"执行步骤 {i+1}/{len(workflow_steps)}: {step}")
                
                step_result = await self._execute_workflow_step(context, step, **kwargs)
                
                if step_result:
                    custom_result["results"][step] = step_result
                    custom_result["executed_steps"].append(step)
                    self.add_insight(context, f"自定义步骤 {step} 完成")
                else:
                    self.logger.warning(f"自定义步骤 {step} 执行失败")
            
            success_rate = len(custom_result["executed_steps"]) / len(workflow_steps)
            
            yield self.create_success_result(
                data=custom_result,
                confidence=success_rate,
                insights=[
                    f"自定义工作流完成 {len(custom_result['executed_steps'])}/{len(workflow_steps)} 个步骤",
                    f"成功率: {success_rate:.1%}",
                    "自定义编排完成"
                ]
            )
            
        except Exception as e:
            self.logger.error(f"自定义工作流编排异常: {e}")
            yield self.create_error_result(f"自定义工作流编排失败: {str(e)}")
    
    async def _execute_workflow_step(
        self,
        context: ToolContext,
        step_name: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """执行工作流步骤"""
        
        try:
            if step_name == "data_analysis":
                results = []
                async for result in self.data_analyzer.execute(context, **kwargs):
                    results.append(result)
                
                return results[-1].data if results and results[-1].type == ToolResultType.RESULT else None
            
            elif step_name == "sql_generation":
                if not context.placeholders:
                    return {"error": "缺少占位符信息"}
                
                results = []
                async for result in self._orchestrate_sql_generation(context, **kwargs):
                    results.append(result)
                
                return results[-1].data if results and results[-1].type == ToolResultType.RESULT else None
            
            elif step_name == "report_generation":
                results = []
                async for result in self.report_generator.execute(context, **kwargs):
                    results.append(result)
                
                return results[-1].data if results and results[-1].type == ToolResultType.RESULT else None
            
            else:
                self.logger.warning(f"未知的工作流步骤: {step_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"执行工作流步骤 {step_name} 异常: {e}")
            return None
    
    def _extract_data_summary_from_history(self, context: ToolContext) -> Dict[str, Any]:
        """从执行历史中提取数据摘要"""
        
        data_summary = {}
        
        try:
            # 提取SQL结果
            sql_results = []
            analysis_results = []
            
            for history in context.iteration_history:
                result = history.get("result", {})
                
                if isinstance(result, dict):
                    if "sql" in result:
                        sql_results.append(result)
                    elif "analysis_type" in result:
                        analysis_results.append(result)
            
            if sql_results:
                data_summary["sql_queries"] = sql_results
            
            if analysis_results:
                data_summary["analysis_results"] = analysis_results
            
            # 提取数据源信息
            if context.data_source_info:
                data_summary["data_source"] = context.data_source_info
            
            # 提取占位符信息
            if context.placeholders:
                data_summary["placeholders"] = context.placeholders
            
        except Exception as e:
            self.logger.error(f"提取数据摘要异常: {e}")
        
        return data_summary
    
    def _prepare_comprehensive_data_summary(self, comprehensive_result: Dict[str, Any]) -> Dict[str, Any]:
        """准备综合数据摘要"""
        
        data_summary = {
            "workflow_type": "comprehensive",
            "completed_steps": comprehensive_result.get("workflow_steps", [])
        }
        
        results = comprehensive_result.get("results", {})
        
        # 数据分析结果
        if "data_analysis" in results:
            analysis_data = results["data_analysis"].get("analysis_result", {})
            data_summary["data_analysis"] = analysis_data
        
        # SQL生成结果
        if "sql_generation" in results:
            sql_data = results["sql_generation"]
            data_summary["sql_generation"] = {
                "placeholders_processed": sql_data.get("placeholders_processed", 0),
                "success_count": sql_data.get("success_count", 0),
                "has_sql_results": bool(sql_data.get("sql_results"))
            }
        
        return data_summary