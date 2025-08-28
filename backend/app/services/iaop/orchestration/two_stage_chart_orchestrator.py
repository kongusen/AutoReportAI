"""
两阶段图表编排器 - 专门处理图表生成的两阶段流程

阶段一：图表数据查询
- 语义分析 → SQL生成 → SQL执行 → 数据获取
- 适用于：Templates中的placeholder分析（仅到SQL生成）

阶段二：图表生成渲染  
- 基于阶段一的数据 → 图表配置生成 → 图像渲染
- 适用于：Tasks任务执行（完整两阶段）

支持的执行模式：
- test_only: 仅生成SQL供测试
- stage_one: 执行到数据获取
- full_pipeline: 完整两阶段执行
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..context.execution_context import EnhancedExecutionContext, ContextScope
from ..agents.specialized.semantic_analyzer_agent import PlaceholderSemanticAnalyzerAgent
from ..agents.specialized.chart_data_query_agent import ChartDataQueryAgent
from ..agents.specialized.chart_generator_agent import ChartGeneratorAgent

logger = logging.getLogger(__name__)


class TwoStageChartOrchestrator:
    """两阶段图表编排器"""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        
        # 初始化各阶段Agent
        self.semantic_agent = PlaceholderSemanticAnalyzerAgent()
        self.data_query_agent = ChartDataQueryAgent(db_session=db_session)
        self.chart_generator_agent = ChartGeneratorAgent()
        
        logger.info("两阶段图表编排器初始化完成")
    
    async def execute_for_template_placeholder(
        self,
        placeholder_text: str,
        data_source_id: str, 
        user_id: str,
        template_id: Optional[str] = None,
        execution_mode: str = "test_with_chart"  # sql_only | test_with_chart | full_pipeline
    ) -> Dict[str, Any]:
        """
        为模板占位符执行图表生成流程
        
        主要用于前端的"测试SQL"功能
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始模板占位符图表流程: {placeholder_text}, 模式: {execution_mode}")
            
            # 创建执行上下文
            context = self._create_execution_context(
                placeholder_text, data_source_id, user_id, template_id
            )
            context.set_context('execution_mode', execution_mode, ContextScope.REQUEST)
            
            # 阶段0：语义分析（可选，主要用于优化SQL生成）
            semantic_result = await self._execute_semantic_analysis(context)
            
            # 阶段1：数据查询（包含SQL生成）
            stage_one_result = await self.data_query_agent.execute(context)
            
            if not stage_one_result.get('success', False):
                return self._create_template_error_result(
                    "stage_one", 
                    stage_one_result.get('error', 'unknown'),
                    start_time
                )
            
            stage_one_data = stage_one_result.get('data', {})
            
            # 根据执行模式决定是否继续
            if execution_mode == "sql_only":
                return {
                    'success': True,
                    'stage': 'sql_generated',
                    'execution_mode': execution_mode,
                    'data': {
                        'sql_query': stage_one_data.get('sql_query', ''),
                        'sql_metadata': stage_one_data.get('sql_metadata', {}),
                        'semantic_analysis': semantic_result.get('data', {}),
                        'chart_ready': False,
                        'message': 'SQL已生成，请在前端测试验证'
                    },
                    'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                    'next_actions': ['test_sql', 'validate_sql', 'edit_sql']
                }
            
            # 新增：仅数据查询模式（适用于非图表占位符）
            elif execution_mode == "test_with_data":
                return {
                    'success': True,
                    'stage': 'data_query_complete',
                    'execution_mode': execution_mode,
                    'data': {
                        'sql_query': stage_one_data.get('sql_query', ''),
                        'sql_metadata': stage_one_data.get('sql_metadata', {}),
                        'raw_data': stage_one_data.get('raw_data', []),
                        'processed_data': stage_one_data.get('processed_data', []),
                        'execution_metadata': stage_one_data.get('execution_metadata', {}),
                        'chart_ready': False,
                        'message': 'SQL已执行，数据获取成功'
                    },
                    'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                    'next_actions': ['view_data', 'edit_sql', 'validate_sql']
                }
            
            # 测试模式（包含图表生成）或全流程模式：继续执行阶段2
            if execution_mode in ["test_with_chart", "full_pipeline"]:
                if not stage_one_data.get('chart_ready', False):
                    # 数据查询成功但无法生成图表数据时，仍返回部分结果
                    return {
                        'success': False,
                        'stage': 'data_query_partial',
                        'execution_mode': execution_mode,
                        'error': '数据查询成功，但图表数据准备失败',
                        'data': {
                            'sql_query': stage_one_data.get('sql_query', ''),
                            'sql_metadata': stage_one_data.get('sql_metadata', {}),
                            'raw_data': stage_one_data.get('raw_data', []),
                            'chart_ready': False,
                            'error_details': '可能是数据格式不符合图表要求'
                        },
                        'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                        'troubleshooting': [
                            "检查SQL查询返回的数据格式",
                            "确认数据包含适合图表显示的字段",
                            "验证数据不为空"
                        ]
                    }
                
                # 执行阶段2：图表生成
                logger.info(f"执行阶段2：图表生成，模式: {execution_mode}")
                stage_two_result = await self.chart_generator_agent.execute(context)
                
                if not stage_two_result.get('success', False):
                    return self._create_template_error_result(
                        "chart_generation", 
                        stage_two_result.get('error', 'unknown'),
                        start_time,
                        {
                            'sql_query': stage_one_data.get('sql_query', ''),
                            'raw_data': stage_one_data.get('raw_data', []),
                            'partial_success': True
                        }
                    )
                
                stage_two_data = stage_two_result.get('data', {})
                
                # 组合完整结果
                complete_result = {
                    'success': True,
                    'stage': 'chart_test_complete' if execution_mode == 'test_with_chart' else 'chart_complete',
                    'execution_mode': execution_mode,
                    'data': {
                        # SQL和数据信息
                        'sql_query': stage_one_data.get('sql_query', ''),
                        'sql_metadata': stage_one_data.get('sql_metadata', {}),
                        'raw_data': stage_one_data.get('raw_data', []),
                        'processed_data': stage_one_data.get('processed_data', []),
                        'execution_metadata': stage_one_data.get('execution_metadata', {}),
                        
                        # 图表配置
                        'chart_config': stage_two_data,
                        'chart_type': stage_two_data.get('chart_type', 'bar_chart'),
                        'echarts_config': stage_two_data.get('echarts_config', {}),
                        
                        # 状态标志
                        'chart_ready': True,
                        'ready_for_display': True,
                        'ready_for_preview': execution_mode == 'test_with_chart',
                        
                        # 测试模式特有信息
                        'test_summary': {
                            'data_points': len(stage_one_data.get('processed_data', [])),
                            'chart_type': stage_two_data.get('chart_type', 'bar_chart'),
                            'data_quality': stage_one_data.get('execution_metadata', {}).get('data_quality_score', 0.8),
                            'generation_success': True
                        } if execution_mode == 'test_with_chart' else None
                    },
                    'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                    'next_actions': ['preview_chart', 'save_config', 'edit_sql'] if execution_mode == 'test_with_chart' else ['display_chart', 'export_chart']
                }
                
                logger.info(f"模板图表测试完成: {placeholder_text}, 图表类型: {stage_two_data.get('chart_type')}, 数据点: {len(stage_one_data.get('processed_data', []))}")
                
                return complete_result
            
            # 其他模式返回阶段一结果
            return {
                'success': True,
                'stage': 'stage_one_complete',
                'execution_mode': execution_mode,
                'data': stage_one_data,
                'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }
            
        except Exception as e:
            logger.error(f"模板占位符图表流程执行失败: {e}")
            return self._create_template_error_result("orchestration", str(e), start_time)
    
    async def execute_for_task_execution(
        self,
        placeholder_text: str,
        data_source_id: str,
        user_id: str,
        task_id: Optional[str] = None,
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        为任务执行完整的两阶段图表生成流程
        
        适用于自动化报告任务
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始任务图表生成流程: {placeholder_text}, 任务ID: {task_id}")
            
            # 创建执行上下文
            context = self._create_execution_context(
                placeholder_text, data_source_id, user_id, template_id=None
            )
            context.set_context('execution_mode', 'full_pipeline', ContextScope.REQUEST)
            context.set_context('task_id', task_id, ContextScope.REQUEST)
            
            if task_context:
                context.set_context('task_context', task_context, ContextScope.REQUEST)
            
            # 阶段0：语义分析
            semantic_result = await self._execute_semantic_analysis(context)
            
            # 阶段1：数据查询和获取
            logger.info("执行阶段1：数据查询和获取")
            stage_one_result = await self.data_query_agent.execute(context)
            
            if not stage_one_result.get('success', False):
                return self._create_task_error_result(
                    "data_query", 
                    stage_one_result.get('error', 'unknown'),
                    start_time
                )
            
            stage_one_data = stage_one_result.get('data', {})
            
            if not stage_one_data.get('chart_ready', False):
                return self._create_task_error_result(
                    "data_preparation",
                    "数据查询成功但图表数据未就绪", 
                    start_time
                )
            
            # 阶段2：图表配置生成
            logger.info("执行阶段2：图表配置生成")
            stage_two_result = await self.chart_generator_agent.execute(context)
            
            if not stage_two_result.get('success', False):
                return self._create_task_error_result(
                    "chart_generation",
                    stage_two_result.get('error', 'unknown'),
                    start_time
                )
            
            stage_two_data = stage_two_result.get('data', {})
            
            # 组合最终结果
            final_result = {
                'success': True,
                'stage': 'complete',
                'execution_mode': 'full_pipeline',
                'data': {
                    # 阶段1数据
                    'sql_query': stage_one_data.get('sql_query', ''),
                    'sql_metadata': stage_one_data.get('sql_metadata', {}),
                    'raw_data': stage_one_data.get('raw_data', []),
                    'processed_data': stage_one_data.get('processed_data', []),
                    'execution_metadata': stage_one_data.get('execution_metadata', {}),
                    
                    # 阶段2数据
                    'chart_config': stage_two_data,
                    'chart_type': stage_two_data.get('chart_type', 'bar_chart'),
                    'echarts_config': stage_two_data.get('echarts_config', {}),
                    
                    # 元数据
                    'semantic_analysis': semantic_result.get('data', {}),
                    'ready_for_display': True,
                    'ready_for_export': True
                },
                'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                'metadata': {
                    'task_id': task_id,
                    'stages_completed': ['semantic_analysis', 'data_query', 'chart_generation'],
                    'data_quality_score': stage_one_data.get('execution_metadata', {}).get('data_quality_score', 0.8),
                    'chart_complexity': self._assess_chart_complexity(stage_two_data)
                }
            }
            
            logger.info(f"任务图表生成完成: {placeholder_text}, 耗时: {final_result['processing_time_ms']:.2f}ms")
            
            return final_result
            
        except Exception as e:
            logger.error(f"任务图表生成流程执行失败: {e}")
            return self._create_task_error_result("orchestration", str(e), start_time)
    
    async def _execute_semantic_analysis(self, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """执行语义分析（可选步骤）"""
        try:
            placeholder_text = context.get_context('placeholder_text', '')
            execution_mode = context.get_context('execution_mode', 'test_with_chart')
            
            # 检查是否需要图表分析
            needs_chart_analysis = (
                execution_mode in ['test_with_chart', 'full_pipeline'] and
                any(keyword in placeholder_text.lower() for keyword in ['图表', '柱状图', '饼图', '折线图', '散点图', '雷达图', '漏斗图'])
            )
            
            if needs_chart_analysis:
                # 执行语义分析以优化后续步骤
                semantic_result = await self.semantic_agent.execute(context)
                
                # 增强语义分析结果，添加图表类型提示
                if semantic_result.get('success'):
                    semantic_data = semantic_result.get('data', {})
                    
                    # 根据占位符文本推断图表类型
                    chart_type_hint = self._infer_chart_type_from_text(placeholder_text)
                    semantic_data['chart_type_hint'] = chart_type_hint
                    semantic_data['is_chart_request'] = True
                    
                    semantic_result['data'] = semantic_data
                
                return semantic_result
            else:
                # 非图表模式，提供基础语义分析
                return {
                    'success': True,
                    'data': {
                        'primary_intent': 'data_query',
                        'data_type': 'statistical',
                        'chart_type_hint': None,
                        'is_chart_request': False,
                        'confidence': 0.8
                    }
                }
                
        except Exception as e:
            logger.warning(f"语义分析失败，使用默认配置: {e}")
            return {
                'success': False,
                'data': {
                    'primary_intent': 'data_query',
                    'chart_type_hint': None,
                    'is_chart_request': False,
                    'confidence': 0.5
                }
            }
    
    def _infer_chart_type_from_text(self, text: str) -> str:
        """从文本推断图表类型"""
        text_lower = text.lower()
        
        # 图表类型关键词映射
        chart_keywords = {
            'bar_chart': ['柱状图', '柱形图', '条形图', '对比'],
            'pie_chart': ['饼图', '饼状图', '占比', '比例', '份额'],
            'line_chart': ['折线图', '线图', '趋势', '变化', '时间'],
            'scatter_chart': ['散点图', '散布图', '关系', '相关'],
            'radar_chart': ['雷达图', '蛛网图', '多维', '综合'],
            'funnel_chart': ['漏斗图', '转化', '流程', '阶段']
        }
        
        for chart_type, keywords in chart_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return chart_type
        
        # 默认返回柱状图
        return 'bar_chart'
    
    def _create_execution_context(
        self,
        placeholder_text: str,
        data_source_id: str,
        user_id: str,
        template_id: Optional[str] = None
    ) -> EnhancedExecutionContext:
        """创建执行上下文"""
        import uuid
        
        context = EnhancedExecutionContext(
            session_id=f"chart_{uuid.uuid4()}",
            user_id=user_id,
            request={}
        )
        
        # 设置基础上下文数据
        context.set_context('placeholder_text', placeholder_text, ContextScope.REQUEST)
        context.set_context('data_source_context', {'data_source_id': data_source_id}, ContextScope.REQUEST)
        
        if template_id:
            context.set_context('template_context', {'template_id': template_id}, ContextScope.REQUEST)
        
        return context
    
    def _assess_chart_complexity(self, chart_data: Dict[str, Any]) -> str:
        """评估图表复杂度"""
        try:
            echarts_config = chart_data.get('echarts_config', {})
            series_count = len(echarts_config.get('series', []))
            data_points = chart_data.get('metadata', {}).get('data_points', 0)
            
            if series_count > 3 or data_points > 50:
                return 'high'
            elif series_count > 1 or data_points > 10:
                return 'medium'
            else:
                return 'low'
                
        except:
            return 'unknown'
    
    def _create_template_error_result(self, stage: str, error_msg: str, start_time: datetime, 
                                     partial_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建模板错误结果"""
        result = {
            'success': False,
            'stage': f'{stage}_error',
            'execution_mode': 'template_placeholder',
            'error': f'{stage}阶段失败: {error_msg}',
            'data': partial_data or {},
            'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
            'troubleshooting': self._get_troubleshooting_tips(stage)
        }
        
        # 如果有部分成功的数据，标记为部分成功
        if partial_data:
            result['partial_success'] = True
            result['success_stages'] = []
            if partial_data.get('sql_query'):
                result['success_stages'].append('sql_generation')
            if partial_data.get('raw_data'):
                result['success_stages'].append('data_query')
        
        return result
    
    def _create_task_error_result(self, stage: str, error_msg: str, start_time: datetime) -> Dict[str, Any]:
        """创建任务错误结果"""
        return {
            'success': False,
            'stage': f'{stage}_error', 
            'execution_mode': 'task_execution',
            'error': f'{stage}阶段失败: {error_msg}',
            'data': {},
            'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
            'recovery_suggestions': self._get_recovery_suggestions(stage)
        }
    
    def _get_troubleshooting_tips(self, stage: str) -> List[str]:
        """获取故障排除提示"""
        tips_map = {
            'stage_one': [
                "检查数据源连接是否正常",
                "验证SQL查询语法是否正确", 
                "确认表结构是否存在"
            ],
            'stage_two': [
                "检查数据格式是否符合图表要求",
                "确认图表类型是否支持当前数据结构",
                "验证数据量是否在合理范围内"
            ],
            'orchestration': [
                "检查系统资源是否充足",
                "确认各Agent服务是否正常",
                "查看详细日志获取更多信息"
            ]
        }
        return tips_map.get(stage, ["请联系系统管理员"])
    
    def _get_recovery_suggestions(self, stage: str) -> List[str]:
        """获取恢复建议"""
        suggestions_map = {
            'data_query': [
                "尝试简化SQL查询",
                "检查数据源性能", 
                "使用缓存数据（如果可用）"
            ],
            'chart_generation': [
                "尝试使用简单图表类型",
                "减少数据点数量",
                "使用默认配置重试"
            ],
            'orchestration': [
                "重启相关服务",
                "清理临时数据",
                "使用简化流程重试"
            ]
        }
        return suggestions_map.get(stage, ["稍后重试或联系技术支持"])


# 全局实例
_global_two_stage_orchestrator = None

def get_two_stage_chart_orchestrator(db_session=None) -> TwoStageChartOrchestrator:
    """获取两阶段图表编排器实例"""
    global _global_two_stage_orchestrator
    if _global_two_stage_orchestrator is None or (_global_two_stage_orchestrator.db_session != db_session):
        _global_two_stage_orchestrator = TwoStageChartOrchestrator(db_session)
    return _global_two_stage_orchestrator