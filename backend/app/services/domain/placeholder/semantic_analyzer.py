"""
占位符语义分析器

专门用于深度理解占位符的语义含义，特别是时间相关的占位符
"""

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PlaceholderSemanticType(Enum):
    """占位符语义类型"""

    TEMPORAL = "temporal"  # 时间相关
    STATISTICAL = "statistical"  # 统计相关
    DIMENSIONAL = "dimensional"  # 维度相关
    IDENTIFIER = "identifier"  # 标识相关
    METRIC = "metric"  # 指标相关
    FILTER = "filter"  # 过滤相关
    UNKNOWN = "unknown"  # 未知类型


class TemporalSubType(Enum):
    """时间子类型"""

    DATE_START = "date_start"  # 开始日期
    DATE_END = "date_end"  # 结束日期
    PERIOD = "period"  # 周期
    YEAR = "year"  # 年份
    MONTH = "month"  # 月份
    DAY = "day"  # 日期
    DATETIME = "datetime"  # 日期时间
    TIME_RANGE = "time_range"  # 时间范围


@dataclass
class SemanticAnalysisResult:
    """语义分析结果"""

    primary_type: PlaceholderSemanticType
    sub_type: Optional[str] = None
    confidence: float = 0.0
    keywords: List[str] = None
    data_intent: str = ""
    sql_hint: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.metadata is None:
            self.metadata = {}


class PlaceholderSemanticAnalyzer:
    """占位符语义分析器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._init_patterns()

    def _init_patterns(self):
        """初始化语义模式"""

        # 时间相关模式
        self.temporal_patterns = {
            "start_date": [
                r"开始日期|起始日期|开始时间|统计开始|起始时间",
                r"start.*date|begin.*date|from.*date|start.*time",
                r"周期.*开始|期间.*开始",
            ],
            "end_date": [
                r"结束日期|终止日期|结束时间|统计结束|截止日期",
                r"end.*date|finish.*date|to.*date|end.*time|until.*date",
                r"周期.*结束|期间.*结束",
            ],
            "period": [r"周期|期间|时间段|时段", r"period|duration|timespan|interval"],
            "year": [r"年份|年度|年", r"year|yearly|annual"],
            "month": [r"月份|月度|月", r"month|monthly"],
            "day": [r"日期|日|天", r"day|date|daily"],
        }

        # 统计相关模式
        self.statistical_patterns = {
            "count": [r"总数|数量|个数|条数|计数", r"count|total|number|quantity"],
            "sum": [r"总计|合计|总和|求和", r"sum|total|aggregate"],
            "average": [r"平均|均值|平均数", r"average|avg|mean"],
            "percentage": [r"百分比|占比|比例", r"percentage|percent|ratio|proportion"],
        }

        # 维度相关模式
        self.dimensional_patterns = {
            "region": [r"地区|区域|城市|省份|地域", r"region|area|city|province|location"],
            "category": [r"类别|分类|种类", r"category|type|classification"],
        }

    def analyze(self, placeholder_text: str, context: Dict[str, Any] = None) -> SemanticAnalysisResult:
        """分析占位符语义"""

        self.logger.debug(f"开始语义分析: {placeholder_text}")

        # 标准化文本
        normalized_text = self._normalize_text(placeholder_text)

        # 提取关键词
        keywords = self._extract_keywords(normalized_text)

        # 识别主要类型
        primary_type, confidence, sub_type = self._identify_primary_type(normalized_text, keywords)

        # 生成数据意图
        data_intent = self._generate_data_intent(primary_type, sub_type, keywords, normalized_text)

        # 生成SQL提示
        sql_hint = self._generate_sql_hint(primary_type, sub_type, keywords)

        # 构建元数据
        metadata = self._build_metadata(normalized_text, keywords, context or {})

        result = SemanticAnalysisResult(
            primary_type=primary_type,
            sub_type=sub_type,
            confidence=confidence,
            keywords=keywords,
            data_intent=data_intent,
            sql_hint=sql_hint,
            metadata=metadata,
        )

        self.logger.debug(f"语义分析完成: {result}")
        return result

    def _normalize_text(self, text: str) -> str:
        """标准化文本"""
        if not text:
            return ""

        # 去掉各种括号和标记
        normalized = re.sub(r"[{\[\(<>）】）]+|[}\]\)>（【（]+", "", text)
        normalized = normalized.strip()

        return normalized

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        keywords = []

        # 中文词汇
        chinese_words = re.findall(r"[\u4e00-\u9fff]+", text)
        keywords.extend(chinese_words)

        # 英文单词
        english_words = re.findall(r"[a-zA-Z]+", text)
        keywords.extend([word.lower() for word in english_words])

        # 去重并过滤短词
        keywords = list(set([kw for kw in keywords if len(kw) >= 2]))

        return keywords

    def _identify_primary_type(
        self, text: str, keywords: List[str]
    ) -> Tuple[PlaceholderSemanticType, float, Optional[str]]:
        """识别主要类型"""

        # 检查时间类型
        temporal_result = self._check_temporal_type(text, keywords)
        if temporal_result[1] > 0.7:  # 置信度阈值
            return PlaceholderSemanticType.TEMPORAL, temporal_result[1], temporal_result[0]

        # 检查统计类型
        statistical_result = self._check_statistical_type(text, keywords)
        if statistical_result[1] > 0.7:
            return PlaceholderSemanticType.STATISTICAL, statistical_result[1], statistical_result[0]

        # 检查维度类型
        dimensional_result = self._check_dimensional_type(text, keywords)
        if dimensional_result[1] > 0.7:
            return PlaceholderSemanticType.DIMENSIONAL, dimensional_result[1], dimensional_result[0]

        # 默认返回最高置信度的结果
        all_results = [
            (PlaceholderSemanticType.TEMPORAL, temporal_result[1], temporal_result[0]),
            (PlaceholderSemanticType.STATISTICAL, statistical_result[1], statistical_result[0]),
            (PlaceholderSemanticType.DIMENSIONAL, dimensional_result[1], dimensional_result[0]),
        ]

        best_result = max(all_results, key=lambda x: x[1])
        if best_result[1] > 0.3:  # 最低置信度
            return best_result

        return PlaceholderSemanticType.UNKNOWN, 0.1, None

    def _check_temporal_type(self, text: str, keywords: List[str]) -> Tuple[Optional[str], float]:
        """检查时间类型"""

        max_confidence = 0.0
        best_sub_type = None

        for sub_type, patterns in self.temporal_patterns.items():
            confidence = 0.0

            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    confidence += 0.3

            # 关键词匹配
            for keyword in keywords:
                for pattern in patterns:
                    if re.search(pattern, keyword, re.IGNORECASE):
                        confidence += 0.2

            # 特殊加权
            if sub_type == "start_date" and ("开始" in text or "起始" in text or "start" in text.lower()):
                confidence += 0.3
            elif sub_type == "end_date" and ("结束" in text or "终止" in text or "end" in text.lower()):
                confidence += 0.3
            elif sub_type == "period" and "周期" in text:
                confidence += 0.4

            if confidence > max_confidence:
                max_confidence = confidence
                best_sub_type = sub_type

        return best_sub_type, min(max_confidence, 1.0)

    def _check_statistical_type(self, text: str, keywords: List[str]) -> Tuple[Optional[str], float]:
        """检查统计类型"""

        max_confidence = 0.0
        best_sub_type = None

        for sub_type, patterns in self.statistical_patterns.items():
            confidence = 0.0

            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    confidence += 0.4

            for keyword in keywords:
                for pattern in patterns:
                    if re.search(pattern, keyword, re.IGNORECASE):
                        confidence += 0.3

            if confidence > max_confidence:
                max_confidence = confidence
                best_sub_type = sub_type

        return best_sub_type, min(max_confidence, 1.0)

    def _check_dimensional_type(self, text: str, keywords: List[str]) -> Tuple[Optional[str], float]:
        """检查维度类型"""

        max_confidence = 0.0
        best_sub_type = None

        for sub_type, patterns in self.dimensional_patterns.items():
            confidence = 0.0

            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    confidence += 0.4

            for keyword in keywords:
                for pattern in patterns:
                    if re.search(pattern, keyword, re.IGNORECASE):
                        confidence += 0.3

            if confidence > max_confidence:
                max_confidence = confidence
                best_sub_type = sub_type

        return best_sub_type, min(max_confidence, 1.0)

    def _generate_data_intent(
        self, primary_type: PlaceholderSemanticType, sub_type: Optional[str], keywords: List[str], text: str
    ) -> str:
        """生成数据意图描述"""

        if primary_type == PlaceholderSemanticType.TEMPORAL:
            if sub_type == "start_date":
                return f"获取统计周期的开始日期，用于时间范围过滤的起始点"
            elif sub_type == "end_date":
                return f"获取统计周期的结束日期，用于时间范围过滤的终止点"
            elif sub_type == "period":
                return f"获取统计周期标识，可能用于时间维度分组或过滤"
            elif sub_type == "year":
                return f"获取年份信息，用于按年度过滤或分组统计"
            elif sub_type == "month":
                return f"获取月份信息，用于按月度过滤或分组统计"
            else:
                return f"获取时间相关信息用于时间维度分析"

        elif primary_type == PlaceholderSemanticType.STATISTICAL:
            if sub_type == "count":
                return f"计算记录总数或数量统计"
            elif sub_type == "sum":
                return f"计算数值字段的总和或累计值"
            elif sub_type == "average":
                return f"计算平均值或均值统计"
            elif sub_type == "percentage":
                return f"计算百分比或占比统计"
            else:
                return f"执行统计计算获取汇总指标"

        elif primary_type == PlaceholderSemanticType.DIMENSIONAL:
            if sub_type == "region":
                return f"获取地区或区域维度信息用于地域分析"
            elif sub_type == "category":
                return f"获取分类或类别维度信息用于分组分析"
            else:
                return f"获取维度属性信息用于多维分析"

        else:
            return f"根据占位符文本'{text}'提取相关数据信息"

    def _generate_sql_hint(
        self, primary_type: PlaceholderSemanticType, sub_type: Optional[str], keywords: List[str]
    ) -> str:
        """生成SQL提示"""

        if primary_type == PlaceholderSemanticType.TEMPORAL:
            if sub_type == "start_date":
                return "SELECT date_value FROM time_dimension WHERE time_type = 'period_start'"
            elif sub_type == "end_date":
                return "SELECT date_value FROM time_dimension WHERE time_type = 'period_end'"
            elif sub_type == "year":
                return "SELECT YEAR(date_column) FROM target_table"
            elif sub_type == "month":
                return "SELECT MONTH(date_column) FROM target_table"
            else:
                return "SELECT date_column FROM target_table WHERE date_condition"

        elif primary_type == PlaceholderSemanticType.STATISTICAL:
            if sub_type == "count":
                return "SELECT COUNT(*) FROM target_table"
            elif sub_type == "sum":
                return "SELECT SUM(numeric_column) FROM target_table"
            elif sub_type == "average":
                return "SELECT AVG(numeric_column) FROM target_table"
            elif sub_type == "percentage":
                return "SELECT (COUNT(*) * 100.0 / total_count) as percentage FROM target_table"
            else:
                return "SELECT aggregation_function(column) FROM target_table"

        elif primary_type == PlaceholderSemanticType.DIMENSIONAL:
            if sub_type == "region":
                return "SELECT region_name FROM target_table"
            elif sub_type == "category":
                return "SELECT category_name FROM target_table"
            else:
                return "SELECT dimension_column FROM target_table"

        else:
            return "SELECT relevant_columns FROM target_table WHERE conditions"

    def _build_metadata(self, text: str, keywords: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """构建元数据"""

        metadata = {
            "original_text": text,
            "normalized_text": text,
            "extracted_keywords": keywords,
            "analysis_timestamp": datetime.now().isoformat(),
            "context_keys": list(context.keys()) if context else [],
        }

        # 检测特殊模式
        patterns = {
            "has_colon": ":" in text,
            "has_chinese": bool(re.search(r"[\u4e00-\u9fff]", text)),
            "has_english": bool(re.search(r"[a-zA-Z]", text)),
            "has_numbers": bool(re.search(r"\d", text)),
            "length": len(text),
        }

        metadata["text_patterns"] = patterns

        return metadata


def create_semantic_analyzer() -> PlaceholderSemanticAnalyzer:
    """创建语义分析器实例"""
    return PlaceholderSemanticAnalyzer()
