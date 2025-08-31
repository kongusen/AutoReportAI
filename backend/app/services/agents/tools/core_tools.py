"""
核心工作流工具集合
提供系统级工作流编排和诊断功能
"""

import json
import logging
from typing import List, Dict, Any, Optional

from llama_index.core.tools import FunctionTool

from .base_tool import ToolsCollection, create_standard_tool
from ...application.workflows.intelligent_placeholder_workflow import IntelligentPlaceholderWorkflow
from ...application.workflows.enhanced_report_generation_workflow import EnhancedReportGenerationWorkflow
from ...application.workflows.context_aware_task_service import ContextAwareTaskService

logger = logging.getLogger(__name__)


class CoreToolsCollection(ToolsCollection):
    """核心工作流工具集合"""
    
    def __init__(self):
        super().__init__(category="core")
        
        # 初始化工作流服务
        self.placeholder_workflow = None
        self.report_workflow = None
        self.task_service = None
    
    async def _get_placeholder_workflow(self):
        """获取占位符工作流"""
        if not self.placeholder_workflow:
            self.placeholder_workflow = IntelligentPlaceholderWorkflow()
        return self.placeholder_workflow
    
    async def _get_report_workflow(self):
        """获取报告生成工作流"""
        if not self.report_workflow:
            self.report_workflow = EnhancedReportGenerationWorkflow()
        return self.report_workflow
    
    async def _get_task_service(self):
        """获取上下文感知任务服务"""
        if not self.task_service:
            self.task_service = ContextAwareTaskService()
        return self.task_service
    
    def create_tools(self) -> List[FunctionTool]:
        """创建核心工作流工具列表"""
        return [
            self._create_complete_analysis_workflow_tool(),
            self._create_placeholder_workflow_tool(),
            self._create_system_diagnostic_tool(),
            self._create_workflow_status_tool()
        ]
    
    def _create_complete_analysis_workflow_tool(self) -> FunctionTool:
        """创建完整分析工作流工具"""
        
        async def execute_complete_analysis_workflow(
            template_content: str,
            data_source_id: str,
            analysis_requirements: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            执行端到端的完整分析工作流
            
            Args:
                template_content: 模板内容
                data_source_id: 数据源ID
                analysis_requirements: 分析需求描述
                
            Returns:
                完整分析工作流结果
            """
from llama_index.core.tools import FunctionTool
