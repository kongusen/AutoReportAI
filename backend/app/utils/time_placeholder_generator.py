"""
时间占位符生成工具类

用于在占位符分析过程中生成时间占位符，支持不同时间周期的占位符生成
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from app.utils.time_context import TimeContextManager

logger = logging.getLogger(__name__)


class TimePlaceholderGenerator:
    """
    时间占位符生成器
    
    负责在占位符分析过程中生成时间占位符，支持：
    1. 基于时间窗口生成占位符
    2. 基于cron表达式生成占位符
    3. 基于执行时间生成占位符
    4. 支持多种时间格式和周期
    """
    
    def __init__(self):
        self.time_manager = TimeContextManager()
    
    def generate_time_placeholders(
        self,
        time_window: Optional[Dict[str, str]] = None,
        cron_expression: Optional[str] = None,
        execution_time: Optional[datetime] = None,
        data_range: str = "day",
        time_column: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成时间占位符
        
        Args:
            time_window: 时间窗口，包含start_date和end_date
            cron_expression: cron表达式
            execution_time: 执行时间
            data_range: 数据范围 (day, week, month, quarter, year)
            time_column: 时间列名
            
        Returns:
            包含时间占位符信息的字典
        """
        logger.info(f"🕐 开始生成时间占位符 - data_range: {data_range}, time_column: {time_column}")
        
        try:
            # 1. 构建时间上下文
            time_context = self._build_time_context(
                time_window, cron_expression, execution_time, data_range
            )
            
            # 2. 生成基础时间占位符
            basic_placeholders = self._generate_basic_placeholders(time_context)
            
            # 3. 生成SQL时间占位符
            sql_placeholders = self._generate_sql_placeholders(time_context, time_column)
            
            # 4. 生成时间范围占位符
            range_placeholders = self._generate_range_placeholders(time_context)
            
            # 5. 生成周期相关占位符
            period_placeholders = self._generate_period_placeholders(time_context, data_range)
            
            # 6. 合并所有占位符
            all_placeholders = {
                **basic_placeholders,
                **sql_placeholders,
                **range_placeholders,
                **period_placeholders
            }
            
            result = {
                'time_placeholders': all_placeholders,
                'time_context': time_context,
                'time_column': time_column,
                'data_range': data_range,
                'generated_at': datetime.now().isoformat(),
                'placeholder_count': len(all_placeholders)
            }
            
            logger.info(f"✅ 时间占位符生成完成 - 共生成 {len(all_placeholders)} 个占位符")
            return result
            
        except Exception as e:
            logger.error(f"❌ 时间占位符生成失败: {e}", exc_info=True)
            return {
                'time_placeholders': {},
                'time_context': {},
                'error': str(e),
                'generated_at': datetime.now().isoformat(),
                'placeholder_count': 0
            }
    
    def _build_time_context(
        self,
        time_window: Optional[Dict[str, str]] = None,
        cron_expression: Optional[str] = None,
        execution_time: Optional[datetime] = None,
        data_range: str = "day"
    ) -> Dict[str, Any]:
        """构建时间上下文"""
        
        # 如果有cron表达式和执行时间，使用TimeContextManager
        if cron_expression and execution_time:
            try:
                context = self.time_manager.build_task_time_context(cron_expression, execution_time)
                if isinstance(context, dict):
                    return context
            except Exception as e:
                logger.warning(f"使用TimeContextManager构建时间上下文失败: {e}")
        
        # 如果有时间窗口，直接使用
        if time_window and isinstance(time_window, dict):
            start_date = time_window.get('start_date') or time_window.get('data_start_time')
            end_date = time_window.get('end_date') or time_window.get('data_end_time')
            
            if start_date and end_date:
                return {
                    'data_start_time': start_date,
                    'data_end_time': end_date,
                    'execution_time': execution_time.isoformat() if execution_time else datetime.now().isoformat(),
                    'period': data_range
                }
        
        # 默认回退：使用当前时间
        now = datetime.now()
        if data_range == "day":
            start_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
            end_date = start_date
        elif data_range == "week":
            start_date = (now - timedelta(days=7)).strftime('%Y-%m-%d')
            end_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        elif data_range == "month":
            start_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            start_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
            end_date = start_date
        
        return {
            'data_start_time': start_date,
            'data_end_time': end_date,
            'execution_time': now.isoformat(),
            'period': data_range
        }
    
    def _generate_basic_placeholders(self, time_context: Dict[str, Any]) -> Dict[str, str]:
        """生成基础时间占位符"""
        placeholders = {}
        
        # 基础时间占位符
        if 'data_start_time' in time_context:
            placeholders['start_date'] = time_context['data_start_time']
            placeholders['period_start_date'] = time_context['data_start_time']
        
        if 'data_end_time' in time_context:
            placeholders['end_date'] = time_context['data_end_time']
            placeholders['period_end_date'] = time_context['data_end_time']
        
        if 'execution_time' in time_context:
            exec_time = time_context['execution_time']
            if isinstance(exec_time, str) and 'T' in exec_time:
                exec_date = exec_time.split('T')[0]
            else:
                exec_date = str(exec_time)
            placeholders['execution_date'] = exec_date
            placeholders['current_date'] = exec_date
        
        return placeholders
    
    def _generate_sql_placeholders(self, time_context: Dict[str, Any], time_column: Optional[str] = None) -> Dict[str, str]:
        """生成SQL时间占位符"""
        placeholders = {}
        
        if not time_column:
            return placeholders
        
        # 基于时间列生成SQL占位符
        if 'data_start_time' in time_context and 'data_end_time' in time_context:
            start_time = time_context['data_start_time']
            end_time = time_context['data_end_time']
            
            # 单日期过滤
            if start_time == end_time:
                placeholders[f'{time_column}_filter'] = f"{time_column} = '{{{{start_date}}}}'"
                placeholders[f'{time_column}_equals'] = f"{time_column} = '{{{{start_date}}}}'"
            else:
                # 日期范围过滤
                placeholders[f'{time_column}_filter'] = f"{time_column} BETWEEN '{{{{start_date}}}}' AND '{{{{end_date}}}}'"
                placeholders[f'{time_column}_between'] = f"{time_column} BETWEEN '{{{{start_date}}}}' AND '{{{{end_date}}}}'"
                placeholders[f'{time_column}_range'] = f"{time_column} >= '{{{{start_date}}}}' AND {time_column} <= '{{{{end_date}}}}'"
        
        return placeholders
    
    def _generate_range_placeholders(self, time_context: Dict[str, Any]) -> Dict[str, str]:
        """生成时间范围占位符"""
        placeholders = {}
        
        if 'data_start_time' in time_context and 'data_end_time' in time_context:
            start_time = time_context['data_start_time']
            end_time = time_context['data_end_time']
            
            # 时间范围描述
            if start_time == end_time:
                placeholders['time_range'] = start_time
                placeholders['period_description'] = f"数据日期: {start_time}"
            else:
                placeholders['time_range'] = f"{start_time} 至 {end_time}"
                placeholders['period_description'] = f"数据期间: {start_time} 至 {end_time}"
                placeholders['date_range'] = f"{start_time}～{end_time}"
        
        return placeholders
    
    def _generate_period_placeholders(self, time_context: Dict[str, Any], data_range: str) -> Dict[str, str]:
        """生成周期相关占位符"""
        placeholders = {}
        
        # 周期描述
        period_descriptions = {
            'day': '日',
            'week': '周',
            'month': '月',
            'quarter': '季度',
            'year': '年'
        }
        
        period_name = period_descriptions.get(data_range, '日')
        placeholders['period_type'] = period_name
        placeholders['data_range'] = data_range
        
        # 基于周期生成特定占位符
        if data_range == 'day':
            placeholders['daily_period'] = 'true'
            placeholders['day_period'] = 'true'
            placeholders['period_key'] = 'daily'
        elif data_range == 'week':
            placeholders['weekly_period'] = 'true'
            placeholders['week_period'] = 'true'
            placeholders['period_key'] = 'weekly'
        elif data_range == 'month':
            placeholders['monthly_period'] = 'true'
            placeholders['month_period'] = 'true'
            placeholders['period_key'] = 'monthly'
        elif data_range == 'quarter':
            placeholders['quarterly_period'] = 'true'
            placeholders['quarter_period'] = 'true'
            placeholders['period_key'] = 'quarterly'
        elif data_range == 'year':
            placeholders['yearly_period'] = 'true'
            placeholders['year_period'] = 'true'
            placeholders['period_key'] = 'yearly'
        
        return placeholders
    
    def extract_time_placeholders_from_sql(self, sql: str) -> List[str]:
        """
        从SQL中提取时间占位符
        
        Args:
            sql: SQL字符串
            
        Returns:
            时间占位符列表
        """
        if not sql:
            return []
        
        # 匹配 {{placeholder}} 格式的占位符
        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, sql)
        
        # 过滤出时间相关的占位符
        time_keywords = [
            'start_date', 'end_date', 'execution_date', 'current_date',
            'period_start_date', 'period_end_date', 'data_start_time', 'data_end_time'
        ]
        
        time_placeholders = [match for match in matches if any(keyword in match.lower() for keyword in time_keywords)]
        
        return list(set(time_placeholders))  # 去重
    
    def validate_time_placeholders(self, sql: str, time_placeholders: Dict[str, str]) -> Dict[str, Any]:
        """
        验证SQL中的时间占位符是否都有对应的值
        
        Args:
            sql: SQL字符串
            time_placeholders: 时间占位符字典
            
        Returns:
            验证结果
        """
        extracted_placeholders = self.extract_time_placeholders_from_sql(sql)
        
        missing_placeholders = []
        available_placeholders = []
        
        for placeholder in extracted_placeholders:
            if placeholder in time_placeholders:
                available_placeholders.append(placeholder)
            else:
                missing_placeholders.append(placeholder)
        
        return {
            'is_valid': len(missing_placeholders) == 0,
            'extracted_placeholders': extracted_placeholders,
            'available_placeholders': available_placeholders,
            'missing_placeholders': missing_placeholders,
            'coverage_rate': len(available_placeholders) / len(extracted_placeholders) if extracted_placeholders else 1.0
        }


# 全局实例
time_placeholder_generator = TimePlaceholderGenerator()


def generate_time_placeholders(
    time_window: Optional[Dict[str, str]] = None,
    cron_expression: Optional[str] = None,
    execution_time: Optional[datetime] = None,
    data_range: str = "day",
    time_column: Optional[str] = None
) -> Dict[str, Any]:
    """
    便捷函数：生成时间占位符
    
    Args:
        time_window: 时间窗口
        cron_expression: cron表达式
        execution_time: 执行时间
        data_range: 数据范围
        time_column: 时间列名
        
    Returns:
        时间占位符信息
    """
    return time_placeholder_generator.generate_time_placeholders(
        time_window, cron_expression, execution_time, data_range, time_column
    )


logger.info("✅ 时间占位符生成工具类已加载")
