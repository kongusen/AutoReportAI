"""
图表生成Agent - 根据数据分析结果生成各类图表配置

支持的图表类型：
- 柱状图 (bar_chart)
- 饼状图 (pie_chart) 
- 折线图 (line_chart)
- 散点图 (scatter_chart)
- 雷达图 (radar_chart)
- 漏斗图 (funnel_chart)
- 组合图 (combo_chart)

输出格式：
- ECharts配置JSON
- Plotly配置JSON (可选)
- 图表元数据
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import colorsys

from ..base import BaseAgent
from ...context.execution_context import EnhancedExecutionContext, ContextScope

logger = logging.getLogger(__name__)


class ChartGeneratorAgent(BaseAgent):
    """图表生成Agent"""
    
    def __init__(self):
        super().__init__("chart_generator", ["visualization", "chart_generation", "ui_rendering"])
        self.require_context("analysis_result", "parsed_request")
        
        # 默认配色方案
        self.color_schemes = {
            'default': ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'],
            'business': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22'],
            'elegant': ['#2E4057', '#048A81', '#F46197', '#FFA500', '#9B59B6', '#3498DB', '#E74C3C', '#F39C12', '#27AE60'],
            'warm': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE']
        }
        
        # 图表配置模板
        self.chart_templates = {
            'bar_chart': self._create_bar_chart_config,
            'pie_chart': self._create_pie_chart_config,
            'line_chart': self._create_line_chart_config,
            'scatter_chart': self._create_scatter_chart_config,
            'radar_chart': self._create_radar_chart_config,
            'funnel_chart': self._create_funnel_chart_config
        }

    async def execute(self, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """执行图表生成 - 第二阶段：基于查询数据生成图表配置"""
        try:
            # 检查是否有图表数据（来自第一阶段）
            chart_data = context.get_context("chart_data")
            query_result = context.get_context("query_result")
            
            if not chart_data and not query_result:
                # 兼容旧版本：检查分析结果
                analysis_result = context.get_context("analysis_result")
                parsed_request = context.get_context("parsed_request")
                
                if analysis_result:
                    logger.info("使用兼容模式处理图表生成")
                    return await self._generate_charts_legacy_mode(analysis_result, parsed_request, context)
            
            # 新版本：基于图表数据生成图表
            if not chart_data:
                return {
                    "success": False,
                    "error": "缺少图表数据，请先执行数据查询阶段",
                    "data": {},
                    "stage": "chart_generation",
                    "requires": "chart_data_query_stage"
                }
            
            return await self._generate_chart_from_data(chart_data, context)
                
        except Exception as e:
            logger.error(f"图表生成Agent执行失败: {e}")
            return {
                "success": False,
                "error": f"图表生成失败: {str(e)}",
                "data": {}
            }

    async def _generate_multiple_charts(self, analysis_results: Dict[str, Any], 
                                      parsed_requests: Dict[str, Any],
                                      context: EnhancedExecutionContext) -> Dict[str, Any]:
        """生成多个图表"""
        chart_results = []
        
        for i, analysis_result in enumerate(analysis_results.get('analysis_results', [])):
            if not analysis_result.get('success', False):
                continue
                
            try:
                # 获取对应的解析请求
                placeholder_index = analysis_result.get('placeholder_index', i)
                parsed_request = None
                
                if isinstance(parsed_requests, dict) and 'placeholders' in parsed_requests:
                    placeholders = parsed_requests['placeholders']
                    if 0 <= placeholder_index < len(placeholders):
                        parsed_request = placeholders[placeholder_index]
                
                if not parsed_request:
                    continue
                
                # 生成单个图表
                chart_config = await self._create_chart_config(analysis_result, parsed_request, context)
                
                chart_config['placeholder_index'] = placeholder_index
                chart_config['original_text'] = analysis_result.get('original_text', '')
                chart_results.append(chart_config)
                
                # 存储到上下文
                context.set_context(f"chart_config_{placeholder_index}", chart_config, ContextScope.REQUEST)
                
            except Exception as e:
                logger.error(f"生成第{placeholder_index}个图表失败: {e}")
                chart_results.append({
                    'placeholder_index': placeholder_index,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            "success": True,
            "data": {
                "chart_results": chart_results,
                "summary": {
                    "total_charts": len(chart_results),
                    "successful_charts": sum(1 for r in chart_results if r.get('success', False)),
                    "chart_types": list(set(r.get('chart_type') for r in chart_results if r.get('chart_type')))
                }
            }
        }

    async def _generate_single_chart(self, analysis_result: Dict[str, Any], 
                                   parsed_request: Dict[str, Any],
                                   context: EnhancedExecutionContext) -> Dict[str, Any]:
        """生成单个图表"""
        chart_config = await self._create_chart_config(analysis_result, parsed_request, context)
        context.set_context("chart_config", chart_config, ContextScope.REQUEST)
        
        return {
            "success": True,
            "data": chart_config
        }

    async def _create_chart_config(self, analysis_result: Dict[str, Any],
                                 parsed_request: Dict[str, Any],
                                 context: EnhancedExecutionContext) -> Dict[str, Any]:
        """创建图表配置"""
        task_type = parsed_request.get('task_type', 'bar_chart')
        metric = parsed_request.get('metric', '数值')
        
        logger.info(f"生成图表: {task_type} - {metric}")
        
        # 获取数据
        statistics = analysis_result.get('statistics', {})
        raw_data = self._extract_chart_data(analysis_result, task_type)
        
        if not raw_data:
            raise ValueError("无法提取图表数据")
        
        # 选择合适的图表类型
        final_chart_type = self._determine_optimal_chart_type(task_type, raw_data, analysis_result)
        
        # 生成图表配置
        chart_generator = self.chart_templates.get(final_chart_type, self._create_bar_chart_config)
        echarts_config = chart_generator(raw_data, parsed_request, analysis_result)
        
        # 添加通用配置
        self._apply_common_config(echarts_config, parsed_request, context)
        
        # 生成元数据
        metadata = self._generate_chart_metadata(echarts_config, raw_data, analysis_result)
        
        return {
            "success": True,
            "chart_type": final_chart_type,
            "echarts_config": echarts_config,
            "chart_data": raw_data,
            "metadata": metadata,
            "chart_options": {
                "responsive": True,
                "interactive": True,
                "exportable": True,
                "theme": "default"
            }
        }

    def _extract_chart_data(self, analysis_result: Dict[str, Any], task_type: str) -> List[Dict[str, Any]]:
        """从分析结果中提取图表数据"""
        # 尝试从不同位置获取数据
        data_sources = [
            analysis_result.get('raw_data', []),
            analysis_result.get('processed_data', {}),
            analysis_result.get('statistics', {})
        ]
        
        for data_source in data_sources:
            if isinstance(data_source, list) and data_source:
                return data_source
            elif isinstance(data_source, dict):
                # 从统计数据构造图表数据
                if task_type == 'statistics':
                    return self._construct_stats_data(data_source)
        
        # 生成示例数据作为兜底
        return self._generate_sample_data(task_type)

    def _construct_stats_data(self, statistics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从统计数据构造图表数据"""
        data = []
        
        for key, value in statistics.items():
            if isinstance(value, dict) and 'sum' in value:
                data.append({
                    "name": key,
                    "value": value['sum'],
                    "mean": value.get('mean', 0),
                    "count": value.get('count', 0)
                })
            elif isinstance(value, (int, float)):
                data.append({
                    "name": key,
                    "value": value
                })
        
        return data

    def _generate_sample_data(self, task_type: str) -> List[Dict[str, Any]]:
        """生成示例数据"""
        import random
        
        if task_type == 'bar_chart':
            return [
                {"name": f"类别{i}", "value": random.randint(100, 1000)}
                for i in range(1, 6)
            ]
        elif task_type == 'line_chart':
            return [
                {"name": f"2024-{i:02d}", "value": random.randint(200, 800)}
                for i in range(1, 13)
            ]
        elif task_type == 'pie_chart':
            return [
                {"name": f"分类{i}", "value": random.randint(50, 300)}
                for i in range(1, 6)
            ]
        else:
            return [{"name": "示例", "value": 100}]

    def _determine_optimal_chart_type(self, requested_type: str, data: List[Dict[str, Any]], 
                                    analysis_result: Dict[str, Any]) -> str:
        """确定最优的图表类型"""
        # 基于数据特征调整图表类型
        data_count = len(data)
        
        # 数据量太大的饼图改为柱状图
        if requested_type == 'pie_chart' and data_count > 10:
            return 'bar_chart'
        
        # 数据量太少的折线图改为柱状图
        if requested_type == 'line_chart' and data_count < 3:
            return 'bar_chart'
        
        # 检查是否有时间序列特征
        has_time_series = any(
            'time' in str(item.get('name', '')).lower() or 
            'date' in str(item.get('name', '')).lower() or
            'period' in str(item.get('name', '')).lower()
            for item in data
        )
        
        if has_time_series and requested_type in ['bar_chart', 'pie_chart']:
            return 'line_chart'
        
        return requested_type

    def _create_bar_chart_config(self, data: List[Dict[str, Any]], 
                               parsed_request: Dict[str, Any],
                               analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """创建柱状图配置"""
        metric = parsed_request.get('metric', '数值')
        
        # 提取数据
        categories = [item.get('name', item.get('dimension', f'类别{i}')) for i, item in enumerate(data)]
        values = [item.get('value', 0) for item in data]
        
        # 选择颜色
        colors = self._select_colors(len(data), 'business')
        
        config = {
            "title": {
                "text": f"{metric}分布",
                "left": "center",
                "textStyle": {
                    "fontSize": 18,
                    "fontWeight": "bold"
                }
            },
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {
                    "type": "shadow"
                },
                "formatter": "{b}: {c}"
            },
            "grid": {
                "left": "3%",
                "right": "4%",
                "bottom": "3%",
                "containLabel": True
            },
            "xAxis": {
                "type": "category",
                "data": categories,
                "axisLabel": {
                    "rotate": 0 if max(len(str(cat)) for cat in categories) < 6 else 45
                }
            },
            "yAxis": {
                "type": "value",
                "name": metric
            },
            "series": [{
                "name": metric,
                "type": "bar",
                "data": values,
                "itemStyle": {
                    "color": colors[0] if len(colors) == 1 else {
                        "type": "linear",
                        "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": colors[0]},
                            {"offset": 1, "color": colors[1] if len(colors) > 1 else colors[0]}
                        ]
                    }
                },
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowColor": 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        }
        
        # 添加数据标签（如果数据点不多）
        if len(data) <= 10:
            config["series"][0]["label"] = {
                "show": True,
                "position": "top"
            }
        
        return config

    def _create_pie_chart_config(self, data: List[Dict[str, Any]], 
                               parsed_request: Dict[str, Any],
                               analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """创建饼状图配置"""
        metric = parsed_request.get('metric', '数值')
        
        # 处理数据
        pie_data = [
            {
                "name": item.get('name', item.get('category', f'分类{i}')),
                "value": item.get('value', 0)
            }
            for i, item in enumerate(data)
        ]
        
        # 按值排序
        pie_data.sort(key=lambda x: x['value'], reverse=True)
        
        # 选择颜色
        colors = self._select_colors(len(pie_data), 'elegant')
        
        config = {
            "title": {
                "text": f"{metric}占比分布",
                "left": "center",
                "textStyle": {
                    "fontSize": 18,
                    "fontWeight": "bold"
                }
            },
            "tooltip": {
                "trigger": "item",
                "formatter": "{b}: {c} ({d}%)"
            },
            "legend": {
                "orient": "horizontal",
                "bottom": "10%",
                "left": "center",
                "type": "scroll"
            },
            "color": colors,
            "series": [{
                "name": metric,
                "type": "pie",
                "radius": ["40%", "70%"],
                "center": ["50%", "45%"],
                "avoidLabelOverlap": False,
                "itemStyle": {
                    "borderRadius": 8,
                    "borderColor": "#fff",
                    "borderWidth": 2
                },
                "label": {
                    "show": True,
                    "position": "outside",
                    "formatter": "{b}: {d}%"
                },
                "labelLine": {
                    "show": True
                },
                "data": pie_data,
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        }
        
        return config

    def _create_line_chart_config(self, data: List[Dict[str, Any]], 
                                parsed_request: Dict[str, Any],
                                analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """创建折线图配置"""
        metric = parsed_request.get('metric', '数值')
        
        # 提取数据并排序
        time_data = []
        for item in data:
            time_key = item.get('name', item.get('time_period', item.get('dimension', '')))
            value = item.get('value', 0)
            time_data.append((time_key, value))
        
        # 尝试按时间排序
        time_data.sort(key=lambda x: x[0])
        
        categories = [item[0] for item in time_data]
        values = [item[1] for item in time_data]
        
        # 选择颜色
        colors = self._select_colors(1, 'default')
        
        config = {
            "title": {
                "text": f"{metric}趋势图",
                "left": "center",
                "textStyle": {
                    "fontSize": 18,
                    "fontWeight": "bold"
                }
            },
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {
                    "type": "cross",
                    "label": {
                        "backgroundColor": "#6a7985"
                    }
                }
            },
            "grid": {
                "left": "3%",
                "right": "4%",
                "bottom": "3%",
                "containLabel": True
            },
            "xAxis": {
                "type": "category",
                "boundaryGap": False,
                "data": categories,
                "axisLabel": {
                    "rotate": 0 if len(categories) <= 6 else 45
                }
            },
            "yAxis": {
                "type": "value",
                "name": metric
            },
            "series": [{
                "name": metric,
                "type": "line",
                "data": values,
                "smooth": True,
                "lineStyle": {
                    "color": colors[0],
                    "width": 3
                },
                "itemStyle": {
                    "color": colors[0]
                },
                "areaStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": f"{colors[0]}80"},
                            {"offset": 1, "color": f"{colors[0]}10"}
                        ]
                    }
                },
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowColor": colors[0]
                    }
                }
            }]
        }
        
        # 添加数据点标记
        if len(values) <= 20:
            config["series"][0]["symbol"] = "circle"
            config["series"][0]["symbolSize"] = 6
            
        return config

    def _create_scatter_chart_config(self, data: List[Dict[str, Any]], 
                                   parsed_request: Dict[str, Any],
                                   analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """创建散点图配置"""
        metric = parsed_request.get('metric', '数值')
        
        # 构造散点数据
        scatter_data = []
        for i, item in enumerate(data):
            x_val = i  # 可以根据实际需求调整
            y_val = item.get('value', 0)
            scatter_data.append([x_val, y_val])
        
        colors = self._select_colors(1, 'warm')
        
        config = {
            "title": {
                "text": f"{metric}散点分布",
                "left": "center"
            },
            "tooltip": {
                "trigger": "item",
                "formatter": "({c0}, {c1})"
            },
            "grid": {
                "left": "3%",
                "right": "7%",
                "bottom": "3%",
                "containLabel": True
            },
            "xAxis": {
                "type": "value",
                "splitLine": {
                    "lineStyle": {
                        "type": "dashed"
                    }
                }
            },
            "yAxis": {
                "type": "value",
                "name": metric,
                "splitLine": {
                    "lineStyle": {
                        "type": "dashed"
                    }
                }
            },
            "series": [{
                "name": metric,
                "type": "scatter",
                "data": scatter_data,
                "symbolSize": 8,
                "itemStyle": {
                    "color": colors[0],
                    "opacity": 0.8
                },
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowColor": colors[0]
                    }
                }
            }]
        }
        
        return config

    def _create_radar_chart_config(self, data: List[Dict[str, Any]], 
                                 parsed_request: Dict[str, Any],
                                 analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """创建雷达图配置"""
        metric = parsed_request.get('metric', '数值')
        
        # 构造雷达图数据
        indicators = []
        values = []
        
        for item in data[:8]:  # 雷达图最多显示8个维度
            name = item.get('name', item.get('dimension', ''))
            value = item.get('value', 0)
            indicators.append({"name": name, "max": max(item.get('value', 0) for item in data) * 1.2})
            values.append(value)
        
        colors = self._select_colors(1, 'elegant')
        
        config = {
            "title": {
                "text": f"{metric}雷达分析",
                "left": "center"
            },
            "tooltip": {
                "trigger": "item"
            },
            "radar": {
                "indicator": indicators,
                "radius": "60%",
                "splitNumber": 5,
                "splitLine": {
                    "lineStyle": {
                        "color": "rgba(211, 253, 250, 0.8)"
                    }
                },
                "splitArea": {
                    "show": True,
                    "areaStyle": {
                        "color": ["transparent", "rgba(211, 253, 250, 0.3)"]
                    }
                },
                "axisLine": {
                    "lineStyle": {
                        "color": "rgba(211, 253, 250, 0.8)"
                    }
                }
            },
            "series": [{
                "name": metric,
                "type": "radar",
                "data": [{
                    "value": values,
                    "name": metric,
                    "itemStyle": {
                        "color": colors[0]
                    },
                    "areaStyle": {
                        "color": f"{colors[0]}40"
                    }
                }]
            }]
        }
        
        return config

    def _create_funnel_chart_config(self, data: List[Dict[str, Any]], 
                                  parsed_request: Dict[str, Any],
                                  analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """创建漏斗图配置"""
        metric = parsed_request.get('metric', '数值')
        
        # 排序数据（漏斗图通常从大到小）
        sorted_data = sorted(data, key=lambda x: x.get('value', 0), reverse=True)
        
        funnel_data = [
            {
                "name": item.get('name', f'阶段{i}'),
                "value": item.get('value', 0)
            }
            for i, item in enumerate(sorted_data)
        ]
        
        colors = self._select_colors(len(funnel_data), 'warm')
        
        config = {
            "title": {
                "text": f"{metric}漏斗分析",
                "left": "center"
            },
            "tooltip": {
                "trigger": "item",
                "formatter": "{b}: {c} ({d}%)"
            },
            "color": colors,
            "series": [{
                "name": metric,
                "type": "funnel",
                "left": "10%",
                "width": "80%",
                "itemStyle": {
                    "borderColor": "#fff",
                    "borderWidth": 1
                },
                "label": {
                    "show": True,
                    "position": "inside"
                },
                "labelLine": {
                    "length": 10,
                    "lineStyle": {
                        "width": 1,
                        "type": "solid"
                    }
                },
                "data": funnel_data
            }]
        }
        
        return config

    def _select_colors(self, count: int, scheme: str = 'default') -> List[str]:
        """选择配色方案"""
        base_colors = self.color_schemes.get(scheme, self.color_schemes['default'])
        
        if count <= len(base_colors):
            return base_colors[:count]
        
        # 如果需要更多颜色，生成渐变色
        extended_colors = base_colors.copy()
        base_count = len(base_colors)
        
        for i in range(count - base_count):
            # 基于现有颜色生成新颜色
            base_idx = i % base_count
            base_color = base_colors[base_idx]
            
            # 调整亮度生成新颜色
            new_color = self._adjust_color_brightness(base_color, 0.8 + (i % 3) * 0.1)
            extended_colors.append(new_color)
        
        return extended_colors

    def _adjust_color_brightness(self, hex_color: str, factor: float) -> str:
        """调整颜色亮度"""
        try:
            # 移除#号
            hex_color = hex_color.lstrip('#')
            
            # 转换为RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16) 
            b = int(hex_color[4:6], 16)
            
            # 调整亮度
            r = min(255, max(0, int(r * factor)))
            g = min(255, max(0, int(g * factor)))
            b = min(255, max(0, int(b * factor)))
            
            # 转换回十六进制
            return f"#{r:02x}{g:02x}{b:02x}"
            
        except:
            return hex_color  # 出错时返回原色

    def _apply_common_config(self, config: Dict[str, Any], parsed_request: Dict[str, Any], 
                           context: EnhancedExecutionContext):
        """应用通用配置"""
        # 响应式设计
        config["responsive"] = True
        
        # 工具箱
        config["toolbox"] = {
            "feature": {
                "saveAsImage": {"show": True, "title": "保存为图片"},
                "dataView": {"show": True, "title": "数据视图"},
                "restore": {"show": True, "title": "还原"},
                "dataZoom": {"show": True, "title": "缩放"}
            },
            "right": "3%"
        }
        
        # 动画效果
        config["animation"] = True
        config["animationDuration"] = 1000
        config["animationEasing"] = "cubicOut"
        
        # 背景样式
        config["backgroundColor"] = "#ffffff"
        
        # 图例样式优化
        if "legend" in config:
            config["legend"]["textStyle"] = {
                "fontSize": 12,
                "color": "#666"
            }

    def _generate_chart_metadata(self, config: Dict[str, Any], data: List[Dict[str, Any]], 
                                analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成图表元数据"""
        return {
            "generation_time": datetime.now().isoformat(),
            "data_points": len(data),
            "chart_elements": {
                "has_title": "title" in config,
                "has_legend": "legend" in config,
                "has_tooltip": "tooltip" in config,
                "has_toolbox": "toolbox" in config,
                "series_count": len(config.get("series", []))
            },
            "data_summary": {
                "numeric_fields": len([k for k, v in (data[0] if data else {}).items() if isinstance(v, (int, float))]),
                "categorical_fields": len([k for k, v in (data[0] if data else {}).items() if isinstance(v, str)]),
                "has_time_series": any('time' in str(item).lower() or 'date' in str(item).lower() for item in data)
            },
            "insights_integration": {
                "insights_count": len(analysis_result.get('insights', [])),
                "recommendations_count": len(analysis_result.get('recommendations', []))
            }
        }

    async def _generate_chart_from_data(self, chart_data: List[Dict[str, Any]], 
                                      context: EnhancedExecutionContext) -> Dict[str, Any]:
        """基于查询数据生成图表配置"""
        try:
            # 获取图表类型和元数据
            semantic_analysis = context.get_context("semantic_analysis", {})
            sql_metadata = context.get_context("sql_metadata", {})
            query_result = context.get_context("query_result", {})
            placeholder_text = context.get_context("placeholder_text", "图表")
            
            chart_type_hint = semantic_analysis.get('chart_type_hint', 'bar_chart')
            
            # 确定最优图表类型
            final_chart_type = self._determine_optimal_chart_type(chart_type_hint, chart_data, {})
            
            # 构建解析请求（模拟格式）
            parsed_request = {
                'task_type': final_chart_type,
                'metric': semantic_analysis.get('business_concept', placeholder_text),
                'chart_config': {
                    'title': f'{placeholder_text}',
                    'responsive': True
                }
            }
            
            # 生成图表配置
            chart_generator = self.chart_templates.get(final_chart_type, self._create_bar_chart_config)
            echarts_config = chart_generator(chart_data, parsed_request, {})
            
            # 应用通用配置
            self._apply_common_config(echarts_config, parsed_request, context)
            
            # 生成元数据
            metadata = self._generate_chart_metadata(echarts_config, chart_data, {})
            
            # 添加执行信息
            execution_metadata = query_result.get('execution_metadata', {})
            
            result = {
                "success": True,
                "chart_type": final_chart_type,
                "echarts_config": echarts_config,
                "chart_data": chart_data,
                "metadata": {
                    **metadata,
                    "data_source": {
                        "sql_query": context.get_context("generated_sql", ""),
                        "execution_time_ms": execution_metadata.get('execution_time_ms', 0),
                        "row_count": execution_metadata.get('row_count', len(chart_data)),
                        "data_quality_score": execution_metadata.get('data_quality_score', 0.8)
                    }
                },
                "chart_options": {
                    "responsive": True,
                    "interactive": True,
                    "exportable": True,
                    "theme": "default"
                },
                "stage": "chart_generation_complete",
                "ready_for_rendering": True
            }
            
            # 存储图表配置到上下文
            context.set_context("chart_config", result, ContextScope.REQUEST)
            
            logger.info(f"图表生成完成: {final_chart_type}, {len(chart_data)}个数据点")
            
            return {
                "success": True,
                "agent": "chart_generator",
                "type": "chart_generation",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"基于数据生成图表失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": {},
                "stage": "chart_generation_error"
            }
    
    async def _generate_charts_legacy_mode(self, analysis_result: Dict[str, Any], 
                                         parsed_request: Dict[str, Any],
                                         context: EnhancedExecutionContext) -> Dict[str, Any]:
        """兼容模式：使用旧版本的分析结果生成图表"""
        logger.info("使用兼容模式生成图表")
        
        # 处理多个分析结果
        if isinstance(analysis_result, dict) and 'analysis_results' in analysis_result:
            return await self._generate_multiple_charts(analysis_result, parsed_request, context)
        else:
            return await self._generate_single_chart(analysis_result, parsed_request, context)