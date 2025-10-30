"""
智能表检测工具

基于模板占位符信息，检测任务是否只使用单张数据表，用于优化Schema加载策略
"""

import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TableDetectionResult:
    """表检测结果"""
    is_single_table: bool           # 是否为单表场景
    primary_table: Optional[str]     # 主要使用的表名
    all_tables: Set[str]             # 涉及的所有表名
    confidence: float                # 检测置信度（0-1）
    recommendation: str              # 优化建议
    details: Dict[str, Any]          # 详细信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_single_table": self.is_single_table,
            "primary_table": self.primary_table,
            "all_tables": list(self.all_tables),
            "confidence": self.confidence,
            "recommendation": self.recommendation,
            "details": self.details
        }


class TableDetector:
    """表检测器 - 智能分析任务使用的数据表"""

    def __init__(self):
        self.logger = logger

    def detect_from_placeholders(
        self,
        placeholders: List[Any],
        template_content: Optional[str] = None
    ) -> TableDetectionResult:
        """
        从占位符列表中检测表使用情况

        Args:
            placeholders: 占位符列表（TemplatePlaceholder对象）
            template_content: 模板内容（可选，用于辅助分析）

        Returns:
            TableDetectionResult: 检测结果
        """
        if not placeholders:
            return TableDetectionResult(
                is_single_table=False,
                primary_table=None,
                all_tables=set(),
                confidence=0.0,
                recommendation="无占位符，跳过优化",
                details={"reason": "no_placeholders"}
            )

        # 收集所有占位符的 target_table
        table_names: List[str] = []
        analyzed_count = 0
        total_count = len(placeholders)

        for ph in placeholders:
            # 检查是否已分析且有 target_table
            target_table = getattr(ph, 'target_table', None)
            if target_table and isinstance(target_table, str) and target_table.strip():
                table_names.append(target_table.strip())
                analyzed_count += 1

        # 统计表频率
        if not table_names:
            # 没有占位符有 target_table（可能都未分析）
            return TableDetectionResult(
                is_single_table=False,
                primary_table=None,
                all_tables=set(),
                confidence=0.0,
                recommendation="占位符未分析，无法优化。建议先分析第一个占位符。",
                details={
                    "reason": "no_target_table",
                    "analyzed_count": analyzed_count,
                    "total_count": total_count
                }
            )

        unique_tables = set(table_names)
        table_frequency = {table: table_names.count(table) for table in unique_tables}
        primary_table = max(table_frequency, key=table_frequency.get)

        # 判断是否为单表场景
        is_single_table = len(unique_tables) == 1

        # 计算置信度
        confidence = analyzed_count / total_count if total_count > 0 else 0.0

        # 生成建议
        if is_single_table:
            recommendation = f"✅ 单表场景检测成功！建议启用单表优化模式，只加载表 '{primary_table}' 的 schema，预计节省 60-70% token"
        else:
            # 多表场景，但检查是否有主导表（占比>80%）
            primary_table_ratio = table_frequency[primary_table] / len(table_names)
            if primary_table_ratio >= 0.8:
                recommendation = (
                    f"⚠️ 多表场景，但主表 '{primary_table}' 占比 {primary_table_ratio*100:.1f}%。"
                    f"建议：可尝试单表优化（风险低），或使用多表模式（更安全）"
                )
            else:
                recommendation = (
                    f"❌ 多表场景检测：涉及 {len(unique_tables)} 张表。"
                    f"建议：使用多表模式，加载所有表 schema"
                )

        details = {
            "analyzed_count": analyzed_count,
            "total_count": total_count,
            "analysis_coverage": f"{analyzed_count}/{total_count} ({confidence*100:.1f}%)",
            "table_frequency": table_frequency,
            "primary_table_usage": f"{table_frequency.get(primary_table, 0)}/{len(table_names)}"
        }

        self.logger.info(
            f"📊 表检测结果: is_single_table={is_single_table}, "
            f"primary_table={primary_table}, "
            f"all_tables={unique_tables}, "
            f"confidence={confidence:.2f}"
        )

        return TableDetectionResult(
            is_single_table=is_single_table,
            primary_table=primary_table,
            all_tables=unique_tables,
            confidence=confidence,
            recommendation=recommendation,
            details=details
        )

    def detect_from_first_placeholder_analysis(
        self,
        placeholder_name: str,
        placeholder_text: str,
        analyzed_result: Dict[str, Any]
    ) -> Optional[str]:
        """
        从第一个占位符的分析结果中提取表名

        这用于在占位符还未批量分析时的快速检测

        Args:
            placeholder_name: 占位符名称
            placeholder_text: 占位符文本
            analyzed_result: Agent分析结果

        Returns:
            Optional[str]: 检测到的表名，如果无法确定则返回 None
        """
        # 尝试从分析结果中提取 target_table
        target_table = analyzed_result.get("target_table")
        if target_table and isinstance(target_table, str):
            self.logger.info(
                f"✅ 从第一个占位符 '{placeholder_name}' 分析结果中检测到目标表: {target_table}"
            )
            return target_table.strip()

        # 尝试从 SQL 中提取表名（简单正则匹配）
        generated_sql = analyzed_result.get("generated_sql", {}).get("sql", "")
        if generated_sql:
            table_name = self._extract_table_from_sql(generated_sql)
            if table_name:
                self.logger.info(
                    f"✅ 从第一个占位符 '{placeholder_name}' 的 SQL 中提取表名: {table_name}"
                )
                return table_name

        self.logger.warning(
            f"⚠️ 无法从第一个占位符 '{placeholder_name}' 的分析结果中提取表名"
        )
        return None

    def _extract_table_from_sql(self, sql: str) -> Optional[str]:
        """
        从 SQL 中提取表名（简单实现）

        Args:
            sql: SQL 查询语句

        Returns:
            Optional[str]: 提取到的表名
        """
        import re

        # 匹配 FROM 子句中的表名
        # 支持：FROM table_name, FROM `table_name`, FROM "table_name", FROM schema.table_name
        patterns = [
            r'FROM\s+`?([a-zA-Z0-9_]+)`?',      # FROM table_name 或 FROM `table_name`
            r'FROM\s+"?([a-zA-Z0-9_]+)"?',      # FROM "table_name"
            r'FROM\s+\w+\.`?([a-zA-Z0-9_]+)`?', # FROM schema.table_name
        ]

        sql_upper = sql.upper()
        for pattern in patterns:
            match = re.search(pattern, sql_upper, re.IGNORECASE)
            if match:
                return match.group(1).lower()

        return None


def create_table_detector() -> TableDetector:
    """创建表检测器实例（工厂函数）"""
    return TableDetector()
