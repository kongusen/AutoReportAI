"""
Agent系统统一门面
提供简洁的Agent执行入口，封装内部复杂性
支持动态认证和配置集成
"""

from typing import Dict, Any, Optional, Callable
from .types import AgentInput, AgentOutput
from .orchestrator import UnifiedOrchestrator
from .auth_context import auth_manager, UserAuthContext
from .config_context import config_manager, AgentSystemConfig


class AgentFacade:
    """Agent系统的统一入口门面"""

    def __init__(self, container) -> None:
        """
        初始化Agent门面

        Args:
            container: 依赖注入容器 (备份系统的服务容器)
        """
        self.container = container
        self.orchestrator = UnifiedOrchestrator(container)

    def configure_auth(
        self,
        auth_context: Optional[UserAuthContext] = None,
        auth_provider: Optional[Callable[[str], UserAuthContext]] = None
    ) -> None:
        """
        配置认证系统

        Args:
            auth_context: 直接设置的认证上下文
            auth_provider: 认证提供器函数，接受token返回认证上下文
        """
        if auth_context:
            auth_manager.set_context(auth_context)

        # 可以在此处扩展设置auth_provider的逻辑

    def configure_system(
        self,
        config: Optional[AgentSystemConfig] = None,
        config_loader: Optional[Callable[[str], Dict[str, Any]]] = None
    ) -> None:
        """
        配置系统设置

        Args:
            config: 直接设置的系统配置
            config_loader: 配置加载器函数，接受user_id返回配置字典
        """
        if config:
            config_manager.set_config(config)

        if config_loader:
            config_manager.set_config_loader(config_loader)

    async def execute(self, ai: AgentInput, mode: str = "ptof") -> AgentOutput:
        """
        执行Agent任务的统一入口

        Args:
            ai: 标准化的Agent输入
            mode: 执行模式
                - "ptof": 传统Plan-Tool-Observe-Finalize一次性流程（默认）
                - "ptav": Plan-Tool-Active-Validate单步骤循环流程
                - "task_sql_validation": Task任务中SQL有效性验证和更新
                - "report_chart_generation": 报告生成中数据转图表流程

        Returns:
            AgentOutput: 标准化的Agent输出
        """
        # 如果AI输入没有指定user_id，尝试从认证上下文获取
        if not ai.user_id:
            current_user_id = auth_manager.get_current_user_id()
            if current_user_id:
                # 创建新的AgentInput实例，设置user_id
                ai = self._clone_agent_input_with_user_id(ai, current_user_id)

        return await self.orchestrator.execute(ai, mode=mode)

    async def execute_task_validation(self, ai: AgentInput) -> AgentOutput:
        """
        任务验证专用方法: SQL验证模式 + PTAV回退机制

        完整工作流:
        1. 任务触发 -> 检查是否存在SQL？
        2. [有SQL] -> SQL验证模式 (Schema检查 -> 语法验证 -> 时间属性验证 -> 快速修正)
        3. [无SQL/验证失败] -> PTAV回退模式 -> 从零生成新SQL
        4. 实现自动化运维: 维护存量任务健康 + 自动初始化新任务

        Args:
            ai: Agent输入，应包含任务上下文

        Returns:
            AgentOutput: 验证结果或新生成的SQL
        """
        from typing import Optional
        import logging

        logger = logging.getLogger(f"{self.__class__.__name__}.task_validation")

        # 提取当前SQL（如果存在）
        current_sql = self._extract_current_sql_from_context(ai)

        if current_sql:
            logger.info(f"🔍 [任务验证] 发现现有SQL，启动验证模式: {current_sql[:100]}...")

            # 阶段1: SQL验证模式 - 检查现有SQL健康状态
            validation_result = await self.execute(ai, mode="task_sql_validation")

            if validation_result.success:
                logger.info(f"✅ [任务验证] SQL验证通过，任务健康")
                return validation_result

            else:
                # 安全获取错误信息
                error_info = "未知错误"
                try:
                    if isinstance(validation_result.metadata, dict):
                        error_info = validation_result.metadata.get('error', '未知错误')
                    else:
                        error_info = str(validation_result.metadata) if validation_result.metadata else '未知错误'
                except Exception:
                    error_info = '元数据访问异常'

                logger.warning(f"⚠️ [任务验证] SQL验证失败: {error_info}")

                # 检查是否是可修复的问题
                if self._is_repairable_sql_issue(validation_result):
                    logger.info(f"🔧 [任务验证] 问题可修复，继续使用验证模式")
                    return validation_result
                else:
                    logger.info(f"🔄 [任务验证] SQL不可修复，启动PTAV回退生成新SQL")
                    # 进入PTAV回退模式
                    return await self._execute_ptav_fallback(ai, reason="sql_validation_failed")

        else:
            logger.info(f"📝 [任务验证] 未发现现有SQL，启动PTAV回退生成新SQL")
            # 阶段2: PTAV回退模式 - 从零生成新SQL
            return await self._execute_ptav_fallback(ai, reason="missing_sql")

    async def _execute_ptav_fallback(self, ai: AgentInput, reason: str) -> AgentOutput:
        """PTAV回退模式执行"""
        import logging

        logger = logging.getLogger(f"{self.__class__.__name__}.ptav_fallback")
        logger.info(f"🔄 [PTAV回退] 开始回退生成，原因: {reason}")

        # 使用PTAV循环模式重新生成SQL
        result = await self.execute(ai, mode="ptav")

        if result.success:
            logger.info(f"✅ [PTAV回退] 成功生成新SQL")
            # 在结果中标记这是通过回退生成的
            try:
                if isinstance(result.metadata, dict):
                    result.metadata["fallback_reason"] = reason
                    result.metadata["generation_method"] = "ptav_fallback"
                elif hasattr(result, 'metadata'):
                    # 如果metadata不是字典，创建一个新的字典
                    result.metadata = {
                        "fallback_reason": reason,
                        "generation_method": "ptav_fallback",
                        "original_metadata": result.metadata
                    }
            except Exception as e:
                logger.warning(f"设置回退标记时出错: {e}")
        else:
            logger.error(f"❌ [PTAV回退] 回退生成失败")

        return result

    def _extract_current_sql_from_context(self, ai: AgentInput) -> Optional[str]:
        """从AgentInput中提取当前SQL"""
        # 尝试多种方式获取当前SQL
        try:
            # 方式1: 直接从属性获取
            if hasattr(ai, 'current_sql') and ai.current_sql:
                return ai.current_sql.strip()

            # 方式2: 从context中获取
            if hasattr(ai, 'context') and ai.context:
                if hasattr(ai.context, 'current_sql') and ai.context.current_sql:
                    return ai.context.current_sql.strip()

            # 方式3: 从task_driven_context中获取
            if hasattr(ai, 'task_driven_context') and ai.task_driven_context:
                task_context = ai.task_driven_context
                if isinstance(task_context, dict):
                    if task_context.get('current_sql'):
                        return task_context['current_sql'].strip()
                    if task_context.get('existing_sql'):
                        return task_context['existing_sql'].strip()

            # 方式4: 从data_source中获取
            if hasattr(ai, 'data_source') and ai.data_source:
                if isinstance(ai.data_source, dict) and ai.data_source.get('sql_to_test'):
                    return ai.data_source['sql_to_test'].strip()

        except Exception as e:
            import logging
            logging.getLogger(f"{self.__class__.__name__}").warning(f"提取SQL时出错: {e}")

        return None

    def _is_repairable_sql_issue(self, validation_result: AgentOutput) -> bool:
        """判断SQL问题是否可修复"""
        try:
            # 安全检查metadata类型
            if not validation_result.metadata:
                return False

            if not isinstance(validation_result.metadata, dict):
                # 如果metadata不是字典，尝试检查结果字符串中的关键词
                metadata_str = str(validation_result.metadata).lower()
                return any(pattern in metadata_str for pattern in ['syntax', '语法', 'table', '表名'])

            # 如果有corrected_sql，说明问题已经修复
            if validation_result.metadata.get('corrected_sql'):
                return True

            # 检查错误类型
            error = validation_result.metadata.get('error', '')
            issues = validation_result.metadata.get('issues', [])

            # 可修复的问题类型
            repairable_patterns = [
                'syntax', '语法', 'schema_mismatch', '表名', '列名',
                'time', '时间', 'date', '日期', 'column', 'table',
                'update', 'UPDATE'  # 添加UPDATE关键词相关的修复
            ]

            # 如果错误消息中包含可修复的关键词
            error_text = str(error).lower()
            issues_text = ' '.join(str(issue).lower() for issue in issues)
            combined_text = f"{error_text} {issues_text}"

            return any(pattern in combined_text for pattern in repairable_patterns)

        except Exception as e:
            # 如果检查过程出错，保守地返回True，让系统尝试修复
            import logging
            logging.getLogger(f"{self.__class__.__name__}").warning(f"检查可修复性时出错: {e}")
            return True

    def _clone_agent_input_with_user_id(self, ai: AgentInput, user_id: str) -> AgentInput:
        """克隆AgentInput并设置user_id"""
        from dataclasses import replace
        return replace(ai, user_id=user_id)

    async def execute_with_auth(
        self,
        ai: AgentInput,
        auth_context: UserAuthContext,
        mode: str = "ptof"
    ) -> AgentOutput:
        """
        使用指定认证上下文执行Agent任务

        Args:
            ai: 标准化的Agent输入
            auth_context: 用户认证上下文
            mode: 执行模式（同execute方法）

        Returns:
            AgentOutput: 标准化的Agent输出
        """
        # 临时设置认证上下文
        original_context = auth_manager.get_context()
        try:
            auth_manager.set_context(auth_context)

            # 确保AgentInput有user_id
            if not ai.user_id:
                ai = self._clone_agent_input_with_user_id(ai, auth_context.user_id)

            return await self.execute(ai, mode=mode)
        finally:
            # 恢复原认证上下文
            if original_context:
                auth_manager.set_context(original_context)
            else:
                auth_manager.clear_context()

    async def health_check(self) -> Dict[str, Any]:
        """
        Agent系统健康检查

        Returns:
            Dict: 健康状态信息
        """
        try:
            # 检查核心组件状态
            orchestrator_ok = self.orchestrator is not None
            executor_ok = self.orchestrator.executor is not None
            tools_count = len(self.orchestrator.executor.registry._tools)

            return {
                "status": "healthy",
                "architecture": "PTOF",
                "orchestrator_ok": orchestrator_ok,
                "executor_ok": executor_ok,
                "tools_registered": tools_count,
                "version": "2.0-simplified"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }