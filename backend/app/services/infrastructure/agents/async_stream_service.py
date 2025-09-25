"""
异步流式Agent执行服务
支持长时间运行的Agent任务，实时流式输出每个阶段的进度
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, AsyncGenerator, Optional
from datetime import datetime, timedelta
from enum import Enum
import json

from .orchestrator import UnifiedOrchestrator as Orchestrator
from .planner import AgentPlanner as Planner
from .executor import StepExecutor
from ..agents.facade import AgentFacade

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    OBSERVING = "observing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StreamEvent:
    def __init__(self, event_type: str, data: Dict[str, Any], timestamp: datetime = None):
        self.event_type = event_type
        self.data = data
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AsyncAgentTask:
    def __init__(self, task_id: str, input_data: Dict[str, Any]):
        self.task_id = task_id
        self.input_data = input_data
        self.status = TaskStatus.PENDING
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.result = None
        self.error = None
        self.progress = 0.0
        self.current_step = ""
        self.total_steps = 0
        self.completed_steps = 0

    def update_status(self, status: TaskStatus, step: str = "", progress: float = None):
        self.status = status
        self.updated_at = datetime.utcnow()
        self.current_step = step
        if progress is not None:
            self.progress = progress

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress": self.progress,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "result": self.result,
            "error": self.error
        }


class AsyncAgentStreamService:
    """异步流式Agent执行服务"""

    def __init__(self, container):
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)
        self._active_tasks: Dict[str, AsyncAgentTask] = {}
        self._task_queues: Dict[str, asyncio.Queue] = {}

        # 配置
        self.max_task_duration = 600  # 10分钟超时
        self.cleanup_interval = 3600  # 1小时清理一次过期任务
        self.max_active_tasks = 100  # 最大并发任务数

        # 启动清理任务
        asyncio.create_task(self._cleanup_expired_tasks())

    async def start_async_task(self, input_data: Dict[str, Any]) -> str:
        """启动异步Agent任务"""
        if len(self._active_tasks) >= self.max_active_tasks:
            raise Exception(f"达到最大并发任务数限制: {self.max_active_tasks}")

        task_id = str(uuid.uuid4())
        task = AsyncAgentTask(task_id, input_data)

        self._active_tasks[task_id] = task
        self._task_queues[task_id] = asyncio.Queue()

        self._logger.info(f"🚀 [AsyncAgent] 启动异步任务: {task_id}")

        # 异步执行任务
        asyncio.create_task(self._execute_async_task(task))

        return task_id

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self._active_tasks.get(task_id)
        if not task:
            return None
        return task.to_dict()

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._active_tasks.get(task_id)
        if not task:
            return False

        task.update_status(TaskStatus.CANCELLED)
        self._logger.info(f"🛑 [AsyncAgent] 任务已取消: {task_id}")
        return True

    async def stream_task_events(self, task_id: str) -> AsyncGenerator[StreamEvent, None]:
        """流式获取任务事件"""
        if task_id not in self._task_queues:
            self._logger.error(f"❌ [AsyncAgent] 任务不存在: {task_id}")
            return

        queue = self._task_queues[task_id]
        task = self._active_tasks.get(task_id)

        self._logger.info(f"📡 [AsyncAgent] 开始流式输出: {task_id}")

        try:
            # 首先发送任务状态
            if task:
                yield StreamEvent("task_status", task.to_dict())

            # 流式输出事件
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield event

                    # 如果是完成或失败事件，结束流
                    if event.event_type in ["task_completed", "task_failed"]:
                        break

                except asyncio.TimeoutError:
                    # 检查任务是否仍然活跃
                    if task_id not in self._active_tasks:
                        break

                    current_task = self._active_tasks[task_id]
                    if current_task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                        break

                    # 发送心跳事件
                    yield StreamEvent("heartbeat", {"task_id": task_id, "timestamp": datetime.utcnow().isoformat()})

        except Exception as e:
            self._logger.error(f"❌ [AsyncAgent] 流式输出异常: {str(e)}")
            yield StreamEvent("error", {"error": str(e)})

    async def _execute_async_task(self, task: AsyncAgentTask):
        """执行异步Agent任务"""
        start_time = datetime.utcnow()

        try:
            # 发送任务开始事件
            await self._emit_event(task.task_id, "task_started", {
                "task_id": task.task_id,
                "input_data": task.input_data
            })

            # 1. Planning阶段
            task.update_status(TaskStatus.PLANNING, "正在制定计划...", 10.0)
            await self._emit_event(task.task_id, "stage_started", {
                "stage": "planning",
                "progress": 10.0
            })

            plan_result = await self._execute_planning(task)
            task.total_steps = len(plan_result.get("steps", []))

            await self._emit_event(task.task_id, "planning_completed", {
                "plan": plan_result,
                "total_steps": task.total_steps,
                "progress": 25.0
            })

            # 2. Execution阶段
            task.update_status(TaskStatus.EXECUTING, "正在执行计划...", 25.0)

            execution_results = []
            step_progress_increment = 50.0 / max(task.total_steps, 1)

            for i, step in enumerate(plan_result.get("steps", [])):
                if task.status == TaskStatus.CANCELLED:
                    return

                step_progress = 25.0 + (i + 1) * step_progress_increment
                task.update_status(TaskStatus.EXECUTING, f"执行步骤 {i+1}/{task.total_steps}: {step.get('name', '')}", step_progress)

                await self._emit_event(task.task_id, "step_started", {
                    "step_index": i,
                    "step": step,
                    "progress": step_progress
                })

                step_result = await self._execute_step(task, step, i)
                execution_results.append(step_result)
                task.completed_steps = i + 1

                await self._emit_event(task.task_id, "step_completed", {
                    "step_index": i,
                    "step_result": step_result,
                    "progress": step_progress
                })

            # 3. Observation阶段
            task.update_status(TaskStatus.OBSERVING, "正在观察结果...", 80.0)
            await self._emit_event(task.task_id, "stage_started", {
                "stage": "observing",
                "progress": 80.0
            })

            observation_result = await self._execute_observation(task, execution_results)

            await self._emit_event(task.task_id, "observation_completed", {
                "observation": observation_result,
                "progress": 90.0
            })

            # 4. Finalization阶段
            task.update_status(TaskStatus.FINALIZING, "正在生成最终结果...", 90.0)
            await self._emit_event(task.task_id, "stage_started", {
                "stage": "finalizing",
                "progress": 90.0
            })

            final_result = await self._execute_finalization(task, execution_results, observation_result)

            # 完成任务
            task.update_status(TaskStatus.COMPLETED, "任务已完成", 100.0)
            task.result = final_result

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            await self._emit_event(task.task_id, "task_completed", {
                "result": final_result,
                "execution_time": execution_time,
                "progress": 100.0
            })

            self._logger.info(f"✅ [AsyncAgent] 任务完成: {task.task_id}, 耗时: {execution_time:.2f}s")

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            task.update_status(TaskStatus.FAILED, f"任务失败: {str(e)}")
            task.error = str(e)

            await self._emit_event(task.task_id, "task_failed", {
                "error": str(e),
                "execution_time": execution_time
            })

            self._logger.error(f"❌ [AsyncAgent] 任务失败: {task.task_id}, 错误: {str(e)}")

    async def _emit_event(self, task_id: str, event_type: str, data: Dict[str, Any]):
        """发送事件到流"""
        if task_id in self._task_queues:
            event = StreamEvent(event_type, data)
            try:
                self._task_queues[task_id].put_nowait(event)
            except asyncio.QueueFull:
                self._logger.warning(f"⚠️ [AsyncAgent] 事件队列已满: {task_id}")

    async def _execute_planning(self, task: AsyncAgentTask) -> Dict[str, Any]:
        """执行计划阶段"""
        try:
            facade = AgentFacade(self.container)

            # 使用现有的计划逻辑
            planner = Planner(self.container)
            plan = await planner.create_plan(task.input_data)

            return plan
        except Exception as e:
            self._logger.error(f"❌ [AsyncAgent] 计划阶段失败: {str(e)}")
            raise

    async def _execute_step(self, task: AsyncAgentTask, step: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """执行单个步骤"""
        try:
            executor = StepExecutor(self.container)

            # 构建步骤输入
            step_input = {
                **task.input_data,
                "step": step,
                "step_index": step_index
            }

            result = await executor.execute_step(step_input)
            return result
        except Exception as e:
            self._logger.error(f"❌ [AsyncAgent] 步骤执行失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _execute_observation(self, task: AsyncAgentTask, execution_results: list) -> Dict[str, Any]:
        """执行观察阶段"""
        try:
            # 简化的观察逻辑
            successful_steps = [r for r in execution_results if r.get("success")]
            failed_steps = [r for r in execution_results if not r.get("success")]

            return {
                "total_steps": len(execution_results),
                "successful_steps": len(successful_steps),
                "failed_steps": len(failed_steps),
                "success_rate": len(successful_steps) / len(execution_results) if execution_results else 0,
                "results": execution_results
            }
        except Exception as e:
            self._logger.error(f"❌ [AsyncAgent] 观察阶段失败: {str(e)}")
            raise

    async def _execute_finalization(self, task: AsyncAgentTask, execution_results: list, observation: Dict[str, Any]) -> Dict[str, Any]:
        """执行最终化阶段"""
        try:
            # 获取最终结果
            final_outputs = []
            for result in execution_results:
                if result.get("success") and result.get("output"):
                    final_outputs.append(result["output"])

            return {
                "success": observation.get("success_rate", 0) > 0.5,
                "outputs": final_outputs,
                "summary": observation,
                "execution_metadata": {
                    "task_id": task.task_id,
                    "total_steps": task.total_steps,
                    "completed_steps": task.completed_steps,
                    "execution_time": (task.updated_at - task.created_at).total_seconds()
                }
            }
        except Exception as e:
            self._logger.error(f"❌ [AsyncAgent] 最终化阶段失败: {str(e)}")
            raise

    async def _cleanup_expired_tasks(self):
        """清理过期任务"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)

                current_time = datetime.utcnow()
                expired_tasks = []

                for task_id, task in self._active_tasks.items():
                    if (current_time - task.updated_at).total_seconds() > self.max_task_duration:
                        expired_tasks.append(task_id)

                for task_id in expired_tasks:
                    self._logger.info(f"🧹 [AsyncAgent] 清理过期任务: {task_id}")
                    self._active_tasks.pop(task_id, None)
                    self._task_queues.pop(task_id, None)

            except Exception as e:
                self._logger.error(f"❌ [AsyncAgent] 清理任务异常: {str(e)}")

    def get_active_tasks_count(self) -> int:
        """获取活跃任务数量"""
        return len(self._active_tasks)

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status_counts = {}
        for task in self._active_tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "active_tasks": len(self._active_tasks),
            "max_active_tasks": self.max_active_tasks,
            "status_breakdown": status_counts,
            "system_healthy": len(self._active_tasks) < self.max_active_tasks
        }