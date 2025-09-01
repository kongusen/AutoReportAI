# Task任务中Agent调用架构设计

基于template中agent调用方式的分析和整体DDD架构优化，设计task任务中agent的调用方案。

## 🏗️ Agent在DDD架构中的重新定位

### 1. Domain层的Agent服务
```
app/services/domain/agents/
├── __init__.py
├── placeholder_analysis_agent.py      # 占位符分析智能代理
├── sql_generation_agent.py           # SQL生成智能代理  
├── business_rule_agent.py            # 业务规则推理代理
└── domain_knowledge_agent.py         # 领域知识代理
```

### 2. Application层的Agent服务
```
app/services/application/agents/
├── __init__.py
├── workflow_orchestration_agent.py   # 工作流编排代理
├── task_coordination_agent.py        # 任务协调代理
├── report_generation_agent.py        # 报告生成协调代理
└── context_aware_agent.py           # 上下文感知代理
```

### 3. Infrastructure层的Agent服务
```
app/services/infrastructure/agents/
├── __init__.py
├── llm_integration_agent.py         # LLM集成代理
├── external_api_agent.py            # 外部API调用代理
├── data_transformation_agent.py     # 数据转换代理
└── tool_execution_agent.py          # 工具执行代理
```

## 🚀 Task任务中的Agent调用模式

### 基于Template调用方式的设计原则

从template中的agent调用方式学到的模式：
```python
# 1. 服务注入模式
from ..placeholder import get_intelligent_placeholder_service
self._placeholder_service = await get_intelligent_placeholder_service()

# 2. 工厂创建模式  
from app.services.application.factories import create_multi_database_agent
self._multi_db_agent = create_multi_database_agent(self.db, self.user_id)

# 3. 异步调用模式
analysis_result = await self._placeholder_service.analyze_template_for_sql_generation(...)

# 4. 上下文传递模式
agent_result = await self.multi_db_agent.analyze_placeholder_requirements(agent_input, execution_context)
```

### Task任务中的Agent调用实现

#### 1. Application层编排任务中的Agent调用

```python
# app/services/application/tasks/orchestration_tasks.py

@celery_app.task(name='application.orchestration.report_generation', bind=True)
def orchestrate_report_generation(self, template_id: str, data_source_ids: List[str], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    编排报告生成的完整工作流
    
    在Application层编排任务中，agent调用应该：
    1. 调用Application层的编排代理
    2. 通过代理协调其他层的服务
    3. 不直接调用Domain/Infrastructure层的agent
    """
    
    async def _execute_with_agent():
        # 1. 获取Application层的工作流编排代理
        from ...application.agents import get_workflow_orchestration_agent
        workflow_agent = await get_workflow_orchestration_agent()
        
        # 2. 通过代理编排整个工作流
        orchestration_result = await workflow_agent.orchestrate_report_generation(
            template_id=template_id,
            data_source_ids=data_source_ids,
            execution_context={
                'task_id': self.request.id,
                'config': config,
                'started_at': datetime.now().isoformat()
            }
        )
        
        # 3. 代理内部会协调Domain层和Infrastructure层的服务
        return orchestration_result
    
    # 在Celery任务中运行异步代码
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_execute_with_agent())


@celery_app.task(name='application.orchestration.data_processing', bind=True) 
def orchestrate_data_processing(self, pipeline_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    编排数据处理工作流
    """
    
    async def _execute_with_agent():
        # 1. 获取Application层的任务协调代理
        from ...application.agents import get_task_coordination_agent
        task_agent = await get_task_coordination_agent()
        
        # 2. 通过代理协调数据处理流程
        coordination_result = await task_agent.coordinate_data_processing(
            pipeline_config=pipeline_config,
            execution_context={
                'task_id': self.request.id,
                'workflow_type': 'data_processing',
                'started_at': datetime.now().isoformat()
            }
        )
        
        return coordination_result
    
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_execute_with_agent())


# 新增：Context-aware任务编排
@celery_app.task(name='application.orchestration.context_aware_task', bind=True)
def orchestrate_context_aware_task(self, task_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    编排上下文感知任务
    
    整合ContextAwareApplicationService的功能
    """
    
    async def _execute_with_agent():
        # 1. 获取Application层的上下文感知代理
        from ...application.agents import get_context_aware_agent
        context_agent = await get_context_aware_agent()
        
        # 2. 通过代理处理上下文感知任务
        task_result = await context_agent.execute_contextual_task(
            task_request=task_request,
            execution_context={
                'task_id': self.request.id,
                'orchestrator': 'context_aware_orchestration',
                'started_at': datetime.now().isoformat()
            }
        )
        
        return task_result
    
    import asyncio
    try:
        loop = asyncio.get_event_loop() 
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_execute_with_agent())
```

#### 2. Application层Agent服务实现

