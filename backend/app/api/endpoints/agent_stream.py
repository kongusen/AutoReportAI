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

from ..deps import get_current_user
# Updated imports for new agent architecture
from ...services.infrastructure.agents.core.orchestration.coordinator import (
    AgentCoordinator
)
# from ...services.infrastructure.agents.core.tt_controller import TTEvent, TTEventType  # deprecated

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


async def format_tt_event_for_stream(event: TTEvent) -> StreamEvent:
    """将TTEvent格式化为前端流事件"""
    
    # 事件类型映射
    event_type_mapping = {
        TTEventType.UI_STATE_UPDATE: "ui_update",
        TTEventType.STAGE_START: "stage_start", 
        TTEventType.STAGE_COMPLETE: "stage_complete",
        TTEventType.TOOL_EXECUTION_START: "tool_start",
        TTEventType.TOOL_EXECUTION_COMPLETE: "tool_complete",
        TTEventType.LLM_INTERACTION_START: "llm_start",
        TTEventType.LLM_INTERACTION_COMPLETE: "llm_complete",
        TTEventType.PROGRESS_UPDATE: "progress",
        TTEventType.SQL_GENERATED: "sql_generated",
        TTEventType.DATA_PREVIEW: "data_preview",
        TTEventType.SYSTEM_ERROR: "error",
        TTEventType.TASK_COMPLETE: "task_complete"
    }
    
    # 阶段映射
    phase_mapping = {
        "intent_understanding": "意图理解",
        "context_analysis": "上下文分析", 
        "structure_planning": "结构规划",
        "implementation": "实现执行",
        "optimization": "优化审查",
        "synthesis": "综合整合"
    }
    
    event_type = event_type_mapping.get(event.type, "unknown")
    phase = None
    progress = None
    
    # 提取阶段和进度信息
    if hasattr(event, 'data') and event.data:
        stage_name = event.data.get('stage_name')
        if stage_name:
            phase = phase_mapping.get(stage_name, stage_name)
        
        # 提取进度信息
        if 'progress' in event.data:
            progress = event.data['progress']
        elif event_type == "stage_complete":
            progress = event.data.get('completion_progress', None)
    
    return StreamEvent(
        event_type=event_type,
        timestamp=datetime.utcnow(),
        data=event.data if hasattr(event, 'data') else {},
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
        
        # 创建协调器
        coordinator = UniversalAgentCoordinator(coordination_mode=coordination_mode)
        
        # 发送开始事件
        start_event = StreamEvent(
            event_type="task_start",
            data={
                "task_description": task_request.task_description,
                "mode": task_request.coordination_mode,
                "streaming_enabled": task_request.enable_streaming
            }
        )
        yield f"data: {start_event.json()}\n\n"
        
        # 如果启用流式输出，我们需要修改协调器以支持流式事件
        if task_request.enable_streaming:
            # 执行智能任务（这里我们需要修改以支持流式输出）
            result = await coordinator.execute_intelligent_task(
                task_description=task_request.task_description,
                context_data=task_request.context_data,
                user_id=user_id,
                coordination_mode=coordination_mode
            )
            
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
            result = await coordinator.execute_intelligent_task(
                task_description=task_request.task_description,
                context_data=task_request.context_data,
                user_id=user_id,
                coordination_mode=coordination_mode
            )
        
        # 发送最终结果
        final_event = StreamEvent(
            event_type="task_complete",
            progress=100,
            data={
                "success": result.success,
                "result": result.result,
                "task_id": result.task_id,
                "execution_time": result.execution_time,
                "phases_completed": [p.value for p in result.phases_completed],
                "metadata": result.metadata
            }
        )
        yield f"data: {final_event.json()}\n\n"
        
        # 如果有SQL生成，发送SQL预览事件
        if (task_request.sql_preview and 
            result.success and 
            result.metadata and 
            result.metadata.get('scenario') in ['sql_generation', 'data_analysis']):
            
            sql_event = StreamEvent(
                event_type="sql_generated",
                data={
                    "sql_query": "SELECT * FROM users WHERE DATE(created_at) = '2025-09-14'",  # 示例
                    "query_explanation": "根据上下文生成的用户数据查询",
                    "estimated_rows": 1500,
                    "complexity": "simple"
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


@router.post("/execute-stream")
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
    
    try:
        return StreamingResponse(
            agent_task_stream_generator(task_request, str(current_user.id)),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
        
    except Exception as e:
        logger.error(f"Agent stream endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=AgentTaskResponse)
async def execute_agent_task(
    task_request: AgentTaskRequest,
    current_user = Depends(get_current_user)
):
    """
    执行Agent任务（标准响应）
    
    提供传统的请求-响应模式，适用于不需要实时反馈的场景。
    """
    
    try:
        # 解析协调模式
        mode_mapping = {
            "intelligent": CoordinationMode.INTELLIGENT,
            "standard": CoordinationMode.STANDARD,
            "simple": CoordinationMode.SIMPLE
        }
        coordination_mode = mode_mapping.get(task_request.coordination_mode, CoordinationMode.INTELLIGENT)
        
        # 创建协调器并执行任务
        coordinator = UniversalAgentCoordinator(coordination_mode=coordination_mode)
        
        result = await coordinator.execute_intelligent_task(
            task_description=task_request.task_description,
            context_data=task_request.context_data,
            user_id=str(current_user.id),
            coordination_mode=coordination_mode
        )
        
        return AgentTaskResponse(
            task_id=result.task_id,
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time=result.execution_time,
            phases_completed=[p.value for p in result.phases_completed],
            metadata=result.metadata
        )
        
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
async def get_agent_task_status(
    task_id: str,
    current_user = Depends(get_current_user)
):
    """
    获取Agent任务状态
    
    查询特定任务的执行状态和结果。
    """
    
    try:
        # 这里需要实现任务状态查询
        # 暂时返回示例数据
        return {
            "task_id": task_id,
            "status": "completed",
            "progress": 100,
            "phases_completed": ["context_building", "strategy_generation", "tool_selection"],
            "current_phase": None,
            "result": {"message": "Task completed successfully"}
        }
        
    except Exception as e:
        logger.error(f"Get task status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/coordinator/status")
async def get_coordinator_status(
    current_user = Depends(get_current_user)
):
    """
    获取Agent协调器状态
    
    返回协调器的整体运行状态和性能指标。
    """
    
    try:
        coordinator = UniversalAgentCoordinator()
        status = coordinator.get_coordination_status()
        
        return {
            "coordinator_status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get coordinator status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))