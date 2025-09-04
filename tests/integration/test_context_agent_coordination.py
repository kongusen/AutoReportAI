"""
Context控制和Agent协调集成测试

专门测试Context在不同层次间的传递、状态管理和Agent间的协调机制
验证我们分析的架构中Context的完整生命周期
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List
from dataclasses import asdict

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.services.application.orchestration.workflow_engine import (
    WorkflowContext, WorkflowStatus, StepDefinition, StepType
)
from app.services.infrastructure.ai.agents.task_context import (
    AITaskContext, TaskComplexity, ExecutionStep, ExecutionStepType
)
from app.services.application.services.context_aware_service import (
    ContextualTaskRequest, ContextAwareTaskType, TaskPriority, ContextAwareApplicationService
)


@pytest.mark.integration
@pytest.mark.agent
@pytest.mark.asyncio
class TestContextAgentCoordination:
    """Context控制和Agent协调测试"""
    
    async def test_workflow_context_creation_and_management(self):
        """测试工作流上下文的创建和管理"""
        
        # 创建工作流上下文
        workflow_context = WorkflowContext(
            workflow_id="wf-context-test-001",
            inputs={
                "user_id": "test-user-001",
                "template_id": "template-001",
                "data_source_id": "datasource-001"
            },
            metadata={
                "created_by": "system",
                "priority": "high",
                "estimated_duration": 300
            }
        )
        
        # 验证初始状态
        assert workflow_context.workflow_id == "wf-context-test-001"
        assert workflow_context.variables == {}
        assert len(workflow_context.inputs) == 3
        assert workflow_context.metadata["priority"] == "high"
        
        # 测试变量设置和获取
        workflow_context.set_variable("current_step", "template_analysis")
        workflow_context.set_variable("progress", 0.25)
        
        assert workflow_context.get_variable("current_step") == "template_analysis"
        assert workflow_context.get_variable("progress") == 0.25
        assert workflow_context.get_variable("nonexistent", "default") == "default"
        
        # 测试输出合并
        step_outputs = {
            "placeholders_found": 5,
            "complexity_score": 0.7,
            "recommendations": ["优化建议1", "优化建议2"]
        }
        workflow_context.merge_outputs(step_outputs)
        
        assert workflow_context.outputs["placeholders_found"] == 5
        assert len(workflow_context.outputs["recommendations"]) == 2

    async def test_ai_task_context_lifecycle(self):
        """测试AI任务上下文的生命周期管理"""
        
        # 创建AI任务上下文
        task_context = AITaskContext(
            task_id="ai-task-001",
            placeholder_text="{{monthly_sales_growth}}",
            statistical_type="percentage_change",
            description="计算月度销售增长率",
            complexity=TaskComplexity.MEDIUM,
            user_id="test-user-002"
        )
        
        # 验证初始状态
        assert task_context.current_step_index == 0
        assert task_context.execution_results == {}
        assert task_context.execution_started_at is None
        assert task_context.execution_completed_at is None
        
        # 模拟执行开始
        task_context.execution_started_at = datetime.utcnow()
        
        # 模拟执行步骤
        execution_steps = [
            ExecutionStep(
                step_id="step_001",
                step_type=ExecutionStepType.PARSE,
                description="解析占位符语法",
                estimated_time=0.5
            ),
            ExecutionStep(
                step_id="step_002", 
                step_type=ExecutionStepType.SQL_GENERATION,
                description="生成SQL查询",
                estimated_time=1.0
            ),
            ExecutionStep(
                step_id="step_003",
                step_type=ExecutionStepType.CALCULATION,
                description="计算增长率",
                estimated_time=0.3
            )
        ]
        
        task_context.execution_steps = execution_steps
        
        # 模拟步骤执行和状态更新
        for i, step in enumerate(execution_steps):
            task_context.current_step_index = i
            task_context.execution_results[step.step_id] = {
                "status": "completed",
                "result": f"步骤{i+1}执行完成",
                "execution_time": step.estimated_time,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # 模拟执行完成
        task_context.execution_completed_at = datetime.utcnow()
        task_context.current_step_index = len(execution_steps)
        
        # 验证最终状态
        assert len(task_context.execution_results) == 3
        assert task_context.current_step_index == 3
        assert task_context.execution_completed_at is not None
        
        # 计算执行时长
        execution_duration = (task_context.execution_completed_at - 
                            task_context.execution_started_at).total_seconds()
        assert execution_duration >= 0

    async def test_context_propagation_across_agents(self):
        """测试Context在不同Agent间的传播"""
        
        # 模拟原始请求Context
        original_context = {
            "request_id": "req-001", 
            "user_id": "user-001",
            "session_id": "session-001",
            "timestamp": datetime.utcnow().isoformat(),
            "user_preferences": {
                "language": "zh-CN",
                "timezone": "Asia/Shanghai",
                "quality_level": "high"
            },
            "business_context": {
                "department": "sales",
                "role": "analyst",
                "access_level": "standard"
            }
        }
        
        # 第一层：API适配器层Context增强
        api_context = original_context.copy()
        api_context.update({
            "api_version": "v1",
            "endpoint": "/templates/analyze", 
            "method": "POST",
            "client_ip": "192.168.1.100"
        })
        
        # 第二层：工作流编排层Context扩展
        workflow_context = api_context.copy()
        workflow_context.update({
            "workflow_id": "wf-template-analysis-001",
            "workflow_type": "template_processing",
            "expected_duration": 120,
            "resource_allocation": {
                "cpu_priority": "medium",
                "memory_limit": "512MB"
            }
        })
        
        # 第三层：上下文感知层Context丰富
        context_aware_context = workflow_context.copy()
        context_aware_context.update({
            "domain_context": {
                "business_domain": "financial_analysis",
                "technical_complexity": "medium",
                "data_sensitivity": "internal"
            },
            "analysis_context": {
                "requires_sql": True,
                "requires_visualization": True,
                "requires_business_logic": True
            }
        })
        
        # 第四层：AI执行引擎Context特化
        ai_execution_context = context_aware_context.copy()
        ai_execution_context.update({
            "execution_mode": "react_agent",
            "model_requirements": {
                "task_type": "reasoning",
                "complexity": "medium", 
                "quality": "high"
            },
            "tool_requirements": ["chart_generation", "sql_generation"]
        })
        
        # 第五层：React Agent个人化Context
        react_agent_context = ai_execution_context.copy()
        react_agent_context.update({
            "agent_id": "react-agent-001",
            "max_iterations": 10,
            "memory_limit": 4000,
            "tools_available": ["generate_chart", "execute_sql", "analyze_data"],
            "model_config": {
                "temperature": 0.7,
                "max_tokens": 2000,
                "model_type": "think"
            }
        })
        
        # 验证Context在各层的完整性和增强
        contexts = [
            ("original", original_context),
            ("api", api_context), 
            ("workflow", workflow_context),
            ("context_aware", context_aware_context),
            ("ai_execution", ai_execution_context),
            ("react_agent", react_agent_context)
        ]
        
        # 验证每一层都包含前一层的信息
        for i in range(1, len(contexts)):
            current_name, current_context = contexts[i]
            previous_name, previous_context = contexts[i-1]
            
            # 检查关键信息是否被保留
            assert current_context["request_id"] == original_context["request_id"]
            assert current_context["user_id"] == original_context["user_id"]
            
            # 检查每层是否有新增信息
            new_keys = set(current_context.keys()) - set(previous_context.keys())
            assert len(new_keys) > 0, f"{current_name}层没有添加新的Context信息"
        
        # 验证最终Context的完整性
        final_context = react_agent_context
        required_keys = [
            "request_id", "user_id", "workflow_id", "agent_id", 
            "model_requirements", "tool_requirements", "domain_context"
        ]
        
        for key in required_keys:
            assert key in final_context, f"最终Context缺少必要字段: {key}"

    async def test_context_state_synchronization(self):
        """测试Context状态同步机制"""
        
        # 创建共享状态管理器模拟
        class SharedStateManager:
            def __init__(self):
                self.states = {}
                self.subscribers = {}
            
            def set_state(self, context_id: str, key: str, value: Any):
                if context_id not in self.states:
                    self.states[context_id] = {}
                self.states[context_id][key] = value
                self._notify_subscribers(context_id, key, value)
            
            def get_state(self, context_id: str, key: str = None):
                if context_id not in self.states:
                    return None
                if key is None:
                    return self.states[context_id]
                return self.states[context_id].get(key)
            
            def subscribe(self, context_id: str, callback):
                if context_id not in self.subscribers:
                    self.subscribers[context_id] = []
                self.subscribers[context_id].append(callback)
            
            def _notify_subscribers(self, context_id: str, key: str, value: Any):
                if context_id in self.subscribers:
                    for callback in self.subscribers[context_id]:
                        callback(key, value)
        
        # 创建状态管理器
        state_manager = SharedStateManager()
        context_id = "ctx-sync-test-001"
        
        # 模拟多个Agent订阅状态变化
        workflow_agent_updates = []
        react_agent_updates = []
        execution_engine_updates = []
        
        state_manager.subscribe(context_id, 
            lambda k, v: workflow_agent_updates.append((k, v)))
        state_manager.subscribe(context_id,
            lambda k, v: react_agent_updates.append((k, v)))
        state_manager.subscribe(context_id,
            lambda k, v: execution_engine_updates.append((k, v)))
        
        # 模拟状态更新序列
        updates_sequence = [
            ("workflow_status", "started"),
            ("current_step", "template_parsing"),
            ("progress", 0.1),
            ("placeholders_found", 5),
            ("current_step", "sql_generation"),
            ("progress", 0.4),
            ("sql_generated", True),
            ("current_step", "data_query"),
            ("progress", 0.7),
            ("data_retrieved", True),
            ("current_step", "analysis"), 
            ("progress", 0.9),
            ("analysis_complete", True),
            ("workflow_status", "completed"),
            ("progress", 1.0)
        ]
        
        # 执行状态更新
        for key, value in updates_sequence:
            state_manager.set_state(context_id, key, value)
        
        # 验证所有Agent都收到了状态更新
        assert len(workflow_agent_updates) == len(updates_sequence)
        assert len(react_agent_updates) == len(updates_sequence) 
        assert len(execution_engine_updates) == len(updates_sequence)
        
        # 验证最终状态
        final_state = state_manager.get_state(context_id)
        assert final_state["workflow_status"] == "completed"
        assert final_state["progress"] == 1.0
        assert final_state["analysis_complete"] == True

    async def test_cross_agent_data_sharing(self):
        """测试跨Agent的数据共享机制"""
        
        # 创建数据共享总线模拟
        class DataSharingBus:
            def __init__(self):
                self.data_store = {}
                self.access_log = []
            
            async def publish_data(self, source_agent: str, data_type: str, data: Any):
                key = f"{source_agent}:{data_type}"
                self.data_store[key] = {
                    "data": data,
                    "timestamp": datetime.utcnow(),
                    "source": source_agent
                }
                self.access_log.append(("PUBLISH", source_agent, data_type))
            
            async def consume_data(self, consumer_agent: str, source_agent: str, data_type: str):
                key = f"{source_agent}:{data_type}"
                if key in self.data_store:
                    self.access_log.append(("CONSUME", consumer_agent, f"{source_agent}:{data_type}"))
                    return self.data_store[key]["data"]
                return None
            
            def get_access_log(self):
                return self.access_log
        
        # 创建数据共享总线
        data_bus = DataSharingBus()
        
        # 模拟Agent间的数据共享流程
        
        # 1. WorkflowOrchestrationAgent发布初始配置
        await data_bus.publish_data(
            "WorkflowOrchestrationAgent",
            "workflow_config",
            {
                "template_id": "template-001",
                "data_source_id": "datasource-001",
                "user_preferences": {"quality": "high", "speed": "medium"}
            }
        )
        
        # 2. ContextAwareService发布上下文分析结果
        await data_bus.publish_data(
            "ContextAwareService",
            "context_analysis",
            {
                "business_domain": "sales",
                "complexity_level": "medium",
                "required_capabilities": ["sql_generation", "chart_creation", "analysis"]
            }
        )
        
        # 3. AIExecutionEngine发布执行计划
        await data_bus.publish_data(
            "AIExecutionEngine",
            "execution_plan",
            {
                "steps": ["parse", "generate_sql", "query_data", "analyze", "visualize"],
                "estimated_time": 180,
                "resource_requirements": {"memory": "256MB", "cpu": "medium"}
            }
        )
        
        # 4. ReactAgent消费其他Agent的数据
        workflow_config = await data_bus.consume_data(
            "ReactAgent", "WorkflowOrchestrationAgent", "workflow_config"
        )
        context_analysis = await data_bus.consume_data(
            "ReactAgent", "ContextAwareService", "context_analysis"
        )
        execution_plan = await data_bus.consume_data(
            "ReactAgent", "AIExecutionEngine", "execution_plan"
        )
        
        # 5. ReactAgent基于消费的数据生成执行结果
        react_agent_result = {
            "template_processed": workflow_config["template_id"],
            "context_applied": context_analysis["business_domain"],
            "steps_executed": execution_plan["steps"],
            "execution_time": 175,
            "results": {
                "sql_queries": 3,
                "charts_generated": 2,
                "insights_found": 5
            }
        }
        
        await data_bus.publish_data(
            "ReactAgent",
            "execution_results", 
            react_agent_result
        )
        
        # 6. 验证数据共享流程
        access_log = data_bus.get_access_log()
        
        # 验证发布操作
        publish_ops = [op for op in access_log if op[0] == "PUBLISH"]
        assert len(publish_ops) == 4
        
        # 验证消费操作  
        consume_ops = [op for op in access_log if op[0] == "CONSUME"]
        assert len(consume_ops) == 3
        
        # 验证ReactAgent消费了所需的数据
        react_agent_consumes = [op for op in consume_ops if op[1] == "ReactAgent"]
        assert len(react_agent_consumes) == 3
        
        # 验证数据完整性
        assert workflow_config["template_id"] == "template-001"
        assert context_analysis["business_domain"] == "sales"
        assert len(execution_plan["steps"]) == 5

    async def test_error_context_propagation(self):
        """测试错误Context的传播和处理"""
        
        # 创建错误上下文管理器
        class ErrorContextManager:
            def __init__(self):
                self.error_history = []
                self.recovery_attempts = []
            
            def record_error(self, agent: str, error_type: str, context: Dict, recovery_action: str = None):
                error_record = {
                    "timestamp": datetime.utcnow(),
                    "agent": agent,
                    "error_type": error_type,
                    "context": context.copy(),
                    "recovery_action": recovery_action
                }
                self.error_history.append(error_record)
                
                if recovery_action:
                    self.recovery_attempts.append({
                        "timestamp": datetime.utcnow(),
                        "agent": agent,
                        "action": recovery_action,
                        "original_context": context.copy()
                    })
            
            def get_error_context_for_agent(self, agent: str):
                return [err for err in self.error_history if err["agent"] == agent]
            
            def get_recovery_suggestions(self, current_context: Dict):
                # 基于历史错误和当前上下文提供恢复建议
                suggestions = []
                for error in self.error_history:
                    if error["error_type"] == "model_timeout" and current_context.get("model_type") == "think":
                        suggestions.append("switch_to_default_model")
                    elif error["error_type"] == "tool_failure" and "chart_generation" in current_context.get("required_tools", []):
                        suggestions.append("use_fallback_visualization")
                return suggestions
        
        # 创建错误管理器
        error_manager = ErrorContextManager()
        
        # 模拟错误传播场景
        base_context = {
            "request_id": "req-error-test-001",
            "user_id": "user-001", 
            "template_id": "template-001",
            "workflow_id": "wf-001"
        }
        
        # 1. React Agent遇到模型超时错误
        react_agent_context = base_context.copy()
        react_agent_context.update({
            "agent": "ReactAgent",
            "model_type": "think",
            "timeout_duration": 30,
            "retry_count": 2
        })
        
        error_manager.record_error(
            "ReactAgent",
            "model_timeout",
            react_agent_context,
            "switch_to_default_model"
        )
        
        # 2. 模型执行器处理降级
        model_executor_context = react_agent_context.copy()
        model_executor_context.update({
            "fallback_model": "default",
            "original_model": "think",
            "degraded_performance": True
        })
        
        # 3. 工作流编排器记录异常
        workflow_context = model_executor_context.copy() 
        workflow_context.update({
            "workflow_status": "degraded",
            "performance_impact": "medium",
            "user_notification_required": True
        })
        
        error_manager.record_error(
            "WorkflowOrchestrationAgent",
            "performance_degradation",
            workflow_context,
            "notify_user_and_continue"
        )
        
        # 4. 验证错误上下文传播
        react_agent_errors = error_manager.get_error_context_for_agent("ReactAgent")
        workflow_errors = error_manager.get_error_context_for_agent("WorkflowOrchestrationAgent")
        
        assert len(react_agent_errors) == 1
        assert len(workflow_errors) == 1
        assert react_agent_errors[0]["recovery_action"] == "switch_to_default_model"
        assert workflow_errors[0]["context"]["degraded_performance"] == True
        
        # 5. 测试恢复建议生成
        current_error_context = {
            "model_type": "think",
            "required_tools": ["chart_generation", "data_analysis"]
        }
        
        suggestions = error_manager.get_recovery_suggestions(current_error_context)
        assert "switch_to_default_model" in suggestions

    @pytest.mark.slow
    async def test_context_performance_under_load(self):
        """测试Context机制在负载下的性能"""
        
        # 模拟高并发Context处理
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        class ContextPerformanceTracker:
            def __init__(self):
                self.processing_times = []
                self.context_sizes = []
                self.memory_usage = []
            
            async def process_context(self, context_id: str, context_data: Dict):
                start_time = datetime.utcnow()
                
                # 模拟Context处理操作
                await asyncio.sleep(0.01)  # 模拟处理延迟
                
                # 模拟Context增强
                enhanced_context = context_data.copy()
                enhanced_context.update({
                    "processed_at": start_time.isoformat(),
                    "processing_agent": "TestAgent",
                    "enhancement_applied": True,
                    "context_size": len(str(context_data))
                })
                
                end_time = datetime.utcnow()
                processing_duration = (end_time - start_time).total_seconds()
                
                # 记录性能指标
                self.processing_times.append(processing_duration)
                self.context_sizes.append(len(str(enhanced_context)))
                
                return enhanced_context
        
        # 创建性能跟踪器
        performance_tracker = ContextPerformanceTracker()
        
        # 生成测试Context数据
        test_contexts = []
        for i in range(100):
            context = {
                "context_id": f"ctx-perf-{i:03d}",
                "user_id": f"user-{i % 10}",
                "request_data": {
                    "template_id": f"template-{i % 5}",
                    "params": [f"param-{j}" for j in range(10)],
                    "metadata": {"priority": "normal", "complexity": "medium"}
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            test_contexts.append(context)
        
        # 并发处理Context
        tasks = []
        for i, context in enumerate(test_contexts):
            task = performance_tracker.process_context(f"ctx-{i}", context)
            tasks.append(task)
        
        # 执行所有任务
        start_time = datetime.utcnow()
        results = await asyncio.gather(*tasks)
        end_time = datetime.utcnow()
        
        total_duration = (end_time - start_time).total_seconds()
        
        # 验证性能指标
        assert len(results) == 100
        assert len(performance_tracker.processing_times) == 100
        
        # 计算性能统计
        avg_processing_time = sum(performance_tracker.processing_times) / len(performance_tracker.processing_times)
        max_processing_time = max(performance_tracker.processing_times)
        min_processing_time = min(performance_tracker.processing_times)
        
        # 性能断言
        assert avg_processing_time < 0.1  # 平均处理时间应小于100ms
        assert max_processing_time < 0.2   # 最大处理时间应小于200ms
        assert total_duration < 10         # 总处理时间应小于10秒
        
        # 验证Context完整性
        for result in results:
            assert "processed_at" in result
            assert "processing_agent" in result
            assert result["enhancement_applied"] == True


if __name__ == "__main__":
    # 运行测试
    asyncio.run(pytest.main([__file__, "-v", "-s", "--tb=short"]))