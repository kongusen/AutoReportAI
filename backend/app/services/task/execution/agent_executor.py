"""
Agent Executor

Agent执行器，负责：
- Agent任务执行
- 结果处理
- 错误处理
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from app.services.agents.orchestration import AgentOrchestrator
from app.services.agents.core_types import AgentResult

logger = logging.getLogger(__name__)


class AgentExecutor:
    """Agent执行器"""
    
    def __init__(self):
        self.orchestrator = AgentOrchestrator()
    
    async def execute_agent_task(
        self,
        agent_input: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """
        执行Agent任务
        
        Args:
            agent_input: Agent输入数据
            context: 执行上下文
            
        Returns:
            Agent执行结果
        """
        try:
            logger.info(f"开始执行Agent任务: {agent_input.get('task_type', 'unknown')}")
            
            # 执行Agent编排
            result = await self.orchestrator.execute(agent_input, context)
            
            if result.success:
                logger.info("Agent任务执行成功")
            else:
                logger.warning(f"Agent任务执行失败: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Agent任务执行异常: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                data=None
            )
    
    def execute_agent_task_sync(
        self,
        agent_input: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """
        同步执行Agent任务（在Celery任务中使用）
        
        Args:
            agent_input: Agent输入数据
            context: 执行上下文
            
        Returns:
            Agent执行结果
        """
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 执行异步任务
            result = loop.run_until_complete(
                self.execute_agent_task(agent_input, context)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"同步Agent任务执行异常: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                data=None
            )
        finally:
            try:
                loop.close()
            except:
                pass
    
    async def execute_placeholder_analysis(
        self,
        placeholder_data: Dict[str, Any],
        data_source_id: str,
        task_id: int
    ) -> AgentResult:
        """
        执行占位符分析
        
        Args:
            placeholder_data: 占位符数据
            data_source_id: 数据源ID
            task_id: 任务ID
            
        Returns:
            分析结果
        """
        agent_input = {
            "placeholder_type": placeholder_data.get('type', '统计'),
            "description": placeholder_data.get('description', ''),
            "data_source_id": data_source_id,
            "name": placeholder_data.get('name', ''),
            "task_id": task_id,
            **placeholder_data
        }
        
        context = {
            "task_id": task_id,
            "processing_mode": "placeholder_analysis"
        }
        
        return await self.execute_agent_task(agent_input, context)
    
    async def execute_report_generation(
        self,
        template_content: str,
        placeholders: list,
        data_source_id: str,
        task_id: int,
        user_id: str
    ) -> AgentResult:
        """
        执行报告生成
        
        Args:
            template_content: 模板内容
            placeholders: 占位符列表
            data_source_id: 数据源ID
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            生成结果
        """
        agent_input = {
            "template_content": template_content,
            "placeholders": placeholders,
            "data_source_id": data_source_id,
            "task_id": task_id,
            "user_id": user_id,
            "task_type": "report_generation"
        }
        
        context = {
            "task_id": task_id,
            "user_id": user_id,
            "processing_mode": "report_generation"
        }
        
        return await self.execute_agent_task(agent_input, context)
