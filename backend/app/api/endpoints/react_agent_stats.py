"""
React Agent统计API端点
提供智能模型选择相关的统计数据
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api import deps
from app.services.infrastructure.ai.agents.react_agent import ReactAgent
from app.services.infrastructure.ai.llm.simple_model_selector import get_simple_model_selector

router = APIRouter()


@router.get("/agent-stats")
async def get_react_agent_stats(
    *,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user)
):
    """获取React Agent统计数据"""
    
    try:
        # 获取用户的模型配置统计
        selector = get_simple_model_selector()
        user_stats = selector.get_user_model_stats(str(current_user.id), db)
        
        # 从实际系统获取统计数据
        try:
            from app.services.infrastructure.monitoring.agent_stats_service import agent_stats_service
            agent_stats = await agent_stats_service.get_user_agent_stats(str(current_user.id))
        except Exception as e:
            logger.error(f"获取代理统计数据失败: {e}")
            raise HTTPException(
                status_code=500,
                detail="统计数据不可用"
            )
        
        return {
            "success": True,
            "data": agent_stats,
            "user_model_config": {
                "total_models": user_stats["total_models"],
                "default_models": user_stats["default_models"],
                "think_models": user_stats["think_models"],
                "servers_count": user_stats["servers_count"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "total_agents": 0,
                "active_agents": 0,
                "processing_tasks": 0,
                "completed_today": 0,
                "success_rate": 0,
                "smart_selections_today": 0,
                "model_switches_today": 0,
            }
        }


@router.get("/system-performance")
async def get_system_performance(
    *,
    performance_type: str = "intelligent",
    current_user = Depends(deps.get_current_active_user)
):
    """获取系统性能指标"""
    
    try:
        # 模拟系统性能数据（实际应用中应该从监控系统获取）
        performance_data = {
            "performance_score": 87,
            "response_time": 245,
            "memory_usage": 68,
            "cpu_usage": 34,
            "queue_size": 3,
            "intelligent_features": {
                "model_selection_accuracy": 94,
                "task_analysis_accuracy": 91,
                "auto_optimization_rate": 89
            }
        }
        
        return {
            "success": True,
            "data": performance_data,
            "type": performance_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "performance_score": 0,
                "response_time": 0,
                "memory_usage": 0,
                "cpu_usage": 0,
                "queue_size": 0
            }
        }


@router.get("/recent-activities")
async def get_recent_activities(
    *,
    limit: int = 10,
    current_user = Depends(deps.get_current_active_user)
):
    """获取最近的智能选择活动"""
    
    try:
        # 模拟最近活动数据（实际应用中应该从日志系统获取）
        activities = [
            {
                "type": "smart_model_selection",
                "title": "智能模型选择",
                "description": "React Agent自动检测为推理任务，切换到THINK模型 (claude-3-sonnet)",
                "timestamp": datetime.utcnow() - timedelta(minutes=1),
                "model_type": "THINK",
                "task_type": "reasoning"
            },
            {
                "type": "task_optimization",
                "title": "任务类型优化", 
                "description": "检测到翻译任务，自动切换到成本优化的CHAT模型",
                "timestamp": datetime.utcnow() - timedelta(minutes=3),
                "model_type": "CHAT",
                "task_type": "translation"
            },
            {
                "type": "template_analysis",
                "title": "模板分析完成",
                "description": "React Agent处理了模板 #1234 的占位符分析，智能选择最优模型",
                "timestamp": datetime.utcnow() - timedelta(minutes=8),
                "model_type": "THINK",
                "task_type": "analysis"
            },
            {
                "type": "report_generation",
                "title": "报告生成任务启动",
                "description": "React Agent为复杂分析任务自动选择高推理能力模型",
                "timestamp": datetime.utcnow() - timedelta(minutes=12),
                "model_type": "THINK", 
                "task_type": "reasoning"
            }
        ]
        
        # 转换时间戳为字符串
        for activity in activities:
            activity["timestamp"] = activity["timestamp"].isoformat()
        
        return {
            "success": True,
            "data": activities[:limit],
            "total_count": len(activities),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": []
        }


@router.get("/model-usage-stats")
async def get_model_usage_stats(
    *,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user)
):
    """获取模型使用统计"""
    
    try:
        # 获取用户的模型配置
        selector = get_simple_model_selector()
        user_stats = selector.get_user_model_stats(str(current_user.id), db)
        
        # 模拟模型使用统计
        if user_stats["total_models"] > 0:
            usage_stats = {
                "model_distribution": {
                    "chat_model_usage": 40,  # CHAT模型使用比例
                    "think_model_usage": 60  # THINK模型使用比例
                },
                "current_models": {
                    "chat_model": "gpt-3.5-turbo",
                    "think_model": "claude-3-sonnet"
                },
                "selection_accuracy": {
                    "overall": 94,
                    "reasoning_tasks": 96,
                    "chat_tasks": 92
                },
                "performance_metrics": {
                    "avg_response_time": 245,
                    "success_rate": 95.2,
                    "cost_optimization": 23  # 相比固定模型选择节省的成本百分比
                }
            }
        else:
            usage_stats = {
                "model_distribution": {"chat_model_usage": 0, "think_model_usage": 0},
                "current_models": {"chat_model": None, "think_model": None},
                "selection_accuracy": {"overall": 0},
                "performance_metrics": {"avg_response_time": 0, "success_rate": 0, "cost_optimization": 0}
            }
        
        return {
            "success": True,
            "data": usage_stats,
            "user_config": user_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {}
        }