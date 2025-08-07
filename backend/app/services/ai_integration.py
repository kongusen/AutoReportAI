"""
AI集成服务
使用配置的AI供应商进行智能分析和报告生成
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

import aiohttp
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config.ai_provider_config import get_ai_config

logger = logging.getLogger(__name__)

@dataclass
class LLMRequest:
    """LLM请求数据类"""
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    model: Optional[str] = None

@dataclass 
class LLMResponse:
    """LLM响应数据类"""
    content: str
    usage: Dict[str, int]
    model: str
    response_time: float
    success: bool
    error: Optional[str] = None

class AIService:
    """AI服务集成类"""
    
    def __init__(self, scenario: str = "default"):
        self.config = get_ai_config(scenario)
        self.session = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        connector = aiohttp.TCPConnector(
            verify_ssl=self.config.get('verify_ssl', True),
            timeout=aiohttp.ClientTimeout(total=self.config.get('timeout', 60))
        )
        self.session = aiohttp.ClientSession(connector=connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def call_llm_async(self, request: LLMRequest) -> LLMResponse:
        """异步调用LLM"""
        if not self.session:
            raise RuntimeError("AIService must be used as async context manager")
        
        # 构建消息
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        # 构建请求payload
        payload = {
            "model": request.model or self.config["model"],
            "messages": messages,
            "max_tokens": request.max_tokens or self.config["max_tokens"],
            "temperature": request.temperature or self.config["temperature"],
            "stream": self.config.get("stream", False)
        }
        
        headers = {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        
        try:
            async with self.session.post(
                self.config["api_base_url"],
                json=payload,
                headers=headers
            ) as response:
                
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    
                    return LLMResponse(
                        content=data["choices"][0]["message"]["content"],
                        usage=data.get("usage", {}),
                        model=data.get("model", payload["model"]),
                        response_time=response_time,
                        success=True
                    )
                else:
                    error_text = await response.text()
                    logger.error(f"LLM API错误 {response.status}: {error_text}")
                    
                    return LLMResponse(
                        content="",
                        usage={},
                        model=payload["model"],
                        response_time=response_time,
                        success=False,
                        error=f"HTTP {response.status}: {error_text}"
                    )
                    
        except asyncio.TimeoutError:
            return LLMResponse(
                content="",
                usage={},
                model=payload["model"],
                response_time=time.time() - start_time,
                success=False,
                error="Request timeout"
            )
        except Exception as e:
            logger.error(f"LLM调用异常: {e}")
            return LLMResponse(
                content="",
                usage={},
                model=payload["model"],
                response_time=time.time() - start_time,
                success=False,
                error=str(e)
            )
    
    def call_llm_sync(self, request: LLMRequest) -> LLMResponse:
        """同步调用LLM（用于非异步环境）"""
        # 构建消息
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        # 构建请求payload
        payload = {
            "model": request.model or self.config["model"],
            "messages": messages,
            "max_tokens": request.max_tokens or self.config["max_tokens"],
            "temperature": request.temperature or self.config["temperature"]
        }
        
        headers = {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        
        try:
            response = requests.post(
                self.config["api_base_url"],
                json=payload,
                headers=headers,
                timeout=self.config.get("timeout", 60),
                verify=self.config.get('verify_ssl', True)
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                return LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    usage=data.get("usage", {}),
                    model=data.get("model", payload["model"]),
                    response_time=response_time,
                    success=True
                )
            else:
                logger.error(f"LLM API错误 {response.status_code}: {response.text}")
                
                return LLMResponse(
                    content="",
                    usage={},
                    model=payload["model"],
                    response_time=response_time,
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text}"
                )
                
        except requests.exceptions.Timeout:
            return LLMResponse(
                content="",
                usage={},
                model=payload["model"],
                response_time=time.time() - start_time,
                success=False,
                error="Request timeout"
            )
        except Exception as e:
            logger.error(f"LLM调用异常: {e}")
            return LLMResponse(
                content="",
                usage={},
                model=payload["model"],
                response_time=time.time() - start_time,
                success=False,
                error=str(e)
            )

class BigDataAIAnalyzer:
    """大数据AI分析器 - 专门用于大数据分析场景"""
    
    def __init__(self):
        self.ai_service = AIService("data_analysis")
    
    async def analyze_placeholder_requirements(self, template: str, placeholders: List[Dict]) -> Dict[str, Any]:
        """分析占位符需求"""
        
        system_prompt = """你是一个大数据分析专家，专门分析报告模板中的占位符需求。
        
你需要：
1. 分析每个占位符的数据需求
2. 确定需要的数据表和字段
3. 判断聚合计算类型
4. 评估查询复杂度
5. 提供优化建议

