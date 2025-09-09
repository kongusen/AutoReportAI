"""
服务编排器 - Claude Code 架构的统一入口
整合AgentController和现有系统，提供向后兼容的接口
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, AsyncGenerator, Optional

from .core import (
    AgentController, 
    AgentTask, 
    TaskType, 
    AgentMessage, 
    MessageType
)
from .tools.template_analysis_tool import create_template_analysis_tool
from .tools.sql_generation_tool import create_sql_generation_tool

logger = logging.getLogger(__name__)


class ServiceOrchestrator:
    """服务编排器 - 统一管理新旧架构"""
    
    def __init__(self):
        self.controller = AgentController()
        self._initialize_tools()
        logger.info("服务编排器初始化完成")
    
    def _initialize_tools(self):
        """初始化所有工具"""
        # 注册新架构的工具
        self.controller.register_tool(create_template_analysis_tool())
        self.controller.register_tool(create_sql_generation_tool())
        
    async def analyze_template_streaming(
        self,
        user_id: str,
        template_id: str,
        template_content: str,
        data_source_info: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式模板分析 - 新架构入口
        兼容现有API格式
        """
        
        # 创建任务
        task = AgentTask(
            type=TaskType.TEMPLATE_ANALYSIS,
            task_id=f"template_analysis_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            data={
                "template_id": template_id,
                "template_content": template_content,
                "data_source_info": data_source_info
            },
            created_at=datetime.utcnow().isoformat()
        )
        
        logger.info(f"开始流式模板分析: {task.task_id}")
        
        # 执行任务并转换消息格式
        async for message in self.controller.execute_task(task):
            yield self._convert_message_to_api_format(message)
    
    async def generate_sql_streaming(
        self,
        user_id: str,
        placeholders: list,
        data_source_info: Optional[Dict[str, Any]] = None,
        template_context: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式SQL生成 - 新架构入口
        """
        
        task = AgentTask(
            type=TaskType.SQL_GENERATION,
            task_id=f"sql_generation_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            data={
                "placeholders": placeholders,
                "data_source_info": data_source_info,
                "template_context": template_context
            },
            created_at=datetime.utcnow().isoformat()
        )
        
        logger.info(f"开始流式SQL生成: {task.task_id}")
        
        async for message in self.controller.execute_task(task):
            yield self._convert_message_to_api_format(message)
    
    async def execute_full_workflow_streaming(
        self,
        user_id: str,
        template_id: str,
        template_content: str,
        data_source_id: str,
        data_source_info: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        完整工作流执行 - 从模板分析到SQL生成
        """
        
        task = AgentTask(
            type=TaskType.FULL_WORKFLOW,
            task_id=f"full_workflow_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            data={
                "template_id": template_id,
                "template_content": template_content,
                "data_source_id": data_source_id,
                "data_source_info": data_source_info
            },
            created_at=datetime.utcnow().isoformat()
        )
        
        logger.info(f"开始完整工作流: {task.task_id}")
        
        async for message in self.controller.execute_task(task):
            yield self._convert_message_to_api_format(message)
    
    def _convert_message_to_api_format(self, message: AgentMessage) -> Dict[str, Any]:
        """
        将AgentMessage转换为API格式
        保持与现有前端的兼容性
        """
        
        base_format = {
            "type": message.type.value,
            "uuid": message.uuid,
            "timestamp": message.timestamp,
            "user_id": message.user_id,
            "task_id": message.task_id,
            "tool_name": message.tool_name
        }
        
        if message.type == MessageType.PROGRESS:
            if message.progress:
                base_format.update({
                    "progress": {
                        "current_step": message.progress.current_step,
                        "total_steps": message.progress.total_steps,
                        "current_step_number": message.progress.current_step_number,
                        "percentage": message.progress.percentage,
                        "details": message.progress.details
                    }
                })
        
        elif message.type == MessageType.RESULT:
            base_format["result"] = message.content
        
        elif message.type == MessageType.ERROR:
            if message.error:
                base_format.update({
                    "error": {
                        "error_type": message.error.error_type,
                        "error_message": message.error.error_message,
                        "error_code": message.error.error_code,
                        "recoverable": message.error.recoverable
                    }
                })
        
        return base_format
    
    async def analyze_single_placeholder_streaming(
        self,
        user_id: str,
        placeholder_name: str,
        placeholder_text: str,
        template_id: str,
        template_context: Optional[str] = None,
        data_source_info: Optional[Dict[str, Any]] = None,
        task_params: Optional[Dict[str, Any]] = None,
        cron_expression: Optional[str] = None,
        execution_time: Optional[datetime] = None,
        task_type: str = "manual"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        单个占位符分析 - 流式处理
        """
        
        task = AgentTask(
            type=TaskType.PLACEHOLDER_ANALYSIS,
            task_id=f"placeholder_analysis_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            data={
                "placeholder_name": placeholder_name,
                "placeholder_text": placeholder_text,
                "template_id": template_id,
                "template_context": template_context,
                "data_source_info": data_source_info,
                "task_params": task_params or {},
                "cron_expression": cron_expression,
                "execution_time": execution_time,
                "task_type": task_type
            },
            created_at=datetime.utcnow().isoformat()
        )
        
        logger.info(f"开始单个占位符分析: {task.task_id}")
        
        async for message in self.controller.execute_task(task):
            yield self._convert_message_to_api_format(message)
    
    async def analyze_single_placeholder_simple(
        self,
        user_id: str,
        placeholder_name: str,
        placeholder_text: str,
        template_id: str,
        template_context: Optional[str] = None,
        data_source_info: Optional[Dict[str, Any]] = None,
        task_params: Optional[Dict[str, Any]] = None,
        cron_expression: Optional[str] = None,
        execution_time: Optional[datetime] = None,
        task_type: str = "manual"
    ) -> Dict[str, Any]:
        """
        单个占位符分析 - 非流式，向后兼容，支持时间上下文
        """
        
        result = None
        error = None
        
        async for message_data in self.analyze_single_placeholder_streaming(
            user_id=user_id,
            placeholder_name=placeholder_name,
            placeholder_text=placeholder_text,
            template_id=template_id,
            template_context=template_context,
            data_source_info=data_source_info,
            task_params=task_params,
            cron_expression=cron_expression,
            execution_time=execution_time,
            task_type=task_type
        ):
            if message_data["type"] == "result":
                result = message_data["result"]
            elif message_data["type"] == "error":
                error = message_data["error"]
        
        if error:
            return {
                "status": "error",
                "error": error,
                "placeholder_name": placeholder_name
            }
        
        return result or {
            "status": "completed",
            "placeholder_name": placeholder_name,
            "analysis": "分析完成，但未收到具体结果",
            "generated_sql": "",
            "confidence_score": 0.0
        }

    # 向后兼容方法 - 支持现有的非流式调用
    
    async def analyze_template_simple(
        self,
        user_id: str,
        template_id: str,
        template_content: str,
        data_source_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        简单模板分析 - 非流式，向后兼容
        """
        
        result = None
        error = None
        
        async for message_data in self.analyze_template_streaming(
            user_id=user_id,
            template_id=template_id,
            template_content=template_content,
            data_source_info=data_source_info
        ):
            if message_data["type"] == "result":
                result = message_data["result"]
            elif message_data["type"] == "error":
                error = message_data["error"]
        
        if error:
            return {
                "status": "error",
                "error": error,
                "template_id": template_id
            }
        
        return result or {
            "status": "completed",
            "template_id": template_id,
            "placeholder_analysis": {
                "total_count": 0,
                "placeholders": [],
                "processing_status": "no_result"
            }
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self.controller.get_task_status(task_id)
    
    def list_active_tasks(self) -> list:
        """列出活跃任务"""
        return self.controller.list_active_tasks()
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        return await self.controller.cancel_task(task_id)


# 全局实例
_orchestrator: Optional[ServiceOrchestrator] = None


def get_service_orchestrator() -> ServiceOrchestrator:
    """获取服务编排器单例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ServiceOrchestrator()
    return _orchestrator


# 向后兼容的便捷函数

async def analyze_template_with_new_architecture(
    user_id: str,
    template_id: str,
    template_content: str,
    data_source_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """使用新架构分析模板 - 便捷函数"""
    orchestrator = get_service_orchestrator()
    return await orchestrator.analyze_template_simple(
        user_id=user_id,
        template_id=template_id,
        template_content=template_content,
        data_source_info=data_source_info
    )