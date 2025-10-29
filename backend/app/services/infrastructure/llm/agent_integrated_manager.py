"""
Agent集成的LLM管理器

将Agent系统深度集成到LLM基础设施层，让LLM服务原生支持Agent能力
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncIterator, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .pure_database_manager import PureDatabaseLLMManager, get_pure_llm_manager
from .model_executor import ModelExecutor, get_model_executor
from .types import TaskRequirement, ModelSelection, LLMExecutionContext

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Agent执行上下文"""
    agent_id: str
    user_id: str
    session_id: Optional[str] = None
    task_type: str = "general"
    complexity: str = "medium"
    
    # Agent特定配置
    enable_tools: bool = True
    enable_react: bool = True
    max_iterations: int = 5
    
    # 执行状态
    iteration_count: int = 0
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    context_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 性能监控
    start_time: Optional[datetime] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Agent响应结果"""
    content: str
    agent_id: str
    context: AgentContext
    
    # 执行信息
    tool_calls_made: List[Dict[str, Any]] = field(default_factory=list)
    model_used: Optional[str] = None
    execution_time: Optional[float] = None
    
    # 状态信息
    is_complete: bool = True
    needs_continuation: bool = False
    error: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentIntegratedLLMManager:
    """
    Agent集成的LLM管理器
    
    将Agent能力深度集成到LLM基础设施中，让LLM服务原生支持：
    1. Agent上下文管理
    2. 工具调用编排
    3. ReAct推理循环
    4. 多轮对话状态保持
    5. 智能模型选择和切换
    """
    
    def __init__(self):
        self.base_llm_manager = get_pure_llm_manager()
        self.model_executor = get_model_executor()
        
        # Agent状态管理
        self.active_agents: Dict[str, AgentContext] = {}
        self.agent_sessions: Dict[str, List[AgentContext]] = {}
        
        # 工具注册表
        self.available_tools: Dict[str, Any] = {}
        
        # 性能监控
        self.agent_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "tool_usage_stats": {}
        }
        
        self._initialize_tools()
        logger.info("Agent集成LLM管理器初始化完成")
    
    def _initialize_tools(self):
        """初始化可用工具"""
        # 从Agent系统导入工具
        try:
            from ..agents.tools.sql_tools import SQLGeneratorTool, SQLExecutorTool
            from ..agents.tools.data_transform import DataTransformTool
            from ..agents.tools.chart_builder import ChartBuilderTool
            from ..agents.tools.doc_assembler import DocumentAssemblerTool
            
            self.available_tools = {
                "sql_generator": SQLGeneratorTool(),
                # SQLExecutorTool 需要 container 参数，暂时注释掉
                # "sql_executor": SQLExecutorTool(),
                "data_transform": DataTransformTool(),
                "chart_builder": ChartBuilderTool(),
                "doc_assembler": DocumentAssemblerTool()
            }
            
            logger.info(f"已加载 {len(self.available_tools)} 个工具")
            
        except ImportError as e:
            logger.warning(f"部分工具加载失败: {e}")
            self.available_tools = {}
    
    async def ask_agent_with_context(
        self,
        user_id: str,
        question: str,
        agent_context: Optional[AgentContext] = None,
        **kwargs
    ) -> AgentResponse:
        """
        使用Agent上下文的智能问答
        
        这是LLM基础设施层提供给上层的主要Agent接口
        """
        start_time = datetime.now()
        self.agent_metrics["total_requests"] += 1
        
        try:
            # 创建或获取Agent上下文
            if agent_context is None:
                agent_context = AgentContext(
                    agent_id=f"agent_{user_id}_{int(start_time.timestamp())}",
                    user_id=user_id,
                    session_id=kwargs.get("session_id"),
                    task_type=kwargs.get("task_type", "general"),
                    complexity=kwargs.get("complexity", "medium"),
                    enable_tools=kwargs.get("enable_tools", True),
                    enable_react=kwargs.get("enable_react", True),
                    start_time=start_time
                )
            
            # 注册活跃Agent
            self.active_agents[agent_context.agent_id] = agent_context
            
            # 智能模型选择（基于Agent上下文）
            model_selection = await self._select_model_for_agent(agent_context, question)
            
            # 检查是否需要工具调用
            if agent_context.enable_tools:
                tool_plan = await self._analyze_tool_requirements(question, agent_context)
                if tool_plan["needs_tools"]:
                    return await self._execute_with_tools(question, agent_context, model_selection, tool_plan)
            
            # 直接LLM调用
            response = await self._execute_simple_llm_call(question, agent_context, model_selection)
            
            # 更新统计
            execution_time = (datetime.now() - start_time).total_seconds()
            self.agent_metrics["successful_requests"] += 1
            self._update_response_time(execution_time)
            
            return AgentResponse(
                content=response,
                agent_id=agent_context.agent_id,
                context=agent_context,
                model_used=model_selection.get("model"),
                execution_time=execution_time,
                is_complete=True
            )
            
        except Exception as e:
            logger.error(f"Agent执行失败: {e}")
            self.agent_metrics["failed_requests"] += 1
            
            return AgentResponse(
                content=f"执行失败: {str(e)}",
                agent_id=agent_context.agent_id if agent_context else "unknown",
                context=agent_context or AgentContext(agent_id="error", user_id=user_id),
                error=str(e),
                is_complete=True
            )
        
        finally:
            # 清理
            if agent_context and agent_context.agent_id in self.active_agents:
                del self.active_agents[agent_context.agent_id]
    
    async def _select_model_for_agent(self, agent_context: AgentContext, question: str) -> Dict[str, Any]:
        """为Agent选择最佳模型"""
        
        # 基于Agent上下文增强模型选择
        enhanced_context = {
            "user_id": agent_context.user_id,
            "task_type": agent_context.task_type,
            "complexity": agent_context.complexity,
            "agent_context": {
                "has_tool_calls": len(agent_context.tool_calls) > 0,
                "iteration_count": agent_context.iteration_count,
                "enable_tools": agent_context.enable_tools,
                "enable_react": agent_context.enable_react
            },
            "question_analysis": {
                "length": len(question),
                "has_sql_keywords": any(kw in question.lower() for kw in ["select", "insert", "update", "delete"]),
                "has_analysis_keywords": any(kw in question.lower() for kw in ["分析", "统计", "汇总", "分组"])
            }
        }
        
        # 调用底层模型选择服务
        selection = await self.base_llm_manager.select_best_model_for_user(
            user_id=agent_context.user_id,
            task_type=agent_context.task_type,
            complexity=agent_context.complexity,
            context=enhanced_context
        )
        
        # Agent特定的模型选择优化
        if agent_context.enable_react and enhanced_context["question_analysis"]["has_analysis_keywords"]:
            # 复杂分析任务使用更强的模型
            if selection.get("model") == "gpt-3.5-turbo":
                selection["model"] = "gpt-4"
                selection["reason"] = "Agent ReAct推理需要更强模型"
        
        return selection
    
    async def _analyze_tool_requirements(self, question: str, agent_context: AgentContext) -> Dict[str, Any]:
        """分析是否需要工具调用"""
        
        tool_plan = {
            "needs_tools": False,
            "suggested_tools": [],
            "execution_strategy": "sequential",
            "confidence": 0.0
        }
        
        question_lower = question.lower()
        
        # SQL相关工具检查
        if any(kw in question_lower for kw in ["sql", "查询", "数据库", "select", "table"]):
            tool_plan["needs_tools"] = True
            tool_plan["suggested_tools"].extend(["sql_generator", "sql_executor"])
            tool_plan["confidence"] += 0.8
        
        # 数据分析工具检查
        if any(kw in question_lower for kw in ["分析", "统计", "汇总", "分组", "计算"]):
            tool_plan["needs_tools"] = True
            tool_plan["suggested_tools"].append("data_transform")
            tool_plan["confidence"] += 0.6
        
        # 图表生成工具检查
        if any(kw in question_lower for kw in ["图表", "可视化", "chart", "graph", "plot"]):
            tool_plan["needs_tools"] = True
            tool_plan["suggested_tools"].append("chart_builder")
            tool_plan["confidence"] += 0.7
        
        # 文档生成工具检查
        if any(kw in question_lower for kw in ["报告", "文档", "导出", "生成"]):
            tool_plan["needs_tools"] = True
            tool_plan["suggested_tools"].append("doc_assembler")
            tool_plan["confidence"] += 0.5
        
        # 去重并标准化
        tool_plan["suggested_tools"] = list(set(tool_plan["suggested_tools"]))
        tool_plan["confidence"] = min(tool_plan["confidence"], 1.0)
        
        return tool_plan
    
    async def _execute_with_tools(
        self,
        question: str,
        agent_context: AgentContext,
        model_selection: Dict[str, Any],
        tool_plan: Dict[str, Any]
    ) -> AgentResponse:
        """使用工具执行复杂任务"""
        
        if not agent_context.enable_react:
            # 简单工具执行模式
            return await self._execute_simple_tool_call(question, agent_context, model_selection, tool_plan)
        else:
            # ReAct推理模式
            return await self._execute_react_loop(question, agent_context, model_selection, tool_plan)
    
    async def _execute_react_loop(
        self,
        question: str,
        agent_context: AgentContext,
        model_selection: Dict[str, Any],
        tool_plan: Dict[str, Any]
    ) -> AgentResponse:
        """执行ReAct推理循环"""
        
        conversation_history = [
            {
                "role": "system",
                "content": f"""你是一个智能助手，可以使用以下工具来回答问题：
{', '.join(tool_plan['suggested_tools'])}

