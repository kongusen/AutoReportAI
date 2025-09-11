"""
API消息模块 - 面向LLM的精简消息格式
基于Claude Code理念：CliMessage vs APIMessage的双重表示
"""

import json
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, AsyncGenerator

from .messages import AgentMessage, MessageType


@dataclass
class APIMessage:
    """面向LLM的精简消息格式 - 类似Claude Code的APIMessage"""
    role: str  # "system" | "user" | "assistant"
    content: str
    
    @classmethod
    def from_agent_message(cls, agent_msg: AgentMessage) -> "APIMessage":
        """从AgentMessage转换为APIMessage"""
        if agent_msg.type == MessageType.PROGRESS:
            return cls(
                role="assistant", 
                content=f"进度更新: {agent_msg.progress.current_step}"
            )
        elif agent_msg.type == MessageType.RESULT:
            return cls(
                role="assistant", 
                content=json.dumps(agent_msg.content, ensure_ascii=False) if agent_msg.content else ""
            )
        elif agent_msg.type == MessageType.ERROR:
            return cls(
                role="assistant", 
                content=f"错误: {agent_msg.error.error_message}" if agent_msg.error else "发生未知错误"
            )
        else:
            return cls(
                role="assistant", 
                content=str(agent_msg.content) if agent_msg.content else ""
            )
    
    @classmethod
    def system_message(cls, content: str) -> "APIMessage":
        """创建系统消息"""
        return cls(role="system", content=content)
    
    @classmethod
    def user_message(cls, content: str) -> "APIMessage":
        """创建用户消息"""
        return cls(role="user", content=content)
    
    @classmethod
    def assistant_message(cls, content: str) -> "APIMessage":
        """创建助手消息"""
        return cls(role="assistant", content=content)
    
    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式"""
        return {
            "role": self.role,
            "content": self.content
        }


class StreamingJSONParser:
    """流式JSON解析器 - 类似Claude Code的流式解析能力"""
    
    def __init__(self):
        self.buffer = ""
        self.bracket_count = 0
        self.in_quotes = False
        self.escape_next = False
    
    async def parse_tool_calls_stream(
        self, 
        stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式解析工具调用参数
        
        Args:
            stream: 文本流
            
        Yields:
            解析出的JSON对象
        """
        async for chunk in stream:
            results = self.process_chunk(chunk)
            for result in results:
                yield result
    
    def process_chunk(self, chunk: str) -> List[Dict[str, Any]]:
        """
        处理单个文本块
        
        Args:
            chunk: 文本块
            
        Returns:
            解析出的JSON对象列表
        """
        results = []
        self.buffer += chunk
        
        i = 0
        while i < len(chunk):
            char = chunk[i]
            
            # 处理转义字符
            if self.escape_next:
                self.escape_next = False
                i += 1
                continue
            
            if char == '\\':
                self.escape_next = True
                i += 1
                continue
            
            # 处理引号状态
            if char == '"':
                self.in_quotes = not self.in_quotes
                i += 1
                continue
            
            # 只在非引号内处理括号
            if not self.in_quotes:
                if char == '{':
                    self.bracket_count += 1
                elif char == '}':
                    self.bracket_count -= 1
                    
                    # 当括号计数回到0时，尝试解析完整的JSON
                    if self.bracket_count == 0:
                        try:
                            parsed = json.loads(self.buffer.strip())
                            results.append(parsed)
                            self.buffer = ""
                        except json.JSONDecodeError:
                            # 尝试修复并解析
                            fixed = self._fix_incomplete_json(self.buffer)
                            if fixed:
                                results.append(fixed)
                                self.buffer = ""
            
            i += 1
        
        return results
    
    def _fix_incomplete_json(self, buffer: str) -> Optional[Dict[str, Any]]:
        """
        尝试修复不完整的JSON
        
        Args:
            buffer: 缓冲区内容
            
        Returns:
            修复后的JSON对象，如果无法修复则返回None
        """
        try:
            # 尝试添加缺失的括号和引号
            fixed_buffer = buffer.strip()
            
            # 修复未闭合的引号
            quote_count = fixed_buffer.count('"') - fixed_buffer.count('\\"')
            if quote_count % 2 != 0:
                fixed_buffer += '"'
            
            # 修复未闭合的括号
            open_count = fixed_buffer.count('{') - fixed_buffer.count('\\{')
            close_count = fixed_buffer.count('}') - fixed_buffer.count('\\}')
            
            for _ in range(open_count - close_count):
                fixed_buffer += '}'
            
            # 尝试解析修复后的JSON
            return json.loads(fixed_buffer)
            
        except (json.JSONDecodeError, ValueError):
            return None
    
    def reset(self):
        """重置解析器状态"""
        self.buffer = ""
        self.bracket_count = 0
        self.in_quotes = False
        self.escape_next = False


class MessageConverter:
    """消息转换器 - 处理内部消息和API消息之间的转换"""
    
    @staticmethod
    def agent_messages_to_api_messages(
        agent_messages: List[AgentMessage]
    ) -> List[APIMessage]:
        """将AgentMessage列表转换为APIMessage列表"""
        return [APIMessage.from_agent_message(msg) for msg in agent_messages]
    
    @staticmethod
    def build_conversation_context(
        system_prompt: str,
        user_query: str, 
        conversation_history: List[AgentMessage] = None
    ) -> List[APIMessage]:
        """
        构建完整的对话上下文
        
        Args:
            system_prompt: 系统提示
            user_query: 用户查询
            conversation_history: 对话历史
            
        Returns:
            完整的API消息列表
        """
        messages = []
        
        # 添加系统消息
        if system_prompt:
            messages.append(APIMessage.system_message(system_prompt))
        
        # 添加历史对话
        if conversation_history:
            for msg in conversation_history[-5:]:  # 只保留最近5条
                messages.append(APIMessage.from_agent_message(msg))
        
        # 添加当前用户查询
        messages.append(APIMessage.user_message(user_query))
        
        return messages
    
    @staticmethod
    def format_for_llm_call(api_messages: List[APIMessage]) -> List[Dict[str, str]]:
        """格式化为LLM调用格式"""
        return [msg.to_dict() for msg in api_messages]


# 便捷导出
__all__ = [
    "APIMessage",
    "StreamingJSONParser", 
    "MessageConverter"
]