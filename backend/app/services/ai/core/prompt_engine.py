"""
Context-Aware Prompt Engineering Engine

上下文感知的提示工程引擎，支持：
1. 动态提示模板构建
2. 上下文感知的提示生成
3. 多轮对话管理
4. 提示优化和调试
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from jinja2 import Template, Environment, BaseLoader

from .context_manager import AgentContext, ContextScope

logger = logging.getLogger(__name__)


class PromptType(Enum):
    """提示类型"""
    SYSTEM = "system"
    USER = "user" 
    ASSISTANT = "assistant"
    FUNCTION = "function"


@dataclass
class PromptTemplate:
    """提示模板"""
    name: str
    template: str
    prompt_type: PromptType
    required_context: List[str] = field(default_factory=list)
    optional_context: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def render(self, context: Dict[str, Any]) -> str:
        """渲染模板"""
        # 检查必需的上下文
        missing_context = [key for key in self.required_context if key not in context]
        if missing_context:
            raise ValueError(f"Missing required context: {missing_context}")
        
        # 使用Jinja2渲染
        template = Template(self.template)
        return template.render(**context)


@dataclass
class ConversationTurn:
    """对话轮次"""
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


class ConversationManager:
    """对话管理器"""
    
    def __init__(self, max_history: int = 50):
        self.conversations: Dict[str, List[ConversationTurn]] = {}
        self.max_history = max_history
    
    def add_turn(self, session_id: str, role: str, content: str, 
                metadata: Dict[str, Any] = None):
        """添加对话轮次"""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        
        turn = ConversationTurn(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        self.conversations[session_id].append(turn)
        
        # 保持历史记录在合理范围内
        if len(self.conversations[session_id]) > self.max_history:
            self.conversations[session_id] = self.conversations[session_id][-self.max_history//2:]
    
    def get_conversation(self, session_id: str, 
                        limit: Optional[int] = None) -> List[ConversationTurn]:
        """获取对话历史"""
        conversation = self.conversations.get(session_id, [])
        if limit:
            return conversation[-limit:]
        return conversation
    
    def format_for_llm(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """格式化为LLM输入格式"""
        conversation = self.get_conversation(session_id, limit)
        return [{'role': turn.role, 'content': turn.content} for turn in conversation]
    
    def clear_conversation(self, session_id: str):
        """清空对话历史"""
        if session_id in self.conversations:
            del self.conversations[session_id]


class PromptEngine:
    """提示工程引擎"""
    
    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self.conversation_manager = ConversationManager()
        self._prompt_processors: List[Callable] = []
        self._context_extractors: Dict[str, Callable] = {}
        
        # 初始化Jinja2环境
        self.jinja_env = Environment(loader=BaseLoader())
        self._register_custom_filters()
    
    def _register_custom_filters(self):
        """注册自定义过滤器"""
        def truncate_text(text: str, max_length: int = 1000) -> str:
            if len(text) <= max_length:
                return text
            return text[:max_length] + "..."
        
        def format_json(obj: Any, indent: int = 2) -> str:
            return json.dumps(obj, indent=indent, ensure_ascii=False)
        
        def format_list(items: List[Any], separator: str = ", ") -> str:
            return separator.join(str(item) for item in items)
        
        self.jinja_env.filters['truncate'] = truncate_text
        self.jinja_env.filters['format_json'] = format_json
        self.jinja_env.filters['format_list'] = format_list
    
    def register_template(self, template: PromptTemplate):
        """注册提示模板"""
        self.templates[template.name] = template
    
    def register_templates_from_dict(self, templates_dict: Dict[str, Dict[str, Any]]):
        """从字典批量注册模板"""
        for name, template_data in templates_dict.items():
            template = PromptTemplate(
                name=name,
                template=template_data['template'],
                prompt_type=PromptType(template_data.get('type', 'user')),
                required_context=template_data.get('required_context', []),
                optional_context=template_data.get('optional_context', []),
                metadata=template_data.get('metadata', {})
            )
            self.register_template(template)
    
    def register_context_extractor(self, context_key: str, extractor: Callable):
        """注册上下文提取器"""
        self._context_extractors[context_key] = extractor
    
    def extract_dynamic_context(self, agent_context: AgentContext) -> Dict[str, Any]:
        """提取动态上下文"""
        dynamic_context = {}
        
        # 应用上下文提取器
        for key, extractor in self._context_extractors.items():
            try:
                dynamic_context[key] = extractor(agent_context)
            except Exception as e:
                logger.warning(f"Context extractor '{key}' failed: {e}")
        
        return dynamic_context
    
    def build_context_dict(self, agent_context: AgentContext, 
                          additional_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """构建完整的上下文字典"""
        # 基础上下文
        context_dict = {
            'session_id': agent_context.session_id,
            'task_id': agent_context.task_id,
            'user_id': agent_context.user_id,
            'timestamp': datetime.now().isoformat()
        }
        
        # Agent上下文数据
        for key, entry in agent_context.entries.items():
            context_dict[key] = entry.value
        
        # 动态上下文
        dynamic_context = self.extract_dynamic_context(agent_context)
        context_dict.update(dynamic_context)
        
        # 额外上下文
        if additional_context:
            context_dict.update(additional_context)
        
        # 对话历史
        conversation_history = self.conversation_manager.get_conversation(
            agent_context.session_id, limit=10
        )
        context_dict['conversation_history'] = [turn.to_dict() for turn in conversation_history]
        
        return context_dict
    
    def generate_prompt(self, template_name: str, agent_context: AgentContext,
                       additional_context: Dict[str, Any] = None) -> str:
        """生成上下文感知的提示"""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        context_dict = self.build_context_dict(agent_context, additional_context)
        
        # 应用提示处理器
        for processor in self._prompt_processors:
            try:
                context_dict = processor(context_dict, template)
            except Exception as e:
                logger.warning(f"Prompt processor failed: {e}")
        
        # 渲染提示
        prompt = template.render(context_dict)
        
        # 记录对话
        if template.prompt_type in [PromptType.USER, PromptType.SYSTEM]:
            self.conversation_manager.add_turn(
                session_id=agent_context.session_id,
                role=template.prompt_type.value,
                content=prompt,
                metadata={'template_name': template_name}
            )
        
        return prompt
    
    def generate_multi_turn_prompt(self, session_id: str, turns: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """生成多轮对话提示"""
        formatted_turns = []
        
        for turn in turns:
            role = turn.get('role', 'user')
            content = turn.get('content', '')
            
            # 记录对话轮次
            self.conversation_manager.add_turn(session_id, role, content)
            
            formatted_turns.append({
                'role': role,
                'content': content
            })
        
        return formatted_turns
    
    def register_prompt_processor(self, processor: Callable):
        """注册提示处理器"""
        self._prompt_processors.append(processor)
    
    def analyze_prompt_quality(self, prompt: str) -> Dict[str, Any]:
        """分析提示质量"""
        analysis = {
            'length': len(prompt),
            'word_count': len(prompt.split()),
            'has_instructions': bool(re.search(r'(请|Please|分析|analyze|生成|generate)', prompt, re.IGNORECASE)),
            'has_context': bool(re.search(r'(根据|based on|考虑|considering)', prompt, re.IGNORECASE)),
            'has_examples': bool(re.search(r'(例如|for example|示例|sample)', prompt, re.IGNORECASE)),
            'complexity_score': self._calculate_complexity_score(prompt)
        }
        
        return analysis
    
    def _calculate_complexity_score(self, prompt: str) -> float:
        """计算提示复杂度分数"""
        # 简单的复杂度评估
        factors = {
            'length': min(len(prompt) / 1000, 1.0),  # 长度因子
            'structure': len(re.findall(r'[.!?]', prompt)) / 10,  # 结构因子
            'context_refs': len(re.findall(r'\{\{|\}\}', prompt)) / 5,  # 上下文引用因子
        }
        
        return sum(factors.values()) / len(factors)


# 默认提示模板
DEFAULT_TEMPLATES = {
    'sql_analysis_system': {
        'template': '''你是一个专业的数据库分析专家。你的任务是根据用户需求和数据源信息生成准确的SQL查询。

当前上下文信息：
- 用户ID: {{ user_id }}
- 数据源类型: {{ data_source_type }}
- 可用表: {{ available_tables | format_list }}
- 时间戳: {{ timestamp }}

请遵循以下原则：
1. 生成高效、准确的SQL查询
2. 考虑数据源的特性和限制
3. 提供查询解释和优化建议
4. 确保查询安全性，避免SQL注入

{% if conversation_history %}
对话历史：
{% for turn in conversation_history[-3:] %}
- {{ turn.role }}: {{ turn.content | truncate(200) }}
{% endfor %}
{% endif %}''',
        'type': 'system',
        'required_context': ['user_id', 'data_source_type'],
        'optional_context': ['available_tables', 'conversation_history']
    },
    
    'placeholder_analysis': {
        'template': '''请分析以下占位符的含义和数据需求：

占位符: {{ placeholder_text }}
模板上下文: {{ template_context }}

{% if schema_info %}
相关数据库schema信息：
{{ schema_info | format_json }}
{% endif %}

请提供：
1. 占位符的业务含义解析
2. 推荐的数据源和表
3. 建议的SQL查询逻辑
4. 数据处理建议

输出格式要求：JSON格式，包含analysis、recommendations、sql_logic、data_processing字段。''',
        'type': 'user',
        'required_context': ['placeholder_text'],
        'optional_context': ['template_context', 'schema_info']
    }
}


def create_default_prompt_engine() -> PromptEngine:
    """创建默认配置的提示引擎"""
    engine = PromptEngine()
    engine.register_templates_from_dict(DEFAULT_TEMPLATES)
    
    # 注册默认的上下文提取器
    def extract_execution_summary(context: AgentContext) -> str:
        """提取执行摘要"""
        recent_executions = context.execution_history[-5:] if context.execution_history else []
        if not recent_executions:
            return "无历史执行记录"
        
        return f"最近执行了{len(recent_executions)}个操作，最后一次操作：{recent_executions[-1].get('action', 'unknown')}"
    
    engine.register_context_extractor('execution_summary', extract_execution_summary)
    
    return engine