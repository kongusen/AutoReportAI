"""
生产级Agent集成服务
使用真实的数据库认证和配置提供器
"""

from typing import Dict, Any, Optional
import logging

from .facade import AgentFacade
from .auth_context import UserAuthContext, auth_manager
from .config_context import config_manager
from .production_auth_provider import production_auth_provider
from .production_config_provider import production_config_provider
from .types import AgentInput


logger = logging.getLogger(__name__)


class ProductionAgentService:
    """生产级Agent服务"""

    def __init__(self, container):
        """
        初始化生产级Agent服务

        Args:
            container: 依赖注入容器
        """
        self.container = container
        self.facade = AgentFacade(container)

        # 设置真实的provider
        self._setup_production_providers()

        self.logger = logging.getLogger(self.__class__.__name__)

    def _setup_production_providers(self):
        """设置生产级提供器"""
        # 设置认证提供器
        # 注意：这里我们不直接设置到auth_manager，而是在执行时动态获取

        # 设置配置提供器
        config_manager.set_config_loader(production_config_provider.get_user_config)

        self.logger.info("✅ 生产级提供器初始化完成")

    async def execute_with_jwt_token(
        self,
        jwt_token: str,
        agent_input: AgentInput
    ) -> Dict[str, Any]:
        """
        使用JWT令牌执行Agent任务

        Args:
            jwt_token: JWT访问令牌
            agent_input: Agent输入

        Returns:
            执行结果
        """
        # 1. JWT认证
        auth_context = production_auth_provider.get_auth_context_by_token(jwt_token)
        if not auth_context:
            return {
                "success": False,
                "error": "JWT令牌无效或已过期",
                "error_code": "AUTH_JWT_INVALID"
            }

        return await self._execute_with_auth_context(agent_input, auth_context)

    async def execute_with_session(
        self,
        session_id: str,
        agent_input: AgentInput
    ) -> Dict[str, Any]:
        """
        使用会话ID执行Agent任务

        Args:
            session_id: 会话ID
            agent_input: Agent输入

        Returns:
            执行结果
        """
        # 1. 会话认证
        auth_context = production_auth_provider.get_auth_context_by_session(session_id)
        if not auth_context:
            return {
                "success": False,
                "error": "无效的会话ID",
                "error_code": "AUTH_SESSION_INVALID"
            }

        return await self._execute_with_auth_context(agent_input, auth_context)

    async def execute_for_user(
        self,
        user_id: str,
        agent_input: AgentInput
    ) -> Dict[str, Any]:
        """
        为指定用户执行Agent任务（内部调用）

        Args:
            user_id: 用户UUID
            agent_input: Agent输入

        Returns:
            执行结果
        """
        # 获取用户认证上下文
        auth_context = production_auth_provider.get_auth_context_by_user_id(user_id)
        if not auth_context:
            return {
                "success": False,
                "error": f"用户 {user_id} 不存在或不活跃",
                "error_code": "USER_NOT_FOUND"
            }

        return await self._execute_with_auth_context(agent_input, auth_context)

    async def _execute_with_auth_context(
        self,
        agent_input: AgentInput,
        auth_context: UserAuthContext
    ) -> Dict[str, Any]:
        """
        使用认证上下文执行Agent任务

        Args:
            agent_input: Agent输入
            auth_context: 用户认证上下文

        Returns:
            执行结果
        """
        try:
            # 2. 权限检查
            if not auth_context.has_permission("agent.use"):
                return {
                    "success": False,
                    "error": "用户无Agent使用权限",
                    "error_code": "PERMISSION_DENIED",
                    "user_id": auth_context.user_id
                }

            # 3. 检查SQL执行权限（如果需要）
            if (agent_input.constraints and
                agent_input.constraints.output_kind == "sql" and
                not auth_context.has_permission("sql.execute")):
                return {
                    "success": False,
                    "error": "用户无SQL执行权限",
                    "error_code": "SQL_PERMISSION_DENIED",
                    "user_id": auth_context.user_id
                }

            # 4. 获取用户配置
            user_config = production_config_provider.get_agent_config(auth_context.user_id)

            # 5. 检查使用配额（如果配置了限制）
            quota_check = self._check_usage_quota(auth_context.user_id, user_config)
            if not quota_check["allowed"]:
                return {
                    "success": False,
                    "error": f"已超出使用配额: {quota_check['reason']}",
                    "error_code": "QUOTA_EXCEEDED",
                    "user_id": auth_context.user_id,
                    "quota_info": quota_check
                }

            # 6. 执行Agent任务
            start_time = __import__('time').time()

            result = await self.facade.execute_with_auth(agent_input, auth_context)

            execution_time = int((__import__('time').time() - start_time) * 1000)

            # 7. 记录使用量（异步）
            self._record_usage(auth_context.user_id, result, execution_time)

            return {
                "success": result.success,
                "result": result.result,
                "metadata": result.metadata,
                "user_id": auth_context.user_id,
                "execution_time_ms": execution_time,
                "user_config_applied": True
            }

        except Exception as e:
            self.logger.error(f"Agent执行失败 (用户: {auth_context.user_id}): {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "EXECUTION_FAILED",
                "user_id": auth_context.user_id
            }

    def _check_usage_quota(self, user_id: str, config) -> Dict[str, Any]:
        """
        检查用户使用配额

        Args:
            user_id: 用户ID
            config: 用户配置

        Returns:
            配额检查结果
        """
        try:
            # 这里可以实现具体的配额检查逻辑
            # 例如检查每日Token使用量、月度成本等

            # 简单示例：检查用户是否活跃
            from app.crud.crud_user import crud_user
            from app.db.session import SessionLocal

            db = SessionLocal()
            try:
                user = crud_user.get(db, id=user_id)
                if not user or not user.is_active:
                    return {
                        "allowed": False,
                        "reason": "用户账户不活跃",
                        "quota_type": "account_status"
                    }
            finally:
                db.close()

            return {
                "allowed": True,
                "reason": "配额检查通过",
                "remaining_quota": "unlimited"  # 可以添加具体的剩余配额信息
            }

        except Exception as e:
            self.logger.warning(f"配额检查失败 (user_id: {user_id}): {e}")
            # 配额检查失败时允许执行，但记录警告
            return {
                "allowed": True,
                "reason": "配额检查失败，允许执行",
                "warning": str(e)
            }

    def _record_usage(self, user_id: str, result, execution_time_ms: int):
        """
        记录用户使用量（异步执行）

        Args:
            user_id: 用户ID
            result: 执行结果
            execution_time_ms: 执行时间（毫秒）
        """
        try:
            # 这里可以实现使用量记录逻辑
            # 例如：更新数据库中的使用统计、发送监控指标等

            self.logger.info(
                f"用户使用记录 - "
                f"user_id: {user_id}, "
                f"success: {result.success}, "
                f"execution_time: {execution_time_ms}ms"
            )

            # 可以在这里添加：
            # - 更新用户LLM使用量配额
            # - 发送监控指标
            # - 记录审计日志

        except Exception as e:
            self.logger.error(f"记录使用量失败 (user_id: {user_id}): {e}")

    async def health_check(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        系统健康检查

        Args:
            user_id: 可选的用户ID，用于检查用户特定配置

        Returns:
            健康状态信息
        """
        try:
            # 基础健康检查
            facade_health = await self.facade.health_check()

            # 认证提供器检查
            auth_status = "healthy"
            config_status = "healthy"

            if user_id:
                # 检查用户认证
                auth_context = production_auth_provider.get_auth_context_by_user_id(user_id)
                auth_status = "healthy" if auth_context else "user_not_found"

                # 检查用户配置
                try:
                    user_config = production_config_provider.get_user_config(user_id)
                    config_status = "healthy" if user_config else "config_not_found"
                except Exception:
                    config_status = "config_error"

            return {
                "status": "healthy",
                "facade": facade_health,
                "auth_provider": auth_status,
                "config_provider": config_status,
                "production_mode": True,
                "user_id": user_id
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "production_mode": True,
                "user_id": user_id
            }