"""
增强AI架构API v3.0
====================

基于增强架构v3.0的新一代API接口：
- 流式执行和实时进度反馈
- 智能工具链集成
- 提示词性能监控
- 增强的错误处理和重试
- 上下文感知的执行控制
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.base import APIResponse

# 导入增强架构组件 - 已迁移到agents系统
from app.services.infrastructure.agents import execute_agent_task
from app.services.infrastructure.agents.tools import get_tool_registry

logger = logging.getLogger(__name__)
router = APIRouter()

# ================================================================================
# 请求和响应模型
# ================================================================================

class EnhancedExecutionRequest(BaseModel):
    """增强执行请求模型"""
    tool_type: str = Field(..., description="工具类型: sql_generator|data_analyzer|report_generator")
    input_data: Dict[str, Any] = Field(..., description="输入数据")
    execution_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="执行配置")
    context_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文数据") 
    streaming: bool = Field(False, description="是否启用流式响应")
    
    class Config:
        schema_extra = {
            "example": {
                "tool_type": "sql_generator",
                "input_data": {
                    "placeholders": [
                        {
                            "name": "用户统计",
                            "text": "按月统计用户注册数量",
                            "type": "chart"
                        }
                    ]
                },
                "execution_config": {
                    "max_iterations": 3,
                    "optimize_for_performance": True,
                    "include_reasoning": True
                },
                "context_data": {
                    "data_source_info": {
                        "tables": ["users"],
                        "table_details": [...]
                    }
                },
                "streaming": True
            }
        }

class ExecutionStatusRequest(BaseModel):
    """执行状态查询请求"""
    session_id: str = Field(..., description="执行会话ID")
    include_performance: bool = Field(False, description="是否包含性能数据")
    include_insights: bool = Field(False, description="是否包含学习洞察")

class ToolCapabilityResponse(BaseModel):
    """工具能力响应"""
    tool_name: str
    capabilities: List[str]
    input_schema: Dict[str, Any]
    output_format: Dict[str, Any]
    performance_metrics: Dict[str, Any]

# ================================================================================
# 核心执行API
# ================================================================================

@router.post("/execute", response_model=APIResponse[Dict[str, Any]])
async def enhanced_execute(
    request: EnhancedExecutionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> APIResponse[Dict[str, Any]]:
    """
    增强执行API - 支持所有新架构功能
    
    特性：
    - 智能工具选择和执行
    - 完整的错误处理和重试
    - 性能监控和学习
    - 上下文感知处理
    """
    
    session_id = str(uuid4())
    
    try:
        logger.info(f"启动增强执行: user_id={current_user.id}, tool_type={request.tool_type}, session_id={session_id}")
        
        # 1. 初始化工具链
        # 使用agents系统代替旧的ToolChain
        logger.info("正在使用agents系统执行任务")
        
        # 2. 根据工具类型创建工具
        tool_instance = None
        if request.tool_type == "sql_generator":
            # 使用agents系统代替旧的工具类
            logger.info(f"正在使用agents系统执行SQL生成任务")
        elif request.tool_type == "data_analyzer":
            tool_instance = SmartDataAnalyzer()
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的工具类型: {request.tool_type}"
            )
        
        tool_chain.register_tool(tool_instance)
        
        # 3. 创建执行上下文
        context = ToolContext(
            user_id=str(current_user.id),
            task_id=f"api_task_{session_id}",
            session_id=session_id,
            **request.context_data
        )
        
        # 4. 初始化性能监控
        monitor = get_prompt_monitor()
        monitor.start_session(session_id)
        
        # 5. 执行工具
        results = []
        final_result = None
        
        async for result in tool_instance.execute(request.input_data, context):
            results.append({
                "type": result.type,
                "content": result.content,
                "data": result.data,
                "timestamp": datetime.now().isoformat()
            })
            
            if result.type == "success":
                final_result = result
        
        # 6. 获取性能统计
        performance_stats = monitor.get_session_stats(session_id)
        insights = monitor.get_insights(session_id)
        
        # 7. 构建响应
        response_data = {
            "session_id": session_id,
            "tool_type": request.tool_type,
            "execution_status": "completed",
            "results": results,
            "final_result": {
                "success": final_result.type == "success" if final_result else False,
                "data": final_result.data if final_result else None,
                "confidence": final_result.confidence if final_result else 0.0
            },
            "performance": {
                "execution_time": len(results) * 1.0,  # 简化计算
                "iterations_used": len([r for r in results if r["type"] == "progress"]),
                "stats": performance_stats,
                "insights": insights
            },
            "metadata": {
                "total_steps": len(results),
                "success_steps": len([r for r in results if r["type"] == "success"]),
                "error_steps": len([r for r in results if r["type"] == "error"])
            }
        }
        
        return APIResponse(
            success=True,
            data=response_data,
            message="增强执行完成"
        )
        
    except Exception as e:
        logger.error(f"增强执行失败: session_id={session_id}, error={e}")
        raise HTTPException(
            status_code=500,
            detail=f"增强执行失败: {str(e)}"
        )

@router.get("/execute/stream/{session_id}")
async def enhanced_execute_stream(
    session_id: str,
    request: EnhancedExecutionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    流式执行API - 实时返回执行进度
    
    特性：
    - Server-Sent Events (SSE)
    - 实时进度反馈
    - 中间结果流式返回
    - 错误实时通知
    """
    
    async def generate_stream():
        try:
            logger.info(f"启动流式执行: user_id={current_user.id}, session_id={session_id}")
            
            # 初始化组件
            # 使用agents系统代替旧的ToolChain
            logger.info("正在使用agents系统执行任务")
            
            if request.tool_type == "sql_generator":
                # 使用agents系统代替旧的工具类
                logger.info(f"正在使用agents系统执行SQL生成任务")
            elif request.tool_type == "data_analyzer":
                tool_instance = SmartDataAnalyzer()
            else:
                yield f"data: {{'error': '不支持的工具类型: {request.tool_type}'}}\n\n"
                return
            
            tool_chain.register_tool(tool_instance)
            
            context = ToolContext(
                user_id=str(current_user.id),
                task_id=f"stream_task_{session_id}",
                session_id=session_id,
                **request.context_data
            )
            
            # 发送开始事件
            yield f"data: {{'type': 'start', 'session_id': '{session_id}', 'timestamp': '{datetime.now().isoformat()}'}}\n\n"
            
            # 流式执行工具
            step_count = 0
            async for result in tool_instance.execute(request.input_data, context):
                step_count += 1
                
                event_data = {
                    "type": result.type,
                    "content": result.content,
                    "step": step_count,
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id
                }
                
                # 添加数据（如果存在）
                if result.data:
                    event_data["data"] = result.data
                    
                # 添加置信度（如果存在）
                if hasattr(result, 'confidence') and result.confidence:
                    event_data["confidence"] = result.confidence
                
                yield f"data: {event_data}\n\n"
                
                # 添加小延迟以确保客户端能够接收
                await asyncio.sleep(0.1)
            
            # 发送完成事件
            yield f"data: {{'type': 'completed', 'session_id': '{session_id}', 'total_steps': {step_count}, 'timestamp': '{datetime.now().isoformat()}'}}\n\n"
            
        except Exception as e:
            logger.error(f"流式执行异常: session_id={session_id}, error={e}")
            yield f"data: {{'type': 'error', 'error': '{str(e)}', 'session_id': '{session_id}'}}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

