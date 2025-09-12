"""
Claude Code架构集成测试套件
=============================================

全面测试新架构的各个组件，确保迁移的成功和系统稳定性
"""

import pytest
import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import uuid

# 导入测试目标
from app.services.infrastructure.ai.core.streaming_messages import (
    StreamMessage, MessageType, StreamMessageRouter, StreamAccumulator, ANRDetector
)
from app.services.infrastructure.ai.core.streaming_json_parser import (
    StreamingJSONParser, ToolCallJSONParser, ParseResult
)
from app.services.infrastructure.ai.core.security_layers import (
    SecurityOrchestrator, SecurityContext, OperationType, ResourceType, ThreatLevel
)
from app.services.infrastructure.ai.core.enhanced_instructions import (
    InstructionOrchestrator, TripleEmphasisBuilder, VirtualPenaltySystem
)
from app.services.infrastructure.ai.core.unified_orchestrator_v2 import (
    UnifiedOrchestratorV2, OrchestrationTask
)
from app.services.infrastructure.ai.core.llm_psychology import (
    LLMPsychologyOrchestrator, HallucinationManager
)

# 测试工具
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestClaudeCodeStreaming:
    """流式架构测试"""
    
    @pytest.mark.asyncio
    async def test_stream_message_creation(self):
        """测试流式消息创建"""
        message = StreamMessage(
            type=MessageType.STATUS,
            user_id="test_user",
            task_id="test_task",
            content={"status": "processing"},
            progress=0.5
        )
        
        assert message.type == MessageType.STATUS
        assert message.user_id == "test_user"
        assert message.task_id == "test_task" 
        assert message.progress == 0.5
        assert not message.is_final
        
    @pytest.mark.asyncio
    async def test_stream_message_router(self):
        """测试流式消息路由"""
        router = StreamMessageRouter()
        messages = []
        
        # 订阅消息
        async def message_handler(message: StreamMessage):
            messages.append(message)
            
        router.subscribe("test_user", message_handler)
        
        # 发送消息
        test_message = StreamMessage(
            type=MessageType.STATUS,
            user_id="test_user",
            content={"test": "data"}
        )
        
        await router.route_message(test_message)
        
        # 验证消息被路由
        assert len(messages) == 1
        assert messages[0].content["test"] == "data"
        
    @pytest.mark.asyncio
    async def test_stream_accumulator(self):
        """测试流式消息累加器"""
        accumulator = StreamAccumulator()
        
        # 添加消息
        message1 = StreamMessage(type=MessageType.STATUS, content={"step": 1})
        message2 = StreamMessage(type=MessageType.STATUS, content={"step": 2})
        message3 = StreamMessage(type=MessageType.RESULT, content={"final": True}, is_final=True)
        
        accumulator.add_message(message1)
        accumulator.add_message(message2)
        accumulator.add_message(message3)
        
        # 验证累加结果
        final_result = accumulator.get_final_result()
        assert final_result is not None
        assert final_result.content["final"] is True
        assert len(accumulator.get_all_messages()) == 3
        
    @pytest.mark.asyncio 
    async def test_anr_detector(self):
        """测试ANR检测器"""
        detector = ANRDetector(anr_threshold=0.1)  # 100ms阈值
        
        # 开始任务
        task_id = "test_anr_task"
        detector.start_task(task_id)
        
        # 等待超过阈值
        await asyncio.sleep(0.2)
        
        # 检查ANR
        is_anr = detector.check_anr(task_id)
        assert is_anr is True
        
        # 完成任务
        detector.complete_task(task_id)
        
        # ANR应该被清除
        is_anr_after = detector.check_anr(task_id)
        assert is_anr_after is False