请使用ReAct思维模式：
1. Thought（思考）：分析问题需要什么信息
2. Action（行动）：选择并调用合适的工具
3. Observation（观察）：分析工具返回的结果
4. 重复上述步骤直到获得完整答案

当前可用工具：{list(self.available_tools.keys())}
"""
            },
            {
                "role": "user", 
                "content": question
            }
        ]
        
        total_response = ""
        tool_calls_made = []
        
        for iteration in range(agent_context.max_iterations):
            agent_context.iteration_count = iteration + 1
            
            # LLM推理步骤
            llm_response = await self._call_llm_with_tools(
                conversation_history,
                agent_context,
                model_selection
            )
            
            total_response += f"\n[迭代 {iteration + 1}]\n{llm_response}"
            
            # 检查是否需要工具调用
            tool_call = self._extract_tool_call(llm_response)
            
            if tool_call:
                # 执行工具调用
                tool_result = await self._execute_tool_call(tool_call, agent_context)
                tool_calls_made.append({
                    "tool": tool_call["tool"],
                    "input": tool_call["input"],
                    "output": tool_result,
                    "iteration": iteration + 1
                })
                
                # 添加工具结果到对话历史
                conversation_history.append({
                    "role": "assistant",
                    "content": llm_response
                })
                conversation_history.append({
                    "role": "user",
                    "content": f"工具执行结果：{tool_result}"
                })
                
                # 更新工具使用统计
                tool_name = tool_call["tool"]
                if tool_name not in self.agent_metrics["tool_usage_stats"]:
                    self.agent_metrics["tool_usage_stats"][tool_name] = 0
                self.agent_metrics["tool_usage_stats"][tool_name] += 1
                
            else:
                # 没有工具调用，认为任务完成
                break
        
        return AgentResponse(
            content=total_response,
            agent_id=agent_context.agent_id,
            context=agent_context,
            tool_calls_made=tool_calls_made,
            model_used=model_selection.get("model"),
            is_complete=True,
            metadata={
                "iterations_used": agent_context.iteration_count,
                "tools_called": len(tool_calls_made),
                "react_mode": True
            }
        )
    
    async def _execute_simple_tool_call(
        self,
        question: str,
        agent_context: AgentContext,
        model_selection: Dict[str, Any],
        tool_plan: Dict[str, Any]
    ) -> AgentResponse:
        """简单工具调用模式"""
        
        # 为问题生成工具调用计划
        plan_prompt = f"""
