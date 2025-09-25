"""
任务驱动的上下文构建服务

专门为Agent React迭代设计，结合模版信息、数据源信息和任务信息
提供精确的上下文用于SQL生成质量保证
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """任务类型枚举"""
    DAILY_REPORT = "daily_report"
    WEEKLY_REPORT = "weekly_report"
    MONTHLY_REPORT = "monthly_report"
    QUARTERLY_REPORT = "quarterly_report"
    ANNUAL_REPORT = "annual_report"
    CUSTOM_PERIOD = "custom_period"
    REAL_TIME = "real_time"


class PlaceholderType(Enum):
    """占位符类型枚举"""
    TIME_SERIES = "time_series"
    AGGREGATION = "aggregation"
    COMPARISON = "comparison"
    RANKING = "ranking"
    CALCULATION = "calculation"
    FILTER = "filter"


@dataclass
class TimeRange:
    """时间范围"""
    start_date: datetime
    end_date: datetime
    period_type: TaskType
    time_zone: str = "Asia/Shanghai"

    def to_sql_params(self) -> Dict[str, str]:
        """转换为SQL参数"""
        return {
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "start_datetime": self.start_date.strftime("%Y-%m-%d %H:%M:%S"),
            "end_datetime": self.end_date.strftime("%Y-%m-%d %H:%M:%S")
        }


@dataclass
class TemplateContextInfo:
    """模版上下文信息"""
    template_id: str
    template_name: str
    template_type: str
    placeholders: List[Dict[str, Any]]
    business_domain: Optional[str] = None
    expected_frequency: Optional[TaskType] = None

    @property
    def placeholder_count(self) -> int:
        return len(self.placeholders)


@dataclass
class DataSourceContextInfo:
    """数据源上下文信息"""
    data_source_id: str
    data_source_name: str
    source_type: str
    connection_config: Dict[str, Any]
    available_tables: Optional[List[str]] = None
    schema_info: Optional[Dict[str, Any]] = None
    connection_healthy: bool = True

    @property
    def database_name(self) -> Optional[str]:
        return self.connection_config.get("database")


@dataclass
class TaskContextInfo:
    """任务上下文信息"""
    task_id: str
    task_type: TaskType
    current_placeholder: Dict[str, Any]
    placeholder_index: int
    total_placeholders: int
    execution_context: Dict[str, Any] = field(default_factory=dict)
    # 用户配置的周期信息
    user_task_config: Optional[Dict[str, Any]] = None

    @property
    def is_first_placeholder(self) -> bool:
        return self.placeholder_index == 0

    @property
    def is_last_placeholder(self) -> bool:
        return self.placeholder_index == self.total_placeholders - 1

    @property
    def progress_percentage(self) -> float:
        if self.total_placeholders == 0:
            return 100.0
        return (self.placeholder_index + 1) / self.total_placeholders * 100


@dataclass
class DerivedContextInfo:
    """派生上下文信息"""
    time_range: TimeRange
    sql_parameters: Dict[str, Any]
    business_rules: List[str] = field(default_factory=list)
    data_quality_hints: List[str] = field(default_factory=list)
    performance_hints: List[str] = field(default_factory=list)

    def get_full_sql_context(self) -> Dict[str, Any]:
        """获取完整的SQL上下文"""
        context = self.sql_parameters.copy()
        context.update(self.time_range.to_sql_params())
        return context


@dataclass
class TaskDrivenContext:
    """任务驱动的完整上下文"""
    template_info: TemplateContextInfo
    data_source_info: DataSourceContextInfo
    task_info: TaskContextInfo
    derived_context: DerivedContextInfo
    user_id: str
    organization_id: Optional[str] = None

    def to_react_context(self) -> Dict[str, Any]:
        """转换为React Agent所需的上下文格式"""
        return {
            "task_id": self.task_info.task_id,
            "user_id": self.user_id,
            "template": {
                "id": self.template_info.template_id,
                "name": self.template_info.template_name,
                "type": self.template_info.template_type,
                "business_domain": self.template_info.business_domain
            },
            "data_source": {
                "id": self.data_source_info.data_source_id,
                "name": self.data_source_info.data_source_name,
                "type": self.data_source_info.source_type,
                "database": self.data_source_info.database_name,
                "tables": self.data_source_info.available_tables or []
            },
            "current_placeholder": self.task_info.current_placeholder,

            # 智能时间上下文 - Agent将基于此信息推导准确的时间范围
            "time_context": {
                "task_schedule": self.derived_context.sql_parameters.get("task_schedule", {}),
                "execution_time": datetime.now().isoformat(),
                "timezone": self.derived_context.time_range.time_zone,
                "agent_instructions": self._generate_time_instructions()
            },

            "sql_parameters": self.derived_context.get_full_sql_context(),
            "business_rules": self.derived_context.business_rules,
            "progress": {
                "current": self.task_info.placeholder_index + 1,
                "total": self.task_info.total_placeholders,
                "percentage": self.task_info.progress_percentage
            }
        }

    def _generate_time_instructions(self) -> str:
        """为Agent生成时间推导指令"""
        task_schedule = self.derived_context.sql_parameters.get("task_schedule", {})
        cron_expr = task_schedule.get("cron_expression", "0 0 * * *")
        description = task_schedule.get("description", "")
        offset = task_schedule.get("data_period_offset", 1)

        return f"""
