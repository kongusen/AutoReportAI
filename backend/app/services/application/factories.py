"""
应用层统一工厂 - 基于Agent系统成功经验

简洁的现代化服务工厂，移除复杂的兼容性包装器。
基于Agent系统提供统一的服务创建接口。
"""

from __future__ import annotations

import logging
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# =============================================================================
# Agent系统核心工厂
# =============================================================================

def create_agent_coordinator(user_id: str = None):
    """创建Agent协调器"""
    from app.services.infrastructure.agents.core.orchestration import AgentCoordinator
    return AgentCoordinator()


def execute_agent_task(
    task_name: str,
    task_description: str,
    context_data: dict,
    user_id: str = None
):
    """执行Agent任务 - 统一的任务执行入口"""
    from app.services.infrastructure.agents import execute_agent_task as execute_task
    return execute_task(
        task_name=task_name,
        task_description=task_description,
        context_data=context_data
    )


# =============================================================================
# 核心业务服务工厂
# =============================================================================

def create_task_application_service(user_id: str = None):
    """创建任务应用服务"""
    from app.services.application.tasks.task_application_service import TaskApplicationService
    return TaskApplicationService()


def create_llm_orchestration_service(db: Session, user_id: str):
    """创建LLM编排服务"""
    if not user_id:
        raise ValueError("user_id is required for LLM Orchestration Service")
    
    from app.services.application.llm.llm_orchestration_service import LLMOrchestrationService
    return LLMOrchestrationService(db, user_id)


def create_data_analysis_service(db: Session, user_id: str = None):
    """创建数据分析服务"""
    from app.services.data.processing.analysis import create_data_analysis_service as create_service
    return create_service(db, user_id)


def create_report_generation_service(db: Session, user_id: str):
    """创建报告生成服务"""
    if not user_id:
        raise ValueError("user_id is required for Report Generation Service")
    
    from app.services.domain.reporting.generator import ReportGenerationService
    return ReportGenerationService(db, user_id)


# =============================================================================
# 基础设施服务工厂
# =============================================================================

def create_notification_service():
    """创建通知服务"""
    from app.services.infrastructure.notification.notification_service import NotificationService
    return NotificationService()


def create_file_storage_service():
    """创建文件存储服务"""
    from app.services.infrastructure.storage.file_storage_service import FileStorageService
    return FileStorageService()


def create_llm_service(db: Session):
    """创建LLM服务"""
    from app.services.infrastructure.llm import get_llm_manager
    return get_llm_manager()


# =============================================================================
# 导出列表
# =============================================================================

__all__ = [
    # Agent系统核心
    "create_agent_coordinator",
    "execute_agent_task",
    
    # 核心业务服务
    "create_task_application_service",
    "create_llm_orchestration_service",
    "create_data_analysis_service",
    "create_report_generation_service",
    
    # 基础设施服务
    "create_notification_service",
    "create_file_storage_service",
    "create_llm_service",
]