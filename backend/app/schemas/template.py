from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TemplateBase(BaseModel):
    """模板基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, max_length=500, description="模板描述")
    template_type: str = Field(default="docx", description="模板类型")
    content: str = Field(..., description="模板内容")
    placeholders: List[Dict[str, Any]] = Field(default_factory=list, description="占位符定义")
    sections: List[Dict[str, Any]] = Field(default_factory=list, description="模板段落")
    is_public: bool = Field(default=False, description="是否公开模板")


class TemplateCreate(TemplateBase):
    """创建模板"""
    pass


class TemplateUpdate(BaseModel):
    """更新模板"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    placeholders: Optional[List[Dict[str, Any]]] = None
    sections: Optional[List[Dict[str, Any]]] = None
    is_public: Optional[bool] = None


class TemplateInDB(TemplateBase):
    """数据库中的模板"""
    id: str
    user_id: int
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    original_filename: Optional[str] = None
    version: str = "1.0"
    parent_id: Optional[str] = None
    is_active: bool = True
    
    class Config:
        from_attributes = True


class Template(TemplateInDB):
    """模板响应模型"""
    pass


class TemplateUpload(BaseModel):
    """模板上传模型"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_public: bool = Field(default=False)
