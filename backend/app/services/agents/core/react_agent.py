"""
React Intelligent Agent
基于LlamaIndex ReActAgent的纯粹智能代理实现
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms.llm import LLM
from llama_index.core.chat_engine.types import AgentChatResponse

from ..tools import create_all_tools, get_tools_summary
from .llm_adapter import create_llm_adapter, LLMClientAdapter

logger = logging.getLogger(__name__)


class ReactIntelligentAgent:
    """
    纯粹的ReAct智能代理
    
    特点:
    1. 基于LlamaIndex ReActAgent实现
    2. 具备完整的推理-行动循环能力
    3. 支持多轮对话和上下文记忆
    4. 自动工具选择和调用编排
    5. 透明的推理过程展示
    """
    
    def __init__(
        self,
        llm: Optional[LLM] = None,
        tools: Optional[List] = None,
        memory_token_limit: int = 4000,
        max_iterations: int = 15,
        verbose: bool = True,
        system_prompt: Optional[str] = None
    ):
        self.llm = llm
        self.tools = tools or []
        self.memory_token_limit = memory_token_limit
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.system_prompt = system_prompt
        
        self.agent: Optional[ReActAgent] = None
        self.initialized = False
        
        # 统计信息
        self.total_conversations = 0
        self.successful_conversations = 0
        self.total_tool_calls = 0
        self.average_reasoning_steps = 0.0
        self.start_time = datetime.utcnow()
    
    async def initialize(self):
        """初始化ReAct代理"""
        if self.initialized:
            return
        
        logger.info("初始化ReAct智能代理...")
        
        try:
            # 1. 创建LLM适配器（如果未提供）
            if not self.llm:
                self.llm = await create_llm_adapter(
                    model_name="react-agent",
                    user_id="system",
                    provider_preference=["openai", "anthropic"]
                )
            
            # 2. 创建工具集合（如果未提供）
            if not self.tools:
                self.tools = await create_all_tools()
            
            # 3. 创建ReAct代理
            self.agent = ReActAgent.from_tools(
                tools=self.tools,
                llm=self.llm,
                memory=ChatMemoryBuffer.from_defaults(token_limit=self.memory_token_limit),
                verbose=self.verbose,
                max_iterations=self.max_iterations,
                system_prompt=self.system_prompt or self._get_react_system_prompt()
            )
            
            self.initialized = True
            logger.info(f"ReAct代理初始化完成 - 工具数量: {len(self.tools)}, 最大推理轮次: {self.max_iterations}")
            
        except Exception as e:
            logger.error(f"ReAct代理初始化失败: {e}")
            raise
    
    def _get_react_system_prompt(self) -> str:
        """获取ReAct系统提示词"""
        tools_info = self._get_tools_description()
        
        return f"""你是一个专业的数据分析和报告生成助手，具备完整的ReAct推理能力。

## 核心能力
你可以通过"推理 → 行动 → 观察"的循环来解决复杂问题：
- **推理 (Thought)**: 分析当前状态，理解问题，规划下一步行动
- **行动 (Action)**: 选择并调用最合适的工具
- **观察 (Observation)**: 分析工具执行结果，决定下一步策略

## 可用工具概览
{tools_info}

## 工作流程
严格按照以下ReAct格式进行推理：

Thought: [分析当前状态和问题，规划解决方案]
Action: [工具名称]
Action Input: [工具所需参数的JSON格式]
Observation: [工具执行结果]

...继续推理循环，直到问题解决...

Final Answer: [最终完整答案]

## 工作原则
1. **深度思考**: 每次行动前都要充分思考和分析
2. **工具选择**: 根据任务需求选择最合适的工具
3. **循序渐进**: 复杂任务分解为多个简单步骤
4. **错误恢复**: 遇到错误时分析原因并调整策略
5. **结果验证**: 关键步骤后验证结果的正确性
6. **完整回答**: 最终答案要完整、准确、有用

