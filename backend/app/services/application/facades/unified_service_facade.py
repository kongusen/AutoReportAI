"""
Unified Service Facade

统一服务门面，为外部提供简化的API接口
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..orchestration.service_orchestrator import ServiceOrchestrator, OrchestrationMode
from ..task_management.core.scheduler import TaskScheduler as RefactoredTaskManager

logger = logging.getLogger(__name__)


class UnifiedServiceFacade:
    """统一服务门面"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.orchestrator = ServiceOrchestrator()
        self.db_session = db_session
        self._task_manager: Optional[RefactoredTaskManager] = None
    
    async def get_task_manager(self) -> RefactoredTaskManager:
        """获取任务管理器"""
        if self._task_manager is None:
            from ...task.refactored_task_module import create_task_manager
            self._task_manager = await create_task_manager(self.db_session)
        return self._task_manager
    
    # ========== 任务管理相关接口 ==========
    
    async def create_task(self, task_data: Dict[str, Any], owner_id: str) -> Dict[str, Any]:
        """创建任务"""
        try:
            task_manager = await self.get_task_manager()
            task = await task_manager.create_task(task_data, owner_id)
            
            return {
                "success": True,
                "data": task.to_dict()
            }
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_task(self, task_id: str, user_id: str, 
                          context: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行任务"""
        try:
            task_manager = await self.get_task_manager()
            result = await task_manager.execute_task(
                task_id=task_id,
                execution_mode="manual",  # 简化为字符串
                context=context,
                triggered_by=user_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute task {task_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            task_manager = await self.get_task_manager()
            return await task_manager.get_task_status(task_id)
            
        except Exception as e:
            logger.error(f"Failed to get task status {task_id}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_user_tasks(self, user_id: str, 
                           filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """获取用户任务列表"""
        try:
            task_manager = await self.get_task_manager()
            tasks = await task_manager.get_user_tasks(
                user_id=user_id,
                filters=filters or {}
            )
            
            return {
                "success": True,
                "data": [task.to_dict() for task in tasks]
            }
            
        except Exception as e:
            logger.error(f"Failed to get user tasks for {user_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========== 报告生成相关接口 ==========
    
    async def generate_report(self, template_id: str, data_source_id: str,
                            user_id: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成报告"""
        try:
            # 使用编排器执行报告生成流水线
            request = {
                "request_id": f"report_{template_id}_{user_id}",
                "user_id": user_id,
                "pipeline": [
                    {
                        "name": "parse_template",
                        "service": "template",
                        "method": "analyze_template_structure",
                        "parameters": {"template_id": template_id}
                    },
                    {
                        "name": "analyze_placeholders",
                        "service": "placeholder",
                        "method": "extract_and_analyze_placeholders",
                        "parameters": {
                            "data_source_id": data_source_id,
                            "parameters": parameters or {}
                        },
                        "use_previous_result": True
                    },
                    {
                        "name": "generate_report",
                        "service": "reporting",
                        "method": "generate_report_content",
                        "parameters": {
                            "template_id": template_id,
                            "user_id": user_id
                        },
                        "use_previous_result": True
                    }
                ]
            }
            
            result = await self.orchestrator.execute(request, OrchestrationMode.PIPELINE)
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========== 数据分析相关接口 ==========
    
    async def analyze_data(self, data_source_id: str, analysis_type: str = "descriptive",
                          user_id: str = None) -> Dict[str, Any]:
        """分析数据"""
        try:
            request = {
                "request_id": f"analysis_{data_source_id}_{user_id}",
                "user_id": user_id,
                "service": "analysis",
                "method": "analyze_data_source",
                "parameters": {
                    "data_source_id": data_source_id,
                    "analysis_type": analysis_type
                }
            }
            
            result = await self.orchestrator.execute(request, OrchestrationMode.SIMPLE)
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze data: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========== 模板管理相关接口 ==========
    
    async def validate_template(self, template_content: str,
                              template_type: str = "report") -> Dict[str, Any]:
        """验证模板"""
        try:
            request = {
                "service": "template",
                "method": "validate_template_content",
                "parameters": {
                    "content": template_content,
                    "template_type": template_type
                }
            }
            
            result = await self.orchestrator.execute(request, OrchestrationMode.SIMPLE)
            return result
            
        except Exception as e:
            logger.error(f"Failed to validate template: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def analyze_template(self, template_content: str) -> Dict[str, Any]:
        """分析模板结构"""
        try:
            request = {
                "service": "template",
                "method": "parse_template_structure",
                "parameters": {
                    "content": template_content
                }
            }
            
            result = await self.orchestrator.execute(request, OrchestrationMode.SIMPLE)
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze template: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========== 占位符相关接口 ==========
    
    async def extract_placeholders(self, content: str,
                                 context: Dict[str, Any] = None) -> Dict[str, Any]:
        """提取占位符"""
        try:
            request = {
                "service": "placeholder",
                "method": "extract_placeholders",
                "parameters": {
                    "content": content,
                    "context": context or {}
                }
            }
            
            result = await self.orchestrator.execute(request, OrchestrationMode.SIMPLE)
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract placeholders: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def analyze_placeholder(self, placeholder_name: str, 
                                description: str = "",
                                data_source_id: str = None) -> Dict[str, Any]:
        """分析占位符"""
        try:
            request = {
                "service": "placeholder",
                "method": "analyze_placeholder_semantics",
                "parameters": {
                    "placeholder_name": placeholder_name,
                    "description": description,
                    "data_source_id": data_source_id
                }
            }
            
            result = await self.orchestrator.execute(request, OrchestrationMode.SIMPLE)
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze placeholder: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========== 高级编排接口 ==========
    
    async def execute_workflow(self, workflow_definition: Dict[str, Any],
                             inputs: Dict[str, Any] = None,
                             user_id: str = None) -> Dict[str, Any]:
        """执行工作流"""
        try:
            request = {
                "request_id": f"workflow_{workflow_definition.get('workflow_id', 'unknown')}",
                "user_id": user_id,
                "workflow": workflow_definition,
                "inputs": inputs or {}
            }
            
            result = await self.orchestrator.execute(request, OrchestrationMode.WORKFLOW)
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute workflow: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_ai_driven_task(self, goal: str, user_id: str,
                                   available_services: List[str] = None,
                                   constraints: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行AI驱动的任务"""
        try:
            request = {
                "request_id": f"ai_task_{user_id}_{hash(goal)}",
                "user_id": user_id,
                "use_ai_context": True,
                "goal": goal,
                "services": available_services or ["template", "placeholder", "analysis", "reporting"],
                "constraints": constraints or {}
            }
            
            result = await self.orchestrator.execute(request, OrchestrationMode.AI_DRIVEN)
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute AI-driven task: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========== 批量操作接口 ==========
    
    async def batch_process(self, operations: List[Dict[str, Any]],
                          parallel: bool = False) -> Dict[str, Any]:
        """批量处理操作"""
        try:
            if parallel:
                request = {
                    "tasks": [
                        {
                            "name": op.get("name", f"op_{i}"),
                            "service": op["service"],
                            "method": op["method"],
                            "parameters": op.get("parameters", {})
                        }
                        for i, op in enumerate(operations)
                    ]
                }
                mode = OrchestrationMode.PARALLEL
            else:
                request = {
                    "pipeline": [
                        {
                            "name": op.get("name", f"step_{i}"),
                            "service": op["service"],
                            "method": op["method"],
                            "parameters": op.get("parameters", {}),
                            "use_previous_result": op.get("use_previous_result", False)
                        }
                        for i, op in enumerate(operations)
                    ]
                }
                mode = OrchestrationMode.PIPELINE
            
            result = await self.orchestrator.execute(request, mode)
            return result
            
        except Exception as e:
            logger.error(f"Failed to batch process operations: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========== 系统管理接口 ==========
    
    async def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        try:
            health_check = await self.orchestrator.health_check()
            
            # 添加任务管理器状态
            try:
                task_manager = await self.get_task_manager()
                scheduler_status = await task_manager.get_scheduler_status()
                health_check["services"]["task_scheduler"] = scheduler_status
            except Exception as e:
                health_check["services"]["task_scheduler"] = {"status": "error", "error": str(e)}
            
            return {
                "success": True,
                "data": health_check
            }
            
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_service_registry(self) -> Dict[str, Any]:
        """获取服务注册表"""
        try:
            registry = self.orchestrator.get_service_registry()
            
            return {
                "success": True,
                "data": registry
            }
            
        except Exception as e:
            logger.error(f"Failed to get service registry: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self._task_manager:
                await self._task_manager.stop_scheduler()
            
            logger.info("Unified service facade cleaned up")
            
        except Exception as e:
            logger.error(f"Failed to cleanup service facade: {e}")


# 全局实例（可选）
_global_facade: Optional[UnifiedServiceFacade] = None


async def get_global_facade(db_session: Optional[Session] = None) -> UnifiedServiceFacade:
    """获取全局门面实例"""
    global _global_facade
    if _global_facade is None:
        _global_facade = UnifiedServiceFacade(db_session)
    return _global_facade


async def cleanup_global_facade():
    """清理全局门面实例"""
    global _global_facade
    if _global_facade:
        await _global_facade.cleanup()
        _global_facade = None