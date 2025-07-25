"""
智能ETL执行器

基于占位符需求和字段匹配结果，智能生成和执行ETL操作。
支持动态查询生成、时间过滤、区域过滤和聚合计算。
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ....core.config import settings
from ....crud.crud_data_source import crud_data_source
from ....db.session import get_db_session
from ....models.data_source import DataSource
from ...data_source_service import DataSourceService
from ...intelligent_placeholder.matcher import FieldMatchingResult

logger = logging.getLogger(__name__)


@dataclass
class TimeFilterConfig:
    """时间过滤配置"""

    field: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    period: str = "monthly"  # daily, weekly, monthly, yearly
    relative_period: Optional[str] = None  # "last_month", "this_year", etc.


@dataclass
class RegionFilterConfig:
    """区域过滤配置"""

    field: str
    region_value: str
    region_type: str = "exact"  # exact, contains, starts_with
    region_level: str = "province"  # province, city, district


@dataclass
class AggregationConfig:
    """聚合配置"""

    function: str  # sum, avg, count, min, max
    field: str
    group_by: Optional[List[str]] = None
    having_condition: Optional[str] = None


@dataclass
class ETLInstructions:
    """ETL指令"""

    instruction_id: str
    query_type: str  # select, aggregate, select_for_chart
    source_fields: List[str]
    filters: List[Dict[str, Any]]
    aggregations: List[AggregationConfig]
    transformations: List[Dict[str, Any]]
    time_config: Optional[TimeFilterConfig] = None
    region_config: Optional[RegionFilterConfig] = None
    output_format: str = "dataframe"  # dataframe, scalar, array
    performance_hints: List[str] = None


@dataclass
class ProcessedData:
    """处理后的数据"""

    raw_data: Any
    processed_value: Any
    metadata: Dict[str, Any]
    processing_time: float
    confidence: float
    query_executed: str
    rows_processed: int


class IntelligentETLExecutor:
    """智能ETL执行器"""

    def __init__(self):
        self.data_source_service = DataSourceService()

    async def execute_etl(
        self,
        instructions: ETLInstructions,
        data_source_id: int,
        task_config: Optional[Dict[str, Any]] = None,
    ) -> ProcessedData:
        """
        执行ETL处理

        Args:
            instructions: ETL指令
            data_source_id: 数据源ID
            task_config: 任务配置（包含时间范围、区域等）

        Returns:
            处理后的数据
        """
        start_time = datetime.now()

        try:
            logger.info(f"开始执行智能ETL，指令ID: {instructions.instruction_id}")

            # 1. 获取数据源信息
            with get_db_session() as db:
                data_source = crud_data_source.get(db, id=data_source_id)
                if not data_source:
                    raise ValueError(f"数据源 {data_source_id} 不存在")

            # 2. 生成动态查询
            query = await self._generate_dynamic_query(
                instructions, data_source, task_config
            )
            logger.info(f"生成的查询: {query}")

            # 3. 执行查询
            raw_data = await self._execute_query(query, data_source)
            logger.info(
                f"查询执行完成，获得 {len(raw_data) if isinstance(raw_data, pd.DataFrame) else 'N/A'} 行数据"
            )

            # 4. 应用数据转换
            processed_data = await self._apply_transformations(
                raw_data, instructions.transformations
            )

            # 5. 格式化输出
            final_value = await self._format_output(
                processed_data, instructions.output_format
            )

            # 6. 计算处理时间和置信度
            processing_time = (datetime.now() - start_time).total_seconds()
            confidence = self._calculate_confidence(instructions, raw_data, final_value)

            db.close()

            return ProcessedData(
                raw_data=raw_data,
                processed_value=final_value,
                metadata={
                    "instruction_id": instructions.instruction_id,
                    "data_source_id": data_source_id,
                    "query_type": instructions.query_type,
                    "filters_applied": len(instructions.filters),
                    "aggregations_applied": len(instructions.aggregations),
                    "transformations_applied": len(instructions.transformations),
                },
                processing_time=processing_time,
                confidence=confidence,
                query_executed=query,
                rows_processed=(
                    len(raw_data) if isinstance(raw_data, pd.DataFrame) else 1
                ),
            )

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"ETL执行失败: {e}")

            if "db" in locals():
                db.close()

            return ProcessedData(
                raw_data=None,
                processed_value=None,
                metadata={"error": str(e)},
                processing_time=processing_time,
                confidence=0.0,
                query_executed="",
                rows_processed=0,
            )

    async def _generate_dynamic_query(
        self,
        instructions: ETLInstructions,
        data_source: DataSource,
        task_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """生成动态查询"""

        # 基础查询构建
        if data_source.source_type == "sql":
            return await self._generate_sql_query(
                instructions, data_source, task_config
            )
        else:
            # 对于非SQL数据源，生成pandas操作指令
            return await self._generate_pandas_operations(
                instructions, data_source, task_config
            )

    async def _generate_sql_query(
        self,
        instructions: ETLInstructions,
        data_source: DataSource,
        task_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """生成SQL查询"""

        # 1. SELECT子句
        if instructions.query_type == "aggregate":
            select_parts = []
            for agg in instructions.aggregations:
                agg_expr = f"{agg.function.upper()}({agg.field})"
                select_parts.append(agg_expr)

            # 添加GROUP BY字段
            if instructions.aggregations and instructions.aggregations[0].group_by:
                select_parts.extend(instructions.aggregations[0].group_by)

            select_clause = "SELECT " + ", ".join(select_parts)
        else:
            if instructions.source_fields:
                select_clause = f"SELECT {', '.join(instructions.source_fields)}"
            else:
                select_clause = "SELECT *"

        # 2. FROM子句
        table_name = data_source.wide_table_name or "main_table"
        from_clause = f"FROM {table_name}"

        # 3. WHERE子句
        where_conditions = []

        # 应用过滤条件
        for filter_config in instructions.filters:
            condition = self._build_filter_condition(filter_config)
            if condition:
                where_conditions.append(condition)

        # 应用时间过滤
        if instructions.time_config:
            time_condition = await self._build_time_filter(
                instructions.time_config, task_config
            )
            if time_condition:
                where_conditions.append(time_condition)

        # 应用区域过滤
        if instructions.region_config:
            region_condition = await self._build_region_filter(
                instructions.region_config, task_config
            )
            if region_condition:
                where_conditions.append(region_condition)

        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)

        # 4. GROUP BY子句
        group_by_clause = ""
        if instructions.query_type == "aggregate" and instructions.aggregations:
            group_by_fields = instructions.aggregations[0].group_by
            if group_by_fields:
                group_by_clause = f"GROUP BY {', '.join(group_by_fields)}"

        # 5. HAVING子句
        having_clause = ""
        if instructions.aggregations and instructions.aggregations[0].having_condition:
            having_clause = f"HAVING {instructions.aggregations[0].having_condition}"

        # 6. ORDER BY子句（可选）
        order_by_clause = ""
        if instructions.query_type == "select_for_chart":
            # 为图表数据添加排序
            if instructions.source_fields:
                order_by_clause = f"ORDER BY {instructions.source_fields[0]}"

        # 组合查询
        query_parts = [select_clause, from_clause]
        if where_clause:
            query_parts.append(where_clause)
        if group_by_clause:
            query_parts.append(group_by_clause)
        if having_clause:
            query_parts.append(having_clause)
        if order_by_clause:
            query_parts.append(order_by_clause)

        return " ".join(query_parts)

    async def _generate_pandas_operations(
        self,
        instructions: ETLInstructions,
        data_source: DataSource,
        task_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """为非SQL数据源生成pandas操作指令"""

        operations = []

        # 1. 数据加载
        if data_source.source_type == "csv":
            operations.append(f"df = pd.read_csv('{data_source.connection_string}')")
        elif data_source.source_type == "api":
            operations.append(f"df = fetch_api_data('{data_source.api_url}')")

        # 2. 字段选择
        if instructions.source_fields:
            fields_str = str(instructions.source_fields)
            operations.append(f"df = df[{fields_str}]")

        # 3. 过滤条件
        for filter_config in instructions.filters:
            condition = self._build_filter_condition(filter_config)
            if condition:
                operations.append(f"df = df[{condition}]")

        # 4. 时间过滤
        if instructions.time_config:
            time_filter = await self._build_pandas_time_filter(
                instructions.time_config, task_config
            )
            if time_filter:
                operations.append(time_filter)

        # 5. 聚合操作
        if instructions.query_type == "aggregate" and instructions.aggregations:
            agg_config = instructions.aggregations[0]
            if agg_config.group_by:
                group_fields = str(agg_config.group_by)
                operations.append(
                    f"df = df.groupby({group_fields}).{agg_config.function}()"
                )
            else:
                operations.append(
                    f"result = df['{agg_config.field}'].{agg_config.function}()"
                )

        return "; ".join(operations)

    def _build_filter_condition(self, filter_config: Dict[str, Any]) -> str:
        """构建过滤条件"""

        column = filter_config.get("column", "")
        operator = filter_config.get("operator", "=")
        value = filter_config.get("value", "")

        if not column or not value:
            return ""

        # 处理不同的操作符
        if operator == "=":
            return f"{column} = '{value}'"
        elif operator == "!=":
            return f"{column} != '{value}'"
        elif operator == ">":
            return f"{column} > '{value}'"
        elif operator == ">=":
            return f"{column} >= '{value}'"
        elif operator == "<":
            return f"{column} < '{value}'"
        elif operator == "<=":
            return f"{column} <= '{value}'"
        elif operator == "LIKE":
            return f"{column} LIKE '%{value}%'"
        elif operator == "IN":
            if isinstance(value, list):
                values_str = "', '".join(str(v) for v in value)
                return f"{column} IN ('{values_str}')"

        return f"{column} = '{value}'"

    async def _build_time_filter(
        self,
        time_config: TimeFilterConfig,
        task_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建时间过滤条件"""

        if not time_config.field:
            return ""

        conditions = []

        # 使用任务配置中的时间范围
        if task_config and "time_range" in task_config:
            time_range = task_config["time_range"]
            start_date = time_range.get("start_date")
            end_date = time_range.get("end_date")
        else:
            start_date = time_config.start_date
            end_date = time_config.end_date

        # 处理相对时间周期
        if time_config.relative_period:
            start_date, end_date = await self._calculate_relative_period(
                time_config.relative_period
            )

        if start_date:
            conditions.append(f"{time_config.field} >= '{start_date}'")

        if end_date:
            conditions.append(f"{time_config.field} <= '{end_date}'")

        return " AND ".join(conditions)

    async def _build_region_filter(
        self,
        region_config: RegionFilterConfig,
        task_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建区域过滤条件"""

        if not region_config.field:
            return ""

        # 使用任务配置中的区域设置
        region_value = region_config.region_value
        if task_config and "region" in task_config:
            region_value = task_config["region"]

        # 根据匹配类型构建条件
        if region_config.region_type == "exact":
            return f"{region_config.field} = '{region_value}'"
        elif region_config.region_type == "contains":
            return f"{region_config.field} LIKE '%{region_value}%'"
        elif region_config.region_type == "starts_with":
            return f"{region_config.field} LIKE '{region_value}%'"

        return f"{region_config.field} = '{region_value}'"

    async def _calculate_relative_period(self, relative_period: str) -> tuple:
        """计算相对时间周期"""

        now = datetime.now()

        if relative_period == "last_month":
            # 上个月
            if now.month == 1:
                start_date = datetime(now.year - 1, 12, 1)
                end_date = datetime(now.year, 1, 1) - timedelta(days=1)
            else:
                start_date = datetime(now.year, now.month - 1, 1)
                if now.month == 12:
                    end_date = datetime(now.year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(now.year, now.month, 1) - timedelta(days=1)

        elif relative_period == "this_month":
            # 本月
            start_date = datetime(now.year, now.month, 1)
            if now.month == 12:
                end_date = datetime(now.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(now.year, now.month + 1, 1) - timedelta(days=1)

        elif relative_period == "this_year":
            # 今年
            start_date = datetime(now.year, 1, 1)
            end_date = datetime(now.year, 12, 31)

        elif relative_period == "last_year":
            # 去年
            start_date = datetime(now.year - 1, 1, 1)
            end_date = datetime(now.year - 1, 12, 31)

        else:
            # 默认为本月
            start_date = datetime(now.year, now.month, 1)
            if now.month == 12:
                end_date = datetime(now.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(now.year, now.month + 1, 1) - timedelta(days=1)

        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

    def _build_pandas_filter(self, filter_config: Dict[str, Any]) -> str:
        """构建pandas过滤条件"""

        column = filter_config.get("column", "")
        operator = filter_config.get("operator", "=")
        value = filter_config.get("value", "")

        if not column or not value:
            return ""

        # 处理不同的操作符
        if operator == "=":
            return f"df['{column}'] == '{value}'"
        elif operator == "!=":
            return f"df['{column}'] != '{value}'"
        elif operator == ">":
            return f"df['{column}'] > '{value}'"
        elif operator == ">=":
            return f"df['{column}'] >= '{value}'"
        elif operator == "<":
            return f"df['{column}'] < '{value}'"
        elif operator == "<=":
            return f"df['{column}'] <= '{value}'"
        elif operator == "LIKE":
            return f"df['{column}'].str.contains('{value}')"
        elif operator == "IN":
            if isinstance(value, list):
                return f"df['{column}'].isin({value})"

        return f"df['{column}'] == '{value}'"

    async def _build_pandas_time_filter(
        self,
        time_config: TimeFilterConfig,
        task_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建pandas时间过滤"""

        if not time_config.field:
            return ""

        operations = []

        # 确保时间字段是datetime类型
        operations.append(
            f"df['{time_config.field}'] = pd.to_datetime(df['{time_config.field}'])"
        )

        # 应用时间过滤
        if task_config and "time_range" in task_config:
            time_range = task_config["time_range"]
            start_date = time_range.get("start_date")
            end_date = time_range.get("end_date")
        else:
            start_date = time_config.start_date
            end_date = time_config.end_date

        if start_date:
            operations.append(f"df = df[df['{time_config.field}'] >= '{start_date}']")

        if end_date:
            operations.append(f"df = df[df['{time_config.field}'] <= '{end_date}']")

        return "; ".join(operations)

    async def _execute_query(self, query: str, data_source: DataSource) -> Any:
        """执行查询"""

        if data_source.source_type == "sql":
            # SQL查询
            engine = create_engine(data_source.connection_string)
            return pd.read_sql(text(query), engine)

        else:
            # 非SQL数据源，执行pandas操作
            return await self._execute_pandas_operations(query, data_source)

    async def _execute_pandas_operations(
        self, operations: str, data_source: DataSource
    ) -> pd.DataFrame:
        """执行pandas操作"""

        # 创建执行环境
        exec_globals = {"pd": pd, "datetime": datetime, "timedelta": timedelta}

        # 添加数据获取函数
        def fetch_api_data(url: str) -> pd.DataFrame:
            # 这里应该实现API数据获取逻辑
            # 暂时返回空DataFrame
            return pd.DataFrame()

        exec_globals["fetch_api_data"] = fetch_api_data

        # 执行操作
        exec(operations, exec_globals)

        # 返回结果
        if "df" in exec_globals:
            return exec_globals["df"]
        elif "result" in exec_globals:
            # 对于聚合结果，转换为DataFrame
            result = exec_globals["result"]
            return pd.DataFrame({"result": [result]})
        else:
            return pd.DataFrame()

    async def _apply_transformations(
        self, data: Any, transformations: List[Dict[str, Any]]
    ) -> Any:
        """应用数据转换"""

        if not transformations or data is None:
            return data

        transformed_data = data

        for transformation in transformations:
            transform_type = transformation.get("type", "")

            if transform_type == "cast":
                # 类型转换
                target_type = transformation.get("target_type", "string")
                field = transformation.get("field", "")

                if (
                    isinstance(transformed_data, pd.DataFrame)
                    and field in transformed_data.columns
                ):
                    if target_type == "integer":
                        transformed_data[field] = pd.to_numeric(
                            transformed_data[field], errors="coerce"
                        ).astype("Int64")
                    elif target_type == "float":
                        transformed_data[field] = pd.to_numeric(
                            transformed_data[field], errors="coerce"
                        )
                    elif target_type == "date":
                        transformed_data[field] = pd.to_datetime(
                            transformed_data[field], errors="coerce"
                        )
                    elif target_type == "string":
                        transformed_data[field] = transformed_data[field].astype(str)

            elif transform_type == "format":
                # 格式化
                field = transformation.get("field", "")
                format_pattern = transformation.get("pattern", "")

                if (
                    isinstance(transformed_data, pd.DataFrame)
                    and field in transformed_data.columns
                ):
                    if format_pattern:
                        # 应用格式化模式
                        transformed_data[field] = transformed_data[field].apply(
                            lambda x: format_pattern.format(x) if x is not None else x
                        )

            elif transform_type == "calculate":
                # 计算字段
                formula = transformation.get("formula", "")
                target_field = transformation.get("target_field", "calculated_field")

                if isinstance(transformed_data, pd.DataFrame) and formula:
                    try:
                        # 安全的表达式计算
                        transformed_data[target_field] = transformed_data.eval(formula)
                    except Exception as e:
                        logger.warning(f"计算字段失败: {e}")

        return transformed_data

    async def _format_output(self, data: Any, output_format: str) -> Any:
        """格式化输出"""

        if data is None:
            return None

        if output_format == "scalar":
            # 返回单个值
            if isinstance(data, pd.DataFrame):
                if len(data) == 1 and len(data.columns) == 1:
                    return data.iloc[0, 0]
                elif len(data) > 0:
                    return data.iloc[0, 0]  # 返回第一行第一列
            return data

        elif output_format == "array":
            # 返回数组
            if isinstance(data, pd.DataFrame):
                if len(data.columns) == 1:
                    return data.iloc[:, 0].tolist()
                else:
                    return data.to_dict(orient="records")
            return data

        elif output_format == "json":
            # 返回JSON
            if isinstance(data, pd.DataFrame):
                return data.to_dict(orient="records")
            return data

        else:
            # 默认返回DataFrame
            return data

    def _calculate_confidence(
        self, instructions: ETLInstructions, raw_data: Any, final_value: Any
    ) -> float:
        """计算处理置信度"""

        confidence = 1.0

        # 基于数据质量调整置信度
        if isinstance(raw_data, pd.DataFrame):
            if len(raw_data) == 0:
                confidence *= 0.1  # 无数据
            elif raw_data.isnull().sum().sum() > len(raw_data) * 0.5:
                confidence *= 0.7  # 数据缺失较多

        # 基于查询复杂度调整置信度
        complexity_score = (
            len(instructions.filters) * 0.1
            + len(instructions.aggregations) * 0.2
            + len(instructions.transformations) * 0.1
        )

        if complexity_score > 1.0:
            confidence *= 0.9  # 复杂查询降低置信度

        # 基于输出格式调整置信度
        if instructions.output_format == "scalar" and final_value is None:
            confidence *= 0.5  # 期望标量但返回空值

        return max(0.1, min(1.0, confidence))


# 创建全局实例
intelligent_etl_executor = IntelligentETLExecutor()
