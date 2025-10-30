from __future__ import annotations

from loom.interfaces.tool import BaseTool
"""
数据采样工具

从数据源中采样数据进行分析
支持多种采样策略和数据处理
"""


import logging
import random
import math
from typing import Any, Dict, List, Optional, Union, Literal
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field


from ...types import ToolCategory, ContextInfo

logger = logging.getLogger(__name__)


class SamplingStrategy(str, Enum):
    """采样策略"""
    RANDOM = "random"           # 随机采样
    SYSTEMATIC = "systematic"   # 系统采样
    STRATIFIED = "stratified"   # 分层采样
    CLUSTER = "cluster"         # 聚类采样
    CONVENIENCE = "convenience" # 便利采样


class DataType(str, Enum):
    """数据类型"""
    NUMERIC = "numeric"         # 数值型
    CATEGORICAL = "categorical" # 分类型
    TEXT = "text"              # 文本型
    DATETIME = "datetime"      # 日期时间型
    BOOLEAN = "boolean"        # 布尔型


@dataclass
class SamplingConfig:
    """采样配置"""
    strategy: SamplingStrategy
    sample_size: int
    random_seed: Optional[int] = None
    strata_column: Optional[str] = None
    cluster_column: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SamplingResult:
    """采样结果"""
    data: List[Dict[str, Any]]
    sample_size: int
    total_size: int
    sampling_rate: float
    strategy: SamplingStrategy
    columns: List[str]
    data_types: Dict[str, DataType]
    statistics: Dict[str, Any]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DataSamplerTool(BaseTool):
    """数据采样工具"""
    
    def __init__(self, container: Any):
        """
        Args:
            container: 服务容器
        """
        super().__init__()

        self.name = "data_sampler"

        self.category = ToolCategory.DATA

        self.description = "从数据源中采样数据进行分析" 
        self.container = container
        self._data_source_service = None
        
        # 使用 Pydantic 定义参数模式（args_schema）
        class DataSamplerArgs(BaseModel):
            sql: str = Field(description="要采样的 SQL 查询")
            connection_config: Dict[str, Any] = Field(description="数据源连接配置")
            strategy: Literal["random", "systematic", "stratified", "cluster", "convenience"] = Field(
                default="random", description="采样策略"
            )
            sample_size: int = Field(default=1000, description="采样大小")
            random_seed: Optional[int] = Field(default=None, description="随机种子")
            strata_column: Optional[str] = Field(default=None, description="分层列名（用于分层采样）")
            cluster_column: Optional[str] = Field(default=None, description="聚类列名（用于聚类采样）")
            max_total_size: int = Field(default=100000, description="最大总数据量")
            analyze_data_types: bool = Field(default=True, description="是否分析数据类型")

        self.args_schema = DataSamplerArgs
    
    async def _get_data_source_service(self):
        """获取数据源服务"""
        if self._data_source_service is None:
            self._data_source_service = getattr(
                self.container, 'data_source', None
            ) or getattr(self.container, 'data_source_service', None)
        return self._data_source_service
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式（基于 args_schema 生成）"""
        try:
            parameters = self.args_schema.model_json_schema()
        except Exception:
            parameters = self.args_schema.schema()  # type: ignore[attr-defined]
        return {
            "type": "function",
            "function": {
                "name": "data_sampler",
                "description": "从数据源中采样数据进行分析",
                "parameters": parameters,
            },
        }
    
    async def run(

    
        self,
        sql: str,
        connection_config: Dict[str, Any],
        strategy: str = "random",
        sample_size: int = 1000,
        random_seed: Optional[int] = None,
        strata_column: Optional[str] = None,
        cluster_column: Optional[str] = None,
        max_total_size: int = 100000,
        analyze_data_types: bool = True,
        **kwargs
    

    
    ) -> Dict[str, Any]:
        """
        执行数据采样
        
        Args:
            sql: 要采样的 SQL 查询
            connection_config: 数据源连接配置
            strategy: 采样策略
            sample_size: 采样大小
            random_seed: 随机种子
            strata_column: 分层列名
            cluster_column: 聚类列名
            max_total_size: 最大总数据量
            analyze_data_types: 是否分析数据类型
            
        Returns:
            Dict[str, Any]: 采样结果
        """
        logger.info(f"📊 [DataSamplerTool] 开始采样")
        logger.info(f"   采样策略: {strategy}")

    
    async def execute(self, **kwargs) -> Dict[str, Any]:

    
        """向后兼容的execute方法"""

    
        return await self.run(**kwargs)
        logger.info(f"   采样大小: {sample_size}")
        
        try:
            # 获取数据源服务
            data_source_service = await self._get_data_source_service()
            if not data_source_service:
                return {
                    "success": False,
                    "error": "数据源服务不可用",
                    "result": None
                }
            
            # 构建采样配置
            config = SamplingConfig(
                strategy=SamplingStrategy(strategy),
                sample_size=sample_size,
                random_seed=random_seed,
                strata_column=strata_column,
                cluster_column=cluster_column
            )
            
            # 执行采样
            result = await self._execute_sampling(
                data_source_service, connection_config, sql, config, max_total_size, analyze_data_types
            )
            
            return {
                "success": True,
                "result": result,
                "metadata": {
                    "strategy": strategy,
                    "sample_size": sample_size,
                    "total_size": result.total_size,
                    "sampling_rate": result.sampling_rate,
                    "columns_count": len(result.columns)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [DataSamplerTool] 采样失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    async def _execute_sampling(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        sql: str,
        config: SamplingConfig,
        max_total_size: int,
        analyze_data_types: bool
    ) -> SamplingResult:
        """执行采样"""
        # 首先获取总数据量
        total_size = await self._get_total_size(data_source_service, connection_config, sql)
        
        if total_size > max_total_size:
            logger.warning(f"⚠️ 数据量过大 ({total_size})，限制为 {max_total_size}")
            total_size = max_total_size
        
        # 调整采样大小
        if config.sample_size > total_size:
            config.sample_size = total_size
            logger.info(f"📝 调整采样大小为 {config.sample_size}")
        
        # 根据策略执行采样
        if config.strategy == SamplingStrategy.RANDOM:
            sampled_data = await self._random_sampling(
                data_source_service, connection_config, sql, config, total_size
            )
        elif config.strategy == SamplingStrategy.SYSTEMATIC:
            sampled_data = await self._systematic_sampling(
                data_source_service, connection_config, sql, config, total_size
            )
        elif config.strategy == SamplingStrategy.STRATIFIED:
            sampled_data = await self._stratified_sampling(
                data_source_service, connection_config, sql, config, total_size
            )
        elif config.strategy == SamplingStrategy.CLUSTER:
            sampled_data = await self._cluster_sampling(
                data_source_service, connection_config, sql, config, total_size
            )
        else:  # CONVENIENCE
            sampled_data = await self._convenience_sampling(
                data_source_service, connection_config, sql, config, total_size
            )
        
        # 分析数据类型
        data_types = {}
        if analyze_data_types and sampled_data:
            data_types = self._analyze_data_types(sampled_data)
        
        # 计算统计信息
        statistics = self._calculate_statistics(sampled_data, data_types)
        
        # 提取列名
        columns = list(sampled_data[0].keys()) if sampled_data else []
        
        return SamplingResult(
            data=sampled_data,
            sample_size=len(sampled_data),
            total_size=total_size,
            sampling_rate=len(sampled_data) / total_size if total_size > 0 else 0,
            strategy=config.strategy,
            columns=columns,
            data_types=data_types,
            statistics=statistics
        )
    
    async def _get_total_size(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        sql: str
    ) -> int:
        """获取总数据量"""
        try:
            # 构建计数查询
            count_sql = f"SELECT COUNT(*) as total FROM ({sql}) as subquery"
            
            result = await data_source_service.run_query(
                connection_config=connection_config,
                sql=count_sql,
                limit=1
            )
            
            if result.get("success"):
                rows = result.get("rows", []) or result.get("data", [])
                if rows and isinstance(rows[0], dict):
                    return int(rows[0].get("total", 0))
                elif rows and isinstance(rows[0], (list, tuple)):
                    return int(rows[0][0])
            
            return 0
            
        except Exception as e:
            logger.warning(f"⚠️ 获取总数据量失败: {e}")
            return 0
    
    async def _random_sampling(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        sql: str,
        config: SamplingConfig,
        total_size: int
    ) -> List[Dict[str, Any]]:
        """随机采样"""
        try:
            # 设置随机种子
            if config.random_seed is not None:
                random.seed(config.random_seed)
            
            # 生成随机行号
            sample_indices = sorted(random.sample(range(total_size), config.sample_size))
            
            # 分批获取数据
            sampled_data = []
            batch_size = 1000
            
            for i in range(0, len(sample_indices), batch_size):
                batch_indices = sample_indices[i:i + batch_size]
                
                # 构建查询获取指定行的数据
                # 这里使用 LIMIT 和 OFFSET 的简化实现
                for idx in batch_indices:
                    offset_sql = f"{sql} LIMIT 1 OFFSET {idx}"
                    
                    result = await data_source_service.run_query(
                        connection_config=connection_config,
                        sql=offset_sql,
                        limit=1
                    )
                    
                    if result.get("success"):
                        rows = result.get("rows", []) or result.get("data", [])
                        if rows:
                            sampled_data.extend(self._format_rows(rows))
            
            return sampled_data
            
        except Exception as e:
            logger.error(f"❌ 随机采样失败: {e}")
            return []
    
    async def _systematic_sampling(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        sql: str,
        config: SamplingConfig,
        total_size: int
    ) -> List[Dict[str, Any]]:
        """系统采样"""
        try:
            # 计算采样间隔
            interval = total_size // config.sample_size
            
            # 随机选择起始点
            if config.random_seed is not None:
                random.seed(config.random_seed)
            start_point = random.randint(0, interval - 1)
            
            # 生成采样点
            sample_indices = [start_point + i * interval for i in range(config.sample_size)]
            sample_indices = [idx for idx in sample_indices if idx < total_size]
            
            # 获取数据
            sampled_data = []
            for idx in sample_indices:
                offset_sql = f"{sql} LIMIT 1 OFFSET {idx}"
                
                result = await data_source_service.run_query(
                    connection_config=connection_config,
                    sql=offset_sql,
                    limit=1
                )
                
                if result.get("success"):
                    rows = result.get("rows", []) or result.get("data", [])
                    if rows:
                        sampled_data.extend(self._format_rows(rows))
            
            return sampled_data
            
        except Exception as e:
            logger.error(f"❌ 系统采样失败: {e}")
            return []
    
    async def _stratified_sampling(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        sql: str,
        config: SamplingConfig,
        total_size: int
    ) -> List[Dict[str, Any]]:
        """分层采样"""
        try:
            if not config.strata_column:
                logger.warning("⚠️ 分层采样需要指定 strata_column")
                return await self._random_sampling(data_source_service, connection_config, sql, config, total_size)
            
            # 获取分层信息
            strata_sql = f"""
            SELECT {config.strata_column}, COUNT(*) as count
            FROM ({sql}) as subquery
            GROUP BY {config.strata_column}
            """
            
            result = await data_source_service.run_query(
                connection_config=connection_config,
                sql=strata_sql,
                limit=1000
            )
            
            if not result.get("success"):
                logger.warning("⚠️ 获取分层信息失败，使用随机采样")
                return await self._random_sampling(data_source_service, connection_config, sql, config, total_size)
            
            strata_info = result.get("rows", []) or result.get("data", [])
            
            # 计算每层的采样数量
            sampled_data = []
            for stratum in strata_info:
                stratum_value = stratum.get(config.strata_column)
                stratum_count = stratum.get("count", 0)
                
                if stratum_count > 0:
                    stratum_sample_size = max(1, int(config.sample_size * stratum_count / total_size))
                    
                    # 从每层采样
                    stratum_sql = f"""
                    SELECT * FROM ({sql}) as subquery
                    WHERE {config.strata_column} = '{stratum_value}'
                    LIMIT {stratum_sample_size}
                    """
                    
                    stratum_result = await data_source_service.run_query(
                        connection_config=connection_config,
                        sql=stratum_sql,
                        limit=stratum_sample_size
                    )
                    
                    if stratum_result.get("success"):
                        rows = stratum_result.get("rows", []) or stratum_result.get("data", [])
                        sampled_data.extend(self._format_rows(rows))
            
            return sampled_data
            
        except Exception as e:
            logger.error(f"❌ 分层采样失败: {e}")
            return await self._random_sampling(data_source_service, connection_config, sql, config, total_size)
    
    async def _cluster_sampling(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        sql: str,
        config: SamplingConfig,
        total_size: int
    ) -> List[Dict[str, Any]]:
        """聚类采样"""
        try:
            if not config.cluster_column:
                logger.warning("⚠️ 聚类采样需要指定 cluster_column")
                return await self._random_sampling(data_source_service, connection_config, sql, config, total_size)
            
            # 获取聚类信息
            cluster_sql = f"""
            SELECT {config.cluster_column}, COUNT(*) as count
            FROM ({sql}) as subquery
            GROUP BY {config.cluster_column}
            """
            
            result = await data_source_service.run_query(
                connection_config=connection_config,
                sql=cluster_sql,
                limit=1000
            )
            
            if not result.get("success"):
                logger.warning("⚠️ 获取聚类信息失败，使用随机采样")
                return await self._random_sampling(data_source_service, connection_config, sql, config, total_size)
            
            clusters = result.get("rows", []) or result.get("data", [])
            
            # 随机选择聚类
            if config.random_seed is not None:
                random.seed(config.random_seed)
            
            selected_clusters = random.sample(clusters, min(len(clusters), config.sample_size))
            
            # 从选中的聚类中获取数据
            sampled_data = []
            for cluster in selected_clusters:
                cluster_value = cluster.get(config.cluster_column)
                
                cluster_sql = f"""
                SELECT * FROM ({sql}) as subquery
                WHERE {config.cluster_column} = '{cluster_value}'
                """
                
                cluster_result = await data_source_service.run_query(
                    connection_config=connection_config,
                    sql=cluster_sql,
                    limit=1000
                )
                
                if cluster_result.get("success"):
                    rows = cluster_result.get("rows", []) or cluster_result.get("data", [])
                    sampled_data.extend(self._format_rows(rows))
            
            return sampled_data
            
        except Exception as e:
            logger.error(f"❌ 聚类采样失败: {e}")
            return await self._random_sampling(data_source_service, connection_config, sql, config, total_size)
    
    async def _convenience_sampling(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        sql: str,
        config: SamplingConfig,
        total_size: int
    ) -> List[Dict[str, Any]]:
        """便利采样（取前N条）"""
        try:
            convenience_sql = f"{sql} LIMIT {config.sample_size}"
            
            result = await data_source_service.run_query(
                connection_config=connection_config,
                sql=convenience_sql,
                limit=config.sample_size
            )
            
            if result.get("success"):
                rows = result.get("rows", []) or result.get("data", [])
                return self._format_rows(rows)
            
            return []
            
        except Exception as e:
            logger.error(f"❌ 便利采样失败: {e}")
            return []
    
    def _format_rows(self, rows: List[Any]) -> List[Dict[str, Any]]:
        """格式化行数据"""
        formatted_rows = []
        
        for row in rows:
            if isinstance(row, dict):
                formatted_rows.append(row)
            elif isinstance(row, (list, tuple)):
                # 转换为字典格式
                row_dict = {}
                for i, value in enumerate(row):
                    row_dict[f"column_{i}"] = value
                formatted_rows.append(row_dict)
            else:
                formatted_rows.append({"value": row})
        
        return formatted_rows
    
    def _analyze_data_types(self, data: List[Dict[str, Any]]) -> Dict[str, DataType]:
        """分析数据类型"""
        if not data:
            return {}
        
        data_types = {}
        columns = list(data[0].keys())
        
        for column in columns:
            values = [row.get(column) for row in data if row.get(column) is not None]
            
            if not values:
                data_types[column] = DataType.TEXT
                continue
            
            # 检查数值型
            numeric_count = 0
            for value in values:
                try:
                    float(str(value))
                    numeric_count += 1
                except (ValueError, TypeError):
                    break
            
            if numeric_count == len(values):
                data_types[column] = DataType.NUMERIC
                continue
            
            # 检查布尔型
            boolean_count = 0
            for value in values:
                if str(value).lower() in ['true', 'false', '1', '0', 'yes', 'no']:
                    boolean_count += 1
            
            if boolean_count == len(values):
                data_types[column] = DataType.BOOLEAN
                continue
            
            # 检查日期时间型
            datetime_count = 0
            for value in values:
                try:
                    import datetime
                    if isinstance(value, (datetime.datetime, datetime.date)):
                        datetime_count += 1
                    elif isinstance(value, str) and len(str(value)) > 8:
                        # 简单检查日期格式
                        if any(char in str(value) for char in ['-', '/', ':']):
                            datetime_count += 1
                except:
                    pass
            
            if datetime_count > len(values) * 0.8:  # 80% 以上是日期时间
                data_types[column] = DataType.DATETIME
                continue
            
            # 检查分类型（唯一值较少）
            unique_values = set(str(value) for value in values)
            if len(unique_values) < min(20, len(values) * 0.1):  # 少于20个唯一值或少于10%的唯一值
                data_types[column] = DataType.CATEGORICAL
                continue
            
            # 默认为文本型
            data_types[column] = DataType.TEXT
        
        return data_types
    
    def _calculate_statistics(self, data: List[Dict[str, Any]], data_types: Dict[str, DataType]) -> Dict[str, Any]:
        """计算统计信息"""
        if not data:
            return {}
        
        statistics = {
            "total_rows": len(data),
            "total_columns": len(data[0]) if data else 0,
            "column_statistics": {}
        }
        
        for column, data_type in data_types.items():
            values = [row.get(column) for row in data if row.get(column) is not None]
            
            if not values:
                statistics["column_statistics"][column] = {
                    "type": data_type.value,
                    "null_count": len(data),
                    "null_percentage": 100.0
                }
                continue
            
            null_count = len(data) - len(values)
            null_percentage = (null_count / len(data)) * 100
            
            column_stats = {
                "type": data_type.value,
                "null_count": null_count,
                "null_percentage": null_percentage,
                "non_null_count": len(values),
                "unique_count": len(set(str(v) for v in values))
            }
            
            if data_type == DataType.NUMERIC:
                numeric_values = []
                for value in values:
                    try:
                        numeric_values.append(float(str(value)))
                    except (ValueError, TypeError):
                        pass
                
                if numeric_values:
                    column_stats.update({
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "mean": sum(numeric_values) / len(numeric_values),
                        "median": sorted(numeric_values)[len(numeric_values) // 2]
                    })
            
            elif data_type == DataType.CATEGORICAL:
                value_counts = {}
                for value in values:
                    value_str = str(value)
                    value_counts[value_str] = value_counts.get(value_str, 0) + 1
                
                column_stats["value_counts"] = value_counts
                column_stats["most_common"] = max(value_counts.items(), key=lambda x: x[1]) if value_counts else None
            
            statistics["column_statistics"][column] = column_stats
        
        return statistics


def create_data_sampler_tool(container: Any) -> DataSamplerTool:
    """
    创建数据采样工具
    
    Args:
        container: 服务容器
        
    Returns:
        DataSamplerTool 实例
    """
    return DataSamplerTool(container)


# 导出
__all__ = [
    "DataSamplerTool",
    "SamplingStrategy",
    "DataType",
    "SamplingConfig",
    "SamplingResult",
    "create_data_sampler_tool",
]