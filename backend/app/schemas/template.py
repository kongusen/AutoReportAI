from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_serializer


class TemplateBase(BaseModel):
    """模板基础模型"""

    name: str = Field(..., min_length=1, max_length=255, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    template_type: str = Field(default="docx", description="模板类型")
    content: Optional[str] = Field(None, description="模板内容")
    original_filename: Optional[str] = Field(
        None, max_length=255, description="原始文件名"
    )
    file_path: Optional[str] = Field(None, max_length=500, description="文件存储路径")
    file_size: Optional[int] = Field(None, description="文件大小")
    is_public: bool = Field(default=False, description="是否公开模板")
    is_active: bool = Field(default=True, description="是否激活")


class TemplateCreate(TemplateBase):
    """创建模板"""

    pass


class TemplateUpdate(BaseModel):
    """更新模板"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    content: Optional[str] = None
    template_type: Optional[str] = None
    original_filename: Optional[str] = Field(None, max_length=255)
    file_path: Optional[str] = Field(None, max_length=500)
    file_size: Optional[int] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None


class Template(TemplateBase):
    """模板响应模型"""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    @computed_field
    @property
    def unique_id(self) -> str:
        return str(self.id)

    @field_serializer('created_at')
    def serialize_created_at(self, value: datetime) -> str:
        return value.isoformat() if value else None

    @field_serializer('updated_at')
    def serialize_updated_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    class Config:
        from_attributes = True


class TemplateUpload(BaseModel):
    """模板上传模型"""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    is_public: bool = Field(default=False)


class TemplatePreview(BaseModel):
    """模板预览模型"""
    
    template_id: UUID
    content: Optional[str] = Field(None, description="模板内容预览")
    html_content: Optional[str] = Field(None, description="HTML格式内容")
    placeholders: Optional[list] = Field(default=[], description="占位符列表")
    metadata: Optional[dict] = Field(default={}, description="模板元数据")
    
    class Config:
        from_attributes = True