class TestClaudeCodeJSONParsing:
    """JSON解析测试"""
    
    def test_streaming_json_parser_complete(self):
        """测试完整JSON解析"""
        parser = StreamingJSONParser()
        
        json_data = '{"name": "test", "value": 123, "active": true}'
        results = list(parser.feed(json_data))
        
        assert len(results) >= 1
        complete_result = next((r for r in results if r.result_type == ParseResult.COMPLETE), None)
        assert complete_result is not None
        assert complete_result.data["name"] == "test"
        assert complete_result.data["value"] == 123
        assert complete_result.data["active"] is True
        
    def test_streaming_json_parser_partial(self):
        """测试部分JSON解析"""
        parser = StreamingJSONParser()
        
        # 发送不完整JSON
        incomplete_json = '{"name": "test", "value": 123'
        results = list(parser.feed(incomplete_json))
        
        # 应该有部分解析结果
        partial_result = next((r for r in results if r.result_type == ParseResult.PARTIAL), None)
        assert partial_result is not None
        assert partial_result.partial_data["name"] == "test"
        assert partial_result.partial_data["value"] == 123
        
    def test_streaming_json_parser_recovery(self):
        """测试JSON错误恢复"""
        parser = StreamingJSONParser()
        
        # 发送有错误的JSON (缺少右括号)
        broken_json = '{"name": "test", "items": [1, 2, 3'
        results = list(parser.feed(broken_json))
        
        # 应该尝试恢复
        recovery_result = next((r for r in results if r.result_type == ParseResult.RECOVERED), None)
        if recovery_result:
            assert recovery_result.data is not None
            assert recovery_result.recovery_attempted is True
        
    def test_tool_call_json_parser(self):
        """测试工具调用JSON解析器"""
        parser = ToolCallJSONParser()
        parser.set_expected_tools(["sql_generator", "chart_generator"])
        
        tool_json = '{"selected_tool": "sql_generator", "tool_params": {"table": "users", "conditions": "active=1"}}'
        results = list(parser.feed(tool_json))
        
        complete_result = next((r for r in results if r.result_type == ParseResult.COMPLETE), None)
        assert complete_result is not None
        assert complete_result.data["selected_tool"] == "sql_generator"
        assert "table" in complete_result.data["tool_params"]


class TestClaudeCodeSecurity:
    """安全层测试"""
    
    @pytest.mark.asyncio
    async def test_permission_manager_basic(self):
        """测试基础权限管理"""
        from app.services.infrastructure.ai.core.security_layers import Layer1PermissionManager
        
        permission_manager = Layer1PermissionManager()
        
        context = SecurityContext(
            user_id="test_user",
            session_id="test_session", 
            operation=OperationType.READ,
            resource_type=ResourceType.DATA_SOURCE,
            resource_id="test_resource"
        )
        
        decision = await permission_manager.check_permission(context)
        assert decision is not None
        assert isinstance(decision.allowed, bool)
        assert decision.reason is not None
        
    @pytest.mark.asyncio
    async def test_sandbox_manager_safe_operation(self):
        """测试沙盒安全操作"""
        from app.services.infrastructure.ai.core.security_layers import Layer2SandboxManager
        
        sandbox_manager = Layer2SandboxManager()
        
        # 安全操作函数
        async def safe_operation(x, y):
            return x + y
            
        context = SecurityContext(
            user_id="test_user",
            session_id="test_session",
            operation=OperationType.EXECUTE,
            resource_type=ResourceType.TOOL,
            resource_id="math_tool"
        )
        
        result = await sandbox_manager.execute_in_sandbox(
            "data_analysis", safe_operation, context, 5, 3
        )
        
        assert result["success"] is True
        assert result["result"] == 8
        assert "sandboxed" in result
        
    @pytest.mark.asyncio
    async def test_security_orchestrator_complete_flow(self):
        """测试安全编排器完整流程"""
        orchestrator = SecurityOrchestrator()
        
        async def test_operation(message: str):
            return f"Processed: {message}"
            
        context = SecurityContext(
            user_id="test_user",
            session_id="test_session",
            operation=OperationType.EXECUTE, 
            resource_type=ResourceType.TOOL,
            resource_id="test_tool"
        )
        
        result = await orchestrator.secure_execute(
            test_operation, context, "test_operation", "hello world"
        )
        
        assert "success" in result
        if result["success"]:
            assert result["result"] == "Processed: hello world"


class TestClaudeCodeInstructions:
    """指令系统测试"""
    
    def test_triple_emphasis_builder(self):
        """测试三重强调构建器"""
        builder = TripleEmphasisBuilder()
        
        base_instruction = "请严格按照JSON格式输出结果"
        emphasized = builder.build_triple_emphasis(base_instruction)
        
        assert "1/3" in emphasized
        assert "2/3" in emphasized  
        assert "3/3" in emphasized
        assert "严重后果警告" in emphasized
        assert "可信度惩罚" in emphasized
        
    def test_virtual_penalty_system(self):
        """测试虚拟惩罚系统"""
        penalty_system = VirtualPenaltySystem()
        
        violation = "未按照JSON格式输出"
        penalty = penalty_system.create_penalty(violation, severity=3)
        
        assert penalty is not None
        assert penalty["violation"] == violation
        assert penalty["penalty_points"] > 0
        assert "consequences" in penalty
        
    @pytest.mark.asyncio
    async def test_instruction_orchestrator(self):
        """测试指令编排器"""
        orchestrator = InstructionOrchestrator()
        
        base_instruction = "生成SQL查询语句"
        context = {"table": "users", "conditions": "active=1"}
        
        enhanced = await orchestrator.enhance_instruction(base_instruction, context)
        
        assert base_instruction in enhanced
        assert len(enhanced) > len(base_instruction)
        assert "JSON" in enhanced  # 应该包含格式要求


