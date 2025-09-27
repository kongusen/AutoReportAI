"""
图表集成服务
集成到真实的ETL和任务处理流程中
基于真实数据源和模板生成图表
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.data_source import DataSource
from app.models.template import Template
from app.models.report_history import ReportHistory
from app.services.data.connectors.connector_factory import create_connector
# AI tools migrated to agents
# from app.services.infrastructure.agents.tools import get_tool_registry  # deprecated
from app.services.data.processing.visualization_service import VisualizationService, ChartType as VsChartType

logger = logging.getLogger(__name__)


class ChartIntegrationService:
    """图表集成服务 - 集成到真实业务流程"""
    
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.logger = logger
        
    async def generate_charts_for_task(
        self, 
        task: Task,
        data_results: Dict[str, Any],
        placeholder_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        为任务生成图表
        集成到真实的任务执行流程中
        
        Args:
            task: 任务对象
            data_results: ETL处理后的数据结果
            placeholder_data: 占位符填充数据
        """
        try:
            self.logger.info(f"开始为任务 {task.id} 生成图表")
            
            # 获取模板和数据源信息
            template = self.db.query(Template).filter(Template.id == task.template_id).first()
            data_source = self.db.query(DataSource).filter(DataSource.id == task.data_source_id).first()
            
            if not template or not data_source:
                raise ValueError("模板或数据源不存在")
            
            # 分析模板内容，确定需要的图表类型
            chart_requirements = self._analyze_template_for_charts(template, placeholder_data)
            
            # 基于真实数据生成图表
            generated_charts = []
            
            for chart_req in chart_requirements:
                try:
                    chart_result = await self._generate_single_chart(
                        chart_req, data_results, data_source
                    )
                    if chart_result.get('success'):
                        generated_charts.append(chart_result)
                        self.logger.info(f"生成图表成功: {chart_result.get('filename')}")
                    
                except Exception as e:
                    self.logger.error(f"生成图表失败: {e}")
                    continue
            
            # 返回图表生成结果
            return {
                'success': True,
                'charts': generated_charts,
                'chart_count': len(generated_charts),
                'task_id': task.id,
                'template_name': template.name,
                'data_source_name': data_source.name
            }
            
        except Exception as e:
            self.logger.error(f"任务图表生成失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'charts': [],
                'chart_count': 0
            }
    
    def _analyze_template_for_charts(
        self, 
        template: Template, 
        placeholder_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """分析模板内容，确定需要的图表类型"""
        chart_requirements = []
        
        template_content = template.content.lower()
        
        # 基于占位符和模板内容分析需要的图表
        if 'sales' in template_content or 'total_sales' in placeholder_data:
            # 销售相关 - 生成柱状图
            chart_requirements.append({
                'type': 'bar',
                'title': '销售业绩分析',
                'data_source': 'sales',
                'metrics': ['total_sales', 'order_count']
            })
        
        if 'trend' in template_content or 'sales_trend' in placeholder_data:
            # 趋势相关 - 生成折线图
            chart_requirements.append({
                'type': 'line', 
                'title': '销售趋势分析',
                'data_source': 'trend',
                'metrics': ['sales_trend', 'growth_rate']
            })
        
        if 'user' in template_content or 'active_users' in placeholder_data:
            # 用户相关 - 生成饼图
            chart_requirements.append({
                'type': 'pie',
                'title': '用户分布分析', 
                'data_source': 'users',
                'metrics': ['active_users', 'user_segments']
            })
        
        # 如果没有特定要求，默认生成基础图表
        if not chart_requirements:
            chart_requirements.append({
                'type': 'bar',
                'title': '数据概览',
                'data_source': 'default',
                'metrics': list(placeholder_data.keys())[:5]
            })
        
        return chart_requirements
    
    async def _generate_single_chart(
        self,
        chart_req: Dict[str, Any],
        data_results: Dict[str, Any], 
        data_source: DataSource
    ) -> Dict[str, Any]:
        """生成单个图表"""
        
        chart_type = chart_req.get('type', 'bar')
        title = chart_req.get('title', '数据图表')
        
        # 生成示例数据（在真实环境中应该从data_results提取）
        chart_data = self._prepare_chart_data(chart_req, data_results, data_source)
        
        # 使用统一可视化服务生成图表配置（JSON 输出）
        vs = VisualizationService()
        # 将 chart_data 转为列表数据 + 配置
        data, cfg = self._to_visualization_inputs(chart_type, title, chart_data)
        return vs.generate_chart(data, self._map_chart_type(chart_type), cfg, output_format="json")

    def _to_visualization_inputs(self, chart_type: str, title: str, chart_data: Dict[str, Any]):
        """将内部chart_data转换为 VisualizationService 所需输入。"""
        if chart_type == 'bar':
            x = chart_data.get('x_data') or chart_data.get('labels') or []
            y = chart_data.get('y_data') or []
            data = [{"x": xv, "y": y[i] if i < len(y) else None} for i, xv in enumerate(x)]
            cfg = {"title": title, "x_column": "x", "y_column": "y"}
            return data, cfg
        if chart_type == 'line':
            x = chart_data.get('x_data') or []
            series = chart_data.get('series') or []
            # Flatten first series for demo
            if series:
                name = series[0].get('name', 'y')
                vals = series[0].get('data', [])
                data = [{"x": xv, name: vals[i] if i < len(vals) else None} for i, xv in enumerate(x)]
                cfg = {"title": title, "x_column": "x", "y_column": name}
            else:
                data = [{"x": i, "y": v} for i, v in enumerate(x)]
                cfg = {"title": title, "x_column": "x", "y_column": "y"}
            return data, cfg
        # default map to bar
        x = chart_data.get('x_data') or []
        y = chart_data.get('y_data') or []
        data = [{"x": xv, "y": y[i] if i < len(y) else None} for i, xv in enumerate(x)]
        cfg = {"title": title, "x_column": "x", "y_column": "y"}
        return data, cfg

    def _map_chart_type(self, chart_type: str) -> str:
        mapping = {"bar": VsChartType.BAR.value, "line": VsChartType.LINE.value, "pie": VsChartType.PIE.value}
        return mapping.get(chart_type, VsChartType.BAR.value)
    
    def _prepare_chart_data(
        self,
        chart_req: Dict[str, Any],
        data_results: Dict[str, Any],
        data_source: DataSource
    ) -> Dict[str, Any]:
        """准备图表数据 - 基于真实ETL结果"""
        
        chart_type = chart_req.get('type', 'bar')
        
        # 优先从ETL结果中提取真实数据
        if data_results and 'processed_data' in data_results:
            processed_data = data_results['processed_data']
            
            # 如果有DataFrame形式的数据
            if hasattr(processed_data, 'columns') and hasattr(processed_data, 'values'):
                return self._extract_chart_data_from_dataframe(processed_data, chart_type)
                
            # 如果是字典形式的聚合数据
            elif isinstance(processed_data, dict):
                return self._extract_chart_data_from_dict(processed_data, chart_type)
        
        # 从占位符填充结果中提取数据
        if data_results and 'placeholder_results' in data_results:
            placeholder_data = data_results['placeholder_results']
            return self._extract_chart_data_from_placeholders(placeholder_data, chart_type)
        
        # 生成基于数据源类型的示例数据
        return self._generate_contextual_sample_data(chart_type, data_source)
    
    def _extract_chart_data_from_dataframe(self, df, chart_type):
        """从DataFrame提取图表数据"""
        import pandas as pd
        
        if df.empty:
            return self._generate_default_chart_data(chart_type)
            
        # 获取数值列和分类列
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        if chart_type == 'bar' and len(numeric_cols) >= 1:
            if categorical_cols:
                # 使用分类列作为X轴，数值列作为Y轴
                x_col = categorical_cols[0]
                y_col = numeric_cols[0]
                
                # 如果数据太多，取前10个
                df_subset = df.head(10) if len(df) > 10 else df
                
                return {
                    'x_data': df_subset[x_col].astype(str).tolist(),
                    'y_data': df_subset[y_col].tolist(),
                    'x_label': x_col,
                    'y_label': y_col,
                    'colors': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'] * 2
                }
            else:
                # 使用索引作为X轴
                df_subset = df.head(10)
                return {
                    'x_data': [f'项目{i+1}' for i in range(len(df_subset))],
                    'y_data': df_subset[numeric_cols[0]].tolist(),
                    'x_label': '项目',
                    'y_label': numeric_cols[0]
                }
        
        elif chart_type == 'line' and len(numeric_cols) >= 1:
            df_subset = df.head(20)
            x_data = list(range(1, len(df_subset) + 1))
            
            if len(numeric_cols) >= 2:
                return {
                    'x_data': x_data,
                    'series': [
                        {'name': numeric_cols[0], 'data': df_subset[numeric_cols[0]].tolist()},
                        {'name': numeric_cols[1], 'data': df_subset[numeric_cols[1]].tolist()}
                    ],
                    'x_label': '序号',
                    'y_label': '数值'
                }
            else:
                return {
                    'x_data': x_data,
                    'series': [
                        {'name': numeric_cols[0], 'data': df_subset[numeric_cols[0]].tolist()}
                    ],
                    'x_label': '序号', 
                    'y_label': numeric_cols[0]
                }
        
        elif chart_type == 'pie' and len(categorical_cols) >= 1:
            # 按分类统计
            value_counts = df[categorical_cols[0]].value_counts().head(8)
            return {
                'labels': value_counts.index.astype(str).tolist(),
                'sizes': value_counts.values.tolist()
            }
        
        # 默认返回通用数据
        return self._generate_default_chart_data(chart_type)
    
    def _extract_chart_data_from_dict(self, data_dict, chart_type):
        """从字典数据提取图表数据"""
        if chart_type == 'bar':
            # 寻找键值对形式的数据
            x_data = []
            y_data = []
            
            for key, value in data_dict.items():
                if isinstance(value, (int, float)):
                    x_data.append(str(key))
                    y_data.append(value)
            
            if x_data and y_data:
                return {
                    'x_data': x_data[:10],  # 限制显示数量
                    'y_data': y_data[:10],
                    'x_label': '类别',
                    'y_label': '数值'
                }
        
        return self._generate_default_chart_data(chart_type)
    
    def _extract_chart_data_from_placeholders(self, placeholder_data, chart_type):
        """从占位符数据提取图表数据"""
        # 寻找数值型占位符用于图表
        numeric_placeholders = {}
        for key, value in placeholder_data.items():
            if isinstance(value, (int, float)):
                numeric_placeholders[key] = value
        
        if numeric_placeholders and chart_type == 'bar':
            return {
                'x_data': list(numeric_placeholders.keys()),
                'y_data': list(numeric_placeholders.values()),
                'x_label': '指标',
                'y_label': '数值'
            }
        
        return self._generate_default_chart_data(chart_type)
    
    def _generate_contextual_sample_data(self, chart_type, data_source):
        """基于数据源类型生成上下文相关的示例数据"""
        if data_source.source_type.value == 'doris':
            # Doris数据源 - 生成业务相关示例数据
            if chart_type == 'bar':
                return {
                    'x_data': ['产品A', '产品B', '产品C', '产品D', '产品E'],
                    'y_data': [85000, 92000, 78000, 105000, 88000],
                    'x_label': '产品类型',
                    'y_label': '销售额 (元)',
                    'colors': ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#592941']
                }
            elif chart_type == 'line':
                return {
                    'x_data': ['1月', '2月', '3月', '4月', '5月', '6月'],
                    'series': [
                        {'name': '收入', 'data': [120, 135, 145, 160, 155, 180]},
                        {'name': '成本', 'data': [80, 85, 90, 95, 90, 100]}
                    ],
                    'x_label': '月份',
                    'y_label': '金额 (万元)'
                }
            elif chart_type == 'pie':
                return {
                    'labels': ['华北', '华东', '华南', '西部', '其他'],
                    'sizes': [30, 25, 20, 15, 10]
                }
        
        return self._generate_default_chart_data(chart_type)
    
    def _generate_default_chart_data(self, chart_type):
        """生成默认图表数据"""
        if chart_type == 'bar':
            return {
                'x_data': ['类别A', '类别B', '类别C'],
                'y_data': [100, 200, 150],
                'x_label': '类别',
                'y_label': '数值'
            }
        elif chart_type == 'line':
            return {
                'x_data': [1, 2, 3, 4],
                'series': [{'name': '数据', 'data': [10, 20, 15, 25]}],
                'x_label': '时间',
                'y_label': '数值'
            }
        elif chart_type == 'pie':
            return {
                'labels': ['项目1', '项目2', '项目3'],
                'sizes': [40, 35, 25]
            }
        else:
            return {
                'x_data': ['A', 'B', 'C'],
                'y_data': [1, 2, 3],
                'x_label': '项目',
                'y_label': '数值'
            }
    
    async def extract_data_from_source(
        self,
        data_source: DataSource,
        query_requirements: List[str]
    ) -> Dict[str, Any]:
        """从数据源提取数据用于图表生成"""
        try:
            # 创建数据源连接器
            connector = create_connector(data_source)
            await connector.connect()
            
            try:
                # 获取表列表
                tables = await connector.get_tables()
                
                if not tables:
                    self.logger.warning("数据源没有可用表")
                    return {'success': False, 'data': {}}
                
                # 选择第一个表进行查询（简化处理）
                table_name = tables[0].get('name') if tables else None
                
                if table_name:
                    # 执行简单查询获取数据
                    query = f"SELECT * FROM {table_name} LIMIT 1000"
                    result = await connector.execute_query(query)
                    
                    if hasattr(result, 'data') and not result.data.empty:
                        # 转换为图表所需的数据格式
                        df = result.data
                        return {
                            'success': True,
                            'data': {
                                'rows': df.to_dict('records'),
                                'columns': df.columns.tolist(),
                                'row_count': len(df)
                            }
                        }
                
                return {'success': False, 'data': {}}
                
            finally:
                await connector.disconnect()
                
        except Exception as e:
            self.logger.error(f"从数据源提取数据失败: {e}")
            return {'success': False, 'error': str(e), 'data': {}}


class TaskChartProcessor:
    """任务图表处理器 - 集成到任务执行流程"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def process_task_with_charts(
        self,
        task: Task,
        etl_results: Dict[str, Any],
        placeholder_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理任务并生成图表
        集成到任务的完整执行流程中
        """
        try:
            # 创建图表集成服务
            chart_service = ChartIntegrationService(self.db, str(task.owner_id))
            
            # 生成图表
            chart_results = await chart_service.generate_charts_for_task(
                task=task,
                data_results=etl_results,
                placeholder_data=placeholder_results
            )
            
            # 将图表信息添加到任务结果中
            enhanced_results = {
                **placeholder_results,
                'generated_charts': chart_results.get('charts', []),
                'chart_count': chart_results.get('chart_count', 0),
                'chart_generation_success': chart_results.get('success', False)
            }
            
            # 如果有生成的图表，添加图表引用到占位符数据
            if chart_results.get('charts'):
                chart_references = []
                for chart in chart_results['charts']:
                    chart_references.append({
                        'title': chart.get('title', '图表'),
                        'filename': chart.get('filename', ''),
                        'type': chart.get('chart_type', 'unknown')
                    })
                
                enhanced_results['chart_references'] = chart_references
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"任务图表处理失败: {e}")
            # 返回原始结果，不影响主流程
            return placeholder_results


# 工厂函数
def create_chart_integration_service(db: Session, user_id: str) -> ChartIntegrationService:
    """创建图表集成服务实例"""
    return ChartIntegrationService(db, user_id)

def create_task_chart_processor(db: Session) -> TaskChartProcessor:
    """创建任务图表处理器实例"""
    return TaskChartProcessor(db)