基于任务调度信息推导数据时间范围：
- 任务周期：{cron_expr} ({description})
- 当前执行时间：{task_schedule.get("current_execution_time", "")}
- 数据周期偏移：{offset}个周期前的数据
- 时区：{task_schedule.get("timezone", "Asia/Shanghai")}

请根据cron表达式智能推导出准确的数据时间范围用于SQL查询。
例如：如果是每月1号执行的月报，应查询上个月的数据；
如果是每周一执行的周报，应查询上周的数据。
"""


class TaskDrivenContextBuilder:
    """任务驱动上下文构建器"""

    def __init__(self, container=None):
        self.container = container
        # 适配当前架构的依赖注入
        self.template_repository = None
        self.user_data_source_service = None

        if container:
            try:
                # 从容器获取服务实例
                from app.infrastructure.repositories.template_repository import TemplateRepository
                from app.services.infrastructure.data_sources.user_data_source_service import UserDataSourceService

                self.template_repository = TemplateRepository()
                self.user_data_source_service = UserDataSourceService(container)
            except Exception as e:
                logger.warning(f"Failed to initialize task context dependencies: {e}")

    async def build_task_driven_context(
        self,
        user_id: str,
        template_id: str,
        data_source_id: str,
        task_definition: Dict[str, Any]
    ) -> TaskDrivenContext:
        """构建任务驱动上下文"""

        # 1. 获取模版信息
        template_info = await self._build_template_context(template_id)

        # 2. 获取数据源信息
        data_source_info = await self._build_data_source_context(
            user_id, data_source_id
        )

        # 3. 构建任务信息
        task_info = await self._build_task_context(task_definition, template_info)

        # 4. 派生上下文信息（时间范围等）
        derived_context = await self._build_derived_context(
            task_info, template_info, data_source_info
        )

        return TaskDrivenContext(
            template_info=template_info,
            data_source_info=data_source_info,
            task_info=task_info,
            derived_context=derived_context,
            user_id=user_id,
            organization_id=None  # 当前架构中暂无组织概念
        )

    async def _build_template_context(self, template_id: str) -> TemplateContextInfo:
        """构建模版上下文信息"""
        try:
            if self.template_repository:
                template = await self.template_repository.get(template_id)
                if template:
                    return TemplateContextInfo(
                        template_id=template_id,
                        template_name=template.get("name", ""),
                        template_type=template.get("type", "business_report"),
                        placeholders=template.get("placeholders", []),
                        business_domain=template.get("business_domain", "general"),
                        expected_frequency=TaskType.DAILY_REPORT  # 默认值
                    )
        except Exception as e:
            logger.warning(f"Failed to get template from repository: {e}")

        # 无法获取真实模板时，返回空信息（不使用mock占位符）
        return TemplateContextInfo(
            template_id=template_id,
            template_name="",
            template_type="business_report",
            placeholders=[],
            business_domain=None,
            expected_frequency=TaskType.DAILY_REPORT
        )

    async def _build_data_source_context(
        self, user_id: str, data_source_id: str
    ) -> DataSourceContextInfo:
        """构建数据源上下文信息"""
        try:
            if self.user_data_source_service:
                user_data_source = await self.user_data_source_service.get_user_data_source(
                    user_id=user_id,
                    data_source_id=data_source_id
                )

                if user_data_source:
                    return DataSourceContextInfo(
                        data_source_id=data_source_id,
                        data_source_name=user_data_source.name,
                        source_type=user_data_source.source_type,
                        connection_config=user_data_source.connection_config or {},
                        available_tables=user_data_source.get("available_tables", []),
                        schema_info=user_data_source.get("schema_info"),
                        connection_healthy=getattr(user_data_source, 'connection_healthy', True)
                    )
        except Exception as e:
            logger.warning(f"Failed to get data source from service: {e}")

        # 无法获取真实数据源时，返回空信息（不使用mock文案）
        return DataSourceContextInfo(
            data_source_id=data_source_id,
            data_source_name="",
            source_type="",
            connection_config={},
            available_tables=[],
            schema_info=None,
            connection_healthy=False
        )

    async def _build_task_context(
        self, task_definition: Dict[str, Any], template_info: TemplateContextInfo
    ) -> TaskContextInfo:
        """构建任务上下文信息"""
        task_type_str = task_definition.get("task_type", TaskType.DAILY_REPORT.value)
        try:
            task_type = TaskType(task_type_str)
        except ValueError:
            task_type = TaskType.DAILY_REPORT

        placeholder_index = task_definition.get("placeholder_index", 0)

        if placeholder_index >= len(template_info.placeholders):
            # 如果索引超出范围，使用第一个占位符
            placeholder_index = 0

        if template_info.placeholders:
            current_placeholder = template_info.placeholders[placeholder_index]
        else:
            # 如果没有占位符，创建一个默认的
            current_placeholder = {
                "id": "default_placeholder",
                "name": "默认占位符",
                "type": PlaceholderType.AGGREGATION.value
            }

        return TaskContextInfo(
            task_id=task_definition.get("task_id", f"task_{datetime.now().timestamp()}"),
            task_type=task_type,
            current_placeholder=current_placeholder,
            placeholder_index=placeholder_index,
            total_placeholders=len(template_info.placeholders) or 1,
            execution_context=task_definition.get("execution_context", {}),
            user_task_config=task_definition.get("user_task_config", {})
        )

    async def _build_derived_context(
        self,
        task_info: TaskContextInfo,
        template_info: TemplateContextInfo,
        data_source_info: DataSourceContextInfo
    ) -> DerivedContextInfo:
        """构建派生上下文信息"""

        # 1. 计算时间范围（基于用户配置）
        time_range = self._derive_time_range(task_info)

        # 2. 构建SQL参数
        sql_parameters = self._build_sql_parameters(
            task_info, template_info, data_source_info
        )

        # 3. 生成业务规则提示
        business_rules = self._generate_business_rules(
            task_info, template_info
        )

        # 4. 生成数据质量提示
        data_quality_hints = self._generate_data_quality_hints(
            data_source_info, task_info.current_placeholder
        )

        # 5. 生成性能优化提示
        performance_hints = self._generate_performance_hints(
            task_info.task_type, task_info.current_placeholder
        )

        return DerivedContextInfo(
            time_range=time_range,
            sql_parameters=sql_parameters,
            business_rules=business_rules,
            data_quality_hints=data_quality_hints,
            performance_hints=performance_hints
        )

    def _derive_time_range(self, task_info: TaskContextInfo) -> TimeRange:
        """简化的时间范围创建 - 将具体推导交给Agent处理"""
        user_config = task_info.user_task_config or {}

        # 优先使用用户配置的时间范围
        if user_config.get("custom_time_range"):
            custom_range = user_config["custom_time_range"]
            start_date = datetime.fromisoformat(custom_range["start_date"])
            end_date = datetime.fromisoformat(custom_range["end_date"])
            return TimeRange(
                start_date=start_date,
                end_date=end_date,
                period_type=TaskType.CUSTOM_PERIOD
            )

        # 如果没有自定义时间范围，创建一个包含必要信息的TimeRange
        # 具体的时间推导将由Agent基于cron表达式智能完成
        now = datetime.now()
        timezone_str = user_config.get("timezone", "Asia/Shanghai")

        return TimeRange(
            start_date=now,  # 占位符，Agent会基于cron表达式重新计算
            end_date=now,    # 占位符，Agent会基于cron表达式重新计算
            period_type=TaskType.CUSTOM_PERIOD,  # 让Agent自己推断
            time_zone=timezone_str
        )

    def _build_sql_parameters(
        self,
        task_info: TaskContextInfo,
        template_info: TemplateContextInfo,
        data_source_info: DataSourceContextInfo
    ) -> Dict[str, Any]:
        """构建SQL参数 - 包含时间上下文供Agent智能推导"""
        user_config = task_info.user_task_config or {}

        # 获取当前执行时间
        current_time = datetime.now()

        return {
            "database_name": data_source_info.database_name,
            "data_source_id": data_source_info.data_source_id,
            "placeholder_id": task_info.current_placeholder.get("id"),
            "placeholder_type": task_info.current_placeholder.get("type"),
            "template_id": template_info.template_id,
            "business_domain": template_info.business_domain,
            "task_type": task_info.task_type.value,

            # 时间上下文 - 供Agent智能推导使用
            "task_schedule": {
                "cron_expression": user_config.get("cron_expression", "0 0 * * *"),
                "timezone": user_config.get("timezone", "Asia/Shanghai"),
                "current_execution_time": current_time.isoformat(),
                "data_period_offset": user_config.get("data_period_offset", 1),
                "description": self._describe_cron_expression(user_config.get("cron_expression", "0 0 * * *"))
            }
        }

    def _describe_cron_expression(self, cron_expression: str) -> str:
        """为Agent提供cron表达式的自然语言描述"""
        descriptions = {
            "0 0 * * *": "每天凌晨执行",
            "0 0 * * 1": "每周一凌晨执行",
            "0 0 1 * *": "每月1号凌晨执行",
            "0 0 1 */3 *": "每季度1号凌晨执行",
            "0 0 1 1 *": "每年1月1号凌晨执行",
            "0 0 * * 1-5": "工作日凌晨执行",
            "0 */6 * * *": "每6小时执行一次",
            "*/30 * * * *": "每30分钟执行一次"
        }

        return descriptions.get(cron_expression, f"按表达式 {cron_expression} 执行")

    def _generate_business_rules(
        self,
        task_info: TaskContextInfo,
        template_info: TemplateContextInfo
    ) -> List[str]:
        """生成业务规则提示"""
        rules = []

        placeholder_type = task_info.current_placeholder.get("type")
        business_domain = template_info.business_domain

        if placeholder_type == PlaceholderType.TIME_SERIES.value:
            rules.append("确保时间序列数据的连续性和完整性")
            rules.append("使用适当的时间分组函数（日/周/月）")

        if placeholder_type == PlaceholderType.AGGREGATION.value:
            rules.append("注意处理NULL值对聚合函数的影响")
            rules.append("考虑数据去重的必要性")

        if business_domain == "sales":
            rules.append("销售金额应排除退货和取消订单")
            rules.append("确保货币单位的一致性")

        return rules

    def _generate_data_quality_hints(
        self,
        data_source_info: DataSourceContextInfo,
        current_placeholder: Dict[str, Any]
    ) -> List[str]:
        """生成数据质量提示"""
        hints = []

        if not data_source_info.connection_healthy:
            hints.append("数据源连接状态异常，请检查数据完整性")

        placeholder_type = current_placeholder.get("type")

        if placeholder_type == PlaceholderType.AGGREGATION.value:
            hints.append("检查是否存在异常值或离群数据")
            hints.append("验证聚合结果的合理性范围")

        if placeholder_type == PlaceholderType.TIME_SERIES.value:
            hints.append("检查时间字段的格式和时区")
            hints.append("确认数据时间范围的覆盖度")

        return hints

    def _generate_performance_hints(
        self,
        task_type: TaskType,
        current_placeholder: Dict[str, Any]
    ) -> List[str]:
        """生成性能优化提示"""
        hints = []

        if task_type in [TaskType.MONTHLY_REPORT, TaskType.QUARTERLY_REPORT, TaskType.ANNUAL_REPORT]:
            hints.append("大时间范围查询，建议使用分区表优化")
            hints.append("考虑使用汇总表减少计算量")

        placeholder_type = current_placeholder.get("type")

        if placeholder_type == PlaceholderType.TIME_SERIES.value:
            hints.append("确保时间字段上有适当的索引")

        if placeholder_type == PlaceholderType.AGGREGATION.value:
            hints.append("对于大数据量聚合，考虑使用近似算法")

        return hints

    async def build_context_for_placeholder(
        self,
        user_id: str,
        template_id: str,
        data_source_id: str,
        placeholder_name: str,
        task_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        为特定占位符构建任务上下文

        Args:
            user_id: 用户ID
            template_id: 模板ID
            data_source_id: 数据源ID
            placeholder_name: 占位符名称
            task_config: 任务配置

        Returns:
            包含占位符任务上下文的字典
        """
        try:
            # 创建任务定义
            task_definition = {
                "task_id": f"placeholder_{placeholder_name}_{datetime.now().timestamp()}",
                "task_type": TaskType.CUSTOM_PERIOD.value,
                "placeholder_index": 0,  # 将在构建过程中根据placeholder_name调整
                "execution_context": {"placeholder_name": placeholder_name},
                "user_task_config": task_config or {}
            }

            # 构建完整上下文
            context = await self.build_task_driven_context(
                user_id=user_id,
                template_id=template_id,
                data_source_id=data_source_id,
                task_definition=task_definition
            )

            return {
                "success": True,
                "context": context.to_react_context(),
                "placeholder_name": placeholder_name
            }

        except Exception as e:
            logger.error(f"Failed to build context for placeholder {placeholder_name}: {e}")
            return {
                "success": False,
                "error": f"Context building failed: {str(e)}"
            }
