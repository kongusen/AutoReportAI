"""
IAOP API数据模式定义

定义所有API请求和响应的数据结构
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class TaskType(str, Enum):
    """任务类型枚举"""
    STATISTICS = "statistics"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    LINE_CHART = "line_chart"
    TABLE = "table"
    SCATTER_CHART = "scatter_chart"
    RADAR_CHART = "radar_chart"


class ExecutionMode(str, Enum):
    """执行模式枚举"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    CONDITIONAL = "conditional"


class Priority(str, Enum):
    """优先级枚举"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# 请求模式
class PlaceholderRequest(BaseModel):
    """占位符解析请求"""
    template_content: str = Field(..., description="包含占位符的模板内容")
    data_source_id: Optional[str] = Field(None, description="数据源ID")
    context_params: Dict[str, Any] = Field(default_factory=dict, description="上下文参数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_content": "报告显示{{柱状图：过去6个月的销售额}}和{{统计：总用户数}}",
                "data_source_id": "doris_main",
                "context_params": {
                    "user_id": "admin",
                    "department": "sales"
                }
            }
        }


class ReportGenerationRequest(BaseModel):
    """报告生成请求"""
    placeholder_text: str = Field(..., description="单个占位符文本")
    task_type: Optional[TaskType] = Field(None, description="任务类型，如不指定则自动识别")
    data_source_context: Dict[str, Any] = Field(default_factory=dict, description="数据源上下文")
    template_context: Dict[str, Any] = Field(default_factory=dict, description="模板上下文")
    execution_mode: ExecutionMode = Field(ExecutionMode.SEQUENTIAL, description="执行模式")
    enable_cache: bool = Field(True, description="是否启用缓存")
    
    class Config:
        json_schema_extra = {
            "example": {
                "placeholder_text": "柱状图：过去6个月的销售额",
                "data_source_context": {
                    "tables": [{"name": "sales_orders", "columns": [...]}]
                },
                "execution_mode": "sequential",
                "enable_cache": True
            }
        }


class AgentExecutionRequest(BaseModel):
    """Agent执行请求"""
    agent_name: str = Field(..., description="Agent名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="执行参数")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="上下文数据")
    timeout: Optional[float] = Field(30.0, description="超时时间（秒）")


class BatchProcessingRequest(BaseModel):
    """批量处理请求"""
    requests: List[ReportGenerationRequest] = Field(..., description="批量请求列表")
    execution_mode: ExecutionMode = Field(ExecutionMode.PARALLEL, description="批量执行模式")
    max_concurrency: int = Field(5, description="最大并发数")


# 响应模式
class InsightResponse(BaseModel):
    """洞察响应"""
    type: str = Field(..., description="洞察类型")
    title: str = Field(..., description="洞察标题")
    description: str = Field(..., description="洞察描述")
    importance: float = Field(..., description="重要性评分(0-1)")
    confidence: float = Field(..., description="置信度(0-1)")
    business_impact: Optional[str] = Field(None, description="业务影响")
    data_points: List[Any] = Field(default_factory=list, description="相关数据点")


class RecommendationResponse(BaseModel):
    """建议响应"""
    type: str = Field(..., description="建议类型")
    title: str = Field(..., description="建议标题")
    description: str = Field(..., description="建议描述")
    priority: Priority = Field(..., description="优先级")
    timeframe: str = Field(..., description="执行时间框架")
    expected_impact: str = Field(..., description="预期影响")


class ChartConfigResponse(BaseModel):
    """图表配置响应"""
    chart_type: str = Field(..., description="图表类型")
    echarts_config: Dict[str, Any] = Field(..., description="ECharts配置JSON")
    chart_data: List[Dict[str, Any]] = Field(..., description="图表数据")
    metadata: Dict[str, Any] = Field(..., description="图表元数据")
    chart_options: Dict[str, Any] = Field(..., description="图表选项")


class NarrativeResponse(BaseModel):
    """叙述响应"""
    narrative_text: str = Field(..., description="主要叙述文本")
    key_insights: List[InsightResponse] = Field(..., description="关键洞察")
    recommendations: List[RecommendationResponse] = Field(..., description="建议列表")
    structured_narrative: Dict[str, Any] = Field(..., description="结构化叙述")
    narrative_metadata: Dict[str, Any] = Field(..., description="叙述元数据")


class ReportResponse(BaseModel):
    """报告生成响应"""
    success: bool = Field(..., description="执行是否成功")
    task_type: str = Field(..., description="任务类型")
    metric: str = Field(..., description="指标名称")
    
    # 核心结果
    chart_config: Optional[ChartConfigResponse] = Field(None, description="图表配置")
    narrative: Optional[NarrativeResponse] = Field(None, description="叙述内容")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="统计数据")
    
    # 执行信息
    execution_time: float = Field(..., description="执行时间（秒）")
    agent_execution_path: List[str] = Field(..., description="Agent执行路径")
    context_summary: Dict[str, Any] = Field(default_factory=dict, description="上下文摘要")
    
    # 错误信息
    error: Optional[str] = Field(None, description="错误信息")
    warnings: List[str] = Field(default_factory=list, description="警告信息")


class BatchProcessingResponse(BaseModel):
    """批量处理响应"""
    success: bool = Field(..., description="批量处理是否成功")
    total_requests: int = Field(..., description="总请求数")
    successful_requests: int = Field(..., description="成功请求数")
    failed_requests: int = Field(..., description="失败请求数")
    results: List[ReportResponse] = Field(..., description="处理结果列表")
    execution_time: float = Field(..., description="总执行时间")
    summary: Dict[str, Any] = Field(..., description="执行摘要")


class AgentStatusResponse(BaseModel):
    """Agent状态响应"""
    name: str = Field(..., description="Agent名称")
    status: str = Field(..., description="Agent状态")
    capabilities: List[str] = Field(..., description="能力列表")
    requirements: List[str] = Field(..., description="上下文要求")
    priority: int = Field(..., description="优先级")
    last_execution: Optional[datetime] = Field(None, description="最后执行时间")
    execution_count: int = Field(0, description="执行次数")
    success_rate: float = Field(1.0, description="成功率")
    average_execution_time: float = Field(0.0, description="平均执行时间")


class SystemStatusResponse(BaseModel):
    """系统状态响应"""
    status: str = Field(..., description="系统状态")
    version: str = Field(..., description="版本信息")
    uptime: float = Field(..., description="运行时间（秒）")
    
    # Agent信息
    total_agents: int = Field(..., description="总Agent数")
    active_agents: int = Field(..., description="活跃Agent数")
    agent_chains: List[str] = Field(..., description="Agent链列表")
    
    # 执行统计
    total_executions: int = Field(0, description="总执行次数")
    successful_executions: int = Field(0, description="成功执行次数")
    average_execution_time: float = Field(0.0, description="平均执行时间")
    
    # 系统资源
    cpu_usage: Optional[float] = Field(None, description="CPU使用率")
    memory_usage: Optional[float] = Field(None, description="内存使用率")
    active_contexts: int = Field(0, description="活跃上下文数")


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(False, description="操作是否成功")
    error: str = Field(..., description="错误信息")
    error_type: str = Field(..., description="错误类型")
    error_code: Optional[str] = Field(None, description="错误代码")
    details: Dict[str, Any] = Field(default_factory=dict, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="错误时间")
    trace_id: Optional[str] = Field(None, description="追踪ID")


# 配置模式
class AgentConfig(BaseModel):
    """Agent配置"""
    name: str = Field(..., description="Agent名称")
    enabled: bool = Field(True, description="是否启用")
    priority: int = Field(50, description="优先级")
    timeout: float = Field(30.0, description="超时时间")
    retry_count: int = Field(3, description="重试次数")
    cache_enabled: bool = Field(True, description="是否启用缓存")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Agent参数")


class ExecutionPlanConfig(BaseModel):
    """执行计划配置"""
    name: str = Field(..., description="计划名称")
    enabled: bool = Field(True, description="是否启用")
    mode: ExecutionMode = Field(..., description="执行模式")
    fail_fast: bool = Field(True, description="遇到错误是否快速失败")
    agents: List[str] = Field(..., description="包含的Agent列表")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="执行条件")


class IAOPConfig(BaseModel):
    """IAOP系统配置"""
    debug_mode: bool = Field(False, description="调试模式")
    max_concurrency: int = Field(10, description="最大并发数")
    default_timeout: float = Field(60.0, description="默认超时时间")
    cache_enabled: bool = Field(True, description="是否启用缓存")
    cache_ttl: int = Field(3600, description="缓存TTL（秒）")
    
    # Agent配置
    agents: List[AgentConfig] = Field(default_factory=list, description="Agent配置列表")
    
    # 执行计划配置
    execution_plans: List[ExecutionPlanConfig] = Field(default_factory=list, description="执行计划配置")
    
    # 系统参数
    context_cleanup_interval: int = Field(3600, description="上下文清理间隔（秒）")
    max_context_age: int = Field(86400, description="上下文最大存活时间（秒）")
    
    # 监控配置
    metrics_enabled: bool = Field(True, description="是否启用指标收集")
    health_check_interval: int = Field(30, description="健康检查间隔（秒）")