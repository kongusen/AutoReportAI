"""
统一 Facade 接口

为 Agent 系统提供统一的业务接口
封装复杂的内部实现，提供简洁易用的 API
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, AsyncGenerator, Tuple, Union

from .types import (
    AgentRequest, AgentResponse, ExecutionStage, TaskComplexity,
    AgentConfig, AgentEvent, ContextInfo
)
from .runtime import LoomAgentRuntime, build_default_runtime, create_runtime_with_context_retriever, StageAwareRuntime, build_stage_aware_runtime
from .context_retriever import create_schema_context_retriever
from .config.agent import create_default_agent_config, AgentConfigManager
from .prompts.system import create_system_prompt
from .prompts.stages import get_stage_prompt
from .prompts.templates import format_request_prompt, format_result_summary

logger = logging.getLogger(__name__)


def _extract_response_metrics(response_payload: Any) -> Tuple[float, int]:
    """提取质量评分和迭代次数，兼容字典和AgentResponse对象"""
    if isinstance(response_payload, AgentResponse):
        return (
            response_payload.quality_score or 0.0,
            response_payload.iterations_used or 0,
        )
    if isinstance(response_payload, dict):
        quality = response_payload.get("quality_score", 0.0) or 0.0
        iterations = response_payload.get("iterations_used", 0) or 0
        return (float(quality), int(iterations))
    return 0.0, 0


class LoomAgentFacade:
    """
    Loom Agent 统一 Facade 接口
    
    提供简洁的业务接口，封装复杂的内部实现
    """

    def __init__(
        self,
        container: Any,
        config: Optional[AgentConfig] = None,
        enable_context_retriever: bool = True
    ):
        """
        Args:
            container: 服务容器
            config: Agent 配置
            enable_context_retriever: 是否启用上下文检索器
        """
        self.container = container
        self.config = config or create_default_agent_config()
        self.enable_context_retriever = enable_context_retriever
        
        # 运行时实例
        self._runtime: Optional[LoomAgentRuntime] = None
        self._config_manager = AgentConfigManager(self.config)
        
        # 状态管理
        self._initialized = False
        self._active_requests: Dict[str, AgentRequest] = {}
        
        logger.info("🏗️ [LoomAgentFacade] 初始化完成")
    
    async def initialize(
        self,
        user_id: Optional[str] = None,
        task_type: str = "placeholder_analysis",
        task_complexity: Union[TaskComplexity, float] = 0.5
    ):
        """初始化 Facade

        Args:
            user_id: 用户ID
            task_type: 任务类型
            task_complexity: 任务复杂度，可以是 TaskComplexity 枚举或 float (0.0-1.0)
        """
        if self._initialized:
            return

        try:
            logger.info("🚀 [LoomAgentFacade] 开始初始化")

            # 转换 task_complexity 为 float
            complexity_value = float(task_complexity) if isinstance(task_complexity, (TaskComplexity, float, int)) else 0.5

            # 如果提供了用户ID，解析用户配置
            if user_id:
                logger.info(f"🔧 解析用户配置: user_id={user_id}, task_type={task_type}, complexity={task_complexity}")
                self.config = await self._config_manager.resolve_user_config(user_id, task_type, complexity_value)
                logger.info(f"✅ 用户配置解析完成: max_context_tokens={self.config.max_context_tokens}")
            
            # 验证配置
            validation_results = self._config_manager.validate_config()
            if any(validation_results.values()):
                logger.warning("⚠️ 配置验证发现问题，使用默认配置")
                self.config = create_default_agent_config()
                self._config_manager = AgentConfigManager(self.config)
            
            # 创建运行时
            self._runtime = await self._create_runtime()
            
            self._initialized = True
            logger.info("✅ [LoomAgentFacade] 初始化完成")
            
        except Exception as e:
            logger.error(f"❌ [LoomAgentFacade] 初始化失败: {e}", exc_info=True)
            raise
    
    async def _create_runtime(self) -> LoomAgentRuntime:
        """创建运行时实例"""
        if self.enable_context_retriever:
            # 创建带上下文检索器的运行时
            return build_default_runtime(
                container=self.container,
                config=self.config
            )
        else:
            # 创建基础运行时
            return build_default_runtime(
                container=self.container,
                config=self.config
            )

    async def analyze_placeholder(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        task_context: Optional[Dict[str, Any]] = None,
        template_context: Optional[Dict[str, Any]] = None,
        max_iterations: Optional[int] = None,
        complexity: Optional[TaskComplexity] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        分析占位符（生成 SQL）- 使用 TT 自动迭代

        这是主要的业务接口，用于分析占位符并生成相应的 SQL 查询

        Args:
            placeholder: 占位符文本
            data_source_id: 数据源ID
            user_id: 用户ID
            task_context: 任务上下文
            template_context: 模板上下文
            max_iterations: 最大迭代次数
            complexity: 任务复杂度
            constraints: 约束条件

        Yields:
            AgentEvent: 执行事件流
        """
        # 使用LLM自主判断任务复杂度和模型选择
        model_selection_result = await self._assess_and_select_model(
            placeholder, user_id, task_context, complexity
        )

        if not self._initialized:
            await self.initialize(
                user_id=user_id,
                task_type="placeholder_analysis",
                task_complexity=model_selection_result["complexity_assessment"]["complexity_score"]
            )

        # 🔥 关键修复：为每个请求动态创建带 ContextRetriever 的运行时
        if self.enable_context_retriever:
            logger.info(f"🔍 [LoomAgentFacade] 为数据源 {data_source_id} 创建带 Schema 上下文的运行时")
            try:
                # 🔧 设置当前用户ID以便获取正确的数据源配置
                self._current_user_id = user_id
                # 获取数据源连接配置
                connection_config = await self._get_connection_config(data_source_id)

                if connection_config:
                    # 创建带上下文检索器的运行时
                    context_retriever = create_schema_context_retriever(
                        data_source_id=str(data_source_id),
                        connection_config=connection_config,
                        container=self.container
                    )

                    # 初始化上下文检索器
                    await context_retriever.initialize()

                    # 创建带上下文的运行时（临时覆盖）
                    runtime_with_context = build_default_runtime(
                        container=self.container,
                        config=self.config,
                        context_retriever=context_retriever
                    )

                    logger.info(f"✅ [LoomAgentFacade] Schema 上下文运行时创建成功")
                    # 使用带上下文的运行时
                    runtime_to_use = runtime_with_context
                else:
                    logger.warning(f"⚠️ [LoomAgentFacade] 无法获取数据源 {data_source_id} 的连接配置，使用默认运行时")
                    runtime_to_use = self._runtime

            except Exception as e:
                logger.warning(f"⚠️ [LoomAgentFacade] 创建 Schema 上下文失败: {e}，使用默认运行时")
                runtime_to_use = self._runtime
        else:
            runtime_to_use = self._runtime

        # 创建请求
        request = AgentRequest(
            placeholder=placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            task_context=task_context or {},
            template_context=template_context,
            max_iterations=max_iterations or self.config.max_iterations,
            complexity=complexity or TaskComplexity.MEDIUM,
            constraints=constraints or {}
        )

        # 生成请求ID
        request_id = f"{user_id}_{data_source_id}_{int(time.time())}"
        self._active_requests[request_id] = request

        logger.info(f"🎯 [LoomAgentFacade] 开始分析占位符: {request_id}")
        logger.info(f"   占位符: {placeholder[:100]}...")
        logger.info(f"   数据源ID: {data_source_id}")
        logger.info(f"   用户ID: {user_id}")
        logger.info(f"   复杂度: {request.complexity.value}")

        try:
            # 发送开始事件
            start_event = AgentEvent(
                event_type="analysis_started",
                stage=ExecutionStage.INITIALIZATION,
                data={
                    "request_id": request_id,
                    "placeholder": placeholder,
                    "data_source_id": data_source_id,
                    "user_id": user_id,
                    "complexity": request.complexity.value
                }
            )
            yield start_event

            # 🔥 使用动态创建的运行时（带上下文）
            async for event in runtime_to_use.execute_with_tt(request):
                # 添加请求ID到事件数据
                event.data["request_id"] = request_id
                yield event

            # 发送完成事件
            completion_event = AgentEvent(
                event_type="analysis_completed",
                stage=ExecutionStage.COMPLETION,
                data={
                    "request_id": request_id,
                    "status": "success"
                }
            )
            yield completion_event
            
        except Exception as e:
            logger.error(f"❌ [LoomAgentFacade] 分析失败: {e}", exc_info=True)
            
            # 发送错误事件
            error_event = AgentEvent(
                event_type="analysis_failed",
                stage=ExecutionStage.INITIALIZATION,
                data={
                    "request_id": request_id,
                    "error": str(e),
                    "status": "error"
                }
            )
            yield error_event
            
            raise
        finally:
            # 清理请求记录
            if request_id in self._active_requests:
                del self._active_requests[request_id]
    
    async def analyze_placeholder_sync(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> AgentResponse:
        """
        同步分析占位符
        
        Args:
            placeholder: 占位符文本
            data_source_id: 数据源ID
            user_id: 用户ID
            **kwargs: 其他参数
            
        Returns:
            AgentResponse: 分析结果
        """
        result = None
        
        async for event in self.analyze_placeholder(
            placeholder=placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            **kwargs
        ):
            if event.event_type == "execution_completed":
                result = event.data["response"]
                break
            elif event.event_type == "execution_failed":
                raise Exception(f"分析失败: {event.data.get('error', 'Unknown error')}")
        
        if result is None:
            raise Exception("分析未完成")
        
        return result
    
    async def generate_sql(
        self,
        business_requirement: str,
        data_source_id: int,
        user_id: str,
        schema_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        生成 SQL 查询
        
        Args:
            business_requirement: 业务需求描述
            data_source_id: 数据源ID
            user_id: 用户ID
            schema_context: Schema 上下文
            **kwargs: 其他参数
            
        Returns:
            str: 生成的 SQL 查询
        """
        # 构建任务上下文
        task_context = kwargs.get("task_context", {})
        if schema_context:
            task_context["schema_context"] = schema_context
        
        # 设置约束条件
        constraints = kwargs.get("constraints", {})
        constraints["output_format"] = "sql"
        
        # 执行分析
        response = await self.analyze_placeholder_sync(
            placeholder=business_requirement,
            data_source_id=data_source_id,
            user_id=user_id,
            task_context=task_context,
            constraints=constraints,
            **kwargs
        )
        
        # 提取 SQL 结果
        if isinstance(response.result, str):
            return response.result
        elif isinstance(response.result, dict):
            return response.result.get("sql", response.result.get("result", ""))
        else:
            return str(response.result)
    
    async def analyze_data(
        self,
        sql_query: str,
        data_source_id: int,
        user_id: str,
        analysis_type: str = "summary",
        **kwargs
    ) -> Dict[str, Any]:
        """
        分析数据
        
        Args:
            sql_query: SQL 查询
            data_source_id: 数据源ID
            user_id: 用户ID
            analysis_type: 分析类型
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        # 构建分析任务
        analysis_placeholder = f"""
执行以下SQL查询并进行{analysis_type}分析：

```sql
{sql_query}
```

请提供：
1. 数据摘要和关键指标
2. 数据趋势和模式分析
3. 业务洞察和建议
4. 异常数据识别
"""
        
        # 构建任务上下文
        task_context = kwargs.get("task_context", {})
        task_context["analysis_type"] = analysis_type
        task_context["sql_query"] = sql_query
        
        # 执行分析
        response = await self.analyze_placeholder_sync(
            placeholder=analysis_placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            task_context=task_context,
            **kwargs
        )
        
        # 解析分析结果
        if isinstance(response.result, dict):
            return response.result
        else:
            return {
                "analysis_result": response.result,
                "quality_score": response.quality_score,
                "reasoning": response.reasoning
            }

    async def generate_chart(
        self,
        data_summary: str,
        chart_requirements: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成图表配置
        
        Args:
            data_summary: 数据摘要
            chart_requirements: 图表需求
            data_source_id: 数据源ID
            user_id: 用户ID
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 图表配置
        """
        # 构建图表生成任务
        chart_placeholder = f"""
基于以下数据摘要生成图表配置：

数据摘要：
{data_summary}

图表需求：
{chart_requirements}

请提供：
1. 合适的图表类型选择
2. 图表配置参数
3. 颜色和样式设置
4. 交互功能配置
"""
        
        # 构建任务上下文
        task_context = kwargs.get("task_context", {})
        task_context["data_summary"] = data_summary
        task_context["chart_requirements"] = chart_requirements
        
        # 设置约束条件
        constraints = kwargs.get("constraints", {})
        constraints["output_format"] = "chart_config"
        
        # 执行分析
        response = await self.analyze_placeholder_sync(
            placeholder=chart_placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            task_context=task_context,
            constraints=constraints,
            **kwargs
        )
        
        # 解析图表配置
        if isinstance(response.result, dict):
            return response.result
        else:
            return {
                "chart_config": response.result,
                "quality_score": response.quality_score,
                "reasoning": response.reasoning
            }
    
    async def get_schema_info(
        self,
        data_source_id: int,
        user_id: str,
        table_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        获取数据源 Schema 信息
        
        Args:
            data_source_id: 数据源ID
            user_id: 用户ID
            table_names: 指定表名列表
            
        Returns:
            Dict[str, Any]: Schema 信息
        """
        if not self._initialized:
            await self.initialize()
        
        # 创建上下文检索器
        try:
            # 获取数据源连接配置
            user_ds_service = self.container.user_data_source_service
            data_source = await user_ds_service.get_user_data_source(str(user_id), str(data_source_id))
            
            if not data_source:
                raise ValueError(f"未找到数据源: {data_source_id}")
            
            # 创建 Schema 检索器
            context_retriever = create_schema_context_retriever(
                data_source_id=str(data_source_id),
                connection_config=data_source.connection_config,
                container=self.container
            )
            
            # 初始化并获取 Schema
            await context_retriever.initialize()
            
            # 构建查询
            query = "获取表结构信息"
            if table_names:
                query += f" 表: {', '.join(table_names)}"
            
            # 检索 Schema 信息
            documents = await context_retriever.retrieve(query, top_k=20)
            
            # 解析结果
            schema_info = {
                "data_source_id": data_source_id,
                "tables": [],
                "total_tables": len(documents)
            }
            
            for doc in documents:
                table_info = {
                    "name": doc.metadata.get("table_name", ""),
                    "content": doc.content,
                    "relevance_score": doc.score
                }
                schema_info["tables"].append(table_info)
            
            return schema_info
            
        except Exception as e:
            logger.error(f"❌ [LoomAgentFacade] 获取 Schema 信息失败: {e}")
            return {
                "data_source_id": data_source_id,
                "tables": [],
                "total_tables": 0,
                "error": str(e)
            }
    
    def get_active_requests(self) -> Dict[str, AgentRequest]:
        """获取活跃请求列表"""
        return self._active_requests.copy()
    
    def get_config(self) -> AgentConfig:
        """获取当前配置"""
        return self.config
    
    def update_config(self, new_config: AgentConfig):
        """更新配置"""
        self.config = new_config
        self._config_manager = AgentConfigManager(self.config)
        self._initialized = False  # 需要重新初始化
        logger.info("🔄 [LoomAgentFacade] 配置已更新，需要重新初始化")
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取运行时指标"""
        if not self._runtime:
            return {}
        
        # 获取协调管理器指标
        if hasattr(self._runtime, '_config') and hasattr(self._runtime._config, 'coordination'):
            coordination_manager = getattr(self._runtime._config.coordination, '_manager', None)
            if coordination_manager:
                return coordination_manager.get_metrics_summary()
        
        return {
            "active_requests": len(self._active_requests),
            "initialized": self._initialized,
            "config": {
                "max_iterations": self.config.max_iterations,
                "max_context_tokens": self.config.max_context_tokens,
                "enabled_tools": len(self.config.tools.enabled_tools)
            }
        }
    
    def _calculate_task_complexity(self, placeholder: str, complexity: Optional[TaskComplexity]) -> float:
        """
        计算任务复杂度
        
        Args:
            placeholder: 占位符文本
            complexity: 用户指定的复杂度
            
        Returns:
            float: 任务复杂度 (0.0-1.0)
        """
        # 如果用户明确指定了复杂度，使用用户指定的值
        if complexity:
            complexity_mapping = {
                TaskComplexity.SIMPLE: 0.3,
                TaskComplexity.MEDIUM: 0.5,
                TaskComplexity.COMPLEX: 0.8
            }
            return complexity_mapping.get(complexity, 0.5)
        
        # 基于占位符内容自动计算复杂度
        complexity_score = 0.0
        
        # 1. 基于文本长度
        text_length = len(placeholder)
        if text_length > 200:
            complexity_score += 0.2
        elif text_length > 100:
            complexity_score += 0.1
        
        # 2. 基于关键词复杂度
        complex_keywords = [
            "复杂", "复合", "多表", "关联", "聚合", "统计", "分析", "计算",
            "复杂查询", "多维度", "时间序列", "趋势分析", "同比", "环比"
        ]
        
        placeholder_lower = placeholder.lower()
        for keyword in complex_keywords:
            if keyword in placeholder_lower:
                complexity_score += 0.1
        
        # 3. 基于SQL复杂度指标
        sql_indicators = ["JOIN", "GROUP BY", "HAVING", "子查询", "窗口函数", "CTE"]
        for indicator in sql_indicators:
            if indicator.lower() in placeholder_lower:
                complexity_score += 0.15
        
        # 4. 基于业务复杂度
        business_indicators = [
            "销售", "订单", "客户", "产品", "库存", "财务", "报表",
            "KPI", "指标", "绩效", "分析", "预测", "趋势"
        ]
        
        business_count = sum(1 for indicator in business_indicators if indicator in placeholder_lower)
        if business_count >= 3:
            complexity_score += 0.2
        elif business_count >= 2:
            complexity_score += 0.1

        # 限制在0.0-1.0范围内
        complexity_score = max(0.0, min(1.0, complexity_score))

        logger.debug(f"计算任务复杂度: placeholder={placeholder[:50]}..., complexity={complexity_score:.2f}")
        return complexity_score

    async def _get_connection_config(self, data_source_id: int) -> Optional[Dict[str, Any]]:
        """
        获取数据源的连接配置

        Args:
            data_source_id: 数据源ID

        Returns:
            Optional[Dict[str, Any]]: 连接配置，如果无法获取则返回 None
        """
        try:
            # 优先使用用户数据源服务（支持密码解密）
            user_ds_service = getattr(self.container, 'user_data_source_service', None)
            if user_ds_service:
                try:
                    # 使用当前用户ID（如果有的话）
                    user_id = getattr(self, '_current_user_id', None) or 'system'
                    data_source = await user_ds_service.get_user_data_source(user_id, str(data_source_id))
                    
                    if data_source and hasattr(data_source, 'connection_config'):
                        connection_config = dict(data_source.connection_config or {})
                        # 确保包含必要字段
                        connection_config.setdefault('id', str(data_source_id))
                        connection_config.setdefault('data_source_id', str(data_source_id))
                        
                        logger.debug(f"✅ 通过用户数据源服务获取配置成功: {data_source_id}")
                        return connection_config
                except Exception as e:
                    logger.warning(f"⚠️ 用户数据源服务获取失败: {e}")

            # 🔧 如果主要路径失败，返回 None
            # 注意：DataSourceAdapter 只有 run_query 方法，没有 get_data_source 方法
            logger.warning(f"⚠️ 无法获取数据源配置: data_source_id={data_source_id}")
            return None

        except Exception as e:
            logger.error(f"❌ 获取数据源配置失败: {e}", exc_info=True)
            return None

    async def _assess_and_select_model(
        self,
        placeholder: str,
        user_id: str,
        task_context: Optional[Dict[str, Any]],
        complexity: Optional[TaskComplexity]
    ) -> Dict[str, Any]:
        """
        使用LLM自主判断任务复杂度和模型选择
        
        Args:
            placeholder: 占位符文本
            user_id: 用户ID
            task_context: 任务上下文
            complexity: 用户指定的复杂度
            
        Returns:
            Dict[str, Any]: 模型选择结果
        """
        try:
            from .tools.model_selection import assess_and_select_model
            
            # 构建任务描述
            task_description = f"分析占位符: {placeholder}"
            
            # 构建上下文
            context = {
                "placeholder": placeholder,
                "task_context": task_context or {},
                "user_complexity": complexity.value if complexity else None
            }
            
            # 使用LLM进行评估和选择
            result = await assess_and_select_model(
                task_description=task_description,
                user_id=user_id,
                context=context,
                task_type="placeholder_analysis",
                container=self.container
            )
            
            logger.info(f"🤖 LLM自主判断完成: {result['model_decision']['selected_model']}({result['model_decision']['model_type']})")
            logger.info(f"   复杂度评分: {result['complexity_assessment']['complexity_score']:.2f}")
            logger.info(f"   推理过程: {result['model_decision']['reasoning']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ LLM自主判断失败: {e}")
            # 不再使用复杂的回退逻辑，直接使用用户配置的默认模型
            try:
                user_config = await self._get_user_model_config(user_id)
                selected_model = user_config.default_model.model_name
                model_type = user_config.default_model.model_type
                
                logger.info(f"✅ 使用用户配置的默认模型: {selected_model}")
                
                return {
                    "complexity_assessment": {
                        "complexity_score": 0.5,
                        "reasoning": "LLM评估失败，使用默认复杂度",
                        "factors": ["评估失败"],
                        "confidence": 0.3
                    },
                    "model_decision": {
                        "selected_model": selected_model,
                        "model_type": model_type,
                        "reasoning": "LLM评估失败，使用用户配置的默认模型",
                        "expected_performance": "标准性能",
                        "fallback_model": None
                    },
                    "max_context_tokens": user_config.default_model.max_tokens
                }
            except Exception as config_error:
                logger.error(f"❌ 获取用户模型配置失败: {config_error}")
                # 不再使用硬编码回退，直接抛出异常
                raise ValueError(f"无法获取用户模型配置: {config_error}")
    
    async def _get_user_model_config(self, user_id: str):
        """获取用户模型配置"""
        from .config.user_model_resolver import get_user_model_config
        return await get_user_model_config(user_id, "placeholder_analysis")


def create_agent_facade(
    container: Any,
    config: Optional[AgentConfig] = None,
    enable_context_retriever: bool = True
) -> LoomAgentFacade:
    """
    创建 Agent Facade 实例
    
    Args:
        container: 服务容器
        config: Agent 配置
        enable_context_retriever: 是否启用上下文检索器
        
    Returns:
        LoomAgentFacade 实例
    """
    return LoomAgentFacade(
        container=container,
        config=config,
        enable_context_retriever=enable_context_retriever
    )


def create_high_performance_facade(container: Any) -> LoomAgentFacade:
    """创建高性能 Facade"""
    from .config.agent import create_high_performance_agent_config
    
    return LoomAgentFacade(
        container=container,
        config=create_high_performance_agent_config(),
        enable_context_retriever=True
    )


def create_lightweight_facade(container: Any) -> LoomAgentFacade:
    """创建轻量级 Facade"""
    from .config.agent import create_lightweight_agent_config
    
    return LoomAgentFacade(
        container=container,
        config=create_lightweight_agent_config(),
        enable_context_retriever=False
    )


class StageAwareFacade(LoomAgentFacade):
    """
    阶段感知的Facade
    
    对外提供三阶段接口，内部保留TT递归能力
    这是基于TT递归的三阶段Agent架构的统一业务接口
    """
    
    def __init__(
        self,
        container: Any,
        config: Optional[AgentConfig] = None,
        enable_context_retriever: bool = True
    ):
        """
        Args:
            container: 服务容器
            config: Agent 配置
            enable_context_retriever: 是否启用上下文检索器
        """
        super().__init__(container, config, enable_context_retriever)
        
        # 创建Stage-Aware Runtime
        self._stage_aware_runtime: Optional[StageAwareRuntime] = None
        
        # 阶段结果缓存
        self.stage_results: Dict[str, Any] = {}
        
        logger.info("🎯 [StageAwareFacade] 初始化完成")
    
    async def _create_runtime(self) -> LoomAgentRuntime:
        """创建Stage-Aware运行时实例"""
        if self.enable_context_retriever:
            # 创建带上下文检索器的Stage-Aware运行时
            self._stage_aware_runtime = build_stage_aware_runtime(
                container=self.container,
                config=self.config
            )
            return self._stage_aware_runtime
        else:
            # 创建基础Stage-Aware运行时
            self._stage_aware_runtime = build_stage_aware_runtime(
                container=self.container,
                config=self.config
            )
            return self._stage_aware_runtime
    
    async def execute_sql_generation_stage(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        执行SQL生成阶段（使用TT递归）
        
        内部会自动迭代优化：
        - 发现Schema
        - 生成SQL
        - 验证SQL
        - 修复问题
        - 再次验证
        - ... 直到达到质量阈值
        
        Yields:
            AgentEvent: 包含所有TT递归步骤的事件
        """
        logger.info("🎯 [SQL生成阶段] 开始执行（TT递归模式）")
        
        # 1. 模型自主选择
        model_config = await self._assess_and_select_model(
            placeholder=placeholder,
            user_id=user_id,
            task_context=kwargs.get('task_context'),
            complexity=kwargs.get('complexity')
        )
        
        # 2. 初始化（如果需要）
        if not self._initialized:
            await self.initialize(
                user_id=user_id,
                task_type="sql_generation",
                task_complexity=model_config['complexity_assessment']['complexity_score']
            )
        
        # 🔥 优化：优先使用现有的运行时，避免重复创建
        runtime_to_use = self._stage_aware_runtime
        
        # 检查是否需要创建新的运行时
        if not runtime_to_use or self.enable_context_retriever:
            if runtime_to_use:
                logger.info("♻️ [StageAwareFacade] 使用现有运行时")
            else:
                logger.info(f"🔄 [StageAwareFacade] 创建新的运行时")

            if self.enable_context_retriever:
                logger.info(f"🔍 [StageAwareFacade] 为数据源 {data_source_id} 创建带 Schema 上下文的运行时")
                try:
                    # 设置当前用户ID以便获取正确的数据源配置
                    self._current_user_id = user_id
                    connection_config = await self._get_connection_config(data_source_id)

                    # 🔧 调试日志
                    logger.info(f"🔧 [StageAwareFacade.execute_sql_generation_stage] connection_config 获取结果: {connection_config is not None}")
                    if connection_config:
                        logger.info(f"🔧 [StageAwareFacade.execute_sql_generation_stage] connection_config keys: {list(connection_config.keys())[:5]}")

                    if connection_config:
                        # 🔥 将connection_config临时存储到container，供工具创建使用
                        setattr(self.container, '_temp_connection_config', connection_config)
                        logger.info(f"🔧 [StageAwareFacade.execute_sql_generation_stage] 已设置 container._temp_connection_config")

                        # 创建并初始化 ContextRetriever
                        context_retriever = create_schema_context_retriever(
                            data_source_id=str(data_source_id),
                            connection_config=connection_config,
                            container=self.container
                        )
                        await context_retriever.initialize()

                        # 基于当前配置创建带 ContextRetriever 的 Stage-Aware 运行时
                        logger.info(f"🔧 [StageAwareFacade.execute_sql_generation_stage] 开始创建 runtime，container._temp_connection_config 存在: {hasattr(self.container, '_temp_connection_config')}")
                        runtime_to_use = build_stage_aware_runtime(
                            container=self.container,
                            config=self.config,
                            context_retriever=context_retriever
                        )

                        # 🔥 清除临时存储
                        if hasattr(self.container, '_temp_connection_config'):
                            delattr(self.container, '_temp_connection_config')
                            logger.info(f"🔧 [StageAwareFacade.execute_sql_generation_stage] 已清除 container._temp_connection_config")

                        # 🔥 缓存运行时实例
                        self._stage_aware_runtime = runtime_to_use
                        logger.info("✅ [StageAwareFacade] Schema 上下文运行时创建成功并缓存")
                    else:
                        logger.warning(f"⚠️ [StageAwareFacade] 无法获取数据源 {data_source_id} 的连接配置，使用默认运行时")
                        runtime_to_use = await self._create_runtime()
                        self._stage_aware_runtime = runtime_to_use
                except Exception as e:
                    logger.warning(f"⚠️ [StageAwareFacade] 创建 Schema 上下文失败: {e}，使用默认运行时")
                    import traceback
                    logger.warning(traceback.format_exc())
                    # 🔥 确保清除临时存储
                    if hasattr(self.container, '_temp_connection_config'):
                        delattr(self.container, '_temp_connection_config')
                    
                    # 使用默认运行时
                    runtime_to_use = await self._create_runtime()
                    self._stage_aware_runtime = runtime_to_use

        # 确保 runtime_to_use 有效
        if not runtime_to_use:
            error_msg = "❌ [StageAwareFacade] runtime_to_use 为 None，runtime 初始化失败！"
            logger.error(error_msg)
            logger.error("   self._stage_aware_runtime: %s", self._stage_aware_runtime)
            raise RuntimeError(error_msg)

        # 执行 SQL 生成阶段
        async for event in runtime_to_use.execute_sql_generation_stage(
            placeholder=placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            **kwargs
        ):
            # 记录TT递归的每一步
            if event.event_type == 'execution_started':
                logger.info(f"🚀 [SQL阶段] 开始TT递归执行")
            elif event.event_type == 'execution_completed':
                logger.info(f"✅ [SQL阶段] TT递归执行完成")
                response_payload = event.data.get('response')
                quality_score, iterations_used = _extract_response_metrics(response_payload)
                logger.info(f"   质量评分: {quality_score:.2f}")
                logger.info(f"   迭代次数: {iterations_used}")

            yield event
        
        logger.info("✅ [SQL生成阶段] 完成（TT递归自动优化）")
    
    async def execute_chart_generation_stage(
        self,
        etl_data: Dict[str, Any],
        chart_placeholder: str,
        user_id: str,
        **kwargs
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        执行图表生成阶段（使用TT递归）
        
        内部会自动迭代优化：
        - 分析数据特征
        - 选择图表类型
        - 生成图表配置
        - 验证配置
        - 优化配置
        - ... 直到达到最优
        
        Yields:
            AgentEvent: 包含所有TT递归步骤的事件
        """
        logger.info("🎯 [图表生成阶段] 开始执行（TT递归模式）")
        
        # 1. 模型自主选择
        model_config = await self._assess_and_select_model(
            placeholder=chart_placeholder,
            user_id=user_id,
            task_context=kwargs.get('task_context'),
            complexity=kwargs.get('complexity')
        )
        
        # 2. 初始化（如果需要）
        if not self._initialized:
            await self.initialize(
                user_id=user_id,
                task_type="chart_generation",
                task_complexity=model_config['complexity_assessment']['complexity_score']
            )
        
        # 3. 使用Stage-Aware Runtime执行
        if self._stage_aware_runtime:
            async for event in self._stage_aware_runtime.execute_chart_generation_stage(
                etl_data=etl_data,
                chart_placeholder=chart_placeholder,
                user_id=user_id,
                **kwargs
            ):
                if event.event_type == 'execution_completed':
                    logger.info(f"✅ [图表阶段] TT递归执行完成")
                    response_payload = event.data.get('response')
                    quality_score, _ = _extract_response_metrics(response_payload)
                    logger.info(f"   质量评分: {quality_score:.2f}")
                
                yield event

        # 确保 runtime 有效
        if not self._stage_aware_runtime:
            error_msg = "❌ [StageAwareFacade] _stage_aware_runtime 为 None，runtime 初始化失败！"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info("✅ [图表生成阶段] 完成（TT递归自动优化）")
    
    async def execute_document_generation_stage(
        self,
        paragraph_context: str,
        placeholder_data: Dict[str, Any],
        user_id: str,
        **kwargs
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        执行文档生成阶段（使用TT递归）
        
        内部会自动迭代优化：
        - 分析段落结构
        - 生成文本
        - 检查风格
        - 验证一致性
        - 优化表达
        - ... 直到达到最优
        
        Yields:
            AgentEvent: 包含所有TT递归步骤的事件
        """
        logger.info("🎯 [文档生成阶段] 开始执行（TT递归模式）")
        
        # 1. 模型自主选择
        model_config = await self._assess_and_select_model(
            placeholder=paragraph_context,
            user_id=user_id,
            task_context=kwargs.get('task_context'),
            complexity=kwargs.get('complexity')
        )
        
        # 2. 初始化（如果需要）
        if not self._initialized:
            await self.initialize(
                user_id=user_id,
                task_type="document_generation",
                task_complexity=model_config['complexity_assessment']['complexity_score']
            )
        
        # 3. 使用Stage-Aware Runtime执行
        if self._stage_aware_runtime:
            async for event in self._stage_aware_runtime.execute_document_generation_stage(
                paragraph_context=paragraph_context,
                placeholder_data=placeholder_data,
                user_id=user_id,
                **kwargs
            ):
                if event.event_type == 'execution_completed':
                    logger.info(f"✅ [文档阶段] TT递归执行完成")
                    response_payload = event.data.get('response')
                    quality_score, _ = _extract_response_metrics(response_payload)
                    logger.info(f"   质量评分: {quality_score:.2f}")
                
                yield event

        # 确保 runtime 有效
        if not self._stage_aware_runtime:
            error_msg = "❌ [StageAwareFacade] _stage_aware_runtime 为 None，runtime 初始化失败！"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info("✅ [文档生成阶段] 完成（TT递归自动优化）")
    
    async def execute_full_pipeline(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        执行完整的三阶段Pipeline
        
        每个阶段内部都使用TT递归自动优化
        
        Yields:
            AgentEvent: 所有阶段的所有事件
        """
        logger.info("🚀 [三阶段Pipeline] 开始执行（每个阶段都使用TT递归）")
        
        # 阶段1：SQL生成（TT递归）
        sql_result = None
        async for event in self.execute_sql_generation_stage(
            placeholder=placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            **kwargs
        ):
            if event.event_type == 'execution_completed':
                sql_result = event.data.get('response')
            yield event
        
        # 阶段2：图表生成（TT递归）- 如果需要
        chart_result = None
        if sql_result and kwargs.get('need_chart', False):
            async for event in self.execute_chart_generation_stage(
                etl_data=sql_result.get('etl_data', {}),
                chart_placeholder=kwargs.get('chart_placeholder', ''),
                user_id=user_id,
                **kwargs
            ):
                if event.event_type == 'execution_completed':
                    chart_result = event.data.get('response')
                yield event
        
        # 阶段3：文档生成（TT递归）
        if sql_result:
            async for event in self.execute_document_generation_stage(
                paragraph_context=kwargs.get('paragraph_context', ''),
                placeholder_data=sql_result.get('placeholder_data', {}),
                user_id=user_id,
                **kwargs
            ):
                yield event
        
        logger.info("✅ [三阶段Pipeline] 完成")
    
    def get_current_stage(self) -> Optional[ExecutionStage]:
        """获取当前执行阶段"""
        if self._stage_aware_runtime:
            return self._stage_aware_runtime.get_current_stage()
        return None
    
    def get_stage_config(self, stage: ExecutionStage):
        """获取阶段配置"""
        if self._stage_aware_runtime:
            return self._stage_aware_runtime.get_stage_config(stage)
        return None
    
    def is_stage_configured(self, stage: ExecutionStage) -> bool:
        """检查阶段是否已配置"""
        if self._stage_aware_runtime:
            return self._stage_aware_runtime.is_stage_configured(stage)
        return False
    
    def get_stage_results(self) -> Dict[str, Any]:
        """获取阶段结果缓存"""
        return self.stage_results.copy()
    
    def clear_stage_results(self):
        """清空阶段结果缓存"""
        self.stage_results.clear()
        logger.info("🧹 [StageAwareFacade] 已清空阶段结果缓存")


def create_stage_aware_facade(
    container: Any,
    config: Optional[AgentConfig] = None,
    enable_context_retriever: bool = True
) -> StageAwareFacade:
    """
    创建 Stage-Aware Facade 实例
    
    Args:
        container: 服务容器
        config: Agent 配置
        enable_context_retriever: 是否启用上下文检索器
        
    Returns:
        StageAwareFacade 实例
    """
    return StageAwareFacade(
        container=container,
        config=config,
        enable_context_retriever=enable_context_retriever
    )


def create_high_performance_stage_aware_facade(container: Any) -> StageAwareFacade:
    """创建高性能 Stage-Aware Facade"""
    from .config.agent import create_high_performance_agent_config
    
    return StageAwareFacade(
        container=container,
        config=create_high_performance_agent_config(),
        enable_context_retriever=True
    )


def create_lightweight_stage_aware_facade(container: Any) -> StageAwareFacade:
    """创建轻量级 Stage-Aware Facade"""
    from .config.agent import create_lightweight_agent_config
    
    return StageAwareFacade(
        container=container,
        config=create_lightweight_agent_config(),
        enable_context_retriever=False
    )


# 导出
__all__ = [
    "LoomAgentFacade",
    "StageAwareFacade",
    "create_agent_facade",
    "create_stage_aware_facade",
    "create_high_performance_facade",
    "create_high_performance_stage_aware_facade",
    "create_lightweight_facade",
    "create_lightweight_stage_aware_facade",
]
