"""
数据执行层

负责连接管理、SQL执行、结果格式化
"""
import logging
from datetime import datetime
from typing import Any, Dict
from sqlalchemy.orm import Session

from .models import ExecutionResult, DataExecutionServiceInterface


class DataExecutionService(DataExecutionServiceInterface):
    """数据执行服务 - 只负责SQL执行"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.connection_manager = ConnectionManager(db_session)
        self.query_executor = QueryExecutor()
        self.result_formatter = ResultFormatter()
        self.logger = logging.getLogger(__name__)
    
    async def execute_sql(self, data_source_id: str, sql: str) -> ExecutionResult:
        """执行SQL查询"""
        start_time = datetime.now()
        
        try:
            self.logger.debug(f"执行SQL: {sql[:100]}...")
            
            # 1. 获取连接
            connector = await self.connection_manager.get_connector(data_source_id)
            if not connector:
                return ExecutionResult(
                    success=False,
                    error_message=f"无法获取数据源连接: {data_source_id}"
                )
            
            # 2. 执行查询
            execution_result = await self.query_executor.execute(connector, sql)
            if not execution_result.success:
                return ExecutionResult(
                    success=False,
                    error_message=execution_result.error_message,
                    execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                )
            
            # 3. 格式化结果
            formatted_value = await self.result_formatter.format(execution_result.raw_data)
            
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ExecutionResult(
                success=True,
                formatted_value=formatted_value,
                execution_time_ms=execution_time_ms,
                row_count=execution_result.row_count,
                raw_data=execution_result.raw_data
            )
            
        except Exception as e:
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"SQL执行异常: {str(e)}")
            
            return ExecutionResult(
                success=False,
                error_message=f"SQL执行异常: {str(e)}",
                execution_time_ms=execution_time_ms
            )


class ConnectionManager:
    """连接管理器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.connections = {}
        self.logger = logging.getLogger(__name__)
    
    async def get_connector(self, data_source_id: str):
        """获取数据源连接器"""
        try:
            # 检查缓存的连接
            if data_source_id in self.connections:
                connector = self.connections[data_source_id]
                if await self._is_connection_valid(connector):
                    return connector
                else:
                    # 连接失效，移除缓存
                    del self.connections[data_source_id]
            
            # 创建新连接
            connector = await self._create_connector(data_source_id)
            if connector:
                self.connections[data_source_id] = connector
                self.logger.debug(f"创建新连接: {data_source_id}")
            
            return connector
            
        except Exception as e:
            self.logger.error(f"获取连接器失败: {data_source_id}, 错误: {e}")
            return None
    
    async def _create_connector(self, data_source_id: str):
        """创建数据源连接器"""
        try:
            from app.models.data_source import DataSource
            from app.services.data.connectors.connector_factory import create_connector
            
            # 获取数据源配置
            data_source = self.db.query(DataSource).filter(
                DataSource.id == data_source_id
            ).first()
            
            if not data_source:
                self.logger.error(f"数据源不存在: {data_source_id}")
                return None
            
            # 创建连接器
            connector = create_connector(data_source)
            
            # 测试连接
            await connector.connect()
            
            return connector
            
        except Exception as e:
            self.logger.error(f"创建连接器失败: {data_source_id}, 错误: {e}")
            return None
    
    async def _is_connection_valid(self, connector) -> bool:
        """检查连接是否有效"""
        try:
            # 简单的连接有效性检查
            if hasattr(connector, '_connected'):
                return connector._connected
            return True
        except:
            return False


