"""
智能字段匹配器服务

该服务实现基于语义相似度和机器学习的智能字段匹配功能，
支持模糊匹配、缓存机制和置信度评分。
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# Optional imports - will gracefully degrade if not available
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from sentence_transformers import SentenceTransformer

    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    from fuzzywuzzy import fuzz, process

    HAS_FUZZYWUZZY = True
except ImportError:
    HAS_FUZZYWUZZY = False

try:
    import redis

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
from sqlalchemy.orm import Session

from ...core.config import settings
from ...crud.crud_placeholder_mapping import crud_placeholder_mapping
from ...db.session import get_db_session
# 避免循环导入，直接使用 SessionLocal
from ...db.session import SessionLocal
from ...models.placeholder_mapping import PlaceholderMapping

logger = logging.getLogger(__name__)


@dataclass
class FieldSuggestion:
    """LLM建议的字段匹配"""

    field_name: str
    confidence: float
    transformation_needed: bool
    transformation_type: str
    calculation_formula: Optional[str] = None
    reasoning: Optional[str] = None


@dataclass
class FieldMatchingResult:
    """字段匹配结果"""

    matched_field: str
    confidence: float
    requires_transformation: bool
    transformation_config: Dict[str, Any]
    fallback_options: List[str]
    processing_time: float
    cache_hit: bool = False
    reasoning: Optional[str] = None


@dataclass
class SimilarityScore:
    """相似度评分"""

    field_name: str
    semantic_score: float
    fuzzy_score: float
    combined_score: float
    reasoning: str


class IntelligentFieldMatcher:
    """智能字段匹配器"""

    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold
        self.embedding_model = None
        self.redis_client = None
        self.cache_ttl = 3600 * 24 * 7  # 7天缓存
        self._initialize_models()

    def _initialize_models(self):
        """初始化模型和缓存"""
        try:
            # 初始化语义相似度模型（如果可用）
            if HAS_SENTENCE_TRANSFORMERS:
                self.embedding_model = SentenceTransformer(
                    "paraphrase-multilingual-MiniLM-L12-v2"
                )
                logger.info("Sentence transformer model loaded successfully")
            else:
                logger.warning(
                    "Sentence transformers not available, using fallback algorithms"
                )

            # 初始化Redis缓存（如果可用）
            if HAS_REDIS and hasattr(settings, "REDIS_URL"):
                self.redis_client = redis.from_url(settings.REDIS_URL)
                logger.info("Redis cache initialized")
            else:
                logger.warning(
                    "Redis not configured or not available, caching disabled"
                )

        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            self.embedding_model = None
            self.redis_client = None

    async def match_fields(
        self,
        llm_suggestions: List[FieldSuggestion],
        available_fields: List[str],
        placeholder_context: str = "",
        data_source_id: Optional[int] = None,
    ) -> FieldMatchingResult:
        """
        匹配字段

        Args:
            llm_suggestions: LLM建议的字段匹配列表
            available_fields: 可用字段列表
            placeholder_context: 占位符上下文
            data_source_id: 数据源ID

        Returns:
            字段匹配结果
        """
        start_time = datetime.now()

        try:
            # 检查缓存
            cache_key = self._generate_cache_key(
                llm_suggestions, available_fields, placeholder_context
            )
            cached_result = await self._get_cached_result(cache_key)
            if cached_result:
                cached_result.cache_hit = True
                return cached_result

            # 执行字段匹配
            best_match = await self._find_best_match(
                llm_suggestions, available_fields, placeholder_context
            )

            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds()

            # 构建结果
            result = FieldMatchingResult(
                matched_field=best_match["field_name"],
                confidence=best_match["confidence"],
                requires_transformation=best_match.get(
                    "requires_transformation", False
                ),
                transformation_config=best_match.get("transformation_config", {}),
                fallback_options=best_match.get("fallback_options", []),
                processing_time=processing_time,
                reasoning=best_match.get("reasoning", ""),
            )

            # 缓存结果
            await self._cache_result(cache_key, result)

            # 保存到数据库
            if data_source_id:
                await self._save_mapping_to_db(
                    llm_suggestions, result, data_source_id, placeholder_context
                )

            return result

        except Exception as e:
            logger.error(f"Field matching failed: {e}")
            # 返回默认结果
            processing_time = (datetime.now() - start_time).total_seconds()
            return FieldMatchingResult(
                matched_field=llm_suggestions[0].field_name if llm_suggestions else "",
                confidence=0.0,
                requires_transformation=False,
                transformation_config={},
                fallback_options=[],
                processing_time=processing_time,
                reasoning=f"Error occurred: {str(e)}",
            )

    async def _find_best_match(
        self,
        llm_suggestions: List[FieldSuggestion],
        available_fields: List[str],
        context: str,
    ) -> Dict[str, Any]:
        """找到最佳匹配"""

        if not llm_suggestions or not available_fields:
            return {
                "field_name": "",
                "confidence": 0.0,
                "reasoning": "No suggestions or available fields",
            }

        # 验证LLM建议的字段是否存在
        validated_suggestions = []
        for suggestion in llm_suggestions:
            if suggestion.field_name in available_fields:
                validated_suggestions.append(
                    {
                        "field_name": suggestion.field_name,
                        "confidence": suggestion.confidence,
                        "requires_transformation": suggestion.transformation_needed,
                        "transformation_config": {
                            "type": suggestion.transformation_type,
                            "formula": suggestion.calculation_formula,
                        },
                        "reasoning": f"Direct match from LLM: {suggestion.reasoning or ''}",
                    }
                )

        # 如果有直接匹配，选择置信度最高的
        if validated_suggestions:
            best_direct = max(validated_suggestions, key=lambda x: x["confidence"])
            if best_direct["confidence"] >= self.similarity_threshold:
                return best_direct

        # 执行语义相似度匹配
        similarity_scores = await self._calculate_similarity_scores(
            llm_suggestions, available_fields, context
        )

        if not similarity_scores:
            return {
                "field_name": llm_suggestions[0].field_name,
                "confidence": 0.0,
                "reasoning": "No similarity matches found",
            }

        # 选择最佳匹配
        best_match = max(similarity_scores, key=lambda x: x.combined_score)

        # 查找对应的LLM建议
        matching_suggestion = None
        for suggestion in llm_suggestions:
            if suggestion.field_name == best_match.field_name:
                matching_suggestion = suggestion
                break

        return {
            "field_name": best_match.field_name,
            "confidence": best_match.combined_score,
            "requires_transformation": (
                matching_suggestion.transformation_needed
                if matching_suggestion
                else False
            ),
            "transformation_config": {
                "type": (
                    matching_suggestion.transformation_type
                    if matching_suggestion
                    else "none"
                ),
                "formula": (
                    matching_suggestion.calculation_formula
                    if matching_suggestion
                    else None
                ),
            },
            "fallback_options": [
                score.field_name for score in similarity_scores[1:6]  # 前5个备选
            ],
            "reasoning": best_match.reasoning,
        }

    async def _calculate_similarity_scores(
        self,
        llm_suggestions: List[FieldSuggestion],
        available_fields: List[str],
        context: str,
    ) -> List[SimilarityScore]:
        """计算相似度评分"""

        if not self.embedding_model:
            logger.warning("Embedding model not available, using fuzzy matching only")
            return await self._fuzzy_match_only(llm_suggestions, available_fields)

        similarity_scores = []

        # 为每个LLM建议计算与可用字段的相似度
        for suggestion in llm_suggestions:
            # 构建查询文本
            query_text = f"{suggestion.field_name} {context}"

            # 计算语义相似度
            semantic_scores = await self._calculate_semantic_similarity(
                query_text, available_fields
            )

            # 计算模糊匹配分数
            fuzzy_scores = self._calculate_fuzzy_similarity(
                suggestion.field_name, available_fields
            )

            # 合并分数
            for field in available_fields:
                semantic_score = semantic_scores.get(field, 0.0)
                fuzzy_score = fuzzy_scores.get(field, 0.0)

                # 加权合并（语义相似度权重更高）
                combined_score = (
                    semantic_score * 0.7 + fuzzy_score * 0.3
                ) * suggestion.confidence

                similarity_scores.append(
                    SimilarityScore(
                        field_name=field,
                        semantic_score=semantic_score,
                        fuzzy_score=fuzzy_score,
                        combined_score=combined_score,
                        reasoning=f"Semantic: {semantic_score:.3f}, Fuzzy: {fuzzy_score:.3f}, LLM confidence: {suggestion.confidence:.3f}",
                    )
                )

        # 按综合分数排序
        similarity_scores.sort(key=lambda x: x.combined_score, reverse=True)

        return similarity_scores

    async def _calculate_semantic_similarity(
        self, query_text: str, available_fields: List[str]
    ) -> Dict[str, float]:
        """计算语义相似度"""

        try:
            # 生成查询文本的嵌入
            query_embedding = self.embedding_model.encode([query_text])

            # 生成字段名的嵌入
            field_embeddings = self.embedding_model.encode(available_fields)

            # 计算余弦相似度
            similarities = np.dot(query_embedding, field_embeddings.T)[0]

            # 归一化到0-1范围
            similarities = (similarities + 1) / 2

            return dict(zip(available_fields, similarities))

        except Exception as e:
            logger.error(f"Semantic similarity calculation failed: {e}")
            return {}

    def _calculate_fuzzy_similarity(
        self, query_field: str, available_fields: List[str]
    ) -> Dict[str, float]:
        """计算模糊匹配相似度"""

        fuzzy_scores = {}

        for field in available_fields:
            if HAS_FUZZYWUZZY:
                # 使用fuzzywuzzy库的多种算法
                ratio_score = fuzz.ratio(query_field.lower(), field.lower()) / 100.0
                partial_score = (
                    fuzz.partial_ratio(query_field.lower(), field.lower()) / 100.0
                )
                token_sort_score = (
                    fuzz.token_sort_ratio(query_field.lower(), field.lower()) / 100.0
                )

                # 取最高分
                fuzzy_scores[field] = max(ratio_score, partial_score, token_sort_score)
            else:
                # 使用自实现的相似度算法
                jaccard_score = self._calculate_jaccard_similarity(query_field, field)
                edit_score = self._calculate_edit_similarity(query_field, field)
                lcs_score = self._calculate_lcs_similarity(query_field, field)

                # 取最高分
                fuzzy_scores[field] = max(jaccard_score, edit_score, lcs_score)

        return fuzzy_scores

    def _calculate_jaccard_similarity(self, str1: str, str2: str) -> float:
        """计算Jaccard相似度"""
        str1_lower = str1.lower()
        str2_lower = str2.lower()

        set1 = set(str1_lower)
        set2 = set(str2_lower)

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0

    def _calculate_edit_similarity(self, str1: str, str2: str) -> float:
        """计算编辑距离相似度（简化版）"""
        str1_lower = str1.lower()
        str2_lower = str2.lower()

        if not str1_lower or not str2_lower:
            return 0.0

        max_len = max(len(str1_lower), len(str2_lower))

        # 计算公共字符数
        common_chars = 0
        for char in str1_lower:
            if char in str2_lower:
                common_chars += 1

        return common_chars / max_len

    def _calculate_lcs_similarity(self, str1: str, str2: str) -> float:
        """计算最长公共子序列相似度（简化版）"""
        str1_lower = str1.lower()
        str2_lower = str2.lower()

        if not str1_lower or not str2_lower:
            return 0.0

        # 简化的LCS计算
        common_length = 0
        i, j = 0, 0

        while i < len(str1_lower) and j < len(str2_lower):
            if str1_lower[i] == str2_lower[j]:
                common_length += 1
                i += 1
                j += 1
            else:
                i += 1

        max_len = max(len(str1_lower), len(str2_lower))
        return common_length / max_len

    async def _fuzzy_match_only(
        self, llm_suggestions: List[FieldSuggestion], available_fields: List[str]
    ) -> List[SimilarityScore]:
        """仅使用模糊匹配"""

        similarity_scores = []

        for suggestion in llm_suggestions:
            fuzzy_scores = self._calculate_fuzzy_similarity(
                suggestion.field_name, available_fields
            )

            for field, score in fuzzy_scores.items():
                combined_score = score * suggestion.confidence

                similarity_scores.append(
                    SimilarityScore(
                        field_name=field,
                        semantic_score=0.0,
                        fuzzy_score=score,
                        combined_score=combined_score,
                        reasoning=f"Fuzzy match: {score:.3f}, LLM confidence: {suggestion.confidence:.3f}",
                    )
                )

        similarity_scores.sort(key=lambda x: x.combined_score, reverse=True)
        return similarity_scores

    def _generate_cache_key(
        self,
        llm_suggestions: List[FieldSuggestion],
        available_fields: List[str],
        context: str,
    ) -> str:
        """生成缓存键"""

        # 创建唯一标识
        suggestions_str = json.dumps(
            [asdict(s) for s in llm_suggestions], sort_keys=True
        )
        fields_str = json.dumps(sorted(available_fields))

        content = f"{suggestions_str}:{fields_str}:{context}"
        return f"field_match:{hashlib.md5(content.encode()).hexdigest()}"

    async def _get_cached_result(self, cache_key: str) -> Optional[FieldMatchingResult]:
        """获取缓存结果"""

        if not self.redis_client:
            return None

        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return FieldMatchingResult(**data)
        except Exception as e:
            logger.error(f"Cache retrieval failed: {e}")

        return None

    async def _cache_result(self, cache_key: str, result: FieldMatchingResult):
        """缓存结果"""

        if not self.redis_client:
            return

        try:
            # 不缓存处理时间和缓存命中标志
            cache_data = asdict(result)
            cache_data.pop("processing_time", None)
            cache_data.pop("cache_hit", None)

            self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(cache_data))
        except Exception as e:
            logger.error(f"Cache storage failed: {e}")

    async def _save_mapping_to_db(
        self,
        llm_suggestions: List[FieldSuggestion],
        result: FieldMatchingResult,
        data_source_id: int,
        context: str,
    ):
        """保存映射到数据库"""

        try:
            # 生成占位符签名
            suggestions_str = json.dumps(
                [asdict(s) for s in llm_suggestions], sort_keys=True
            )
            placeholder_signature = hashlib.md5(
                f"{suggestions_str}:{context}".encode()
            ).hexdigest()

            # 保存到数据库
            with get_db_session() as db:
                # 检查是否已存在
                existing = crud_placeholder_mapping.get_by_signature(
                    db, signature=placeholder_signature, data_source_id=data_source_id
                )

                if existing:
                    # 更新使用次数
                    crud_placeholder_mapping.update_usage(db, db_obj=existing)
                else:
                    # 创建新记录
                    mapping_data = {
                        "placeholder_signature": placeholder_signature,
                        "data_source_id": data_source_id,
                        "matched_field": result.matched_field,
                        "confidence_score": result.confidence,
                        "transformation_config": result.transformation_config,
                        "usage_count": 1,
                    }
                    crud_placeholder_mapping.create(db, obj_in=mapping_data)

        except Exception as e:
            logger.error(f"Failed to save mapping to database: {e}")

    async def get_historical_mappings(
        self, data_source_id: int, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取历史映射记录"""

        try:
            db = next(get_db_session())
            mappings = crud_placeholder_mapping.get_by_data_source(
                db, data_source_id=data_source_id, limit=limit
            )
            db.close()

            return [
                {
                    "signature": mapping.placeholder_signature,
                    "matched_field": mapping.matched_field,
                    "confidence": mapping.confidence_score,
                    "usage_count": mapping.usage_count,
                    "last_used": (
                        mapping.last_used_at.isoformat()
                        if mapping.last_used_at
                        else None
                    ),
                    "transformation_config": mapping.transformation_config,
                }
                for mapping in mappings
            ]

        except Exception as e:
            logger.error(f"Failed to get historical mappings: {e}")
            return []


# 创建全局实例
intelligent_field_matcher = IntelligentFieldMatcher()
