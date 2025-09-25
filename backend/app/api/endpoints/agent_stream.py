"""
Agent流式处理API接口
====================

提供Agent循环过程的实时流式输出能力，支持前端实时展示Agent执行状态。
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Any

from ..deps import get_current_user
# Updated imports for new simplified agent architecture
from ...services.infrastructure.agents import (
    AgentFacade,
    AgentInput,
    PlaceholderSpec,
    SchemaInfo,
    TaskContext,
    AgentConstraints
)
from ...core.container import Container
from enum import Enum

class CoordinationMode(Enum):
    """协调模式 - 在新架构中简化处理"""
    INTELLIGENT = "intelligent"
    STANDARD = "standard"
    SIMPLE = "simple"

router = APIRouter()
logger = logging.getLogger(__name__)


class AgentTaskRequest(BaseModel):
    """Agent任务请求"""
    task_description: str = Field(..., description="任务描述")
    context_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文数据")
    coordination_mode: str = Field(default="intelligent", description="协调模式")
    enable_streaming: bool = Field(default=True, description="启用流式输出")
    sql_preview: bool = Field(default=True, description="启用SQL预览")
    template_id: Optional[str] = Field(None, description="模板ID")
    data_source_id: Optional[str] = Field(None, description="数据源ID")


class AgentTaskResponse(BaseModel):
    """Agent任务响应"""
    task_id: str = Field(..., description="任务ID")
    success: bool = Field(..., description="执行成功")
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: float = Field(..., description="执行时间(秒)")
    phases_completed: list = Field(default_factory=list, description="完成的阶段")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class StreamEvent(BaseModel):
    """流式事件"""
    event_type: str = Field(..., description="事件类型")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")
    data: Dict[str, Any] = Field(default_factory=dict, description="事件数据")
    phase: Optional[str] = Field(None, description="执行阶段")
    progress: Optional[float] = Field(None, description="进度百分比")


async def format_tt_event_for_stream(event: Any) -> StreamEvent:
    """将通用事件格式化为前端流事件（去除对旧TTEvent类型的依赖）"""

    # 阶段映射
    phase_mapping = {
        "intent_understanding": "意图理解",
        "context_analysis": "上下文分析", 
        "structure_planning": "结构规划",
        "implementation": "实现执行",
        "optimization": "优化审查",
        "synthesis": "综合整合"
    }
    
    # 兼容不同事件结构
    raw_type = getattr(event, "type", None)
    if raw_type is None and isinstance(event, dict):
        raw_type = event.get("type")
    event_type = str(getattr(raw_type, "value", raw_type or "unknown"))
    phase = None
    progress = None
    
    # 提取阶段和进度信息
    event_data = None
    if hasattr(event, 'data'):
        event_data = event.data
    elif isinstance(event, dict):
        event_data = event.get('data')

    if isinstance(event_data, dict):
        stage_name = event_data.get('stage_name')
        if stage_name:
            phase = phase_mapping.get(stage_name, stage_name)
        
        # 提取进度信息
        if 'progress' in event_data:
            progress = event_data['progress']
        elif event_type == "stage_complete":
            progress = event_data.get('completion_progress', None)
    
    return StreamEvent(
        event_type=event_type,
        timestamp=datetime.utcnow(),
        data=event_data or {},
        phase=phase,
        progress=progress
    )


async def agent_task_stream_generator(
    task_request: AgentTaskRequest,
    user_id: str
) -> AsyncGenerator[str, None]:
    """Agent任务流式生成器"""
    
    try:
        # 解析协调模式
        mode_mapping = {
            "intelligent": CoordinationMode.INTELLIGENT,
            "standard": CoordinationMode.STANDARD,
            "simple": CoordinationMode.SIMPLE
        }
        coordination_mode = mode_mapping.get(task_request.coordination_mode, CoordinationMode.INTELLIGENT)
        
        # 创建新的Agent系统组件
        container = Container()
        agent_facade = AgentFacade(container)

        # 发送开始事件
        start_event = StreamEvent(
            event_type="task_start",
            data={
                "task_description": task_request.task_description,
                "mode": task_request.coordination_mode,
                "streaming_enabled": task_request.enable_streaming,
                "agent_version": "2.0-simplified"
            }
        )
        yield f"data: {start_event.json()}\n\n"

        # 构建Agent输入
        agent_input = AgentInput(
            user_prompt=task_request.task_description,
            placeholder=PlaceholderSpec(
                id=f"stream_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description=task_request.task_description,
                type="stream_task"
            ),
            schema=SchemaInfo(
                tables=task_request.context_data.get("tables", []),
                columns=task_request.context_data.get("columns", {})
            ),
            context=TaskContext(
                task_time=int(datetime.now().timestamp()),
                timezone="Asia/Shanghai"
            ),
            constraints=AgentConstraints(
                sql_only=task_request.context_data.get("sql_only", False),
                output_kind=task_request.context_data.get("output_kind", "analysis")
            )
        )

        # 发送处理中事件
        processing_event = StreamEvent(
            event_type="task_processing",
            data={"phase": "agent_execution", "message": "正在执行Agent任务..."}
        )
        yield f"data: {processing_event.json()}\n\n"

        # 执行Agent任务
        if task_request.enable_streaming:
            result = await agent_facade.execute(agent_input)
            
            # 模拟阶段进度事件（在实际实现中，这应该来自TT控制循环）
            phases = [
                ("context_building", "智能上下文构建"),
                ("strategy_generation", "执行策略生成"), 
                ("tool_selection", "工具选择"),
                ("tt_execution", "TT控制循环执行"),
                ("result_synthesis", "结果综合")
            ]
            
            for i, (phase_key, phase_name) in enumerate(phases):
                progress = (i + 1) / len(phases) * 100
                
                # 发送阶段开始事件
                phase_start_event = StreamEvent(
                    event_type="stage_start",
                    phase=phase_name,
                    progress=progress - 20,  # 阶段开始时的进度
                    data={
                        "stage_name": phase_key,
                        "description": f"开始{phase_name}..."
                    }
                )
                yield f"data: {phase_start_event.json()}\n\n"
                
                # 模拟处理时间
                await asyncio.sleep(0.5)
                
                # 发送阶段完成事件
                phase_complete_event = StreamEvent(
                    event_type="stage_complete", 
                    phase=phase_name,
                    progress=progress,
                    data={
                        "stage_name": phase_key,
                        "description": f"{phase_name}完成",
                        "result": f"阶段{i+1}执行成功"
                    }
                )
                yield f"data: {phase_complete_event.json()}\n\n"
        
        else:
            # 非流式模式，直接执行
            result = await agent_facade.execute(agent_input)

        # 发送最终结果
        final_event = StreamEvent(
            event_type="task_complete",
            progress=100,
            data={
                "success": result.success,
                "result": result.result,
                "task_id": f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "execution_time": 0.0,  # TODO: 添加执行时间统计
                "phases_completed": ["plan", "tool", "observe", "finalize"],
                "metadata": result.metadata or {}
            }
        )
        yield f"data: {final_event.json()}\n\n"
        
        # 如果有SQL生成，发送SQL预览事件
        if (task_request.sql_preview and result.success and
            "SELECT" in str(result.result).upper()):

            sql_event = StreamEvent(
                event_type="sql_generated",
                data={
                    "sql_query": result.result,
                    "query_explanation": "基于新Agent系统生成的SQL查询",
                    "estimated_rows": 1000,  # 模拟估算
                    "complexity": "standard",
                    "agent_version": "2.0-simplified"
                }
            )
            yield f"data: {sql_event.json()}\n\n"
        
    except Exception as e:
        logger.error(f"Agent task stream failed: {e}")
        error_event = StreamEvent(
            event_type="error",
            data={
                "error": str(e),
                "error_type": "execution_error"
            }
        )
        yield f"data: {error_event.json()}\n\n"


@router.post("/execute-stream", deprecated=True)
async def execute_agent_task_stream(
    task_request: AgentTaskRequest,
    current_user = Depends(get_current_user)
):
    """
    执行Agent任务（流式输出）
    
    提供实时的Agent执行过程反馈，包括：
    - 阶段进度
    - 工具执行状态  
    - LLM交互过程
    - SQL生成和预览
    - 错误处理
    """
    
    # 已废弃：请改用 /api/agent/run-async + /api/agent/run-async/{task_id}/stream
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=410,
        content={
            "error": True,
            "message": "接口已废弃，请改用异步运行与SSE流式监控",
            "code": "API_DEPRECATED",
            "replacement": {
                "start": "POST /api/agent/run-async",
                "status": "GET /api/agent/run-async/{task_id}/status",
                "stream": "GET /api/agent/run-async/{task_id}/stream"
            }
        },
        headers={"X-Deprecated": "true"}
    )


@router.post("/execute", response_model=AgentTaskResponse, deprecated=True)
async def execute_agent_task(
    task_request: AgentTaskRequest,
    current_user = Depends(get_current_user)
):
    """
    执行Agent任务（标准响应）
    
    提供传统的请求-响应模式，适用于不需要实时反馈的场景。
    """
    
    # 已废弃：请改用 /api/agent/run
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=410,
        content={
            "error": True,
            "message": "接口已废弃，请改用同步运行接口 /api/agent/run",
            "code": "API_DEPRECATED",
            "replacement": {
                "run": "POST /api/agent/run"
            }
        },
        headers={"X-Deprecated": "true"}
    )


@router.get("/status/{task_id}", deprecated=True)
async def get_agent_task_status(
    task_id: str,
    current_user = Depends(get_current_user)
):
    """
    获取Agent任务状态
    
    查询特定任务的执行状态和结果。
    """
    
    # 已废弃：请改用 /api/agent/run-async/{task_id}/status
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=410,
        content={
            "error": True,
            "message": "接口已废弃，请改用任务状态查询接口",
            "code": "API_DEPRECATED",
            "replacement": {
                "status": "GET /api/agent/run-async/{task_id}/status"
            }
        },
        headers={"X-Deprecated": "true"}
    )


@router.get("/coordinator/status", deprecated=True)
async def get_coordinator_status(
    current_user = Depends(get_current_user)
):
    """
    获取Agent协调器状态
    
    返回协调器的整体运行状态和性能指标。
    """
    
    # 已废弃：请改用 /api/agent/system/async-status
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=410,
        content={
            "error": True,
            "message": "接口已废弃，请改用异步系统状态接口",
            "code": "API_DEPRECATED",
            "replacement": {
                "system_status": "GET /api/agent/system/async-status"
            }
        },
        headers={"X-Deprecated": "true"}
    )
