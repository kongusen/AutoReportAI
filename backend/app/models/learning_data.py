"""
学习数据模型

用于存储错误日志、用户反馈和学习规则的数据模型
"""

import enum

from sqlalchemy import (
    DECIMAL,
    JSON,
    Boolean,
    Column,
    DateTime,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from ..db.base_class import Base


class ErrorCategoryEnum(enum.Enum):
    """错误分类枚举"""

    PARSING_ERROR = "parsing_error"
    LLM_ERROR = "llm_error"
    FIELD_MATCHING_ERROR = "field_matching_error"
    ETL_ERROR = "etl_error"
    CONTENT_GENERATION_ERROR = "content_generation_error"
    VALIDATION_ERROR = "validation_error"
    SYSTEM_ERROR = "system_error"


class ErrorSeverityEnum(enum.Enum):
    """错误严重程度枚举"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FeedbackTypeEnum(enum.Enum):
    """反馈类型枚举"""

    CORRECTION = "correction"
    IMPROVEMENT = "improvement"
    VALIDATION = "validation"
    COMPLAINT = "complaint"


class PlaceholderProcessingHistory(Base):
    """占位符处理历史表"""

    __tablename__ = "placeholder_processing_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"), nullable=True)
    placeholder_text = Column(String(500), nullable=False)
    placeholder_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    context_info = Column(JSON, nullable=True)
    llm_understanding = Column(JSON, nullable=True)
    field_mapping = Column(JSON, nullable=True)
    processed_value = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    confidence_score = Column(DECIMAL(3, 2), nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    template = relationship("Template", back_populates="processing_history")
    user = relationship("User", back_populates="processing_history")


class ErrorLog(Base):
    """错误日志表"""

    __tablename__ = "error_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    error_id = Column(String(32), unique=True, nullable=False, index=True)
    category = Column(SQLEnum(ErrorCategoryEnum), nullable=False)
    severity = Column(SQLEnum(ErrorSeverityEnum), nullable=False)
    message = Column(Text, nullable=False)
    placeholder_text = Column(String(500), nullable=True)
    placeholder_type = Column(String(50), nullable=True)
    placeholder_description = Column(Text, nullable=True)
    context_before = Column(Text, nullable=True)
    context_after = Column(Text, nullable=True)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id = Column(String(255), nullable=True)
    stack_trace = Column(Text, nullable=True)
    additional_data = Column(JSON, nullable=True)
    resolved = Column(Boolean, default=False, nullable=False)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # 关系
    data_source = relationship("DataSource", back_populates="error_logs")
    user = relationship("User", back_populates="error_logs")
    feedbacks = relationship("UserFeedback", back_populates="error_log")


class UserFeedback(Base):
    """用户反馈表"""

    __tablename__ = "user_feedbacks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(String(32), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    error_id = Column(String(32), ForeignKey("error_logs.error_id"), nullable=True)
    feedback_type = Column(SQLEnum(FeedbackTypeEnum), nullable=False)
    placeholder_text = Column(String(500), nullable=False)
    original_result = Column(Text, nullable=False)
    corrected_result = Column(Text, nullable=True)
    suggested_field = Column(String(255), nullable=True)
    confidence_rating = Column(Integer, nullable=True)  # 1-5分
    comments = Column(Text, nullable=True)
    processed = Column(Boolean, default=False, nullable=False)
    processing_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # 关系
    user = relationship("User", back_populates="feedbacks")
    error_log = relationship("ErrorLog", back_populates="feedbacks")


class LearningRule(Base):
    """学习规则表"""

    __tablename__ = "learning_rules"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(32), unique=True, nullable=False, index=True)
    placeholder_pattern = Column(String(500), nullable=False)
    field_mapping = Column(String(255), nullable=False)
    confidence_score = Column(DECIMAL(3, 2), nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    success_rate = Column(DECIMAL(3, 2), nullable=False, default=0.0)
    created_from_feedback = Column(Boolean, default=False, nullable=False)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False)
    rule_metadata = Column(JSON, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 关系
    data_source = relationship("DataSource", back_populates="learning_rules")


class KnowledgeBase(Base):
    """知识库表"""

    __tablename__ = "knowledge_base"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(String(32), unique=True, nullable=False, index=True)
    placeholder_signature = Column(String(255), nullable=False, index=True)
    successful_mappings = Column(JSON, nullable=True)
    failed_mappings = Column(JSON, nullable=True)
    user_corrections = Column(JSON, nullable=True)
    pattern_analysis = Column(JSON, nullable=True)
    confidence_metrics = Column(JSON, nullable=True)
    usage_statistics = Column(JSON, nullable=True)
    data_source_id = Column(
        UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 关系
    data_source = relationship("DataSource", back_populates="knowledge_entries")


class LLMCallLog(Base):
    """LLM调用日志表"""

    __tablename__ = "llm_call_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    request_type = Column(
        String(50), nullable=False
    )  # understanding, field_matching, etc.
    prompt_template = Column(String(100), nullable=False)
    input_data = Column(JSON, nullable=False)
    response_data = Column(JSON, nullable=True)
    model_used = Column(String(100), nullable=False)
    tokens_used = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    cost_estimate = Column(DECIMAL(10, 6), nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    user = relationship("User", back_populates="llm_call_logs")


class FieldMappingCache(Base):
    """字段映射缓存表"""

    __tablename__ = "field_mapping_cache"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    placeholder_signature = Column(
        String(255), nullable=False, index=True
    )  # hash of type+description+context
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False)
    matched_field = Column(String(255), nullable=False)
    confidence_score = Column(DECIMAL(3, 2), nullable=False)
    transformation_config = Column(JSON, nullable=True)
    usage_count = Column(Integer, default=1, nullable=False)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    data_source = relationship(
        "DataSource", back_populates="field_mapping_cache"
    )


class ReportQualityScore(Base):
    """报告质量评分表"""

    __tablename__ = "report_quality_scores"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(255), nullable=False, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    overall_score = Column(DECIMAL(3, 2), nullable=False)
    language_fluency_score = Column(DECIMAL(3, 2), nullable=True)
    data_consistency_score = Column(DECIMAL(3, 2), nullable=True)
    completeness_score = Column(DECIMAL(3, 2), nullable=True)
    accuracy_score = Column(DECIMAL(3, 2), nullable=True)
    formatting_score = Column(DECIMAL(3, 2), nullable=True)
    quality_issues = Column(JSON, nullable=True)
    improvement_suggestions = Column(JSON, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    llm_analysis_used = Column(Boolean, default=False, nullable=False)
    manual_review_required = Column(Boolean, default=False, nullable=False)
    reviewer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # 关系
    template = relationship("Template", back_populates="quality_scores")
    user = relationship("User", back_populates="quality_scores")
