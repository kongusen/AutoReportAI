"""
LLM占位符理解服务

使用LLM进行占位符语义理解、字段匹配建议生成和ETL指令生成的核心服务。
集成智能占位符处理器和LLM服务框架，提供完整的占位符理解能力。
"""

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.services.ai_integration import AIService, LLMRequest, LLMResponse
from app.services.intelligent_placeholder import (
    PlaceholderMatch,
    PlaceholderProcessor,
    PlaceholderType,
)

logger = logging.getLogger(__name__)


@dataclass
class PlaceholderUnderstanding:
    """占位符理解结果"""

    placeholder: str  # 原始占位符
    type: str  # 占位符类型
    description: str  # 描述
    semantic_meaning: str  # 语义含义
    data_type: str  # 数据类型
    field_suggestions: List[str]  # 字段建议
    calculation_needed: bool  # 是否需要计算
    aggregation_type: Optional[str]  # 聚合类型
    confidence: float  # 理解置信度
    context_analysis: Dict[str, Any]  # 上下文分析
    metadata: Dict[str, Any]  # 元数据


@dataclass
class FieldMatchingSuggestion:
    """字段匹配建议"""

    suggested_field: str  # 建议字段
    match_score: float  # 匹配分数
    match_reason: str  # 匹配原因
    data_transformation: Optional[str]  # 数据转换需求
    validation_rules: List[str]  # 验证规则


@dataclass
class ETLInstruction:
    """ETL指令"""

    instruction_id: str  # 指令ID
    query_type: str  # 查询类型
    source_tables: List[str]  # 源表
    target_fields: List[str]  # 目标字段
    filters: List[Dict[str, Any]]  # 过滤条件
    aggregations: List[Dict[str, Any]]  # 聚合操作
    calculations: List[Dict[str, Any]]  # 计算公式
    transformations: List[Dict[str, Any]]  # 数据转换
    output_format: str  # 输出格式
    execution_order: int  # 执行顺序
    dependencies: List[str]  # 依赖关系


class PlaceholderUnderstandingError(Exception):
    """占位符理解错误"""

    def __init__(self, message: str, placeholder: str = "", error_code: str = ""):
        self.message = message
        self.placeholder = placeholder
        self.error_code = error_code
        super().__init__(f"占位符理解错误: {message}")


