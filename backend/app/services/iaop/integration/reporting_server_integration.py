"""
报告服务器集成
处理占位符数据替换和最终报告生成
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.template_placeholder import TemplatePlaceholder
from app.services.data.processing.retrieval import DataRetrievalService


class ReportingServerIntegration:
    """报告服务器集成，处理占位符数据替换"""
    
    def __init__(self, db: Session):
        self.db = db
        self.data_retrieval = DataRetrievalService()
    
    async def execute_placeholder_replacement(self, task_id: int) -> Dict[str, Any]:
        """
        执行占位符的数据替换
        调用报告服务器进行真实数据替换
        """
        
        # 1. 获取任务和模板信息
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {'success': False, 'error': 'Task not found'}
        
        # 2. 获取所有占位符
        placeholders = self.db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.template_id == task.template_id
        ).all()
        
        if not placeholders:
            return {'success': False, 'error': 'No placeholders found for this task'}
        
        # 3. 执行每个占位符的数据查询
        replacement_results = {}
        successful_replacements = 0
        
        for placeholder in placeholders:
            try:
                if placeholder.generated_sql and placeholder.generated_sql.strip():
                    # 执行SQL查询获取真实数据
                    data_result = await self._execute_placeholder_query(
                        placeholder, task.data_source_id
                    )
                    replacement_results[placeholder.placeholder_name] = data_result
                    
                    if data_result.get('success'):
                        successful_replacements += 1
                else:
                    replacement_results[placeholder.placeholder_name] = {
                        'success': False,
                        'error': 'No SQL generated for this placeholder',
                        'placeholder_name': placeholder.placeholder_name
                    }
            except Exception as e:
                replacement_results[placeholder.placeholder_name] = {
                    'success': False,
                    'error': str(e),
                    'placeholder_name': placeholder.placeholder_name
                }
        
        # 4. 调用报告生成服务
        report_result = None
        if successful_replacements > 0:
            report_result = await self._generate_final_report(task, replacement_results)
        else:
            report_result = {
                'success': False,
                'error': 'No successful placeholder replacements found'
            }
        
        return {
            'success': successful_replacements > 0,
            'task_id': task_id,
            'placeholder_count': len(placeholders),
            'successful_replacements': successful_replacements,
            'placeholder_results': replacement_results,
            'report_result': report_result
        }
    
    async def _execute_placeholder_query(self, placeholder: TemplatePlaceholder, data_source_id) -> Dict[str, Any]:
        """执行占位符的SQL查询"""
        
        try:
            # 使用数据检索服务执行查询
            query_result = await self.data_retrieval.execute_query(
                sql=placeholder.generated_sql,
                data_source_id=str(data_source_id)
            )
            
            # 格式化查询结果
            formatted_result = self._format_query_result(query_result, placeholder)
            
            return {
                'success': True,
                'data': formatted_result,
                'raw_data': self._extract_raw_data(query_result),
                'placeholder_name': placeholder.placeholder_name,
                'execution_time': datetime.now().isoformat(),
                'sql_query': placeholder.generated_sql
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'placeholder_name': placeholder.placeholder_name,
                'sql_query': placeholder.generated_sql
            }
    
    def _extract_raw_data(self, query_result) -> List[Dict[str, Any]]:
        """提取原始查询结果数据"""
        try:
            if hasattr(query_result, 'to_dict'):
                result_dict = query_result.to_dict()
                return result_dict.get('data', [])
            elif isinstance(query_result, dict):
                return query_result.get('data', [])
            elif hasattr(query_result, 'data') and hasattr(query_result.data, 'to_dict'):
                return query_result.data.to_dict('records')
            else:
                return []
        except Exception:
            return []
    
    def _format_query_result(self, query_result, placeholder: TemplatePlaceholder) -> Union[str, Dict[str, Any]]:
        """格式化查询结果为占位符替换内容"""
        
        raw_data = self._extract_raw_data(query_result)
        
        if not raw_data:
            return "无数据"
        
        # 根据占位符类型和数据结构智能格式化
        placeholder_name = placeholder.placeholder_name.lower()
        
        # 1. 单个数值类型（统计类）
        if len(raw_data) == 1 and len(raw_data[0]) == 1:
            value = list(raw_data[0].values())[0]
            
            # 数值格式化
            if isinstance(value, (int, float)):
                if '百分比' in placeholder_name or '占比' in placeholder_name:
                    return f"{value:.1%}" if value <= 1 else f"{value:.1f}%"
                elif '金额' in placeholder_name or '费用' in placeholder_name:
                    return f"¥{value:,.2f}"
                else:
                    return f"{value:,}" if isinstance(value, int) else f"{value:.2f}"
            
            return str(value)
        
        # 2. 单行多列（详细信息）
        elif len(raw_data) == 1:
            row = raw_data[0]
            formatted_pairs = []
            for k, v in row.items():
                if isinstance(v, (int, float)) and v > 1000:
                    formatted_pairs.append(f"{k}: {v:,}")
                else:
                    formatted_pairs.append(f"{k}: {v}")
            return ", ".join(formatted_pairs)
        
        # 3. 多行数据（列表、排行等）
        else:
            return self._format_multi_row_data(raw_data, placeholder_name)
    
    def _format_multi_row_data(self, data: List[Dict], placeholder_name: str) -> Union[str, Dict[str, Any]]:
        """格式化多行数据"""
        
        # 排行榜类型
        if any(word in placeholder_name for word in ['排名', '排行', 'top', 'rank']):
            lines = []
            for i, row in enumerate(data[:10], 1):  # 只显示前10名
                if len(row) >= 2:
                    key, value = list(row.items())[:2]
                    lines.append(f"{i}. {row[key[0]]}: {row[value[0]]}")
            return "\n".join(lines) if lines else "无排名数据"
        
        # 趋势类型（返回结构化数据供图表使用）
        elif any(word in placeholder_name for word in ['趋势', '变化', 'trend', '图表']):
            return {
                'type': 'chart_data',
                'data': data,
                'display': f"共{len(data)}个数据点，详见图表"
            }
        
        # 统计汇总类型
        elif len(data) <= 10:
            lines = []
            for row in data:
                if len(row) == 2:
                    k, v = list(row.items())
                    lines.append(f"{row[k]}: {row[v]}")
                else:
                    line = ", ".join([f"{k}: {v}" for k, v in list(row.items())[:3]])
                    lines.append(line)
            return "\n".join(lines)
        
        # 大量数据，返回汇总
        else:
            total = len(data)
            # 尝试计算总计
            numeric_columns = []
            for col, val in data[0].items():
                if isinstance(val, (int, float)):
                    numeric_columns.append(col)
            
            summary_info = [f"共{total}条记录"]
            for col in numeric_columns[:2]:  # 最多显示2个数值列的汇总
                total_val = sum(row.get(col, 0) for row in data)
                summary_info.append(f"{col}总计: {total_val:,.2f}")
            
            return ", ".join(summary_info)
    
    async def _generate_final_report(self, task: Task, replacement_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成最终报告"""
        
        try:
            from app.services.domain.reporting.generator import ReportGenerationService
            
            # 准备占位符替换数据
            placeholder_data = {}
            for placeholder_name, result in replacement_results.items():
                if result.get('success'):
                    placeholder_data[placeholder_name] = result.get('data')
                else:
                    placeholder_data[placeholder_name] = f"[数据获取失败: {result.get('error', 'Unknown error')}]"
            
            # 调用报告生成服务
            report_service = ReportGenerationService(self.db)
            
            report_result = await report_service.generate_report(
                task_id=task.id,
                template_id=task.template_id,
                data_source_id=task.data_source_id,
                output_dir="generated_reports"
            )
            
            # 增强报告结果信息
            if report_result.get('success'):
                report_result['placeholder_replacements'] = len([r for r in replacement_results.values() if r.get('success')])
                report_result['total_placeholders'] = len(replacement_results)
                report_result['replacement_summary'] = placeholder_data
            
            return report_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Report generation failed: {str(e)}',
                'placeholder_data': replacement_results
            }
    
    async def get_placeholder_preview(self, placeholder_id: str) -> Dict[str, Any]:
        """获取单个占位符的数据预览"""
        
        placeholder = self.db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.id == placeholder_id
        ).first()
        
        if not placeholder:
            return {'success': False, 'error': 'Placeholder not found'}
        
        if not placeholder.generated_sql:
            return {'success': False, 'error': 'No SQL generated for this placeholder'}
        
        # 获取关联的数据源ID
        from app.models.template import Template
        template = self.db.query(Template).filter(Template.id == placeholder.template_id).first()
        
        if not template:
            return {'success': False, 'error': 'Template not found'}
        
        # 执行查询并返回预览
        try:
            result = await self._execute_placeholder_query(placeholder, template.data_source_id)
            
            if result.get('success'):
                # 限制预览数据量
                raw_data = result.get('raw_data', [])
                preview_data = raw_data[:5] if len(raw_data) > 5 else raw_data
                
                return {
                    'success': True,
                    'placeholder_name': placeholder.placeholder_name,
                    'formatted_data': result.get('data'),
                    'raw_data_preview': preview_data,
                    'total_rows': len(raw_data),
                    'sql_query': placeholder.generated_sql
                }
            else:
                return result
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'placeholder_name': placeholder.placeholder_name
            }