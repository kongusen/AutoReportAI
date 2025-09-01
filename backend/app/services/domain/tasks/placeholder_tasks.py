"""
Domain层 - 占位符领域任务

占位符相关的核心业务逻辑任务
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from app.services.infrastructure.task_queue.celery_config import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name='tasks.domain.placeholder.analyze_semantic', bind=True)
def analyze_placeholder_semantic(self, placeholder_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    占位符语义分析
    
    Domain层核心业务逻辑：
    - 分析占位符的业务含义
    - 推断数据类型和来源
    - 评估业务重要性
    """
    logger.info(f"开始占位符语义分析: {placeholder_name}")
    
    try:
        # 语义分析业务逻辑
        semantic_analysis = {
            'business_category': _classify_business_category(placeholder_name),
            'data_type': _infer_data_type(placeholder_name),
            'source_system': _infer_source_system(placeholder_name),
            'business_priority': _calculate_business_priority(placeholder_name),
            'refresh_frequency': _suggest_refresh_frequency(placeholder_name),
            'dependencies': _analyze_business_dependencies(placeholder_name, context)
        }
        
        return {
            'success': True,
            'placeholder_name': placeholder_name,
            'semantic_analysis': semantic_analysis,
            'task_id': self.request.id,
            'analyzed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"占位符语义分析失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'placeholder_name': placeholder_name,
            'task_id': self.request.id
        }


def _classify_business_category(placeholder_name: str) -> str:
    """业务分类逻辑"""
    name_lower = placeholder_name.lower()
    
    # 财务相关
    if any(keyword in name_lower for keyword in ['revenue', 'profit', 'cost', 'budget', 'sales', 'income']):
        return 'financial'
    
    # 客户相关  
    elif any(keyword in name_lower for keyword in ['customer', 'client', 'user', 'member']):
        return 'customer'
        
    # 产品相关
    elif any(keyword in name_lower for keyword in ['product', 'item', 'inventory', 'stock']):
        return 'product'
        
    # 运营相关
    elif any(keyword in name_lower for keyword in ['order', 'delivery', 'shipping', 'logistics']):
        return 'operations'
        
    # 市场相关
    elif any(keyword in name_lower for keyword in ['marketing', 'campaign', 'advertisement', 'promotion']):
        return 'marketing'
        
    # HR相关
    elif any(keyword in name_lower for keyword in ['employee', 'staff', 'hr', 'salary']):
        return 'human_resources'
        
    else:
        return 'general'


def _infer_data_type(placeholder_name: str) -> str:
    """数据类型推断"""
    name_lower = placeholder_name.lower()
    
    # 图表类型
    if any(keyword in name_lower for keyword in ['chart', 'graph', 'plot', 'visualization']):
        return 'chart'
    
    # 数值类型
    elif any(keyword in name_lower for keyword in ['count', 'total', 'sum', 'average', 'rate', 'percentage']):
        return 'numeric'
        
    # 日期时间类型
    elif any(keyword in name_lower for keyword in ['date', 'time', 'timestamp', 'period']):
        return 'datetime'
        
    # 列表类型
    elif any(keyword in name_lower for keyword in ['list', 'items', 'records', 'entries']):
        return 'list'
        
    # 表格类型
    elif any(keyword in name_lower for keyword in ['table', 'grid', 'matrix']):
        return 'table'
        
    else:
        return 'text'


def _infer_source_system(placeholder_name: str) -> str:
    """数据来源系统推断"""
    name_lower = placeholder_name.lower()
    
    # CRM系统
    if any(keyword in name_lower for keyword in ['crm', 'customer', 'lead', 'opportunity']):
        return 'crm_system'
        
    # ERP系统
    elif any(keyword in name_lower for keyword in ['erp', 'inventory', 'procurement', 'manufacturing']):
        return 'erp_system'
        
    # 财务系统
    elif any(keyword in name_lower for keyword in ['finance', 'accounting', 'budget', 'gl']):
        return 'financial_system'
        
    # 电商系统
    elif any(keyword in name_lower for keyword in ['ecommerce', 'order', 'cart', 'payment']):
        return 'ecommerce_system'
        
    # 分析系统
    elif any(keyword in name_lower for keyword in ['analytics', 'bi', 'warehouse', 'olap']):
        return 'analytics_system'
        
    else:
        return 'unknown_system'


def _calculate_business_priority(placeholder_name: str) -> int:
    """业务优先级计算"""
    priority = 50  # 基础优先级
    name_lower = placeholder_name.lower()
    
    # 关键业务指标
    if any(keyword in name_lower for keyword in ['kpi', 'key', 'critical', 'important']):
        priority += 30
        
    # 高层关注指标
    elif any(keyword in name_lower for keyword in ['executive', 'ceo', 'management', 'strategic']):
        priority += 25
        
    # 财务指标
    elif any(keyword in name_lower for keyword in ['revenue', 'profit', 'roi', 'margin']):
        priority += 20
        
    # 客户指标
    elif any(keyword in name_lower for keyword in ['customer', 'satisfaction', 'retention']):
        priority += 15
        
    # 运营指标
    elif any(keyword in name_lower for keyword in ['efficiency', 'productivity', 'utilization']):
        priority += 10
        
    return min(priority, 100)


