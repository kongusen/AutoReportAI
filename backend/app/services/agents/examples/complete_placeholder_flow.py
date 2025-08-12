"""
完整的占位符处理流程演示

展示从占位符输入到自然语言输出的完整流程：
占位符 → 数据查询 → 结构化数据 → 自然语言文本

这是您需求的完整实现：
1. 基于占位符构建数据查询
2. 获取准确的结构化数据
3. 结合模板上下文转换为自然语句
"""

import asyncio
from typing import Dict, Any, List
import json

from ..core.placeholder_processor import PlaceholderProcessor
from ..core.data_to_text_converter import DataToTextConverter, DataContext, TextGenerationRequest


class CompleteWorkflow:
    """完整的占位符处理工作流"""
    
    def __init__(self):
        self.placeholder_processor = PlaceholderProcessor()
        self.text_converter = DataToTextConverter()
    
    async def process_placeholder_to_text(
        self,
        placeholder: str,
        template_context: Dict[str, Any] = None,
        output_style: str = "business_report",
        audience: str = "management"
    ) -> Dict[str, Any]:
        """从占位符到自然文本的完整流程"""
        
        print(f"🚀 开始完整流程处理:")
        print(f"   占位符: {placeholder}")
        print(f"   输出风格: {output_style}")
        print("=" * 60)
        
        try:
            # 阶段1: 处理占位符，获取结构化数据
            print("📊 阶段1: 占位符数据查询...")
            data_result = await self.placeholder_processor.process_placeholder(placeholder)
            
            if not data_result.success:
                return {
                    "success": False,
                    "error": f"数据查询失败: {data_result.error_message}",
                    "stage": "data_query"
                }
            
            structured_data = data_result.data
            print(f"✅ 获得结构化数据: {len(structured_data)} 条记录")
            
            # 阶段2: 转换为自然语言文本
            print("\n📝 阶段2: 数据转文本...")
            
            # 准备转换上下文
            data_context = DataContext(
                data=structured_data,
                placeholder_info={"original": placeholder},
                template_context=template_context or {},
                business_context={}
            )
            
            text_request = TextGenerationRequest(
                data_context=data_context,
                output_style=output_style,
                audience=audience,
                include_insights=True,
                include_numbers=True
            )
            
            text_result = await self.text_converter.convert_to_natural_text(text_request)
            
            if not text_result["success"]:
                return {
                    "success": False,
                    "error": f"文本转换失败: {text_result.get('error')}",
                    "stage": "text_conversion",
                    "structured_data": structured_data
                }
            
            natural_text = text_result["natural_text"]
            print(f"✅ 生成自然文本: {len(natural_text)} 字符")
            
            # 阶段3: 整合结果
            print("\n🎯 阶段3: 结果整合...")
            
            complete_result = {
                "success": True,
                "placeholder": placeholder,
                "structured_data": structured_data,
                "natural_text": natural_text,
                "data_quality": data_result.data_quality,
                "text_analysis": text_result["analysis"],
                "metadata": {
                    "data_records": len(structured_data),
                    "data_quality_score": data_result.data_quality.get("quality_score", 0),
                    "text_length": len(natural_text),
                    "insights_count": len(text_result["analysis"].get("insights", [])),
                    "processing_time": "模拟处理时间",
                    "output_style": output_style,
                    "audience": audience
                }
            }
            
            print(f"🎉 完整流程处理成功!")
            print(f"   数据质量分数: {complete_result['metadata']['data_quality_score']:.2f}")
            print(f"   文本长度: {complete_result['metadata']['text_length']} 字符")
            print(f"   洞察数量: {complete_result['metadata']['insights_count']}")
            
            return complete_result
            
        except Exception as e:
            print(f"❌ 完整流程处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "stage": "unknown"
            }
    
    async def batch_process_placeholders(
        self,
        placeholders: List[str],
        output_style: str = "business_report"
    ) -> List[Dict[str, Any]]:
        """批量处理多个占位符"""
        
        print(f"🚀 批量处理 {len(placeholders)} 个占位符")
        print("=" * 60)
        
        results = []
        
        for i, placeholder in enumerate(placeholders, 1):
            print(f"\n【处理 {i}/{len(placeholders)}】{placeholder}")
            print("-" * 40)
            
            result = await self.process_placeholder_to_text(
                placeholder, 
                output_style=output_style
            )
            results.append(result)
            
            # 显示处理结果
            if result["success"]:
                print(f"✅ 处理成功")
                print(f"   📊 数据: {len(result['structured_data'])} 条记录")
                print(f"   📝 文本: {len(result['natural_text'])} 字符")
                print(f"   🎯 质量: {result['metadata']['data_quality_score']:.2f}")
            else:
                print(f"❌ 处理失败: {result['error']}")
        
        # 统计总结
        success_count = sum(1 for r in results if r["success"])
        print(f"\n📊 批量处理完成:")
        print(f"   总数: {len(results)}")
        print(f"   成功: {success_count}")
        print(f"   失败: {len(results) - success_count}")
        print(f"   成功率: {success_count/len(results)*100:.1f}%")
        
        return results
    
    async def generate_comparison_report(
        self,
        placeholder: str,
        styles: List[str] = None
    ) -> Dict[str, Any]:
        """生成不同风格的对比报告"""
        
        if styles is None:
            styles = ["business_report", "casual", "technical"]
        
        print(f"📊 生成多风格对比报告")
        print(f"   占位符: {placeholder}")
        print(f"   风格数量: {len(styles)}")
        print("=" * 60)
        
        # 首先获取数据（避免重复查询）
        data_result = await self.placeholder_processor.process_placeholder(placeholder)
        
        if not data_result.success:
            return {
                "success": False,
                "error": f"数据查询失败: {data_result.error_message}"
            }
        
        structured_data = data_result.data
        
        # 为每种风格生成文本
        style_results = {}
        
        for style in styles:
            print(f"\n🎨 生成 {style} 风格文本...")
            
            text_result = await self.text_converter.convert_placeholder_result(
                placeholder,
                structured_data,
                style=style
            )
            
            style_results[style] = {
                "text": text_result,
                "length": len(text_result),
                "word_count": len(text_result.replace('，', ' ').replace('。', ' ').split())
            }
            
            print(f"   长度: {len(text_result)} 字符")
        
        comparison_result = {
            "success": True,
            "placeholder": placeholder,
            "structured_data": structured_data,
            "style_results": style_results,
            "data_quality": data_result.data_quality,
            "comparison_metadata": {
                "styles_generated": len(styles),
                "data_records": len(structured_data),
                "average_length": sum(r["length"] for r in style_results.values()) / len(styles),
                "length_range": {
                    "min": min(r["length"] for r in style_results.values()),
                    "max": max(r["length"] for r in style_results.values())
                }
            }
        }
        
        print(f"🎉 对比报告生成完成!")
        print(f"   生成风格数: {len(styles)}")
        print(f"   平均长度: {comparison_result['comparison_metadata']['average_length']:.0f} 字符")
        
        return comparison_result


