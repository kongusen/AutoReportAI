"""
Domain层 - 模板领域任务

模板相关的核心业务逻辑任务
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from app.services.infrastructure.task_queue.celery_config import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name='tasks.domain.template.validate_business_rules', bind=True)
def validate_template_business_rules(self, template_content: str, business_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证模板的业务规则
    
    Domain层核心业务逻辑：
    - 模板内容必须符合业务标准
    - 占位符命名必须遵循业务约定
    - 模板结构必须满足报告要求
    """
    logger.info(f"开始模板业务规则验证，任务ID: {self.request.id}")
    
    try:
        from app.services.domain.template.services.template_domain_service import TemplateDomainService
        
        # 使用领域服务进行业务验证
        domain_service = TemplateDomainService()
        validation_result = domain_service.validate_business_rules(template_content, business_context)
        
        return {
            'success': True,
            'validation_result': validation_result,
            'task_id': self.request.id,
            'processed_at': datetime.now().isoformat()
        }
        
    except ImportError:
        # 如果领域服务不存在，使用基础业务逻辑
        logger.warning("TemplateDomainService not available, using basic validation")
        
        validation_result = _basic_template_validation(template_content)
        
        return {
            'success': True,
            'validation_result': validation_result,
            'task_id': self.request.id,
            'note': 'Using basic validation logic'
        }
        
    except Exception as e:
        logger.error(f"模板业务规则验证失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'task_id': self.request.id
        }


def _basic_template_validation(template_content: str) -> Dict[str, Any]:
    """基础模板验证逻辑"""
    import re
    
    # 基本业务规则检查
    issues = []
    score = 100
    
    # 规则1: 内容不能为空
    if not template_content.strip():
        issues.append("模板内容为空")
        score -= 50
    
    # 规则2: 必须包含占位符
    placeholders = re.findall(r'\{\{([^}]+)\}\}', template_content)
    if not placeholders:
        issues.append("模板缺少占位符")
        score -= 30
    
    # 规则3: 占位符命名规范
    invalid_placeholders = [p for p in placeholders if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', p.strip())]
    if invalid_placeholders:
        issues.append(f"占位符命名不规范: {invalid_placeholders}")
        score -= 20
    
    return {
        'is_valid': len(issues) == 0,
        'score': max(score, 0),
        'issues': issues,
        'placeholders_count': len(placeholders)
    }


@celery_app.task(name='tasks.domain.template.analyze_complexity', bind=True)
def analyze_template_complexity(self, template_content: str) -> Dict[str, Any]:
    """
    分析模板复杂度
    
    Domain层业务逻辑：根据业务需求评估模板复杂度
    """
    logger.info(f"开始模板复杂度分析，任务ID: {self.request.id}")
    
    try:
        import re
        
        # 提取占位符
        placeholders = re.findall(r'\{\{([^}]+)\}\}', template_content)
        
        # 计算复杂度指标
        complexity_metrics = {
            'placeholder_count': len(placeholders),
            'content_length': len(template_content),
            'nested_structures': len(re.findall(r'\{\{.*\{\{.*\}\}.*\}\}', template_content)),
            'conditional_logic': len(re.findall(r'\{\{.*if.*\}\}', template_content, re.IGNORECASE)),
            'loop_structures': len(re.findall(r'\{\{.*for.*\}\}', template_content, re.IGNORECASE))
        }
        
        # 业务复杂度评分
        complexity_score = (
            complexity_metrics['placeholder_count'] * 2 +
            complexity_metrics['nested_structures'] * 10 +
            complexity_metrics['conditional_logic'] * 15 +
            complexity_metrics['loop_structures'] * 20
        )
        
        # 复杂度等级
        if complexity_score < 20:
            complexity_level = 'simple'
        elif complexity_score < 50:
            complexity_level = 'medium'
        elif complexity_score < 100:
            complexity_level = 'complex'
        else:
            complexity_level = 'very_complex'
        
        return {
            'success': True,
            'complexity_metrics': complexity_metrics,
            'complexity_score': complexity_score,
            'complexity_level': complexity_level,
            'recommendations': _get_complexity_recommendations(complexity_level),
            'task_id': self.request.id
        }
        
    except Exception as e:
        logger.error(f"模板复杂度分析失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'task_id': self.request.id
        }


def _get_complexity_recommendations(complexity_level: str) -> List[str]:
    """根据复杂度提供业务建议"""
    recommendations = {
        'simple': ['模板结构良好，适合快速生成报告'],
        'medium': ['考虑优化占位符命名', '可以添加更多业务逻辑'],
        'complex': ['建议拆分为多个子模板', '考虑使用模板继承', '增加文档说明'],
        'very_complex': ['强烈建议重构模板结构', '考虑使用组件化设计', '需要详细的技术文档']
    }
    return recommendations.get(complexity_level, [])