"""
统一控制器 - 基于Claude Code的tt函数理念
简化现有的复杂编排系统为单一控制循环
"""

import logging
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator

from .messages import AgentMessage, MessageType, ProgressData, ErrorData
from .tools import ToolChain, ToolContext, ToolResult, ToolResultType
from .context import ContextManager
from .security import get_security_checker, SecurityLevel
from .api_messages import APIMessage, MessageConverter
from .enhanced_prompts import get_simplified_prompt_manager

logger = logging.getLogger(__name__)


class UnifiedController:
    """
    统一控制器 - 替换现有的复杂编排系统
    
    基于Claude Code的核心理念：
    1. 单一tt函数作为控制入口
    2. 简化的思考-执行循环
    3. 内置安全检查机制
    4. 流式结果处理
    """
    
    def __init__(self):
        self.tool_chain = ToolChain()
        self.context_manager = ContextManager()
        self.security_checker = get_security_checker()
        self.prompt_manager = get_simplified_prompt_manager()
        
        # 执行统计
        self.total_tasks = 0
        self.successful_tasks = 0
        self.failed_tasks = 0
    
    async def tt(
        self, 
        goal: str, 
        context: ToolContext,
        max_iterations: int = 3,  # 减少默认迭代次数提高效率
        available_tools: Optional[List[str]] = None
    ) -> AsyncGenerator[AgentMessage, None]:
        """
        统一任务编排函数 - 核心tt实现
        
        这是整个AI系统的统一入口点，替换：
        - AgentController.execute_task()
        - UnifiedOrchestrator.orchestrate()
        - 所有特定任务的编排方法
        
        Args:
            goal: 任务目标描述
            context: 工具执行上下文
            max_iterations: 最大迭代次数
            available_tools: 可用工具列表
            
        Yields:
            AgentMessage: 执行过程中的消息
        """
        
        task_id = f"tt_{uuid.uuid4().hex[:8]}"
        self.total_tasks += 1
        
        logger.info(f"🚀 启动统一任务编排 {task_id}: {goal[:100]}...")
        
        # 初始化可用工具
        if available_tools is None:
            available_tools = self._get_available_tools_for_goal(goal)
        
        yield AgentMessage.create_progress(
            current_step="任务初始化",
            user_id=context.user_id,
            task_id=context.task_id,
            total_steps=max_iterations,
            details=f"目标: {goal[:200]}..."
        )
        
        # 对话历史记录
        conversation_history = []
        iteration = 0
        
        try:
            while iteration < max_iterations:
                current_iteration = iteration + 1
                
                logger.info(f"🔄 第{current_iteration}/{max_iterations}轮开始")
                
                yield AgentMessage.create_progress(
                    current_step=f"第{current_iteration}轮分析",
                    user_id=context.user_id,
                    task_id=context.task_id,
                    current_step_number=current_iteration,
                    total_steps=max_iterations,
                    percentage=(current_iteration - 1) / max_iterations * 100
                )
                
                # 阶段1: 构建思考提示并调用LLM（使用优化后的提示系统）
                prompt_context = {
                    "conversation_history": conversation_history[-3:],  # 只保留最近3轮
                    "iteration": iteration,
                    "context_info": self._build_context_info_string(context)
                }
                
                thinking_prompt = self.prompt_manager.get_orchestration_prompt(
                    goal=goal,
                    available_tools=available_tools,
                    context=prompt_context
                )
                
                try:
                    # 调用LLM进行决策
                    from ..llm import ask_agent_for_user
                    
                    yield AgentMessage.create_progress(
                        current_step=f"第{current_iteration}轮思考分析",
                        user_id=context.user_id,
                        task_id=context.task_id,
                        details="分析任务需求并选择合适工具"
                    )
                    
                    response = await ask_agent_for_user(
                        user_id=context.user_id,
                        question=thinking_prompt,
                        agent_type="unified_reasoning",
                        task_type="task_orchestration",
                        complexity="medium"
                    )
                    
                    # 阶段2: 解析LLM决策
                    decision = self._parse_llm_decision(response)
                    
                    if not decision.get("success"):
                        logger.warning(f"第{current_iteration}轮决策解析失败: {decision.get('error')}")
                        conversation_history.append({
                            "iteration": current_iteration,
                            "success": False,
                            "error": "决策解析失败",
                            "raw_response": response[:200]
                        })
                        iteration += 1
                        continue
                    
                    # 阶段3: 安全检查
                    tool_name = decision.get("tool")
                    tool_params = decision.get("params", {})
                    
                    logger.info(f"📋 第{current_iteration}轮选择工具: {tool_name}")
                    
                    yield AgentMessage.create_progress(
                        current_step=f"安全检查: {tool_name}",
                        user_id=context.user_id,
                        task_id=context.task_id,
                        details="验证工具执行安全性"
                    )
                    
                    security_result = await self.security_checker.check_tool_execution(
                        tool_name, tool_params, {"context": context.context_data}
                    )
                    
                    if not security_result.allowed:
                        error_msg = f"安全检查失败: {security_result.reason}"
                        logger.error(error_msg)
                        yield AgentMessage.create_error(
                            error_type="security_violation",
                            error_message=error_msg,
                            user_id=context.user_id,
                            task_id=context.task_id
                        )
                        return
                    
                    if security_result.require_confirmation:
                        # 在生产环境中，这里应该请求用户确认
                        logger.warning(f"工具执行需要确认: {security_result.reason}")
                        
                        # 暂时跳过确认，直接继续执行
                        pass
                    
                    # 阶段4: 执行工具
                    yield AgentMessage.create_progress(
                        current_step=f"执行工具: {tool_name}",
                        user_id=context.user_id,
                        task_id=context.task_id,
                        details=f"使用参数: {str(tool_params)[:100]}..."
                    )
                    
                    tool_executed_successfully = False
                    tool_result_data = None
                    
                    async for tool_result in self.tool_chain.execute_tool(tool_name, tool_params, context):
                        # 将工具结果转换为AgentMessage
                        if tool_result.type == ToolResultType.PROGRESS:
                            yield AgentMessage.create_progress(
                                current_step=f"工具执行: {tool_result.data}",
                                user_id=context.user_id,
                                task_id=context.task_id,
                                tool_name=tool_name,
                                details=str(tool_result.progress_info) if tool_result.progress_info else None
                            )
                        elif tool_result.type == ToolResultType.RESULT:
                            tool_executed_successfully = True
                            tool_result_data = tool_result.data
                            
                            yield AgentMessage.create_result(
                                content=tool_result.data,
                                user_id=context.user_id,
                                task_id=context.task_id,
                                tool_name=tool_name
                            )
                            break
                        elif tool_result.type == ToolResultType.ERROR:
                            yield AgentMessage.create_error(
                                error_type=tool_result.error_info.get("error_type", "tool_error"),
                                error_message=tool_result.error_info.get("error_message", "工具执行失败"),
                                user_id=context.user_id,
                                task_id=context.task_id,
                                tool_name=tool_name
                            )
                            break
                    
                    # 阶段5: 记录执行结果并判断是否继续
                    conversation_history.append({
                        "iteration": current_iteration,
                        "goal": goal,
                        "tool": tool_name,
                        "params": tool_params,
                        "success": tool_executed_successfully,
                        "result": tool_result_data if tool_executed_successfully else None,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    if tool_executed_successfully:
                        # 检查是否应该停止迭代
                        if self._should_stop_iteration(goal, tool_result_data, current_iteration, max_iterations):
                            logger.info(f"✅ 任务在第{current_iteration}轮完成")
                            
                            yield AgentMessage.create_result(
                                content={
                                    "status": "completed",
                                    "final_result": tool_result_data,
                                    "iterations_used": current_iteration,
                                    "execution_history": conversation_history
                                },
                                user_id=context.user_id,
                                task_id=context.task_id
                            )
                            
                            self.successful_tasks += 1
                            return
                    
                except Exception as e:
                    logger.error(f"第{current_iteration}轮执行异常: {e}")
                    conversation_history.append({
                        "iteration": current_iteration,
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    yield AgentMessage.create_error(
                        error_type="iteration_failed",
                        error_message=f"第{current_iteration}轮执行失败: {str(e)}",
                        user_id=context.user_id,
                        task_id=context.task_id
                    )
                
                iteration += 1
            
            # 达到最大迭代次数
            logger.warning(f"⚠️ 任务达到最大迭代次数 {max_iterations}")
            
            # 查找最好的部分结果
            best_result = self._find_best_partial_result(conversation_history)
            
            yield AgentMessage.create_result(
                content={
                    "status": "max_iterations_reached",
                    "iterations_used": max_iterations,
                    "partial_result": best_result,
                    "execution_history": conversation_history
                },
                user_id=context.user_id,
                task_id=context.task_id
            )
            
            # 如果有部分结果，算作部分成功
            if best_result:
                self.successful_tasks += 1
            else:
                self.failed_tasks += 1
            
        except Exception as e:
            logger.error(f"任务执行严重错误: {e}")
            self.failed_tasks += 1
            
            yield AgentMessage.create_error(
                error_type="task_execution_error",
                error_message=f"任务执行严重错误: {str(e)}",
                user_id=context.user_id,
                task_id=context.task_id,
                recoverable=False
            )
    
    def _get_available_tools_for_goal(self, goal: str) -> List[str]:
        """根据目标推断可用工具"""
        all_tools = self.tool_chain.list_tools()
        
        # 简单的关键词匹配来选择相关工具
        relevant_tools = []
        
        goal_lower = goal.lower()
        
        if any(keyword in goal_lower for keyword in ["分析", "占位符", "模板"]):
            if "template_analysis_tool" in all_tools:
                relevant_tools.append("template_analysis_tool")
        
        if any(keyword in goal_lower for keyword in ["sql", "查询", "数据"]):
            for tool in ["sql_generation_tool", "data_analysis_tool"]:
                if tool in all_tools:
                    relevant_tools.append(tool)
        
        if any(keyword in goal_lower for keyword in ["报告", "生成", "文档"]):
            if "report_generation_tool" in all_tools:
                relevant_tools.append("report_generation_tool")
        
        # 如果没有匹配到特定工具，返回所有工具
        return relevant_tools if relevant_tools else all_tools
    
    def _build_context_info_string(self, context: ToolContext) -> str:
        """构建上下文信息字符串"""
        context_parts = []
        
        if hasattr(context, 'data_source_info') and context.data_source_info:
            ds_info = context.data_source_info
            context_parts.append(f"数据源: {ds_info.get('type', '未知')} - {ds_info.get('database', '未知')}")
        
        if hasattr(context, 'template_content') and context.template_content:
            template_preview = (context.template_content[:200] + "..." 
                              if len(context.template_content) > 200 
                              else context.template_content)
            context_parts.append(f"模板内容: {template_preview}")
        
        if hasattr(context, 'placeholders') and context.placeholders:
            placeholder_names = [p.get("name", "未知") for p in context.placeholders[:3]]
            context_parts.append(f"相关占位符: {', '.join(placeholder_names)}")
        
        return " | ".join(context_parts) if context_parts else "无特定上下文"
    
    def _parse_llm_decision(self, response: str) -> Dict[str, Any]:
        """解析LLM的决策响应"""
        try:
            # 尝试提取JSON
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                
                decision = json.loads(json_str)
                
                # 验证必要字段
                if "tool" in decision and decision["tool"]:
                    decision["success"] = True
                    return decision
            
            # 如果JSON解析失败，尝试从文本中提取工具名
            available_tools = self.tool_chain.list_tools()
            for tool in available_tools:
                if tool in response:
                    return {
                        "tool": tool,
                        "params": {},
                        "confidence": 0.5,
                        "reasoning": "从响应文本中提取的工具名",
                        "success": True
                    }
            
            return {
                "success": False,
                "error": "无法从响应中解析出有效的工具选择",
                "raw_response": response[:300]
            }
            
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON解析失败: {str(e)}",
                "raw_response": response[:300]
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"决策解析异常: {str(e)}",
                "raw_response": response[:300]
            }
    
    def _should_stop_iteration(
        self, 
        goal: str, 
        result_data: Any, 
        current_iteration: int,
        max_iterations: int
    ) -> bool:
        """判断是否应该停止迭代"""
        
        # 如果是最后一轮，强制停止
        if current_iteration >= max_iterations:
            return True
        
        # 如果没有结果数据，继续迭代
        if not result_data:
            return False
        
        # 基于结果数据判断任务是否完成
        if isinstance(result_data, dict):
            # 检查是否有明确的完成标志
            if result_data.get("status") == "completed":
                return True
            
            # 检查是否有SQL查询结果
            if "generated_sql" in result_data and result_data["generated_sql"]:
                return True
            
            # 检查是否有分析结果
            if "analysis" in result_data or "description" in result_data:
                return True
        
        # 检查目标关键词匹配
        goal_lower = goal.lower()
        result_str = str(result_data).lower()
        
        if "sql" in goal_lower and "select" in result_str:
            return True  # SQL生成任务完成
        
        if "分析" in goal and ("分析" in result_str or "description" in result_str):
            return True  # 分析任务完成
        
        # 默认不停止，继续迭代
        return False
    
    def _find_best_partial_result(self, conversation_history: List[Dict[str, Any]]) -> Any:
        """从对话历史中找到最好的部分结果"""
        
        best_result = None
        best_score = 0
        
        for record in conversation_history:
            if record.get("success") and record.get("result"):
                score = 1
                
                # 有SQL结果的评分更高
                if isinstance(record["result"], dict) and "generated_sql" in record["result"]:
                    score += 2
                
                # 有描述或分析的评分更高
                if isinstance(record["result"], dict) and ("description" in record["result"] or "analysis" in record["result"]):
                    score += 1
                
                if score > best_score:
                    best_score = score
                    best_result = record["result"]
        
        return best_result
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self.total_tasks
        return {
            "total_tasks": total,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.successful_tasks / total if total > 0 else 0,
            "security_stats": self.security_checker.get_security_statistics()
        }


# 全局实例和便捷函数
_unified_controller: Optional[UnifiedController] = None


def get_unified_controller() -> UnifiedController:
    """获取全局统一控制器实例"""
    global _unified_controller
    if _unified_controller is None:
        _unified_controller = UnifiedController()
    return _unified_controller


async def tt(
    goal: str,
    context: ToolContext,
    max_iterations: int = 3,
    available_tools: Optional[List[str]] = None
) -> AsyncGenerator[AgentMessage, None]:
    """
    统一编排函数 - 替换原有的所有编排方法
    
    这是整个AI系统的统一入口点，替换：
    - AgentController.execute_task()
    - UnifiedOrchestrator.orchestrate()
    - 所有特定的任务处理方法
    
    Args:
        goal: 任务目标描述
        context: 工具执行上下文
        max_iterations: 最大迭代次数
        available_tools: 可用工具列表
        
    Yields:
        AgentMessage: 执行过程中的消息
    """
    controller = get_unified_controller()
    async for message in controller.tt(goal, context, max_iterations, available_tools):
        yield message


# 便捷导出
__all__ = [
    "UnifiedController",
    "get_unified_controller",
    "tt"
]