def _suggest_refresh_frequency(placeholder_name: str) -> str:
    """建议刷新频率"""
    name_lower = placeholder_name.lower()
    
    # 实时数据
    if any(keyword in name_lower for keyword in ['realtime', 'live', 'current', 'now']):
        return 'realtime'
        
    # 小时级数据
    elif any(keyword in name_lower for keyword in ['hourly', 'hour', 'alert', 'monitoring']):
        return 'hourly'
        
    # 日级数据
    elif any(keyword in name_lower for keyword in ['daily', 'today', 'yesterday']):
        return 'daily'
        
    # 周级数据
    elif any(keyword in name_lower for keyword in ['weekly', 'week', 'wtd']):
        return 'weekly'
        
    # 月级数据
    elif any(keyword in name_lower for keyword in ['monthly', 'month', 'mtd']):
        return 'monthly'
        
    else:
        return 'daily'  # 默认日刷新


def _analyze_business_dependencies(placeholder_name: str, context: Dict[str, Any]) -> List[str]:
    """业务依赖关系分析"""
    dependencies = []
    name_lower = placeholder_name.lower()
    
    # 从上下文中获取其他占位符
    other_placeholders = context.get('all_placeholders', [])
    
    for other_placeholder in other_placeholders:
        if other_placeholder == placeholder_name:
            continue
            
        other_lower = other_placeholder.lower()
        
        # 总计依赖明细
        if 'total' in name_lower and ('item' in other_lower or 'detail' in other_lower):
            dependencies.append(other_placeholder)
            
        # 图表依赖数据
        elif 'chart' in name_lower and any(keyword in other_lower for keyword in ['data', 'value', 'metric']):
            dependencies.append(other_placeholder)
            
        # 比率依赖基数
        elif any(keyword in name_lower for keyword in ['rate', 'ratio', 'percentage']) and 'total' in other_lower:
            dependencies.append(other_placeholder)
    
    return dependencies


@celery_app.task(name='tasks.domain.placeholder.validate_business_logic', bind=True)
def validate_placeholder_business_logic(self, placeholders: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    占位符业务逻辑验证
    
    验证占位符之间的业务逻辑一致性
    """
    logger.info(f"开始占位符业务逻辑验证，数量: {len(placeholders)}")
    
    try:
        validation_results = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'business_inconsistencies': []
        }
        
        # 业务逻辑检查
        placeholder_names = [p['name'] for p in placeholders]
        
        # 检查1: 财务数据一致性
        financial_placeholders = [p for p in placeholders if _classify_business_category(p['name']) == 'financial']
        if len(financial_placeholders) > 1:
            # 检查是否有收入和成本，但没有利润
            has_revenue = any('revenue' in p['name'].lower() for p in financial_placeholders)
            has_cost = any('cost' in p['name'].lower() for p in financial_placeholders)
            has_profit = any('profit' in p['name'].lower() for p in financial_placeholders)
            
            if has_revenue and has_cost and not has_profit:
                validation_results['warnings'].append('有收入和成本数据，建议添加利润指标')
        
        # 检查2: 图表数据完整性
        chart_placeholders = [p for p in placeholders if _infer_data_type(p['name']) == 'chart']
        for chart_placeholder in chart_placeholders:
            chart_name = chart_placeholder['name'].lower()
            # 检查是否有对应的数据源
            has_data_source = any(
                chart_name.replace('chart', '').replace('_chart', '') in other_name.lower()
                for other_name in placeholder_names
                if other_name != chart_placeholder['name']
            )
            if not has_data_source:
                validation_results['warnings'].append(f'图表 {chart_placeholder["name"]} 可能缺少数据源')
        
        # 检查3: 业务流程完整性
        process_keywords = {
            'order': ['order_count', 'order_value', 'order_status'],
            'customer': ['customer_count', 'customer_acquisition', 'customer_retention'],
            'product': ['product_sales', 'product_inventory', 'product_performance']
        }
        
        for process, expected_metrics in process_keywords.items():
            process_placeholders = [p for p in placeholders if process in p['name'].lower()]
            if process_placeholders:
                missing_metrics = [
                    metric for metric in expected_metrics
                    if not any(metric.replace('_', '') in p['name'].lower().replace('_', '') for p in process_placeholders)
                ]
                if missing_metrics:
                    validation_results['warnings'].append(f'{process} 流程可能缺少指标: {missing_metrics}')
        
        # 总体验证状态
        validation_results['is_valid'] = len(validation_results['errors']) == 0
        
        return {
            'success': True,
            'validation_results': validation_results,
            'placeholders_analyzed': len(placeholders),
            'task_id': self.request.id
        }
        
    except Exception as e:
        logger.error(f"占位符业务逻辑验证失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'task_id': self.request.id
        }