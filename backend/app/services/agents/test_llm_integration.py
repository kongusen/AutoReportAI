"""
测试LLM集成修复
验证LLM适配器是否正确集成了LLMServerClient
"""

import asyncio
import logging
from typing import Dict, Any

from .core.llm_adapter import create_llm_adapter, create_agent_llm
from ..llm.client import get_llm_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_llm_client_basic():
    """测试基本LLM客户端功能"""
    logger.info("=== 测试基本LLM客户端功能 ===")
    
    try:
        # 获取LLM客户端
        client = get_llm_client()
        
        # 测试健康检查
        health = await client.health_check()
        logger.info(f"LLM客户端健康状态: {health}")
        
        # 获取客户端统计
        stats = client.get_client_stats()
        logger.info(f"客户端统计: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"LLM客户端基本测试失败: {e}")
        return False


async def test_llm_adapter_creation():
    """测试LLM适配器创建"""
    logger.info("=== 测试LLM适配器创建 ===")
    
    try:
        # 创建通用适配器
        adapter = await create_llm_adapter(
            model_name="gpt-4o-mini",
            user_id="test_user"
        )
        
        logger.info(f"适配器创建成功:")
        logger.info(f"- 模型: {adapter.model}")
        logger.info(f"- 用户ID: {adapter.user_id}")
        logger.info(f"- 元数据: {adapter.metadata}")
        
        # 测试健康检查
        health = await adapter.health_check()
        logger.info(f"适配器健康状态: {health}")
        
        return True
        
    except Exception as e:
        logger.error(f"LLM适配器创建测试失败: {e}")
        return False


async def test_agent_llm_creation():
    """测试代理专用LLM创建"""
    logger.info("=== 测试代理专用LLM创建 ===")
    
    try:
        agent_types = ["general", "placeholder_expert", "chart_specialist", "data_analyst"]
        
        for agent_type in agent_types:
            logger.info(f"创建 {agent_type} 类型LLM适配器")
            
            adapter = await create_agent_llm(agent_type, "test_user")
            
            logger.info(f"- {agent_type}: 模型={adapter.model}, 用户={adapter.user_id}")
        
        logger.info("所有代理类型LLM创建成功")
        return True
        
    except Exception as e:
        logger.error(f"代理LLM创建测试失败: {e}")
        return False


async def test_llm_chat_functionality():
    """测试LLM聊天功能"""
    logger.info("=== 测试LLM聊天功能 ===")
    
    try:
        # 创建适配器
        adapter = await create_llm_adapter(
            model_name="gpt-4o-mini",
            user_id="test_user"
        )
        
        # 导入ChatMessage
        from llama_index.core.base.llms.types import ChatMessage
        
        # 创建测试消息
        messages = [
            ChatMessage(role="system", content="你是一个友善的助手。"),
            ChatMessage(role="user", content="请说'你好'")
        ]
        
        # 发送聊天请求
        logger.info("发送聊天请求...")
        response = await adapter.achat(messages)
        
        logger.info(f"聊天响应:")
        logger.info(f"- 内容: {response.message.content}")
        logger.info(f"- 原始数据: {response.raw}")
        
        return True
        
    except Exception as e:
        logger.error(f"LLM聊天功能测试失败: {e}")
        return False


async def run_all_tests():
    """运行所有测试"""
    logger.info("开始LLM集成修复验证测试")
    
    tests = [
        ("LLM客户端基本功能", test_llm_client_basic),
        ("LLM适配器创建", test_llm_adapter_creation),
        ("代理LLM创建", test_agent_llm_creation),
        ("LLM聊天功能", test_llm_chat_functionality)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"执行测试: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name} - 通过")
            else:
                logger.error(f"❌ {test_name} - 失败")
                
        except Exception as e:
            results[test_name] = False
            logger.error(f"❌ {test_name} - 异常: {e}")
    
    # 汇总结果
    logger.info(f"\n{'='*50}")
    logger.info("测试结果汇总")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{status} - {test_name}")
    
    logger.info(f"\n总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        logger.info("🎉 所有测试通过，LLM集成修复成功！")
    else:
        logger.warning(f"⚠️ 还有 {total - passed} 个测试需要修复")
    
    return results


if __name__ == "__main__":
    # 运行测试
    asyncio.run(run_all_tests())