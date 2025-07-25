"""
智能占位符学习服务

实现错误处理和学习机制，包括：
- 错误分类和上下文记录
- 用户反馈收集和处理
- 占位符匹配规则自动学习
- 历史经验知识库和查询接口
"""

import asyncio
import hashlib
import json
import logging
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..db.session import get_db_session
from ..models.data_source import DataSource
from ..models.placeholder_mapping import PlaceholderMapping
from ..models.user import User

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """错误分类"""

    PARSING_ERROR = "parsing_error"  # 占位符解析错误
    LLM_ERROR = "llm_error"  # LLM调用错误
    FIELD_MATCHING_ERROR = "field_matching_error"  # 字段匹配错误
    ETL_ERROR = "etl_error"  # ETL处理错误
    CONTENT_GENERATION_ERROR = "content_generation_error"  # 内容生成错误
    VALIDATION_ERROR = "validation_error"  # 验证错误
    SYSTEM_ERROR = "system_error"  # 系统错误


class ErrorSeverity(Enum):
    """错误严重程度"""

    LOW = "low"  # 低级错误，不影响主要功能
    MEDIUM = "medium"  # 中级错误，影响部分功能
    HIGH = "high"  # 高级错误，影响主要功能
    CRITICAL = "critical"  # 严重错误，系统无法正常工作


class FeedbackType(Enum):
    """反馈类型"""

    CORRECTION = "correction"  # 纠正错误
    IMPROVEMENT = "improvement"  # 改进建议
    VALIDATION = "validation"  # 验证结果
    COMPLAINT = "complaint"  # 投诉问题


@dataclass
class ErrorContext:
    """错误上下文信息"""

    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    placeholder_text: str
    placeholder_type: str
    placeholder_description: str
    context_before: str
    context_after: str
    data_source_id: Optional[int]
    user_id: Optional[int]
    session_id: Optional[str]
    timestamp: datetime
    stack_trace: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class UserFeedback:
    """用户反馈信息"""

    feedback_id: str
    user_id: int
    error_id: Optional[str]
    feedback_type: FeedbackType
    placeholder_text: str
    original_result: str
    corrected_result: Optional[str]
    suggested_field: Optional[str]
    confidence_rating: Optional[int]  # 1-5分
    comments: Optional[str]
    timestamp: datetime


@dataclass
class LearningRule:
    """学习规则"""

    rule_id: str
    placeholder_pattern: str
    field_mapping: str
    confidence_score: float
    usage_count: int
    success_rate: float
    created_from_feedback: bool
    last_updated: datetime
    metadata: Dict[str, Any]


@dataclass
class KnowledgeEntry:
    """知识库条目"""

    entry_id: str
    placeholder_signature: str
    successful_mappings: List[Dict[str, Any]]
    failed_mappings: List[Dict[str, Any]]
    user_corrections: List[Dict[str, Any]]
    pattern_analysis: Dict[str, Any]
    confidence_metrics: Dict[str, float]
    last_updated: datetime


