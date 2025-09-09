"""
上下文管理系统 - 基于设计文档实现
"""

import logging
import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class TimeRange(Enum):
    """时间范围枚举"""
    DAY = "day"
    WEEK = "week" 
    MONTH = "month"
    YEAR = "year"
    CUSTOM = "custom"


class ExecutionMode(Enum):
    """执行模式枚举"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"


@dataclass
class TaskContext:
    """任务级别的上下文信息"""
    task_id: str
    user_id: str
    
    # 报告数据范围
    time_range: TimeRange = TimeRange.DAY
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # 报告执行时间
    scheduled_time: Optional[datetime] = None
    execution_mode: ExecutionMode = ExecutionMode.MANUAL
    
    # 报告输出要求
    output_format: str = "docx"
    language: str = "zh-CN"
    
    # 业务上下文
    department: Optional[str] = None
    report_purpose: Optional[str] = None


@dataclass
class PlaceholderInfo:
    """占位符详细信息"""
    name: str
    type: str  # 数值/文本/日期/图表
    description: str
    
    # 位置信息
    paragraph_index: int
    paragraph_context: str
    
    # 数据要求
    aggregation: Optional[str] = None  # sum/avg/count/max/min
    format_pattern: Optional[str] = None
    default_value: Optional[Any] = None


@dataclass
class TemplateSection:
    """模板章节信息"""
    name: str
    index: int
    content: str
    placeholders: List[str] = field(default_factory=list)


@dataclass
class ChartRequirement:
    """图表需求信息"""
    placeholder_name: str
    chart_type: str  # line/bar/pie/table
    aggregation: Optional[str] = None
    time_dimension: bool = False


@dataclass
class TemplateContext:
    """模板级别的上下文信息"""
    template_id: str
    template_name: str
    template_content: str
    
    # 占位符信息
    placeholders: List[PlaceholderInfo] = field(default_factory=list)
    placeholder_count: int = 0
    
    # 模板结构信息
    sections: List[TemplateSection] = field(default_factory=list)
    chart_requirements: List[ChartRequirement] = field(default_factory=list)
    
    # 模板元数据
    template_type: str = "general"  # 日报/周报/月报/年报
    complexity_level: str = "medium"  # simple/medium/complex
    estimated_data_volume: str = "small"


@dataclass
class ColumnInfo:
    """列信息"""
    name: str
    type: str
    nullable: bool = True
    description: Optional[str] = None


@dataclass
class TableSchema:
    """表结构信息"""
    table_name: str
    columns: List[ColumnInfo] = field(default_factory=list)
    indexes: List[str] = field(default_factory=list)
    row_count: Optional[int] = None
    last_updated: Optional[datetime] = None


@dataclass
class QueryResult:
    """SQL查询结果"""
    sql: str
    data: List[Dict[str, Any]] = field(default_factory=list)
    execution_time: float = 0.0
    row_count: int = 0
    columns: List[str] = field(default_factory=list)


@dataclass
class DataSourceContext:
    """数据源级别的上下文信息"""
    data_source_id: str
    data_source_type: str  # doris/mysql/postgresql
    connection_info: Dict[str, str] = field(default_factory=dict)
    
    # 表结构信息
    available_tables: List[str] = field(default_factory=list)
    table_schemas: Dict[str, TableSchema] = field(default_factory=dict)
    
    # 查询历史和结果
    executed_queries: List[QueryResult] = field(default_factory=list)
    cached_data: Dict[str, QueryResult] = field(default_factory=dict)
    
    # 数据源能力
    supports_aggregation: bool = True
    supports_window_functions: bool = True
    max_query_timeout: int = 30


@dataclass
class FailedSQL:
    """失败的SQL信息"""
    sql: str
    error: str
    placeholder_name: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionError:
    """执行错误信息"""
    error_type: str
    error_message: str
    step: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    recoverable: bool = True


@dataclass
class ChartData:
    """图表数据"""
    chart_type: str
    data: List[Dict[str, Any]] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    series: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ExecutionContext:
    """执行过程中的动态上下文"""
    session_id: str
    current_step: str = "初始化"
    
    # SQL执行状态
    generated_sqls: Dict[str, str] = field(default_factory=dict)
    failed_sqls: List[FailedSQL] = field(default_factory=list)
    sql_repair_attempts: Dict[str, int] = field(default_factory=dict)
    
    # 数据转换状态
    raw_data: Dict[str, List[Dict]] = field(default_factory=dict)
    transformed_data: Dict[str, ChartData] = field(default_factory=dict)
    
    # 进度跟踪
    completed_placeholders: Set[str] = field(default_factory=set)
    failed_placeholders: Set[str] = field(default_factory=set)
    current_placeholder: Optional[str] = None
    
    # 错误信息
    errors: List[ExecutionError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ContextManager:
    """统一的上下文管理器"""
    
    def __init__(self):
        self.task_context: Optional[TaskContext] = None
        self.template_context: Optional[TemplateContext] = None
        self.data_source_context: Optional[DataSourceContext] = None
        self.execution_context: Optional[ExecutionContext] = None
        self._change_listeners = []
    
    async def initialize(
        self, 
        task_id: str, 
        user_id: str,
        template_id: str, 
        data_source_id: str
    ):
        """初始化所有上下文信息"""
        try:
            # 并行加载上下文
            contexts = await asyncio.gather(
                self._load_task_context(task_id, user_id),
                self._load_template_context(template_id),
                self._load_data_source_context(data_source_id),
                self._create_execution_context(),
                return_exceptions=True
            )
            
            # 检查加载结果
            for i, context in enumerate(contexts):
                if isinstance(context, Exception):
                    logger.error(f"上下文加载失败 (index {i}): {context}")
                    raise context
            
            self.task_context = contexts[0]
            self.template_context = contexts[1]
            self.data_source_context = contexts[2]
            self.execution_context = contexts[3]
            
            logger.info("所有上下文初始化完成")
            
        except Exception as e:
            logger.error(f"上下文初始化失败: {e}")
            raise
    
    async def _load_task_context(self, task_id: str, user_id: str) -> TaskContext:
        """加载任务上下文"""
        # 这里应该从数据库加载任务信息
        # 目前返回默认值
        return TaskContext(
            task_id=task_id,
            user_id=user_id,
            time_range=TimeRange.DAY,
            execution_mode=ExecutionMode.MANUAL
        )
    
    async def _load_template_context(self, template_id: str) -> TemplateContext:
        """加载模板上下文"""
        # 这里应该从数据库加载模板信息
        # 目前返回默认值
        return TemplateContext(
            template_id=template_id,
            template_name=f"模板_{template_id}",
            template_content="",
            placeholder_count=0
        )
    
    async def _load_data_source_context(self, data_source_id: str) -> DataSourceContext:
        """加载数据源上下文"""
        # 这里应该从数据库加载数据源信息
        # 目前返回默认值
        return DataSourceContext(
            data_source_id=data_source_id,
            data_source_type="doris"
        )
    
    async def _create_execution_context(self) -> ExecutionContext:
        """创建执行上下文"""
        import uuid
        return ExecutionContext(
            session_id=str(uuid.uuid4()),
            current_step="初始化"
        )
    
    def get_context_for_agent(self, agent_type: str) -> Dict[str, Any]:
        """为特定Agent提供相关上下文"""
        base_context = {
            "task": self.task_context,
            "execution": self.execution_context
        }
        
        if agent_type == "sql_generator":
            return {
                **base_context,
                "template": self.template_context,
                "data_source": self.data_source_context,
                "failed_sqls": self.execution_context.failed_sqls if self.execution_context else []
            }
        elif agent_type == "sql_repair":
            return {
                **base_context,
                "data_source": self.data_source_context,
                "failed_sqls": self.execution_context.failed_sqls if self.execution_context else [],
                "repair_history": self.execution_context.sql_repair_attempts if self.execution_context else {}
            }
        elif agent_type == "data_transformer":
            return {
                **base_context,
                "raw_data": self.execution_context.raw_data if self.execution_context else {},
                "chart_requirements": self.template_context.chart_requirements if self.template_context else []
            }
        
        return base_context
    
    def update_execution_state(self, update: Dict[str, Any]):
        """更新执行状态"""
        if not self.execution_context:
            logger.warning("执行上下文未初始化，无法更新状态")
            return
        
        if "completed_placeholder" in update:
            self.execution_context.completed_placeholders.add(
                update["completed_placeholder"]
            )
        
        if "failed_sql" in update:
            self.execution_context.failed_sqls.append(update["failed_sql"])
        
        if "generated_sql" in update:
            placeholder, sql = update["generated_sql"]
            self.execution_context.generated_sqls[placeholder] = sql
        
        if "current_step" in update:
            self.execution_context.current_step = update["current_step"]
        
        # 触发上下文变化事件
        self._notify_context_change(update)
    
    def _notify_context_change(self, update: Dict[str, Any]):
        """通知上下文变化"""
        for listener in self._change_listeners:
            try:
                listener(update)
            except Exception as e:
                logger.error(f"上下文变化通知失败: {e}")
    
    def add_change_listener(self, listener):
        """添加上下文变化监听器"""
        self._change_listeners.append(listener)
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        if not self.execution_context:
            return {"status": "未初始化"}
        
        total_placeholders = len(self.template_context.placeholders) if self.template_context else 0
        completed = len(self.execution_context.completed_placeholders)
        failed = len(self.execution_context.failed_placeholders)
        
        return {
            "current_step": self.execution_context.current_step,
            "total_placeholders": total_placeholders,
            "completed_placeholders": completed,
            "failed_placeholders": failed,
            "progress_percentage": (completed / total_placeholders * 100) if total_placeholders > 0 else 0,
            "errors_count": len(self.execution_context.errors),
            "warnings_count": len(self.execution_context.warnings)
        }