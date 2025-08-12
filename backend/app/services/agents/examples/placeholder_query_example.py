"""
基于占位符构建数据查询的核心示例

展示如何从占位符和提示词构建正确的数据查询，然后使用工具分析获得准确数据。

核心流程：
1. 解析占位符中的提示词
2. 构建语义化的数据查询
3. 执行查询获取数据
4. 验证和优化查询结果
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..enhanced.enhanced_data_query_agent import (
    EnhancedDataQueryAgent, 
    SemanticQueryRequest,
    QueryIntent,
    MetadataInfo
)
from ..tools.data_processing_tools import (
    DataValidationTool,
    DataTransformationTool, 
    SchemaDetectionTool
)
from ..knowledge import KnowledgeContext


class PlaceholderQueryBuilder:
    """占位符查询构建器"""
    
    def __init__(self):
        self.data_agent = EnhancedDataQueryAgent()
        self.validation_tool = DataValidationTool()
        self.transform_tool = DataTransformationTool()
        self.schema_tool = SchemaDetectionTool()
    
    async def parse_placeholder_prompt(self, placeholder_content: str) -> Dict[str, Any]:
        """解析占位符中的提示词"""
        try:
            # 示例占位符内容解析
            # {{销售数据分析:查询最近3个月的销售额,按地区分组,包含同比增长率}}
            
            parsed_info = {
                "analysis_type": None,
                "time_range": None,
                "groupby_fields": [],
                "metrics": [],
                "filters": [],
                "calculations": []
            }
            
            # 提取分析类型
            if "销售数据分析" in placeholder_content:
                parsed_info["analysis_type"] = "sales_analysis"
            elif "用户行为分析" in placeholder_content:
                parsed_info["analysis_type"] = "user_behavior_analysis"
            elif "财务分析" in placeholder_content:
                parsed_info["analysis_type"] = "financial_analysis"
            
            # 提取时间范围
            if "最近3个月" in placeholder_content:
                parsed_info["time_range"] = "3_months"
            elif "最近1年" in placeholder_content:
                parsed_info["time_range"] = "1_year"
            elif "本季度" in placeholder_content:
                parsed_info["time_range"] = "current_quarter"
            
            # 提取分组字段
            if "按地区分组" in placeholder_content:
                parsed_info["groupby_fields"].append("region")
            if "按产品分组" in placeholder_content:
                parsed_info["groupby_fields"].append("product")
            if "按月份分组" in placeholder_content:
                parsed_info["groupby_fields"].append("month")
            
            # 提取指标
            if "销售额" in placeholder_content:
                parsed_info["metrics"].append("sales_amount")
            if "订单数" in placeholder_content:
                parsed_info["metrics"].append("order_count")
            if "客户数" in placeholder_content:
                parsed_info["metrics"].append("customer_count")
            
            # 提取计算要求
            if "同比增长率" in placeholder_content:
                parsed_info["calculations"].append("year_over_year_growth")
            if "环比增长率" in placeholder_content:
                parsed_info["calculations"].append("month_over_month_growth")
            if "平均值" in placeholder_content:
                parsed_info["calculations"].append("average")
            
            print(f"📝 占位符解析结果: {json.dumps(parsed_info, ensure_ascii=False, indent=2)}")
            return parsed_info
            
        except Exception as e:
            print(f"❌ 占位符解析失败: {e}")
            return {}
    
    async def build_semantic_query(self, parsed_info: Dict[str, Any]) -> SemanticQueryRequest:
        """构建语义化查询请求"""
        try:
            # 构建自然语言查询
            natural_query_parts = []
            
            # 添加查询目标
            if parsed_info.get("analysis_type") == "sales_analysis":
                natural_query_parts.append("查询销售数据")
            
            # 添加时间范围
            if parsed_info.get("time_range") == "3_months":
                natural_query_parts.append("最近3个月")
            elif parsed_info.get("time_range") == "1_year":
                natural_query_parts.append("最近1年")
            
            # 添加指标
            if parsed_info.get("metrics"):
                metrics_text = "、".join(parsed_info["metrics"])
                natural_query_parts.append(f"包含{metrics_text}")
            
            # 添加分组
            if parsed_info.get("groupby_fields"):
                groupby_text = "、".join(parsed_info["groupby_fields"])
                natural_query_parts.append(f"按{groupby_text}分组")
            
            # 添加计算
            if parsed_info.get("calculations"):
                calc_text = "、".join(parsed_info["calculations"])
                natural_query_parts.append(f"计算{calc_text}")
            
            natural_query = "，".join(natural_query_parts)
            
            # 构建查询请求
            query_request = SemanticQueryRequest(
                query=natural_query,
                data_source="main_database",  # 根据实际情况修改
                natural_language=True,
                semantic_enhancement=True,
                intent_analysis=True,
                query_optimization=True,
                context={
                    "analysis_type": parsed_info.get("analysis_type"),
                    "time_range": parsed_info.get("time_range"),
                    "required_fields": parsed_info.get("metrics", []) + parsed_info.get("groupby_fields", [])
                }
            )
            
            print(f"🔍 构建的语义查询: {natural_query}")
            return query_request
            
        except Exception as e:
            print(f"❌ 语义查询构建失败: {e}")
            raise
    
    async def execute_data_query(self, query_request: SemanticQueryRequest) -> Dict[str, Any]:
        """执行数据查询"""
        try:
            print(f"🚀 开始执行数据查询...")
            
            # 创建知识上下文
            knowledge_context = KnowledgeContext(
                agent_id="enhanced_data_query_agent",
                task_type="semantic_query",
                data_characteristics=query_request.context
            )
            
            # 执行语义查询
            result = await self.data_agent.execute_semantic_query(query_request)
            
            if result.success:
                print(f"✅ 查询执行成功")
                query_result = result.data
                
                # 显示查询结果信息
                if hasattr(query_result, 'results') and query_result.results:
                    print(f"📊 获得 {len(query_result.results)} 条数据记录")
                    
                    # 显示前几条记录作为示例
                    sample_records = query_result.results[:3]
                    for i, record in enumerate(sample_records, 1):
                        print(f"   记录{i}: {record}")
                
                # 显示元数据信息
                if hasattr(query_result, 'metadata'):
                    metadata = query_result.metadata
                    print(f"🔧 查询元数据:")
                    print(f"   - 执行时间: {metadata.get('execution_time', 'N/A')}ms")
                    print(f"   - 优化应用: {metadata.get('optimizations_applied', [])}")
                    print(f"   - 字段映射: {metadata.get('field_mappings', {})}")
                
                return {
                    "success": True,
                    "data": query_result.results if hasattr(query_result, 'results') else [],
                    "metadata": query_result.metadata if hasattr(query_result, 'metadata') else {},
                    "query_info": {
                        "original_query": query_request.query,
                        "optimized_query": getattr(query_result, 'optimized_query', None),
                        "execution_plan": getattr(query_result, 'execution_plan', None)
                    }
                }
            else:
                print(f"❌ 查询执行失败: {result.error_message}")
                return {
                    "success": False,
                    "error": result.error_message,
                    "data": []
                }
                
        except Exception as e:
            print(f"❌ 数据查询异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }
    
    async def validate_and_process_data(self, query_result: Dict[str, Any]) -> Dict[str, Any]:
        """验证和处理查询结果数据"""
        try:
            if not query_result.get("success") or not query_result.get("data"):
                return query_result
            
            raw_data = query_result["data"]
            print(f"🔍 开始数据验证和处理...")
            
            # 1. 数据验证
            validation_result = await self.validation_tool.execute(
                raw_data,
                context={"validation_rules": ["not_empty", "type_consistency", "range_check"]}
            )
            
            if validation_result.success:
                validation_info = validation_result.data
                print(f"✅ 数据验证通过:")
                print(f"   - 总记录数: {validation_info.get('total_records', 0)}")
                print(f"   - 有效记录: {validation_info.get('valid_records', 0)}")
                print(f"   - 数据质量分数: {validation_info.get('quality_score', 0):.2f}")
            else:
                print(f"⚠️  数据验证发现问题: {validation_result.error_message}")
            
            # 2. 模式检测
            schema_result = await self.schema_tool.execute(
                raw_data,
                context={"detect_types": True, "suggest_improvements": True}
            )
            
            if schema_result.success:
                schema_info = schema_result.data
                print(f"📋 数据模式分析:")
                detected_schema = schema_info.get('detected_schema', {})
                for field, field_info in detected_schema.items():
                    print(f"   - {field}: {field_info.get('type')} (缺失率: {field_info.get('null_rate', 0):.1%})")
            
            # 3. 数据转换和清理
            transform_result = await self.transform_tool.execute(
                raw_data,
                context={
                    "operations": ["clean_nulls", "standardize_formats", "detect_outliers"],
                    "schema": schema_result.data.get('detected_schema', {}) if schema_result.success else {}
                }
            )
            
            processed_data = raw_data
            if transform_result.success:
                processed_data = transform_result.data.get('transformed_data', raw_data)
                transform_info = transform_result.data
                print(f"🔧 数据处理完成:")
                print(f"   - 清理的空值: {transform_info.get('nulls_cleaned', 0)}")
                print(f"   - 标准化字段: {len(transform_info.get('standardized_fields', []))}")
                print(f"   - 检测到的异常值: {transform_info.get('outliers_detected', 0)}")
            
            # 4. 构建最终结果
            final_result = {
                "success": True,
                "data": processed_data,
                "metadata": {
                    **query_result.get("metadata", {}),
                    "validation": validation_result.data if validation_result.success else {},
                    "schema": schema_result.data if schema_result.success else {},
                    "transformation": transform_result.data if transform_result.success else {}
                },
                "query_info": query_result.get("query_info", {}),
                "data_quality": {
                    "total_records": len(processed_data),
                    "quality_score": validation_info.get('quality_score', 0) if validation_result.success else 0,
                    "processing_applied": transform_result.success
                }
            }
            
            return final_result
            
        except Exception as e:
            print(f"❌ 数据验证和处理失败: {e}")
            return {
                **query_result,
                "processing_error": str(e)
            }
    
    async def demonstrate_complete_flow(self, placeholder_examples: List[str]):
        """演示完整的占位符->查询->数据流程"""
        print("🎯 演示：从占位符到准确数据的完整流程")
        print("=" * 60)
        
        for i, placeholder in enumerate(placeholder_examples, 1):
            print(f"\n【示例 {i}】处理占位符: {placeholder}")
            print("-" * 40)
            
            try:
                # 步骤1: 解析占位符
                parsed_info = await self.parse_placeholder_prompt(placeholder)
                if not parsed_info:
                    print("❌ 占位符解析失败，跳过此示例")
                    continue
                
                # 步骤2: 构建语义查询
                query_request = await self.build_semantic_query(parsed_info)
                
                # 步骤3: 执行查询
                query_result = await self.execute_data_query(query_request)
                
                # 步骤4: 验证和处理数据
                final_result = await self.validate_and_process_data(query_result)
                
                # 步骤5: 总结结果
                if final_result.get("success"):
                    data_quality = final_result.get("data_quality", {})
                    print(f"\n✅ 完整流程执行成功!")
                    print(f"   📊 最终数据量: {data_quality.get('total_records', 0)} 条记录")
                    print(f"   🎯 数据质量分数: {data_quality.get('quality_score', 0):.2f}/1.0")
                    print(f"   🔧 已应用数据处理: {'是' if data_quality.get('processing_applied') else '否'}")
                    
                    # 显示数据样例
                    sample_data = final_result.get("data", [])[:2]
                    if sample_data:
                        print(f"   📋 数据样例:")
                        for j, record in enumerate(sample_data, 1):
                            print(f"      记录{j}: {record}")
                else:
                    print(f"❌ 流程执行失败: {final_result.get('error', '未知错误')}")
                    
            except Exception as e:
                print(f"❌ 示例 {i} 执行异常: {e}")
        
        print(f"\n🎉 演示完成! 展示了从占位符到准确数据的完整智能化流程")


async def main():
    """主演示函数"""
    builder = PlaceholderQueryBuilder()
    
    # 准备占位符示例
    placeholder_examples = [
        "{{销售数据分析:查询最近3个月的销售额,按地区分组,包含同比增长率}}",
        "{{用户行为分析:统计最近1年的用户活跃度,按月份分组,计算平均值}}",
        "{{财务分析:获取本季度的收入和成本数据,按产品分组,包含环比增长率}}",
        "{{订单分析:查询最近6个月的订单数据,按状态分组,计算完成率}}"
    ]
    
    # 执行完整演示
    await builder.demonstrate_complete_flow(placeholder_examples)
    
    print(f"\n" + "="*60)
    print("💡 核心价值总结:")
    print("✅ 占位符智能解析 - 自动理解用户意图")
    print("✅ 语义查询构建 - 将自然语言转换为精确查询")
    print("✅ 智能数据获取 - 优化查询性能和准确性") 
    print("✅ 数据质量保证 - 自动验证、清理和处理数据")
    print("✅ 端到端自动化 - 从需求到数据的完全自动化")


if __name__ == "__main__":
    asyncio.run(main())