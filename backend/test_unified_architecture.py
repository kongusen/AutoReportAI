"""
统一架构测试 - 验证重构后的AI核心系统
基于Claude Code理念的重构效果验证
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any

# 导入重构后的核心组件
from app.services.infrastructure.ai.core import (
    # 新的统一架构
    tt, get_unified_controller, get_auto_report_ai,
    
    # 安全系统
    get_security_checker, SecurityLevel,
    
    # API消息系统
    APIMessage, MessageConverter,
    
    # 工具和上下文
    ToolContext, AgentMessage,
    
    # 兼容性层
    execute_task_unified, get_compatibility_layer,
    
    # 旧系统（用于对比）
    AgentController, AgentTask, TaskType
)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArchitectureTestSuite:
    """
    架构重构测试套件
    
    测试内容：
    1. 新统一架构的功能完整性
    2. 安全检查机制的有效性
    3. 兼容性层的平滑迁移
    4. 性能和可靠性对比
    """
    
    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
        
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("🧪 开始架构重构验证测试")
        
        tests = [
            ("基础消息系统测试", self.test_message_system),
            ("安全检查系统测试", self.test_security_system),
            ("统一控制器测试", self.test_unified_controller),
            ("兼容性层测试", self.test_compatibility_layer),
            ("性能对比测试", self.test_performance_comparison),
            ("端到端集成测试", self.test_end_to_end_integration)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"🔍 执行测试: {test_name}")
            try:
                start_time = datetime.now()
                result = await test_func()
                duration = (datetime.now() - start_time).total_seconds()
                
                self.test_results[test_name] = {
                    "status": "passed" if result else "failed",
                    "duration": duration,
                    "details": result
                }
                
                logger.info(f"✅ {test_name} {'通过' if result else '失败'} ({duration:.2f}s)")
                
            except Exception as e:
                logger.error(f"❌ {test_name} 异常: {e}")
                self.test_results[test_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # 输出测试总结
        self.print_test_summary()
        return self.test_results
    
    async def test_message_system(self) -> bool:
        """测试消息系统的双重表示功能"""
        logger.info("测试 AgentMessage <-> APIMessage 转换")
        
        try:
            # 创建原始消息
            agent_msg = AgentMessage.create_progress(
                current_step="测试步骤",
                user_id="test_user",
                task_id="test_task",
                percentage=50.0,
                details="测试详情"
            )
            
            # 转换为API消息
            api_msg = agent_msg.to_api_message()
            
            # 验证转换结果
            assert api_msg.role == "assistant"
            assert "测试步骤" in api_msg.content
            
            # 测试消息转换器
            converter = MessageConverter()
            api_messages = converter.agent_messages_to_api_messages([agent_msg])
            
            assert len(api_messages) == 1
            assert isinstance(api_messages[0], APIMessage)
            
            logger.info("✅ 消息系统转换正常")
            return True
            
        except Exception as e:
            logger.error(f"❌ 消息系统测试失败: {e}")
            return False
    
    async def test_security_system(self) -> bool:
        """测试安全检查系统"""
        logger.info("测试多层安全检查机制")
        
        try:
            security_checker = get_security_checker()
            
            # 测试安全工具执行
            safe_result = await security_checker.check_tool_execution(
                "template_analysis_tool",
                {"template_id": "test_template"}
            )
            assert safe_result.allowed == True
            assert safe_result.level == SecurityLevel.SAFE
            
            # 测试危险操作检测
            dangerous_result = await security_checker.check_tool_execution(
                "sql_execution_tool",
                {"sql": "DROP DATABASE test; rm -rf /"}
            )
            assert dangerous_result.level in [SecurityLevel.FORBIDDEN, SecurityLevel.HIGH_RISK]
            
            # 测试中等风险操作
            medium_risk_result = await security_checker.check_tool_execution(
                "bash_tool",
                {"command": "ls -la && grep something"}
            )
            
            logger.info("✅ 安全检查机制正常")
            logger.info(f"安全统计: {security_checker.get_security_statistics()}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 安全系统测试失败: {e}")
            return False
    
    async def test_unified_controller(self) -> bool:
        """测试统一控制器的tt函数"""
        logger.info("测试统一控制器的核心tt函数")
        
        try:
            # 创建测试上下文
            context = ToolContext(
                user_id="test_user",
                task_id="test_task_unified",
                session_id="test_session",
                context_data={"test": "data"}
            )
            
            # 测试简单任务
            goal = "分析测试占位符并生成相应的查询"
            results = []
            
            # 收集tt函数的输出
            async for message in tt(goal, context, max_iterations=2):
                results.append(message)
                logger.info(f"收到消息: {message.type.value} - {message.get_display_text()}")
            
            # 验证结果
            assert len(results) > 0
            
            # 应该有进度消息和最终结果
            progress_messages = [r for r in results if r.type.value == "progress"]
            result_messages = [r for r in results if r.type.value == "result"]
            
            assert len(progress_messages) > 0, "应该有进度消息"
            logger.info(f"进度消息数量: {len(progress_messages)}")
            logger.info(f"结果消息数量: {len(result_messages)}")
            
            # 测试控制器统计
            controller = get_unified_controller()
            stats = controller.get_statistics()
            logger.info(f"控制器统计: {stats}")
            
            logger.info("✅ 统一控制器测试正常")
            return True
            
        except Exception as e:
            logger.error(f"❌ 统一控制器测试失败: {e}")
            return False
    
    async def test_compatibility_layer(self) -> bool:
        """测试兼容性层的迁移功能"""
        logger.info("测试新旧系统兼容性")
        
        try:
            # 创建旧格式任务
            old_task = AgentTask(
                type=TaskType.PLACEHOLDER_ANALYSIS,
                task_id="compat_test_task",
                user_id="test_user",
                data={
                    "placeholder_name": "test_placeholder",
                    "placeholder_text": "{{test}}",
                    "template_context": "这是一个测试占位符"
                }
            )
            
            # 使用兼容性层执行
            results = []
            async for message in execute_task_unified(old_task):
                results.append(message)
                logger.info(f"兼容层消息: {message.type.value}")
            
            # 验证兼容性
            assert len(results) > 0
            
            # 检查迁移统计
            compat_layer = get_compatibility_layer()
            migration_stats = compat_layer.get_migration_statistics()
            logger.info(f"迁移统计: {migration_stats}")
            
            # 验证新系统使用率
            assert migration_stats["total_usage"] > 0
            
            logger.info("✅ 兼容性层测试正常")
            return True
            
        except Exception as e:
            logger.error(f"❌ 兼容性层测试失败: {e}")
            return False
    
    async def test_performance_comparison(self) -> bool:
        """性能对比测试：新系统 vs 旧系统"""
        logger.info("执行性能对比测试")
        
        try:
            # 测试数据
            test_task = AgentTask(
                type=TaskType.PLACEHOLDER_ANALYSIS,
                task_id="perf_test",
                user_id="test_user",
                data={
                    "placeholder_name": "performance_test",
                    "placeholder_text": "{{perf_test}}",
                    "template_context": "性能测试占位符"
                }
            )
            
            # 测试新系统性能
            new_system_start = datetime.now()
            new_results = []
            async for msg in execute_task_unified(test_task):
                new_results.append(msg)
            new_system_duration = (datetime.now() - new_system_start).total_seconds()
            
            # 测试旧系统性能（如果可用）
            old_system_duration = 0
            old_results = []
            try:
                old_controller = AgentController()
                old_system_start = datetime.now()
                async for msg in old_controller.execute_task(test_task):
                    old_results.append(msg)
                old_system_duration = (datetime.now() - old_system_start).total_seconds()
            except Exception as e:
                logger.warning(f"旧系统测试跳过: {e}")
                old_system_duration = float('inf')  # 表示无法测试
            
            # 记录性能指标
            self.performance_metrics = {
                "new_system": {
                    "duration": new_system_duration,
                    "message_count": len(new_results),
                    "avg_message_time": new_system_duration / len(new_results) if new_results else 0
                },
                "old_system": {
                    "duration": old_system_duration,
                    "message_count": len(old_results),
                    "avg_message_time": old_system_duration / len(old_results) if old_results else 0
                }
            }
            
            logger.info(f"新系统耗时: {new_system_duration:.2f}s ({len(new_results)} 消息)")
            if old_system_duration != float('inf'):
                logger.info(f"旧系统耗时: {old_system_duration:.2f}s ({len(old_results)} 消息)")
                speedup = old_system_duration / new_system_duration if new_system_duration > 0 else 0
                logger.info(f"性能提升: {speedup:.2f}x")
            
            logger.info("✅ 性能对比测试完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 性能对比测试失败: {e}")
            return False
    
    async def test_end_to_end_integration(self) -> bool:
        """端到端集成测试"""
        logger.info("执行端到端集成测试")
        
        try:
            # 获取AutoReportAI实例
            ai_system = get_auto_report_ai()
            
            # 创建复杂的测试场景
            context = ToolContext(
                user_id="integration_test_user",
                task_id="integration_test",
                session_id="integration_session",
                context_data={
                    "template_id": "test_template",
                    "data_source_id": "test_datasource"
                }
            )
            
            # 执行复杂任务
            goal = "执行完整的模板分析工作流，包括占位符识别、SQL生成和数据查询"
            
            messages = []
            start_time = datetime.now()
            
            async for message in ai_system.process_task(goal, context):
                messages.append(message)
                logger.info(f"集成测试消息: {message.type.value} - {message.get_display_text()[:100]}")
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # 验证集成结果
            assert len(messages) > 0
            
            # 检查系统统计
            system_stats = ai_system.get_system_statistics()
            logger.info(f"系统统计: {system_stats}")
            
            # 验证各子系统协作
            assert system_stats["total_requests"] > 0
            
            logger.info(f"✅ 端到端集成测试完成 ({duration:.2f}s, {len(messages)} 消息)")
            return True
            
        except Exception as e:
            logger.error(f"❌ 端到端集成测试失败: {e}")
            return False
    
    def print_test_summary(self):
        """打印测试总结"""
        logger.info("=" * 60)
        logger.info("🏆 架构重构测试总结")
        logger.info("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r.get("status") == "passed")
        failed_tests = sum(1 for r in self.test_results.values() if r.get("status") == "failed")
        error_tests = sum(1 for r in self.test_results.values() if r.get("status") == "error")
        
        logger.info(f"总测试数: {total_tests}")
        logger.info(f"通过: {passed_tests} ✅")
        logger.info(f"失败: {failed_tests} ❌")
        logger.info(f"异常: {error_tests} 💥")
        logger.info(f"成功率: {passed_tests/total_tests*100:.1f}%")
        
        # 详细结果
        for test_name, result in self.test_results.items():
            status_emoji = {"passed": "✅", "failed": "❌", "error": "💥"}.get(result["status"], "❓")
            duration = result.get("duration", 0)
            logger.info(f"{status_emoji} {test_name}: {result['status']} ({duration:.2f}s)")
        
        # 性能指标
        if self.performance_metrics:
            logger.info("\n📊 性能指标:")
            for system, metrics in self.performance_metrics.items():
                logger.info(f"{system}: {metrics['duration']:.2f}s ({metrics['message_count']} 消息)")
        
        logger.info("=" * 60)


async def main():
    """主测试函数"""
    print("🚀 启动AutoReportAI架构重构验证")
    
    test_suite = ArchitectureTestSuite()
    results = await test_suite.run_all_tests()
    
    # 评估重构成功度
    passed_count = sum(1 for r in results.values() if r.get("status") == "passed")
    total_count = len(results)
    success_rate = passed_count / total_count * 100
    
    print(f"\n🎯 重构验证结果: {success_rate:.1f}% 成功率")
    
    if success_rate >= 80:
        print("🎉 重构基本成功！新架构运行良好。")
    elif success_rate >= 60:
        print("⚠️ 重构部分成功，需要进一步优化。")
    else:
        print("❌ 重构存在重大问题，需要修复。")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())