class QueryExecutor:
    """查询执行器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, connector, sql: str) -> ExecutionResult:
        """执行SQL查询"""
        start_time = datetime.now()
        
        try:
            # 执行查询
            query_result = await connector.execute_query(sql)
            
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 提取行数
            row_count = self._extract_row_count(query_result)
            
            return ExecutionResult(
                success=True,
                raw_data=query_result,
                execution_time_ms=execution_time_ms,
                row_count=row_count
            )
            
        except Exception as e:
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"查询执行失败: {str(e)}")
            
            return ExecutionResult(
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time_ms
            )
    
    def _extract_row_count(self, query_result: Any) -> int:
        """从查询结果中提取行数"""
        try:
            # 处理 DorisQueryResult 对象
            if hasattr(query_result, 'data'):
                if hasattr(query_result.data, '__len__'):
                    return len(query_result.data)
                return getattr(query_result, 'rows_scanned', 0)
            
            # 处理列表格式
            if isinstance(query_result, list):
                return len(query_result)
            
            # 处理字典格式
            elif isinstance(query_result, dict) and "count" in query_result:
                return int(query_result["count"])
            
            # 其他情况
            return 1 if query_result else 0
            
        except Exception as e:
            self.logger.warning(f"提取行数失败: {e}")
            return 0


class ResultFormatter:
    """结果格式化器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def format(self, raw_data: Any) -> str:
        """格式化查询结果为字符串"""
        try:
            if not raw_data:
                return "无数据"
            
            # 处理 DorisQueryResult 对象
            if hasattr(raw_data, 'data') and hasattr(raw_data, 'execution_time'):
                # 这是一个 DorisQueryResult 对象，提取其中的 data
                df = raw_data.data
                if df is None or (hasattr(df, 'empty') and df.empty):
                    return "0"
                
                # 单行单列结果（常见的统计查询）
                if hasattr(df, 'iloc') and len(df) == 1 and len(df.columns) == 1:
                    value = df.iloc[0, 0]
                    return self._format_single_value(value)
                elif hasattr(df, 'iloc') and len(df) == 1:
                    # 单行多列，取第一个值
                    value = df.iloc[0, 0]
                    return self._format_single_value(value)
                else:
                    # 多行结果 - 尝试提取第一行第一列的值
                    if hasattr(df, 'iloc') and len(df) > 0:
                        try:
                            # 对于多行结果，通常第一行第一列包含我们需要的主要信息
                            value = df.iloc[0, 0]
                            formatted_value = self._format_single_value(value)
                            # 如果提取的值有意义（不为空且不是NaN），返回它
                            if formatted_value and formatted_value != "nan" and formatted_value != "None":
                                self.logger.debug(f"从多行结果中提取第一行第一列值: {formatted_value}")
                                return formatted_value
                        except Exception as e:
                            self.logger.warning(f"无法从多行结果提取值: {e}")
                    
                    # 如果无法提取有效值，则返回行数
                    row_count = len(df) if hasattr(df, '__len__') else 0
                    self.logger.debug(f"多行结果无有效值，返回记录数: {row_count}")
                    return f"共 {row_count} 条记录"
            
            # 处理列表格式
            if isinstance(raw_data, list):
                if not raw_data:
                    return "无数据"
                
                # 单行单列结果
                if len(raw_data) == 1 and isinstance(raw_data[0], dict):
                    first_row = raw_data[0]
                    if len(first_row) == 1:
                        # 单个统计值
                        value = list(first_row.values())[0]
                        return self._format_single_value(value)
                    else:
                        # 多列，选择第一个值
                        value = list(first_row.values())[0]
                        return self._format_single_value(value)
                
                # 多行结果 - 尝试提取第一行的第一个值
                if len(raw_data) > 0:
                    try:
                        first_row = raw_data[0]
                        if isinstance(first_row, dict) and first_row:
                            # 获取第一个字典的第一个值
                            first_value = list(first_row.values())[0]
                            formatted_value = self._format_single_value(first_value)
                            # 如果提取的值有意义，返回它
                            if formatted_value and formatted_value != "nan" and formatted_value != "None":
                                self.logger.debug(f"从多行列表结果中提取第一行第一列值: {formatted_value}")
                                return formatted_value
                    except Exception as e:
                        self.logger.warning(f"无法从多行列表结果提取值: {e}")
                
                # 如果无法提取有效值，则返回行数
                self.logger.debug(f"多行列表结果无有效值，返回记录数: {len(raw_data)}")
                return f"共 {len(raw_data)} 条记录"
            
            # 处理字典格式
            elif isinstance(raw_data, dict):
                if "count" in raw_data:
                    return self._format_single_value(raw_data["count"])
                elif "value" in raw_data:
                    return self._format_single_value(raw_data["value"])
                else:
                    # 取第一个值
                    if raw_data:
                        value = list(raw_data.values())[0]
                        return self._format_single_value(value)
                    return "无数据"
            
            # 其他格式，直接转换为字符串
            return self._format_single_value(raw_data)
            
        except Exception as e:
            self.logger.error(f"格式化查询结果失败: {str(e)}")
            return f"格式化失败: {str(e)}"
    
    def _format_single_value(self, value: Any) -> str:
        """格式化单个值"""
        try:
            if value is None:
                return "0"
            
            # 处理数字格式
            if isinstance(value, (int, float)):
                # 如果是整数或者小数部分为0，显示为整数
                if isinstance(value, float) and value.is_integer():
                    return str(int(value))
                elif isinstance(value, float):
                    # 保留适当的小数位数
                    return f"{value:.2f}".rstrip('0').rstrip('.')
                else:
                    return str(value)
            
            # 处理字符串
            if isinstance(value, str):
                return value.strip()
            
            # 其他类型直接转换
            return str(value)
            
        except Exception as e:
            self.logger.warning(f"格式化单个值失败: {e}")
            return str(value) if value is not None else "0"