class LLMPlaceholderService:
    """LLM占位符理解服务"""

    def __init__(self, db: Session, type_definitions_path: Optional[str] = None):
        """
        初始化服务

        Args:
            db: 数据库会话
            type_definitions_path: 类型定义文件路径
        """
        self.db = db
        self.ai_service = AIService(db)
        self.placeholder_processor = PlaceholderProcessor(type_definitions_path)

        # 加载提示模板
        self._load_prompt_templates()

        # 缓存理解结果
        self.understanding_cache: Dict[str, PlaceholderUnderstanding] = {}

    def _load_prompt_templates(self):
        """加载LLM提示模板"""
        self.prompt_templates = {
            "semantic_understanding": """
你是一个专业的中文占位符语义理解专家，专门分析智能占位符系统中的占位符含义。

占位符类型说明：
- 周期: 时间相关占位符，如年份、日期、时间段等
- 区域: 地理区域占位符，如省份、城市、地区等  
- 统计: 统计数据占位符，如数量、比例、平均值等
- 图表: 图表可视化占位符，如折线图、饼图、柱状图等

请分析给定的占位符并返回JSON格式的理解结果，包含以下字段：
1. semantic_meaning: 占位符的语义含义和业务意图
2. data_type: 期望的数据类型 (string, integer, float, date, percentage, boolean)
3. field_suggestions: 推荐的数据库字段名列表（基于语义分析）
4. calculation_needed: 是否需要进行计算或聚合 (true/false)
5. aggregation_type: 如果需要聚合，指定类型 (sum, count, avg, max, min, group_by)
6. business_context: 业务上下文和使用场景
7. validation_rules: 数据验证规则
8. confidence: 理解置信度 (0.0-1.0)

请确保分析准确、专业，并考虑中文语境下的语义特点。
""",
            "field_matching": """
你是一个数据字段匹配专家，专门为占位符推荐最合适的数据库字段。

请根据占位符的语义含义和可用的数据字段，提供字段匹配建议。
考虑以下因素：
1. 语义相似度：字段名与占位符描述的语义匹配程度
2. 数据类型兼容性：字段数据类型与期望类型的兼容性
3. 业务逻辑合理性：字段在业务场景中的合理性
4. 数据完整性：字段数据的完整性和质量

返回JSON格式的匹配建议，包含：
1. matches: 匹配建议列表，每个包含：
   - field_name: 字段名
   - match_score: 匹配分数 (0.0-1.0)
   - match_reason: 匹配原因说明
   - data_transformation: 需要的数据转换（如有）
   - confidence: 匹配置信度
2. best_match: 最佳匹配字段
3. alternative_matches: 备选匹配字段
4. no_match_reason: 如果没有合适匹配，说明原因
""",
            "etl_generation": """
你是一个ETL指令生成专家，专门为占位符生成数据提取、转换和加载指令。

请根据占位符需求和数据源结构，生成详细的ETL指令。
考虑以下方面：
1. 数据提取：从哪些表/字段提取数据
2. 数据过滤：需要应用的过滤条件
3. 数据聚合：需要的聚合操作
4. 数据计算：需要的计算公式
5. 数据转换：格式转换和数据清洗
6. 执行顺序：指令的执行顺序和依赖关系

返回JSON格式的ETL指令，包含：
1. query_type: 查询类型 (select, aggregate, calculate, transform)
2. source_tables: 源数据表列表
3. target_fields: 目标字段列表
4. filters: 过滤条件列表
5. aggregations: 聚合操作列表
6. calculations: 计算公式列表
7. transformations: 数据转换列表
8. output_format: 输出格式说明
9. execution_steps: 执行步骤
10. performance_hints: 性能优化建议
""",
            "context_analysis": """
你是一个上下文分析专家，专门分析占位符在文档中的上下文环境。

请分析占位符的上下文，提供以下信息：
1. context_type: 上下文类型 (statistical, temporal, geographical, comparative)
2. surrounding_elements: 周围的关键元素和概念
3. logical_relationships: 与其他占位符的逻辑关系
4. document_structure: 在文档结构中的位置和作用
5. semantic_dependencies: 语义依赖关系
6. formatting_requirements: 格式化要求
7. presentation_context: 展示上下文和要求

返回JSON格式的上下文分析结果。
""",
        }

    def understand_placeholder(
        self,
        placeholder_match: PlaceholderMatch,
        available_fields: Optional[List[str]] = None,
        data_source_schema: Optional[Dict[str, Any]] = None,
    ) -> PlaceholderUnderstanding:
        """
        理解单个占位符的语义含义

        Args:
            placeholder_match: 占位符匹配结果
            available_fields: 可用字段列表
            data_source_schema: 数据源结构

        Returns:
            占位符理解结果
        """
        try:
            # 检查缓存
            cache_key = f"{placeholder_match.full_match}_{hash(str(available_fields))}"
            if cache_key in self.understanding_cache:
                logger.info(f"从缓存获取占位符理解结果: {placeholder_match.full_match}")
                return self.understanding_cache[cache_key]

            # 构建理解请求
            understanding_prompt = self._build_understanding_prompt(
                placeholder_match, available_fields, data_source_schema
            )

            request = LLMRequest(
                messages=[{"role": "user", "content": understanding_prompt}],
                system_prompt=self.prompt_templates["semantic_understanding"],
                max_tokens=1000,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            # 调用LLM进行理解
            response = self.ai_service.call_llm_unified(request)

            # 解析理解结果
            understanding_result = self._parse_understanding_response(
                response, placeholder_match
            )

            # 进行上下文分析
            context_analysis = self._analyze_context(placeholder_match)
            understanding_result.context_analysis = context_analysis

            # 缓存结果
            self.understanding_cache[cache_key] = understanding_result

            logger.info(
                f"成功理解占位符: {placeholder_match.full_match} (置信度: {understanding_result.confidence:.2f})"
            )
            return understanding_result

        except Exception as e:
            logger.error(f"占位符理解失败: {placeholder_match.full_match}, 错误: {e}")
            raise PlaceholderUnderstandingError(
                f"理解占位符失败: {str(e)}", placeholder_match.full_match
            )

    def generate_field_matching_suggestions(
        self,
        understanding: PlaceholderUnderstanding,
        available_fields: List[str],
        field_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[FieldMatchingSuggestion]:
        """
        生成字段匹配建议

        Args:
            understanding: 占位符理解结果
            available_fields: 可用字段列表
            field_metadata: 字段元数据

        Returns:
            字段匹配建议列表
        """
        try:
            # 构建字段匹配请求
            matching_prompt = self._build_field_matching_prompt(
                understanding, available_fields, field_metadata
            )

            request = LLMRequest(
                messages=[{"role": "user", "content": matching_prompt}],
                system_prompt=self.prompt_templates["field_matching"],
                max_tokens=800,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            # 调用LLM生成匹配建议
            response = self.ai_service.call_llm_unified(request)

            # 解析匹配建议
            suggestions = self._parse_field_matching_response(response, understanding)

            logger.info(f"生成字段匹配建议: {len(suggestions)} 个建议")
            return suggestions

        except Exception as e:
            logger.error(f"字段匹配建议生成失败: {e}")
            return []

    def generate_etl_instructions(
        self,
        understanding: PlaceholderUnderstanding,
        data_source_schema: Dict[str, Any],
        field_mapping: Optional[Dict[str, str]] = None,
    ) -> ETLInstruction:
        """
        生成ETL指令

        Args:
            understanding: 占位符理解结果
            data_source_schema: 数据源结构
            field_mapping: 字段映射

        Returns:
            ETL指令
        """
        try:
            # 构建ETL生成请求
            etl_prompt = self._build_etl_generation_prompt(
                understanding, data_source_schema, field_mapping
            )

            request = LLMRequest(
                messages=[{"role": "user", "content": etl_prompt}],
                system_prompt=self.prompt_templates["etl_generation"],
                max_tokens=1200,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            # 调用LLM生成ETL指令
            response = self.ai_service.call_llm_unified(request)

            # 解析ETL指令
            etl_instruction = self._parse_etl_response(response, understanding)

            logger.info(f"生成ETL指令: {etl_instruction.instruction_id}")
            return etl_instruction

        except Exception as e:
            logger.error(f"ETL指令生成失败: {e}")
            raise PlaceholderUnderstandingError(
                f"ETL指令生成失败: {str(e)}", understanding.placeholder
            )

    def batch_understand_placeholders(
        self,
        placeholder_matches: List[PlaceholderMatch],
        available_fields: Optional[List[str]] = None,
        data_source_schema: Optional[Dict[str, Any]] = None,
    ) -> List[PlaceholderUnderstanding]:
        """
        批量理解占位符

        Args:
            placeholder_matches: 占位符匹配结果列表
            available_fields: 可用字段列表
            data_source_schema: 数据源结构

        Returns:
            占位符理解结果列表
        """
        understanding_results = []

        for placeholder_match in placeholder_matches:
            try:
                understanding = self.understand_placeholder(
                    placeholder_match, available_fields, data_source_schema
                )
                understanding_results.append(understanding)
            except Exception as e:
                logger.warning(
                    f"批量理解中跳过占位符 {placeholder_match.full_match}: {e}"
                )
                # 创建默认理解结果
                default_understanding = self._create_default_understanding(
                    placeholder_match
                )
                understanding_results.append(default_understanding)

        logger.info(
            f"批量理解完成: {len(understanding_results)}/{len(placeholder_matches)} 个占位符"
        )
        return understanding_results

    def _build_understanding_prompt(
        self,
        placeholder_match: PlaceholderMatch,
        available_fields: Optional[List[str]],
        data_source_schema: Optional[Dict[str, Any]],
    ) -> str:
        """构建理解提示"""
        prompt_parts = [
            f"占位符: {placeholder_match.full_match}",
            f"类型: {placeholder_match.type.value}",
            f"描述: {placeholder_match.description}",
            f"置信度: {placeholder_match.confidence:.2f}",
        ]

        if placeholder_match.context_before:
            prompt_parts.append(f"前置上下文: {placeholder_match.context_before}")

        if placeholder_match.context_after:
            prompt_parts.append(f"后置上下文: {placeholder_match.context_after}")

        if available_fields:
            prompt_parts.append(
                f"可用字段: {', '.join(available_fields[:20])}"
            )  # 限制字段数量

        if data_source_schema:
            schema_summary = self._summarize_schema(data_source_schema)
            prompt_parts.append(f"数据源结构: {schema_summary}")

        return "\n".join(prompt_parts)

    def _build_field_matching_prompt(
        self,
        understanding: PlaceholderUnderstanding,
        available_fields: List[str],
        field_metadata: Optional[Dict[str, Any]],
    ) -> str:
        """构建字段匹配提示"""
        prompt_parts = [
            f"占位符: {understanding.placeholder}",
            f"语义含义: {understanding.semantic_meaning}",
            f"期望数据类型: {understanding.data_type}",
            f"可用字段: {', '.join(available_fields)}",
        ]

        if understanding.field_suggestions:
            prompt_parts.append(
                f"初始字段建议: {', '.join(understanding.field_suggestions)}"
            )

        if field_metadata:
            metadata_summary = self._summarize_field_metadata(field_metadata)
            prompt_parts.append(f"字段元数据: {metadata_summary}")

        return "\n".join(prompt_parts)

    def _build_etl_generation_prompt(
        self,
        understanding: PlaceholderUnderstanding,
        data_source_schema: Dict[str, Any],
        field_mapping: Optional[Dict[str, str]],
    ) -> str:
        """构建ETL生成提示"""
        prompt_parts = [
            f"占位符: {understanding.placeholder}",
            f"语义含义: {understanding.semantic_meaning}",
            f"数据类型: {understanding.data_type}",
            f"需要计算: {understanding.calculation_needed}",
            f"聚合类型: {understanding.aggregation_type or '无'}",
        ]

        schema_summary = self._summarize_schema(data_source_schema)
        prompt_parts.append(f"数据源结构: {schema_summary}")

        if field_mapping:
            prompt_parts.append(
                f"字段映射: {json.dumps(field_mapping, ensure_ascii=False)}"
            )

        return "\n".join(prompt_parts)

    def _parse_understanding_response(
        self, response: LLMResponse, placeholder_match: PlaceholderMatch
    ) -> PlaceholderUnderstanding:
        """解析理解响应"""
        try:
            result = json.loads(response.content)

            return PlaceholderUnderstanding(
                placeholder=placeholder_match.full_match,
                type=placeholder_match.type.value,
                description=placeholder_match.description,
                semantic_meaning=result.get("semantic_meaning", ""),
                data_type=result.get("data_type", "string"),
                field_suggestions=result.get("field_suggestions", []),
                calculation_needed=result.get("calculation_needed", False),
                aggregation_type=result.get("aggregation_type"),
                confidence=result.get("confidence", 0.5),
                context_analysis={},
                metadata={
                    "llm_provider": response.provider,
                    "llm_model": response.model,
                    "response_time": response.response_time,
                    "cost_estimate": response.cost_estimate,
                    "business_context": result.get("business_context", ""),
                    "validation_rules": result.get("validation_rules", []),
                },
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"解析理解响应失败: {e}")
            return self._create_default_understanding(placeholder_match)

    def _parse_field_matching_response(
        self, response: LLMResponse, understanding: PlaceholderUnderstanding
    ) -> List[FieldMatchingSuggestion]:
        """解析字段匹配响应"""
        try:
            result = json.loads(response.content)
            suggestions = []

            matches = result.get("matches", [])
            for match in matches:
                suggestion = FieldMatchingSuggestion(
                    suggested_field=match.get("field_name", ""),
                    match_score=match.get("match_score", 0.0),
                    match_reason=match.get("match_reason", ""),
                    data_transformation=match.get("data_transformation"),
                    validation_rules=match.get("validation_rules", []),
                )
                suggestions.append(suggestion)

            return suggestions

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"解析字段匹配响应失败: {e}")
            return []

    def _parse_etl_response(
        self, response: LLMResponse, understanding: PlaceholderUnderstanding
    ) -> ETLInstruction:
        """解析ETL响应"""
        try:
            result = json.loads(response.content)

            return ETLInstruction(
                instruction_id=f"etl_{hash(understanding.placeholder)}_{int(datetime.now().timestamp())}",
                query_type=result.get("query_type", "select"),
                source_tables=result.get("source_tables", []),
                target_fields=result.get("target_fields", []),
                filters=result.get("filters", []),
                aggregations=result.get("aggregations", []),
                calculations=result.get("calculations", []),
                transformations=result.get("transformations", []),
                output_format=result.get("output_format", "scalar"),
                execution_order=1,
                dependencies=[],
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"解析ETL响应失败: {e}")
            return self._create_default_etl_instruction(understanding)

    def _analyze_context(self, placeholder_match: PlaceholderMatch) -> Dict[str, Any]:
        """分析占位符上下文"""
        try:
            context_prompt = f"""
            占位符: {placeholder_match.full_match}
            前置上下文: {placeholder_match.context_before}
            后置上下文: {placeholder_match.context_after}
            """

            request = LLMRequest(
                messages=[{"role": "user", "content": context_prompt}],
                system_prompt=self.prompt_templates["context_analysis"],
                max_tokens=600,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            response = self.ai_service.call_llm_unified(request)
            return json.loads(response.content)

        except Exception as e:
            logger.warning(f"上下文分析失败: {e}")
            return {
                "context_type": "unknown",
                "surrounding_elements": [],
                "logical_relationships": [],
                "document_structure": "unknown",
            }

    def _create_default_understanding(
        self, placeholder_match: PlaceholderMatch
    ) -> PlaceholderUnderstanding:
        """创建默认理解结果"""
        return PlaceholderUnderstanding(
            placeholder=placeholder_match.full_match,
            type=placeholder_match.type.value,
            description=placeholder_match.description,
            semantic_meaning=f"默认理解: {placeholder_match.description}",
            data_type="string",
            field_suggestions=[],
            calculation_needed=False,
            aggregation_type=None,
            confidence=0.3,
            context_analysis={},
            metadata={"source": "default"},
        )

    def _create_default_etl_instruction(
        self, understanding: PlaceholderUnderstanding
    ) -> ETLInstruction:
        """创建默认ETL指令"""
        return ETLInstruction(
            instruction_id=f"default_etl_{hash(understanding.placeholder)}",
            query_type="select",
            source_tables=[],
            target_fields=[],
            filters=[],
            aggregations=[],
            calculations=[],
            transformations=[],
            output_format="scalar",
            execution_order=1,
            dependencies=[],
        )

    def _summarize_schema(self, schema: Dict[str, Any]) -> str:
        """总结数据源结构"""
        summary_parts = []

        if "tables" in schema:
            tables = schema["tables"][:5]  # 限制表数量
            summary_parts.append(f"表: {', '.join(tables)}")

        if "columns" in schema:
            columns = schema["columns"][:10]  # 限制列数量
            summary_parts.append(f"列: {', '.join(columns)}")

        return "; ".join(summary_parts)

    def _summarize_field_metadata(self, metadata: Dict[str, Any]) -> str:
        """总结字段元数据"""
        summary_parts = []

        for field, meta in list(metadata.items())[:10]:  # 限制字段数量
            if isinstance(meta, dict):
                field_type = meta.get("type", "unknown")
                summary_parts.append(f"{field}({field_type})")
            else:
                summary_parts.append(field)

        return ", ".join(summary_parts)

    def get_understanding_statistics(self) -> Dict[str, Any]:
        """获取理解统计信息"""
        if not self.understanding_cache:
            return {
                "total_understood": 0,
                "avg_confidence": 0.0,
                "type_distribution": {},
                "cache_size": 0,
            }

        understandings = list(self.understanding_cache.values())

        # 计算统计
        total = len(understandings)
        avg_confidence = sum(u.confidence for u in understandings) / total

        # 类型分布
        type_dist = {}
        for u in understandings:
            type_dist[u.type] = type_dist.get(u.type, 0) + 1

        return {
            "total_understood": total,
            "avg_confidence": round(avg_confidence, 3),
            "type_distribution": type_dist,
            "cache_size": len(self.understanding_cache),
            "llm_usage": self.ai_service.get_llm_usage_stats(24),
        }

    def clear_cache(self):
        """清除理解缓存"""
        self.understanding_cache.clear()
        logger.info("占位符理解缓存已清除")


# 便捷函数
def understand_placeholder_text(
    text: str,
    db: Session,
    available_fields: Optional[List[str]] = None,
    data_source_schema: Optional[Dict[str, Any]] = None,
) -> List[PlaceholderUnderstanding]:
    """
    理解文本中所有占位符的便捷函数

    Args:
        text: 包含占位符的文本
        db: 数据库会话
        available_fields: 可用字段列表
        data_source_schema: 数据源结构

    Returns:
        占位符理解结果列表
    """
    service = LLMPlaceholderService(db)

    # 提取占位符
    processor = PlaceholderProcessor()
    placeholder_matches = processor.extract_placeholders(text)

    # 批量理解
    return service.batch_understand_placeholders(
        placeholder_matches, available_fields, data_source_schema
    )
