"""
占位符图表缓存模型 - 存储图表生成的两阶段结果
"""

from sqlalchemy import Column, String, Text, DateTime, Integer, Float, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from datetime import datetime
import uuid

from app.db.base_class import Base


class PlaceholderChartCache(Base):
    """占位符图表缓存表 - 存储两阶段图表生成结果"""
    
    __tablename__ = "placeholder_chart_cache"
    
    # 主键
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # 关联字段
    placeholder_id = Column(UUID(as_uuid=True), ForeignKey("template_placeholders.id"), nullable=False, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"), nullable=False, index=True)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 阶段一：SQL和数据
    generated_sql = Column(Text, nullable=False)  # 生成的SQL查询
    sql_metadata = Column(JSON)  # SQL元数据（质量分数、业务逻辑等）
    raw_data = Column(JSON)  # 原始查询数据
    processed_data = Column(JSON)  # 处理后的图表数据
    data_quality_score = Column(Float, default=0.0)  # 数据质量分数
    
    # 阶段二：图表配置
    chart_type = Column(String(50), nullable=False)  # 图表类型
    echarts_config = Column(JSON, nullable=False)  # ECharts配置
    chart_metadata = Column(JSON)  # 图表元数据
    
    # 执行信息
    execution_mode = Column(String(20), default='test_with_chart')  # sql_only | test_with_chart | full_pipeline
    execution_time_ms = Column(Integer, default=0)  # 总执行时间（毫秒）
    sql_execution_time_ms = Column(Integer, default=0)  # SQL执行时间
    chart_generation_time_ms = Column(Integer, default=0)  # 图表生成时间
    
    # 状态标志
    is_valid = Column(Boolean, default=True)  # 缓存是否有效
    is_preview = Column(Boolean, default=True)  # 是否为预览模式
    stage_completed = Column(String(20), default='chart_complete')  # 完成阶段
    
    # 缓存管理
    cache_key = Column(String(255), unique=True, index=True)  # 缓存键（基于内容hash）
    cache_ttl_hours = Column(Integer, default=24)  # 缓存TTL（小时）
    hit_count = Column(Integer, default=0)  # 命中次数
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)  # 过期时间
    last_accessed_at = Column(DateTime)  # 最后访问时间
    
    # 关系
    placeholder = relationship("TemplatePlaceholder", back_populates="chart_cache")
    template = relationship("Template")
    data_source = relationship("DataSource")
    user = relationship("User")
    
    def __repr__(self):
        return f"<PlaceholderChartCache(id={self.id}, chart_type={self.chart_type}, stage={self.stage_completed})>"
    
    @property
    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_chart_ready(self) -> bool:
        """检查图表是否就绪"""
        return (self.stage_completed == 'chart_complete' and 
                self.echarts_config is not None and 
                self.chart_type is not None)
    
    @property
    def is_sql_ready(self) -> bool:
        """检查SQL是否就绪"""
        return self.generated_sql is not None and self.generated_sql.strip() != ''
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'id': str(self.id),
            'placeholder_id': str(self.placeholder_id),
            'template_id': str(self.template_id),
            'data_source_id': str(self.data_source_id),
            
            # 阶段一数据
            'generated_sql': self.generated_sql,
            'sql_metadata': self.sql_metadata,
            'raw_data': self.raw_data,
            'processed_data': self.processed_data,
            'data_quality_score': self.data_quality_score,
            
            # 阶段二数据
            'chart_type': self.chart_type,
            'echarts_config': self.echarts_config,
            'chart_metadata': self.chart_metadata,
            
            # 执行信息
            'execution_mode': self.execution_mode,
            'execution_time_ms': self.execution_time_ms,
            'sql_execution_time_ms': self.sql_execution_time_ms,
            'chart_generation_time_ms': self.chart_generation_time_ms,
            
            # 状态
            'is_valid': self.is_valid,
            'is_preview': self.is_preview,
            'is_chart_ready': self.is_chart_ready,
            'is_sql_ready': self.is_sql_ready,
            'stage_completed': self.stage_completed,
            
            # 时间戳
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_accessed_at': self.last_accessed_at.isoformat() if self.last_accessed_at else None
        }
    
    def update_hit_count(self):
        """更新命中次数和最后访问时间"""
        self.hit_count += 1
        self.last_accessed_at = datetime.utcnow()
    
    def invalidate(self):
        """使缓存失效"""
        self.is_valid = False
        self.updated_at = datetime.utcnow()
    
    def extend_ttl(self, hours: int = None):
        """延长缓存TTL"""
        if hours:
            self.cache_ttl_hours = hours
        
        if self.cache_ttl_hours > 0:
            from datetime import timedelta
            self.expires_at = datetime.utcnow() + timedelta(hours=self.cache_ttl_hours)
            self.updated_at = datetime.utcnow()