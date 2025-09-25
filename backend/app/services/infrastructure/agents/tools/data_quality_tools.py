"""
数据质量检查工具

提供数据质量验证和分析功能
"""

import logging
from typing import Dict, Any, List

from .base import Tool


class DataQualityTool(Tool):
    """数据质量检查工具"""

    def __init__(self, container):
        super().__init__()
        self.name = "data.quality"
        self.description = "执行数据质量检查和验证"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据质量检查"""
        try:
            # 从执行结果中获取数据
            execution_result = input_data.get("execution_result", {})
            rows = execution_result.get("rows", input_data.get("rows", []))
            columns = execution_result.get("columns", input_data.get("columns", []))

            # 如果直接传入了数据
            if not rows and input_data.get("data"):
                data = input_data["data"]
                if isinstance(data, list) and len(data) > 0:
                    if isinstance(data[0], dict):
                        # 字典格式数据
                        columns = list(data[0].keys())
                        rows = [[item[col] for col in columns] for item in data]
                    else:
                        # 列表格式数据
                        rows = data

            quality_result = self._check_data_quality(rows, columns, input_data)

            return {
                "success": True,
                "quality_score": quality_result["score"],
                "issues": quality_result["issues"],
                "statistics": quality_result["statistics"],
                "recommendations": quality_result["recommendations"]
            }

        except Exception as e:
            self._logger.error(f"数据质量检查失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _check_data_quality(self, rows: List[List], columns: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据质量检查"""
        issues = []
        recommendations = []
        score = 1.0  # 初始满分

        # 基础统计
        total_rows = len(rows)
        total_columns = len(columns)

        statistics = {
            "total_rows": total_rows,
            "total_columns": total_columns,
            "empty_cells": 0,
            "null_values": 0,
            "data_types": {}
        }

        # 检查数据量 - 添加空值处理
        constraints = context.get("constraints", {})
        min_rows = constraints.get("quality_min_rows")

        # 确保min_rows是有效的数字
        if min_rows is None:
            min_rows = 1  # 默认最小行数
        elif not isinstance(min_rows, int):
            try:
                min_rows = int(min_rows)
            except (ValueError, TypeError):
                self._logger.warning(f"Invalid quality_min_rows value: {min_rows}, using default 1")
                min_rows = 1

        if total_rows < min_rows:
            issues.append(f"数据行数不足: {total_rows} < {min_rows}")
            score -= 0.3

        # 检查空数据
        if total_rows == 0:
            issues.append("查询结果为空")
            score = 0.0
            return {
                "score": score,
                "issues": issues,
                "statistics": statistics,
                "recommendations": ["检查查询条件", "确认数据源连接"]
            }

        # 检查列数据
        empty_cells = 0
        null_values = 0

        for row_idx, row in enumerate(rows):
            if len(row) != total_columns:
                issues.append(f"第 {row_idx + 1} 行列数不匹配: {len(row)} != {total_columns}")
                score -= 0.1

            for col_idx, cell_value in enumerate(row):
                if cell_value is None:
                    null_values += 1
                elif str(cell_value).strip() == "":
                    empty_cells += 1

        statistics["empty_cells"] = empty_cells
        statistics["null_values"] = null_values

        # 空值检查
        total_cells = total_rows * total_columns
        if total_cells > 0:
            null_ratio = (null_values + empty_cells) / total_cells
            if null_ratio > 0.5:
                issues.append(f"空值比例过高: {null_ratio:.1%}")
                score -= 0.2
            elif null_ratio > 0.2:
                issues.append(f"空值比例较高: {null_ratio:.1%}")
                score -= 0.1

        # 数据类型分析
        if rows and columns:
            for col_idx, col_name in enumerate(columns):
                sample_values = []
                for row in rows[:10]:  # 采样前10行
                    if col_idx < len(row) and row[col_idx] is not None:
                        sample_values.append(row[col_idx])

                if sample_values:
                    detected_type = self._detect_data_type(sample_values)
                    statistics["data_types"][col_name] = detected_type

        # 数据一致性检查
        if total_rows > 1:
            consistency_score = self._check_data_consistency(rows, columns)
            if consistency_score < 0.8:
                issues.append("数据一致性较差")
                score -= 0.1

        # 生成建议
        if empty_cells > 0 or null_values > 0:
            recommendations.append("考虑处理空值和NULL值")
        if total_rows < 10:
            recommendations.append("数据量较少，可能需要扩大查询范围")
        if len(issues) == 0:
            recommendations.append("数据质量良好")

        # 确保分数在合理范围内
        score = max(0.0, min(1.0, score))

        return {
            "score": round(score, 2),
            "issues": issues,
            "statistics": statistics,
            "recommendations": recommendations
        }

    def _detect_data_type(self, sample_values: List) -> str:
        """检测数据类型"""
        if not sample_values:
            return "unknown"

        # 统计不同类型的出现次数
        type_counts = {"int": 0, "float": 0, "string": 0, "boolean": 0, "date": 0}

        for value in sample_values:
            if isinstance(value, bool):
                type_counts["boolean"] += 1
            elif isinstance(value, int):
                type_counts["int"] += 1
            elif isinstance(value, float):
                type_counts["float"] += 1
            elif isinstance(value, str):
                # 尝试解析为数字
                try:
                    float(value)
                    if "." in value:
                        type_counts["float"] += 1
                    else:
                        type_counts["int"] += 1
                except ValueError:
                    # 尝试解析为日期
                    if self._is_date_string(value):
                        type_counts["date"] += 1
                    else:
                        type_counts["string"] += 1
            else:
                type_counts["string"] += 1

        # 返回出现最多的类型
        return max(type_counts, key=type_counts.get)

    def _is_date_string(self, value: str) -> bool:
        """检查是否为日期字符串"""
        import re

        # 简单的日期格式匹配
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
        ]

        for pattern in date_patterns:
            if re.match(pattern, value.strip()):
                return True

        return False

    def _check_data_consistency(self, rows: List[List], columns: List[str]) -> float:
        """检查数据一致性"""
        if not rows or not columns:
            return 0.0

        consistency_scores = []

        # 检查每列的数据一致性
        for col_idx in range(len(columns)):
            col_values = []
            for row in rows:
                if col_idx < len(row) and row[col_idx] is not None:
                    col_values.append(type(row[col_idx]))

            if col_values:
                # 计算类型一致性
                most_common_type = max(set(col_values), key=col_values.count)
                consistency = col_values.count(most_common_type) / len(col_values)
                consistency_scores.append(consistency)

        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.0