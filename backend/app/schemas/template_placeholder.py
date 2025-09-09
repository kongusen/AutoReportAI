"""
Template Placeholder Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Base schemas
class TemplatePlaceholderBase(BaseModel):
    """模板占位符基础Schema"""
    placeholder_name: str = Field(..., min_length=1, max_length=255)
    placeholder_text: str = Field(..., min_length=1, max_length=500)
    placeholder_type: str = Field(..., min_length=1, max_length=50)
    content_type: str = Field(..., min_length=1, max_length=50)
    
    # Agent分析结果
    agent_analyzed: bool = False
    target_database: Optional[str] = Field(None, max_length=100)
    target_table: Optional[str] = Field(None, max_length=100)
    required_fields: Optional[Dict[str, Any]] = None
    generated_sql: Optional[str] = None
    sql_validated: bool = False
    
    # 执行配置
    execution_order: int = Field(default=1, ge=1)
    cache_ttl_hours: int = Field(default=24, ge=1, le=24*30)  # 最多30天
    is_required: bool = True
    is_active: bool = True
    
    # Agent配置 (已简化，不再需要复杂配置)
    agent_workflow_id: Optional[str] = Field(None, max_length=100)
    # agent_config 字段已移除，现在使用统一的分析流程
    
    # 元数据
    description: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)


class TemplatePlaceholderCreate(TemplatePlaceholderBase):
    """创建模板占位符Schema"""
    template_id: str = Field(..., description="模板ID")
    content_hash: Optional[str] = Field(None, max_length=16, description="内容哈希，用于去重")
    
    # 解析元数据
    original_type: Optional[str] = None
    extracted_description: Optional[str] = None
    parsing_metadata: Optional[Dict[str, Any]] = None


class TemplatePlaceholderUpdate(BaseModel):
    """更新模板占位符Schema"""
    placeholder_name: Optional[str] = Field(None, min_length=1, max_length=255)
    placeholder_type: Optional[str] = Field(None, min_length=1, max_length=50)
    content_type: Optional[str] = Field(None, min_length=1, max_length=50)
    
    # Agent分析结果
    agent_analyzed: Optional[bool] = None
    target_database: Optional[str] = Field(None, max_length=100)
    target_table: Optional[str] = Field(None, max_length=100)
    required_fields: Optional[Dict[str, Any]] = None
    generated_sql: Optional[str] = None
    sql_validated: Optional[bool] = None
    analysis: Optional[str] = None
    
    # 执行配置
    execution_order: Optional[int] = Field(None, ge=1)
    cache_ttl_hours: Optional[int] = Field(None, ge=1, le=24*30)
    is_required: Optional[bool] = None
    is_active: Optional[bool] = None
    
    # Agent配置 (已简化，不再需要复杂配置)
    agent_workflow_id: Optional[str] = Field(None, max_length=100)
    # agent_config 字段已移除，现在使用统一的分析流程
    
    # 元数据
    description: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class TemplatePlaceholderInDBBase(TemplatePlaceholderBase):
    """数据库模板占位符基础Schema"""
    id: str
    template_id: str
    content_hash: Optional[str] = None
    
    # 解析元数据
    original_type: Optional[str] = None
    extracted_description: Optional[str] = None
    parsing_metadata: Optional[Dict[str, Any]] = None
    
    # 时间戳
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    analyzed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TemplatePlaceholder(TemplatePlaceholderInDBBase):
    """返回给客户端的模板占位符Schema"""
    pass


class TemplatePlaceholderDisplay(BaseModel):
    """占位符卡片显示Schema - 优化前端显示"""
    id: str
    placeholder_name: str = Field(..., description="占位符名称")
    placeholder_text: str = Field(..., description="占位符文本")
    placeholder_type: str = Field(..., description="占位符类型")
    
    # 核心配置
    execution_order: int = Field(default=1, description="执行顺序")
    cache_ttl_hours: int = Field(default=24, description="缓存时间(小时)")
    is_required: bool = Field(default=True, description="是否必需")
    is_active: bool = Field(default=True, description="是否启用")
    
    # 分析结果
    generated_sql: Optional[str] = Field(None, description="生成的SQL")
    analysis: Optional[str] = Field(None, description="分析结果")
    agent_analyzed: bool = Field(default=False, description="是否已分析")
    sql_validated: bool = Field(default=False, description="SQL是否验证")
    confidence_score: float = Field(default=0.0, description="置信度")
    
    # 数据库信息
    target_database: Optional[str] = Field(None, description="目标数据库")
    target_table: Optional[str] = Field(None, description="目标表")
    
    # 时间信息
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    analyzed_at: Optional[datetime] = None
    
    # 显示状态
    status: str = Field(default="pending", description="状态: pending/analyzed/tested/error")
    last_test_result: Optional[Dict[str, Any]] = Field(None, description="最后测试结果")
    
    class Config:
        from_attributes = True


class TemplatePlaceholderInDB(TemplatePlaceholderInDBBase):
    """存储在数据库中的模板占位符Schema"""
    pass


# 分析相关schemas
class PlaceholderAnalysisRequest(BaseModel):
    """占位符分析请求Schema"""
    data_source_id: str = Field(..., description="数据源ID")
    force_reanalyze: bool = Field(default=False, description="是否强制重新分析")
    target_placeholders: Optional[List[str]] = Field(None, description="指定要分析的占位符ID列表")


class PlaceholderAnalysisResult(BaseModel):
    """占位符分析结果Schema"""
    placeholder_id: str
    success: bool
    target_database: Optional[str] = None
    target_table: Optional[str] = None
    generated_sql: Optional[str] = None
    confidence_score: float = 0.0
    error_message: Optional[str] = None
    analysis_metadata: Optional[Dict[str, Any]] = None


class BatchAnalysisResult(BaseModel):
    """批量分析结果Schema"""
    total_placeholders: int
    analyzed_placeholders: int
    failed_placeholders: int
    results: List[PlaceholderAnalysisResult]
    analysis_duration_ms: int
    success: bool
    error_message: Optional[str] = None


# 统计相关schemas
class PlaceholderAnalytics(BaseModel):
    """占位符分析统计Schema"""
    total_placeholders: int
    analyzed_placeholders: int
    sql_validated_placeholders: int
    average_confidence_score: float
    cache_hit_rate: float
    analysis_coverage: float  # 分析覆盖率百分比
    
    # 执行统计
    execution_stats: Dict[str, Any] = Field(
        default_factory=lambda: {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time_ms": 0
        }
    )


# API response schemas
class PlaceholderParseResponse(BaseModel):
    """占位符解析响应Schema"""
    success: bool
    action: str  # parsed, reparsed, skipped
    total_parsed: Optional[int] = None
    newly_stored: Optional[int] = None
    total_stored: Optional[int] = None
    placeholders: Optional[List[TemplatePlaceholder]] = None
    message: str
    error: Optional[str] = None
    placeholders_count: int = 0


class PlaceholderListResponse(BaseModel):
    """占位符列表响应Schema"""
    placeholders: List[TemplatePlaceholder]
    analytics: Optional[PlaceholderAnalytics] = None