## 典型工作场景
- **占位符处理**: extract_placeholders → analyze_placeholder_semantics → create_placeholder_mappings → execute_placeholder_replacement
- **数据查询**: analyze_data_source → generate_sql_query → execute_sql_with_monitoring
- **图表生成**: analyze_data_for_chart_recommendations → generate_intelligent_charts → optimize_chart_design
- **完整流程**: execute_complete_analysis_workflow 或相关工作流工具

请根据用户的具体需求，运用ReAct推理能力，智能选择和组合工具来解决问题。"""
    
    def _get_tools_description(self) -> str:
        """获取工具描述"""
        try:
            tools_summary = get_tools_summary()
            
            description = f"共有{tools_summary['total_tools']}个专业工具，分为{tools_summary['total_collections']}个类别：\\n"
            
            for category, details in tools_summary['collections_detail'].items():
                if 'error' not in details:
                    tool_count = details['tool_count']
                    description += f"- **{category}类工具** ({tool_count}个): "
                    
                    if category == "placeholder":
                        description += "占位符提取、语义分析和替换\\n"
                    elif category == "data":
                        description += "数据源分析、SQL生成和查询执行\\n"
                    elif category == "chart":
                        description += "图表生成、优化和可视化\\n"
                    elif category == "core":
                        description += "工作流编排和系统诊断\\n"
                    else:
                        description += "专业工具集合\\n"
            
            return description
            
        except Exception:
            return "多个专业工具类别，包括占位符处理、数据分析、图表生成等"
    
    async def chat(
        self,
        message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        智能对话接口
        
        Args:
            message: 用户消息
            chat_history: 对话历史
            max_tokens: 最大token限制
            
        Returns:
            包含响应、推理步骤和工具使用情况的结果
        """
        if not self.initialized:
            await self.initialize()
        
        start_time = time.time()
        self.total_conversations += 1
        
        try:
            logger.info(f"开始ReAct对话: {message[:100]}...")
            
            # 构建增强消息
            enhanced_message = self._build_enhanced_message(message, chat_history)
            
            # 执行ReAct推理
            response: AgentChatResponse = await self.agent.achat(enhanced_message)
            
            # 解析推理过程
            reasoning_steps = self._extract_reasoning_steps(response)
            tools_used = self._extract_tools_used(response)
            
            # 更新统计
            processing_time = time.time() - start_time
            self.successful_conversations += 1
            self.total_tool_calls += len(tools_used)
            self.average_reasoning_steps = (
                (self.average_reasoning_steps * (self.successful_conversations - 1) + len(reasoning_steps)) 
                / self.successful_conversations
            )
            
            result = {
                "success": True,
                "message": message,
                "response": response.response,
                "reasoning_steps": reasoning_steps,
                "tools_used": tools_used,
                "metadata": {
                    "processing_time": processing_time,
                    "reasoning_steps_count": len(reasoning_steps),
                    "tools_called_count": len(tools_used),
                    "max_iterations": self.max_iterations,
                    "model_info": getattr(self.llm, 'model', 'unknown')
                }
            }
            
            logger.info(f"ReAct对话完成 - 推理步骤: {len(reasoning_steps)}, 工具调用: {len(tools_used)}, 耗时: {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            logger.error(f"ReAct对话失败: {e}")
            
            return {
                "success": False,
                "message": message,
                "error": str(e),
                "error_type": type(e).__name__,
                "metadata": {
                    "processing_time": processing_time,
                    "reasoning_steps_count": 0,
                    "tools_called_count": 0
                }
            }
    
    def _build_enhanced_message(self, message: str, chat_history: Optional[List[Dict[str, str]]]) -> str:
        """构建增强消息"""
        enhanced_parts = []
        
        # 添加对话历史（如果有）
        if chat_history and len(chat_history) > 0:
            enhanced_parts.append("## 对话历史")
            for i, entry in enumerate(chat_history[-3:]):  # 只保留最近3轮对话
                role = entry.get("role", "unknown")
                content = entry.get("content", "")
                enhanced_parts.append(f"{role}: {content[:100]}{'...' if len(content) > 100 else ''}")
            enhanced_parts.append("")
        
        # 添加当前消息
        enhanced_parts.append("## 当前任务")
        enhanced_parts.append(message)
        
        # 添加ReAct提示
        enhanced_parts.append("")
        enhanced_parts.append("请使用ReAct推理模式来解决这个问题，按照 Thought → Action → Observation 的循环进行推理。")
        
        return "\\n".join(enhanced_parts)
    
    def _extract_reasoning_steps(self, response: AgentChatResponse) -> List[Dict[str, Any]]:
        """提取推理步骤"""
        try:
            steps = []
            
            # 从响应中提取推理过程
            if hasattr(response, 'source_nodes') and response.source_nodes:
                for i, node in enumerate(response.source_nodes):
                    if hasattr(node, 'metadata') and 'thought' in node.metadata:
                        step = {
                            "step_number": i + 1,
                            "thought": node.metadata.get('thought', ''),
                            "action": node.metadata.get('action', ''),
                            "action_input": node.metadata.get('action_input', {}),
                            "observation": node.metadata.get('observation', '')
                        }
                        steps.append(step)
            
            # 如果没有找到结构化的推理步骤，尝试从响应文本中解析
            if not steps and hasattr(response, 'response'):
                steps = self._parse_reasoning_from_text(response.response)
            
            return steps
            
        except Exception as e:
            logger.warning(f"提取推理步骤失败: {e}")
            return []
    
    def _parse_reasoning_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中解析推理步骤"""
        steps = []
        lines = text.split('\\n')
        current_step = {}
        step_number = 0
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('Thought:'):
                if current_step:
                    steps.append(current_step)
                step_number += 1
                current_step = {
                    "step_number": step_number,
                    "thought": line.replace('Thought:', '').strip(),
                    "action": "",
                    "action_input": {},
                    "observation": ""
                }
            elif line.startswith('Action:'):
                if current_step:
                    current_step["action"] = line.replace('Action:', '').strip()
            elif line.startswith('Action Input:'):
                if current_step:
                    input_text = line.replace('Action Input:', '').strip()
                    try:
                        import json
                        current_step["action_input"] = json.loads(input_text)
                    except:
                        current_step["action_input"] = {"raw": input_text}
            elif line.startswith('Observation:'):
                if current_step:
                    current_step["observation"] = line.replace('Observation:', '').strip()
        
        # 添加最后一个步骤
        if current_step:
            steps.append(current_step)
        
        return steps
    
    def _extract_tools_used(self, response: AgentChatResponse) -> List[str]:
        """提取使用的工具"""
        try:
            tools_used = []
            
            if hasattr(response, 'sources') and response.sources:
                for source in response.sources:
                    if hasattr(source, 'tool_name'):
                        tools_used.append(source.tool_name)
                    elif hasattr(source, 'metadata') and 'tool_name' in source.metadata:
                        tools_used.append(source.metadata['tool_name'])
            
            # 从推理步骤中提取工具名称
            if hasattr(response, 'source_nodes') and response.source_nodes:
                for node in response.source_nodes:
                    if hasattr(node, 'metadata') and 'action' in node.metadata:
                        action = node.metadata['action']
                        if action and action not in tools_used:
                            tools_used.append(action)
            
            return list(set(tools_used))  # 去重
            
        except Exception as e:
            logger.warning(f"提取工具使用情况失败: {e}")
            return []
    
    async def execute_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        执行复杂任务
        
        Args:
            task_description: 任务描述
            context: 任务上下文
            timeout: 超时时间（秒）
            
        Returns:
            任务执行结果
        """
        try:
            # 构建任务消息
            task_message = f"""
## 任务描述
{task_description}

## 任务要求
请使用ReAct推理模式完成以下任务：
1. 仔细分析任务需求
2. 制定详细的执行计划
3. 按步骤调用相应工具
4. 验证每步结果的正确性
5. 提供完整的任务总结

"""
            
            if context:
                task_message += f"""
## 上下文信息
{chr(10).join([f"- {k}: {v}" for k, v in context.items()])}
"""
            
            task_message += "\\n请开始执行任务。"
            
            # 执行任务（带超时控制）
            result = await asyncio.wait_for(
                self.chat(message=task_message),
                timeout=timeout
            )
            
            # 添加任务特定信息
            if result.get("success"):
                result.update({
                    "task_description": task_description,
                    "task_context": context,
                    "execution_timeout": timeout
                })
            
            return result
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "task_description": task_description,
                "error": f"任务执行超时（{timeout}秒）",
                "error_type": "timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "task_description": task_description,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取代理统计信息"""
        uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "agent_status": "initialized" if self.initialized else "not_initialized",
            "uptime_seconds": uptime_seconds,
            "total_conversations": self.total_conversations,
            "successful_conversations": self.successful_conversations,
            "failed_conversations": self.total_conversations - self.successful_conversations,
            "success_rate": (
                self.successful_conversations / max(self.total_conversations, 1)
            ),
            "total_tool_calls": self.total_tool_calls,
            "average_tool_calls_per_conversation": (
                self.total_tool_calls / max(self.successful_conversations, 1)
            ),
            "average_reasoning_steps": self.average_reasoning_steps,
            "configuration": {
                "memory_token_limit": self.memory_token_limit,
                "max_iterations": self.max_iterations,
                "tools_count": len(self.tools),
                "verbose": self.verbose
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            health_info = {
                "status": "healthy" if self.initialized else "not_initialized",
                "timestamp": datetime.utcnow().isoformat(),
                "agent_initialized": self.initialized,
                "tools_available": len(self.tools),
                "llm_status": "unknown"
            }
            
            # 检查LLM状态
            if self.llm and hasattr(self.llm, 'health_check'):
                try:
                    llm_health = await self.llm.health_check()
                    health_info["llm_status"] = llm_health.get("status", "unknown")
                except Exception as e:
                    health_info["llm_status"] = f"error: {str(e)}"
            
            # 检查工具状态
            tools_summary = get_tools_summary()
            health_info["tools_summary"] = tools_summary
            
            # 整体状态判断
            if (self.initialized and 
                len(self.tools) > 0 and 
                health_info["llm_status"] != "error"):
                health_info["status"] = "healthy"
            else:
                health_info["status"] = "degraded"
            
            return health_info
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def reset(self):
        """重置代理状态"""
        logger.info("重置ReAct代理...")
        
        try:
            # 清理现有代理
            if self.agent:
                # 清理内存
                if hasattr(self.agent, 'memory'):
                    self.agent.memory.reset()
            
            # 重新初始化
            self.initialized = False
            await self.initialize()
            
            # 重置统计信息
            self.total_conversations = 0
            self.successful_conversations = 0
            self.total_tool_calls = 0
            self.average_reasoning_steps = 0.0
            self.start_time = datetime.utcnow()
            
            logger.info("ReAct代理重置完成")
            
        except Exception as e:
            logger.error(f"ReAct代理重置失败: {e}")
            raise


# 全局代理实例
_global_react_agent: Optional[ReactIntelligentAgent] = None


async def get_react_agent() -> ReactIntelligentAgent:
    """获取全局ReAct代理实例"""
    global _global_react_agent
    if _global_react_agent is None:
        _global_react_agent = ReactIntelligentAgent()
        await _global_react_agent.initialize()
    return _global_react_agent


async def create_react_agent(
    llm: Optional[LLM] = None,
    tools: Optional[List] = None,
    memory_token_limit: int = 4000,
    max_iterations: int = 15,
    verbose: bool = True,
    system_prompt: Optional[str] = None
) -> ReactIntelligentAgent:
    """创建新的ReAct代理实例"""
    agent = ReactIntelligentAgent(
        llm=llm,
        tools=tools,
        memory_token_limit=memory_token_limit,
        max_iterations=max_iterations,
        verbose=verbose,
        system_prompt=system_prompt
    )
    await agent.initialize()
    return agent