```python
# app/services/application/agents/workflow_orchestration_agent.py

"""
工作流编排代理

Application层的代理，负责协调Domain层和Infrastructure层的服务
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WorkflowOrchestrationAgent:
    """
    工作流编排代理
    
    职责：
    1. 协调Domain层的业务逻辑服务
    2. 协调Infrastructure层的技术服务
    3. 管理跨层的工作流状态
    4. 处理工作流级别的错误和重试
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        # 延迟初始化各层的服务
        self._domain_agents = {}
        self._infrastructure_agents = {}
    
    async def orchestrate_report_generation(
        self,
        template_id: str,
        data_source_ids: List[str], 
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        编排报告生成工作流
        
        协调各层服务完成报告生成
        """
        try:
            self.logger.info(f"开始编排报告生成工作流: template={template_id}")
            
            workflow_context = {
                'workflow_id': execution_context.get('task_id'),
                'template_id': template_id,
                'data_source_ids': data_source_ids,
                'execution_context': execution_context,
                'started_at': datetime.now().isoformat()
            }
            
            # 1. 调用Domain层的模板分析agent
            template_analysis_result = await self._analyze_template_with_domain_agent(
                template_id, execution_context
            )
            
            # 2. 调用Domain层的占位符分析agent
            placeholder_analysis_result = await self._analyze_placeholders_with_domain_agent(
                template_id, data_source_ids, execution_context
            )
            
            # 3. 调用Infrastructure层的数据获取agent
            data_extraction_result = await self._extract_data_with_infrastructure_agent(
                data_source_ids, placeholder_analysis_result, execution_context
            )
            
            # 4. 调用Domain层的报告生成agent
            report_generation_result = await self._generate_report_with_domain_agent(
                template_analysis_result, data_extraction_result, execution_context
            )
            
            # 5. 调用Infrastructure层的结果存储agent
            storage_result = await self._store_results_with_infrastructure_agent(
                report_generation_result, execution_context
            )
            
            return {
                'success': True,
                'workflow_context': workflow_context,
                'results': {
                    'template_analysis': template_analysis_result,
                    'placeholder_analysis': placeholder_analysis_result, 
                    'data_extraction': data_extraction_result,
                    'report_generation': report_generation_result,
                    'storage': storage_result
                },
                'completed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"报告生成工作流编排失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'workflow_context': workflow_context,
                'failed_at': datetime.now().isoformat()
            }
    
    async def _analyze_template_with_domain_agent(
        self, 
        template_id: str, 
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用Domain层的模板分析agent"""
        try:
            # 获取Domain层的模板分析agent
            template_agent = await self._get_domain_agent('template_analysis')
            
            result = await template_agent.analyze_template_structure(
                template_id=template_id,
                analysis_context=execution_context
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Domain层模板分析失败: {e}")
            raise
    
    async def _analyze_placeholders_with_domain_agent(
        self, 
        template_id: str, 
        data_source_ids: List[str],
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用Domain层的占位符分析agent"""
        try:
            # 获取Domain层的占位符分析agent
            placeholder_agent = await self._get_domain_agent('placeholder_analysis')
            
            result = await placeholder_agent.analyze_template_placeholders(
                template_id=template_id,
                data_source_ids=data_source_ids,
                analysis_context=execution_context
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Domain层占位符分析失败: {e}")
            raise
    
    async def _extract_data_with_infrastructure_agent(
        self,
        data_source_ids: List[str],
        placeholder_analysis: Dict[str, Any],
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用Infrastructure层的数据提取agent"""
        try:
            # 获取Infrastructure层的数据提取agent
            data_agent = await self._get_infrastructure_agent('data_extraction')
            
            result = await data_agent.extract_data_for_placeholders(
                data_source_ids=data_source_ids,
                placeholder_specs=placeholder_analysis.get('placeholder_specs', []),
                extraction_context=execution_context
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Infrastructure层数据提取失败: {e}")
            raise
    
    async def _generate_report_with_domain_agent(
        self,
        template_analysis: Dict[str, Any],
        data_extraction: Dict[str, Any], 
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用Domain层的报告生成agent"""
        try:
            # 获取Domain层的报告生成agent
            report_agent = await self._get_domain_agent('report_generation')
            
            result = await report_agent.generate_report_content(
                template_structure=template_analysis,
                extracted_data=data_extraction,
                generation_context=execution_context
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Domain层报告生成失败: {e}")
            raise
    
    async def _store_results_with_infrastructure_agent(
        self,
        report_content: Dict[str, Any],
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用Infrastructure层的结果存储agent"""
        try:
            # 获取Infrastructure层的存储agent
            storage_agent = await self._get_infrastructure_agent('result_storage')
            
            result = await storage_agent.store_report_results(
                report_content=report_content,
                storage_context=execution_context
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Infrastructure层结果存储失败: {e}")
            raise
    
    async def _get_domain_agent(self, agent_type: str):
        """获取Domain层的agent实例"""
        if agent_type not in self._domain_agents:
            if agent_type == 'template_analysis':
                from ...domain.agents import get_template_analysis_agent
                self._domain_agents[agent_type] = await get_template_analysis_agent()
            elif agent_type == 'placeholder_analysis':
                from ...domain.agents import get_placeholder_analysis_agent  
                self._domain_agents[agent_type] = await get_placeholder_analysis_agent()
            elif agent_type == 'report_generation':
                from ...domain.agents import get_report_generation_agent
                self._domain_agents[agent_type] = await get_report_generation_agent()
            else:
                raise ValueError(f"Unknown domain agent type: {agent_type}")
        
        return self._domain_agents[agent_type]
    
    async def _get_infrastructure_agent(self, agent_type: str):
        """获取Infrastructure层的agent实例"""
        if agent_type not in self._infrastructure_agents:
            if agent_type == 'data_extraction':
                from ...infrastructure.agents import get_data_extraction_agent
                self._infrastructure_agents[agent_type] = await get_data_extraction_agent()
            elif agent_type == 'result_storage':
                from ...infrastructure.agents import get_result_storage_agent
                self._infrastructure_agents[agent_type] = await get_result_storage_agent()
            else:
                raise ValueError(f"Unknown infrastructure agent type: {agent_type}")
        
        return self._infrastructure_agents[agent_type]


# 全局服务实例
_global_workflow_agent: Optional[WorkflowOrchestrationAgent] = None


async def get_workflow_orchestration_agent() -> WorkflowOrchestrationAgent:
    """获取全局工作流编排代理实例"""
    global _global_workflow_agent
    if _global_workflow_agent is None:
        _global_workflow_agent = WorkflowOrchestrationAgent()
    return _global_workflow_agent
```

