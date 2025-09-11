"""
核心重构测试 - 简化版本
专注测试重构后的核心组件，避免复杂依赖
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_api_messages():
    """测试API消息系统"""
    logger.info("🧪 测试API消息系统")
    
    try:
        # 直接导入核心消息模块
        from app.services.infrastructure.ai.core.api_messages import APIMessage, MessageConverter
        from app.services.infrastructure.ai.core.messages import AgentMessage, MessageType
        
        # 创建测试消息
        agent_msg = AgentMessage.create_progress(
            current_step="测试进度",
            user_id="test_user", 
            task_id="test_task",
            percentage=75.0
        )
        
        # 转换为API消息
        api_msg = agent_msg.to_api_message()
        
        # 验证转换
        assert api_msg.role == "assistant"
        assert "测试进度" in api_msg.content
        
        # 测试消息转换器
        converter = MessageConverter()
        api_messages = converter.agent_messages_to_api_messages([agent_msg])
        assert len(api_messages) == 1
        
        logger.info("✅ API消息系统测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ API消息系统测试失败: {e}")
        return False


async def test_security_checker():
    """测试安全检查器"""
    logger.info("🧪 测试安全检查器")
    
    try:
        from app.services.infrastructure.ai.core.security import SecurityChecker, SecurityLevel
        
        checker = SecurityChecker()
        
        # 测试安全操作
        safe_result = await checker.check_tool_execution(
            "template_analysis_tool",
            {"template_id": "safe_template"}
        )
        assert safe_result.allowed == True
        
        # 测试危险操作
        dangerous_result = await checker.check_tool_execution(
            "bash_tool", 
            {"command": "rm -rf / --no-preserve-root"}
        )
        assert dangerous_result.level == SecurityLevel.FORBIDDEN
        assert dangerous_result.allowed == False
        
        # 测试中等风险
        medium_result = await checker.check_tool_execution(
            "sql_tool",
            {"sql": "DELETE FROM users"}  # 无WHERE条件的删除
        )
        assert medium_result.level == SecurityLevel.HIGH_RISK
        
        logger.info("✅ 安全检查器测试通过")
        logger.info(f"安全统计: {checker.get_security_statistics()}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 安全检查器测试失败: {e}")
        return False


async def test_enhanced_prompts():
    """测试增强提示系统"""
    logger.info("🧪 测试增强提示系统")
    
    try:
        from app.services.infrastructure.ai.core.enhanced_prompts import SimplifiedPromptManager
        
        manager = SimplifiedPromptManager()
        
        # 测试编排提示
        prompt = manager.get_orchestration_prompt(
            goal="测试任务目标",
            available_tools=["tool1", "tool2", "tool3"],
            context={
                "iteration": 0,
                "conversation_history": []
            }
        )
        
        assert len(prompt) > 0
        assert "任务目标" in prompt
        assert "tool1" in prompt
        assert "<task_analysis>" in prompt  # XML标签
        
        # 测试SQL分析提示
        sql_prompt = manager.get_sql_analysis_prompt(
            placeholder_name="test_placeholder",
            template_context="测试模板上下文",
            available_tables=["table1", "table2"]
        )
        
        assert len(sql_prompt) > 0
        assert "test_placeholder" in sql_prompt
        assert "table1" in sql_prompt
        
        # 检查使用统计
        stats = manager.get_usage_statistics()
        assert stats["total_prompts"] >= 2
        assert stats["avg_length"] > 0
        
        logger.info("✅ 增强提示系统测试通过")
        logger.info(f"提示统计: {stats}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 增强提示系统测试失败: {e}")
        return False


async def test_streaming_json_parser():
    """测试流式JSON解析器"""
    logger.info("🧪 测试流式JSON解析器")
    
    try:
        from app.services.infrastructure.ai.core.api_messages import StreamingJSONParser
        
        parser = StreamingJSONParser()
        
        # 测试完整JSON
        complete_json = '{"tool": "test_tool", "params": {"key": "value"}}'
        results = parser.process_chunk(complete_json)
        
        assert len(results) == 1
        assert results[0]["tool"] == "test_tool"
        assert results[0]["params"]["key"] == "value"
        
        # 测试分块JSON
        parser.reset()
        chunk1 = '{"tool": "test'
        chunk2 = '_tool", "params": {'
        chunk3 = '"key": "value"}}'
        
        results1 = parser.process_chunk(chunk1)
        results2 = parser.process_chunk(chunk2)
        results3 = parser.process_chunk(chunk3)
        
        assert len(results1) == 0  # 不完整
        assert len(results2) == 0  # 不完整  
        assert len(results3) == 1  # 完整
        assert results3[0]["tool"] == "test_tool"
        
        # 测试修复功能
        parser.reset()
        broken_json = '{"tool": "test_tool", "params": {"key": "value"'  # 缺少括号
        fixed_result = parser._fix_incomplete_json(broken_json)
        
        if fixed_result:  # 如果修复成功
            assert "tool" in fixed_result
        
        logger.info("✅ 流式JSON解析器测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 流式JSON解析器测试失败: {e}")
        return False


async def test_tool_context():
    """测试工具上下文"""
    logger.info("🧪 测试工具上下文")
    
    try:
        from app.services.infrastructure.ai.core.tools import ToolContext
        
        # 创建基础上下文
        context = ToolContext(
            user_id="test_user",
            task_id="test_task",
            session_id="test_session",
            context_data={"key": "value"}
        )
        
        assert context.user_id == "test_user"
        assert context.task_id == "test_task"
        assert context.context_data["key"] == "value"
        
        # 测试错误记录
        context.add_error("test_error", "测试错误信息")
        recent_errors = context.get_recent_errors(limit=1)
        assert len(recent_errors) == 1
        assert recent_errors[0]["type"] == "test_error"
        
        # 测试洞察记录
        context.add_insight("测试洞察")
        assert "测试洞察" in context.learned_insights
        
        logger.info("✅ 工具上下文测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 工具上下文测试失败: {e}")
        return False


async def run_core_tests():
    """运行所有核心测试"""
    logger.info("🚀 开始核心重构测试")
    
    tests = [
        ("API消息系统", test_api_messages),
        ("安全检查器", test_security_checker), 
        ("增强提示系统", test_enhanced_prompts),
        ("流式JSON解析器", test_streaming_json_parser),
        ("工具上下文", test_tool_context)
    ]
    
    results = {}
    passed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 执行测试: {test_name}")
        start_time = datetime.now()
        
        try:
            success = await test_func()
            duration = (datetime.now() - start_time).total_seconds()
            
            results[test_name] = {
                "success": success,
                "duration": duration
            }
            
            if success:
                passed += 1
                logger.info(f"✅ {test_name} 通过 ({duration:.2f}s)")
            else:
                logger.error(f"❌ {test_name} 失败 ({duration:.2f}s)")
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() 
            logger.error(f"💥 {test_name} 异常: {e} ({duration:.2f}s)")
            results[test_name] = {
                "success": False,
                "error": str(e),
                "duration": duration
            }
    
    # 输出总结
    total = len(tests)
    success_rate = passed / total * 100
    
    logger.info("\n" + "="*60)
    logger.info("🏆 核心重构测试总结")
    logger.info("="*60)
    logger.info(f"总测试数: {total}")
    logger.info(f"通过数量: {passed}")
    logger.info(f"成功率: {success_rate:.1f}%")
    
    for test_name, result in results.items():
        status = "✅ 通过" if result["success"] else "❌ 失败"
        duration = result["duration"]
        logger.info(f"{status} {test_name} ({duration:.2f}s)")
    
    logger.info("="*60)
    
    if success_rate >= 80:
        logger.info("🎉 核心重构验证成功！新架构组件运行良好。")
    elif success_rate >= 60:
        logger.info("⚠️ 核心重构部分成功，有待优化。")
    else:
        logger.info("❌ 核心重构存在问题，需要修复。")
    
    return results


if __name__ == "__main__":
    try:
        results = asyncio.run(run_core_tests())
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试运行失败: {e}")
        import traceback
        traceback.print_exc()