根据用户问题：{question}
建议的工具：{tool_plan['suggested_tools']}

请生成具体的工具调用计划，格式：
工具名: 输入参数
"""
        
        plan_response = await self._call_llm_simple(plan_prompt, agent_context, model_selection)
        
        # 执行工具调用
        tool_results = []
        for tool_name in tool_plan['suggested_tools']:
            if tool_name in self.available_tools:
                try:
                    # 简化的工具参数提取
                    tool_input = {"question": question, "context": agent_context.context_history}
                    result = await self._execute_tool_call({
                        "tool": tool_name,
                        "input": tool_input
                    }, agent_context)
                    tool_results.append(f"{tool_name}: {result}")
                except Exception as e:
                    tool_results.append(f"{tool_name}: 执行失败 - {str(e)}")
        
        # 生成最终响应
        final_prompt = f"""
用户问题：{question}
工具执行结果：
{chr(10).join(tool_results)}

请基于工具结果生成完整的回答。
"""
        
        final_response = await self._call_llm_simple(final_prompt, agent_context, model_selection)
        
        return AgentResponse(
            content=final_response,
            agent_id=agent_context.agent_id,
            context=agent_context,
            tool_calls_made=[{"tools_used": tool_plan['suggested_tools'], "results": tool_results}],
            model_used=model_selection.get("model"),
            is_complete=True,
            metadata={"simple_tool_mode": True}
        )
    
    async def _execute_simple_llm_call(
        self,
        question: str,
        agent_context: AgentContext,
        model_selection: Dict[str, Any]
    ) -> str:
        """简单LLM调用"""
        return await self._call_llm_simple(question, agent_context, model_selection)
    
    async def _call_llm_simple(
        self,
        prompt: str,
        agent_context: AgentContext,
        model_selection: Dict[str, Any]
    ) -> str:
        """调用底层LLM服务"""
        
        # 使用现有的ask_agent接口
        from . import ask_agent
        
        response = await ask_agent(
            user_id=agent_context.user_id,
            question=prompt,
            agent_type=agent_context.task_type,
            context=str(agent_context.context_history),
            task_type=agent_context.task_type,
            complexity=agent_context.complexity
        )
        
        return response
    
    async def _call_llm_with_tools(
        self,
        messages: List[Dict[str, str]],
        agent_context: AgentContext,
        model_selection: Dict[str, Any]
    ) -> str:
        """带工具支持的LLM调用"""
        
        # 将消息转换为单个prompt
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(f"[{role}] {content}")
        
        combined_prompt = "\n\n".join(prompt_parts)
        
        return await self._call_llm_simple(combined_prompt, agent_context, model_selection)
    
    def _extract_tool_call(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """从LLM响应中提取工具调用"""
        
        # 简单的工具调用检测
        import re
        
        # 查找工具调用模式：工具名(参数)
        tool_pattern = r'(\w+)\s*\((.*?)\)'
        matches = re.findall(tool_pattern, llm_response)
        
        for tool_name, params in matches:
            if tool_name in self.available_tools:
                return {
                    "tool": tool_name,
                    "input": {"params": params, "full_response": llm_response}
                }
        
        return None
    
    async def _execute_tool_call(self, tool_call: Dict[str, Any], agent_context: AgentContext) -> str:
        """执行工具调用"""
        
        tool_name = tool_call["tool"]
        tool_input = tool_call["input"]
        
        if tool_name not in self.available_tools:
            return f"工具 {tool_name} 不可用"
        
        try:
            tool = self.available_tools[tool_name]
            result = await tool.execute(tool_input)
            return str(result)
        except Exception as e:
            logger.error(f"工具 {tool_name} 执行失败: {e}")
            return f"工具执行失败: {str(e)}"
    
    def _update_response_time(self, execution_time: float):
        """更新平均响应时间"""
        current_avg = self.agent_metrics["avg_response_time"]
        total_requests = self.agent_metrics["successful_requests"]
        
        self.agent_metrics["avg_response_time"] = (
            (current_avg * (total_requests - 1) + execution_time) / total_requests
        )
    
    def get_agent_metrics(self) -> Dict[str, Any]:
        """获取Agent性能指标"""
        return {
            **self.agent_metrics,
            "active_agents_count": len(self.active_agents),
            "available_tools_count": len(self.available_tools),
            "available_tools": list(self.available_tools.keys())
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        base_health = await self.base_llm_manager.health_check()
        
        return {
            **base_health,
            "agent_integration": {
                "status": "healthy",
                "active_agents": len(self.active_agents),
                "available_tools": len(self.available_tools),
                "total_requests": self.agent_metrics["total_requests"],
                "success_rate": (
                    self.agent_metrics["successful_requests"] / max(1, self.agent_metrics["total_requests"])
                ) * 100
            }
        }


# 全局实例管理
_global_agent_llm_manager: Optional[AgentIntegratedLLMManager] = None

def get_agent_integrated_llm_manager() -> AgentIntegratedLLMManager:
    """获取Agent集成的LLM管理器"""
    global _global_agent_llm_manager
    if _global_agent_llm_manager is None:
        _global_agent_llm_manager = AgentIntegratedLLMManager()
    return _global_agent_llm_manager


# 向后兼容的增强接口
async def ask_agent_enhanced(
    user_id: str,
    question: str,
    agent_type: str = "general",
    context: Optional[str] = None,
    task_type: str = "general",
    complexity: str = "medium",
    enable_tools: bool = True,
    enable_react: bool = True,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    增强的Agent问答接口
    
    保持与原始ask_agent兼容，但增加Agent能力
    """
    
    manager = get_agent_integrated_llm_manager()
    
    # 创建Agent上下文
    agent_context = AgentContext(
        agent_id=f"enhanced_agent_{user_id}_{int(datetime.now().timestamp())}",
        user_id=user_id,
        session_id=session_id,
        task_type=task_type,
        complexity=complexity,
        enable_tools=enable_tools,
        enable_react=enable_react
    )
    
    # 如果有上下文，解析并添加到历史
    if context:
        try:
            import json
            if context.startswith('[') or context.startswith('{'):
                agent_context.context_history = json.loads(context)
            else:
                agent_context.context_history = [{"content": context, "timestamp": datetime.now().isoformat()}]
        except:
            agent_context.context_history = [{"content": context, "timestamp": datetime.now().isoformat()}]
    
    # 执行Agent任务
    response = await manager.ask_agent_with_context(
        user_id=user_id,
        question=question,
        agent_context=agent_context
    )
    
    # 返回兼容格式
    return {
        "response": response.content,
        "agent_id": response.agent_id,
        "model_used": response.model_used,
        "execution_time": response.execution_time,
        "tool_calls": response.tool_calls_made,
        "metadata": response.metadata,
        "success": not bool(response.error),
        "error": response.error
    }