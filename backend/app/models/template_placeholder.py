"""
Template Placeholder Models

模板占位符相关数据模型，支持Agent分析的SQL持久化和数据缓存
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.base_class import Base


class TemplatePlaceholder(Base):
    """模板占位符配置表"""
    __tablename__ = "template_placeholders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id", ondelete="CASCADE"), nullable=False)
    
    # 占位符基本信息
    placeholder_name = Column(String(255), nullable=False)
    placeholder_text = Column(String(500), nullable=False)  # {{统计:总数}}
    placeholder_type = Column(String(50), nullable=False)   # statistic, analysis, chart, table
    content_type = Column(String(50), nullable=False)       # text, table, chart, image
    
    # Agent分析结果存储
    agent_analyzed = Column(Boolean, default=False)         # 是否已被Agent分析
    target_database = Column(String(100))                   # 目标数据库名
    target_table = Column(String(100))                      # 目标数据表名
    required_fields = Column(JSON)                          # 需要的字段列表
    generated_sql = Column(Text)                            # Agent生成的SQL
    sql_validated = Column(Boolean, default=False)          # SQL是否已验证
    
    # 执行配置
    execution_order = Column(Integer, default=1)
    cache_ttl_hours = Column(Integer, default=24)
    is_required = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    # Agent配置
    agent_workflow_id = Column(String(100))
    agent_config = Column(JSON, default=dict)
    
    # 元数据
    description = Column(Text)
    confidence_score = Column(Float, default=0.0)           # Agent分析的置信度
    content_hash = Column(String(16), index=True)           # 内容哈希，用于去重
    
    # 解析元数据
    original_type = Column(String(50))                      # 原始解析类型
    extracted_description = Column(Text)                    # 提取的描述
    parsing_metadata = Column(JSON, default=dict)          # 解析元数据
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    analyzed_at = Column(DateTime(timezone=True))           # Agent分析时间
    
    # 关系
    template = relationship("Template", back_populates="placeholders")
    chart_cache = relationship("PlaceholderChartCache", back_populates="placeholder", cascade="all, delete-orphan")
    placeholder_values = relationship("PlaceholderValue", back_populates="placeholder", cascade="all, delete-orphan")
    
    class Config:
        from_attributes = True


class PlaceholderValue(Base):
    """占位符值存储表 - 存储每次执行的结果"""
    __tablename__ = "placeholder_values"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    placeholder_id = Column(UUID(as_uuid=True), ForeignKey("template_placeholders.id", ondelete="CASCADE"), nullable=False)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False)
    
    # 执行结果
    raw_query_result = Column(JSON)                         # 原始查询结果
    processed_value = Column(JSON)                          # 处理后的结构化数据
    formatted_text = Column(Text)                           # 最终显示文本
    
    # 执行元数据
    execution_sql = Column(Text)                            # 实际执行的SQL
    execution_time_ms = Column(Integer)                     # 执行耗时
    row_count = Column(Integer, default=0)                  # 返回行数
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    source = Column(String(50), default="agent")            # 数据来源：agent, rule, cache
    confidence_score = Column(Float, default=0.0)           # 置信度分数
    analysis_metadata = Column(JSON, default=dict)          # 分析元数据
    
    # 时间相关字段 - 支持基于时间的动态SQL和历史数据管理
    execution_time = Column(DateTime(timezone=True))        # 任务执行时间（来自execution_context）
    report_period = Column(String(20))                      # 报告周期：daily/weekly/monthly/yearly
    period_start = Column(DateTime(timezone=True))          # 报告周期开始时间
    period_end = Column(DateTime(timezone=True))            # 报告周期结束时间
    
    # SQL参数快照 - 记录执行时使用的动态参数
    sql_parameters_snapshot = Column(JSON)                  # SQL参数快照，便于历史追溯
    
    # 版本控制和历史管理
    execution_batch_id = Column(String(100))               # 批次ID，同一次任务执行的所有占位符共享
    version_hash = Column(String(64))                       # 基于SQL+参数+时间的版本哈希
    is_latest_version = Column(Boolean, default=True)       # 是否为最新版本
    
    # 缓存管理
    cache_key = Column(String(255), unique=True)            # 缓存键
    expires_at = Column(DateTime(timezone=True))
    hit_count = Column(Integer, default=0)
    last_hit_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    placeholder = relationship("TemplatePlaceholder", back_populates="placeholder_values")
    data_source = relationship("DataSource")
    
    class Config:
        from_attributes = True


class TemplateExecutionHistory(Base):
    """模板执行历史表"""
    __tablename__ = "template_execution_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"), nullable=False)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # 执行信息
    execution_type = Column(String(50), nullable=False)     # manual, scheduled, api
    status = Column(String(50), nullable=False)             # analyzing, running, completed, failed
    
    # 阶段标记
    analysis_completed = Column(Boolean, default=False)     # Agent分析完成
    sql_validation_completed = Column(Boolean, default=False)  # SQL验证完成
    data_extraction_completed = Column(Boolean, default=False) # 数据提取完成
    report_generation_completed = Column(Boolean, default=False) # 报告生成完成
    
    # 性能指标
    total_duration_ms = Column(Integer)
    analysis_duration_ms = Column(Integer)
    extraction_duration_ms = Column(Integer)
    generation_duration_ms = Column(Integer)
    
    # 结果信息
    placeholders_analyzed = Column(Integer, default=0)
    placeholders_extracted = Column(Integer, default=0)
    cache_hit_rate = Column(Float, default=0.0)
    output_file_path = Column(String(500))
    output_file_size = Column(Integer)
    
    # 错误信息
    error_details = Column(JSON)
    failed_placeholders = Column(JSON)
    
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    
    class Config:
        from_attributes = True