#### 3. Agent服务工厂

```python
# app/services/application/agents/__init__.py

"""
Application层Agent服务

提供统一的Agent服务获取接口
"""

from .workflow_orchestration_agent import get_workflow_orchestration_agent
from .task_coordination_agent import get_task_coordination_agent  
from .context_aware_agent import get_context_aware_agent

__all__ = [
    'get_workflow_orchestration_agent',
    'get_task_coordination_agent', 
    'get_context_aware_agent'
]
```

## 🎯 Agent调用的DDD原则

### 1. 分层调用原则
```python
# ✅ 正确：Application层调用Application层agent
from ...application.agents import get_workflow_orchestration_agent

# ✅ 正确：Application层agent内部协调其他层的服务
# 在WorkflowOrchestrationAgent内部
from ...domain.agents import get_placeholder_analysis_agent
from ...infrastructure.agents import get_data_extraction_agent

# ❌ 错误：Application层直接调用Domain层agent
# 在Application层任务中直接调用
from ...domain.agents import get_placeholder_analysis_agent  # 违反分层原则
```

### 2. 依赖方向原则
```python
# ✅ 正确：上层依赖下层
Application层 → Domain层
Application层 → Infrastructure层

# ❌ 错误：下层依赖上层
Domain层 → Application层  # 违反依赖倒置原则
```

### 3. 上下文传递原则
```python
# ✅ 正确：完整的上下文传递
execution_context = {
    'task_id': self.request.id,
    'workflow_type': 'report_generation',
    'started_at': datetime.now().isoformat(),
    'user_id': config.get('user_id'),
    'request_metadata': config.get('metadata', {})
}

agent_result = await agent.process_request(request_data, execution_context)
```

### 4. 错误处理原则
```python
# ✅ 正确：层级化错误处理
try:
    result = await workflow_agent.orchestrate_report_generation(...)
except DomainException as e:
    # Domain层的业务错误
    return {'success': False, 'error_type': 'business_error', 'error': str(e)}
except InfrastructureException as e:
    # Infrastructure层的技术错误
    return {'success': False, 'error_type': 'infrastructure_error', 'error': str(e)}
except Exception as e:
    # 应用层的协调错误
    return {'success': False, 'error_type': 'orchestration_error', 'error': str(e)}
```

## 🔧 实施步骤

1. **重构现有Agents目录结构**
   - 将agents分配到对应的DDD层次
   - 创建层级化的agent服务接口

2. **更新Task任务调用方式**
   - Application层任务只调用Application层agent
   - 通过agent协调其他层的服务

3. **建立Agent服务注册机制**
   - 创建统一的agent工厂
   - 实现依赖注入和生命周期管理

4. **完善错误处理和监控**
   - 建立层级化的错误处理机制
   - 添加agent调用的监控和日志

这个设计确保了：
- ✅ 符合DDD分层原则
- ✅ 保持清晰的职责分离
- ✅ 实现松耦合的架构
- ✅ 易于测试和维护
- ✅ 支持未来的扩展需求