"""
优化的模板模型
统一模板管理，支持多种模板类型
"""

import enum
from sqlalchemy import Boolean, Column, Enum, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from app.db.base_class_optimized import UserOwnedModel


class TemplateType(str, enum.Enum):
    """模板类型枚举"""
    REPORT = "report"          # 报告模板
    CHART = "chart"            # 图表模板
    DASHBOARD = "dashboard"    # 仪表盘模板
    EMAIL = "email"            # 邮件模板
    EXPORT = "export"          # 导出模板


class TemplateStatus(str, enum.Enum):
    """模板状态枚举"""
    DRAFT = "draft"            # 草稿
    ACTIVE = "active"          # 激活
    ARCHIVED = "archived"      # 归档
    DEPRECATED = "deprecated"  # 已弃用


class TemplateCategory(str, enum.Enum):
    """模板分类枚举"""
    FINANCIAL = "financial"    # 财务类
    SALES = "sales"           # 销售类
    MARKETING = "marketing"   # 营销类
    OPERATIONS = "operations" # 运营类
    HR = "hr"                 # 人力资源类
    CUSTOM = "custom"         # 自定义类


class Template(UserOwnedModel):
    """模板模型"""
    
    __tablename__ = "templates"
    
    # 基本信息
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    template_type = Column(Enum(TemplateType), nullable=False, index=True)
    category = Column(Enum(TemplateCategory), default=TemplateCategory.CUSTOM, nullable=False)
    
    # 模板内容
    content = Column(Text, nullable=False)  # 模板内容（支持占位符）
    schema_config = Column(JSON, nullable=True)  # 模板架构配置
    
    # 状态管理
    status = Column(Enum(TemplateStatus), default=TemplateStatus.DRAFT, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)  # 是否公开
    is_featured = Column(Boolean, default=False, nullable=False)  # 是否推荐
    
    # 使用统计
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(String, nullable=True)
    
    # 验证和质量
    is_validated = Column(Boolean, default=False, nullable=False)
    validation_errors = Column(JSON, nullable=True)  # 验证错误信息
    quality_score = Column(Integer, default=0, nullable=False)  # 质量评分 0-100
    
    # 占位符管理
    placeholders = Column(JSON, nullable=True)  # 占位符定义
    placeholder_mappings = Column(JSON, nullable=True)  # 占位符映射关系
    
    # 扩展配置
    tags = Column(JSON, nullable=True)  # 标签
    extra_metadata = Column(JSON, nullable=True)  # 扩展元数据
    render_options = Column(JSON, nullable=True)  # 渲染选项
    
    # 关联关系
    reports = relationship("Report", back_populates="template")
    
    @property
    def is_ready_for_use(self) -> bool:
        """模板是否可用"""
        return (
            self.status == TemplateStatus.ACTIVE and 
            self.is_validated and 
            not self.is_deleted
        )
    
    @property
    def placeholder_count(self) -> int:
        """占位符数量"""
        if not self.placeholders:
            return 0
        return len(self.placeholders)
    
    @property
    def complexity_level(self) -> str:
        """复杂度等级"""
        count = self.placeholder_count
        if count <= 3:
            return "simple"
        elif count <= 8:
            return "medium"
        else:
            return "complex"
    
    def get_placeholders_by_type(self, placeholder_type: str = None) -> list:
        """根据类型获取占位符"""
        if not self.placeholders:
            return []
        
        if not placeholder_type:
            return self.placeholders
        
        return [
            p for p in self.placeholders 
            if p.get('type') == placeholder_type
        ]
    
    def increment_usage(self):
        """增加使用次数"""
        self.usage_count += 1
        from datetime import datetime
        self.last_used_at = datetime.utcnow().isoformat()
    
    def validate_template(self) -> dict:
        """验证模板"""
        errors = []
        warnings = []
        
        # 检查基本信息
        if not self.name or len(self.name.strip()) < 3:
            errors.append("模板名称不能少于3个字符")
        
        if not self.content or len(self.content.strip()) < 10:
            errors.append("模板内容不能少于10个字符")
        
        # 检查占位符
        if self.placeholders:
            for i, placeholder in enumerate(self.placeholders):
                if not placeholder.get('name'):
                    errors.append(f"占位符 #{i+1} 缺少名称")
                if not placeholder.get('type'):
                    errors.append(f"占位符 #{i+1} 缺少类型")
        
        # 更新验证状态
        self.validation_errors = errors if errors else None
        self.is_validated = len(errors) == 0
        
        # 计算质量评分
        score = 100
        score -= len(errors) * 20  # 每个错误扣20分
        score -= len(warnings) * 5  # 每个警告扣5分
        
        # 额外评分因素
        if self.description and len(self.description) > 50:
            score += 5
        if self.placeholder_count > 0:
            score += 5
        if self.tags and len(self.tags) > 0:
            score += 3
        
        self.quality_score = max(0, min(100, score))
        
        return {
            "is_valid": self.is_validated,
            "errors": errors,
            "warnings": warnings,
            "quality_score": self.quality_score
        }
    
    def to_summary_dict(self) -> dict:
        """转换为摘要字典"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "template_type": self.template_type.value,
            "category": self.category.value,
            "status": self.status.value,
            "is_public": self.is_public,
            "is_featured": self.is_featured,
            "usage_count": self.usage_count,
            "quality_score": self.quality_score,
            "placeholder_count": self.placeholder_count,
            "complexity_level": self.complexity_level,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at,
            "tags": self.tags or []
        }