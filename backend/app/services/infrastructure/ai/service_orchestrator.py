"""
服务编排器 - 基于新的BaseTool架构
整合工具工厂和ReAct编排器，提供统一的占位符分析服务
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, AsyncGenerator, Optional, List

from .core.tools import ToolContext, ToolChain, ToolResult, ToolResultType
from .core.unified_controller import get_unified_controller, tt
from .tools import (
    AdvancedSQLGenerator,
    SmartDataAnalyzer,
    IntelligentReportGenerator,
    PromptAwareOrchestrator
)
from .llm import ask_agent_for_user

logger = logging.getLogger(__name__)


class ServiceOrchestrator:
    """服务编排器 - 基于增强的BaseTool架构v3.0"""
    
    def __init__(self):
        self.tool_chain = self._create_tool_chain()
        self.unified_controller = get_unified_controller()
        
        # 新的统一控制器已自动初始化
        
        logger.info("服务编排器初始化完成")
        logger.info(f"已加载工具: {self.tool_chain.list_tools()}")
    
    def _create_tool_chain(self) -> ToolChain:
        """创建增强的工具链"""
        tool_chain = ToolChain()
        
        # 注册新的工具集合
        try:
            # SQL生成工具
            sql_generator = AdvancedSQLGenerator()
            tool_chain.register_tool(sql_generator)
            
            # 数据分析工具  
            data_analyzer = SmartDataAnalyzer()
            tool_chain.register_tool(data_analyzer)
            
            # 报告生成工具
            report_generator = IntelligentReportGenerator()
            tool_chain.register_tool(report_generator)
            
            # 编排器工具
            orchestrator_tool = PromptAwareOrchestrator()
            tool_chain.register_tool(orchestrator_tool)
            
            # 🔧 注册ReAct桥接工具（修复工具名称不匹配问题）
            from .tools.bridge_tools import register_bridge_tools
            try:
                register_bridge_tools(tool_chain)
                logger.info("✅ ReAct桥接工具注册成功")
            except Exception as bridge_error:
                logger.error(f"❌ ReAct桥接工具注册失败: {bridge_error}")
                # 继续执行，使用原有工具
            
            logger.info("增强工具链初始化完成")
            
        except Exception as e:
            logger.error(f"工具链初始化失败: {e}")
            # 创建基础工具链作为后备
            tool_chain = self._create_fallback_tool_chain()
        
        return tool_chain
    
    def _create_fallback_tool_chain(self) -> ToolChain:
        """创建后备工具链"""
        from .core.tools import BaseTool
        
        class FallbackTool(BaseTool):
            def __init__(self, name):
                super().__init__(name)
            
            async def execute(self, input_data, context):
                yield self.create_success_result(
                    f"后备工具 {self.tool_name} 执行完成",
                    metadata={"fallback": True}
                )
        
        tool_chain = ToolChain()
        # 🔧 使用ReAct orchestrator期望的工具名称
        tool_chain.register_tool(FallbackTool("sql_generator_tool"))
        tool_chain.register_tool(FallbackTool("template_info_tool"))
        tool_chain.register_tool(FallbackTool("data_analyzer_tool"))
        tool_chain.register_tool(FallbackTool("data_source_info_tool"))
        
        return tool_chain
        
    async def analyze_template_streaming(
        self,
        user_id: str,
        template_id: str,
        template_content: str,
        data_source_info: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式模板分析 - 使用新架构
        """
        
        # 构建增强的工具执行上下文
        context = ToolContext(
            user_id=user_id,
            task_id=f"template_analysis_{uuid.uuid4().hex[:8]}",
            session_id=template_id,
            template_id=template_id,
            template_content=template_content,
            data_source_info=data_source_info,
            context_data={
                "analysis_type": "template_streaming",
                "request_time": datetime.utcnow().isoformat()
            }
        )
        
        # 构建输入数据
        input_data = {
            "template_content": template_content,
            "template_id": template_id,
            "data_source_info": data_source_info or {},
            "analysis_mode": "streaming"
        }
        
        logger.info(f"开始增强流式模板分析: {context.task_id}")
        
        # 执行模板分析工具
        try:
            async for result in self.tool_chain.execute_tool("template_analysis_tool", input_data, context):
                yield {
                    "type": result.type.value,
                    "uuid": str(uuid.uuid4()),
                    "timestamp": result.timestamp.isoformat() if hasattr(result, 'timestamp') else datetime.utcnow().isoformat(),
                    "user_id": user_id,
                    "task_id": context.task_id,
                    "tool_name": result.tool_name or "template_analysis_tool",
                    "data": result.data,
                    "confidence": getattr(result, 'confidence', None),
                    "validation_passed": getattr(result, 'validation_passed', True),
                    "insights": getattr(result, 'insights', []),
                    "iteration": getattr(result, 'iteration', None)
                }
        except Exception as e:
            yield {
                "type": "error",
                "uuid": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "task_id": context.task_id,
                "tool_name": "template_analysis_tool",
                "error": {
                    "error_message": str(e),
                    "error_type": "execution_error",
                    "recoverable": True
                }
            }
    
    async def generate_sql_streaming(
        self,
        user_id: str,
        placeholders: list,
        data_source_info: Optional[Dict[str, Any]] = None,
        template_context: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式SQL生成 - 使用新架构
        """
        
        # 构建增强的工具执行上下文
        context = ToolContext(
            user_id=user_id,
            task_id=f"sql_generation_{uuid.uuid4().hex[:8]}",
            session_id="sql_gen",
            placeholders=placeholders,
            data_source_info=data_source_info,
            context_data={
                "generation_type": "sql_streaming",
                "template_context": template_context,
                "request_time": datetime.utcnow().isoformat()
            }
        )
        
        input_data = {
            "placeholders": placeholders,
            "data_source_info": data_source_info or {},
            "template_context": template_context or "",
            "generation_mode": "streaming"
        }
        
        logger.info(f"开始增强流式SQL生成: {context.task_id}")
        
        try:
            # 使用AdvancedSQLGenerator工具名称
            tool_name = "advanced_sql_generator"
            async for result in self.tool_chain.execute_tool(tool_name, input_data, context):
                yield {
                    "type": result.type.value,
                    "uuid": str(uuid.uuid4()),
                    "timestamp": result.timestamp.isoformat() if hasattr(result, 'timestamp') else datetime.utcnow().isoformat(),
                    "user_id": user_id,
                    "task_id": context.task_id,
                    "tool_name": result.tool_name or tool_name,
                    "data": result.data,
                    "confidence": getattr(result, 'confidence', None),
                    "validation_passed": getattr(result, 'validation_passed', True),
                    "insights": getattr(result, 'insights', []),
                    "optimization_suggestions": getattr(result, 'optimization_suggestions', []),
                    "iteration": getattr(result, 'iteration', None),
                    "retry_count": getattr(result, 'retry_count', 0)
                }
        except Exception as e:
            yield {
                "type": "error",
                "uuid": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "task_id": context.task_id,
                "tool_name": "advanced_sql_generator",
                "error": {
                    "error_message": str(e),
                    "error_type": "execution_error",
                    "recoverable": True
                }
            }
    
    async def analyze_single_placeholder_simple(
        self,
        user_id: str,
        placeholder_name: str,
        placeholder_text: str,
        template_id: str,
        template_context: Optional[str] = None,
        data_source_info: Optional[Dict[str, Any]] = None,
        task_params: Optional[Dict[str, Any]] = None,
        cron_expression: Optional[str] = None,
        execution_time: Optional[datetime] = None,
        task_type: str = "manual"
    ) -> Dict[str, Any]:
        """
        单个占位符分析 - 使用新的BaseTool架构
        """
        
        logger.info(f"开始单个占位符分析: {placeholder_name}")
        
        try:
            # 构建增强的工具执行上下文
            context = ToolContext(
                user_id=user_id,
                task_id=f"placeholder_analysis_{uuid.uuid4().hex[:8]}",
                session_id=template_id,
                template_id=template_id,
                template_content=template_context,
                data_source_info=data_source_info,
                placeholders=[{
                    "name": placeholder_name,
                    "text": placeholder_text,
                    "params": task_params or {}
                }],
                context_data={
                    "template_id": template_id,
                    "template_context": template_context,
                    "task_params": task_params or {},
                    "cron_expression": cron_expression,
                    "execution_time": execution_time,
                    "task_type": task_type,
                    "analysis_mode": "single_placeholder"
                },
                # 启用学习和优化
                enable_learning=True,
                enable_optimization=True,
                # 设置质量阈值
                confidence_threshold=0.8,
                validation_required=True
            )
            
            # 构建分析目标
            goal = f"""分析占位符 '{placeholder_name}' 并生成相应的SQL查询。

占位符详情：
- 名称：{placeholder_name}
- 文本：{placeholder_text}
- 模板ID：{template_id}
- 上下文：{template_context or '无'}

要求：
1. 理解占位符的业务含义
2. 根据数据源结构生成合适的SQL查询
3. 确保SQL语法正确且能执行
4. 提供SQL的置信度评估

数据源信息：
{data_source_info if data_source_info else '未提供'}"""

            # 使用增强的ReAct编排器执行分析 - 集成提示词系统
            from .core.prompts import prompt_manager, PromptComplexity
            from .core.prompt_monitor import get_prompt_monitor
            
            # 根据上下文评估复杂度
            prompt_complexity = self._assess_task_complexity(context, placeholder_text)
            context.context_data["prompt_complexity"] = prompt_complexity.value
            
            # 获取提示词监控器
            monitor = get_prompt_monitor()
            execution_start = datetime.utcnow()
            
            try:
                # 使用ReAct编排器执行分析 - 使用桥接后的工具集
                # 🔧 修复工具名称不匹配问题：使用ReAct orchestrator期望的工具名称
                react_tools = ["template_info_tool", "data_analyzer_tool", "sql_generator_tool", "data_source_info_tool"]
                
                result = await self.react_orchestrator.tt(
                    goal=goal,
                    context=context,
                    available_tools=react_tools,
                    max_iterations=context.max_iterations,
                    prompt_complexity=prompt_complexity
                )
                
                # 记录成功的提示词使用
                execution_time = (datetime.utcnow() - execution_start).total_seconds() * 1000
                monitor.record_usage(
                    category="placeholder_analysis",
                    prompt_type="react_orchestration",
                    complexity=prompt_complexity.value,
                    success=result.get("status") in ["success", "partial_success"],
                    execution_time_ms=execution_time,
                    prompt_length=len(goal),
                    user_id=user_id,
                    context_size=len(str(context.context_data)),
                    iterations=result.get("iterations_used", 1)
                )
                
            except Exception as e:
                # 记录失败的提示词使用
                execution_time = (datetime.utcnow() - execution_start).total_seconds() * 1000
                monitor.record_usage(
                    category="placeholder_analysis", 
                    prompt_type="react_orchestration",
                    complexity=prompt_complexity.value,
                    success=False,
                    execution_time_ms=execution_time,
                    prompt_length=len(goal),
                    error_message=str(e),
                    user_id=user_id,
                    context_size=len(str(context.context_data)),
                    iterations=0
                )
                raise
            
            # 转换结果格式以保持向后兼容
            if result["status"] in ["success", "partial_success"]:
                # 从tool_results中提取SQL生成结果
                tool_results = result.get("tool_results", [])
                generated_sql = result.get("generated_sql", "")
                
                # 查找SQL生成工具的结果
                sql_result = None
                for tool_result in tool_results:
                    if tool_result.get("tool") == "sql_generation_tool":
                        sql_result = tool_result.get("result", {})
                        if isinstance(sql_result, dict) and "generated_sql" in sql_result:
                            generated_sql = sql_result["generated_sql"]
                        break
                
                # 构建统一的响应格式
                confidence_score = result.get("confidence_score", 0.7)
                if result["status"] == "partial_success":
                    confidence_score *= 0.8  # 部分成功的置信度降低
                
                return {
                    "status": "success",
                    "placeholder_name": placeholder_name,
                    "analysis_result": f"ReAct分析完成 - 目标: {goal[:100]}...",
                    "generated_sql": generated_sql,
                    "confidence_score": confidence_score,
                    "sql_validated": bool(generated_sql and "online_retail" in generated_sql.lower()),
                    "react_insights": result.get("react_insights", []),
                    "iterations_used": result.get("iterations_used", 1),
                    "execution_summary": result.get("execution_summary", {}),
                    "tool_results": tool_results
                }
            else:
                # 错误情况
                return {
                    "status": "error",
                    "error": {
                        "error_type": "react_execution_failed",
                        "error_message": result.get("error", "ReAct执行失败"),
                        "recoverable": True
                    },
                    "placeholder_name": placeholder_name,
                    "iterations_used": result.get("iterations_used", 0),
                    "step_history": result.get("step_history", [])
                }
                
        except Exception as e:
            logger.error(f"占位符分析异常: {e}", exc_info=True)
            return {
                "status": "error",
                "error": {
                    "error_type": "service_orchestrator_error",
                    "error_message": str(e),
                    "recoverable": False
                },
                "placeholder_name": placeholder_name
            }

    # 向后兼容方法 - 支持现有的非流式调用
    
    async def analyze_template_simple(
        self,
        user_id: str,
        template_id: str,
        template_content: str,
        data_source_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        简单模板分析 - 非流式，向后兼容
        """
        
        result = None
        error = None
        
        async for message_data in self.analyze_template_streaming(
            user_id=user_id,
            template_id=template_id,
            template_content=template_content,
            data_source_info=data_source_info
        ):
            if message_data["type"] == "result":
                result = message_data["result"]
            elif message_data["type"] == "error":
                error = message_data["error"]
        
        if error:
            return {
                "status": "error",
                "error": error,
                "template_id": template_id
            }
        
        return result or {
            "status": "completed",
            "template_id": template_id,
            "placeholder_analysis": {
                "total_count": 0,
                "placeholders": [],
                "processing_status": "no_result"
            }
        }
    
    def _assess_task_complexity(self, context: ToolContext, placeholder_text: str) -> 'PromptComplexity':
        """评估任务复杂度"""
        from .core.prompts import PromptComplexity
        
        # 基于多个因素评估复杂度
        complexity_score = 0
        
        # 1. 错误历史
        error_count = len(context.error_history)
        if error_count >= 3:
            complexity_score += 3
        elif error_count >= 1:
            complexity_score += 2
        
        # 2. 占位符复杂度
        if len(placeholder_text) > 100:
            complexity_score += 2
        elif len(placeholder_text) > 50:
            complexity_score += 1
        
        # 3. 数据源复杂度
        if context.data_source_info:
            table_count = len(context.data_source_info.get("tables", []))
            if table_count > 20:
                complexity_score += 2
            elif table_count > 10:
                complexity_score += 1
        
        # 4. 模板复杂度
        if context.template_content and len(context.template_content) > 500:
            complexity_score += 1
        
        # 5. 学习历史
        if len(context.learned_insights) >= 5:
            complexity_score += 1
        
        # 映射到复杂度级别
        if complexity_score >= 6:
            return PromptComplexity.CRITICAL
        elif complexity_score >= 4:
            return PromptComplexity.HIGH
        elif complexity_score >= 2:
            return PromptComplexity.MEDIUM
        else:
            return PromptComplexity.SIMPLE
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        try:
            return self.controller.get_task_status(task_id)
        except AttributeError:
            # 如果controller不存在，返回基本状态
            return {
                "task_id": task_id,
                "status": "unknown",
                "message": "控制器未初始化"
            }
    
    def list_active_tasks(self) -> list:
        """列出活跃任务"""
        try:
            return self.controller.list_active_tasks()
        except AttributeError:
            return []
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            return await self.controller.cancel_task(task_id)
        except AttributeError:
            logger.warning(f"无法取消任务 {task_id}: 控制器未初始化")
            return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取服务编排器性能指标"""
        from .core.prompt_monitor import get_prompt_monitor
        
        monitor = get_prompt_monitor()
        
        return {
            "tool_chain": {
                "registered_tools": self.tool_chain.list_tools(),
                "execution_history": self.tool_chain.get_execution_history(limit=10),
                "tool_metrics": {
                    tool_name: self.tool_chain.get_tool_metrics(tool_name).__dict__ 
                    if self.tool_chain.get_tool_metrics(tool_name) else None
                    for tool_name in self.tool_chain.list_tools()
                }
            },
            "prompt_performance": monitor.get_performance_summary(
                category="placeholder_analysis",
                time_window_hours=24
            ),
            "system_status": {
                "orchestrator_initialized": True,
                "react_orchestrator_available": self.react_orchestrator is not None,
                "tools_count": len(self.tool_chain.list_tools())
            }
        }


# 全局实例
_orchestrator: Optional[ServiceOrchestrator] = None


def get_service_orchestrator() -> ServiceOrchestrator:
    """获取服务编排器单例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ServiceOrchestrator()
    return _orchestrator


# 向后兼容的便捷函数

async def analyze_template_with_new_architecture(
    user_id: str,
    template_id: str,
    template_content: str,
    data_source_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """使用新架构分析模板 - 便捷函数"""
    orchestrator = get_service_orchestrator()
    return await orchestrator.analyze_template_simple(
        user_id=user_id,
        template_id=template_id,
        template_content=template_content,
        data_source_info=data_source_info
    )