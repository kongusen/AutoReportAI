"""
Agent Message Processor
======================

实现类似Claude Code的结构化消息处理流程
将用户输入转换为结构化的LLM消息格式
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

from .message_types import AgentMessage, MessageType, MessagePriority, MessageMetadata
from ..context.context_builder import AgentContext, ContextType
from ...llm import TaskRequirement, TaskComplexity, ProcessingStep

logger = logging.getLogger(__name__)


class InputType(Enum):
    """输入类型检测"""
    USER_TEXT = "user_text"           # 普通用户文本
    COMMAND = "command"               # /命令
    SHELL_COMMAND = "shell_command"   # !shell命令
    MEMORY_NOTE = "memory_note"       # #内存笔记
    PASTED_CONTENT = "pasted_content" # 粘贴的内容
    STRUCTURED_DATA = "structured_data" # 结构化数据


class ContentType(Enum):
    """内容类型"""
    TEXT = "text"
    IMAGE = "image"
    JSON = "json"
    CODE = "code"
    SQL = "sql"
    TABLE_DATA = "table_data"


@dataclass
class ProcessedContent:
    """处理后的内容块"""
    content_type: ContentType
    content: Any
    metadata: Dict[str, Any]
    token_count: Optional[int] = None


@dataclass
class StructuredMessage:
    """结构化消息 - 发送给LLM的最终格式"""
    message_id: str
    user_id: str
    task_type: str
    context: AgentContext
    processed_content: List[ProcessedContent]
    requirements: TaskRequirement
    complexity: TaskComplexity
    processing_step: ProcessingStep
    metadata: MessageMetadata
    
    # Token管理
    total_tokens: int = 0
    is_compacted: bool = False
    
    def to_llm_format(self) -> Dict[str, Any]:
        """转换为LLM API格式"""
        return {
            "message_id": self.message_id,
            "user_id": self.user_id,
            "task": {
                "type": self.task_type,
                "complexity": self.complexity.value,
                "step": self.processing_step.value,
                "requirements": asdict(self.requirements)
            },
            "context": {
                "type": self.context.context_type.value if self.context.context_type else "general",
                "task_name": self.context.task_info.task_name if self.context.task_info else "unknown",
                "task_description": self.context.task_info.description if self.context.task_info else "",
                "placeholders": self.context.resolved_placeholders,
                "schema_info": [asdict(schema) for schema in self.context.database_schemas] if self.context.database_schemas else []
            },
            "content": [
                {
                    "type": content.content_type.value,
                    "data": content.content,
                    "metadata": content.metadata,
                    "tokens": content.token_count
                }
                for content in self.processed_content
            ],
            "metadata": {
                "total_tokens": self.total_tokens,
                "is_compacted": self.is_compacted,
                "created_at": self.metadata.created_at.isoformat(),
                "correlation_id": self.metadata.correlation_id,
                "priority": self.metadata.headers.get("priority", "normal")
            }
        }


class MessageProcessor:
    """消息处理器 - 实现Claude Code风格的消息转换流程"""
    
    def __init__(self, token_limit: int = 8000):
        self.token_limit = token_limit
        self.content_detectors = {
            "image": self._detect_image_content,
            "json": self._detect_json_content,
            "sql": self._detect_sql_content,
            "code": self._detect_code_content,
        }
    
    async def process_user_input(
        self,
        user_input: str,
        user_id: str,
        context: AgentContext,
        task_requirements: Optional[TaskRequirement] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StructuredMessage:
        """
        处理用户输入 - 类似Claude Code的Input Processing阶段
        
        Args:
            user_input: 原始用户输入
            user_id: 用户ID
            context: Agent上下文
            task_requirements: 任务要求
            metadata: 额外元数据
        
        Returns:
            StructuredMessage: 结构化消息
        """
        
        # 1. 输入类型检测
        input_type = self._detect_input_type(user_input)
        logger.info(f"检测到输入类型: {input_type.value}")
        
        # 2. 内容处理
        processed_contents = await self._process_content(user_input, input_type)
        
        # 3. 任务分析
        complexity, processing_step = self._analyze_task_complexity(user_input, context)
        
        # 4. 构建结构化消息
        message_metadata = MessageMetadata()
        if metadata:
            message_metadata.headers.update(metadata)
        
        structured_message = StructuredMessage(
            message_id=message_metadata.correlation_id,
            user_id=user_id,
            task_type=context.context_type.value if context.context_type else "general",
            context=context,
            processed_content=processed_contents,
            requirements=task_requirements or TaskRequirement(),
            complexity=complexity,
            processing_step=processing_step,
            metadata=message_metadata
        )
        
        # 5. Token计算和压缩
        await self._calculate_tokens(structured_message)
        
        if structured_message.total_tokens > self.token_limit:
            await self._compact_message(structured_message)
        
        logger.info(f"消息处理完成: {structured_message.total_tokens} tokens")
        
        return structured_message
    
    def _detect_input_type(self, user_input: str) -> InputType:
        """输入类型检测 - 类似Claude Code的命令检测"""
        user_input = user_input.strip()
        
        if user_input.startswith('/'):
            return InputType.COMMAND
        elif user_input.startswith('!'):
            return InputType.SHELL_COMMAND
        elif user_input.startswith('#'):
            return InputType.MEMORY_NOTE
        elif self._is_structured_data(user_input):
            return InputType.STRUCTURED_DATA
        elif len(user_input) > 1000 and ('\n' in user_input or '\t' in user_input):
            return InputType.PASTED_CONTENT
        else:
            return InputType.USER_TEXT
    
    async def _process_content(self, user_input: str, input_type: InputType) -> List[ProcessedContent]:
        """内容处理 - 类似Claude Code的Content Detection"""
        contents = []
        
        if input_type == InputType.COMMAND:
            # 处理命令
            content = ProcessedContent(
                content_type=ContentType.TEXT,
                content=user_input[1:],  # 移除/前缀
                metadata={"is_command": True, "command": user_input.split()[0][1:]}
            )
            contents.append(content)
            
        elif input_type == InputType.STRUCTURED_DATA:
            # 检测结构化数据类型
            detected_type = self._detect_content_type(user_input)
            content = ProcessedContent(
                content_type=detected_type,
                content=user_input,
                metadata={"detected_format": detected_type.value}
            )
            contents.append(content)
            
        elif input_type == InputType.PASTED_CONTENT:
            # 分析粘贴内容
            lines = user_input.split('\n')
            if self._is_table_data(lines):
                content = ProcessedContent(
                    content_type=ContentType.TABLE_DATA,
                    content=self._parse_table_data(lines),
                    metadata={"rows": len(lines), "columns": len(lines[0].split('\t')) if lines else 0}
                )
            else:
                content = ProcessedContent(
                    content_type=ContentType.TEXT,
                    content=user_input,
                    metadata={"is_pasted": True, "length": len(user_input)}
                )
            contents.append(content)
            
        else:
            # 普通文本
            content = ProcessedContent(
                content_type=ContentType.TEXT,
                content=user_input,
                metadata={"length": len(user_input)}
            )
            contents.append(content)
        
        return contents
    
    def _analyze_task_complexity(self, user_input: str, context: AgentContext) -> Tuple[TaskComplexity, ProcessingStep]:
        """任务复杂度分析"""
        # 基于内容长度和关键词判断复杂度
        complexity = TaskComplexity.LOW
        step = ProcessingStep.GENERAL_REASONING
        
        keywords_analysis = {
            'sql': (TaskComplexity.HIGH, ProcessingStep.SQL_GENERATION),
            'query': (TaskComplexity.MEDIUM, ProcessingStep.SQL_GENERATION),
            'report': (TaskComplexity.HIGH, ProcessingStep.CONTEXT_ANALYSIS),
            'chart': (TaskComplexity.MEDIUM, ProcessingStep.CHART_SPEC_GENERATION),
            'analysis': (TaskComplexity.MEDIUM, ProcessingStep.DATA_SOURCE_ANALYSIS),
            'etl': (TaskComplexity.HIGH, ProcessingStep.ETL_DATA_PROCESSING),
        }
        
        user_lower = user_input.lower()
        for keyword, (comp, step_type) in keywords_analysis.items():
            if keyword in user_lower:
                complexity = comp
                step = step_type
                break
        
        # 基于长度调整复杂度
        if len(user_input) > 500:
            complexity = TaskComplexity.MEDIUM if complexity == TaskComplexity.LOW else TaskComplexity.HIGH
        
        return complexity, step
    
    async def _calculate_tokens(self, message: StructuredMessage):
        """Token计算 - 简化版本"""
        total_tokens = 0
        
        for content in message.processed_content:
            # 简化的token计算 (实际应该使用tokenizer)
            if isinstance(content.content, str):
                content.token_count = len(content.content.split()) * 1.3  # 粗略估算
            elif isinstance(content.content, dict):
                content.token_count = len(str(content.content)) * 0.3
            else:
                content.token_count = 50  # 默认
            
            total_tokens += content.token_count
        
        # 添加上下文和元数据的token
        context_tokens = 0
        if message.context.task_info and message.context.task_info.description:
            context_tokens = len(str(message.context.task_info.description).split()) * 1.3
        total_tokens += context_tokens + 100  # 元数据开销
        
        message.total_tokens = int(total_tokens)
    
    async def _compact_message(self, message: StructuredMessage):
        """消息压缩 - 类似Claude Code的Compaction Process"""
        logger.info(f"开始压缩消息: {message.total_tokens} tokens")
        
        # 1. 优先压缩大内容块
        for content in message.processed_content:
            if content.token_count and content.token_count > 200:
                if content.content_type == ContentType.TEXT:
                    # 截断长文本
                    original = content.content
                    content.content = original[:500] + "...[truncated]"
                    content.metadata["truncated"] = True
                    content.metadata["original_length"] = len(original)
                
                elif content.content_type == ContentType.TABLE_DATA:
                    # 表格数据采样
                    if isinstance(content.content, list) and len(content.content) > 10:
                        content.content = content.content[:5] + ["...[more rows]"] + content.content[-2:]
                        content.metadata["sampled"] = True
        
        # 2. 重新计算tokens
        await self._calculate_tokens(message)
        message.is_compacted = True
        
        logger.info(f"压缩完成: {message.total_tokens} tokens")
    
    # 辅助检测方法
    def _detect_content_type(self, content: str) -> ContentType:
        """内容类型检测"""
        content_lower = content.strip().lower()
        
        if content_lower.startswith(('select', 'insert', 'update', 'delete', 'create', 'alter')):
            return ContentType.SQL
        elif content_lower.startswith(('{', '[')):
            return ContentType.JSON
        elif any(keyword in content_lower for keyword in ['def ', 'function', 'class ', 'import ']):
            return ContentType.CODE
        else:
            return ContentType.TEXT
    
    def _is_structured_data(self, content: str) -> bool:
        """判断是否为结构化数据"""
        return any([
            content.strip().startswith(('{', '[')),
            content.lower().strip().startswith(('select', 'insert', 'update')),
            '\t' in content and '\n' in content,  # 可能是表格数据
        ])
    
    def _detect_image_content(self, content: str) -> bool:
        """图片内容检测"""
        return False  # 暂不支持
    
    def _detect_json_content(self, content: str) -> bool:
        """JSON内容检测"""
        try:
            json.loads(content.strip())
            return True
        except:
            return False
    
    def _detect_sql_content(self, content: str) -> bool:
        """SQL内容检测"""
        sql_keywords = ['select', 'insert', 'update', 'delete', 'create', 'alter', 'drop']
        return any(content.lower().strip().startswith(keyword) for keyword in sql_keywords)
    
    def _detect_code_content(self, content: str) -> bool:
        """代码内容检测"""
        code_indicators = ['def ', 'function', 'class ', 'import ', 'from ', '<?php', '<script']
        return any(indicator in content.lower() for indicator in code_indicators)
    
    def _is_table_data(self, lines: List[str]) -> bool:
        """判断是否为表格数据"""
        if len(lines) < 2:
            return False
        
        # 检查是否有一致的分隔符
        first_line_tabs = lines[0].count('\t')
        first_line_commas = lines[0].count(',')
        
        if first_line_tabs > 0:
            return all(line.count('\t') == first_line_tabs for line in lines[:5])
        elif first_line_commas > 0:
            return all(line.count(',') == first_line_commas for line in lines[:5])
        
        return False
    
    def _parse_table_data(self, lines: List[str]) -> List[List[str]]:
        """解析表格数据"""
        delimiter = '\t' if '\t' in lines[0] else ','
        return [line.split(delimiter) for line in lines if line.strip()]


# 便捷函数
async def process_user_message(
    user_input: str,
    user_id: str,
    context: AgentContext,
    task_requirements: Optional[TaskRequirement] = None
) -> StructuredMessage:
    """处理用户消息的便捷函数"""
    processor = MessageProcessor()
    return await processor.process_user_input(user_input, user_id, context, task_requirements)