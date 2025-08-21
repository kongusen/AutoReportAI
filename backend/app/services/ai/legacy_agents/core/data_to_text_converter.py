"""
数据到文本转换器

将结构化的JSON数据结合模板上下文，转换为自然、流畅的中文语句。
专门处理占位符查询结果，生成业务友好的文本描述。

核心功能：
1. JSON数据智能解读
2. 模板上下文理解
3. 自然语言生成
4. 业务洞察提取
5. 多种文本风格支持
"""

import asyncio
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

from ..enhanced.enhanced_content_generation_agent import (
    EnhancedContentGenerationAgent,
    ContextualContentRequest,
    StyleProfile
)


@dataclass
class DataContext:
    """数据上下文"""
    data: List[Dict[str, Any]]
    placeholder_info: Dict[str, Any]
    template_context: Dict[str, Any]
    business_context: Dict[str, Any]


@dataclass 
class TextGenerationRequest:
    """文本生成请求"""
    data_context: DataContext
    output_style: str = "business_report"  # business_report, casual, technical
    audience: str = "management"  # management, analyst, general
    language: str = "zh-CN"
    include_insights: bool = True
    include_numbers: bool = True
    max_length: int = 500


class DataAnalyzer:
    """数据分析器 - 提取数据特征和洞察"""
    
    def __init__(self):
        pass
    
    async def analyze_data_patterns(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析数据模式"""
        try:
            if not data:
                return {"pattern": "empty_data"}
            
            analysis = {
                "total_records": len(data),
                "data_type": self._identify_data_type(data),
                "key_metrics": self._extract_key_metrics(data),
                "rankings": self._calculate_rankings(data),
                "trends": self._identify_trends(data),
                "insights": self._generate_insights(data)
            }
            
            return analysis
            
        except Exception as e:
            return {"error": str(e)}
    
    def _identify_data_type(self, data: List[Dict[str, Any]]) -> str:
        """识别数据类型"""
        if not data:
            return "unknown"
        
        first_record = data[0]
        
        # 客户分析数据
        if any(key in first_record for key in ["type", "customer_type", "count", "avg_spend"]):
            return "customer_analysis"
        
        # 销售分析数据
        elif any(key in first_record for key in ["region", "sales", "revenue", "amount"]):
            return "sales_analysis"
        
        # 产品分析数据
        elif any(key in first_record for key in ["product", "category", "quantity", "volume"]):
            return "product_analysis"
        
        # 时间序列数据
        elif any(key in first_record for key in ["date", "month", "quarter", "year"]):
            return "time_series"
        
        else:
            return "general_analysis"
    
    def _extract_key_metrics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取关键指标"""
        if not data:
            return {}
        
        numeric_fields = []
        for record in data:
            for key, value in record.items():
                if isinstance(value, (int, float)) and key not in ["rank", "index"]:
                    numeric_fields.append(key)
        
        numeric_fields = list(set(numeric_fields))
        
        metrics = {}
        for field in numeric_fields:
            values = [record.get(field, 0) for record in data if isinstance(record.get(field), (int, float))]
            if values:
                metrics[field] = {
                    "total": sum(values),
                    "average": sum(values) / len(values),
                    "max": max(values),
                    "min": min(values),
                    "max_record": max(data, key=lambda x: x.get(field, 0)),
                    "min_record": min(data, key=lambda x: x.get(field, 0))
                }
        
        return metrics
    
    def _calculate_rankings(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """计算排名信息"""
        if not data:
            return []
        
        # 找到主要的数值字段进行排名
        numeric_fields = []
        for record in data:
            for key, value in record.items():
                if isinstance(value, (int, float)) and key not in ["rank", "index"]:
                    numeric_fields.append(key)
        
        if not numeric_fields:
            return []
        
        # 选择最重要的指标进行排名
        main_metric = numeric_fields[0]  # 简化处理，取第一个数值字段
        
        # 按主要指标排序
        sorted_data = sorted(data, key=lambda x: x.get(main_metric, 0), reverse=True)
        
        rankings = []
        for i, record in enumerate(sorted_data, 1):
            ranking_info = {
                "rank": i,
                "record": record,
                "metric": main_metric,
                "value": record.get(main_metric, 0)
            }
            rankings.append(ranking_info)
        
        return rankings
    
    def _identify_trends(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """识别趋势"""
        trends = {
            "dominant_leader": None,
            "performance_gap": None,
            "distribution_pattern": "balanced"
        }
        
        if not data:
            return trends
        
        # 找到数值字段
        numeric_fields = [k for k, v in data[0].items() if isinstance(v, (int, float))]
        
        if numeric_fields:
            main_field = numeric_fields[0]
            values = [record.get(main_field, 0) for record in data]
            
            if values:
                max_val = max(values)
                min_val = min(values)
                avg_val = sum(values) / len(values)
                
                # 判断是否有主导者
                if max_val > avg_val * 2:
                    max_record = max(data, key=lambda x: x.get(main_field, 0))
                    trends["dominant_leader"] = max_record
                
                # 计算性能差距
                if min_val > 0:
                    trends["performance_gap"] = round((max_val - min_val) / min_val * 100, 1)
                
                # 判断分布模式
                if max_val > avg_val * 3:
                    trends["distribution_pattern"] = "highly_concentrated"
                elif max_val > avg_val * 1.5:
                    trends["distribution_pattern"] = "moderately_concentrated"
                else:
                    trends["distribution_pattern"] = "balanced"
        
        return trends
    
    def _generate_insights(self, data: List[Dict[str, Any]]) -> List[str]:
        """生成数据洞察"""
        insights = []
        
        if not data:
            return ["数据为空，无法生成洞察"]
        
        # 基于数据量的洞察
        if len(data) > 10:
            insights.append(f"数据维度丰富，包含{len(data)}个不同类别")
        elif len(data) < 3:
            insights.append(f"数据相对集中，仅有{len(data)}个主要类别")
        
        # 基于数值分布的洞察
        numeric_fields = [k for k, v in data[0].items() if isinstance(v, (int, float))]
        
        if numeric_fields:
            main_field = numeric_fields[0]
            values = [record.get(main_field, 0) for record in data]
            
            if values:
                total = sum(values)
                max_val = max(values)
                max_record = max(data, key=lambda x: x.get(main_field, 0))
                
                # 主导性洞察
                if max_val / total > 0.5:
                    category = max_record.get('type', max_record.get('region', max_record.get('category', '主要类别')))
                    percentage = round(max_val / total * 100, 1)
                    insights.append(f"{category}占据主导地位，贡献了{percentage}%的份额")
                
                # 分布均匀性洞察
                avg_val = total / len(values)
                variance = sum((v - avg_val) ** 2 for v in values) / len(values)
                
                if variance < avg_val * 0.1:
                    insights.append("各类别表现较为均衡，差异不大")
                elif variance > avg_val * 2:
                    insights.append("各类别表现差异显著，存在明显的强弱分化")
        
        return insights


class TemplateEngine:
    """模板引擎 - 根据数据类型和上下文选择合适的模板"""
    
    def __init__(self):
        self.templates = {
            "customer_analysis": {
                "business_report": {
                    "intro": "根据本年度客户数据分析显示：",
                    "summary": "在{total_customers}位客户中，{dominant_type}客户群体表现最为突出",
                    "detail": "{type}客户共有{count}位，人均消费{avg_spend}元，贡献了{contribution}%的总收入",
                    "insight": "数据表明{insight_text}",
                    "conclusion": "建议重点关注{recommendation}"
                },
                "casual": {
                    "intro": "让我们看看客户情况：",
                    "summary": "总共{total_customers}个客户，{dominant_type}客户最给力",
                    "detail": "{type}客户有{count}个，平均花{avg_spend}块钱，占了{contribution}%的收入",
                    "insight": "{insight_text}",
                    "conclusion": "所以{recommendation}"
                },
                "technical": {
                    "intro": "客户分层分析结果：",
                    "summary": "样本量{total_customers}，{dominant_type}段客户价值密度最高",
                    "detail": "{type}客户：数量{count}，ARPU{avg_spend}元，收入贡献率{contribution}%",
                    "insight": "关键发现：{insight_text}",
                    "conclusion": "策略建议：{recommendation}"
                }
            },
            "sales_analysis": {
                "business_report": {
                    "intro": "销售业绩分析结果表明：",
                    "summary": "各地区中，{top_region}表现最优，销售额达到{top_sales}元",
                    "detail": "{region}地区实现销售额{sales}元，环比增长{growth}%",
                    "insight": "市场趋势显示{insight_text}",
                    "conclusion": "建议对{recommendation}地区加大投入"
                }
            }
        }
    
    async def select_template(
        self, 
        data_type: str, 
        style: str, 
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """选择合适的模板"""
        
        # 获取模板
        template = self.templates.get(data_type, {}).get(style)
        
        if not template:
            # 使用默认模板
            template = {
                "intro": "数据分析结果显示：",
                "summary": "在所有类别中，表现最突出的是{top_item}",
                "detail": "{item}：{main_metric}",
                "insight": "分析表明{insight_text}",
                "conclusion": "建议{recommendation}"
            }
        
        return template


class NaturalLanguageGenerator:
    """自然语言生成器"""
    
    def __init__(self):
        self.content_agent = EnhancedContentGenerationAgent()
    
    async def generate_narrative(
        self,
        data: List[Dict[str, Any]],
        analysis: Dict[str, Any],
        template: Dict[str, str],
        style: str = "business_report"
    ) -> str:
        """生成自然语言叙述"""
        try:
            # 1. 准备数据变量
            variables = await self._prepare_variables(data, analysis)
            
            # 2. 填充模板
            filled_sections = {}
            for section, template_text in template.items():
                filled_sections[section] = template_text.format(**variables)
            
            # 3. 组装完整文本
            narrative_parts = []
            
            # 添加介绍
            if "intro" in filled_sections:
                narrative_parts.append(filled_sections["intro"])
            
            # 添加总结
            if "summary" in filled_sections:
                narrative_parts.append(filled_sections["summary"])
            
            # 添加详细描述
            if "detail" in filled_sections and data:
                detail_parts = []
                for record in data:
                    detail_text = self._format_detail(record, template.get("detail", ""), variables)
                    if detail_text:
                        detail_parts.append(detail_text)
                
                if detail_parts:
                    if len(detail_parts) <= 3:
                        narrative_parts.extend(detail_parts)
                    else:
                        # 只显示前3个，其他概括
                        narrative_parts.extend(detail_parts[:3])
                        narrative_parts.append(f"其他{len(detail_parts)-3}个类别表现各异。")
            
            # 添加洞察
            if "insight" in filled_sections and analysis.get("insights"):
                insight_text = "；".join(analysis["insights"][:2])  # 最多2个洞察
                insight_section = filled_sections["insight"].replace("{insight_text}", insight_text)
                narrative_parts.append(insight_section)
            
            # 添加结论
            if "conclusion" in filled_sections:
                recommendation = self._generate_recommendation(data, analysis)
                conclusion_text = filled_sections["conclusion"].replace("{recommendation}", recommendation)
                narrative_parts.append(conclusion_text)
            
            # 组装最终文本
            final_text = ""
            for i, part in enumerate(narrative_parts):
                if i == 0:
                    final_text += part
                else:
                    # 智能添加连接词
                    connector = self._choose_connector(i, len(narrative_parts), style)
                    final_text += connector + part
            
            return final_text
            
        except Exception as e:
            return f"文本生成失败：{str(e)}"
    
    async def _prepare_variables(
        self, 
        data: List[Dict[str, Any]], 
        analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """准备模板变量"""
        variables = {}
        
        if not data:
            return variables
        
        # 基础统计
        variables["total_records"] = str(len(data))
        
        # 客户分析特定变量
        if analysis.get("data_type") == "customer_analysis":
            total_customers = sum(record.get("count", 0) for record in data)
            variables["total_customers"] = str(total_customers)
            
            # 找到主导客户类型
            if data:
                dominant_record = max(data, key=lambda x: x.get("contribution", 0))
                variables["dominant_type"] = str(dominant_record.get("type", "主要"))
        
        # 销售分析特定变量
        elif analysis.get("data_type") == "sales_analysis":
            if data:
                top_record = max(data, key=lambda x: x.get("sales", 0))
                variables["top_region"] = str(top_record.get("region", "主要地区"))
                variables["top_sales"] = f"{top_record.get('sales', 0):,}"
        
        # 通用变量
        if analysis.get("rankings"):
            top_item = analysis["rankings"][0]["record"]
            main_key = [k for k, v in top_item.items() if not isinstance(v, (int, float))][0]
            variables["top_item"] = str(top_item.get(main_key, "顶级类别"))
        
        return variables
    
    def _format_detail(
        self, 
        record: Dict[str, Any], 
        detail_template: str, 
        variables: Dict[str, str]
    ) -> str:
        """格式化详细信息"""
        try:
            # 准备记录特定的变量
            record_vars = {**variables}
            
            for key, value in record.items():
                if isinstance(value, (int, float)):
                    if key in ["avg_spend", "sales", "amount", "revenue"]:
                        record_vars[key] = f"{value:,.0f}"
                    elif key in ["contribution", "percentage", "growth"]:
                        record_vars[key] = f"{value:.1f}"
                    else:
                        record_vars[key] = str(value)
                else:
                    record_vars[key] = str(value)
            
            return detail_template.format(**record_vars)
            
        except (KeyError, ValueError):
            return ""
    
    def _generate_recommendation(
        self, 
        data: List[Dict[str, Any]], 
        analysis: Dict[str, Any]
    ) -> str:
        """生成建议"""
        if not data or not analysis:
            return "持续监控数据变化"
        
        data_type = analysis.get("data_type")
        trends = analysis.get("trends", {})
        
        if data_type == "customer_analysis":
            if trends.get("dominant_leader"):
                dominant_type = trends["dominant_leader"].get("type", "高价值客户")
                return f"继续深耕{dominant_type}群体，并尝试将其他客户转化为此类客户"
            else:
                return "平衡发展各客户群体，提升整体客户价值"
        
        elif data_type == "sales_analysis":
            if trends.get("dominant_leader"):
                top_region = trends["dominant_leader"].get("region", "优势地区")
                return f"复制{top_region}的成功经验到其他地区"
            else:
                return "加强区域间协调，提升整体销售效率"
        
        else:
            return "根据数据表现优化资源配置"
    
    def _choose_connector(self, index: int, total: int, style: str) -> str:
        """选择合适的连接词"""
        connectors = {
            "business_report": ["。", "。具体来看，", "。从数据来看，", "。此外，", "。综合分析，"],
            "casual": ["。", "。另外，", "。还有，", "。而且，", "。总的来说，"],
            "technical": ["。", "。数据显示，", "。进一步分析，", "。同时，", "。综上所述，"]
        }
        
        style_connectors = connectors.get(style, connectors["business_report"])
        
        if index < len(style_connectors):
            return style_connectors[index]
        else:
            return "。"


class DataToTextConverter:
    """数据到文本转换器 - 主控制器"""
    
    def __init__(self):
        self.data_analyzer = DataAnalyzer()
        self.template_engine = TemplateEngine()
        self.text_generator = NaturalLanguageGenerator()
    
    async def convert_to_natural_text(
        self,
        request: TextGenerationRequest
    ) -> Dict[str, Any]:
        """将数据转换为自然文本"""
        try:
            data = request.data_context.data
            placeholder_info = request.data_context.placeholder_info
            
            print(f"🎯 开始数据到文本转换...")
            print(f"   数据记录数: {len(data)}")
            print(f"   输出风格: {request.output_style}")
            print(f"   目标受众: {request.audience}")
            
            # 1. 分析数据
            analysis = await self.data_analyzer.analyze_data_patterns(data)
            print(f"   数据类型: {analysis.get('data_type', 'unknown')}")
            
            # 2. 选择模板
            template = await self.template_engine.select_template(
                analysis.get("data_type", "general_analysis"),
                request.output_style,
                request.data_context.template_context
            )
            
            # 3. 生成自然语言
            natural_text = await self.text_generator.generate_narrative(
                data, analysis, template, request.output_style
            )
            
            # 4. 构建结果
            result = {
                "success": True,
                "natural_text": natural_text,
                "analysis": analysis,
                "template_used": template,
                "metadata": {
                    "data_records": len(data),
                    "data_type": analysis.get("data_type"),
                    "style": request.output_style,
                    "insights_count": len(analysis.get("insights", [])),
                    "text_length": len(natural_text)
                }
            }
            
            print(f"✅ 文本转换完成!")
            print(f"   生成文本长度: {len(natural_text)} 字符")
            print(f"   包含洞察数: {len(analysis.get('insights', []))}")
            print(f"   文本预览: {natural_text[:100]}...")
            
            return result
            
        except Exception as e:
            print(f"❌ 文本转换失败: {e}")
            return {
                "success": False,
                "natural_text": f"数据转换失败：{str(e)}",
                "error": str(e)
            }
    
    async def convert_placeholder_result(
        self,
        placeholder: str,
        data: List[Dict[str, Any]],
        template_context: Dict[str, Any] = None,
        style: str = "business_report"
    ) -> str:
        """简化的占位符结果转换"""
        try:
            # 构建请求
            data_context = DataContext(
                data=data,
                placeholder_info={"original": placeholder},
                template_context=template_context or {},
                business_context={}
            )
            
            request = TextGenerationRequest(
                data_context=data_context,
                output_style=style,
                audience="management",
                include_insights=True,
                include_numbers=True
            )
            
            # 执行转换
            result = await self.convert_to_natural_text(request)
            
            if result["success"]:
                return result["natural_text"]
            else:
                return f"转换失败：{result.get('error', '未知错误')}"
                
        except Exception as e:
            return f"转换异常：{str(e)}"


async def demo_data_to_text_conversion():
    """演示数据到文本转换功能"""
    converter = DataToTextConverter()
    
    # 示例数据1：客户分析
    print("🎯 示例1：客户分析数据转换")
    print("=" * 50)
    
    placeholder1 = "{{客户分析:统计本年度各客户类型的客户数量和平均消费,计算贡献占比}}"
    data1 = [
        {"type": "VIP", "count": 150, "avg_spend": 8500, "contribution": 65.2},
        {"type": "普通", "count": 1200, "avg_spend": 2300, "contribution": 28.5},
        {"type": "新用户", "count": 800, "avg_spend": 850, "contribution": 6.3}
    ]
    
    # 商务报告风格
    text1_business = await converter.convert_placeholder_result(
        placeholder1, data1, style="business_report"
    )
    print(f"📊 商务报告风格:\n{text1_business}\n")
    
    # 轻松风格
    text1_casual = await converter.convert_placeholder_result(
        placeholder1, data1, style="casual"
    )
    print(f"💬 轻松风格:\n{text1_casual}\n")
    
    # 技术风格
    text1_technical = await converter.convert_placeholder_result(
        placeholder1, data1, style="technical"
    )
    print(f"🔧 技术风格:\n{text1_technical}\n")
    
    # 示例数据2：销售分析
    print("\n🎯 示例2：销售分析数据转换")
    print("=" * 50)
    
    placeholder2 = "{{销售数据分析:查询各地区销售额,按销售额排序,包含增长率}}"
    data2 = [
        {"region": "华南", "sales": 500000, "growth": 15.2, "rank": 1},
        {"region": "华东", "sales": 450000, "growth": 8.7, "rank": 2},
        {"region": "华北", "sales": 300000, "growth": -2.1, "rank": 3},
        {"region": "西南", "sales": 170000, "growth": 22.3, "rank": 4}
    ]
    
    text2 = await converter.convert_placeholder_result(
        placeholder2, data2, style="business_report"
    )
    print(f"📈 销售分析结果:\n{text2}\n")
    
    print("🎉 数据到文本转换演示完成!")


if __name__ == "__main__":
    asyncio.run(demo_data_to_text_conversion())