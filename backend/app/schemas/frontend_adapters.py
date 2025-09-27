"""
前端组件数据适配器
确保后端数据格式与前端组件完全兼容
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field


class ChartDataSource(BaseModel):
    """图表数据源信息 - 前端ChartPreview组件兼容"""
    sql_query: Optional[str] = Field(None, description="SQL查询语句")
    execution_time_ms: Optional[int] = Field(None, description="执行时间(毫秒)")
    row_count: Optional[int] = Field(None, description="数据行数")
    data_quality_score: Optional[float] = Field(None, description="数据质量分数(0-1)")


class ChartElements(BaseModel):
    """图表元素信息"""
    series_count: Optional[int] = Field(None, description="数据系列数量")
    chart_type: Optional[str] = Field(None, description="图表类型")
    dimensions: Optional[List[str]] = Field(None, description="维度列表")
    measures: Optional[List[str]] = Field(None, description="度量列表")


class ChartDataSummary(BaseModel):
    """图表数据摘要"""
    min_value: Optional[float] = Field(None, description="最小值")
    max_value: Optional[float] = Field(None, description="最大值")
    avg_value: Optional[float] = Field(None, description="平均值")
    total_value: Optional[float] = Field(None, description="总值")
    null_count: Optional[int] = Field(None, description="空值数量")


class FrontendChartMetadata(BaseModel):
    """前端图表元数据 - 完全兼容ChartPreview组件"""
    data_points: Optional[int] = Field(None, description="数据点数量")
    chart_elements: Optional[ChartElements] = Field(None, description="图表元素信息")
    data_summary: Optional[ChartDataSummary] = Field(None, description="数据摘要")
    generation_time: Optional[str] = Field(None, description="生成时间(ISO格式)")
    data_source: Optional[ChartDataSource] = Field(None, description="数据源信息")


class FrontendChartData(BaseModel):
    """前端图表数据格式"""
    echartsConfig: Dict[str, Any] = Field(..., description="ECharts配置对象")
    chartType: str = Field(..., description="图表类型")
    chartData: List[Dict[str, Any]] = Field(..., description="原始图表数据")
    metadata: Optional[FrontendChartMetadata] = Field(None, description="图表元数据")
    title: Optional[str] = Field(None, description="图表标题")


class PlaceholderDisplayInfo(BaseModel):
    """占位符显示信息 - 前端组件兼容"""
    text: str = Field(..., description="占位符文本")
    kind: str = Field(..., description="占位符类型")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="描述")
    status: str = Field("pending", description="处理状态: pending, processing, completed, failed")
    confidence: Optional[float] = Field(None, description="识别置信度")
    needs_reanalysis: bool = Field(False, description="是否需要重新分析")

    # UI样式属性
    badge_color: str = Field("default", description="标签颜色")
    icon: Optional[str] = Field(None, description="图标名称")
    tooltip: Optional[str] = Field(None, description="提示信息")


class AnalysisProgressInfo(BaseModel):
    """分析进度信息 - 前端进度组件兼容"""
    current_step: int = Field(..., description="当前步骤")
    total_steps: int = Field(..., description="总步骤数")
    step_name: str = Field(..., description="当前步骤名称")
    progress_percent: float = Field(..., description="进度百分比(0-100)")
    status: str = Field("running", description="状态: pending, running, completed, failed")
    estimated_remaining: Optional[int] = Field(None, description="预计剩余时间(秒)")

    # 步骤详情
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="步骤详情列表")


class ErrorDisplayInfo(BaseModel):
    """错误显示信息 - 前端错误组件兼容"""
    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误消息")
    user_friendly_message: str = Field(..., description="用户友好的错误消息")
    error_type: str = Field("system", description="错误类型: validation, system, network, permission")
    severity: str = Field("error", description="严重性: info, warning, error, critical")

    # 错误详情和建议
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    suggestions: List[str] = Field(default_factory=list, description="解决建议")
    support_info: Optional[Dict[str, str]] = Field(None, description="支持信息")


def adapt_placeholder_for_frontend(
    backend_placeholder: Dict[str, Any]
) -> PlaceholderDisplayInfo:
    """将后端占位符数据适配为前端显示格式"""

    # 获取占位符类型对应的显示信息
    kind_display_map = {
        "period": {
            "display_name": "时间周期",
            "description": "自动计算时间范围的占位符",
            "badge_color": "info",
            "icon": "calendar",
            "tooltip": "基于任务调度自动计算报告周期"
        },
        "statistical": {
            "display_name": "统计数据",
            "description": "通过SQL查询获取统计结果",
            "badge_color": "success",
            "icon": "chart-bar",
            "tooltip": "从数据源获取统计指标"
        },
        "chart": {
            "display_name": "图表",
            "description": "生成数据可视化图表",
            "badge_color": "warning",
            "icon": "chart-pie",
            "tooltip": "根据数据生成可视化图表"
        }
    }

    kind = backend_placeholder.get("kind", "unknown")
    display_info = kind_display_map.get(kind, {
        "display_name": kind,
        "description": "未知类型占位符",
        "badge_color": "default",
        "icon": "question-mark",
        "tooltip": "未识别的占位符类型"
    })

    return PlaceholderDisplayInfo(
        text=backend_placeholder.get("text", ""),
        kind=kind,
        display_name=display_info["display_name"],
        description=display_info.get("description"),
        status="completed" if not backend_placeholder.get("needs_reanalysis", False) else "pending",
        confidence=backend_placeholder.get("confidence"),
        needs_reanalysis=backend_placeholder.get("needs_reanalysis", False),
        badge_color=display_info["badge_color"],
        icon=display_info.get("icon"),
        tooltip=display_info.get("tooltip")
    )


def adapt_chart_for_frontend(
    echarts_config: Dict[str, Any],
    chart_type: str,
    raw_data: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None
) -> FrontendChartData:
    """将后端图表数据适配为前端ChartPreview组件格式"""

    # 构建图表元数据
    chart_metadata = None
    if metadata:
        data_source_info = None
        if "data_source" in metadata:
            ds = metadata["data_source"]
            data_source_info = ChartDataSource(
                sql_query=ds.get("sql_query"),
                execution_time_ms=ds.get("execution_time_ms"),
                row_count=ds.get("row_count"),
                data_quality_score=ds.get("data_quality_score")
            )

        chart_elements_info = None
        if "chart_elements" in metadata:
            ce = metadata["chart_elements"]
            chart_elements_info = ChartElements(
                series_count=ce.get("series_count"),
                chart_type=ce.get("chart_type", chart_type),
                dimensions=ce.get("dimensions"),
                measures=ce.get("measures")
            )

        data_summary_info = None
        if "data_summary" in metadata:
            ds_sum = metadata["data_summary"]
            data_summary_info = ChartDataSummary(
                min_value=ds_sum.get("min_value"),
                max_value=ds_sum.get("max_value"),
                avg_value=ds_sum.get("avg_value"),
                total_value=ds_sum.get("total_value"),
                null_count=ds_sum.get("null_count")
            )

        chart_metadata = FrontendChartMetadata(
            data_points=len(raw_data),
            chart_elements=chart_elements_info,
            data_summary=data_summary_info,
            generation_time=metadata.get("generation_time", datetime.now().isoformat()),
            data_source=data_source_info
        )

    return FrontendChartData(
        echartsConfig=echarts_config,
        chartType=chart_type,
        chartData=raw_data,
        metadata=chart_metadata,
        title=metadata.get("title") if metadata else None
    )


def adapt_analysis_progress_for_frontend(
    current_step: int,
    total_steps: int,
    step_name: str,
    status: str,
    progress_percent: Optional[float] = None
) -> AnalysisProgressInfo:
    """将后端分析进度适配为前端进度组件格式"""

    # 如果没有提供进度百分比，根据步骤计算
    if progress_percent is None:
        progress_percent = (current_step / total_steps) * 100

    # 预定义的分析步骤
    default_steps = [
        {"name": "准备分析环境", "description": "初始化分析组件", "status": "completed" if current_step > 1 else "active"},
        {"name": "扫描模板占位符", "description": "识别模板中的占位符", "status": "completed" if current_step > 2 else ("active" if current_step == 2 else "pending")},
        {"name": "分析占位符类型", "description": "确定占位符类型和处理方式", "status": "completed" if current_step > 3 else ("active" if current_step == 3 else "pending")},
        {"name": "生成处理结果", "description": "完成分析并生成结果", "status": "completed" if current_step > 4 else ("active" if current_step == 4 else "pending")},
    ]

    return AnalysisProgressInfo(
        current_step=current_step,
        total_steps=total_steps,
        step_name=step_name,
        progress_percent=progress_percent,
        status=status,
        steps=default_steps[:total_steps]
    )


def adapt_error_for_frontend(
    error_message: str,
    error_type: str = "system",
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> ErrorDisplayInfo:
    """将后端错误适配为前端错误显示格式"""

    # 生成用户友好的错误消息
    user_friendly_messages = {
        "template_not_found": "模板不存在，请检查模板ID是否正确",
        "data_source_not_found": "数据源不存在，请检查数据源配置",
        "database_connection_error": "数据库连接失败，请检查网络连接和数据源配置",
        "sql_execution_error": "数据查询失败，请检查数据源和权限配置",
        "template_parse_error": "模板格式错误，请检查模板内容",
        "agent_service_unavailable": "AI分析服务暂时不可用，请稍后重试",
        "permission_denied": "权限不足，请联系管理员",
        "rate_limit_exceeded": "请求过于频繁，请稍后重试"
    }

    friendly_message = user_friendly_messages.get(error_code or "", error_message)

    # 根据错误类型生成建议
    suggestions_map = {
        "template_not_found": ["检查模板ID是否正确", "确认模板是否已删除", "联系管理员确认权限"],
        "data_source_not_found": ["检查数据源配置", "确认数据源是否激活", "联系管理员"],
        "database_connection_error": ["检查网络连接", "确认数据源配置", "联系系统管理员"],
        "sql_execution_error": ["检查数据源权限", "确认数据表是否存在", "联系数据库管理员"],
        "agent_service_unavailable": ["等待几分钟后重试", "检查系统状态", "联系技术支持"],
        "permission_denied": ["联系管理员申请权限", "检查用户角色配置"],
        "rate_limit_exceeded": ["等待一段时间后重试", "减少请求频率"]
    }

    suggestions = suggestions_map.get(error_code or "", ["检查输入参数", "稍后重试", "联系技术支持"])

    return ErrorDisplayInfo(
        error_code=error_code or "unknown_error",
        error_message=error_message,
        user_friendly_message=friendly_message,
        error_type=error_type,
        severity="error",
        details=details,
        suggestions=suggestions,
        support_info={
            "contact": "support@autoreportai.com",
            "documentation": "/help/troubleshooting",
            "status_page": "/status"
        }
    )