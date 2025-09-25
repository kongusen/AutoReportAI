"""
Agent系统集成示例
展示如何将Agent系统与现有的认证和配置系统集成
"""

from typing import Dict, Any, Optional
import asyncio
import logging

from .facade import AgentFacade
from .auth_context import UserAuthContext, auth_manager
from .config_context import AgentSystemConfig, config_manager
from .types import AgentInput, PlaceholderSpec, SchemaInfo, TaskContext, AgentConstraints


class UserAuthProvider:
    """示例：用户认证提供器"""

    def __init__(self):
        # 模拟用户数据库
        self._users = {
            "4d404820-a26a-45c4-bcdb-e2233590b17e": {
                "username": "admin_user",
                "roles": ["admin", "analyst"],
                "permissions": ["sql_execute", "data_access", "agent_use"],
                "tenant_id": "tenant_001",
                "organization_id": "org_001"
            },
            "user-123": {
                "username": "regular_user",
                "roles": ["user"],
                "permissions": ["agent_use"],
                "tenant_id": "tenant_001",
                "organization_id": "org_001"
            }
        }

    def get_auth_context_by_token(self, token: str) -> Optional[UserAuthContext]:
        """根据token获取认证上下文（模拟JWT解析）"""
        # 这里应该是JWT解析逻辑
        # 为示例目的，我们假设token就是user_id
        user_id = token
        user_data = self._users.get(user_id)

        if not user_data:
            return None

        return UserAuthContext(
            user_id=user_id,
            username=user_data["username"],
            roles=user_data["roles"],
            permissions=user_data["permissions"],
            tenant_id=user_data["tenant_id"],
            organization_id=user_data["organization_id"]
        )

    def get_auth_context_by_user_id(self, user_id: str) -> Optional[UserAuthContext]:
        """根据用户ID获取认证上下文"""
        return self.get_auth_context_by_token(user_id)


class ConfigProvider:
    """示例：配置提供器"""

    def __init__(self):
        # 模拟配置数据库
        self._user_configs = {
            "4d404820-a26a-45c4-bcdb-e2233590b17e": {
                "default_model": "gpt-4o-mini",
                "max_retries": 5,
                "timeout_seconds": 180,
                "enable_sql_validation": True,
                "enable_policy_check": True,
                "max_result_rows": 50000,
                "debug_mode": True
            },
            "user-123": {
                "default_model": "gpt-3.5-turbo",
                "max_retries": 3,
                "timeout_seconds": 60,
                "enable_sql_validation": True,
                "enable_policy_check": False,
                "max_result_rows": 1000,
                "debug_mode": False
            }
        }

    def get_user_config(self, user_id: str) -> Dict[str, Any]:
        """获取用户特定配置"""
        return self._user_configs.get(user_id, {})


class IntegratedAgentService:
    """集成的Agent服务示例"""

    def __init__(self, container):
        self.container = container
        self.facade = AgentFacade(container)
        self.auth_provider = UserAuthProvider()
        self.config_provider = ConfigProvider()

        # 配置认证和配置系统
        self._setup_integrations()

    def _setup_integrations(self):
        """设置集成"""
        # 配置动态配置加载器
        config_manager.set_config_loader(self.config_provider.get_user_config)

    async def execute_with_session(
        self,
        session_token: str,
        agent_input: AgentInput
    ) -> Dict[str, Any]:
        """
        使用会话令牌执行Agent任务

        Args:
            session_token: 会话令牌（JWT、session_id等）
            agent_input: Agent输入

        Returns:
            执行结果
        """
        # 1. 认证
        auth_context = self.auth_provider.get_auth_context_by_token(session_token)
        if not auth_context:
            return {
                "success": False,
                "error": "无效的会话令牌",
                "error_code": "AUTH_FAILED"
            }

        # 2. 权限检查
        if not auth_context.has_permission("agent_use"):
            return {
                "success": False,
                "error": "用户无Agent使用权限",
                "error_code": "PERMISSION_DENIED"
            }

        try:
            # 3. 执行Agent任务
            result = await self.facade.execute_with_auth(agent_input, auth_context)

            return {
                "success": result.success,
                "result": result.result,
                "metadata": result.metadata,
                "user_id": auth_context.user_id,
                "execution_time": result.metadata.get("execution_time") if result.metadata else None
            }

        except Exception as e:
            logging.error(f"Agent执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "EXECUTION_FAILED"
            }

    async def execute_for_user(
        self,
        user_id: str,
        agent_input: AgentInput
    ) -> Dict[str, Any]:
        """
        为指定用户执行Agent任务

        Args:
            user_id: 用户ID
            agent_input: Agent输入

        Returns:
            执行结果
        """
        # 获取用户认证上下文
        auth_context = self.auth_provider.get_auth_context_by_user_id(user_id)
        if not auth_context:
            return {
                "success": False,
                "error": f"用户 {user_id} 不存在",
                "error_code": "USER_NOT_FOUND"
            }

        # 确保AgentInput包含user_id
        if not agent_input.user_id:
            from dataclasses import replace
            agent_input = replace(agent_input, user_id=user_id)

        try:
            result = await self.facade.execute_with_auth(agent_input, auth_context)

            return {
                "success": result.success,
                "result": result.result,
                "metadata": result.metadata,
                "user_id": user_id
            }

        except Exception as e:
            logging.error(f"Agent执行失败 (用户: {user_id}): {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "EXECUTION_FAILED",
                "user_id": user_id
            }


# 使用示例
async def example_usage():
    """集成使用示例"""
    from ....core.container import Container

    # 创建服务
    container = Container()
    agent_service = IntegratedAgentService(container)

    # 创建测试输入
    agent_input = AgentInput(
        user_prompt="查询所有用户的姓名和邮箱",
        placeholder=PlaceholderSpec(
            id="test_query",
            description="查询用户信息",
            type="stat"
        ),
        schema=SchemaInfo(
            tables=["users"],
            columns={"users": ["name", "email", "created_at"]}
        ),
        context=TaskContext(),
        constraints=AgentConstraints(sql_only=True, output_kind="sql")
    )

    # 方式1: 使用会话令牌
    print("=== 使用会话令牌执行 ===")
    result1 = await agent_service.execute_with_session(
        session_token="4d404820-a26a-45c4-bcdb-e2233590b17e",  # 模拟token
        agent_input=agent_input
    )
    print(f"结果: {result1}")

    # 方式2: 直接指定用户ID
    print("\n=== 直接指定用户ID执行 ===")
    result2 = await agent_service.execute_for_user(
        user_id="user-123",
        agent_input=agent_input
    )
    print(f"结果: {result2}")


if __name__ == "__main__":
    asyncio.run(example_usage())