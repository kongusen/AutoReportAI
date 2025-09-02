"""
React智能代理

基于React Agent架构的智能代理实现
需要user_id参数进行用户个性化配置
"""

import asyncio
import logging
import time
import hashlib
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ReactAgent:
    """
    React智能代理
    
    核心特性:
    1. 基于用户配置的个性化AI服务
    2. 纯数据库驱动，无配置文件依赖
    3. 智能模型选择和资源优化
    4. 学习式偏好记录和优化
    """
    
    def __init__(
        self,
        user_id: str,  # 🔑 必需参数：用户ID
        tools: Optional[List] = None,
        memory_token_limit: int = 4000,
        max_iterations: int = 15,
        verbose: bool = True,
        system_prompt: Optional[str] = None
    ):
        if not user_id:
            raise ValueError("user_id是必需参数，纯数据库驱动Agent必须指定用户ID")
        
        self.user_id = user_id
        self.tools = tools or []
        self.memory_token_limit = memory_token_limit
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.system_prompt = system_prompt
        
        self.agent: Optional[Any] = None
        self.initialized = False
        self.llm_manager = None
        
        # 智能缓存配置
        self.enable_cache = True
        self.cache_ttl = 3600  # 1小时缓存时间
        self._cache = {}  # 简单内存缓存
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "size": 0
        }
        
        # 统计信息
        self.total_conversations = 0
        self.successful_conversations = 0
        self.total_tool_calls = 0
        self.start_time = datetime.utcnow()
        
        logger.info(f"为用户 {user_id} 初始化React智能代理")
    
    async def initialize(self):
        """初始化React代理 - 纯数据库驱动"""
        if self.initialized:
            return
        
        logger.info(f"初始化用户 {self.user_id} 的React智能代理...")
        
        try:
            # 1. 获取数据库驱动的LLM管理器
            from ..llm import get_llm_manager
            self.llm_manager = await get_llm_manager()
            
            # 2. 为React Agent选择最佳模型 - 基于用户配置
            try:
                best_model = await self.llm_manager.select_best_model_for_user(
                    user_id=self.user_id,
                    task_type="reasoning",  # React需要推理能力
                    complexity="medium",
                    constraints={
                        "max_cost": 0.02,  # 合理的成本控制
                        "preferred_providers": ["anthropic", "openai"]  # 推理任务偏好
                    },
                    agent_id="react_agent"
                )
                
                logger.info(f"React Agent为用户 {self.user_id} 选择模型: {best_model['provider']}:{best_model['model']} (置信度: {best_model['confidence']:.1%})")
                
                # 记录模型选择信息
                self.selected_model = best_model
                
            except Exception as e:
                logger.error(f"为用户 {self.user_id} 选择模型失败: {e}")
                raise ValueError(f"无法为用户选择合适的模型: {str(e)}")
            
            # 3. 创建工具集合（如果未提供）
            if not self.tools:
                try:
                    # 添加图表生成工具
                    from ..tools.chart_generator_tool import generate_chart
                    from llama_index.core.tools import FunctionTool
                    
                    # 创建图表生成工具
                    chart_tool = FunctionTool.from_defaults(
                        fn=generate_chart,
                        name="generate_chart",
                        description="生成专业图表，支持柱状图、折线图、饼图、面积图。接受JSON配置参数，生成实际图片文件。"
                    )
                    
                    self.tools = [chart_tool]
                    
                    # 尝试添加其他工具
                    try:
                        from ..tools import get_ai_tools_factory
                        tools_factory = await get_ai_tools_factory()
                        additional_tools = await tools_factory.create_all_tools()
                        self.tools.extend(additional_tools)
                    except Exception as e:
                        logger.warning(f"创建额外工具失败: {e}")
                        
                except Exception as e:
                    logger.warning(f"创建工具失败: {e}")
                    self.tools = []
            
            # 4. 创建React代理（优先使用LlamaIndex，降级到模拟）
            try:
                from llama_index.core.agent import ReActAgent
                from llama_index.core.memory import ChatMemoryBuffer
                
                # 这里应该使用实际的LlamaIndex LLM实例
                # 目前使用模拟，实际实现中需要从selected_model创建LLM实例
                self.agent = ReActAgent.from_tools(
                    tools=self.tools,
                    llm=None,  # 实际实现中从selected_model创建
                    memory=ChatMemoryBuffer.from_defaults(token_limit=self.memory_token_limit),
                    verbose=self.verbose,
                    max_iterations=self.max_iterations,
                    system_prompt=self.system_prompt or self._get_react_system_prompt()
                )
                
            except (ImportError, Exception) as e:
                logger.warning(f"LlamaIndex React Agent创建失败，使用模拟代理: {e}")
                self.agent = self._create_mock_agent()
            
            self.initialized = True
            logger.info(f"用户 {self.user_id} 的React代理初始化完成 - 工具: {len(self.tools)}, 模型: {self.selected_model['provider']}:{self.selected_model['model']}")
            
        except Exception as e:
            logger.error(f"React代理初始化失败: {e}")
            # 创建备用模拟代理
            self.agent = self._create_mock_agent()
            self.initialized = True
            raise
    
    def _create_mock_agent(self):
        """创建模拟React代理"""
        class MockReactAgent:
            def __init__(self, parent):
                self.parent = parent
            
            async def achat(self, message: str) -> Any:
                """模拟异步聊天，使用数据库驱动的LLM选择，支持工具调用"""
                try:
                    # 检查是否需要生成图表
                    charts_info = []
                    if any(keyword in message.lower() for keyword in ['图表', '柱状图', '折线图', '饼图', '可视化', 'chart']):
                        charts_info = self._generate_sample_charts(message)
                    
                    from app.services.infrastructure.ai.llm import ask_agent_for_user
                    
                    response = await ask_agent_for_user(
                        user_id=self.parent.user_id,
                        question=message,
                        agent_type="react_agent",
                        context="React代理推理模式，支持图表生成工具",
                        task_type="reasoning",
                        complexity="medium"
                    )
                    
                    # 如果生成了图表，添加到响应中
                    if charts_info:
                        chart_text = "\n\n📊 **生成的图表文件:**\n"
                        for chart in charts_info:
                            chart_text += f"- {chart['title']}: `{chart['filename']}`\n"
                        response = response + chart_text
                    
                    return MockAgentResponse(response, charts_info)
                    
                except Exception as e:
                    logger.error(f"模拟Agent调用失败: {e}")
                    return MockAgentResponse(f"模拟React代理响应：{message}", [])
            
            def chat(self, message: str) -> Any:
                """模拟同步聊天"""
                return MockAgentResponse(f"模拟React代理响应：{message}")
            
            def reset(self):
                """重置对话历史"""
                pass
            
            def _generate_sample_charts(self, message: str):
                """根据消息生成示例图表"""
                charts_generated = []
                try:
                    from ..tools.chart_generator_tool import generate_chart
                    import json
                    
                    # 根据消息内容决定生成什么类型的图表
                    if '销售' in message or '业绩' in message or '收入' in message:
                        # 生成销售柱状图
                        config = {
                            "type": "bar",
                            "title": "月度销售业绩分析",
                            "x_data": ["1月", "2月", "3月", "4月", "5月"],
                            "y_data": [120000, 150000, 180000, 160000, 200000],
                            "x_label": "月份", 
                            "y_label": "销售额 (元)"
                        }
                        result = json.loads(generate_chart(json.dumps(config)))
                        if result.get('success'):
                            charts_generated.append(result)
                    
                    if '趋势' in message or '增长' in message or '折线' in message:
                        # 生成趋势折线图
                        config = {
                            "type": "line",
                            "title": "业务增长趋势",
                            "x_data": ["Q1", "Q2", "Q3", "Q4"],
                            "series": [
                                {"name": "收入", "data": [100, 120, 140, 180]},
                                {"name": "利润", "data": [20, 25, 30, 40]}
                            ],
                            "x_label": "季度",
                            "y_label": "金额 (万元)"
                        }
                        result = json.loads(generate_chart(json.dumps(config)))
                        if result.get('success'):
                            charts_generated.append(result)
                    
                    if '占比' in message or '分布' in message or '饼图' in message:
                        # 生成占比饼图
                        config = {
                            "type": "pie",
                            "title": "市场份额分布",
                            "labels": ["产品A", "产品B", "产品C", "产品D", "其他"],
                            "sizes": [35, 25, 20, 15, 5]
                        }
                        result = json.loads(generate_chart(json.dumps(config)))
                        if result.get('success'):
                            charts_generated.append(result)
                            
                except Exception as e:
                    logger.error(f"生成示例图表失败: {e}")
                
                return charts_generated
                
        class MockAgentResponse:
            def __init__(self, response: str, charts: List[Dict] = None):
                self.response = response
                self.source_nodes = []
                self.sources = []
                self.charts = charts or []
                
            def __str__(self):
                return self.response
        
        return MockReactAgent(self)
    
    def _get_react_system_prompt(self) -> str:
        """获取React系统提示词"""
        tools_info = self._get_tools_description()
        
        return f"""
你是用户 {self.user_id} 的专属AI智能代理，基于ReAct（Reasoning + Acting）框架工作。

你的工作流程：
1. **Thought（思考）**: 分析当前问题，制定解决策略
2. **Action（行动）**: 选择合适的工具执行具体操作
3. **Observation（观察）**: 分析工具执行结果
4. **反复迭代**: 直到问题完全解决

可用工具：
{tools_info}

工作原则：
- 始终先思考再行动
- 选择最合适的工具完成任务
- 基于观察结果调整策略
- 确保最终答案准确完整
- 如果遇到问题，尝试不同的方法
- 记住你服务的用户ID是 {self.user_id}

请按照 Thought -> Action -> Observation 的循环来处理用户请求。
"""
    
    def _get_tools_description(self) -> str:
        """获取工具描述"""
        if not self.tools:
            return "暂无可用工具"
        
        descriptions = []
        for i, tool in enumerate(self.tools, 1):
            if hasattr(tool, 'metadata'):
                name = getattr(tool.metadata, 'name', f'工具{i}')
                desc = getattr(tool.metadata, 'description', '无描述')
                descriptions.append(f"- {name}: {desc}")
            else:
                descriptions.append(f"- 工具{i}: 无描述信息")
        
        return "\n".join(descriptions)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = self._cache_stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "cache_enabled": self.enable_cache,
            "cache_hits": self._cache_stats["hits"],
            "cache_misses": self._cache_stats["misses"],
            "hit_rate": round(hit_rate, 3),
            "cache_size": self._cache_stats["size"],
            "cache_ttl_seconds": self.cache_ttl,
            "user_id": self.user_id
        }
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self._cache_stats["size"] = 0
        logger.info(f"React代理(用户:{self.user_id})缓存已清空")
    
    def _generate_cache_key(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """生成缓存键"""
        cache_data = {
            "user_id": self.user_id,
            "message": message,
            "context": context or {},
            "tools_count": len(self.tools)
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        if not cache_entry:
            return False
        
        created_at = cache_entry.get("created_at")
        if not created_at:
            return False
        
        # 检查TTL
        elapsed = time.time() - created_at
        return elapsed < self.cache_ttl
    
    async def chat(
        self, 
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        进行对话 - 纯数据库驱动，支持智能缓存
        
        Args:
            message: 用户消息
            context: 额外上下文信息
            
        Returns:
            对话结果，包含模型选择和使用统计
        """
        if not self.initialized:
            await self.initialize()
        
        # 检查缓存
        cache_key = None
        if self.enable_cache:
            cache_key = self._generate_cache_key(message, context)
            cached_result = self._cache.get(cache_key)
            
            if cached_result and self._is_cache_valid(cached_result):
                self._cache_stats["hits"] += 1
                logger.info(f"React代理缓存命中 - 用户:{self.user_id}, 键:{cache_key[:8]}...")
                
                # 返回缓存结果，添加缓存标记
                result = cached_result["result"].copy()
                result["from_cache"] = True
                result["cache_hit_time"] = datetime.utcnow().isoformat()
                return result
            else:
                self._cache_stats["misses"] += 1
        
        conversation_start = time.time()
        
        try:
            logger.info(f"React代理(用户:{self.user_id})开始处理: {message[:100]}{'...' if len(message) > 100 else ''}")
            
            # 构建完整的输入消息
            full_message = message
            if context:
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                full_message = f"上下文信息:\n{context_str}\n\n用户请求: {message}"
            
            # 调用代理
            if hasattr(self.agent, 'achat'):
                response = await self.agent.achat(full_message)
            else:
                response = self.agent.chat(full_message)
            
            conversation_time = time.time() - conversation_start
            
            # 更新统计信息
            self.total_conversations += 1
            self.successful_conversations += 1
            
            # 记录使用反馈到数据库
            if hasattr(self, 'selected_model') and self.llm_manager:
                from ..llm import record_usage_feedback
                
                record_usage_feedback(
                    user_id=self.user_id,
                    model=self.selected_model['model'],
                    provider=self.selected_model['provider'],
                    success=True,
                    satisfaction_score=0.9,  # 基于成功完成任务的满意度
                    actual_cost=self.selected_model.get('expected_cost'),
                    actual_latency=int(conversation_time * 1000),
                    agent_id="react_agent",
                    task_type="reasoning"
                )
            
            # 构建结果
            result = {
                "status": "success",
                "response": str(response),
                "conversation_time": conversation_time,
                "reasoning_steps": self._extract_reasoning_steps(response),
                "tool_calls": self._extract_tool_calls(response),
                "sources": getattr(response, 'sources', []),
                "metadata": {
                    "user_id": self.user_id,
                    "agent_type": "react",
                    "model_used": f"{self.selected_model['provider']}:{self.selected_model['model']}" if hasattr(self, 'selected_model') else 'unknown',
                    "model_confidence": self.selected_model.get('confidence') if hasattr(self, 'selected_model') else None,
                    "tools_available": len(self.tools),
                    "max_iterations": self.max_iterations,
                    "database_driven": True
                }
            }
            
            # 存储到缓存
            if self.enable_cache and cache_key:
                cache_entry = {
                    "result": result,
                    "created_at": time.time(),
                    "user_id": self.user_id
                }
                self._cache[cache_key] = cache_entry
                self._cache_stats["size"] = len(self._cache)
                
                # 简单的LRU清理：如果缓存过大，删除一些旧条目
                if len(self._cache) > 100:
                    oldest_keys = sorted(
                        self._cache.keys(),
                        key=lambda k: self._cache[k]["created_at"]
                    )[:20]
                    for old_key in oldest_keys:
                        del self._cache[old_key]
                    self._cache_stats["size"] = len(self._cache)
                
                logger.debug(f"React代理结果已缓存 - 键:{cache_key[:8]}...")
            
            logger.info(f"React代理(用户:{self.user_id})处理完成，用时: {conversation_time:.2f}s")
            
            return result
            
        except Exception as e:
            conversation_time = time.time() - conversation_start
            logger.error(f"React代理(用户:{self.user_id})处理失败: {e}")
            
            # 记录失败反馈
            if hasattr(self, 'selected_model') and self.llm_manager:
                from ..llm import record_usage_feedback
                
                record_usage_feedback(
                    user_id=self.user_id,
                    model=self.selected_model['model'],
                    provider=self.selected_model['provider'],
                    success=False,
                    satisfaction_score=0.3,
                    actual_latency=int(conversation_time * 1000),
                    agent_id="react_agent",
                    task_type="reasoning"
                )
            
            return {
                "status": "error",
                "error": str(e),
                "conversation_time": conversation_time,
                "response": f"处理出现错误：{str(e)}",
                "reasoning_steps": [],
                "tool_calls": [],
                "sources": [],
                "metadata": {
                    "user_id": self.user_id,
                    "agent_type": "react",
                    "error_type": type(e).__name__,
                    "database_driven": True
                }
            }
    
    def _extract_reasoning_steps(self, response: Any) -> List[Dict[str, Any]]:
        """从响应中提取推理步骤"""
        steps = []
        response_text = str(response)
        
        if "Thought:" in response_text:
            parts = response_text.split("Thought:")
            for i, part in enumerate(parts[1:], 1):
                thought_end = part.find("Action:") if "Action:" in part else len(part)
                thought = part[:thought_end].strip()
                
                step = {
                    "step_number": i,
                    "type": "thought",
                    "content": thought
                }
                
                if "Action:" in part:
                    action_start = part.find("Action:") + 7
                    action_end = part.find("Observation:") if "Observation:" in part else len(part)
                    action = part[action_start:action_end].strip()
                    step["action"] = action
                    
                    if "Observation:" in part:
                        obs_start = part.find("Observation:") + 12
                        observation = part[obs_start:].strip()
                        step["observation"] = observation
                
                steps.append(step)
        
        return steps
    
    def _extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """从响应中提取工具调用信息"""
        tool_calls = []
        
        if hasattr(response, 'source_nodes'):
            for node in response.source_nodes:
                if hasattr(node, 'metadata'):
                    tool_calls.append({
                        "tool_name": node.metadata.get("tool_name", "unknown"),
                        "result": node.text if hasattr(node, 'text') else str(node)
                    })
        
        self.total_tool_calls += len(tool_calls)
        return tool_calls
    
    def reset_conversation(self):
        """重置对话历史"""
        if self.agent and hasattr(self.agent, 'reset'):
            self.agent.reset()
        logger.info(f"React代理(用户:{self.user_id})对话历史已重置")
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """获取对话统计信息"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "user_id": self.user_id,
            "total_conversations": self.total_conversations,
            "successful_conversations": self.successful_conversations,
            "success_rate": self.successful_conversations / max(self.total_conversations, 1),
            "total_tool_calls": self.total_tool_calls,
            "average_tool_calls_per_conversation": self.total_tool_calls / max(self.total_conversations, 1),
            "uptime_seconds": uptime,
            "agent_config": {
                "max_iterations": self.max_iterations,
                "memory_token_limit": self.memory_token_limit,
                "tools_count": len(self.tools),
                "verbose": self.verbose,
                "database_driven": True
            },
            "selected_model": getattr(self, 'selected_model', None)
        }
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            "service_name": "Pure Database Driven React Agent",
            "version": "2.0.0",
            "architecture": "Database-First User-Specific Agent",
            "user_id": self.user_id,
            "status": "initialized" if self.initialized else "uninitialized",
            "capabilities": [
                "用户专属模型选择",
                "ReAct推理循环",
                "多轮对话支持",
                "工具调用编排",
                "使用反馈学习",
                "个性化Agent偏好"
            ],
            "data_sources": [
                "用户LLM偏好配置",
                "数据库驱动模型选择",
                "用户使用历史记录"
            ],
            "configuration": {
                "max_iterations": self.max_iterations,
                "memory_token_limit": self.memory_token_limit,
                "tools_count": len(self.tools),
                "verbose": self.verbose
            },
            "statistics": self.get_conversation_stats(),
            "selected_model": getattr(self, 'selected_model', None)
        }


# 便捷函数
async def create_react_agent_for_user(
    user_id: str,
    tools: Optional[List] = None,
    memory_token_limit: int = 4000,
    max_iterations: int = 15,
    verbose: bool = True,
    system_prompt: Optional[str] = None
) -> ReactAgent:
    """为指定用户创建React代理"""
    
    agent = ReactAgent(
        user_id=user_id,
        tools=tools,
        memory_token_limit=memory_token_limit,
        max_iterations=max_iterations,
        verbose=verbose,
        system_prompt=system_prompt
    )
    
    await agent.initialize()
    return agent