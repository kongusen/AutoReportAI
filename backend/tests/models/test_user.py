"""
用户模型测试
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


@pytest.mark.unit
@pytest.mark.database
class TestUserModel:
    """测试用户模型"""
    
    async def test_user_creation(self, db_session: AsyncSession):
        """测试用户创建"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "hashed_password_123"
        }
        
        user = User(**user_data)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_admin is False
        assert user.created_at is not None
    
    async def test_user_unique_constraints(self, db_session: AsyncSession):
        """测试用户唯一性约束"""
        # 创建第一个用户
        user1 = User(
            username="testuser",
            email="test@example.com",
            hashed_password="password1"
        )
        db_session.add(user1)
        await db_session.commit()
        
        # 尝试创建相同用户名的用户
        user2 = User(
            username="testuser",  # 重复用户名
            email="different@example.com",
            hashed_password="password2"
        )
        db_session.add(user2)
        
        with pytest.raises(Exception):  # 应该违反唯一性约束
            await db_session.commit()
    
    async def test_user_email_unique_constraint(self, db_session: AsyncSession):
        """测试邮箱唯一性约束"""
        # 创建第一个用户
        user1 = User(
            username="user1",
            email="test@example.com",
            hashed_password="password1"
        )
        db_session.add(user1)
        await db_session.commit()
        
        # 尝试创建相同邮箱的用户
        user2 = User(
            username="user2",
            email="test@example.com",  # 重复邮箱
            hashed_password="password2"
        )
        db_session.add(user2)
        
        with pytest.raises(Exception):  # 应该违反唯一性约束
            await db_session.commit()
    
    async def test_user_admin_default_false(self, db_session: AsyncSession):
        """测试用户默认不是管理员"""
        user = User(
            username="normaluser",
            email="normal@example.com",
            hashed_password="password"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.is_admin is False
    
    async def test_user_active_default_true(self, db_session: AsyncSession):
        """测试用户默认激活"""
        user = User(
            username="activeuser",
            email="active@example.com",
            hashed_password="password"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.is_active is True
    
    async def test_user_string_representation(self, db_session: AsyncSession):
        """测试用户字符串表示"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="password"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        user_str = str(user)
        assert "testuser" in user_str or "test@example.com" in user_str


@pytest.mark.unit
class TestUserSchemas:
    """测试用户Pydantic schemas"""
    
    def test_user_create_schema(self):
        """测试用户创建schema"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com", 
            "password": "testpassword123"
        }
        
        user_create = UserCreate(**user_data)
        assert user_create.username == "testuser"
        assert user_create.email == "test@example.com"
        assert user_create.password == "testpassword123"
    
    def test_user_create_schema_validation(self):
        """测试用户创建schema验证"""
        # 测试无效邮箱
        with pytest.raises(ValueError):
            UserCreate(
                username="testuser",
                email="invalid_email",
                password="password123"
            )
        
        # 测试过短密码
        with pytest.raises(ValueError):
            UserCreate(
                username="testuser", 
                email="test@example.com",
                password="123"  # 太短
            )
    
    def test_user_update_schema(self):
        """测试用户更新schema"""
        update_data = {
            "email": "newemail@example.com",
            "is_active": False
        }
        
        user_update = UserUpdate(**update_data)
        assert user_update.email == "newemail@example.com"
        assert user_update.is_active is False
        assert user_update.username is None  # 可选字段
    
    def test_user_update_partial(self):
        """测试用户部分更新"""
        # 只更新邮箱
        user_update = UserUpdate(email="updated@example.com")
        assert user_update.email == "updated@example.com"
        assert user_update.username is None
        assert user_update.is_active is None


@pytest.mark.integration
@pytest.mark.database
class TestUserModelIntegration:
    """测试用户模型与数据库集成"""
    
    async def test_user_crud_workflow(self, db_session: AsyncSession):
        """测试用户CRUD完整工作流"""
        # Create
        user = User(
            username="cruduser",
            email="crud@example.com",
            hashed_password="hashed_password"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        created_id = user.id
        assert created_id is not None
        
        # Read
        from sqlalchemy import select
        result = await db_session.execute(select(User).where(User.id == created_id))
        found_user = result.scalar_one_or_none()
        assert found_user is not None
        assert found_user.username == "cruduser"
        
        # Update
        found_user.email = "updated@example.com"
        await db_session.commit()
        await db_session.refresh(found_user)
        assert found_user.email == "updated@example.com"
        
        # Delete
        await db_session.delete(found_user)
        await db_session.commit()
        
        result = await db_session.execute(select(User).where(User.id == created_id))
        deleted_user = result.scalar_one_or_none()
        assert deleted_user is None
    
    async def test_user_relationship_cascade(self, db_session: AsyncSession, test_user: User):
        """测试用户关联数据级联删除"""
        # 这个测试可能需要根据实际的关联关系来调整
        user_id = test_user.id
        
        # 创建与用户关联的数据（模板、任务等）
        from app.models.template import Template
        template = Template(
            name="User Template",
            content="Test content",
            template_type="report",
            owner_id=user_id
        )
        db_session.add(template)
        await db_session.commit()
        
        # 删除用户应该级联删除关联数据或设置为null
        await db_session.delete(test_user)
        await db_session.commit()
        
        # 验证模板的owner_id被正确处理
        from sqlalchemy import select
        result = await db_session.execute(select(Template).where(Template.id == template.id))
        remaining_template = result.scalar_one_or_none()
        
        # 根据级联策略，模板可能被删除或owner_id被设为null
        if remaining_template:
            assert remaining_template.owner_id is None