"""
流水线管理API响应模式
确保与前端API客户端完全兼容
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from .base import APIResponse


class PlaceholderItem(BaseModel):
    """占位符项"""

    text: str = Field(..., description="占位符文本")
    kind: str = Field(..., description="占位符类型: period, statistical, chart")
    needs_reanalysis: bool = Field(..., description="是否需要重新分析")
    confidence: Optional[float] = Field(None, description="识别置信度")
    meta: Optional[Dict[str, Any]] = Field(None, description="元数据")


class PlaceholderStats(BaseModel):
    """占位符统计信息"""

    total: int = Field(..., description="总占位符数量")
    need_reanalysis: int = Field(..., description="需要重新分析的数量")
    by_kind: Dict[str, int] = Field(..., description="按类型分组统计")


class ETLScanResponse(BaseModel):
    """ETL前扫描响应数据"""

    success: bool = Field(..., description="扫描是否成功")
    items: List[PlaceholderItem] = Field(..., description="识别的占位符列表")
    stats: PlaceholderStats = Field(..., description="统计信息")
    template_id: str = Field(..., description="模板ID")
    data_source_id: str = Field(..., description="数据源ID")
    scan_time: datetime = Field(default_factory=datetime.now, description="扫描时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ResolvedPlaceholder(BaseModel):
    """已解析占位符"""

    kind: str = Field(..., description="占位符类型")
    value: Any = Field(..., description="解析后的值")
    meta: Optional[Dict[str, Any]] = Field(None, description="元数据")


class ReportAssemblyResponse(BaseModel):
    """报告组装响应数据"""

    success: bool = Field(..., description="组装是否成功")
    content: str = Field(..., description="生成的报告内容")
    artifacts: List[str] = Field(default_factory=list, description="生成的文件路径列表")
    resolved: Dict[str, ResolvedPlaceholder] = Field(..., description="解析后的占位符映射")
    template_id: str = Field(..., description="模板ID")
    data_source_id: str = Field(..., description="数据源ID")
    execution_time: datetime = Field(default_factory=datetime.now, description="执行时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskStatus(BaseModel):
    """任务状态"""

    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态: pending, running, completed, failed")
    progress: float = Field(0.0, description="进度百分比 0-100")
    message: Optional[str] = Field(None, description="状态消息")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthStatusDetail(BaseModel):
    """健康状态详情"""

    component: str = Field(..., description="组件名称")
    status: str = Field(..., description="状态: healthy, degraded, unhealthy")
    message: str = Field(..., description="状态描述")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


class PipelineHealthResponse(BaseModel):
    """流水线健康检查响应数据"""

    status: str = Field(..., description="整体状态: healthy, degraded, unhealthy")
    ready_for_pipeline: bool = Field(..., description="是否准备好运行流水线")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    components: List[HealthStatusDetail] = Field(..., description="组件状态详情")
    recommendations: List[str] = Field(default_factory=list, description="改进建议")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MonitorStats(BaseModel):
    """监控统计数据"""

    active_tasks: int = Field(0, description="活跃任务数")
    completed_tasks_today: int = Field(0, description="今日完成任务数")
    failed_tasks_today: int = Field(0, description="今日失败任务数")
    avg_execution_time: float = Field(0.0, description="平均执行时间(秒)")
    system_uptime: float = Field(0.0, description="系统运行时间(小时)")
    last_update: datetime = Field(default_factory=datetime.now, description="最后更新时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# 为前端API客户端兼容性创建别名
class TemplateAnalysisResponse(ETLScanResponse):
    """模板分析响应 - 前端兼容性别名"""
    pass


# 响应构建工具函数
def create_etl_scan_response(
    items: List[PlaceholderItem],
    stats: PlaceholderStats,
    template_id: str,
    data_source_id: str,
    success: bool = True,
    message: str = "扫描完成"
) -> APIResponse[ETLScanResponse]:
    """创建ETL扫描响应"""

    data = ETLScanResponse(
        success=success,
        items=items,
        stats=stats,
        template_id=template_id,
        data_source_id=data_source_id
    )

    return APIResponse[ETLScanResponse](
        success=success,
        message=message,
        data=data
    )


def create_report_assembly_response(
    content: str,
    resolved: Dict[str, ResolvedPlaceholder],
    template_id: str,
    data_source_id: str,
    artifacts: List[str] = None,
    success: bool = True,
    message: str = "报告生成完成"
) -> APIResponse[ReportAssemblyResponse]:
    """创建报告组装响应"""

    data = ReportAssemblyResponse(
        success=success,
        content=content,
        artifacts=artifacts or [],
        resolved=resolved,
        template_id=template_id,
        data_source_id=data_source_id
    )

    return APIResponse[ReportAssemblyResponse](
        success=success,
        message=message,
        data=data
    )


def create_pipeline_health_response(
    status: str,
    ready_for_pipeline: bool,
    components: List[HealthStatusDetail],
    recommendations: List[str] = None,
    message: str = "健康检查完成"
) -> APIResponse[PipelineHealthResponse]:
    """创建流水线健康检查响应"""

    data = PipelineHealthResponse(
        status=status,
        ready_for_pipeline=ready_for_pipeline,
        components=components,
        recommendations=recommendations or []
    )

    return APIResponse[PipelineHealthResponse](
        success=status != "unhealthy",
        message=message,
        data=data
    )


def create_task_status_response(
    task: TaskStatus,
    message: str = "任务状态查询成功"
) -> APIResponse[TaskStatus]:
    """创建任务状态响应"""

    return APIResponse[TaskStatus](
        success=True,
        message=message,
        data=task
    )


def create_monitor_stats_response(
    stats: MonitorStats,
    message: str = "监控数据获取成功"
) -> APIResponse[MonitorStats]:
    """创建监控统计响应"""

    return APIResponse[MonitorStats](
        success=True,
        message=message,
        data=stats
    )