async def demo_complete_workflow():
    """演示完整工作流程"""
    workflow = CompleteWorkflow()
    
    # 演示1: 单个占位符完整流程
    print("🎯 演示1：单个占位符完整流程")
    print("=" * 70)
    
    placeholder1 = "{{客户分析:统计本年度各客户类型的客户数量和平均消费,计算贡献占比}}"
    result1 = await workflow.process_placeholder_to_text(
        placeholder1,
        template_context={"report_date": "2024年", "department": "市场部"},
        output_style="business_report",
        audience="management"
    )
    
    if result1["success"]:
        print(f"\n🎉 完整结果展示:")
        print(f"📊 原始数据:")
        for i, record in enumerate(result1["structured_data"][:3], 1):
            print(f"   {i}. {record}")
        
        print(f"\n📝 自然语言文本:")
        print(f"{result1['natural_text']}")
        
        print(f"\n📋 处理元数据:")
        metadata = result1["metadata"]
        print(f"   数据记录数: {metadata['data_records']}")
        print(f"   数据质量分数: {metadata['data_quality_score']:.2f}")
        print(f"   文本长度: {metadata['text_length']} 字符")
        print(f"   洞察数量: {metadata['insights_count']}")
    
    # 演示2: 多风格对比
    print(f"\n" + "=" * 70)
    print("🎯 演示2：多风格文本对比")
    print("=" * 70)
    
    comparison_result = await workflow.generate_comparison_report(
        placeholder1,
        styles=["business_report", "casual", "technical"]
    )
    
    if comparison_result["success"]:
        print(f"\n📊 同一数据的不同风格表达:")
        
        for style, style_data in comparison_result["style_results"].items():
            print(f"\n🎨 【{style}风格】({style_data['length']}字符):")
            print(f"{style_data['text']}")
            print("-" * 50)
    
    # 演示3: 批量处理
    print(f"\n" + "=" * 70)
    print("🎯 演示3：批量占位符处理")
    print("=" * 70)
    
    batch_placeholders = [
        "{{销售数据分析:查询最近3个月各地区销售额,按地区排序,包含增长率}}",
        "{{产品分析:统计热销产品TOP5,包含销量和增长趋势}}",
        "{{财务分析:计算本季度收入和利润,与上季度对比}}"
    ]
    
    batch_results = await workflow.batch_process_placeholders(
        batch_placeholders,
        output_style="business_report"
    )
    
    print(f"\n📊 批量处理结果汇总:")
    for i, result in enumerate(batch_results, 1):
        if result["success"]:
            print(f"\n{i}. ✅ {result['placeholder'][:30]}...")
            print(f"   📄 文本预览: {result['natural_text'][:80]}...")
        else:
            print(f"\n{i}. ❌ {result['placeholder'][:30]}...")
            print(f"   🚫 错误: {result['error']}")


