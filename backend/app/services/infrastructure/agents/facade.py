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

    async def execute(self, ai: AgentInput) -> AgentOutput:
        """
        执行Agent任务的统一入口

        Args:
            ai: 标准化的Agent输入

        Returns:
            AgentOutput: 标准化的Agent输出
        """
        # 如果AI输入没有指定user_id，尝试从认证上下文获取
        if not ai.user_id:
            current_user_id = auth_manager.get_current_user_id()
            if current_user_id:
                # 创建新的AgentInput实例，设置user_id
                ai = self._clone_agent_input_with_user_id(ai, current_user_id)

        return await self.orchestrator.execute(ai)

    def _clone_agent_input_with_user_id(self, ai: AgentInput, user_id: str) -> AgentInput:
        """克隆AgentInput并设置user_id"""
        from dataclasses import replace
        return replace(ai, user_id=user_id)

    async def execute_with_auth(
        self,
        ai: AgentInput,
        auth_context: UserAuthContext
    ) -> AgentOutput:
        """
        使用指定认证上下文执行Agent任务

        Args:
            ai: 标准化的Agent输入
            auth_context: 用户认证上下文

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

            return await self.execute(ai)
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