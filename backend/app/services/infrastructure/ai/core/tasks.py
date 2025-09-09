"""
Agent 任务定义
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional


class TaskType(Enum):
    """任务类型"""
    TEMPLATE_ANALYSIS = "template_analysis"
    PLACEHOLDER_ANALYSIS = "placeholder_analysis"
    SQL_GENERATION = "sql_generation" 
    SQL_REPAIR = "sql_repair"
    DATA_TRANSFORMATION = "data_transformation"
    REPORT_GENERATION = "report_generation"
    FULL_WORKFLOW = "full_workflow"


@dataclass
class AgentTask:
    """Agent 任务定义"""
    type: TaskType
    task_id: str
    user_id: str
    
    # 任务数据
    data: Dict[str, Any]
    
    # 任务配置
    config: Optional[Dict[str, Any]] = None
    
    # 优先级和超时
    priority: int = 5  # 1-10, 10为最高
    timeout_seconds: Optional[int] = 300  # 5分钟默认超时
    
    # 任务元数据
    created_at: Optional[str] = None
    parent_task_id: Optional[str] = None
    
    def get_template_id(self) -> Optional[str]:
        """获取模板ID"""
        return self.data.get("template_id")
    
    def get_data_source_id(self) -> Optional[str]:
        """获取数据源ID"""
        return self.data.get("data_source_id")
    
    def get_template_content(self) -> Optional[str]:
        """获取模板内容"""
        return self.data.get("template_content")
    
    def get_placeholders(self) -> Optional[list]:
        """获取占位符列表"""
        return self.data.get("placeholders", [])
    
    def requires_llm(self) -> bool:
        """判断是否需要LLM处理"""
        llm_required_tasks = {
            TaskType.TEMPLATE_ANALYSIS,
            TaskType.PLACEHOLDER_ANALYSIS,
            TaskType.SQL_GENERATION,
            TaskType.SQL_REPAIR,
            TaskType.DATA_TRANSFORMATION
        }
        return self.type in llm_required_tasks
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.type.value,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "data": self.data,
            "config": self.config,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at,
            "parent_task_id": self.parent_task_id
        }