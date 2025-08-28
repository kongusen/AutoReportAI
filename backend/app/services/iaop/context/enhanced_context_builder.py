"""
增强的上下文构建器
集成任务系统的时间和数据周期上下文
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.task import Task, ReportPeriod
from app.models.template_placeholder import TemplatePlaceholder


class EnhancedContextBuilder:
    """增强的上下文构建器，集成任务系统的时间和数据周期"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def build_task_temporal_context(self, task_id: int) -> Dict[str, Any]:
        """
        构建任务的时间上下文
        从任务系统获取执行时间和数据周期范围
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {}
        
        # 计算数据周期范围
        current_time = datetime.now()
        period_ranges = self._calculate_period_ranges(task.report_period, current_time)
        
        temporal_context = {
            'task_id': task_id,
            'report_period': str(task.report_period),
            'execution_time': current_time.isoformat(),
            
            # 数据时间范围
            'data_start_date': period_ranges['start_date'].strftime('%Y-%m-%d'),
            'data_end_date': period_ranges['end_date'].strftime('%Y-%m-%d'),
            'period_description': period_ranges['description'],
            
            # 时间过滤条件（用于SQL生成）
            'time_filter_conditions': {
                'start_date_sql': f"'{period_ranges['start_date'].strftime('%Y-%m-%d')}'",
                'end_date_sql': f"'{period_ranges['end_date'].strftime('%Y-%m-%d')}'",
                'date_format': 'YYYY-MM-DD',
                'period_type': str(task.report_period)
            },
            
            # 业务上下文
            'business_context': {
                'is_current_period': True,
                'comparison_period_available': True,
                'period_length_days': (period_ranges['end_date'] - period_ranges['start_date']).days + 1
            }
        }
        
        return temporal_context
    
    def _calculate_period_ranges(self, report_period: str, current_time: datetime) -> Dict[str, Any]:
        """计算不同周期的数据范围"""
        
        if report_period == ReportPeriod.DAILY:
            start_date = current_time.date()
            end_date = start_date
            description = f"{start_date.strftime('%Y年%m月%d日')}日报"
        
        elif report_period == ReportPeriod.WEEKLY:
            # 本周（周一到今天）
            days_since_monday = current_time.weekday()
            start_date = (current_time - timedelta(days=days_since_monday)).date()
            end_date = current_time.date()
            description = f"{start_date.strftime('%Y年%m月%d日')}至{end_date.strftime('%m月%d日')}周报"
        
        elif report_period == ReportPeriod.MONTHLY:
            # 本月1号到今天
            start_date = current_time.replace(day=1).date()
            end_date = current_time.date()
            description = f"{start_date.strftime('%Y年%m月')}月报"
        
        elif report_period == ReportPeriod.YEARLY:
            # 本年1月1号到今天
            start_date = current_time.replace(month=1, day=1).date()
            end_date = current_time.date()
            description = f"{start_date.strftime('%Y年')}年报"
        
        else:
            # 默认为月报
            start_date = current_time.replace(day=1).date()
            end_date = current_time.date()
            description = f"{start_date.strftime('%Y年%m月')}月报"
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'description': description
        }
    
    def build_placeholder_business_context(self, placeholder_text: str, temporal_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建占位符的业务上下文
        结合时间周期信息为占位符提供更准确的分析上下文
        """
        
        business_context = {
            'placeholder_text': placeholder_text,
            'temporal_scope': temporal_context,
            
            # 业务意图分析
            'business_intent': self._analyze_business_intent(placeholder_text),
            
            # 时间相关的SQL提示
            'sql_time_hints': {
                'date_column_suggestions': ['dt', 'create_time', 'update_time', 'date', 'created_at', 'updated_at'],
                'time_filter_template': f"WHERE {{date_column}} >= '{temporal_context['data_start_date']}' AND {{date_column}} <= '{temporal_context['data_end_date']}'",
                'period_grouping': self._get_period_grouping_sql(temporal_context['report_period'])
            }
        }
        
        return business_context
    
    def _analyze_business_intent(self, placeholder_text: str) -> Dict[str, Any]:
        """分析占位符的业务意图"""
        
        intent_keywords = {
            'statistics': ['统计', '总数', '数量', '计数', 'count', 'total', '总计', '件数'],
            'trend': ['趋势', '变化', '增长', 'trend', 'growth', '同比', '环比'],
            'comparison': ['对比', '比较', '分析', 'compare', 'analysis', '占比'],
            'ranking': ['排名', '排行', 'top', '最大', '最小', 'rank', 'ranking'],
            'distribution': ['分布', '分类', '类型', 'distribution', 'category', 'type'],
            'time_series': ['周期', '时间', '日期', '月度', '年度', '季度']
        }
        
        detected_intents = []
        for intent, keywords in intent_keywords.items():
            if any(keyword in placeholder_text.lower() for keyword in keywords):
                detected_intents.append(intent)
        
        return {
            'detected_intents': detected_intents,
            'primary_intent': detected_intents[0] if detected_intents else 'statistics',
            'complexity': 'complex' if len(detected_intents) > 2 else 'simple'
        }
    
    def _get_period_grouping_sql(self, report_period: str) -> str:
        """根据报告周期生成SQL分组建议"""
        
        grouping_templates = {
            ReportPeriod.DAILY: "DATE({date_column})",
            ReportPeriod.WEEKLY: "YEARWEEK({date_column})",
            ReportPeriod.MONTHLY: "DATE_FORMAT({date_column}, '%Y-%m')",
            ReportPeriod.YEARLY: "YEAR({date_column})"
        }
        
        return grouping_templates.get(report_period, "DATE({date_column})")