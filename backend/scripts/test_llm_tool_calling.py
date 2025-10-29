#!/usr/bin/env python3
"""
LLM 工具调用测试脚本

用于验证 LLM 是否正确支持 JSON 模式和工具调用格式
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.container import Container

async def test_llm_json_mode():
    """测试 LLM 的 JSON 模式支持"""
    print("🧪 测试 LLM JSON 模式支持...")
    
    container = Container()
    llm_service = container.llm  # 修复：使用正确的属性名

    # 测试 JSON 模式
    test_prompt = """请返回 JSON 格式的响应，包含以下结构：
{
  "reasoning": "测试 JSON 模式",
  "action": "tool_call",
  "tool_calls": [
    {
      "name": "test_tool",
      "arguments": {}
    }
  ]
}"""

    try:
        response = await llm_service.ask(
            user_id="f9700549-54d9-4c84-88f7-2d4342b10426",
            prompt=test_prompt,
            response_format={"type": "json_object"}
        )
        print("✅ LLM JSON 模式测试成功")
        print(f"📝 响应: {response}")
        return True
    except Exception as e:
        print(f"❌ LLM JSON 模式测试失败: {e}")
        return False

async def test_llm_tool_calling():
    """测试 LLM 的工具调用理解"""
    print("\n🧪 测试 LLM 工具调用理解...")
    
    container = Container()
    llm_service = container.llm  # 修复：使用正确的属性名

    # 测试工具调用理解
    test_prompt = """你是一个SQL生成专家。现在需要统计退货申请的总数。

**重要**: 你必须先使用工具了解数据库结构，然后才能生成SQL。

请按照以下格式返回：
1. 首先调用 schema_discovery 工具了解数据库结构
2. 然后调用 schema_retrieval 工具获取相关表信息
3. 最后生成SQL

请返回 JSON 格式：
{
  "reasoning": "我需要先了解数据库结构",
  "action": "tool_call",
  "tool_calls": [
    {
      "name": "schema_discovery",
      "arguments": {}
    }
  ]
}"""

    try:
        response = await llm_service.ask(
            user_id="f9700549-54d9-4c84-88f7-2d4342b10426",
            prompt=test_prompt,
            response_format={"type": "json_object"}
        )
        print("✅ LLM 工具调用理解测试成功")
        print(f"📝 响应: {response}")
        return True
    except Exception as e:
        print(f"❌ LLM 工具调用理解测试失败: {e}")
        return False

async def test_llm_direct_sql():
    """测试 LLM 是否直接返回 SQL（不应该的行为）"""
    print("\n🧪 测试 LLM 是否直接返回 SQL...")
    
    container = Container()
    llm_service = container.llm  # 修复：使用正确的属性名

    # 测试直接 SQL 生成
    test_prompt = """请生成一个统计退货申请总数的SQL查询。

数据库中有以下表：
- ods_refund: 退货申请表
- ods_complain: 投诉表

请直接返回SQL语句。"""

    try:
        response = await llm_service.ask(
            user_id="f9700549-54d9-4c84-88f7-2d4342b10426",
            prompt=test_prompt,
            response_format={"type": "json_object"}
        )
        print("📝 LLM 直接 SQL 响应:")
        print(f"📝 响应: {response}")
        
        # 检查是否直接返回了 SQL
        if isinstance(response, dict):
            content = response.get('content', '')
            if 'SELECT' in str(content).upper():
                print("⚠️ LLM 直接返回了 SQL，这可能不是期望的行为")
                return False
            else:
                print("✅ LLM 没有直接返回 SQL")
                return True
        else:
            print("⚠️ 响应格式不是预期的 JSON")
            return False
            
    except Exception as e:
        print(f"❌ LLM 直接 SQL 测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始 LLM 工具调用测试...")
    
    # 运行所有测试
    tests = [
        test_llm_json_mode(),
        test_llm_tool_calling(),
        test_llm_direct_sql()
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    print("\n📊 测试结果汇总:")
    test_names = ["JSON 模式", "工具调用理解", "直接 SQL 测试"]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        if isinstance(result, Exception):
            print(f"❌ {name}: 异常 - {result}")
        elif result:
            print(f"✅ {name}: 通过")
        else:
            print(f"❌ {name}: 失败")
    
    print("\n🎯 测试完成!")

if __name__ == "__main__":
    asyncio.run(main())
