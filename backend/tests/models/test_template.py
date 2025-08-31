"""
模板模型测试
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.template import Template
from app.models.user import User


@pytest.mark.unit
@pytest.mark.database
class TestTemplateModel:
    """测试模板模型"""
    
    async def test_template_creation(self, db_session: AsyncSession, test_user: User):
        """测试模板创建"""
        template_data = {
            "name": "Test Template",
            "description": "A test template",
            "content": "Hello {{name}}",
            "template_type": "report",
            "variables": {"name": "string"},
            "owner_id": test_user.id
        }
        
        template = Template(**template_data)
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)
        
        assert template.id is not None
        assert template.name == "Test Template"
        assert template.content == "Hello {{name}}"
        assert template.template_type == "report"
        assert template.variables == {"name": "string"}
        assert template.owner_id == test_user.id
        assert template.created_at is not None
        assert template.updated_at is not None
    
    async def test_template_variables_json_field(self, db_session: AsyncSession, test_user: User):
        """测试模板变量JSON字段"""
        complex_variables = {
            "user_name": "string",
            "age": "number",
            "is_active": "boolean",
            "tags": "array",
            "profile": {
                "type": "object",
                "properties": {
                    "bio": "string",
                    "avatar": "string"
                }
            }
        }
        
        template = Template(
            name="Complex Template",
            content="Complex content",
            template_type="report",
            variables=complex_variables,
            owner_id=test_user.id
        )
        
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)
        
        assert template.variables == complex_variables
        assert template.variables["profile"]["properties"]["bio"] == "string"
    
    async def test_template_type_enum(self, db_session: AsyncSession, test_user: User):
        """测试模板类型枚举"""
        valid_types = ["docx", "report", "email", "dashboard", "export"]
        
        for template_type in valid_types:
            template = Template(
                name=f"Template {template_type}",
                content="Test content",
                template_type=template_type,
                owner_id=test_user.id
            )
            
            db_session.add(template)
            await db_session.commit()
            await db_session.refresh(template)
            
            assert template.template_type == template_type
            
            # 清理
            await db_session.delete(template)
            await db_session.commit()
    
    async def test_template_content_length(self, db_session: AsyncSession, test_user: User):
        """测试模板内容长度"""
        # 测试长内容
        long_content = "A" * 10000  # 10k字符
        
        template = Template(
            name="Long Template",
            content=long_content,
            template_type="report",
            owner_id=test_user.id
        )
        
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)
        
        assert len(template.content) == 10000
        assert template.content == long_content
    
    async def test_template_owner_relationship(self, db_session: AsyncSession, test_user: User):
        """测试模板与用户的关系"""
        template = Template(
            name="Relationship Template",
            content="Test content",
            template_type="report",
            owner_id=test_user.id
        )
        
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)
        
        # 加载关联的用户
        await db_session.refresh(template, ["owner"])
        assert template.owner is not None
        assert template.owner.id == test_user.id
        assert template.owner.username == test_user.username
    
    async def test_template_timestamps(self, db_session: AsyncSession, test_user: User):
        """测试模板时间戳"""
        import time
        
        template = Template(
            name="Timestamp Template",
            content="Test content",
            template_type="report",
            owner_id=test_user.id
        )
        
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)
        
        created_at = template.created_at
        updated_at = template.updated_at
        
        assert created_at is not None
        assert updated_at is not None
        assert created_at == updated_at  # 初始时相等
        
        # 等待一小段时间后更新
        time.sleep(0.1)
        template.name = "Updated Template"
        await db_session.commit()
        await db_session.refresh(template)
        
        assert template.updated_at > created_at  # 更新时间应该更新
        assert template.created_at == created_at  # 创建时间不变
    
    async def test_template_file_fields(self, db_session: AsyncSession, test_user: User):
        """测试模板文件相关字段"""
        template = Template(
            name="File Template",
            content="Test content",
            template_type="docx",
            owner_id=test_user.id,
            file_path="/path/to/template.docx",
            file_size=1024,
            file_hash="abcd1234"
        )
        
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)
        
        assert template.file_path == "/path/to/template.docx"
        assert template.file_size == 1024
        assert template.file_hash == "abcd1234"
    
    async def test_template_variables_default(self, db_session: AsyncSession, test_user: User):
        """测试模板变量默认值"""
        template = Template(
            name="Default Variables Template",
            content="No variables",
            template_type="report", 
            owner_id=test_user.id
            # 不设置variables
        )
        
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)
        
        # variables应该有默认值或为空
        assert template.variables is not None or template.variables == {}


@pytest.mark.integration
@pytest.mark.database
class TestTemplateIntegration:
    """测试模板集成功能"""
    
    async def test_template_with_placeholders(self, db_session: AsyncSession, test_user: User):
        """测试模板与占位符的关系"""
        # 创建带占位符的模板
        template = Template(
            name="Placeholder Template",
            content="Hello {{user.name}}, your score is {{data.score}}",
            template_type="report",
            variables={
                "user.name": "string",
                "data.score": "number"
            },
            owner_id=test_user.id
        )
        
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)
        
        # 创建关联的占位符
        from app.models.template_placeholder import TemplatePlaceholder
        placeholder = TemplatePlaceholder(
            template_id=template.id,
            placeholder_key="user.name",
            placeholder_type="simple",
            data_source_table="users",
            data_source_column="name"
        )
        
        db_session.add(placeholder)
        await db_session.commit()
        
        # 验证关系
        await db_session.refresh(template, ["placeholders"])
        assert len(template.placeholders) == 1
        assert template.placeholders[0].placeholder_key == "user.name"
    
    async def test_template_soft_delete(self, db_session: AsyncSession, test_user: User):
        """测试模板软删除（如果实现了）"""
        template = Template(
            name="Delete Template",
            content="To be deleted",
            template_type="report",
            owner_id=test_user.id
        )
        
        db_session.add(template)
        await db_session.commit()
        template_id = template.id
        
        # 如果实现了软删除，测试相应逻辑
        # 这里假设有is_deleted字段
        if hasattr(template, 'is_deleted'):
            template.is_deleted = True
            await db_session.commit()
            
            # 验证软删除
            from sqlalchemy import select
            result = await db_session.execute(
                select(Template).where(Template.id == template_id)
            )
            found_template = result.scalar_one_or_none()
            assert found_template.is_deleted is True
    
    async def test_template_search_functionality(self, db_session: AsyncSession, test_user: User):
        """测试模板搜索功能"""
        # 创建多个模板用于搜索测试
        templates_data = [
            ("Python Report", "Python programming report template"),
            ("Sales Dashboard", "Sales performance dashboard"),
            ("Email Template", "Customer email template"),
        ]
        
        created_templates = []
        for name, description in templates_data:
            template = Template(
                name=name,
                description=description,
                content="Content for " + name,
                template_type="report",
                owner_id=test_user.id
            )
            db_session.add(template)
            created_templates.append(template)
        
        await db_session.commit()
        
        # 测试按名称搜索
        from sqlalchemy import select
        result = await db_session.execute(
            select(Template).where(Template.name.ilike("%Python%"))
        )
        python_templates = result.scalars().all()
        assert len(python_templates) == 1
        assert python_templates[0].name == "Python Report"
        
        # 测试按描述搜索  
        result = await db_session.execute(
            select(Template).where(Template.description.ilike("%dashboard%"))
        )
        dashboard_templates = result.scalars().all()
        assert len(dashboard_templates) == 1
        assert dashboard_templates[0].name == "Sales Dashboard"