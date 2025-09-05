"""
简单测试流式API
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
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

from app.services.infrastructure.ai.llm.pure_database_manager import (
    get_user_llm_config,
    call_streaming_llm_api
)


async def test_simple_streaming():
    """简单测试流式调用"""
    try:
        os.environ["DATABASE_URL"] = "postgresql://postgres:postgres123@localhost:5432/autoreport"
        
        user_id = "c9244981-d32d-4ff7-9e92-b50bfd7e4502"
        llm_config = await get_user_llm_config(user_id)
        
        if not llm_config:
            logger.error("未找到LLM配置")
            return
        
        logger.info(f"LLM配置: {llm_config}")
        
        # 构建简单的请求
        request_data = {
            "model": "deepseek-v3.1-think-250821",
            "messages": [
                {"role": "user", "content": "什么是人工智能？请简单解释"}
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": True
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {llm_config['api_key']}"
        }
        
        logger.info("开始流式调用...")
        result = await call_streaming_llm_api(llm_config, request_data, headers)
        logger.info(f"结果: {result}")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_simple_streaming())