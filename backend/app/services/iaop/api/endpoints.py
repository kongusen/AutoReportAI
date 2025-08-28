"""
IAOP API端点定义

提供FastAPI路由和端点实现
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from typing import List, Optional

from .schemas import *
from .services import IAOPService, get_iaop_service

logger = logging.getLogger(__name__)


def create_iaop_router() -> APIRouter:
    """创建IAOP API路由器"""
    router = APIRouter(prefix="/api/v1/iaop", tags=["IAOP"])
    
    @router.post("/reports/generate", response_model=ReportResponse)
    async def generate_report(
        request: ReportGenerationRequest,
        service: IAOPService = Depends(get_iaop_service)
    ):
        """
        生成单个报告
        
        根据占位符文本生成完整的数据报告，包括：
        - 数据查询和分析
        - 图表配置生成
        - 自然语言解释
        """
        try:
            result = await service.generate_report(request)
            return result
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/placeholders/process", response_model=BatchProcessingResponse)
    async def process_placeholders(
        request: PlaceholderRequest,
        service: IAOPService = Depends(get_iaop_service)
    ):
        """
        处理模板中的占位符
        
        解析模板内容中的所有占位符，并生成对应的报告
        """
        try:
            result = await service.process_placeholders(request)
            return result
        except Exception as e:
            logger.error(f"处理占位符失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/agents/{agent_name}/execute")
    async def execute_agent(
        agent_name: str,
        request: AgentExecutionRequest,
        service: IAOPService = Depends(get_iaop_service)
    ):
        """
        执行指定的Agent
        
        直接调用指定Agent进行处理
        """
        try:
            request.agent_name = agent_name  # 确保agent_name正确
            result = await service.execute_agent(request)
            return result
        except Exception as e:
            logger.error(f"执行Agent失败: {agent_name}, 错误: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/agents", response_model=List[AgentStatusResponse])
    async def list_agents(
        service: IAOPService = Depends(get_iaop_service)
    ):
        """
        列出所有已注册的Agent
        """
        try:
            agents = await service.list_agents()
            return agents
        except Exception as e:
            logger.error(f"获取Agent列表失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/agents/{agent_name}", response_model=AgentStatusResponse)
    async def get_agent_status(
        agent_name: str,
        service: IAOPService = Depends(get_iaop_service)
    ):
        """
        获取指定Agent的状态信息
        """
        try:
            status = await service.get_agent_status(agent_name)
            if not status:
                raise HTTPException(status_code=404, detail=f"Agent不存在: {agent_name}")
            return status
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取Agent状态失败: {agent_name}, 错误: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/system/status", response_model=SystemStatusResponse)
    async def get_system_status(
        service: IAOPService = Depends(get_iaop_service)
    ):
        """
        获取系统整体状态
        """
        try:
            status = await service.get_system_status()
            return status
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/system/health")
    async def health_check():
        """
        健康检查端点
        """
        return {"status": "healthy", "timestamp": datetime.utcnow()}
    
    @router.post("/system/agents/register")
    async def register_agents(
        service: IAOPService = Depends(get_iaop_service)
    ):
        """
        重新注册所有Agent
        """
        try:
            from ..agents.specialized import register_all_specialized_agents
            registry = register_all_specialized_agents()
            status = registry.get_registry_status()
            return {
                "success": True,
                "message": "Agent注册完成",
                "registry_status": status
            }
        except Exception as e:
            logger.error(f"重新注册Agent失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 调试和开发端点
    @router.get("/debug/context/{session_id}")
    async def get_context_debug(
        session_id: str,
        service: IAOPService = Depends(get_iaop_service)
    ):
        """
        获取调试用的上下文信息（仅在调试模式下可用）
        """
        try:
            context = service.context_manager.get_context(session_id)
            if not context:
                raise HTTPException(status_code=404, detail=f"上下文不存在: {session_id}")
            
            return {
                "session_id": context.session_id,
                "user_id": context.user_id,
                "task_id": context.task_id,
                "created_at": context.created_at,
                "context_entries_count": len(context.context_entries),
                "execution_history_count": len(context.execution_history),
                "error_count": len(context.error_stack),
                "capabilities": context.capabilities
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取调试上下文失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.delete("/debug/contexts")
    async def cleanup_contexts(
        max_age_hours: int = Query(24, description="清理超过指定小时数的上下文"),
        service: IAOPService = Depends(get_iaop_service)
    ):
        """
        清理过期上下文（调试用）
        """
        try:
            initial_count = len(service.context_manager.contexts)
            service.context_manager.cleanup_expired_contexts(max_age_hours)
            final_count = len(service.context_manager.contexts)
            
            return {
                "success": True,
                "cleaned_count": initial_count - final_count,
                "remaining_count": final_count
            }
        except Exception as e:
            logger.error(f"清理上下文失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return router


# 错误处理器
class IAOPAPIRouter:
    """IAOP API路由器类"""
    
    def __init__(self):
        self.router = create_iaop_router()
        self._setup_error_handlers()
    
    def _setup_error_handlers(self):
        """设置错误处理器"""
        
        @self.router.exception_handler(ValueError)
        async def value_error_handler(request, exc):
            logger.error(f"参数错误: {exc}")
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error=str(exc),
                    error_type="ValueError",
                    error_code="INVALID_PARAMETER"
                ).dict()
            )
        
        @self.router.exception_handler(TimeoutError)
        async def timeout_error_handler(request, exc):
            logger.error(f"超时错误: {exc}")
            return JSONResponse(
                status_code=408,
                content=ErrorResponse(
                    error="请求超时",
                    error_type="TimeoutError", 
                    error_code="REQUEST_TIMEOUT"
                ).dict()
            )
        
        @self.router.exception_handler(Exception)
        async def general_error_handler(request, exc):
            logger.error(f"未处理的错误: {exc}")
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error="内部服务器错误",
                    error_type=type(exc).__name__,
                    error_code="INTERNAL_ERROR",
                    details={"original_error": str(exc)}
                ).dict()
            )
    
    def get_router(self) -> APIRouter:
        """获取路由器实例"""
        return self.router


# 便捷函数
def get_iaop_router() -> APIRouter:
    """获取IAOP API路由器"""
    return IAOPAPIRouter().get_router()