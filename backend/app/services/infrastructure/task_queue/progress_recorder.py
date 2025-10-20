"""
统一任务进度记录与通知工具

负责：
- 将进度事件写入 TaskExecution.progress_details
- 更新进度百分比与当前步骤
- 通过 WebSocket 流水线通知服务推送实时进度
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.services.infrastructure.websocket.pipeline_notifications import (
    PipelineTaskStatus,
    PipelineTaskType,
    notify_task_complete,
    notify_task_error,
    notify_task_progress,
    notify_task_start,
)

logger = logging.getLogger(__name__)


def _dispatch_async(coro):
    """在同步或异步环境中安全调度协程执行。"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
    else:
        loop.create_task(coro)


class TaskProgressRecorder:
    """封装任务进度写入和通知逻辑。"""

    def __init__(
        self,
        db: Session,
        task,
        task_execution,
        *,
        websocket_task_id: Optional[str] = None,
    ) -> None:
        self.db = db
        self.task = task
        self.task_execution = task_execution
        self.task_id = task.id
        self.execution_id = str(task_execution.execution_id)
        self.websocket_task_id = websocket_task_id or f"report_task_{self.execution_id}"
        self.user_id = str(task.owner_id)
        self.template_id = str(getattr(task, "template_id", "") or "")
        self.data_source_id = str(getattr(task, "data_source_id", "") or "")
        self.started = False

    # ------------------------------------------------------------------ #
    # 公共 API
    # ------------------------------------------------------------------ #
    def start(self, message: str = "任务开始") -> None:
        """标记任务开始并发送首次通知。"""
        if self.started:
            return

        self._append_event(
            progress=0,
            message=message,
            stage="initialization",
            status="running",
        )
        self.started = True

        details = {
            "template_id": self.template_id,
            "data_source_id": self.data_source_id,
            "task_internal_id": self.task_id,
        }
        _dispatch_async(
            notify_task_start(
                task_id=self.websocket_task_id,
                task_type=PipelineTaskType.REPORT_ASSEMBLY,
                user_id=self.user_id,
                message=message,
                template_id=self.template_id or None,
                data_source_id=self.data_source_id or None,
            )
        )
        _dispatch_async(
            notify_task_progress(
                task_id=self.websocket_task_id,
                status=PipelineTaskStatus.SCANNING,
                progress=0.0,
                message=message,
                details=details,
            )
        )

    def update(
        self,
        progress: int,
        message: str,
        *,
        stage: Optional[str] = None,
        status: str = "running",
        pipeline_status: PipelineTaskStatus = PipelineTaskStatus.ANALYZING,
        placeholder: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        record_only: bool = False,
    ) -> None:
        """
        更新任务进度。

        Args:
            progress: 0-100 的进度百分比
            message: 当前步骤描述
            stage: 自定义阶段标记
            status: running/success/failed
            pipeline_status: WebSocket 端的状态枚举
            placeholder: 关联的占位符名称
            details: 额外信息
            error: 错误信息（若有）
            record_only: 若为 True，仅记录事件不更新 progress_percentage
        """
        if not self.started:
            self.start()

        self._append_event(
            progress=progress,
            message=message,
            stage=stage,
            status=status,
            placeholder=placeholder,
            details=details,
            error=error,
            update_percentage=not record_only,
        )

        ws_details = {
            "stage": stage,
            "status": status,
            "placeholder": placeholder,
            **(details or {}),
        }
        ws_progress = (self.task_execution.progress_percentage or 0) / 100.0
        _dispatch_async(
            notify_task_progress(
                task_id=self.websocket_task_id,
                status=pipeline_status,
                progress=ws_progress,
                message=message,
                details=ws_details,
            )
        )

    def complete(self, message: str = "任务执行完成", result: Optional[Dict[str, Any]] = None) -> None:
        """任务成功完成。"""
        self._append_event(
            progress=100,
            message=message,
            stage="completion",
            status="success",
        )
        _dispatch_async(
            notify_task_complete(
                task_id=self.websocket_task_id,
                result_data=result,
                message=message,
            )
        )

    def fail(
        self,
        message: str,
        *,
        stage: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """任务失败通知。"""
        self._append_event(
            progress=self.task_execution.progress_percentage or 0,
            message=message,
            stage=stage,
            status="failed",
            details=error_details,
        )
        _dispatch_async(
            notify_task_error(
                task_id=self.websocket_task_id,
                error_message=message,
                error_details=error_details,
            )
        )

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _append_event(
        self,
        *,
        progress: int,
        message: str,
        stage: Optional[str],
        status: str,
        placeholder: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        update_percentage: bool = True,
    ) -> None:
        """写入数据库 JSON 字段并更新基础进度信息。"""
        from app.models.task import TaskStatus

        self.db.refresh(self.task_execution)
        if self.task_execution.execution_status == TaskStatus.CANCELLED:
            raise Exception("任务已被用户取消")

        event: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "progress": progress,
            "message": message,
            "stage": stage,
            "status": status,
        }
        if placeholder:
            event["placeholder"] = placeholder
        if details:
            event["details"] = details
        if error:
            event["error"] = error

        progress_details = list(self.task_execution.progress_details or [])
        progress_details.append(event)
        # 限制长度，避免无限增长
        self.task_execution.progress_details = progress_details[-200:]
        flag_modified(self.task_execution, "progress_details")

        if update_percentage:
            self.task_execution.progress_percentage = progress
            self.task_execution.current_step = message

        self.db.commit()
        logger.info(
            "Task %s progress updated to %s%% - %s",
            self.task_id,
            progress,
            message,
        )

