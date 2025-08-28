"""
结果解释Agent - 对分析结果和图表进行自然语言解释和洞察生成

功能特性：
- 数据结果的自然语言描述
- 关键洞察的提取和表达
- 业务建议的生成
- 趋势分析的文字解释
- 异常值的说明
- 报告级别的结构化叙述
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re

from ..base import BaseAgent
from ...context.execution_context import EnhancedExecutionContext, ContextScope

logger = logging.getLogger(__name__)


class InsightNarratorAgent(BaseAgent):
    """结果解释Agent"""
    
    def __init__(self):
        super().__init__("insight_narrator", ["narrative_generation", "insight_extraction", "text_generation"])
        self.require_context("analysis_result", "chart_config", "parsed_request")
        
        # 叙述模板
        self.narrative_templates = {
            'statistics': self._generate_statistics_narrative,
            'bar_chart': self._generate_bar_chart_narrative,
            'pie_chart': self._generate_pie_chart_narrative,
            'line_chart': self._generate_line_chart_narrative,
            'table': self._generate_table_narrative
        }
        
        # 数值描述词汇
        self.value_descriptors = {
            'increase': ['上升', '增长', '提升', '增加', '攀升'],
            'decrease': ['下降', '减少', '降低', '衰减', '下滑'],
            'stable': ['稳定', '持平', '维持', '保持'],
            'high': ['较高', '偏高', '显著', '突出'],
            'low': ['较低', '偏低', '微弱', '有限'],
            'significant': ['显著', '明显', '重要', '关键'],
            'moderate': ['适中', '中等', '一般', '正常']
        }
        
        # 时间表达
        self.time_expressions = {
            'recent': ['近期', '最近', '当前'],
            'past': ['过去', '之前', '历史'],
            'future': ['未来', '接下来', '后续'],
            'trend': ['趋势', '走势', '态势', '发展']
        }

    async def execute(self, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """执行结果解释"""
        try:
            # 获取必要的上下文
            analysis_result = context.get_context("analysis_result")
            chart_config = context.get_context("chart_config") 
            parsed_request = context.get_context("parsed_request")
            
            if not analysis_result:
                return {
                    "success": False,
                    "error": "缺少分析结果",
                    "data": {}
                }
            
            # 处理多个结果
            if isinstance(analysis_result, dict) and 'analysis_results' in analysis_result:
                return await self._narrate_multiple_results(analysis_result, chart_config, parsed_request, context)
            else:
                return await self._narrate_single_result(analysis_result, chart_config, parsed_request, context)
                
        except Exception as e:
            logger.error(f"结果解释Agent执行失败: {e}")
            return {
                "success": False,
                "error": f"结果解释失败: {str(e)}",
                "data": {}
            }

    async def _narrate_multiple_results(self, analysis_results: Dict[str, Any],
                                      chart_configs: Dict[str, Any], 
                                      parsed_requests: Dict[str, Any],
                                      context: EnhancedExecutionContext) -> Dict[str, Any]:
        """解释多个结果"""
        narratives = []
        
        for i, analysis_result in enumerate(analysis_results.get('analysis_results', [])):
            if not analysis_result.get('success', False):
                continue
                
            try:
                # 获取对应的配置
                placeholder_index = analysis_result.get('placeholder_index', i)
                
                chart_config = None
                if isinstance(chart_configs, dict) and 'chart_results' in chart_configs:
                    for chart in chart_configs['chart_results']:
                        if chart.get('placeholder_index') == placeholder_index:
                            chart_config = chart
                            break
                
                parsed_request = None
                if isinstance(parsed_requests, dict) and 'placeholders' in parsed_requests:
                    placeholders = parsed_requests['placeholders']
                    if 0 <= placeholder_index < len(placeholders):
                        parsed_request = placeholders[placeholder_index]
                
                if not parsed_request:
                    continue
                
                # 生成单个叙述
                narrative = await self._create_narrative(analysis_result, chart_config, parsed_request, context)
                
                narrative['placeholder_index'] = placeholder_index
                narrative['original_text'] = analysis_result.get('original_text', '')
                narratives.append(narrative)
                
                # 存储到上下文
                context.set_context(f"narrative_{placeholder_index}", narrative, ContextScope.REQUEST)
                
            except Exception as e:
                logger.error(f"解释第{placeholder_index}个结果失败: {e}")
                narratives.append({
                    'placeholder_index': placeholder_index,
                    'success': False,
                    'error': str(e)
                })
        
        # 生成综合报告
        comprehensive_report = await self._generate_comprehensive_report(narratives, context)
        
        return {
            "success": True,
            "data": {
                "individual_narratives": narratives,
                "comprehensive_report": comprehensive_report,
                "summary": {
                    "total_narratives": len(narratives),
                    "successful_narratives": sum(1 for n in narratives if n.get('success', False))
                }
            }
        }

    async def _narrate_single_result(self, analysis_result: Dict[str, Any],
                                   chart_config: Dict[str, Any],
                                   parsed_request: Dict[str, Any], 
                                   context: EnhancedExecutionContext) -> Dict[str, Any]:
        """解释单个结果"""
        narrative = await self._create_narrative(analysis_result, chart_config, parsed_request, context)
        context.set_context("narrative", narrative, ContextScope.REQUEST)
        
        return {
            "success": True,
            "data": narrative
        }

    async def _create_narrative(self, analysis_result: Dict[str, Any],
                              chart_config: Optional[Dict[str, Any]], 
                              parsed_request: Dict[str, Any],
                              context: EnhancedExecutionContext) -> Dict[str, Any]:
        """创建叙述"""
        task_type = parsed_request.get('task_type', 'statistics')
        metric = parsed_request.get('metric', '数据指标')
        
        logger.info(f"生成叙述: {task_type} - {metric}")
        
        # 选择叙述生成器
        narrator = self.narrative_templates.get(task_type, self._generate_default_narrative)
        
        # 生成主要叙述
        main_narrative = narrator(analysis_result, chart_config, parsed_request)
        
        # 提取洞察
        insights = self._extract_key_insights(analysis_result, parsed_request)
        
        # 生成建议
        recommendations = self._generate_actionable_recommendations(analysis_result, parsed_request)
        
        # 构造结构化叙述
        structured_narrative = self._build_structured_narrative(
            main_narrative, insights, recommendations, analysis_result, parsed_request
        )
        
        return {
            "success": True,
            "task_type": task_type,
            "metric": metric,
            "narrative_text": main_narrative,
            "key_insights": insights,
            "recommendations": recommendations,
            "structured_narrative": structured_narrative,
            "narrative_metadata": {
                "word_count": len(main_narrative),
                "insight_count": len(insights),
                "recommendation_count": len(recommendations),
                "generation_time": datetime.now().isoformat()
            }
        }

    def _generate_statistics_narrative(self, analysis_result: Dict[str, Any],
                                     chart_config: Optional[Dict[str, Any]],
                                     parsed_request: Dict[str, Any]) -> str:
        """生成统计数据叙述"""
        metric = parsed_request.get('metric', '数据指标')
        statistics = analysis_result.get('statistics', {})
        
        narrative_parts = [f"基于{metric}的统计分析结果显示："]
        
        # 查找主要的数值统计
        main_stats = None
        for key, value in statistics.items():
            if isinstance(value, dict) and 'sum' in value:
                main_stats = value
                break
        
        if main_stats:
            total = main_stats.get('sum', 0)
            mean = main_stats.get('mean', 0)
            count = main_stats.get('count', 0)
            max_val = main_stats.get('max', 0)
            min_val = main_stats.get('min', 0)
            
            narrative_parts.append(f"总计{metric}达到{total:.2f}")
            
            if count > 1:
                narrative_parts.append(f"平均值为{mean:.2f}")
                narrative_parts.append(f"最高值为{max_val:.2f}，最低值为{min_val:.2f}")
                
                # 变异程度分析
                std = main_stats.get('std', 0)
                if std > 0 and mean > 0:
                    cv = std / mean
                    if cv > 0.3:
                        narrative_parts.append(f"数据波动较大（变异系数{cv:.2f}）")
                    elif cv < 0.1:
                        narrative_parts.append("数据相对稳定")
        
        # 添加洞察
        insights = analysis_result.get('insights', [])
        if insights:
            top_insight = insights[0]
            narrative_parts.append(f"值得注意的是，{top_insight.get('description', '')}")
        
        return "。".join(narrative_parts) + "。"

    def _generate_bar_chart_narrative(self, analysis_result: Dict[str, Any],
                                    chart_config: Optional[Dict[str, Any]],
                                    parsed_request: Dict[str, Any]) -> str:
        """生成柱状图叙述"""
        metric = parsed_request.get('metric', '数据指标')
        dimensions = parsed_request.get('dimensions', ['类别'])
        dimension = dimensions[0] if dimensions else '类别'
        
        # 从分析结果获取分类统计
        category_analysis = analysis_result.get('statistics', {}).get('category_analysis', {})
        
        narrative_parts = [f"从{metric}的{dimension}分布来看："]
        
        if category_analysis:
            top_category = category_analysis.get('top_category')
            top_value = category_analysis.get('top_category_value', 0)
            bottom_category = category_analysis.get('bottom_category')
            bottom_value = category_analysis.get('bottom_category_value', 0)
            concentration_ratio = category_analysis.get('concentration_ratio', 0)
            
            if top_category:
                narrative_parts.append(f"{top_category}表现最为突出，{metric}达到{top_value:.2f}")
                
            if bottom_category and bottom_category != top_category:
                narrative_parts.append(f"而{bottom_category}相对较低，为{bottom_value:.2f}")
            
            # 集中度分析
            if concentration_ratio > 0.5:
                narrative_parts.append(f"数据显示{dimension}分布不均，最大{dimension}占比达{concentration_ratio:.1%}")
            elif concentration_ratio < 0.2:
                narrative_parts.append(f"各{dimension}之间分布相对均衡")
        
        # 添加趋势描述
        insights = analysis_result.get('insights', [])
        dominance_insights = [i for i in insights if i.get('type') == 'dominance']
        if dominance_insights:
            insight = dominance_insights[0]
            narrative_parts.append(insight.get('description', ''))
        
        return "。".join(narrative_parts) + "。"

    def _generate_pie_chart_narrative(self, analysis_result: Dict[str, Any],
                                    chart_config: Optional[Dict[str, Any]],
                                    parsed_request: Dict[str, Any]) -> str:
        """生成饼状图叙述"""
        metric = parsed_request.get('metric', '数据指标')
        
        # 获取分类分析
        category_analysis = analysis_result.get('statistics', {}).get('category_analysis', {})
        
        narrative_parts = [f"从{metric}的占比分析可以看出："]
        
        if category_analysis:
            top_category = category_analysis.get('top_category')
            concentration_ratio = category_analysis.get('concentration_ratio', 0)
            category_count = category_analysis.get('category_count', 0)
            
            if top_category:
                narrative_parts.append(f"{top_category}占据主导地位，比重为{concentration_ratio:.1%}")
                
                if concentration_ratio > 0.6:
                    narrative_parts.append("显示出明显的集中特征")
                elif concentration_ratio < 0.3:
                    narrative_parts.append("各部分相对均衡")
            
            if category_count > 5:
                narrative_parts.append(f"共包含{category_count}个分类，呈现多元化格局")
        
        # 添加集中度洞察
        insights = analysis_result.get('insights', [])
        concentration_insights = [i for i in insights if i.get('type') == 'concentration']
        if concentration_insights:
            insight = concentration_insights[0]
            narrative_parts.append(insight.get('description', ''))
        
        return "。".join(narrative_parts) + "。"

    def _generate_line_chart_narrative(self, analysis_result: Dict[str, Any],
                                     chart_config: Optional[Dict[str, Any]],
                                     parsed_request: Dict[str, Any]) -> str:
        """生成折线图叙述"""
        metric = parsed_request.get('metric', '数据指标')
        time_range = parsed_request.get('time_range', {})
        
        narrative_parts = []
        
        # 时间范围描述
        if time_range:
            time_desc = time_range.get('description', '指定时间段')
            narrative_parts.append(f"在{time_desc}内，{metric}的变化趋势表现为：")
        else:
            narrative_parts.append(f"{metric}的时间序列分析显示：")
        
        # 趋势分析
        trend_analysis = analysis_result.get('statistics', {}).get('trend_analysis', {})
        trends = analysis_result.get('trends', {})
        
        if trends.get('detected'):
            linear_trend = trends.get('linear_trend', {})
            direction = linear_trend.get('direction', 'stable')
            r_squared = linear_trend.get('r_squared', 0)
            
            direction_desc = {
                'increasing': '整体呈上升趋势',
                'decreasing': '整体呈下降趋势', 
                'stable': '整体保持稳定'
            }.get(direction, '趋势不明显')
            
            narrative_parts.append(direction_desc)
            
            if r_squared > 0.8:
                narrative_parts.append("趋势性非常明显")
            elif r_squared > 0.5:
                narrative_parts.append("具有一定的趋势性")
        
        if trend_analysis:
            avg_growth = trend_analysis.get('average_growth_rate', 0)
            positive_periods = trend_analysis.get('positive_periods', 0)
            negative_periods = trend_analysis.get('negative_periods', 0)
            
            if avg_growth > 0.05:
                narrative_parts.append(f"平均增长率为{avg_growth:.1%}")
            elif avg_growth < -0.05:
                narrative_parts.append(f"平均下降率为{abs(avg_growth):.1%}")
            
            total_periods = positive_periods + negative_periods
            if total_periods > 0:
                positive_ratio = positive_periods / total_periods
                if positive_ratio > 0.7:
                    narrative_parts.append("大部分时期表现为正增长")
                elif positive_ratio < 0.3:
                    narrative_parts.append("多数时期出现下降")
        
        # 极值分析
        insights = analysis_result.get('insights', [])
        extreme_insights = [i for i in insights if i.get('type') == 'extremes']
        if extreme_insights:
            insight = extreme_insights[0]
            data_points = insight.get('data_points', [])
            if data_points:
                max_point = next((p for p in data_points if 'max_index' in p), None)
                min_point = next((p for p in data_points if 'min_index' in p), None)
                
                if max_point and min_point:
                    narrative_parts.append(f"峰值出现在第{max_point['max_index']+1}个时间点，谷值在第{min_point['min_index']+1}个时间点")
        
        return "。".join(narrative_parts) + "。"

    def _generate_table_narrative(self, analysis_result: Dict[str, Any],
                                chart_config: Optional[Dict[str, Any]],
                                parsed_request: Dict[str, Any]) -> str:
        """生成表格叙述"""
        metric = parsed_request.get('metric', '数据')
        data_summary = analysis_result.get('data_summary', {})
        
        narrative_parts = [f"{metric}的详细数据显示："]
        
        row_count = data_summary.get('row_count', 0)
        column_count = data_summary.get('column_count', 0)
        
        narrative_parts.append(f"共包含{row_count}条记录，涉及{column_count}个字段")
        
        numeric_columns = data_summary.get('numeric_columns', [])
        categorical_columns = data_summary.get('categorical_columns', [])
        
        if numeric_columns:
            narrative_parts.append(f"其中{len(numeric_columns)}个数值字段")
        if categorical_columns:
            narrative_parts.append(f"{len(categorical_columns)}个分类字段")
        
        # 数据质量描述
        has_missing = data_summary.get('has_missing_values', False)
        if has_missing:
            narrative_parts.append("数据存在部分缺失值，需要关注数据完整性")
        else:
            narrative_parts.append("数据完整性良好")
        
        return "。".join(narrative_parts) + "。"

    def _generate_default_narrative(self, analysis_result: Dict[str, Any],
                                  chart_config: Optional[Dict[str, Any]],
                                  parsed_request: Dict[str, Any]) -> str:
        """生成默认叙述"""
        metric = parsed_request.get('metric', '数据指标')
        task_type = parsed_request.get('task_type', '分析')
        
        narrative_parts = [f"基于{metric}的{task_type}分析："]
        
        # 基础数据描述
        data_summary = analysis_result.get('data_summary', {})
        row_count = data_summary.get('row_count', 0)
        
        if row_count > 0:
            narrative_parts.append(f"分析了{row_count}个数据点")
        
        # 添加主要洞察
        insights = analysis_result.get('insights', [])
        if insights:
            top_insights = insights[:2]  # 取前2个洞察
            for insight in top_insights:
                description = insight.get('description', '')
                if description:
                    narrative_parts.append(description)
        
        return "。".join(narrative_parts) + "。"

    def _extract_key_insights(self, analysis_result: Dict[str, Any], 
                            parsed_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取关键洞察"""
        insights = analysis_result.get('insights', [])
        
        # 过滤和增强洞察
        enhanced_insights = []
        
        for insight in insights[:5]:  # 最多5个洞察
            enhanced_insight = {
                "type": insight.get('type', 'general'),
                "title": insight.get('title', ''),
                "description": insight.get('description', ''),
                "importance": insight.get('importance', 0.5),
                "confidence": insight.get('confidence', 0.5),
                "business_impact": self._assess_business_impact(insight, parsed_request)
            }
            
            enhanced_insights.append(enhanced_insight)
        
        # 按重要性排序
        enhanced_insights.sort(key=lambda x: x['importance'], reverse=True)
        
        return enhanced_insights

    def _assess_business_impact(self, insight: Dict[str, Any], 
                              parsed_request: Dict[str, Any]) -> str:
        """评估业务影响"""
        insight_type = insight.get('type', '')
        metric = parsed_request.get('metric', '')
        
        impact_templates = {
            'trend': '该趋势可能影响未来的业务规划和资源配置',
            'dominance': '主导地位的维持或变化将直接影响整体业绩',
            'anomaly': '异常情况需要及时关注和处理，避免潜在风险',
            'concentration': '集中度变化可能影响业务的稳定性和多样性',
            'growth': '增长态势为业务发展提供了重要参考',
            'distribution': '分布特征有助于优化资源分配和策略制定'
        }
        
        return impact_templates.get(insight_type, '该发现对业务决策具有参考价值')

    def _generate_actionable_recommendations(self, analysis_result: Dict[str, Any],
                                           parsed_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成可执行建议"""
        recommendations = analysis_result.get('recommendations', [])
        
        # 增强建议
        enhanced_recommendations = []
        
        for rec in recommendations:
            enhanced_rec = {
                "type": rec.get('type', 'general'),
                "title": rec.get('title', ''),
                "description": rec.get('description', ''),
                "priority": rec.get('priority', 'medium'),
                "timeframe": self._estimate_timeframe(rec),
                "expected_impact": self._estimate_impact(rec, parsed_request)
            }
            
            enhanced_recommendations.append(enhanced_rec)
        
        # 添加通用建议
        if len(enhanced_recommendations) < 3:
            generic_recommendations = self._generate_generic_recommendations(analysis_result, parsed_request)
            enhanced_recommendations.extend(generic_recommendations)
        
        return enhanced_recommendations[:5]  # 最多5个建议

    def _estimate_timeframe(self, recommendation: Dict[str, Any]) -> str:
        """估计执行时间框架"""
        rec_type = recommendation.get('type', '')
        priority = recommendation.get('priority', 'medium')
        
        timeframes = {
            'alert': '立即执行',
            'data_quality': '1-2周内',
            'data_collection': '1个月内', 
            'action': '2-4周内',
            'balance': '1-3个月内',
            'optimization': '持续进行'
        }
        
        if priority == 'high':
            return '紧急处理'
        
        return timeframes.get(rec_type, '1个月内')

    def _estimate_impact(self, recommendation: Dict[str, Any], parsed_request: Dict[str, Any]) -> str:
        """估计预期影响"""
        rec_type = recommendation.get('type', '')
        metric = parsed_request.get('metric', '')
        
        impact_descriptions = {
            'alert': f'及时响应可避免{metric}进一步恶化',
            'data_quality': '提升数据准确性，改善分析质量',
            'data_collection': '增加样本量，提高分析可信度',
            'action': f'预期对{metric}产生积极影响',
            'balance': '促进均衡发展，降低风险',
            'optimization': '持续改进，逐步提升效果'
        }
        
        return impact_descriptions.get(rec_type, '对业务产生正面影响')

    def _generate_generic_recommendations(self, analysis_result: Dict[str, Any],
                                        parsed_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成通用建议"""
        generic_recs = []
        task_type = parsed_request.get('task_type', '')
        
        # 基于任务类型的通用建议
        if task_type == 'line_chart':
            trends = analysis_result.get('trends', {})
            if trends.get('detected'):
                direction = trends.get('linear_trend', {}).get('direction', 'stable')
                if direction == 'increasing':
                    generic_recs.append({
                        "type": "monitoring",
                        "title": "持续监控上升趋势",
                        "description": "建议密切关注趋势持续性，制定相应的应对策略",
                        "priority": "medium",
                        "timeframe": "持续进行",
                        "expected_impact": "确保趋势可持续发展"
                    })
                elif direction == 'decreasing':
                    generic_recs.append({
                        "type": "intervention",
                        "title": "制定改进措施",
                        "description": "针对下降趋势，建议分析原因并制定改进计划",
                        "priority": "high", 
                        "timeframe": "立即执行",
                        "expected_impact": "扭转下降趋势，回复正常水平"
                    })
        
        # 数据质量建议
        data_summary = analysis_result.get('data_summary', {})
        if data_summary.get('has_missing_values'):
            generic_recs.append({
                "type": "data_improvement",
                "title": "完善数据收集机制",
                "description": "建立更完善的数据收集和验证流程",
                "priority": "medium",
                "timeframe": "2-4周内",
                "expected_impact": "提高数据完整性和分析准确性"
            })
        
        return generic_recs

    def _build_structured_narrative(self, main_narrative: str, insights: List[Dict[str, Any]],
                                  recommendations: List[Dict[str, Any]], 
                                  analysis_result: Dict[str, Any],
                                  parsed_request: Dict[str, Any]) -> Dict[str, Any]:
        """构建结构化叙述"""
        metric = parsed_request.get('metric', '数据指标')
        
        return {
            "executive_summary": self._create_executive_summary(main_narrative, insights),
            "detailed_analysis": {
                "overview": main_narrative,
                "key_findings": [insight['description'] for insight in insights[:3]],
                "statistical_summary": self._create_statistical_summary(analysis_result)
            },
            "insights_section": {
                "critical_insights": [i for i in insights if i.get('importance', 0) > 0.7],
                "supporting_insights": [i for i in insights if i.get('importance', 0) <= 0.7],
                "business_implications": [i.get('business_impact', '') for i in insights]
            },
            "recommendations_section": {
                "immediate_actions": [r for r in recommendations if r.get('priority') == 'high'],
                "medium_term_actions": [r for r in recommendations if r.get('priority') == 'medium'],
                "long_term_strategies": [r for r in recommendations if r.get('priority') == 'low']
            },
            "conclusion": self._create_conclusion(main_narrative, insights, recommendations, metric)
        }

    def _create_executive_summary(self, main_narrative: str, insights: List[Dict[str, Any]]) -> str:
        """创建执行摘要"""
        summary_parts = []
        
        # 提取主要发现
        key_finding = main_narrative.split('。')[1] if '。' in main_narrative else main_narrative
        summary_parts.append(key_finding)
        
        # 添加最重要的洞察
        if insights:
            top_insight = insights[0]
            summary_parts.append(top_insight.get('description', ''))
        
        # 总结性陈述
        if len(insights) > 1:
            summary_parts.append(f"分析发现了{len(insights)}个关键洞察，需要重点关注")
        
        return "。".join(summary_parts) + "。"

    def _create_statistical_summary(self, analysis_result: Dict[str, Any]) -> Dict[str, str]:
        """创建统计摘要"""
        statistics = analysis_result.get('statistics', {})
        summary = {}
        
        # 查找主要统计指标
        for key, value in statistics.items():
            if isinstance(value, dict):
                if 'sum' in value:
                    summary['总计'] = f"{value['sum']:.2f}"
                if 'mean' in value:
                    summary['平均值'] = f"{value['mean']:.2f}"
                if 'count' in value:
                    summary['数据点数'] = str(value['count'])
        
        # 添加趋势信息
        trends = analysis_result.get('trends', {})
        if trends.get('detected'):
            direction = trends.get('linear_trend', {}).get('direction', 'stable')
            trend_map = {'increasing': '上升', 'decreasing': '下降', 'stable': '稳定'}
            summary['趋势方向'] = trend_map.get(direction, '未知')
        
        return summary

    def _create_conclusion(self, main_narrative: str, insights: List[Dict[str, Any]],
                         recommendations: List[Dict[str, Any]], metric: str) -> str:
        """创建结论"""
        conclusion_parts = []
        
        # 总体评估
        high_importance_insights = [i for i in insights if i.get('importance', 0) > 0.7]
        if high_importance_insights:
            conclusion_parts.append(f"综合分析显示，{metric}存在{len(high_importance_insights)}个重要特征")
        
        # 趋势总结
        trend_insights = [i for i in insights if i.get('type') == 'trend']
        if trend_insights:
            conclusion_parts.append("从趋势角度看，数据表现出明确的方向性")
        
        # 建议总结
        high_priority_recs = [r for r in recommendations if r.get('priority') == 'high']
        if high_priority_recs:
            conclusion_parts.append(f"建议优先关注{len(high_priority_recs)}项关键措施")
        
        # 结尾
        conclusion_parts.append("持续监控和优化将有助于实现更好的业务表现")
        
        return "。".join(conclusion_parts) + "。"

    async def _generate_comprehensive_report(self, narratives: List[Dict[str, Any]], 
                                           context: EnhancedExecutionContext) -> Dict[str, Any]:
        """生成综合报告"""
        successful_narratives = [n for n in narratives if n.get('success', False)]
        
        if not successful_narratives:
            return {
                "summary": "无法生成综合报告，所有叙述生成失败",
                "sections": {}
            }
        
        # 收集所有洞察和建议
        all_insights = []
        all_recommendations = []
        
        for narrative in successful_narratives:
            all_insights.extend(narrative.get('key_insights', []))
            all_recommendations.extend(narrative.get('recommendations', []))
        
        # 生成综合摘要
        comprehensive_summary = self._generate_comprehensive_summary(successful_narratives)
        
        # 组织综合洞察
        comprehensive_insights = self._organize_comprehensive_insights(all_insights)
        
        # 整合建议
        comprehensive_recommendations = self._consolidate_recommendations(all_recommendations)
        
        return {
            "summary": comprehensive_summary,
            "sections": {
                "overview": f"本次分析涵盖了{len(successful_narratives)}个方面的数据",
                "key_insights": comprehensive_insights,
                "recommendations": comprehensive_recommendations,
                "conclusion": "基于多维度分析，建议采取系统性的改进措施"
            },
            "metadata": {
                "narrative_count": len(successful_narratives),
                "total_insights": len(all_insights),
                "total_recommendations": len(all_recommendations)
            }
        }

    def _generate_comprehensive_summary(self, narratives: List[Dict[str, Any]]) -> str:
        """生成综合摘要"""
        summary_parts = [f"综合分析了{len(narratives)}个维度的数据"]
        
        # 统计任务类型
        task_types = [n.get('task_type', '') for n in narratives]
        type_counts = {t: task_types.count(t) for t in set(task_types)}
        
        if len(type_counts) > 1:
            summary_parts.append(f"涵盖{len(type_counts)}种不同类型的分析")
        
        # 提取共同主题
        all_insights = []
        for narrative in narratives:
            all_insights.extend(narrative.get('key_insights', []))
        
        high_importance_count = sum(1 for insight in all_insights if insight.get('importance', 0) > 0.7)
        if high_importance_count > 0:
            summary_parts.append(f"发现{high_importance_count}个高重要性洞察")
        
        return "。".join(summary_parts) + "。"

    def _organize_comprehensive_insights(self, all_insights: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """组织综合洞察"""
        organized = {
            "critical": [],
            "important": [],
            "supporting": []
        }
        
        for insight in all_insights:
            importance = insight.get('importance', 0)
            if importance > 0.8:
                organized["critical"].append(insight)
            elif importance > 0.5:
                organized["important"].append(insight)
            else:
                organized["supporting"].append(insight)
        
        # 去重和排序
        for category in organized:
            organized[category] = sorted(organized[category], key=lambda x: x.get('importance', 0), reverse=True)[:5]
        
        return organized

    def _consolidate_recommendations(self, all_recommendations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """整合建议"""
        consolidated = {
            "immediate": [],
            "short_term": [],
            "long_term": []
        }
        
        for rec in all_recommendations:
            priority = rec.get('priority', 'medium')
            timeframe = rec.get('timeframe', '1个月内')
            
            if priority == 'high' or '立即' in timeframe:
                consolidated["immediate"].append(rec)
            elif '周' in timeframe or '1个月' in timeframe:
                consolidated["short_term"].append(rec)
            else:
                consolidated["long_term"].append(rec)
        
        # 去重和限制数量
        for category in consolidated:
            seen_titles = set()
            unique_recs = []
            for rec in consolidated[category]:
                if rec.get('title') not in seen_titles:
                    unique_recs.append(rec)
                    seen_titles.add(rec.get('title'))
            consolidated[category] = unique_recs[:3]  # 每类最多3个
        
        return consolidated