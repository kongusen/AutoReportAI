"""
Infrastructure层可视化代理

提供数据可视化相关的AI技术支撑：

核心职责：
1. 智能图表类型推荐
2. 图表配置生成和优化
3. 数据可视化分析
4. 多种图表格式支持

技术职责：
- 纯技术实现，不包含业务逻辑
- 可被Application/Domain层调用
- 提供稳定的可视化生成服务
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ChartType(Enum):
    """图表类型"""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    RADAR = "radar"
    FUNNEL = "funnel"
    HEATMAP = "heatmap"
    TREEMAP = "treemap"
    GAUGE = "gauge"


class DataDimension(Enum):
    """数据维度"""
    CATEGORICAL = "categorical"
    NUMERICAL = "numerical"
    TEMPORAL = "temporal"
    GEOGRAPHICAL = "geographical"


class VisualizationComplexity(Enum):
    """可视化复杂度"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    ADVANCED = "advanced"


class VisualizationAgent:
    """
    Infrastructure层可视化代理
    
    核心职责：
    1. 分析数据特征并推荐合适的图表类型
    2. 生成ECharts配置和其他图表配置
    3. 优化图表的视觉效果和用户体验
    4. 支持批量图表生成和自定义
    
    技术定位：
    - Infrastructure层技术基础设施
    - 为上层应用提供可视化生成能力
    - 不包含具体业务逻辑
    """
    
    def __init__(self):
        # 可视化统计
        self.visualization_stats = {
            "total_visualizations": 0,
            "successful_visualizations": 0,
            "failed_visualizations": 0,
            "avg_generation_time": 0.0,
            "chart_type_stats": {},
            "complexity_stats": {}
        }
        
        # 图表类型权重配置
        self.chart_type_weights = {
            ChartType.BAR: {"categorical": 0.9, "numerical": 0.8, "comparison": 0.9},
            ChartType.LINE: {"temporal": 0.9, "trend": 0.9, "continuous": 0.8},
            ChartType.PIE: {"proportion": 0.9, "categorical": 0.7, "parts_to_whole": 0.9},
            ChartType.SCATTER: {"correlation": 0.9, "distribution": 0.8, "outlier": 0.7},
            ChartType.AREA: {"temporal": 0.8, "cumulative": 0.9, "trend": 0.7},
            ChartType.RADAR: {"multi_dimensional": 0.9, "comparison": 0.7},
            ChartType.FUNNEL: {"conversion": 0.9, "process": 0.8, "stages": 0.9},
            ChartType.HEATMAP: {"matrix": 0.9, "correlation": 0.8, "intensity": 0.9}
        }
        
        logger.info("可视化代理初始化完成")
    
    async def recommend_chart_type(self,
                                 data: List[Dict[str, Any]],
                                 analysis_intent: str = "",
                                 user_preferences: Dict[str, Any] = None,
                                 user_id: str = "system") -> Dict[str, Any]:
        """
        推荐图表类型
        
        Args:
            data: 数据集
            analysis_intent: 分析意图
            user_preferences: 用户偏好
            user_id: 用户ID
            
        Returns:
            推荐结果
        """
        try:
            # 数据分析
            data_analysis = await self._analyze_data_characteristics(data)
            
            # 意图分析
            intent_analysis = await self._analyze_visualization_intent(analysis_intent)
            
            # 图表类型评分
            chart_scores = await self._score_chart_types(
                data_analysis, intent_analysis, user_preferences or {}
            )
            
            # 排序并选择前3个推荐
            sorted_charts = sorted(chart_scores.items(), key=lambda x: x[1], reverse=True)
            recommendations = []
            
            for chart_type, score in sorted_charts[:3]:
                recommendations.append({
                    "chart_type": chart_type.value,
                    "score": score,
                    "confidence": min(score / max(chart_scores.values()), 1.0),
                    "reasons": self._get_recommendation_reasons(chart_type, data_analysis, intent_analysis)
                })
            
            result = {
                "success": True,
                "recommendations": recommendations,
                "primary_recommendation": recommendations[0] if recommendations else None,
                "data_characteristics": data_analysis,
                "intent_analysis": intent_analysis,
                "metadata": {
                    "data_size": len(data),
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"图表类型推荐完成: 主推荐={result['primary_recommendation']['chart_type'] if recommendations else 'none'}")
            return result
            
        except Exception as e:
            logger.error(f"图表类型推荐失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "data_size": len(data) if data else 0
            }
    
    async def generate_chart_config(self,
                                  data: List[Dict[str, Any]],
                                  chart_type: ChartType,
                                  config_options: Dict[str, Any] = None,
                                  user_id: str = "system") -> Dict[str, Any]:
        """
        生成图表配置
        
        Args:
            data: 数据集
            chart_type: 图表类型
            config_options: 配置选项
            user_id: 用户ID
            
        Returns:
            图表配置
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.visualization_stats["total_visualizations"] += 1
            
            # 数据预处理
            processed_data = await self._preprocess_data_for_chart(data, chart_type)
            
            # 生成基础配置
            base_config = await self._generate_base_config(chart_type, processed_data)
            
            # 应用配置选项
            if config_options:
                base_config = await self._apply_config_options(base_config, config_options)
            
            # 优化配置
            optimized_config = await self._optimize_chart_config(base_config, chart_type, processed_data)
            
            generation_time = asyncio.get_event_loop().time() - start_time
            
            # 更新统计
            self._update_visualization_stats(chart_type, generation_time, success=True)
            
            result = {
                "success": True,
                "chart_config": optimized_config,
                "chart_type": chart_type.value,
                "data_points": len(processed_data) if isinstance(processed_data, list) else 0,
                "generation_time": generation_time,
                "config_complexity": self._assess_config_complexity(optimized_config),
                "metadata": {
                    "original_data_size": len(data),
                    "processed_data_size": len(processed_data) if isinstance(processed_data, list) else 0,
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"图表配置生成成功: 类型={chart_type.value}, 时长={generation_time:.2f}s")
            return result
            
        except Exception as e:
            generation_time = asyncio.get_event_loop().time() - start_time
            
            # 更新统计
            self._update_visualization_stats(chart_type, generation_time, success=False)
            
            logger.error(f"图表配置生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "chart_type": chart_type.value,
                "generation_time": generation_time
            }
    
    async def optimize_visualization(self,
                                   chart_config: Dict[str, Any],
                                   optimization_goals: List[str] = None,
                                   user_id: str = "system") -> Dict[str, Any]:
        """
        优化可视化配置
        
        Args:
            chart_config: 原始图表配置
            optimization_goals: 优化目标
            user_id: 用户ID
            
        Returns:
            优化结果
        """
        try:
            optimization_goals = optimization_goals or ["performance", "readability", "aesthetics"]
            
            optimized_config = chart_config.copy()
            optimization_log = []
            
            # 性能优化
            if "performance" in optimization_goals:
                performance_optimizations = await self._apply_performance_optimizations(optimized_config)
                optimized_config.update(performance_optimizations)
                optimization_log.extend(["减少不必要的动画", "优化数据处理", "简化渲染配置"])
            
            # 可读性优化
            if "readability" in optimization_goals:
                readability_optimizations = await self._apply_readability_optimizations(optimized_config)
                optimized_config.update(readability_optimizations)
                optimization_log.extend(["优化标签显示", "调整字体大小", "改善颜色对比度"])
            
            # 美观性优化
            if "aesthetics" in optimization_goals:
                aesthetic_optimizations = await self._apply_aesthetic_optimizations(optimized_config)
                optimized_config.update(aesthetic_optimizations)
                optimization_log.extend(["优化色彩搭配", "调整间距布局", "增强视觉层次"])
            
            # 响应式优化
            if "responsive" in optimization_goals:
                responsive_optimizations = await self._apply_responsive_optimizations(optimized_config)
                optimized_config.update(responsive_optimizations)
                optimization_log.extend(["添加响应式配置", "优化移动端显示"])
            
            result = {
                "success": True,
                "original_config": chart_config,
                "optimized_config": optimized_config,
                "optimization_goals": optimization_goals,
                "optimization_log": optimization_log,
                "improvement_score": await self._calculate_improvement_score(chart_config, optimized_config),
                "metadata": {
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"可视化优化完成: 目标={optimization_goals}")
            return result
            
        except Exception as e:
            logger.error(f"可视化优化失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "optimization_goals": optimization_goals or []
            }
    
    async def batch_generate_charts(self,
                                  chart_requests: List[Dict[str, Any]],
                                  user_id: str = "system") -> Dict[str, Any]:
        """
        批量生成图表
        
        Args:
            chart_requests: 图表请求列表
            user_id: 用户ID
            
        Returns:
            批量生成结果
        """
        try:
            batch_start_time = asyncio.get_event_loop().time()
            
            # 并发生成
            tasks = []
            for i, request in enumerate(chart_requests):
                task = self.generate_chart_config(
                    data=request.get("data", []),
                    chart_type=ChartType(request.get("chart_type", "bar")),
                    config_options=request.get("config_options"),
                    user_id=f"{user_id}_batch_{i}"
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计结果
            successful_results = []
            failed_results = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append({
                        "index": i,
                        "request": chart_requests[i],
                        "error": str(result)
                    })
                elif result.get("success"):
                    successful_results.append(result)
                else:
                    failed_results.append({
                        "index": i,
                        "request": chart_requests[i],
                        "error": result.get("error", "Unknown error")
                    })
            
            batch_time = asyncio.get_event_loop().time() - batch_start_time
            
            batch_result = {
                "success": True,
                "total_requests": len(chart_requests),
                "successful_count": len(successful_results),
                "failed_count": len(failed_results),
                "success_rate": len(successful_results) / len(chart_requests),
                "batch_time": batch_time,
                "avg_time_per_chart": batch_time / len(chart_requests),
                "results": successful_results,
                "failures": failed_results,
                "metadata": {
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"批量图表生成完成: 成功率={batch_result['success_rate']:.2%}")
            return batch_result
            
        except Exception as e:
            logger.error(f"批量图表生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_requests": len(chart_requests)
            }
    
    # 私有方法
    
    async def _analyze_data_characteristics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析数据特征"""
        if not data:
            return {"empty": True}
        
        characteristics = {
            "size": len(data),
            "columns": list(data[0].keys()) if data else [],
            "column_types": {},
            "dimensions": [],
            "has_temporal": False,
            "has_categorical": False,
            "has_numerical": False,
            "data_distribution": {}
        }
        
        # 分析列类型
        for column in characteristics["columns"]:
            values = [row.get(column) for row in data if row.get(column) is not None]
            
            if not values:
                continue
            
            # 判断数据类型
            sample_value = values[0]
            
            if isinstance(sample_value, (int, float)):
                characteristics["column_types"][column] = "numerical"
                characteristics["has_numerical"] = True
                characteristics["dimensions"].append(DataDimension.NUMERICAL)
            elif isinstance(sample_value, str):
                # 尝试识别时间格式
                if any(keyword in sample_value.lower() for keyword in ["2024", "2023", "月", "日", "-"]):
                    characteristics["column_types"][column] = "temporal"
                    characteristics["has_temporal"] = True
                    characteristics["dimensions"].append(DataDimension.TEMPORAL)
                else:
                    characteristics["column_types"][column] = "categorical"
                    characteristics["has_categorical"] = True
                    characteristics["dimensions"].append(DataDimension.CATEGORICAL)
            else:
                characteristics["column_types"][column] = "mixed"
        
        # 去重维度
        characteristics["dimensions"] = list(set(characteristics["dimensions"]))
        
        return characteristics
    
    async def _analyze_visualization_intent(self, analysis_intent: str) -> Dict[str, Any]:
        """分析可视化意图"""
        intent_keywords = {
            "comparison": ["比较", "对比", "vs", "versus", "compare"],
            "trend": ["趋势", "变化", "增长", "下降", "trend", "change"],
            "proportion": ["占比", "比例", "份额", "percentage", "proportion", "share"],
            "correlation": ["关联", "相关", "关系", "correlation", "relationship"],
            "distribution": ["分布", "分散", "distribution", "spread"],
            "ranking": ["排名", "排序", "top", "ranking", "order"],
            "process": ["流程", "过程", "步骤", "process", "flow", "funnel"]
        }
        
        detected_intents = []
        intent_scores = {}
        
        for intent, keywords in intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in analysis_intent.lower())
            if score > 0:
                detected_intents.append(intent)
                intent_scores[intent] = score
        
        return {
            "raw_intent": analysis_intent,
            "detected_intents": detected_intents,
            "primary_intent": max(intent_scores.keys(), key=intent_scores.get) if intent_scores else "general",
            "intent_scores": intent_scores,
            "confidence": max(intent_scores.values()) / max(1, len(analysis_intent.split())) if intent_scores else 0.5
        }
    
    async def _score_chart_types(self,
                               data_analysis: Dict[str, Any],
                               intent_analysis: Dict[str, Any],
                               user_preferences: Dict[str, Any]) -> Dict[ChartType, float]:
        """为图表类型评分"""
        scores = {}
        
        for chart_type in ChartType:
            score = 0.0
            weights = self.chart_type_weights.get(chart_type, {})
            
            # 基于数据特征评分
            for dimension in data_analysis.get("dimensions", []):
                if dimension.value in weights:
                    score += weights[dimension.value] * 0.4
            
            # 基于意图评分
            primary_intent = intent_analysis.get("primary_intent", "general")
            if primary_intent in weights:
                score += weights[primary_intent] * 0.6
            
            # 基于用户偏好调整
            preferred_charts = user_preferences.get("preferred_chart_types", [])
            if chart_type.value in preferred_charts:
                score += 0.2
            
            scores[chart_type] = score
        
        return scores
    
    def _get_recommendation_reasons(self,
                                  chart_type: ChartType,
                                  data_analysis: Dict[str, Any],
                                  intent_analysis: Dict[str, Any]) -> List[str]:
        """获取推荐理由"""
        reasons = []
        
        if chart_type == ChartType.BAR:
            if data_analysis.get("has_categorical"):
                reasons.append("数据包含分类变量，适合柱状图比较")
            if "comparison" in intent_analysis.get("detected_intents", []):
                reasons.append("分析目标是比较，柱状图效果最佳")
        
        elif chart_type == ChartType.LINE:
            if data_analysis.get("has_temporal"):
                reasons.append("数据包含时间序列，适合折线图显示趋势")
            if "trend" in intent_analysis.get("detected_intents", []):
                reasons.append("分析目标是趋势分析，折线图最适合")
        
        elif chart_type == ChartType.PIE:
            if "proportion" in intent_analysis.get("detected_intents", []):
                reasons.append("分析目标是比例分析，饼图直观展示占比")
            if len(data_analysis.get("columns", [])) <= 2:
                reasons.append("数据维度简单，适合饼图展示")
        
        # 添加更多图表类型的推荐理由...
        
        if not reasons:
            reasons.append("基于数据特征和分析需求的综合推荐")
        
        return reasons
    
    async def _preprocess_data_for_chart(self,
                                       data: List[Dict[str, Any]],
                                       chart_type: ChartType) -> Any:
        """为特定图表类型预处理数据"""
        if not data:
            return []
        
        if chart_type == ChartType.PIE:
            # 饼图需要name-value格式
            processed_data = []
            for item in data:
                name = str(list(item.keys())[0])
                value = item.get(name, 0)
                processed_data.append({"name": name, "value": value})
            return processed_data
        
        elif chart_type == ChartType.BAR:
            # 柱状图需要categories和series
            if data:
                categories = [str(item.get(list(item.keys())[0], "")) for item in data]
                values = [item.get(list(item.keys())[1], 0) if len(item.keys()) > 1 else 0 for item in data]
                return {"categories": categories, "values": values}
        
        elif chart_type == ChartType.LINE:
            # 折线图需要x-y格式
            if data:
                x_data = [str(item.get(list(item.keys())[0], "")) for item in data]
                y_data = [item.get(list(item.keys())[1], 0) if len(item.keys()) > 1 else 0 for item in data]
                return {"x_data": x_data, "y_data": y_data}
        
        return data
    
    async def _generate_base_config(self,
                                  chart_type: ChartType,
                                  processed_data: Any) -> Dict[str, Any]:
        """生成基础图表配置"""
        
        base_config = {
            "title": {"text": "数据可视化"},
            "tooltip": {"trigger": "item"},
            "legend": {"top": "5%"},
            "toolbox": {
                "show": True,
                "feature": {
                    "saveAsImage": {}
                }
            }
        }
        
        if chart_type == ChartType.BAR:
            base_config.update({
                "xAxis": {
                    "type": "category",
                    "data": processed_data.get("categories", []) if isinstance(processed_data, dict) else []
                },
                "yAxis": {"type": "value"},
                "series": [{
                    "data": processed_data.get("values", []) if isinstance(processed_data, dict) else processed_data,
                    "type": "bar"
                }]
            })
        
        elif chart_type == ChartType.LINE:
            base_config.update({
                "xAxis": {
                    "type": "category",
                    "data": processed_data.get("x_data", []) if isinstance(processed_data, dict) else []
                },
                "yAxis": {"type": "value"},
                "series": [{
                    "data": processed_data.get("y_data", []) if isinstance(processed_data, dict) else processed_data,
                    "type": "line",
                    "smooth": True
                }]
            })
        
        elif chart_type == ChartType.PIE:
            base_config.update({
                "series": [{
                    "name": "数据分析",
                    "type": "pie",
                    "radius": "50%",
                    "data": processed_data if isinstance(processed_data, list) else [],
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowOffsetX": 0,
                            "shadowColor": "rgba(0, 0, 0, 0.5)"
                        }
                    }
                }]
            })
        
        elif chart_type == ChartType.SCATTER:
            base_config.update({
                "xAxis": {"type": "value"},
                "yAxis": {"type": "value"},
                "series": [{
                    "data": processed_data if isinstance(processed_data, list) else [],
                    "type": "scatter",
                    "symbolSize": 20
                }]
            })
        
        # 添加更多图表类型的配置...
        
        return base_config
    
    async def _apply_config_options(self,
                                  base_config: Dict[str, Any],
                                  options: Dict[str, Any]) -> Dict[str, Any]:
        """应用配置选项"""
        config = base_config.copy()
        
        # 标题配置
        if "title" in options:
            config["title"].update(options["title"])
        
        # 颜色配置
        if "colors" in options:
            config["color"] = options["colors"]
        
        # 主题配置
        if "theme" in options:
            theme_config = self._get_theme_config(options["theme"])
            config.update(theme_config)
        
        # 尺寸配置
        if "width" in options:
            config["width"] = options["width"]
        if "height" in options:
            config["height"] = options["height"]
        
        return config
    
    def _get_theme_config(self, theme: str) -> Dict[str, Any]:
        """获取主题配置"""
        themes = {
            "dark": {
                "backgroundColor": "#333",
                "textStyle": {"color": "#fff"},
                "color": ["#c23531", "#2f4554", "#61a0a8", "#d48265", "#91c7ae"]
            },
            "light": {
                "backgroundColor": "#fff",
                "textStyle": {"color": "#333"},
                "color": ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de"]
            },
            "minimal": {
                "backgroundColor": "#fafafa",
                "textStyle": {"color": "#666"},
                "color": ["#8884d8", "#82ca9d", "#ffc658", "#ff7c7c", "#8dd1e1"]
            }
        }
        
        return themes.get(theme, themes["light"])
    
    async def _optimize_chart_config(self,
                                   config: Dict[str, Any],
                                   chart_type: ChartType,
                                   data: Any) -> Dict[str, Any]:
        """优化图表配置"""
        optimized_config = config.copy()
        
        # 基于数据量优化
        data_size = len(data) if isinstance(data, list) else 0
        
        if data_size > 100:
            # 大数据集优化
            optimized_config["animation"] = False
            if "series" in optimized_config:
                for series in optimized_config["series"]:
                    if series.get("type") == "line":
                        series["sampling"] = "average"
        
        # 基于图表类型优化
        if chart_type == ChartType.PIE and data_size > 10:
            # 饼图项目过多时合并小项
            if "series" in optimized_config and optimized_config["series"]:
                series = optimized_config["series"][0]
                if "data" in series:
                    data_items = series["data"]
                    # 简化处理：保留前8项，其余合并为"其他"
                    if len(data_items) > 8:
                        top_items = sorted(data_items, key=lambda x: x.get("value", 0), reverse=True)[:7]
                        other_value = sum(item.get("value", 0) for item in data_items[7:])
                        top_items.append({"name": "其他", "value": other_value})
                        series["data"] = top_items
        
        return optimized_config
    
    async def _apply_performance_optimizations(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用性能优化"""
        return {
            "animation": False,
            "blendMode": "source-over",
            "progressive": 1000
        }
    
    async def _apply_readability_optimizations(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用可读性优化"""
        return {
            "textStyle": {
                "fontSize": 12,
                "fontWeight": "normal"
            },
            "tooltip": {
                "textStyle": {"fontSize": 12},
                "backgroundColor": "rgba(0,0,0,0.8)",
                "borderColor": "#333"
            }
        }
    
    async def _apply_aesthetic_optimizations(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用美观性优化"""
        return {
            "color": ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de", "#3ba272"],
            "grid": {
                "left": "3%",
                "right": "4%",
                "bottom": "3%",
                "containLabel": True
            }
        }
    
    async def _apply_responsive_optimizations(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用响应式优化"""
        return {
            "media": [{
                "query": {"maxWidth": 600},
                "option": {
                    "legend": {"bottom": "5%", "orient": "horizontal"},
                    "grid": {"left": "5%", "right": "5%"}
                }
            }]
        }
    
    async def _calculate_improvement_score(self,
                                         original: Dict[str, Any],
                                         optimized: Dict[str, Any]) -> float:
        """计算改进分数"""
        # 简化的改进分数计算
        improvements = 0
        total_checks = 5
        
        # 检查是否添加了性能优化
        if optimized.get("animation") == False:
            improvements += 1
        
        # 检查是否改进了颜色配置
        if "color" in optimized and "color" not in original:
            improvements += 1
        
        # 检查是否添加了响应式配置
        if "media" in optimized:
            improvements += 1
        
        # 检查是否优化了网格布局
        if "grid" in optimized:
            improvements += 1
        
        # 检查是否改进了工具提示
        if optimized.get("tooltip", {}).get("textStyle"):
            improvements += 1
        
        return improvements / total_checks
    
    def _assess_config_complexity(self, config: Dict[str, Any]) -> VisualizationComplexity:
        """评估配置复杂度"""
        complexity_score = 0
        
        # 基于配置项数量
        complexity_score += len(config.keys()) * 0.1
        
        # 基于series数量
        if "series" in config:
            complexity_score += len(config["series"]) * 0.5
        
        # 基于特殊功能
        if "animation" in config:
            complexity_score += 0.3
        if "media" in config:
            complexity_score += 0.5
        if "toolbox" in config:
            complexity_score += 0.2
        
        if complexity_score < 1.0:
            return VisualizationComplexity.SIMPLE
        elif complexity_score < 2.0:
            return VisualizationComplexity.MEDIUM
        elif complexity_score < 3.0:
            return VisualizationComplexity.COMPLEX
        else:
            return VisualizationComplexity.ADVANCED
    
    def _update_visualization_stats(self,
                                  chart_type: ChartType,
                                  generation_time: float,
                                  success: bool):
        """更新可视化统计"""
        if success:
            self.visualization_stats["successful_visualizations"] += 1
        else:
            self.visualization_stats["failed_visualizations"] += 1
        
        # 更新平均时间
        total_visualizations = self.visualization_stats["total_visualizations"]
        if total_visualizations > 1:
            current_avg = self.visualization_stats["avg_generation_time"]
            new_avg = (current_avg * (total_visualizations - 1) + generation_time) / total_visualizations
            self.visualization_stats["avg_generation_time"] = new_avg
        else:
            self.visualization_stats["avg_generation_time"] = generation_time
        
        # 更新图表类型统计
        type_key = chart_type.value
        if type_key not in self.visualization_stats["chart_type_stats"]:
            self.visualization_stats["chart_type_stats"][type_key] = 0
        self.visualization_stats["chart_type_stats"][type_key] += 1
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """获取代理统计信息"""
        return {
            "agent_name": "VisualizationAgent",
            "version": "1.0.0-infrastructure",
            "architecture": "DDD Infrastructure Layer",
            "visualization_stats": self.visualization_stats,
            "supported_chart_types": [t.value for t in ChartType],
            "supported_complexities": [c.value for c in VisualizationComplexity],
            "data_dimensions": [d.value for d in DataDimension],
            "capabilities": [
                "chart_type_recommendation",
                "chart_config_generation",
                "visualization_optimization",
                "batch_chart_generation",
                "responsive_design",
                "theme_customization"
            ]
        }