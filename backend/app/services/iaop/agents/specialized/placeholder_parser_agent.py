"""
占位符解析Agent - 解析模板中的占位符并生成标准化任务请求

支持的占位符格式：
- {{统计：过去六个月的销售额}}
- {{柱状图：各部门业绩对比}}
- {{饼状图：产品销量分布}}
- {{折线图：用户增长趋势}}
- {{表格：员工绩效详情}}
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from ..base import BaseAgent
from ...context.execution_context import EnhancedExecutionContext, ContextScope

logger = logging.getLogger(__name__)


class PlaceholderParserAgent(BaseAgent):
    """占位符解析Agent"""
    
    def __init__(self, db_session=None, db=None, **kwargs):
        super().__init__("placeholder_parser", ["placeholder_parsing", "semantic_analysis"])
        self.require_context("template_content", "data_source_context")
        
        # Store database session if provided (for compatibility)
        self.db_session = db_session or db
        
        # 占位符模式匹配
        self.placeholder_pattern = re.compile(r'\{\{([^}]+)\}\}')
        
        # 支持的图表类型映射
        self.chart_type_mapping = {
            '统计': 'statistics',
            '柱状图': 'bar_chart',
            '柱图': 'bar_chart', 
            '饼状图': 'pie_chart',
            '饼图': 'pie_chart',
            '折线图': 'line_chart',
            '线图': 'line_chart',
            '趋势图': 'line_chart',
            '表格': 'table',
            '数据表': 'table',
            '散点图': 'scatter_chart',
            '雷达图': 'radar_chart',
            '漏斗图': 'funnel_chart'
        }
        
        # 时间范围模式
        self.time_patterns = {
            r'过去(\d+)个?月': lambda m: self._calculate_time_range('months', int(m.group(1))),
            r'过去(\d+)年': lambda m: self._calculate_time_range('years', int(m.group(1))),
            r'过去(\d+)天': lambda m: self._calculate_time_range('days', int(m.group(1))),
            r'过去(\d+)周': lambda m: self._calculate_time_range('weeks', int(m.group(1))),
            r'今年': lambda m: self._calculate_time_range('current_year'),
            r'去年': lambda m: self._calculate_time_range('last_year'),
            r'本月': lambda m: self._calculate_time_range('current_month'),
            r'上月': lambda m: self._calculate_time_range('last_month'),
            r'本季度?': lambda m: self._calculate_time_range('current_quarter'),
            r'上季度?': lambda m: self._calculate_time_range('last_quarter'),
        }
        
        # 聚合方式映射
        self.aggregation_mapping = {
            '总和': 'sum',
            '求和': 'sum',
            '汇总': 'sum',
            '平均': 'avg',
            '均值': 'avg',
            '计数': 'count',
            '数量': 'count',
            '最大': 'max',
            '最小': 'min',
            '最高': 'max',
            '最低': 'min'
        }

    async def execute(self, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """执行占位符解析"""
        try:
            template_content = context.get_context("template_content")
            data_source_context = context.get_context("data_source_context", {})
            
            if not template_content:
                return {
                    "success": False,
                    "error": "模板内容为空",
                    "data": {}
                }
            
            # 提取所有占位符
            placeholders = self._extract_placeholders(template_content)
            
            if not placeholders:
                return {
                    "success": True,
                    "data": {
                        "placeholders": [],
                        "message": "未发现占位符"
                    }
                }
            
            # 解析每个占位符
            parsed_results = []
            for placeholder in placeholders:
                try:
                    parsed = await self._parse_single_placeholder(placeholder, data_source_context)
                    parsed_results.append(parsed)
                    
                    # 将解析结果存储到上下文
                    context.set_context(f"parsed_{len(parsed_results)}", parsed, ContextScope.REQUEST)
                    
                except Exception as e:
                    logger.error(f"解析占位符失败: {placeholder}, 错误: {e}")
                    parsed_results.append({
                        "original_text": placeholder,
                        "success": False,
                        "error": str(e)
                    })
            
            # 统计解析成功率
            success_count = sum(1 for r in parsed_results if r.get("success", False))
            total_count = len(parsed_results)
            
            return {
                "success": True,
                "data": {
                    "placeholders": parsed_results,
                    "summary": {
                        "total_count": total_count,
                        "success_count": success_count,
                        "success_rate": success_count / total_count if total_count > 0 else 0
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"占位符解析Agent执行失败: {e}")
            return {
                "success": False,
                "error": f"占位符解析失败: {str(e)}",
                "data": {}
            }

    def _extract_placeholders(self, template_content: str) -> List[str]:
        """提取模板中的所有占位符"""
        matches = self.placeholder_pattern.findall(template_content)
        return [match.strip() for match in matches if match.strip()]

    async def _parse_single_placeholder(self, placeholder_text: str, data_source_context: Dict[str, Any]) -> Dict[str, Any]:
        """解析单个占位符"""
        logger.info(f"解析占位符: {placeholder_text}")
        
        # 基础解析结果结构
        result = {
            "original_text": placeholder_text,
            "success": False,
            "task_type": "unknown",
            "metric": "",
            "dimensions": [],
            "time_range": None,
            "filters": [],
            "aggregation": "sum",
            "confidence": 0.0
        }
        
        try:
            # 1. 识别图表类型
            task_type, confidence = self._identify_task_type(placeholder_text)
            result["task_type"] = task_type
            result["confidence"] = confidence
            
            # 2. 提取指标信息
            metric = self._extract_metric(placeholder_text, data_source_context)
            result["metric"] = metric
            
            # 3. 提取维度信息
            dimensions = self._extract_dimensions(placeholder_text, data_source_context)
            result["dimensions"] = dimensions
            
            # 4. 提取时间范围
            time_range = self._extract_time_range(placeholder_text)
            result["time_range"] = time_range
            
            # 5. 提取过滤条件
            filters = self._extract_filters(placeholder_text, data_source_context)
            result["filters"] = filters
            
            # 6. 识别聚合方式
            aggregation = self._identify_aggregation(placeholder_text)
            result["aggregation"] = aggregation
            
            # 7. 数据表映射
            table_mapping = self._map_to_tables(metric, dimensions, data_source_context)
            result["table_mapping"] = table_mapping
            
            # 解析成功
            result["success"] = True
            logger.info(f"占位符解析成功: {placeholder_text} -> {task_type}")
            
        except Exception as e:
            logger.error(f"单个占位符解析失败: {placeholder_text}, 错误: {e}")
            result["error"] = str(e)
        
        return result

    def _identify_task_type(self, placeholder_text: str) -> Tuple[str, float]:
        """识别任务类型"""
        text = placeholder_text.lower()
        
        # 直接匹配
        for chart_key, chart_type in self.chart_type_mapping.items():
            if chart_key in placeholder_text:
                return chart_type, 0.9
        
        # 模糊匹配
        if any(keyword in text for keyword in ['图', 'chart']):
            if any(keyword in text for keyword in ['柱', 'bar', '条']):
                return 'bar_chart', 0.7
            elif any(keyword in text for keyword in ['饼', 'pie', '圆']):
                return 'pie_chart', 0.7
            elif any(keyword in text for keyword in ['线', 'line', '趋势']):
                return 'line_chart', 0.7
            else:
                return 'bar_chart', 0.5  # 默认柱状图
        
        if any(keyword in text for keyword in ['统计', '总计', '汇总']):
            return 'statistics', 0.8
        
        if any(keyword in text for keyword in ['表', 'table', '列表']):
            return 'table', 0.8
        
        # 默认返回统计
        return 'statistics', 0.3

    def _extract_metric(self, placeholder_text: str, data_source_context: Dict[str, Any]) -> str:
        """提取指标信息"""
        # 常见指标关键词
        metric_keywords = [
            '销售额', '营业额', '收入', '金额', '价格',
            '数量', '销量', '用户数', '客户数', '访问量',
            '利润', '成本', '费用', '支出',
            '订单', '交易', '转化率', '点击率',
            '增长', '增长率', '占比', '比例'
        ]
        
        for keyword in metric_keywords:
            if keyword in placeholder_text:
                return keyword
        
        # 尝试从数据源上下文中匹配
        if 'columns' in data_source_context:
            for column in data_source_context['columns']:
                if column['name'] in placeholder_text or column.get('comment', '') in placeholder_text:
                    return column['name']
        
        # 提取冒号后的主要内容
        if '：' in placeholder_text:
            content = placeholder_text.split('：', 1)[1].strip()
            # 去除时间范围等修饰词
            for time_pattern in self.time_patterns.keys():
                content = re.sub(time_pattern, '', content).strip()
            return content if content else '未知指标'
        
        return '未知指标'

    def _extract_dimensions(self, placeholder_text: str, data_source_context: Dict[str, Any]) -> List[str]:
        """提取维度信息"""
        dimensions = []
        
        # 时间维度
        if any(keyword in placeholder_text for keyword in ['月', '年', '日', '季', '时间']):
            dimensions.append('时间')
        
        # 分类维度
        category_keywords = ['部门', '地区', '产品', '类别', '分类', '渠道', '来源', '类型']
        for keyword in category_keywords:
            if keyword in placeholder_text:
                dimensions.append(keyword)
        
        # 从数据源上下文中查找可能的维度字段
        if 'columns' in data_source_context:
            for column in data_source_context['columns']:
                if column.get('type', '').lower() in ['varchar', 'char', 'text', 'enum']:
                    if column['name'] in placeholder_text or column.get('comment', '') in placeholder_text:
                        dimensions.append(column['name'])
        
        return list(set(dimensions)) if dimensions else ['默认维度']

    def _extract_time_range(self, placeholder_text: str) -> Optional[Dict[str, Any]]:
        """提取时间范围"""
        for pattern, calculator in self.time_patterns.items():
            match = re.search(pattern, placeholder_text)
            if match:
                return calculator(match)
        
        return None

    def _calculate_time_range(self, unit: str, value: int = None) -> Dict[str, Any]:
        """计算具体的时间范围"""
        now = datetime.now()
        
        if unit == 'months' and value:
            start_date = now.replace(day=1) - timedelta(days=32 * (value - 1))
            start_date = start_date.replace(day=1)
            end_date = now
        elif unit == 'days' and value:
            start_date = now - timedelta(days=value)
            end_date = now
        elif unit == 'weeks' and value:
            start_date = now - timedelta(weeks=value)
            end_date = now
        elif unit == 'years' and value:
            start_date = now.replace(year=now.year - value, month=1, day=1)
            end_date = now
        elif unit == 'current_year':
            start_date = now.replace(month=1, day=1)
            end_date = now
        elif unit == 'last_year':
            start_date = now.replace(year=now.year - 1, month=1, day=1)
            end_date = now.replace(year=now.year - 1, month=12, day=31)
        elif unit == 'current_month':
            start_date = now.replace(day=1)
            end_date = now
        elif unit == 'last_month':
            if now.month == 1:
                start_date = now.replace(year=now.year - 1, month=12, day=1)
            else:
                start_date = now.replace(month=now.month - 1, day=1)
            end_date = start_date.replace(day=1) + timedelta(days=32)
            end_date = end_date.replace(day=1) - timedelta(days=1)
        else:
            # 默认最近30天
            start_date = now - timedelta(days=30)
            end_date = now
        
        return {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'description': f"{unit}_{value}" if value else unit
        }

    def _extract_filters(self, placeholder_text: str, data_source_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取过滤条件"""
        filters = []
        
        # 简单的关键词过滤识别
        filter_patterns = [
            r'(\w+)为(\w+)',
            r'(\w+)等于(\w+)',
            r'(\w+)大于(\d+)',
            r'(\w+)小于(\d+)',
            r'(\w+)包含(\w+)'
        ]
        
        for pattern in filter_patterns:
            matches = re.finditer(pattern, placeholder_text)
            for match in matches:
                filters.append({
                    'field': match.group(1),
                    'operator': '=',  # 简化处理
                    'value': match.group(2)
                })
        
        return filters

    def _identify_aggregation(self, placeholder_text: str) -> str:
        """识别聚合方式"""
        for keyword, agg_type in self.aggregation_mapping.items():
            if keyword in placeholder_text:
                return agg_type
        
        # 根据指标类型推测聚合方式
        if any(keyword in placeholder_text for keyword in ['额', '收入', '利润', '成本']):
            return 'sum'
        elif any(keyword in placeholder_text for keyword in ['数', '量', '个']):
            return 'count'
        elif any(keyword in placeholder_text for keyword in ['率', '比例']):
            return 'avg'
        
        return 'sum'  # 默认求和

    def _map_to_tables(self, metric: str, dimensions: List[str], data_source_context: Dict[str, Any]) -> Dict[str, Any]:
        """映射到数据表"""
        mapping = {
            'suggested_table': None,
            'metric_column': None,
            'dimension_columns': [],
            'confidence': 0.0
        }
        
        if 'tables' not in data_source_context:
            return mapping
        
        # 简单的表名匹配逻辑
        for table in data_source_context.get('tables', []):
            table_name = table.get('name', '')
            
            # 根据指标匹配表
            if any(keyword in table_name for keyword in ['sales', '销售', 'order', '订单']) and '销售' in metric:
                mapping['suggested_table'] = table_name
                mapping['confidence'] = 0.8
                break
            elif any(keyword in table_name for keyword in ['user', '用户', 'customer', '客户']) and '用户' in metric:
                mapping['suggested_table'] = table_name
                mapping['confidence'] = 0.8
                break
        
        return mapping

    async def _get_placeholder_info(self, placeholder_id: str) -> Optional[Dict[str, Any]]:
        """
        获取占位符信息
        
        Args:
            placeholder_id: 占位符ID
            
        Returns:
            占位符信息字典，如果未找到则返回None
        """
        try:
            if not self.db_session:
                logger.error("数据库会话未提供，无法获取占位符信息")
                return None
                
            from app import crud
            from app.models.template_placeholder import TemplatePlaceholder
            
            # 查询占位符信息
            placeholder = self.db_session.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == placeholder_id
            ).first()
            
            if not placeholder:
                logger.warning(f"未找到占位符: {placeholder_id}")
                return None
            
            # 获取关联的模板和数据源信息
            template = crud.template.get(self.db_session, id=placeholder.template_id)
            
            placeholder_info = {
                'id': str(placeholder.id),
                'placeholder_name': placeholder.placeholder_name,
                'placeholder_type': placeholder.placeholder_type or 'text',
                'template_id': str(placeholder.template_id),
                'data_source_id': str(template.data_source_id) if template else None,
                'generated_sql': placeholder.generated_sql,
                'last_analysis_at': placeholder.last_analysis_at,
                'confidence': getattr(placeholder, 'confidence', 0.0)
            }
            
            logger.info(f"获取占位符信息成功: {placeholder_id}")
            return placeholder_info
            
        except Exception as e:
            logger.error(f"获取占位符信息失败: {placeholder_id}, 错误: {e}")
            return None