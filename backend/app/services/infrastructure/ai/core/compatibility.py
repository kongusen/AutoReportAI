"""
兼容性适配器 - 确保平滑迁移到新的统一架构
保持现有API接口不变，内部使用新的tt函数
"""

import logging
from typing import Dict, Any, AsyncGenerator, Optional

from .messages import AgentMessage
from .tasks import AgentTask, TaskType
from .tools import ToolContext
from .unified_controller import tt
from .controller import AgentController  # 保留原始控制器作为后备

logger = logging.getLogger(__name__)


class CompatibilityLayer:
    """
    兼容性适配器 - 确保平滑迁移
    
    功能：
    1. 保持原有API接口不变
    2. 内部使用新的统一架构
    3. 出错时自动降级到旧系统
    4. 逐步迁移功能
    """
    
    def __init__(self):
        # 新旧系统实例
        self.old_controller = AgentController()
        
        # 特性开关
        self.enable_unified_system = True  # 可以通过环境变量控制
        self.fallback_on_error = True
        
        # 统计信息
        self.new_system_usage = 0
        self.old_system_usage = 0
        self.fallback_count = 0
    
    async def execute_task_compatible(
        self, 
        task: AgentTask
    ) -> AsyncGenerator[AgentMessage, None]:
        """
        兼容原有的execute_task接口
        
        Args:
            task: 原始任务对象
            
        Yields:
            AgentMessage: 执行结果消息
        """
        
        if not self.enable_unified_system:
            logger.info("使用旧系统执行任务（特性开关关闭）")
            self.old_system_usage += 1
            async for result in self.old_controller.execute_task(task):
                yield result
            return
        
        try:
            # 尝试使用新的统一系统
            logger.info(f"使用新系统执行任务: {task.type.value}")
            self.new_system_usage += 1
            
            # 转换任务为新格式
            goal = self._convert_task_to_goal(task)
            context = self._convert_task_to_context(task)
            
            # 使用新的tt函数
            async for result in tt(goal, context, max_iterations=3):
                yield result
                
        except Exception as e:
            logger.warning(f"新系统执行失败，回退到旧系统: {e}")
            
            if self.fallback_on_error:
                self.fallback_count += 1
                self.old_system_usage += 1
                
                # 回退到原系统
                try:
                    async for result in self.old_controller.execute_task(task):
                        yield result
                except Exception as fallback_error:
                    logger.error(f"旧系统也执行失败: {fallback_error}")
                    yield AgentMessage.create_error(
                        error_type="system_failure",
                        error_message=f"新旧系统都执行失败。新系统错误: {str(e)}，旧系统错误: {str(fallback_error)}",
                        user_id=task.user_id,
                        task_id=task.task_id
                    )
            else:
                # 不使用回退，直接报错
                yield AgentMessage.create_error(
                    error_type="unified_system_error",
                    error_message=f"统一系统执行失败: {str(e)}",
                    user_id=task.user_id,
                    task_id=task.task_id
                )
    
    def _convert_task_to_goal(self, task: AgentTask) -> str:
        """将旧的AgentTask转换为新的goal描述"""
        
        task_type_goals = {
            TaskType.TEMPLATE_ANALYSIS: self._build_template_analysis_goal(task),
            TaskType.PLACEHOLDER_ANALYSIS: self._build_placeholder_analysis_goal(task),
            TaskType.SQL_GENERATION: self._build_sql_generation_goal(task),
            TaskType.FULL_WORKFLOW: self._build_full_workflow_goal(task)
        }
        
        return task_type_goals.get(
            task.type, 
            f"执行 {task.type.value} 任务"
        )
    
    def _build_template_analysis_goal(self, task: AgentTask) -> str:
        """构建模板分析目标"""
        template_id = task.get_template_id()
        return f"分析模板 {template_id} 中的所有占位符，识别其数据需求和业务用途"
    
    def _build_placeholder_analysis_goal(self, task: AgentTask) -> str:
        """构建占位符分析目标"""
        placeholder_name = task.data.get("placeholder_name", "未知占位符")
        template_context = task.data.get("template_context", "")
        
        goal = f"分析占位符 '{placeholder_name}' 并生成相应的SQL查询"
        
        if template_context:
            goal += f"，占位符出现在以下上下文中：{template_context[:100]}..."
        
        return goal
    
    def _build_sql_generation_goal(self, task: AgentTask) -> str:
        """构建SQL生成目标"""
        placeholders = task.data.get("placeholders", [])
        if placeholders and isinstance(placeholders, list):
            placeholder_names = [p.get("name", "未知") for p in placeholders[:3]]
            return f"为占位符 {', '.join(placeholder_names)} 生成合适的SQL查询语句"
        else:
            return "根据业务需求生成SQL查询语句"
    
    def _build_full_workflow_goal(self, task: AgentTask) -> str:
        """构建完整工作流目标"""
        template_id = task.get_template_id()
        data_source_id = task.get_data_source_id()
        return f"执行完整的报告生成工作流，分析模板 {template_id}，连接数据源 {data_source_id}，生成最终报告"
    
    def _convert_task_to_context(self, task: AgentTask) -> ToolContext:
        """将AgentTask转换为ToolContext"""
        
        # 创建基础上下文
        context = ToolContext(
            user_id=task.user_id,
            task_id=task.task_id,
            session_id=f"compat_{task.task_id}",
            context_data=task.data.copy() if task.data else {},
            tool_config=task.config.copy() if task.config else {}
        )
        
        # 添加任务特定信息
        if hasattr(task, 'get_template_id'):
            template_id = task.get_template_id()
            if template_id:
                context.template_id = template_id
        
        if hasattr(task, 'get_data_source_id'):
            data_source_id = task.get_data_source_id()
            if data_source_id:
                context.data_source_id = data_source_id
        
        # 添加特定任务类型的上下文信息
        if task.type == TaskType.PLACEHOLDER_ANALYSIS:
            self._add_placeholder_context(task, context)
        elif task.type == TaskType.SQL_GENERATION:
            self._add_sql_context(task, context)
        
        return context
    
    def _add_placeholder_context(self, task: AgentTask, context: ToolContext):
        """为占位符分析添加特定上下文"""
        if task.data:
            context.placeholders = [task.data]  # 将单个占位符数据包装成列表
            
            # 添加数据源信息
            data_source_info = task.data.get("data_source_info", {})
            if data_source_info:
                context.data_source_info = data_source_info
            
            # 添加模板上下文
            template_context = task.data.get("template_context", "")
            if template_context:
                context.template_content = template_context
    
    def _add_sql_context(self, task: AgentTask, context: ToolContext):
        """为SQL生成添加特定上下文"""
        if task.data:
            placeholders = task.data.get("placeholders", [])
            if placeholders:
                context.placeholders = placeholders
    
    def get_migration_statistics(self) -> Dict[str, Any]:
        """获取迁移统计信息"""
        total_usage = self.new_system_usage + self.old_system_usage
        
        return {
            "total_usage": total_usage,
            "new_system_usage": self.new_system_usage,
            "old_system_usage": self.old_system_usage,
            "fallback_count": self.fallback_count,
            "new_system_rate": self.new_system_usage / total_usage if total_usage > 0 else 0,
            "fallback_rate": self.fallback_count / self.new_system_usage if self.new_system_usage > 0 else 0,
            "settings": {
                "enable_unified_system": self.enable_unified_system,
                "fallback_on_error": self.fallback_on_error
            }
        }
    
    def set_unified_system_enabled(self, enabled: bool):
        """设置统一系统是否启用"""
        self.enable_unified_system = enabled
        logger.info(f"统一系统{'启用' if enabled else '禁用'}")
    
    def set_fallback_enabled(self, enabled: bool):
        """设置是否启用错误回退"""
        self.fallback_on_error = enabled
        logger.info(f"错误回退{'启用' if enabled else '禁用'}")


# 创建全局兼容性层实例
_compatibility_layer: Optional[CompatibilityLayer] = None


def get_compatibility_layer() -> CompatibilityLayer:
    """获取全局兼容性层实例"""
    global _compatibility_layer
    if _compatibility_layer is None:
        _compatibility_layer = CompatibilityLayer()
    return _compatibility_layer


# 便捷函数 - 可以直接替换原有的AgentController使用
async def execute_task_unified(task: AgentTask) -> AsyncGenerator[AgentMessage, None]:
    """
    统一的任务执行函数 - 可以直接替换 AgentController.execute_task
    
    Args:
        task: 原始任务对象
        
    Yields:
        AgentMessage: 执行结果消息
    """
    compatibility_layer = get_compatibility_layer()
    async for result in compatibility_layer.execute_task_compatible(task):
        yield result


# 便捷导出
__all__ = [
    "CompatibilityLayer",
    "get_compatibility_layer",
    "execute_task_unified"
]