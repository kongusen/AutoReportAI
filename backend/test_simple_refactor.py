"""
简单的重构验证测试 - 直接测试重构的核心类
"""

import sys
import os
import asyncio
import json

# 直接添加路径避免复杂的导入问题
sys.path.append('/Users/shan/work/uploads/AutoReportAI/backend')


def test_api_message():
    """测试API消息类"""
    print("🧪 测试API消息类")
    
    # 直接导入并测试
    from app.services.infrastructure.ai.core.api_messages import APIMessage
    
    # 创建消息
    msg = APIMessage.user_message("测试消息内容")
    assert msg.role == "user"
    assert msg.content == "测试消息内容"
    
    # 转换为字典
    msg_dict = msg.to_dict()
    assert msg_dict["role"] == "user"
    assert msg_dict["content"] == "测试消息内容"
    
    print("✅ API消息类测试通过")
    return True


def test_streaming_parser():
    """测试流式解析器"""
    print("🧪 测试流式JSON解析器")
    
    from app.services.infrastructure.ai.core.api_messages import StreamingJSONParser
    
    parser = StreamingJSONParser()
    
    # 测试完整JSON解析
    json_text = '{"tool": "test_tool", "params": {"key": "value"}}'
    results = parser.process_chunk(json_text)
    
    assert len(results) == 1
    result = results[0]
    assert result["tool"] == "test_tool"
    assert result["params"]["key"] == "value"
    
    print("✅ 流式JSON解析器测试通过")
    return True


async def test_security_basic():
    """测试基础安全检查"""
    print("🧪 测试基础安全检查")
    
    from app.services.infrastructure.ai.core.security import SecurityChecker, SecurityLevel
    
    checker = SecurityChecker()
    
    # 测试安全操作
    result = await checker.check_tool_execution(
        "safe_tool",
        {"safe_param": "safe_value"}
    )
    
    assert result.allowed == True
    print(f"安全检查结果: {result.level.value}")
    
    print("✅ 基础安全检查测试通过")
    return True


def test_enhanced_prompts():
    """测试增强提示系统"""
    print("🧪 测试增强提示系统")
    
    from app.services.infrastructure.ai.core.enhanced_prompts import SimplifiedPromptManager
    
    manager = SimplifiedPromptManager()
    
    # 生成编排提示
    prompt = manager.get_orchestration_prompt(
        goal="测试目标",
        available_tools=["tool1", "tool2"]
    )
    
    assert len(prompt) > 0
    assert "测试目标" in prompt
    assert "tool1" in prompt
    assert "<task_analysis>" in prompt
    
    print(f"生成的提示长度: {len(prompt)} 字符")
    print("✅ 增强提示系统测试通过")
    return True


def test_tool_context():
    """测试工具上下文"""
    print("🧪 测试工具上下文")
    
    from app.services.infrastructure.ai.core.tools import ToolContext
    
    # 创建上下文
    context = ToolContext(
        user_id="test_user",
        task_id="test_task", 
        session_id="test_session"
    )
    
    # 测试基础属性
    assert context.user_id == "test_user"
    assert context.task_id == "test_task"
    
    # 测试错误记录
    context.add_error("test_error", "测试错误")
    errors = context.get_recent_errors()
    assert len(errors) == 1
    assert errors[0]["type"] == "test_error"
    
    # 测试洞察记录
    context.add_insight("测试洞察")
    assert "测试洞察" in context.learned_insights
    
    print("✅ 工具上下文测试通过")
    return True


async def run_simple_tests():
    """运行简单的测试套件"""
    print("🚀 开始简化重构验证测试\n")
    
    tests = [
        ("API消息类", test_api_message),
        ("流式解析器", test_streaming_parser), 
        ("基础安全检查", test_security_basic),
        ("增强提示系统", test_enhanced_prompts),
        ("工具上下文", test_tool_context)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✅ {test_name} 通过\n")
            else:
                print(f"❌ {test_name} 失败\n")
                
        except Exception as e:
            print(f"💥 {test_name} 异常: {e}\n")
    
    # 输出结果
    success_rate = passed / total * 100
    print("=" * 50)
    print("🏆 重构验证结果")
    print("=" * 50)
    print(f"测试总数: {total}")
    print(f"通过数量: {passed}")
    print(f"成功率: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("🎉 重构验证成功！核心组件运行良好。")
    elif success_rate >= 60:
        print("⚠️ 重构部分成功，需要进一步优化。")
    else:
        print("❌ 重构存在问题，需要修复。")
    
    print("=" * 50)
    
    return passed, total


if __name__ == "__main__":
    try:
        passed, total = asyncio.run(run_simple_tests())
        print(f"\n📊 最终结果: {passed}/{total} 通过")
    except Exception as e:
        print(f"测试执行失败: {e}")
        import traceback
        traceback.print_exc()