class LearningService:
    """智能学习服务"""

    def __init__(self, db: Session):
        self.db = db
        self.error_cache: Dict[str, ErrorContext] = {}
        self.feedback_cache: List[UserFeedback] = []
        self.learning_rules: Dict[str, LearningRule] = {}
        self.knowledge_base: Dict[str, KnowledgeEntry] = {}

        # 学习参数
        self.min_confidence_threshold = 0.7
        self.learning_rate = 0.1
        self.pattern_similarity_threshold = 0.8
        self.auto_learning_enabled = True

        # 初始化知识库
        asyncio.create_task(self._initialize_knowledge_base())

    async def _initialize_knowledge_base(self) -> None:
        """初始化知识库"""
        try:
            # 从数据库加载现有的映射规则
            await self._load_existing_mappings()
            # 分析历史模式
            await self._analyze_historical_patterns()
            logger.info("知识库初始化完成")
        except Exception as e:
            logger.error(f"知识库初始化失败: {e}")

    async def record_error(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity,
        message: str,
        placeholder_text: str = "",
        placeholder_type: str = "",
        placeholder_description: str = "",
        context_before: str = "",
        context_after: str = "",
        data_source_id: Optional[int] = None,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        stack_trace: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录错误信息

        Args:
            category: 错误分类
            severity: 错误严重程度
            message: 错误消息
            placeholder_text: 占位符文本
            placeholder_type: 占位符类型
            placeholder_description: 占位符描述
            context_before: 前置上下文
            context_after: 后置上下文
            data_source_id: 数据源ID
            user_id: 用户ID
            session_id: 会话ID
            stack_trace: 堆栈跟踪
            additional_data: 附加数据

        Returns:
            错误ID
        """
        try:
            # 生成错误ID
            error_id = self._generate_error_id(placeholder_text, message)

            # 创建错误上下文
            error_context = ErrorContext(
                error_id=error_id,
                category=category,
                severity=severity,
                message=message,
                placeholder_text=placeholder_text,
                placeholder_type=placeholder_type,
                placeholder_description=placeholder_description,
                context_before=context_before,
                context_after=context_after,
                data_source_id=data_source_id,
                user_id=user_id,
                session_id=session_id,
                timestamp=datetime.utcnow(),
                stack_trace=stack_trace,
                additional_data=additional_data or {},
            )

            # 缓存错误信息
            self.error_cache[error_id] = error_context

            # 记录到日志
            log_level = {
                ErrorSeverity.LOW: logger.info,
                ErrorSeverity.MEDIUM: logger.warning,
                ErrorSeverity.HIGH: logger.error,
                ErrorSeverity.CRITICAL: logger.critical,
            }.get(severity, logger.info)

            log_level(f"错误记录 [{category.value}]: {message} (ID: {error_id})")

            # 检查是否需要触发自动学习
            if self.auto_learning_enabled:
                await self._trigger_auto_learning(error_context)

            # 检查是否需要人工审核
            await self._check_manual_review_trigger(error_context)

            return error_id

        except Exception as e:
            logger.error(f"记录错误失败: {e}")
            return ""

    async def collect_user_feedback(
        self,
        user_id: int,
        feedback_type: FeedbackType,
        placeholder_text: str,
        original_result: str,
        corrected_result: Optional[str] = None,
        suggested_field: Optional[str] = None,
        confidence_rating: Optional[int] = None,
        comments: Optional[str] = None,
        error_id: Optional[str] = None,
    ) -> str:
        """
        收集用户反馈

        Args:
            user_id: 用户ID
            feedback_type: 反馈类型
            placeholder_text: 占位符文本
            original_result: 原始结果
            corrected_result: 纠正后的结果
            suggested_field: 建议的字段
            confidence_rating: 置信度评分 (1-5)
            comments: 评论
            error_id: 关联的错误ID

        Returns:
            反馈ID
        """
        try:
            # 生成反馈ID
            feedback_id = self._generate_feedback_id(user_id, placeholder_text)

            # 创建反馈对象
            feedback = UserFeedback(
                feedback_id=feedback_id,
                user_id=user_id,
                error_id=error_id,
                feedback_type=feedback_type,
                placeholder_text=placeholder_text,
                original_result=original_result,
                corrected_result=corrected_result,
                suggested_field=suggested_field,
                confidence_rating=confidence_rating,
                comments=comments,
                timestamp=datetime.utcnow(),
            )

            # 缓存反馈
            self.feedback_cache.append(feedback)

            logger.info(f"收集用户反馈: {feedback_type.value} (ID: {feedback_id})")

            # 处理反馈并更新学习规则
            await self._process_feedback(feedback)

            return feedback_id

        except Exception as e:
            logger.error(f"收集用户反馈失败: {e}")
            return ""

    async def learn_from_success(
        self,
        placeholder_text: str,
        placeholder_type: str,
        matched_field: str,
        confidence_score: float,
        data_source_id: int,
        processing_time: float,
    ) -> None:
        """
        从成功案例中学习

        Args:
            placeholder_text: 占位符文本
            placeholder_type: 占位符类型
            matched_field: 匹配的字段
            confidence_score: 置信度分数
            data_source_id: 数据源ID
            processing_time: 处理时间
        """
        try:
            # 生成占位符签名
            signature = self._generate_placeholder_signature(
                placeholder_text, placeholder_type, data_source_id
            )

            # 更新或创建映射缓存
            await self._update_mapping_cache(
                signature, data_source_id, matched_field, confidence_score
            )

            # 更新知识库
            await self._update_knowledge_base(
                signature, matched_field, confidence_score, True
            )

            logger.debug(f"从成功案例学习: {placeholder_text} -> {matched_field}")

        except Exception as e:
            logger.error(f"从成功案例学习失败: {e}")

    async def query_knowledge_base(
        self,
        placeholder_text: str,
        placeholder_type: str,
        data_source_id: int,
        context: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        查询知识库获取建议

        Args:
            placeholder_text: 占位符文本
            placeholder_type: 占位符类型
            data_source_id: 数据源ID
            context: 上下文信息

        Returns:
            建议列表
        """
        try:
            suggestions = []

            # 生成查询签名
            signature = self._generate_placeholder_signature(
                placeholder_text, placeholder_type, data_source_id
            )

            # 精确匹配
            exact_match = await self._query_exact_match(signature)
            if exact_match:
                suggestions.append(
                    {
                        "type": "exact_match",
                        "field": exact_match["field"],
                        "confidence": exact_match["confidence"],
                        "usage_count": exact_match["usage_count"],
                        "source": "cache",
                    }
                )

            # 模式匹配
            pattern_matches = await self._query_pattern_matches(
                placeholder_text, placeholder_type, data_source_id
            )
            suggestions.extend(pattern_matches)

            # 语义相似匹配
            semantic_matches = await self._query_semantic_matches(
                placeholder_text, context, data_source_id
            )
            suggestions.extend(semantic_matches)

            # 按置信度排序
            suggestions.sort(key=lambda x: x.get("confidence", 0), reverse=True)

            return suggestions[:5]  # 返回前5个建议

        except Exception as e:
            logger.error(f"查询知识库失败: {e}")
            return []

    async def get_error_statistics(
        self,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
    ) -> Dict[str, Any]:
        """
        获取错误统计信息

        Args:
            time_range: 时间范围
            category: 错误分类
            severity: 错误严重程度

        Returns:
            统计信息
        """
        try:
            # 过滤错误
            filtered_errors = list(self.error_cache.values())

            if time_range:
                start_time, end_time = time_range
                filtered_errors = [
                    e for e in filtered_errors if start_time <= e.timestamp <= end_time
                ]

            if category:
                filtered_errors = [e for e in filtered_errors if e.category == category]

            if severity:
                filtered_errors = [e for e in filtered_errors if e.severity == severity]

            # 统计分析
            total_errors = len(filtered_errors)
            category_stats = Counter(e.category.value for e in filtered_errors)
            severity_stats = Counter(e.severity.value for e in filtered_errors)

            # 时间分布
            time_stats = defaultdict(int)
            for error in filtered_errors:
                hour_key = error.timestamp.strftime("%Y-%m-%d %H:00")
                time_stats[hour_key] += 1

            # 占位符类型分布
            placeholder_type_stats = Counter(
                e.placeholder_type for e in filtered_errors if e.placeholder_type
            )

            return {
                "total_errors": total_errors,
                "category_distribution": dict(category_stats),
                "severity_distribution": dict(severity_stats),
                "time_distribution": dict(time_stats),
                "placeholder_type_distribution": dict(placeholder_type_stats),
                "error_rate_trend": await self._calculate_error_rate_trend(
                    filtered_errors
                ),
            }

        except Exception as e:
            logger.error(f"获取错误统计失败: {e}")
            return {}

    async def get_learning_metrics(self) -> Dict[str, Any]:
        """获取学习指标"""
        try:
            # 映射缓存统计
            cache_stats = await self._get_cache_statistics()

            # 反馈统计
            feedback_stats = self._get_feedback_statistics()

            # 学习规则统计
            rule_stats = self._get_learning_rule_statistics()

            # 知识库统计
            knowledge_stats = self._get_knowledge_base_statistics()

            return {
                "cache_statistics": cache_stats,
                "feedback_statistics": feedback_stats,
                "learning_rule_statistics": rule_stats,
                "knowledge_base_statistics": knowledge_stats,
                "learning_effectiveness": await self._calculate_learning_effectiveness(),
            }

        except Exception as e:
            logger.error(f"获取学习指标失败: {e}")
            return {}

    # 私有方法

    def _generate_error_id(self, placeholder_text: str, message: str) -> str:
        """生成错误ID"""
        content = f"{placeholder_text}_{message}_{datetime.utcnow().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _generate_feedback_id(self, user_id: int, placeholder_text: str) -> str:
        """生成反馈ID"""
        content = f"{user_id}_{placeholder_text}_{datetime.utcnow().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _generate_placeholder_signature(
        self, placeholder_text: str, placeholder_type: str, data_source_id: int
    ) -> str:
        """生成占位符签名"""
        content = f"{placeholder_type}_{placeholder_text}_{data_source_id}"
        return hashlib.md5(content.encode()).hexdigest()

    async def _trigger_auto_learning(self, error_context: ErrorContext) -> None:
        """触发自动学习"""
        try:
            # 检查是否是可学习的错误类型
            learnable_categories = [
                ErrorCategory.FIELD_MATCHING_ERROR,
                ErrorCategory.PARSING_ERROR,
            ]

            if error_context.category not in learnable_categories:
                return

            # 分析错误模式
            pattern = await self._analyze_error_pattern(error_context)
            if pattern:
                await self._create_learning_rule_from_error(error_context, pattern)

        except Exception as e:
            logger.error(f"自动学习触发失败: {e}")

    async def _check_manual_review_trigger(self, error_context: ErrorContext) -> None:
        """检查是否需要触发人工审核"""
        try:
            # 严重错误需要人工审核
            if error_context.severity == ErrorSeverity.CRITICAL:
                await self._trigger_manual_review(error_context, "严重错误")
                return

            # 检查错误频率
            similar_errors = [
                e
                for e in self.error_cache.values()
                if (
                    e.category == error_context.category
                    and e.placeholder_type == error_context.placeholder_type
                    and e.timestamp > datetime.utcnow() - timedelta(hours=1)
                )
            ]

            if len(similar_errors) >= 5:  # 1小时内同类错误超过5次
                await self._trigger_manual_review(
                    error_context, f"高频错误: {len(similar_errors)}次"
                )

        except Exception as e:
            logger.error(f"人工审核检查失败: {e}")

    async def _trigger_manual_review(
        self, error_context: ErrorContext, reason: str
    ) -> None:
        """触发人工审核"""
        logger.warning(f"触发人工审核: {reason} (错误ID: {error_context.error_id})")
        # 这里可以发送通知给管理员或创建审核任务
        # 暂时只记录日志

    async def _process_feedback(self, feedback: UserFeedback) -> None:
        """处理用户反馈"""
        try:
            if feedback.feedback_type == FeedbackType.CORRECTION:
                await self._process_correction_feedback(feedback)
            elif feedback.feedback_type == FeedbackType.IMPROVEMENT:
                await self._process_improvement_feedback(feedback)
            elif feedback.feedback_type == FeedbackType.VALIDATION:
                await self._process_validation_feedback(feedback)

        except Exception as e:
            logger.error(f"处理用户反馈失败: {e}")

    async def _process_correction_feedback(self, feedback: UserFeedback) -> None:
        """处理纠正反馈"""
        if not feedback.corrected_result or not feedback.suggested_field:
            return

        # 更新映射规则
        # 这里需要根据反馈更新占位符映射
        logger.info(
            f"处理纠正反馈: {feedback.placeholder_text} -> {feedback.suggested_field}"
        )

    async def _process_improvement_feedback(self, feedback: UserFeedback) -> None:
        """处理改进反馈"""
        # 分析改进建议并更新算法参数
        logger.info(f"处理改进反馈: {feedback.comments}")

    async def _process_validation_feedback(self, feedback: UserFeedback) -> None:
        """处理验证反馈"""
        if feedback.confidence_rating:
            # 更新置信度模型
            logger.info(f"处理验证反馈: 置信度评分 {feedback.confidence_rating}")

    async def _load_existing_mappings(self) -> None:
        """加载现有映射"""
        try:
            mappings = self.db.query(PlaceholderMapping).all()
            for mapping in mappings:
                # 转换为知识库格式
                pass
        except Exception as e:
            logger.error(f"加载现有映射失败: {e}")

    async def _analyze_historical_patterns(self) -> None:
        """分析历史模式"""
        # 分析历史数据，提取模式
        pass

    async def _update_mapping_cache(
        self,
        signature: str,
        data_source_id: int,
        matched_field: str,
        confidence_score: float,
    ) -> None:
        """更新映射缓存"""
        try:
            # 查找现有映射
            existing = (
                self.db.query(PlaceholderMapping)
                .filter(PlaceholderMapping.placeholder_signature == signature)
                .first()
            )

            if existing:
                # 更新现有映射
                existing.usage_count += 1
                existing.last_used_at = datetime.utcnow()
                # 更新置信度（加权平均）
                existing.confidence_score = (
                    existing.confidence_score * 0.8 + confidence_score * 0.2
                )
            else:
                # 创建新映射
                new_mapping = PlaceholderMapping(
                    placeholder_signature=signature,
                    data_source_id=data_source_id,
                    matched_field=matched_field,
                    confidence_score=confidence_score,
                    usage_count=1,
                )
                self.db.add(new_mapping)

            self.db.commit()

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"更新映射缓存失败: {e}")

    async def _update_knowledge_base(
        self, signature: str, matched_field: str, confidence_score: float, success: bool
    ) -> None:
        """更新知识库"""
        # 更新内存中的知识库
        if signature not in self.knowledge_base:
            self.knowledge_base[signature] = KnowledgeEntry(
                entry_id=signature,
                placeholder_signature=signature,
                successful_mappings=[],
                failed_mappings=[],
                user_corrections=[],
                pattern_analysis={},
                confidence_metrics={},
                last_updated=datetime.utcnow(),
            )

        entry = self.knowledge_base[signature]
        mapping_info = {
            "field": matched_field,
            "confidence": confidence_score,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if success:
            entry.successful_mappings.append(mapping_info)
        else:
            entry.failed_mappings.append(mapping_info)

        entry.last_updated = datetime.utcnow()

    async def _query_exact_match(self, signature: str) -> Optional[Dict[str, Any]]:
        """查询精确匹配"""
        try:
            mapping = (
                self.db.query(PlaceholderMapping)
                .filter(PlaceholderMapping.placeholder_signature == signature)
                .first()
            )

            if mapping:
                return {
                    "field": mapping.matched_field,
                    "confidence": float(mapping.confidence_score),
                    "usage_count": mapping.usage_count,
                }
            return None

        except Exception as e:
            logger.error(f"精确匹配查询失败: {e}")
            return None

    async def _query_pattern_matches(
        self, placeholder_text: str, placeholder_type: str, data_source_id: int
    ) -> List[Dict[str, Any]]:
        """查询模式匹配"""
        # 实现模式匹配逻辑
        return []

    async def _query_semantic_matches(
        self, placeholder_text: str, context: Optional[str], data_source_id: int
    ) -> List[Dict[str, Any]]:
        """查询语义匹配"""
        # 实现语义匹配逻辑
        return []

    async def _analyze_error_pattern(
        self, error_context: ErrorContext
    ) -> Optional[Dict[str, Any]]:
        """分析错误模式"""
        # 分析错误模式，返回模式信息
        return None

    async def _create_learning_rule_from_error(
        self, error_context: ErrorContext, pattern: Dict[str, Any]
    ) -> None:
        """从错误创建学习规则"""
        # 从错误模式创建学习规则
        pass

    async def _calculate_error_rate_trend(
        self, errors: List[ErrorContext]
    ) -> List[Dict[str, Any]]:
        """计算错误率趋势"""
        # 计算错误率趋势
        return []

    async def _get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计"""
        try:
            total_mappings = self.db.query(PlaceholderMapping).count()
            avg_confidence = self.db.query(
                func.avg(PlaceholderMapping.confidence_score)
            ).scalar()

            return {
                "total_mappings": total_mappings,
                "average_confidence": float(avg_confidence) if avg_confidence else 0.0,
            }
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}

    def _get_feedback_statistics(self) -> Dict[str, Any]:
        """获取反馈统计"""
        total_feedback = len(self.feedback_cache)
        feedback_types = Counter(f.feedback_type.value for f in self.feedback_cache)

        return {
            "total_feedback": total_feedback,
            "feedback_type_distribution": dict(feedback_types),
        }

    def _get_learning_rule_statistics(self) -> Dict[str, Any]:
        """获取学习规则统计"""
        return {
            "total_rules": len(self.learning_rules),
            "active_rules": len(
                [r for r in self.learning_rules.values() if r.success_rate > 0.7]
            ),
        }

    def _get_knowledge_base_statistics(self) -> Dict[str, Any]:
        """获取知识库统计"""
        return {
            "total_entries": len(self.knowledge_base),
            "entries_with_corrections": len(
                [e for e in self.knowledge_base.values() if e.user_corrections]
            ),
        }

    async def _calculate_learning_effectiveness(self) -> Dict[str, float]:
        """计算学习效果"""
        # 计算学习效果指标
        return {
            "accuracy_improvement": 0.0,
            "processing_time_reduction": 0.0,
            "user_satisfaction_increase": 0.0,
        }


# 便捷函数
async def get_learning_service(db: Session = None) -> LearningService:
    """获取学习服务实例"""
    if db is None:
        with get_db_session() as db:
            return LearningService(db)
    return LearningService(db)