请用JSON格式返回结构化的分析结果。"""
        
        user_prompt = f"""
请分析以下报告模板中的占位符需求：

模板内容：
{template}

占位符列表：
{json.dumps(placeholders, ensure_ascii=False, indent=2)}

请分析每个占位符的：
1. 数据需求（需要什么数据）
2. 计算类型（统计、聚合、时间分析等）
3. 复杂度评估
4. 建议的SQL查询策略

返回JSON格式的分析结果。
"""
        
        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=3000,
            temperature=0.1
        )
        
        async with self.ai_service as ai:
            response = await ai.call_llm_async(request)
            
            if response.success:
                try:
                    analysis = json.loads(response.content)
                    return {
                        "success": True,
                        "analysis": analysis,
                        "response_time": response.response_time,
                        "token_usage": response.usage
                    }
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": "AI返回的内容不是有效JSON",
                        "raw_content": response.content
                    }
            else:
                return {
                    "success": False,
                    "error": response.error
                }
    
    async def generate_sql_queries(self, placeholder_requirements: Dict, table_schemas: Dict) -> Dict[str, Any]:
        """根据占位符需求生成SQL查询"""
        
        system_prompt = """你是一个SQL专家，专门为大数据分析生成高效的SQL查询。

你需要：
1. 根据占位符需求生成对应的SQL查询
2. 优化查询性能（使用索引、减少JOIN等）
3. 考虑大数据场景下的查询优化
4. 提供批处理建议

请生成可执行的SQL查询，并用JSON格式返回。"""
        
        user_prompt = f"""
基于以下信息生成SQL查询：

占位符需求：
{json.dumps(placeholder_requirements, ensure_ascii=False, indent=2)}

数据库表结构：
{json.dumps(table_schemas, ensure_ascii=False, indent=2)}

请为每个占位符生成对应的SQL查询，要求：
1. 查询要高效（适合大数据场景）
2. 包含必要的WHERE条件和GROUP BY
3. 考虑使用LIMIT减少数据量
4. 提供查询复杂度评估

返回JSON格式，包含每个占位符对应的SQL查询。
"""
        
        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=4000,
            temperature=0.2
        )
        
        async with self.ai_service as ai:
            response = await ai.call_llm_async(request)
            
            if response.success:
                try:
                    queries = json.loads(response.content)
                    return {
                        "success": True,
                        "queries": queries,
                        "response_time": response.response_time,
                        "token_usage": response.usage
                    }
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": "AI生成的SQL查询格式错误",
                        "raw_content": response.content
                    }
            else:
                return {
                    "success": False,
                    "error": response.error
                }
    
    async def optimize_report_template(self, template: str, data_analysis_results: Dict) -> Dict[str, Any]:
        """根据数据分析结果优化报告模板"""
        
        system_prompt = """你是一个报告优化专家，专门优化大数据分析报告的展示效果。

你需要：
1. 根据数据分析结果优化报告结构
2. 改进数据展示方式
3. 增加有价值的洞察和建议
4. 确保报告内容准确且有价值

请返回优化后的报告模板。"""
        
        user_prompt = f"""
请优化以下报告模板：

原始模板：
{template}

数据分析结果：
{json.dumps(data_analysis_results, ensure_ascii=False, indent=2)}

请优化：
1. 改进数据展示结构
2. 添加数据洞察
3. 完善图表建议
4. 增加业务建议

返回优化后的完整报告模板。
"""
        
        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=4000,
            temperature=0.4
        )
        
        async with self.ai_service as ai:
            response = await ai.call_llm_async(request)
            
            return {
                "success": response.success,
                "optimized_template": response.content if response.success else "",
                "error": response.error if not response.success else None,
                "response_time": response.response_time,
                "token_usage": response.usage
            }

# 测试AI配置的函数
async def test_ai_configuration():
    """测试AI配置是否正常工作"""
    print("🧪 测试AI供应商配置...")
    
    ai_service = AIService("placeholder_analysis")
    
    test_request = LLMRequest(
        prompt="请回答：你是什么AI模型？请简要介绍你的能力。",
        system_prompt="你是一个AI助手，专门帮助用户进行数据分析。",
        max_tokens=200,
        temperature=0.3
    )
    
    async with ai_service as ai:
        response = await ai.call_llm_async(test_request)
        
        if response.success:
            print("✅ AI配置测试成功!")
            print(f"响应时间: {response.response_time:.2f}秒")
            print(f"Token使用: {response.usage}")
            print(f"模型: {response.model}")
            print(f"回答: {response.content}")
            return True
        else:
            print("❌ AI配置测试失败!")
            print(f"错误: {response.error}")
            return False

if __name__ == "__main__":
    # 测试AI配置
    import asyncio
    asyncio.run(test_ai_configuration())