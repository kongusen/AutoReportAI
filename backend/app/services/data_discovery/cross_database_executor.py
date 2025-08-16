"""
跨数据库查询执行引擎 - 支持多库多表的复杂查询执行
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from sqlalchemy.orm import Session
from app.db.session import get_db_session
from app.models.data_source import DataSource
from app.models.table_schema import Database, Table
from app.services.connectors.connector_factory import create_connector
from .intelligent_query_router import QueryPlan, TableCandidate


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    data: Optional[pd.DataFrame] = None
    row_count: int = 0
    execution_time: float = 0.0
    query_sql: str = ""
    errors: List[str] = None
    performance_stats: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.performance_stats is None:
            self.performance_stats = {}


@dataclass
class DatabaseQueryTask:
    """数据库查询任务"""
    database_id: str
    database_name: str
    tables: List[TableCandidate]
    sql_query: str
    priority: int = 1  # 优先级：1-高，2-中，3-低


class SQLGenerator:
    """SQL生成器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_sql(self, plan: QueryPlan) -> List[DatabaseQueryTask]:
        """根据查询计划生成SQL"""
        try:
            if plan.cross_database:
                return self._generate_cross_database_sql(plan)
            else:
                return self._generate_single_database_sql(plan)
                
        except Exception as e:
            self.logger.error(f"Error generating SQL: {e}")
            raise
    
    def _generate_single_database_sql(self, plan: QueryPlan) -> List[DatabaseQueryTask]:
        """生成单数据库SQL"""
        all_tables = plan.primary_tables + plan.join_tables
        
        if not all_tables:
            raise ValueError("No tables found in query plan")
        
        # 获取数据库信息
        first_table = all_tables[0].table
        database_id = str(first_table.database_id)
        database_name = first_table.database.name
        
        # 构建SQL
        sql_parts = []
        
        # SELECT子句
        select_clause = "SELECT " + ", ".join(plan.select_columns)
        sql_parts.append(select_clause)
        
        # FROM子句
        from_clause = f"FROM {database_name}.{plan.primary_tables[0].table.name}"
        if plan.primary_tables[0].table.name != plan.primary_tables[0].table.name:
            from_clause += f" AS {plan.primary_tables[0].table.name}"
        sql_parts.append(from_clause)
        
        # JOIN子句
        for i, join_table in enumerate(plan.join_tables):
            if i < len(plan.join_conditions):
                join_clause = f"LEFT JOIN {database_name}.{join_table.table.name} ON {plan.join_conditions[i]}"
                sql_parts.append(join_clause)
        
        # WHERE子句
        if plan.where_conditions:
            where_clause = "WHERE " + " AND ".join(plan.where_conditions)
            sql_parts.append(where_clause)
        
        # GROUP BY子句
        if plan.group_by_columns:
            group_clause = "GROUP BY " + ", ".join(plan.group_by_columns)
            sql_parts.append(group_clause)
        
        # ORDER BY子句
        if plan.order_by_columns:
            order_clause = "ORDER BY " + ", ".join(plan.order_by_columns)
            sql_parts.append(order_clause)
        
        sql_query = " ".join(sql_parts)
        
        return [DatabaseQueryTask(
            database_id=database_id,
            database_name=database_name,
            tables=all_tables,
            sql_query=sql_query,
            priority=1
        )]
    
    def _generate_cross_database_sql(self, plan: QueryPlan) -> List[DatabaseQueryTask]:
        """生成跨数据库SQL"""
        tasks = []
        
        # 按数据库分组表
        database_groups = self._group_tables_by_database(plan.primary_tables + plan.join_tables)
        
        for database_id, table_group in database_groups.items():
            database_name = table_group[0].table.database.name
            
            # 为每个数据库生成查询任务
            sql_parts = []
            
            # SELECT子句 - 只选择当前数据库中的字段
            db_columns = self._filter_columns_by_database(plan.select_columns, table_group)
            if not db_columns:
                continue
                
            select_clause = "SELECT " + ", ".join(db_columns)
            sql_parts.append(select_clause)
            
            # FROM子句
            primary_table = table_group[0]
            from_clause = f"FROM {database_name}.{primary_table.table.name}"
            sql_parts.append(from_clause)
            
            # 同数据库内的JOIN
            same_db_joins = self._filter_same_database_joins(plan.join_conditions, table_group)
            for join_condition in same_db_joins:
                sql_parts.append(f"LEFT JOIN {join_condition}")
            
            # WHERE子句 - 只包含当前数据库的条件
            db_where_conditions = self._filter_where_conditions_by_database(plan.where_conditions, table_group)
            if db_where_conditions:
                where_clause = "WHERE " + " AND ".join(db_where_conditions)
                sql_parts.append(where_clause)
            
            sql_query = " ".join(sql_parts)
            
            task = DatabaseQueryTask(
                database_id=database_id,
                database_name=database_name,
                tables=table_group,
                sql_query=sql_query,
                priority=1 if primary_table in plan.primary_tables else 2
            )
            tasks.append(task)
        
        return tasks
    
    def _group_tables_by_database(self, tables: List[TableCandidate]) -> Dict[str, List[TableCandidate]]:
        """按数据库分组表"""
        groups = {}
        for table in tables:
            db_id = str(table.table.database_id)
            if db_id not in groups:
                groups[db_id] = []
            groups[db_id].append(table)
        return groups
    
    def _filter_columns_by_database(self, columns: List[str], table_group: List[TableCandidate]) -> List[str]:
        """过滤数据库相关的字段"""
        db_columns = []
        table_names = {table.table.name for table in table_group}
        
        for column in columns:
            if '.' in column:
                table_name = column.split('.')[0]
                if table_name in table_names:
                    db_columns.append(column)
            elif column == '*' or any(agg in column.upper() for agg in ['COUNT', 'SUM', 'AVG']):
                db_columns.append(column)
        
        return db_columns
    
    def _filter_same_database_joins(self, join_conditions: List[str], table_group: List[TableCandidate]) -> List[str]:
        """过滤同数据库内的JOIN条件"""
        same_db_joins = []
        table_names = {table.table.name for table in table_group}
        
        for condition in join_conditions:
            # 解析JOIN条件中的表名
            tables_in_condition = set()
            for part in condition.split():
                if '.' in part:
                    table_name = part.split('.')[0]
                    tables_in_condition.add(table_name)
            
            # 如果JOIN条件中的所有表都在同一个数据库中
            if tables_in_condition.issubset(table_names):
                same_db_joins.append(condition)
        
        return same_db_joins
    
    def _filter_where_conditions_by_database(self, where_conditions: List[str], table_group: List[TableCandidate]) -> List[str]:
        """过滤数据库相关的WHERE条件"""
        db_conditions = []
        table_names = {table.table.name for table in table_group}
        
        for condition in where_conditions:
            # 如果条件不包含表名（通用条件）或包含当前数据库的表名
            if '.' not in condition:
                db_conditions.append(condition)
            else:
                for part in condition.split():
                    if '.' in part:
                        table_name = part.split('.')[0]
                        if table_name in table_names:
                            db_conditions.append(condition)
                            break
        
        return db_conditions


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def optimize_tasks(self, tasks: List[DatabaseQueryTask]) -> List[DatabaseQueryTask]:
        """优化查询任务"""
        try:
            # 1. 按优先级排序
            tasks.sort(key=lambda x: x.priority)
            
            # 2. 估算查询成本并调整执行顺序
            self._estimate_query_cost(tasks)
            
            # 3. 添加查询提示和优化
            self._add_query_hints(tasks)
            
            return tasks
            
        except Exception as e:
            self.logger.error(f"Error optimizing tasks: {e}")
            return tasks
    
    def _estimate_query_cost(self, tasks: List[DatabaseQueryTask]):
        """估算查询成本"""
        for task in tasks:
            # 根据表的大小和JOIN数量估算成本
            total_rows = sum(table.table.row_count or 0 for table in task.tables)
            join_count = task.sql_query.upper().count('JOIN')
            
            # 简单的成本计算
            estimated_cost = total_rows * (1 + join_count * 0.5)
            
            # 为大查询降低优先级
            if estimated_cost > 1000000:  # 超过100万行的查询
                task.priority += 1
            
            self.logger.info(f"Task {task.database_name} estimated cost: {estimated_cost}")
    
    def _add_query_hints(self, tasks: List[DatabaseQueryTask]):
        """添加查询提示"""
        for task in tasks:
            sql = task.sql_query
            
            # 为大表查询添加LIMIT
            if any(table.table.row_count and table.table.row_count > 100000 for table in task.tables):
                if 'LIMIT' not in sql.upper():
                    sql += " LIMIT 10000"  # 默认限制1万行
            
            # 为复杂查询添加超时提示
            if sql.upper().count('JOIN') > 2:
                sql = f"/* QUERY_TIMEOUT=300 */ {sql}"
            
            task.sql_query = sql