async def show_practical_examples():
    """展示实际业务场景示例"""
    workflow = CompleteWorkflow()
    
    print("💼 实际业务场景演示")
    print("=" * 70)
    
    # 业务场景1: 日报生成
    print("\n📈 场景1: 日报数据自动转文本")
    print("-" * 40)
    
    daily_placeholder = "{{销售日报:统计昨日各渠道销售情况,包含完成率和排名}}"
    
    # 模拟真实数据
    simulated_data = [
        {"channel": "线上商城", "sales": 125000, "target": 100000, "completion_rate": 125.0, "rank": 1},
        {"channel": "门店销售", "sales": 98000, "target": 110000, "completion_rate": 89.1, "rank": 2},
        {"channel": "分销渠道", "sales": 75000, "target": 80000, "completion_rate": 93.8, "rank": 3}
    ]
    
    # 直接使用文本转换器（模拟已有数据）
    daily_text = await workflow.text_converter.convert_placeholder_result(
        daily_placeholder,
        simulated_data,
        style="business_report"
    )
    
    print(f"📊 日报文本生成结果:")
    print(f"{daily_text}")
    
    # 业务场景2: 月度分析报告
    print(f"\n📊 场景2: 月度客户分析报告")
    print("-" * 40)
    
    monthly_placeholder = "{{客户分析:月度客户价值分析,各类型客户贡献度对比}}"
    
    monthly_data = [
        {"type": "企业客户", "count": 45, "avg_spend": 25000, "contribution": 58.3, "growth": 12.5},
        {"type": "个人高端", "count": 380, "avg_spend": 3200, "contribution": 31.2, "growth": 8.9},
        {"type": "普通客户", "count": 2100, "avg_spend": 650, "contribution": 10.5, "growth": -2.1}
    ]
    
    monthly_text = await workflow.text_converter.convert_placeholder_result(
        monthly_placeholder,
        monthly_data,
        template_context={
            "period": "2024年3月",
            "report_type": "月度客户价值分析"
        },
        style="business_report"
    )
    
    print(f"📈 月度报告文本:")
    print(f"{monthly_text}")
    
    # 业务场景3: 异常分析报告
    print(f"\n⚠️  场景3: 异常数据分析报告")
    print("-" * 40)
    
    anomaly_placeholder = "{{异常分析:识别销售异常波动的产品类别,分析影响程度}}"
    
    anomaly_data = [
        {"category": "数码产品", "normal_sales": 150000, "current_sales": 89000, "deviation": -40.7, "severity": "高"},
        {"category": "家居用品", "normal_sales": 80000, "current_sales": 125000, "deviation": 56.3, "severity": "中"},
        {"category": "服装配件", "normal_sales": 95000, "current_sales": 78000, "deviation": -17.9, "severity": "低"}
    ]
    
    anomaly_text = await workflow.text_converter.convert_placeholder_result(
        anomaly_placeholder,
        anomaly_data,
        template_context={
            "analysis_period": "最近7天",
            "baseline": "过去30天平均值"
        },
        style="technical"
    )
    
    print(f"🔍 异常分析文本:")
    print(f"{anomaly_text}")
    
    print(f"\n🎉 实际业务场景演示完成!")


if __name__ == "__main__":
    print("🚀 启动完整占位符处理流程演示")
    print("从占位符输入到自然语言输出的端到端解决方案")
    print("=" * 80)
    
    # 运行主要演示
    asyncio.run(demo_complete_workflow())
    
    print(f"\n" + "=" * 80)
    
    # 运行实际场景演示
    asyncio.run(show_practical_examples())