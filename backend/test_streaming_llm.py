"""
测试流式LLM API调用和动态超时机制
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 导入项目模块
from app.services.infrastructure.ai.llm.pure_database_manager import (
    ask_agent,
    get_user_llm_config,
    call_llm_api
)


async def test_streaming_api():
    """测试流式API调用"""
    logger.info("🔄 测试流式LLM API调用")
    
    try:
        # 设置数据库连接
        os.environ["DATABASE_URL"] = "postgresql://postgres:postgres123@localhost:5432/autoreport"
        os.environ["POSTGRES_PASSWORD"] = "postgres123"
        
        # 获取用户LLM配置
        user_id = "c9244981-d32d-4ff7-9e92-b50bfd7e4502"  # admin用户ID
        llm_config = await get_user_llm_config(user_id)
        
        if not llm_config:
            logger.error("未找到用户LLM配置")
            return
            
        logger.info(f"找到LLM配置: {llm_config['model_name']} @ {llm_config['base_url']}")
        
        # 测试1: 标准模型调用
        logger.info("\n=== 测试1: 标准模型调用 ===")
        standard_messages = [
            {"role": "system", "content": "你是一个数据分析助手"},
            {"role": "user", "content": "请解释什么是SQL，简短回答"}
        ]
        
        # 临时修改模型名称为标准模型
        standard_config = llm_config.copy()
        standard_config["model_name"] = "gpt-3.5-turbo"  # 标准模型
        
        standard_result = await call_llm_api(standard_config, standard_messages)
        logger.info(f"标准模型响应: {standard_result[:100]}...")
        
        # 测试2: Think模型调用（流式）
        logger.info("\n=== 测试2: Think模型调用（流式） ===")
        think_messages = [
            {"role": "system", "content": "你是一个高级数据分析专家，需要深度思考"},
            {"role": "user", "content": "请详细分析一个电商平台的用户留存率计算方法，包括不同时间窗口的计算逻辑，并给出SQL示例。请仔细思考并给出完整的分析。"}
        ]
        
        # 使用think模型
        think_config = llm_config.copy()
        think_config["model_name"] = "deepseek-v3.1-think-250821"  # think模型
        
        think_result = await call_llm_api(think_config, think_messages)
        logger.info(f"Think模型响应长度: {len(think_result)}")
        logger.info(f"Think模型响应预览: {think_result[:200]}...")
        
        # 测试3: 使用ask_agent接口
        logger.info("\n=== 测试3: 使用ask_agent接口 ===")
        agent_result = await ask_agent(
            user_id=user_id,
            question="基于Doris数据库，如何计算客户生命周期价值（CLV）？",
            agent_type="data_analyst",
            task_type="reasoning",
            complexity="complex"
        )
        logger.info(f"Agent响应: {agent_result[:200]}...")
        
        logger.info("✅ 流式API测试完成")
        
    except Exception as e:
        logger.error(f"流式API测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_timeout_scenarios():
    """测试各种超时场景"""
    logger.info("⏱️ 测试超时场景")
    
    try:
        os.environ["DATABASE_URL"] = "postgresql://postgres:postgres123@localhost:5432/autoreport"
        
        # 获取LLM配置
        user_id = "c9244981-d32d-4ff7-9e92-b50bfd7e4502"
        llm_config = await get_user_llm_config(user_id)
        
        if not llm_config:
            logger.error("未找到用户LLM配置")
            return
        
        # 测试长时间思考任务
        logger.info("\n=== 测试长时间思考任务 ===")
        long_think_messages = [
            {"role": "system", "content": "你是一个哲学家和数学家，需要深度思考复杂问题"},
            {"role": "user", "content": """
            请深入分析以下复杂的数据科学问题：
            
            1. 如何设计一个多维度的用户行为分析模型？
            2. 在大数据环境下如何平衡准确性和效率？
            3. 机器学习模型的可解释性与预测准确性的权衡策略？
            4. 实时数据流处理中的异常检测算法设计？
            5. 分布式计算环境下的数据一致性保证机制？
            
            请对每个问题进行详细分析，包括理论基础、实现方法、优缺点对比、实际应用案例等。
            """}
        ]
        
        think_config = llm_config.copy()
        think_config["model_name"] = "deepseek-v3.1-think-250821"
        
        result = await call_llm_api(think_config, long_think_messages)
        logger.info(f"长时间思考任务完成，响应长度: {len(result)}")
        
        logger.info("✅ 超时测试完成")
        
    except Exception as e:
        logger.error(f"超时测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    try:
        logger.info("🚀 开始流式LLM API测试")
        
        # 基础流式API测试
        await test_streaming_api()
        
        # 超时场景测试
        await test_timeout_scenarios()
        
        logger.info("🎉 所有测试完成")
        
    except Exception as e:
        logger.error(f"主测试异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())