class CrossDatabaseExecutor:
    """跨数据库执行引擎"""
    
    def __init__(self, max_workers: int = 4):
        self.logger = logging.getLogger(__name__)
        self.sql_generator = SQLGenerator()
        self.query_optimizer = QueryOptimizer()
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def execute_query_plan(self, plan: QueryPlan, data_source_id: str) -> ExecutionResult:
        """执行查询计划"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Executing query plan: complexity={plan.estimated_complexity}")
            
            # 1. 生成SQL任务
            tasks = self.sql_generator.generate_sql(plan)
            
            # 2. 优化任务
            optimized_tasks = self.query_optimizer.optimize_tasks(tasks)
            
            # 3. 执行任务
            if len(optimized_tasks) == 1:
                # 单数据库查询
                result = await self._execute_single_database(optimized_tasks[0], data_source_id)
            else:
                # 跨数据库查询
                result = await self._execute_cross_database(optimized_tasks, data_source_id)
            
            result.execution_time = time.time() - start_time
            self.logger.info(f"Query executed successfully in {result.execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing query plan: {e}")
            return ExecutionResult(
                success=False,
                errors=[str(e)],
                execution_time=time.time() - start_time
            )
    
    async def _execute_single_database(self, task: DatabaseQueryTask, data_source_id: str) -> ExecutionResult:
        """执行单数据库查询"""
        try:
            with get_db_session() as db:
                data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
                if not data_source:
                    raise ValueError(f"Data source {data_source_id} not found")
            
            # 创建连接器
            connector = create_connector(data_source)
            
            async with connector:
                # 执行查询
                query_result = await connector.execute_query(task.sql_query)
                
                return ExecutionResult(
                    success=True,
                    data=query_result.data,
                    row_count=len(query_result.data) if query_result.data is not None else 0,
                    query_sql=task.sql_query,
                    performance_stats={
                        'execution_time': query_result.execution_time,
                        'rows_scanned': getattr(query_result, 'rows_scanned', 0),
                        'bytes_scanned': getattr(query_result, 'bytes_scanned', 0)
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Error executing single database query: {e}")
            return ExecutionResult(
                success=False,
                errors=[str(e)],
                query_sql=task.sql_query
            )
    
    async def _execute_cross_database(self, tasks: List[DatabaseQueryTask], data_source_id: str) -> ExecutionResult:
        """执行跨数据库查询"""
        try:
            with get_db_session() as db:
                data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
                if not data_source:
                    raise ValueError(f"Data source {data_source_id} not found")
            
            # 并行执行所有任务
            loop = asyncio.get_event_loop()
            futures = []
            
            for task in tasks:
                future = loop.run_in_executor(
                    self.executor,
                    self._execute_database_task_sync,
                    task,
                    data_source
                )
                futures.append(future)
            
            # 等待所有任务完成
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            # 处理结果
            successful_results = []
            errors = []
            all_sql = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    errors.append(f"Task {i+1}: {str(result)}")
                elif result.success:
                    successful_results.append(result)
                    all_sql.append(result.query_sql)
                else:
                    errors.extend(result.errors)
            
            if not successful_results:
                return ExecutionResult(
                    success=False,
                    errors=errors,
                    query_sql="; ".join(all_sql)
                )
            
            # 合并跨数据库结果
            merged_data = await self._merge_cross_database_results(successful_results)
            total_rows = sum(result.row_count for result in successful_results)
            
            return ExecutionResult(
                success=True,
                data=merged_data,
                row_count=total_rows,
                query_sql="; ".join(all_sql),
                errors=errors if errors else None,
                performance_stats={
                    'databases_queried': len(successful_results),
                    'total_execution_time': sum(result.execution_time for result in successful_results)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error executing cross database query: {e}")
            return ExecutionResult(
                success=False,
                errors=[str(e)]
            )
    
    def _execute_database_task_sync(self, task: DatabaseQueryTask, data_source: DataSource) -> ExecutionResult:
        """同步执行数据库任务（用于线程池）"""
        try:
            # 这里需要使用同步版本的连接器执行
            # 由于当前的连接器是异步的，这里简化处理
            # 在实际实现中，应该有同步版本的连接器
            
            return ExecutionResult(
                success=True,
                data=pd.DataFrame(),  # 占位符
                row_count=0,
                query_sql=task.sql_query,
                performance_stats={'simulated': True}
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                errors=[str(e)],
                query_sql=task.sql_query
            )
    
    async def _merge_cross_database_results(self, results: List[ExecutionResult]) -> pd.DataFrame:
        """合并跨数据库查询结果"""
        try:
            if not results:
                return pd.DataFrame()
            
            if len(results) == 1:
                return results[0].data
            
            # 简单的结果合并策略
            # 实际实现中应该根据查询类型和字段关系进行智能合并
            
            merged_data = pd.DataFrame()
            
            for result in results:
                if result.data is not None and not result.data.empty:
                    if merged_data.empty:
                        merged_data = result.data.copy()
                    else:
                        # 尝试按相同字段合并
                        common_columns = list(set(merged_data.columns) & set(result.data.columns))
                        if common_columns:
                            merged_data = pd.merge(merged_data, result.data, on=common_columns, how='outer')
                        else:
                            # 如果没有相同字段，执行简单的拼接
                            merged_data = pd.concat([merged_data, result.data], axis=0, ignore_index=True)
            
            self.logger.info(f"Merged {len(results)} database results into {len(merged_data)} rows")
            return merged_data
            
        except Exception as e:
            self.logger.error(f"Error merging cross database results: {e}")
            return pd.DataFrame()
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)