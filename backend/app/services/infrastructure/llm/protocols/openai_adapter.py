"""
OpenAI协议适配器
===============

将结构化消息转换为OpenAI API格式，支持JSON输出模式控制
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import asdict
from enum import Enum

# 避免循环导入，使用类型提示字符串
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.services.infrastructure.agents.core import StructuredMessage

logger = logging.getLogger(__name__)


class OpenAIModel(Enum):
    """OpenAI模型枚举"""
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_3_5_TURBO = "gpt-3.5-turbo"


class ResponseFormat(Enum):
    """响应格式枚举"""
    TEXT = "text"
    JSON = "json_object"
    JSON_SCHEMA = "json_schema"


class OpenAIConfig:
    """OpenAI配置类"""
    
    def __init__(
        self,
        model: OpenAIModel = OpenAIModel.GPT_4O,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        response_format: ResponseFormat = ResponseFormat.TEXT
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.response_format = response_format
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        config = {
            "model": self.model.value,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty
        }
        
        if self.max_tokens:
            config["max_tokens"] = self.max_tokens
        
        if self.response_format != ResponseFormat.TEXT:
            config["response_format"] = {"type": self.response_format.value}
        
        return config


class OpenAIAdapter:
    """OpenAI协议适配器"""
    
    def __init__(self, config: Optional[OpenAIConfig] = None):
        self.config = config or OpenAIConfig()
        self.retry_count = 3
        self.timeout = 30
    
    def convert_to_openai_format(self, structured_message: "StructuredMessage") -> Dict[str, Any]:
        """
        将结构化消息转换为OpenAI API格式
        
        Args:
            structured_message: 结构化消息
            
        Returns:
            Dict: OpenAI API请求格式
        """
        llm_format = structured_message.to_llm_format()
        
        # 构建系统提示词
        system_prompt = self._build_system_prompt(llm_format)
        
        # 构建用户消息
        user_message = self._build_user_message(llm_format)
        
        # 构建OpenAI请求
        openai_request = {
            "model": self.config.model.value,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty
        }
        
        # 添加可选参数
        if self.config.max_tokens:
            openai_request["max_tokens"] = self.config.max_tokens
        
        if self.config.response_format != ResponseFormat.TEXT:
            openai_request["response_format"] = {"type": self.config.response_format.value}
        
        # 添加任务特定的参数
        self._add_task_specific_parameters(openai_request, llm_format)
        
        return openai_request
    
    def _build_system_prompt(self, llm_format: Dict[str, Any]) -> str:
        """构建系统提示词"""
        task_type = llm_format["task"]["type"]
        complexity = llm_format["task"]["complexity"]
        step = llm_format["task"]["step"]
        
        system_prompts = {
            "data_analysis": "你是一个数据分析专家，擅长处理和分析结构化数据。",
            "sql_generation": "你是一个SQL专家，擅长编写高效、准确的SQL查询。",
            "report_generation": "你是一个报告生成专家，擅长创建结构清晰的分析报告。",
            "general": "你是一个有帮助的AI助手，擅长处理各种任务。"
        }
        
        base_prompt = system_prompts.get(task_type, system_prompts["general"])
        
        # 添加复杂度提示
        complexity_prompts = {
            "low": "请提供简洁直接的回应。",
            "medium": "请提供详细的分析和解释。",
            "high": "请提供深入的分析、多个角度和详细解释。",
            "critical": "这是关键任务，请提供最全面、准确的分析和解决方案。"
        }
        
        complexity_prompt = complexity_prompts.get(complexity, "")
        
        # 添加JSON输出提示（如果启用）
        json_prompt = ""
        if self.config.response_format == ResponseFormat.JSON:
            json_prompt = "请始终以JSON格式返回响应。"
        elif self.config.response_format == ResponseFormat.JSON_SCHEMA:
            json_prompt = "请按照指定的JSON schema格式返回响应。"
        
        return f"{base_prompt} {complexity_prompt} {json_prompt}".strip()
    
    def _build_user_message(self, llm_format: Dict[str, Any]) -> str:
        """构建用户消息"""
        parts = []
        
        # 添加上下文信息
        context = llm_format["context"]
        if context["task_name"] and context["task_description"]:
            parts.append(f"任务: {context['task_name']}")
            parts.append(f"描述: {context['task_description']}")
        
        # 添加占位符信息
        if context["placeholders"]:
            parts.append("占位符信息:")
            for key, value in context["placeholders"].items():
                parts.append(f"  {key}: {value}")
        
        # 添加内容
        for content in llm_format["content"]:
            content_type = content["type"]
            content_data = content["data"]
            
            if content_type == "text":
                parts.append(f"用户输入: {content_data}")
            elif content_type == "sql":
                parts.append(f"SQL查询: {content_data}")
            elif content_type == "json":
                parts.append(f"JSON数据: {content_data}")
            elif content_type == "code":
                parts.append(f"代码: {content_data}")
            elif content_type == "table_data":
                parts.append(f"表格数据: {json.dumps(content_data, ensure_ascii=False)}")
        
        # 添加任务要求
        requirements = llm_format["task"]["requirements"]
        if requirements["requires_thinking"]:
            parts.append("要求: 需要深入思考和分析")
        if requirements["cost_sensitive"]:
            parts.append("要求: 对成本敏感，请优化资源使用")
        if requirements["speed_priority"]:
            parts.append("要求: 速度优先，请快速响应")
        
        return "\n\n".join(parts)
    
    def _add_task_specific_parameters(self, openai_request: Dict[str, Any], llm_format: Dict[str, Any]):
        """添加任务特定的参数"""
        task_type = llm_format["task"]["type"]
        complexity = llm_format["task"]["complexity"]
        
        # 根据任务类型和复杂度调整参数
        if task_type == "sql_generation":
            # SQL生成任务需要更高的准确性
            openai_request["temperature"] = max(0.1, self.config.temperature - 0.2)
            
        elif task_type == "data_analysis" and complexity in ["high", "critical"]:
            # 复杂数据分析需要更多tokens
            if not openai_request.get("max_tokens"):
                openai_request["max_tokens"] = 4000
        
        elif task_type == "report_generation":
            # 报告生成需要更详细的输出
            openai_request["temperature"] = min(0.9, self.config.temperature + 0.1)
    
    def set_json_mode(self, enabled: bool = True, schema: Optional[Dict] = None):
        """设置JSON输出模式"""
        if enabled:
            if schema:
                self.config.response_format = ResponseFormat.JSON_SCHEMA
                # 这里可以存储schema用于验证
            else:
                self.config.response_format = ResponseFormat.JSON
        else:
            self.config.response_format = ResponseFormat.TEXT
    
    def validate_json_response(self, response: str, expected_schema: Optional[Dict] = None) -> bool:
        """验证JSON响应格式"""
        try:
            data = json.loads(response)
            
            if expected_schema:
                # 简单的schema验证（实际应该使用jsonschema库）
                if not isinstance(data, dict):
                    return False
                
                for key, value_type in expected_schema.items():
                    if key not in data:
                        return False
                    # 简单的类型检查
                    if value_type == "string" and not isinstance(data[key], str):
                        return False
                    elif value_type == "number" and not isinstance(data[key], (int, float)):
                        return False
                    elif value_type == "boolean" and not isinstance(data[key], bool):
                        return False
                    elif value_type == "array" and not isinstance(data[key], list):
                        return False
                    elif value_type == "object" and not isinstance(data[key], dict):
                        return False
            
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    
    async def execute_with_retry(self, structured_message: "StructuredMessage", api_client) -> Dict[str, Any]:
        """带重试的执行方法"""
        openai_request = self.convert_to_openai_format(structured_message)
        
        for attempt in range(self.retry_count):
            try:
                response = await api_client.chat.completions.create(**openai_request)
                
                # 验证响应
                if self.config.response_format != ResponseFormat.TEXT:
                    content = response.choices[0].message.content
                    if not self.validate_json_response(content):
                        raise ValueError("Invalid JSON response format")
                
                return self._parse_response(response)
                
            except Exception as e:
                logger.warning(f"OpenAI API调用失败 (尝试 {attempt + 1}/{self.retry_count}): {e}")
                if attempt == self.retry_count - 1:
                    raise
                
                # 指数退避
                await asyncio.sleep(2 ** attempt)
        
        raise Exception("所有重试尝试都失败了")
    
    def _parse_response(self, response) -> Dict[str, Any]:
        """解析OpenAI响应"""
        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "finish_reason": response.choices[0].finish_reason
        }


# 便捷函数
def create_openai_adapter(
    model: OpenAIModel = OpenAIModel.GPT_4O,
    temperature: float = 0.7,
    json_mode: bool = False
) -> OpenAIAdapter:
    """创建OpenAI适配器的便捷函数"""
    config = OpenAIConfig(
        model=model,
        temperature=temperature,
        response_format=ResponseFormat.JSON if json_mode else ResponseFormat.TEXT
    )
    return OpenAIAdapter(config)