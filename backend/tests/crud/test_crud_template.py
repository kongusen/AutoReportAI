"""
模板CRUD操作测试
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.crud_template import crud_template
from app.schemas.template import TemplateCreate, TemplateUpdate
from app.models.user import User
from app.models.template import Template


@pytest.mark.unit
@pytest.mark.database
@pytest.mark.crud
class TestTemplateCRUD:
    """测试模板CRUD操作"""
    
    async def test_create_template(self, db_session: AsyncSession, test_user: User):
        """测试创建模板"""
        template_data = TemplateCreate(
            name="CRUD Test Template",
            description="Created via CRUD",
            content="Hello {{name}}",
            template_type="report",
            variables={"name": "string"}
        )
        
        template = await crud_template.create_with_owner(
            db_session, obj_in=template_data, owner_id=test_user.id
        )
        
        assert template.id is not None
        assert template.name == "CRUD Test Template"
        assert template.description == "Created via CRUD"
        assert template.content == "Hello {{name}}"
        assert template.template_type == "report"
        assert template.owner_id == test_user.id
        assert template.variables == {"name": "string"}
    
    async def test_get_template_by_id(self, db_session: AsyncSession, test_template: Template):
        """测试根据ID获取模板"""
        template = await crud_template.get(db_session, id=test_template.id)
        
        assert template is not None
        assert template.id == test_template.id
        assert template.name == test_template.name
    
    async def test_get_nonexistent_template(self, db_session: AsyncSession):
        """测试获取不存在的模板"""
        template = await crud_template.get(db_session, id=99999)
        assert template is None
    
    async def test_get_templates_by_owner(self, db_session: AsyncSession, test_user: User):
        """测试根据所有者获取模板列表"""
        # 创建多个模板
        template_names = ["Template 1", "Template 2", "Template 3"]
        created_templates = []
        
        for name in template_names:
            template_data = TemplateCreate(
                name=name,
                content=f"Content for {name}",
                template_type="report"
            )
            template = await crud_template.create_with_owner(
                db_session, obj_in=template_data, owner_id=test_user.id
            )
            created_templates.append(template)
        
        # 获取用户的所有模板
        user_templates = await crud_template.get_multi_by_owner(
            db_session, owner_id=test_user.id
        )
        
        assert len(user_templates) >= 3
        template_names_found = [t.name for t in user_templates]
        for name in template_names:
            assert name in template_names_found
    
    async def test_update_template(self, db_session: AsyncSession, test_template: Template):
        """测试更新模板"""
        update_data = TemplateUpdate(
            name="Updated Template Name",
            description="Updated description",
            content="Updated content {{new_var}}",
            variables={"new_var": "string"}
        )
        
        updated_template = await crud_template.update(
            db_session, db_obj=test_template, obj_in=update_data
        )
        
        assert updated_template.name == "Updated Template Name"
        assert updated_template.description == "Updated description"
        assert updated_template.content == "Updated content {{new_var}}"
        assert updated_template.variables == {"new_var": "string"}
        assert updated_template.updated_at > test_template.updated_at
    
    async def test_partial_update_template(self, db_session: AsyncSession, test_template: Template):
        """测试部分更新模板"""
        original_content = test_template.content
        
        update_data = TemplateUpdate(name="Partially Updated Template")
        
        updated_template = await crud_template.update(
            db_session, db_obj=test_template, obj_in=update_data
        )
        
        assert updated_template.name == "Partially Updated Template"
        assert updated_template.content == original_content  # 未更新的字段保持不变
    
    async def test_delete_template(self, db_session: AsyncSession, test_template: Template):
        """测试删除模板"""
        template_id = test_template.id
        
        # 删除模板
        deleted_template = await crud_template.remove(db_session, id=template_id)
        
        assert deleted_template.id == template_id
        
        # 验证模板已被删除
        template = await crud_template.get(db_session, id=template_id)
        assert template is None
    
    async def test_get_templates_with_pagination(self, db_session: AsyncSession, test_user: User):
        """测试分页获取模板"""
        # 创建多个模板
        for i in range(15):  # 创建15个模板
            template_data = TemplateCreate(
                name=f"Pagination Template {i}",
                content=f"Content {i}",
                template_type="report"
            )
            await crud_template.create_with_owner(
                db_session, obj_in=template_data, owner_id=test_user.id
            )
        
        # 测试第一页
        page1 = await crud_template.get_multi(db_session, skip=0, limit=10)
        assert len(page1) == 10
        
        # 测试第二页
        page2 = await crud_template.get_multi(db_session, skip=10, limit=10)
        assert len(page2) >= 5  # 至少5个（加上之前可能存在的）
        
        # 验证不重复
        page1_ids = {t.id for t in page1}
        page2_ids = {t.id for t in page2}
        assert len(page1_ids.intersection(page2_ids)) == 0
    
    async def test_search_templates_by_name(self, db_session: AsyncSession, test_user: User):
        """测试按名称搜索模板"""
        # 创建搜索测试数据
        search_templates = [
            ("Python Data Analysis", "report"),
            ("Sales Python Report", "report"), 
            ("Email Marketing", "email"),
            ("Dashboard Overview", "dashboard")
        ]
        
        for name, template_type in search_templates:
            template_data = TemplateCreate(
                name=name,
                content="Test content",
                template_type=template_type
            )
            await crud_template.create_with_owner(
                db_session, obj_in=template_data, owner_id=test_user.id
            )
        
        # 搜索包含"Python"的模板
        python_templates = await crud_template.search_by_name(
            db_session, search_term="Python"
        )
        
        assert len(python_templates) == 2
        python_names = [t.name for t in python_templates]
        assert "Python Data Analysis" in python_names
        assert "Sales Python Report" in python_names
    
    async def test_get_templates_by_type(self, db_session: AsyncSession, test_user: User):
        """测试按类型获取模板"""
        # 创建不同类型的模板
        template_types = ["report", "email", "dashboard", "report"]  # report重复以测试多个
        
        for i, template_type in enumerate(template_types):
            template_data = TemplateCreate(
                name=f"Type Test Template {i}",
                content="Test content",
                template_type=template_type
            )
            await crud_template.create_with_owner(
                db_session, obj_in=template_data, owner_id=test_user.id
            )
        
        # 获取report类型的模板
        report_templates = await crud_template.get_by_type(
            db_session, template_type="report"
        )
        
        assert len(report_templates) >= 2
        for template in report_templates:
            assert template.template_type == "report"
    
    async def test_template_exists(self, db_session: AsyncSession, test_template: Template):
        """测试模板存在性检查"""
        # 测试存在的模板
        exists = await crud_template.exists(db_session, id=test_template.id)
        assert exists is True
        
        # 测试不存在的模板
        exists = await crud_template.exists(db_session, id=99999)
        assert exists is False
    
    async def test_bulk_delete_templates(self, db_session: AsyncSession, test_user: User):
        """测试批量删除模板"""
        # 创建多个模板
        template_ids = []
        for i in range(5):
            template_data = TemplateCreate(
                name=f"Bulk Delete Template {i}",
                content="To be deleted",
                template_type="report"
            )
            template = await crud_template.create_with_owner(
                db_session, obj_in=template_data, owner_id=test_user.id
            )
            template_ids.append(template.id)
        
        # 批量删除
        deleted_count = await crud_template.bulk_delete(db_session, ids=template_ids)
        assert deleted_count == 5
        
        # 验证删除
        for template_id in template_ids:
            template = await crud_template.get(db_session, id=template_id)
            assert template is None