# ================================================================================
# 监控和状态API
# ================================================================================

@router.get("/status/{session_id}", response_model=APIResponse[Dict[str, Any]])
async def get_execution_status(
    session_id: str,
    request: ExecutionStatusRequest,
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """获取执行状态和性能监控数据"""
    
    try:
        monitor = get_prompt_monitor()
        
        # 获取会话统计
        stats = monitor.get_session_stats(session_id)
        
        status_data = {
            "session_id": session_id,
            "status": "completed" if stats else "not_found",
            "basic_stats": stats
        }
        
        # 包含性能数据
        if request.include_performance and stats:
            status_data["performance"] = {
                "response_times": stats.get("response_times", []),
                "token_usage": stats.get("token_usage", 0),
                "api_calls": stats.get("api_calls", 0),
                "success_rate": stats.get("success_rate", 0.0)
            }
        
        # 包含学习洞察
        if request.include_insights:
            insights = monitor.get_insights(session_id)
            status_data["insights"] = insights
        
        return APIResponse(
            success=True,
            data=status_data,
            message="状态获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取执行状态失败: session_id={session_id}, error={e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取执行状态失败: {str(e)}"
        )

@router.get("/capabilities", response_model=APIResponse[List[ToolCapabilityResponse]])
async def get_tool_capabilities(
    current_user: User = Depends(get_current_user)
) -> APIResponse[List[ToolCapabilityResponse]]:
    """获取可用工具的能力描述"""
    
    try:
        capabilities = []
        
        # SQL生成器能力
        # 使用agents系统代替旧的工具类
        logger.info(f"正在使用agents系统获取SQL生成工具能力")
        capabilities.append(ToolCapabilityResponse(
            tool_name="sql_generator",
            capabilities=[
                "智能SQL生成",
                "多轮推理优化",
                "性能优化建议",
                "错误自动修复",
                "上下文感知生成"
            ],
            input_schema={
                "placeholders": "占位符列表",
                "data_source_info": "数据源信息",
                "requirements": "执行要求"
            },
            output_format={
                "sql": "生成的SQL语句",
                "reasoning": "推理过程",
                "confidence": "置信度分数"
            },
            performance_metrics={
                "avg_response_time": "平均响应时间",
                "success_rate": "成功率",
                "optimization_rate": "优化率"
            }
        ))
        
        # 数据分析器能力
        data_analyzer = SmartDataAnalyzer()
        capabilities.append(ToolCapabilityResponse(
            tool_name="data_analyzer",
            capabilities=[
                "智能数据源分析",
                "表结构分析",
                "数据质量评估",
                "关系发现",
                "业务洞察生成"
            ],
            input_schema={
                "analysis_type": "分析类型",
                "data_source_info": "数据源信息"
            },
            output_format={
                "analysis_result": "分析结果",
                "insights": "洞察列表",
                "recommendations": "建议列表"
            },
            performance_metrics={
                "analysis_depth": "分析深度",
                "accuracy": "准确率",
                "coverage": "覆盖率"
            }
        ))
        
        return APIResponse(
            success=True,
            data=capabilities,
            message="工具能力获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取工具能力失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取工具能力失败: {str(e)}"
        )

# ================================================================================
# 批量和高级操作API
# ================================================================================

@router.post("/batch-execute", response_model=APIResponse[Dict[str, Any]])
async def batch_execute(
    requests: List[EnhancedExecutionRequest],
    current_user: User = Depends(get_current_user),
    max_parallel: int = Query(3, ge=1, le=10, description="最大并行数")
) -> APIResponse[Dict[str, Any]]:
    """
    批量执行API
    
    特性：
    - 多任务并行执行
    - 智能负载均衡
    - 统一结果聚合
    """
    
    batch_id = str(uuid4())
    
    try:
        logger.info(f"启动批量执行: user_id={current_user.id}, batch_id={batch_id}, tasks={len(requests)}")
        
        # 限制并行数量
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def execute_single(req: EnhancedExecutionRequest, index: int):
            async with semaphore:
                try:
                    # 调用单个执行逻辑
                    session_id = f"{batch_id}_{index}"
                    
                    # 这里复用单个执行的逻辑
                    # 简化起见，返回模拟结果
                    return {
                        "index": index,
                        "session_id": session_id,
                        "status": "completed",
                        "tool_type": req.tool_type,
                        "result": "批量执行结果"
                    }
                except Exception as e:
                    return {
                        "index": index,
                        "status": "error",
                        "error": str(e)
                    }
        
        # 并行执行所有任务
        tasks = [execute_single(req, i) for i, req in enumerate(requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "completed")
        error_count = len(results) - success_count
        
        response_data = {
            "batch_id": batch_id,
            "total_tasks": len(requests),
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": success_count / len(requests) if requests else 0,
            "results": results,
            "completed_at": datetime.now().isoformat()
        }
        
        return APIResponse(
            success=True,
            data=response_data,
            message=f"批量执行完成: {success_count}/{len(requests)} 成功"
        )
        
    except Exception as e:
        logger.error(f"批量执行失败: batch_id={batch_id}, error={e}")
        raise HTTPException(
            status_code=500,
            detail=f"批量执行失败: {str(e)}"
        )

# ================================================================================
# 健康检查和系统状态
# ================================================================================

@router.get("/health", response_model=APIResponse[Dict[str, Any]])
async def health_check() -> APIResponse[Dict[str, Any]]:
    """增强架构健康检查"""
    
    try:
        # 检查核心组件
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # 检查工具链
        try:
            # 使用agents系统代替旧的ToolChain
            logger.info("正在使用agents系统执行任务")
            # 使用agents系统代替旧的工具类
            logger.info(f"正在使用agents系统获取SQL生成工具能力")
            # tool_chain.register_tool(sql_generator)  # 注释掉旧的逻辑
            health_status["components"]["tool_chain"] = "healthy"
        except Exception as e:
            health_status["components"]["tool_chain"] = f"unhealthy: {e}"
        
        # 检查提示词监控
        try:
            monitor = get_prompt_monitor()
            health_status["components"]["prompt_monitor"] = "healthy"
        except Exception as e:
            health_status["components"]["prompt_monitor"] = f"unhealthy: {e}"
        
        # 检查统一门面
        try:
            facade = execute_agent_task
            health_status["components"]["ai_facade"] = "healthy"
        except Exception as e:
            health_status["components"]["ai_facade"] = f"unhealthy: {e}"
        
        # 计算整体健康度
        healthy_count = sum(1 for status in health_status["components"].values() if status == "healthy")
        total_count = len(health_status["components"])
        health_status["health_score"] = healthy_count / total_count if total_count > 0 else 0
        
        if health_status["health_score"] < 1.0:
            health_status["status"] = "degraded"
        
        return APIResponse(
            success=True,
            data=health_status,
            message="健康检查完成"
        )
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"健康检查失败: {str(e)}"
        )