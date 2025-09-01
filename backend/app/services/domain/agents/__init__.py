"""
Domain层Agent服务

Domain层的Agent专注于业务逻辑和领域知识：
1. 业务规则推理
2. 领域知识应用
3. 业务流程决策
4. 领域模型操作

不应包含：
- 技术实现细节（属于Infrastructure层）
- 工作流编排（属于Application层）
- 数据访问逻辑（属于Data层）
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .placeholder_analysis_agent import PlaceholderAnalysisAgent
    from .template_analysis_agent import TemplateAnalysisAgent
    from .business_rule_agent import BusinessRuleAgent

# 全局服务实例缓存
_domain_agent_instances = {}

async def get_placeholder_analysis_agent() -> 'PlaceholderAnalysisAgent':
    """获取占位符分析代理实例"""
    if 'placeholder_analysis' not in _domain_agent_instances:
        from .placeholder_analysis_agent import PlaceholderAnalysisAgent
        _domain_agent_instances['placeholder_analysis'] = PlaceholderAnalysisAgent()
    return _domain_agent_instances['placeholder_analysis']

async def get_template_analysis_agent() -> 'TemplateAnalysisAgent':
    """获取模板分析代理实例"""
    if 'template_analysis' not in _domain_agent_instances:
        from .template_analysis_agent import TemplateAnalysisAgent
        _domain_agent_instances['template_analysis'] = TemplateAnalysisAgent()
    return _domain_agent_instances['template_analysis']

async def get_business_rule_agent() -> 'BusinessRuleAgent':
    """获取业务规则代理实例"""
    if 'business_rule' not in _domain_agent_instances:
        from .business_rule_agent import BusinessRuleAgent
        _domain_agent_instances['business_rule'] = BusinessRuleAgent()
    return _domain_agent_instances['business_rule']

async def get_report_generation_agent():
    """获取报告生成代理实例 - 重用现有的报告生成服务"""
    from ..reporting.services.report_generation_domain_service import get_report_generation_domain_service
    return await get_report_generation_domain_service()

__all__ = [
    'get_placeholder_analysis_agent',
    'get_template_analysis_agent',
    'get_business_rule_agent',
    'get_report_generation_agent'
]