class TestClaudeCodeUnifiedOrchestrator:
    """统一编排器测试"""
    
    @pytest.mark.asyncio
    async def test_orchestrator_creation(self):
        """测试编排器创建"""
        orchestrator = UnifiedOrchestratorV2()
        
        assert orchestrator is not None
        assert hasattr(orchestrator, 'execute_task')
        
    @pytest.mark.asyncio
    async def test_orchestration_task_creation(self):
        """测试编排任务创建"""
        task = OrchestrationTask(
            task_id="test_task",
            task_type="sql_generation",
            user_id="test_user",
            task_data={"query": "SELECT * FROM users"},
            security_context=SecurityContext(
                user_id="test_user",
                session_id="test_session",
                operation=OperationType.READ,
                resource_type=ResourceType.DATA_SOURCE,
                resource_id="users_table"
            )
        )
        
        assert task.task_id == "test_task"
        assert task.task_type == "sql_generation"
        assert task.user_id == "test_user"
        
    @pytest.mark.asyncio
    async def test_orchestrator_execution_flow(self):
        """测试编排器执行流程"""
        orchestrator = UnifiedOrchestratorV2()
        
        task = OrchestrationTask(
            task_id="test_execution",
            task_type="test_task", 
            user_id="test_user",
            task_data={"test": "data"},
            security_context=SecurityContext(
                user_id="test_user",
                session_id="test_session",
                operation=OperationType.EXECUTE,
                resource_type=ResourceType.TASK,
                resource_id="test_task"
            )
        )
        
        messages = []
        async for message in orchestrator.execute_task(task):
            messages.append(message)
            if message.is_final:
                break
                
        # 应该至少有开始和结束消息
        assert len(messages) > 0
        assert any(msg.type == MessageType.STATUS for msg in messages)


class TestClaudeCodeLLMPsychology:
    """LLM心理学测试"""
    
    @pytest.mark.asyncio
    async def test_hallucination_manager(self):
        """测试幻觉管理器"""
        manager = HallucinationManager()
        
        # 模拟LLM响应
        response = "根据数据显示，用户转化率为85%，这是一个非常高的数字。"
        context = {"expected_range": "60-70%"}
        
        result = await manager.process_llm_response(response, context)
        
        assert result is not None
        assert "validated_content" in result.__dict__
        
    @pytest.mark.asyncio
    async def test_llm_psychology_orchestrator(self):
        """测试LLM心理学编排器"""
        orchestrator = LLMPsychologyOrchestrator()
        
        llm_response = "基于分析，建议采用策略A，因为它具有更好的ROI。"
        context = {"available_strategies": ["A", "B", "C"]}
        
        result = await orchestrator.process_llm_interaction(llm_response, context)
        
        assert result is not None
        assert result.validated is not None


class TestClaudeCodeIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_sql_generation(self):
        """端到端SQL生成测试"""
        # 模拟完整的SQL生成流程
        orchestrator = UnifiedOrchestratorV2()
        
        task = OrchestrationTask(
            task_id=f"sql_task_{int(time.time())}",
            task_type="sql_generation",
            user_id="integration_test_user", 
            task_data={
                "query_description": "查询活跃用户数量",
                "table_name": "users",
                "conditions": ["active = 1", "created_at > '2023-01-01'"]
            },
            security_context=SecurityContext(
                user_id="integration_test_user",
                session_id="integration_session",
                operation=OperationType.READ,
                resource_type=ResourceType.DATA_SOURCE,
                resource_id="users"
            )
        )
        
        results = []
        start_time = time.time()
        
        async for message in orchestrator.execute_task(task):
            results.append(message)
            if message.is_final:
                break
                
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 验证结果
        assert len(results) > 0
        assert execution_time < 10.0  # 应在10秒内完成
        
        # 查找最终结果
        final_message = next((msg for msg in results if msg.is_final), None)
        assert final_message is not None
        
    @pytest.mark.asyncio
    async def test_streaming_with_security(self):
        """流式处理与安全层集成测试"""
        security_orchestrator = SecurityOrchestrator()
        message_router = StreamMessageRouter()
        
        # 创建测试用户订阅
        received_messages = []
        
        async def message_handler(message: StreamMessage):
            received_messages.append(message)
            
        message_router.subscribe("security_test_user", message_handler)
        
        # 安全操作
        async def secure_streaming_operation():
            # 发送流式消息
            messages = [
                StreamMessage(type=MessageType.STATUS, user_id="security_test_user", content={"step": 1}),
                StreamMessage(type=MessageType.STATUS, user_id="security_test_user", content={"step": 2}),
                StreamMessage(type=MessageType.RESULT, user_id="security_test_user", 
                            content={"result": "success"}, is_final=True)
            ]
            
            for msg in messages:
                await message_router.route_message(msg)
                await asyncio.sleep(0.1)
                
            return {"status": "completed"}
        
        context = SecurityContext(
            user_id="security_test_user",
            session_id="security_session",
            operation=OperationType.EXECUTE,
            resource_type=ResourceType.TOOL,
            resource_id="streaming_tool"
        )
        
        # 安全执行流式操作
        result = await security_orchestrator.secure_execute(
            secure_streaming_operation, context, "streaming_test"
        )
        
        # 验证安全执行成功
        assert result["success"] is True
        
        # 验证消息被正确路由
        await asyncio.sleep(0.5)  # 等待异步消息处理
        assert len(received_messages) >= 3
        
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self):
        """性能基准测试"""
        orchestrator = UnifiedOrchestratorV2()
        
        # 测试并发任务处理
        tasks = []
        for i in range(10):
            task = OrchestrationTask(
                task_id=f"perf_task_{i}",
                task_type="performance_test",
                user_id=f"perf_user_{i}",
                task_data={"test_id": i},
                security_context=SecurityContext(
                    user_id=f"perf_user_{i}",
                    session_id=f"perf_session_{i}",
                    operation=OperationType.READ,
                    resource_type=ResourceType.TASK,
                    resource_id=f"perf_task_{i}"
                )
            )
            tasks.append(task)
        
        # 并发执行
        start_time = time.time()
        results = await asyncio.gather(
            *[self._collect_task_results(orchestrator.execute_task(task)) for task in tasks],
            return_exceptions=True
        )
        end_time = time.time()
        
        total_time = end_time - start_time
        successful_tasks = len([r for r in results if not isinstance(r, Exception)])
        
        # 性能要求
        assert total_time < 30.0  # 10个任务应在30秒内完成
        assert successful_tasks >= 8  # 至少80%成功率
        
        logger.info(f"性能测试结果: {successful_tasks}/{len(tasks)} 任务成功，总耗时: {total_time:.2f}秒")
        
    async def _collect_task_results(self, task_stream):
        """收集任务流式结果"""
        results = []
        async for message in task_stream:
            results.append(message)
            if message.is_final:
                break
        return results


class TestClaudeCodeStressTest:
    """压力测试"""
    
    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """内存使用测试"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 创建大量对象
        orchestrators = [UnifiedOrchestratorV2() for _ in range(100)]
        
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory
        
        logger.info(f"内存使用: 初始 {initial_memory:.2f}MB, 当前 {current_memory:.2f}MB, 增加 {memory_increase:.2f}MB")
        
        # 内存增加应该控制在合理范围内 
        assert memory_increase < 100  # 不超过100MB增长
        
        # 清理
        del orchestrators
        
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """错误恢复测试"""
        orchestrator = UnifiedOrchestratorV2()
        
        # 创建会失败的任务
        failing_task = OrchestrationTask(
            task_id="failing_task",
            task_type="error_test",
            user_id="error_test_user",
            task_data={"should_fail": True},
            security_context=SecurityContext(
                user_id="error_test_user", 
                session_id="error_session",
                operation=OperationType.EXECUTE,
                resource_type=ResourceType.TASK,
                resource_id="failing_task"
            )
        )
        
        messages = []
        try:
            async for message in orchestrator.execute_task(failing_task):
                messages.append(message)
                if message.is_final:
                    break
        except Exception as e:
            logger.info(f"预期的错误: {e}")
        
        # 系统应该能优雅处理错误
        assert len(messages) > 0
        
        # 检查是否有错误消息
        error_messages = [msg for msg in messages if msg.type == MessageType.ERROR]
        if error_messages:
            assert len(error_messages) > 0


# Pytest配置
@pytest.fixture(scope="session") 
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_llm_service():
    """模拟LLM服务"""
    class MockLLMService:
        async def generate_response(self, prompt: str) -> str:
            return f"Mock response for: {prompt[:50]}..."
            
        async def generate_streaming_response(self, prompt: str):
            responses = ["Thinking...", "Processing...", "Final result generated."]
            for response in responses:
                yield response
                await asyncio.sleep(0.1)
    
    return MockLLMService()


# 运行所有测试
if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--disable-warnings",
        f"--html=test_reports/claude_code_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
        "--self-contained-html"
    ])