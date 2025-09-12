"""
LLM工具模块 - 桥接agents和LLM服务
提供智能模型选择和任务执行能力
"""

from .llm_execution_tool import (
    LLMExecutionTool,
    LLMTaskType,
    create_llm_execution_tool
)

from .llm_reasoning_tool import (
    LLMReasoningTool,
    ReasoningDepth,
    create_llm_reasoning_tool
)

# 全局工具实例
_llm_execution_tool = None
_llm_reasoning_tool = None


def get_llm_execution_tool() -> LLMExecutionTool:
    """获取LLM执行工具实例"""
    global _llm_execution_tool
    if _llm_execution_tool is None:
        _llm_execution_tool = create_llm_execution_tool()
    return _llm_execution_tool


def get_llm_reasoning_tool() -> LLMReasoningTool:
    """获取LLM推理工具实例"""
    global _llm_reasoning_tool
    if _llm_reasoning_tool is None:
        _llm_reasoning_tool = create_llm_reasoning_tool()
    return _llm_reasoning_tool


def get_all_llm_tools() -> dict:
    """获取所有LLM工具"""
    return {
        'llm_execution': get_llm_execution_tool(),
        'llm_reasoning': get_llm_reasoning_tool()
    }


# 导出所有组件
__all__ = [
    # 工具类
    'LLMExecutionTool',
    'LLMReasoningTool',
    
    # 枚举类型
    'LLMTaskType',
    'ReasoningDepth',
    
    # 工厂函数
    'create_llm_execution_tool',
    'create_llm_reasoning_tool',
    
    # 实例获取
    'get_llm_execution_tool',
    'get_llm_reasoning_tool',
    'get_all_llm_tools'
]