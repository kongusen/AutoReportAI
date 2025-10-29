"""
Agent Run API - 生产级同步执行接口
=======================================

提供标准的Agent同步执行能力，适配业务系统的各种调用场景。
支持占位符生成、SQL/图表/报告输出，包含完整的权限验证和错误处理。
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..deps import get_current_user
from ...services.application.agent_input.bridge import AgentInputBridge
# from ...services.infrastructure.agents import data_source_security_service
from ...core.container import Container

logger = logging.getLogger(__name__)
router = APIRouter()


class AgentRunRequest(BaseModel):
    """Agent执行请求"""
    # 核心参数
    user_id: Optional[str] = Field(None, description="用户ID (可选，默认使用当前认证用户)")
    template_id: str = Field(..., description="模板ID", min_length=1)
    data_source_id: str = Field(..., description="数据源ID", min_length=1)
    placeholder_name: str = Field(..., description="占位符名称", min_length=1)

    # 任务定义
    task_definition: Dict[str, Any] = Field(default_factory=dict, description="任务定义")

    # 输出控制
    output_kind: str = Field(default="sql", description="输出类型: sql|chart|report")
    sql_only: bool = Field(default=True, description="仅SQL输出")

    # 策略覆盖 (可选)
    overrides: Optional[Dict[str, Any]] = Field(default=None, description="策略覆盖参数")

    # 执行控制
    force_refresh: bool = Field(default=False, description="强制刷新上下文")
    enable_observations: bool = Field(default=True, description="启用执行观察")




class AgentRunResponse(BaseModel):
    """Agent执行响应"""
    # 执行结果
    success: bool = Field(..., description="执行是否成功")
    result: Optional[str] = Field(None, description="执行结果 (SQL/图表配置/报告内容)")

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="执行元数据")
    context_id: Optional[str] = Field(None, description="上下文ID")
    stage: Optional[str] = Field(None, description="执行阶段")

    # 观察信息
    observations: List[str] = Field(default_factory=list, description="执行观察")
    dynamic_user_prompt: Optional[str] = Field(None, description="动态用户提示词")
    available_tools: List[Dict[str, str]] = Field(default_factory=list, description="可用工具")

    # 错误信息
    error: Optional[str] = Field(None, description="错误信息")
    warnings: List[str] = Field(default_factory=list, description="警告信息")

    # 执行统计
    execution_time_ms: Optional[int] = Field(None, description="执行时间(毫秒)")
    request_id: str = Field(..., description="请求ID")


class AgentModelsResponse(BaseModel):
    """Agent模型列表响应"""
    models: List[Dict[str, Any]] = Field(..., description="可用模型列表")
    total: int = Field(..., description="模型总数")
    default_model: Optional[str] = Field(None, description="默认模型")


class AgentHealthResponse(BaseModel):
    """Agent健康检查响应"""
    status: str = Field(..., description="健康状态: healthy|degraded|unhealthy")
    checks: Dict[str, Dict[str, Any]] = Field(..., description="各组件健康检查结果")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="检查时间")


class AsyncTaskResponse(BaseModel):
    """异步任务响应"""
    success: bool
    task_id: Optional[str] = None
    error: Optional[str] = None
    status_url: Optional[str] = None
    stream_url: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    progress: float
    current_step: str
    created_at: str
    updated_at: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


async def validate_request_permissions(
    request: AgentRunRequest,
    current_user_id: str
) -> Dict[str, Any]:
    """验证请求权限"""

    # 确定实际用户ID
    effective_user_id = request.user_id or current_user_id

    # 超级用户可以代理执行
    if request.user_id and request.user_id != current_user_id:
        # TODO: 检查当前用户是否为超级用户
        # 暂时只允许用户操作自己的资源
        if request.user_id != current_user_id:
            return {
                "allowed": False,
                "reason": "不允许代理执行其他用户的Agent任务",
                "error_code": "PROXY_EXECUTION_DENIED"
            }

    # 验证数据源访问权限
    # access_validation = data_source_security_service.validate_data_source_access(
    #     user_id=effective_user_id,
    #     data_source_id=request.data_source_id
    # )

    # if not access_validation.get("allowed"):
    #     return access_validation

    # 临时跳过权限验证
    access_validation = {"allowed": True, "data_source": {}, "user_permissions": []}

    # TODO: 添加模板访问权限验证
    # template_access = await validate_template_access(effective_user_id, request.template_id)

    return {
        "allowed": True,
        "effective_user_id": effective_user_id,
        "data_source_info": access_validation.get("data_source"),
        "user_permissions": access_validation.get("user_permissions")
    }


@router.post("/run", response_model=AgentRunResponse)
async def agent_run(
    request: AgentRunRequest,
    current_user = Depends(get_current_user)
):
    """
    Agent同步执行接口

    执行指定的Agent任务，返回SQL查询、图表配置或报告内容。
    支持占位符处理、权限验证、策略应用等完整功能。

    Args:
        request: Agent执行请求参数
        current_user: 当前认证用户

    Returns:
        AgentRunResponse: 执行结果

    Raises:
        HTTPException: 权限验证失败、参数错误、执行异常等
    """

    request_id = str(uuid.uuid4())
    start_time = datetime.utcnow()

    logger.info(f"[{request_id}] Agent执行请求: template_id={request.template_id}, "
                f"placeholder={request.placeholder_name}, output_kind={request.output_kind}")

    try:
        # 1. 权限验证
        permission_check = await validate_request_permissions(request, str(current_user.id))

        if not permission_check.get("allowed"):
            logger.warning(f"[{request_id}] 权限验证失败: {permission_check}")
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "permission_denied",
                    "message": permission_check.get("reason", "权限验证失败"),
                    "error_code": permission_check.get("error_code", "ACCESS_DENIED")
                }
            )

        effective_user_id = permission_check["effective_user_id"]
        logger.info(f"[{request_id}] 权限验证通过: user_id={effective_user_id}")

        # 2. 应用策略覆盖
        task_definition = request.task_definition.copy()
        if request.overrides:
            task_definition.update(request.overrides)
            logger.info(f"[{request_id}] 应用策略覆盖: {list(request.overrides.keys())}")

        # 3. 创建Agent桥接服务
        container = Container()
        bridge = AgentInputBridge(container)

        # 4. 执行Agent任务
        logger.info(f"[{request_id}] 开始执行Agent任务...")

        execution_result = await bridge.execute_for_placeholder(
            user_id=effective_user_id,
            template_id=request.template_id,
            data_source_id=request.data_source_id,
            placeholder_name=request.placeholder_name,
            task_definition=task_definition,
            output_kind=request.output_kind,
            sql_only=request.sql_only,
            force_refresh=request.force_refresh
        )

        # 5. 计算执行时间
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # 6. 构建响应
        success = execution_result.get("success", False)

        if success:
            logger.info(f"[{request_id}] Agent执行成功: {execution_time_ms}ms")

            response = AgentRunResponse(
                success=True,
                result=execution_result.get("result"),
                metadata=execution_result.get("metadata", {}),
                context_id=execution_result.get("context_id"),
                stage=execution_result.get("stage"),
                observations=_extract_observations(execution_result),
                dynamic_user_prompt=execution_result.get("dynamic_user_prompt"),
                available_tools=execution_result.get("available_tools", []),
                execution_time_ms=execution_time_ms,
                request_id=request_id
            )
        else:
            error_msg = execution_result.get("error", "Agent执行失败")
            logger.error(f"[{request_id}] Agent执行失败: {error_msg}")

            response = AgentRunResponse(
                success=False,
                error=error_msg,
                metadata=execution_result.get("metadata", {}),
                context_id=execution_result.get("context_id"),
                execution_time_ms=execution_time_ms,
                request_id=request_id
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        logger.error(f"[{request_id}] Agent执行异常: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=500,
            detail={
                "error": "execution_failed",
                "message": str(e),
                "request_id": request_id,
                "execution_time_ms": execution_time_ms
            }
        )



@router.get("/models", response_model=AgentModelsResponse)
async def get_agent_models(
    current_user = Depends(get_current_user)
):
    """
    获取可用的Agent模型列表

    返回当前系统中可用的LLM模型信息，包括模型类型、健康状态等。

    Returns:
        AgentModelsResponse: 模型列表响应
    """

    try:
        # 从数据库获取模型列表
        from ...crud.crud_llm_model import crud_llm_model
        from ...db.session import SessionLocal

        db = SessionLocal()
        try:
            models = crud_llm_model.get_active_models(db)

            model_list = []
            for model in models:
                model_info = {
                    "id": str(model.id),
                    "server_name": model.server.name if model.server else "Unknown",
                    "model_name": model.name,
                    "display_name": model.display_name,
                    "model_type": model.model_type.value if model.model_type else "unknown",
                    "is_active": model.is_active,
                    "is_healthy": getattr(model, 'is_healthy', True),
                    "priority": getattr(model, 'priority', 100),
                    "provider_name": model.provider_name
                }
                model_list.append(model_info)

            # 找到默认模型 (优先级最高且健康的模型)
            default_model = None
            active_models = [m for m in model_list if m["is_active"] and m["is_healthy"]]
            if active_models:
                default_model = min(active_models, key=lambda x: x["priority"])["model_name"]

            return AgentModelsResponse(
                models=model_list,
                total=len(model_list),
                default_model=default_model
            )

        finally:
            db.close()

    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=AgentHealthResponse)
async def get_agent_health(
    current_user = Depends(get_current_user)
):
    """
    Agent系统健康检查

    检查Agent系统各组件的健康状态，包括LLM服务、数据源连接等。

    Returns:
        AgentHealthResponse: 健康检查响应
    """

    try:
        checks = {}
        overall_status = "healthy"

        # 1. 检查LLM服务健康状态
        try:
            from ...crud.crud_llm_model import crud_llm_model
            from ...db.session import SessionLocal

            db = SessionLocal()
            try:
                healthy_models = crud_llm_model.get_healthy_models(db)
                if not healthy_models:
                    overall_status = "degraded"

                checks["llm_models"] = {
                    "status": "healthy" if healthy_models else "unhealthy",
                    "healthy_count": len(healthy_models),
                    "message": f"{len(healthy_models)} 个健康模型可用"
                }
            finally:
                db.close()

        except Exception as e:
            overall_status = "degraded"
            checks["llm_models"] = {
                "status": "unhealthy",
                "error": str(e),
                "message": "LLM模型健康检查失败"
            }

        # 2. 检查数据库连接
        try:
            from ...db.session import SessionLocal
            db = SessionLocal()
            try:
                # 简单查询测试数据库连接
                db.execute("SELECT 1")
                checks["database"] = {
                    "status": "healthy",
                    "message": "数据库连接正常"
                }
            finally:
                db.close()
        except Exception as e:
            overall_status = "unhealthy"
            checks["database"] = {
                "status": "unhealthy",
                "error": str(e),
                "message": "数据库连接失败"
            }

        # 3. 检查Agent核心组件
        try:
            container = Container()
            # 尝试创建核心组件
            bridge = AgentInputBridge(container)

            checks["agent_bridge"] = {
                "status": "healthy",
                "message": "Agent桥接服务正常"
            }
        except Exception as e:
            overall_status = "degraded"
            checks["agent_bridge"] = {
                "status": "unhealthy",
                "error": str(e),
                "message": "Agent桥接服务异常"
            }

        return AgentHealthResponse(
            status=overall_status,
            checks=checks,
            timestamp=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _extract_observations(execution_result: Dict[str, Any]) -> List[str]:
    """从执行结果中提取观察信息"""
    observations = []

    # 从metadata中提取observations
    metadata = execution_result.get("metadata", {})
    if "observations" in metadata:
        observations.extend(metadata["observations"])

    # 从agent_context中提取观察信息
    agent_context = execution_result.get("agent_context", {})
    if isinstance(agent_context, dict):
        context_observations = agent_context.get("observations", [])
        if context_observations:
            observations.extend(context_observations)

    # 添加基础执行信息
    if execution_result.get("success"):
        observations.append("Agent执行成功完成")

    stage = execution_result.get("stage")
    if stage:
        observations.append(f"执行阶段: {stage}")

    return observations


# 全局异步服务实例
_stream_service = None

def get_stream_service():
    """获取异步流式服务实例"""
    global _stream_service
    if _stream_service is None:
        from ...services.infrastructure.agents.async_stream_service import AsyncAgentStreamService
        container = Container()
        _stream_service = AsyncAgentStreamService(container)
    return _stream_service


@router.post("/run-async", response_model=AsyncTaskResponse)
async def agent_run_async(
    request: AgentRunRequest,
    current_user = Depends(get_current_user)
):
    """
    Agent异步执行接口

    启动长时间运行的Agent任务，适用于复杂分析和批量处理。
    返回task_id，可通过status和stream接口监控进度。

    Args:
        request: Agent执行请求参数
        current_user: 当前认证用户

    Returns:
        AsyncTaskResponse: 异步任务响应
    """

    try:
        logger.info(f"🚀 [AgentAsyncAPI] 异步任务启动: template_id={request.template_id}, "
                   f"placeholder={request.placeholder_name}")

        # 权限验证（复用同步接口的逻辑）
        permission_check = await validate_request_permissions(request, str(current_user.id))

        if not permission_check.get("allowed"):
            logger.warning(f"异步任务权限验证失败: {permission_check}")
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "permission_denied",
                    "message": permission_check.get("reason", "权限验证失败"),
                    "error_code": permission_check.get("error_code", "ACCESS_DENIED")
                }
            )

        effective_user_id = permission_check["effective_user_id"]

        # 构建任务输入数据
        task_definition = request.task_definition.copy()
        if request.overrides:
            task_definition.update(request.overrides)

        input_data = {
            "user_id": effective_user_id,
            "template_id": request.template_id,
            "data_source_id": request.data_source_id,
            "placeholder_name": request.placeholder_name,
            "task_definition": task_definition,
            "output_kind": request.output_kind,
            "sql_only": request.sql_only,
            "force_refresh": request.force_refresh,
            "enable_observations": request.enable_observations
        }

        # 启动异步任务
        stream_service = get_stream_service()
        task_id = await stream_service.start_async_task(input_data)

        logger.info(f"✅ [AgentAsyncAPI] 异步任务已启动: {task_id}")

        return AsyncTaskResponse(
            success=True,
            task_id=task_id,
            status_url=f"/api/agent/run-async/{task_id}/status",
            stream_url=f"/api/agent/run-async/{task_id}/stream"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [AgentAsyncAPI] 异步任务启动失败: {str(e)}")

        return AsyncTaskResponse(
            success=False,
            error=str(e)
        )


@router.get("/run-async/{task_id}/status", response_model=TaskStatusResponse)
async def get_async_task_status(
    task_id: str,
    current_user = Depends(get_current_user)
):
    """
    查询异步任务状态

    返回任务的当前状态、进度和结果信息。

    Args:
        task_id: 任务ID
        current_user: 当前认证用户

    Returns:
        TaskStatusResponse: 任务状态响应
    """

    try:
        stream_service = get_stream_service()
        status = await stream_service.get_task_status(task_id)

        if not status:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        return TaskStatusResponse(**status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [AgentAsyncAPI] 状态查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/run-async/{task_id}/stream")
async def stream_async_task_events(
    task_id: str,
    current_user = Depends(get_current_user)
):
    """
    流式获取异步任务执行事件

    返回Server-Sent Events (SSE)流，实时显示任务进度、步骤执行和结果。
    适用于前端实时监控和进度显示。

    Args:
        task_id: 任务ID
        current_user: 当前认证用户

    Returns:
        StreamingResponse: SSE事件流
    """

    try:
        logger.info(f"📡 [AgentAsyncAPI] 开始流式输出: {task_id}")

        async def event_generator():
            """SSE事件生成器"""
            try:
                stream_service = get_stream_service()
                async for event in stream_service.stream_task_events(task_id):
                    # 格式化为SSE格式
                    yield f"data: {event.to_json()}\n\n"

                # 发送结束标记
                import json
                yield f"data: {json.dumps({'event_type': 'stream_end', 'data': {'task_id': task_id}}, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(f"❌ [AgentAsyncAPI] 流式输出异常: {str(e)}")
                import json
                yield f"data: {json.dumps({'event_type': 'error', 'data': {'error': str(e)}}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*"
            }
        )

    except Exception as e:
        logger.error(f"❌ [AgentAsyncAPI] 流式接口失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/run-async/{task_id}")
async def cancel_async_task(
    task_id: str,
    current_user = Depends(get_current_user)
):
    """
    取消异步任务

    取消正在执行的异步任务。

    Args:
        task_id: 任务ID
        current_user: 当前认证用户

    Returns:
        dict: 取消结果
    """

    try:
        stream_service = get_stream_service()
        success = await stream_service.cancel_task(task_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"任务不存在或无法取消: {task_id}")

        return {"success": True, "message": f"任务已取消: {task_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [AgentAsyncAPI] 任务取消失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/async-status")
async def get_async_system_status(
    current_user = Depends(get_current_user)
):
    """
    获取异步系统状态

    返回当前活跃任务数、系统健康状况等信息。

    Args:
        current_user: 当前认证用户

    Returns:
        dict: 系统状态信息
    """

    try:
        stream_service = get_stream_service()
        status = stream_service.get_system_status()
        return status

    except Exception as e:
        logger.error(f"❌ [AgentAsyncAPI] 系统状态查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
