"""
占位符处理器 - 核心数据查询构建引擎

专门处理占位符中的提示词，构建准确的数据查询，并获取正确的数据。
这是实现从占位符到数据的核心处理流程。

核心功能：
1. 智能解析占位符语法和提示词
2. 构建精确的数据库查询
3. 执行查询并获取数据
4. 验证数据准确性和完整性
"""

import re
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ..enhanced.enhanced_data_query_agent import EnhancedDataQueryAgent, SemanticQueryRequest
from ..tools.data_processing_tools import DataValidationTool, DataTransformationTool
from ..base import AgentResult


@dataclass
class PlaceholderContext:
    """占位符上下文"""
    original_placeholder: str
    parsed_content: Dict[str, Any]
    data_source: str
    table_name: Optional[str] = None
    schema_info: Dict[str, Any] = field(default_factory=dict)
    user_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuerySpec:
    """查询规格说明"""
    select_fields: List[str]
    from_table: str
    where_conditions: List[Dict[str, Any]]
    group_by_fields: List[str]
    order_by_fields: List[Dict[str, str]]  # [{"field": "date", "direction": "desc"}]
    aggregations: List[Dict[str, str]]     # [{"function": "sum", "field": "amount", "alias": "total"}]
    calculations: List[Dict[str, Any]]     # 需要计算的指标
    limit: Optional[int] = None


@dataclass
class DataResult:
    """数据结果"""
    success: bool
    data: List[Dict[str, Any]]
    row_count: int
    columns: List[str]
    query_info: Dict[str, Any]
    data_quality: Dict[str, Any]
    processing_log: List[str]
    error_message: Optional[str] = None


class PlaceholderParser:
    """占位符解析器"""
    
    def __init__(self):
        # 定义占位符的正则表达式模式
        self.placeholder_pattern = r'\{\{([^}]+)\}\}'
        
        # 定义关键词映射
        self.time_keywords = {
            "最近3个月": {"type": "relative", "value": 3, "unit": "month"},
            "最近6个月": {"type": "relative", "value": 6, "unit": "month"},
            "最近1年": {"type": "relative", "value": 1, "unit": "year"},
            "本月": {"type": "current", "unit": "month"},
            "本季度": {"type": "current", "unit": "quarter"},
            "本年": {"type": "current", "unit": "year"},
            "上个月": {"type": "previous", "unit": "month"},
            "去年同期": {"type": "year_ago", "unit": "same_period"}
        }
        
        self.metric_keywords = {
            "销售额": {"field": "sales_amount", "type": "numeric", "aggregation": "sum"},
            "销售量": {"field": "sales_quantity", "type": "numeric", "aggregation": "sum"},
            "订单数": {"field": "order_count", "type": "numeric", "aggregation": "count"},
            "客户数": {"field": "customer_count", "type": "numeric", "aggregation": "count_distinct"},
            "平均客单价": {"field": "avg_order_value", "type": "calculated", "formula": "sales_amount / order_count"},
            "利润": {"field": "profit", "type": "numeric", "aggregation": "sum"},
            "利润率": {"field": "profit_rate", "type": "calculated", "formula": "profit / sales_amount * 100"}
        }
        
        self.dimension_keywords = {
            "地区": {"field": "region", "type": "category"},
            "产品": {"field": "product_name", "type": "category"}, 
            "产品类别": {"field": "product_category", "type": "category"},
            "渠道": {"field": "channel", "type": "category"},
            "客户类型": {"field": "customer_type", "type": "category"},
            "月份": {"field": "month", "type": "date_part"},
            "季度": {"field": "quarter", "type": "date_part"},
            "年份": {"field": "year", "type": "date_part"}
        }
        
        self.calculation_keywords = {
            "同比增长率": {"type": "yoy_growth", "requires": ["current_period", "same_period_last_year"]},
            "环比增长率": {"type": "mom_growth", "requires": ["current_period", "previous_period"]},
            "累计值": {"type": "cumulative", "requires": ["running_total"]},
            "平均值": {"type": "average", "function": "avg"},
            "最大值": {"type": "maximum", "function": "max"},
            "最小值": {"type": "minimum", "function": "min"},
            "占比": {"type": "percentage", "requires": ["part", "total"]}
        }
    
    async def parse_placeholder(self, placeholder_text: str) -> PlaceholderContext:
        """解析占位符内容"""
        try:
            # 提取占位符内容
            matches = re.findall(self.placeholder_pattern, placeholder_text)
            if not matches:
                raise ValueError("未找到有效的占位符格式 {{...}}")
            
            placeholder_content = matches[0]
            
            # 分析占位符结构
            parsed_content = {
                "analysis_type": self._extract_analysis_type(placeholder_content),
                "time_range": self._extract_time_range(placeholder_content),
                "metrics": self._extract_metrics(placeholder_content),
                "dimensions": self._extract_dimensions(placeholder_content),
                "calculations": self._extract_calculations(placeholder_content),
                "filters": self._extract_filters(placeholder_content),
                "data_source": self._identify_data_source(placeholder_content)
            }
            
            # 创建上下文
            context = PlaceholderContext(
                original_placeholder=placeholder_text,
                parsed_content=parsed_content,
                data_source=parsed_content["data_source"]
            )
            
            print(f"📝 占位符解析完成:")
            print(f"   原始内容: {placeholder_text}")
            print(f"   分析类型: {parsed_content['analysis_type']}")
            print(f"   时间范围: {parsed_content['time_range']}")
            print(f"   指标: {parsed_content['metrics']}")
            print(f"   维度: {parsed_content['dimensions']}")
            print(f"   计算: {parsed_content['calculations']}")
            
            return context
            
        except Exception as e:
            print(f"❌ 占位符解析失败: {e}")
            raise
    
    def _extract_analysis_type(self, content: str) -> str:
        """提取分析类型"""
        if "销售" in content:
            return "sales_analysis"
        elif "用户" in content or "客户" in content:
            return "customer_analysis"
        elif "财务" in content or "收入" in content or "利润" in content:
            return "financial_analysis"
        elif "订单" in content:
            return "order_analysis"
        elif "产品" in content:
            return "product_analysis"
        else:
            return "general_analysis"
    
    def _extract_time_range(self, content: str) -> Optional[Dict[str, Any]]:
        """提取时间范围"""
        for keyword, time_info in self.time_keywords.items():
            if keyword in content:
                return {
                    "keyword": keyword,
                    **time_info
                }
        return None
    
    def _extract_metrics(self, content: str) -> List[Dict[str, Any]]:
        """提取指标"""
        metrics = []
        for keyword, metric_info in self.metric_keywords.items():
            if keyword in content:
                metrics.append({
                    "keyword": keyword,
                    **metric_info
                })
        return metrics
    
    def _extract_dimensions(self, content: str) -> List[Dict[str, Any]]:
        """提取维度"""
        dimensions = []
        
        # 查找明确的分组维度
        group_patterns = [
            r"按(\w+)分组", r"按(\w+)统计", r"分(\w+)统计", r"(\w+)维度"
        ]
        
        for pattern in group_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if match in self.dimension_keywords:
                    dim_info = self.dimension_keywords[match]
                    dimensions.append({
                        "keyword": match,
                        **dim_info
                    })
        
        # 查找隐含的维度
        for keyword, dim_info in self.dimension_keywords.items():
            if keyword in content and not any(d["keyword"] == keyword for d in dimensions):
                dimensions.append({
                    "keyword": keyword,
                    **dim_info
                })
        
        return dimensions
    
    def _extract_calculations(self, content: str) -> List[Dict[str, Any]]:
        """提取计算要求"""
        calculations = []
        for keyword, calc_info in self.calculation_keywords.items():
            if keyword in content:
                calculations.append({
                    "keyword": keyword,
                    **calc_info
                })
        return calculations
    
    def _extract_filters(self, content: str) -> List[Dict[str, Any]]:
        """提取过滤条件"""
        filters = []
        
        # 提取具体的过滤条件
        # 例如: "大于1000", "等于北京", "包含VIP"
        filter_patterns = [
            (r"大于(\d+)", {"operator": ">", "type": "numeric"}),
            (r"小于(\d+)", {"operator": "<", "type": "numeric"}),
            (r"等于(\w+)", {"operator": "=", "type": "exact"}),
            (r"包含(\w+)", {"operator": "like", "type": "text"}),
            (r"不包含(\w+)", {"operator": "not_like", "type": "text"})
        ]
        
        for pattern, filter_info in filter_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                filters.append({
                    "value": match,
                    **filter_info
                })
        
        return filters
    
    def _identify_data_source(self, content: str) -> str:
        """识别数据源"""
        # 根据分析类型推断数据源
        if "销售" in content:
            return "sales_database"
        elif "用户" in content or "客户" in content:
            return "user_database"
        elif "订单" in content:
            return "order_database"
        elif "财务" in content:
            return "financial_database"
        else:
            return "main_database"


class QueryBuilder:
    """查询构建器"""
    
    def __init__(self):
        # 表名映射
        self.table_mapping = {
            "sales_analysis": "sales_data",
            "customer_analysis": "customer_data", 
            "financial_analysis": "financial_data",
            "order_analysis": "order_data",
            "product_analysis": "product_data"
        }
        
        # 字段映射
        self.field_mapping = {
            "sales_amount": "amount",
            "sales_quantity": "quantity",
            "order_count": "order_id",
            "customer_count": "customer_id",
            "region": "region_name",
            "product_name": "product_name",
            "product_category": "category"
        }
    
    async def build_query_spec(self, context: PlaceholderContext) -> QuerySpec:
        """构建查询规格"""
        try:
            parsed = context.parsed_content
            
            # 确定主表
            table_name = self.table_mapping.get(parsed["analysis_type"], "main_table")
            
            # 构建SELECT字段
            select_fields = []
            aggregations = []
            
            # 添加维度字段
            for dim in parsed["dimensions"]:
                field_name = self.field_mapping.get(dim["field"], dim["field"])
                select_fields.append(field_name)
            
            # 添加指标字段（需要聚合）
            for metric in parsed["metrics"]:
                field_name = self.field_mapping.get(metric["field"], metric["field"])
                if metric["type"] == "numeric":
                    agg_function = metric["aggregation"]
                    aggregations.append({
                        "function": agg_function,
                        "field": field_name,
                        "alias": f"{agg_function}_{field_name}"
                    })
            
            # 构建WHERE条件
            where_conditions = []
            
            # 添加时间条件
            if parsed["time_range"]:
                time_condition = self._build_time_condition(parsed["time_range"])
                if time_condition:
                    where_conditions.append(time_condition)
            
            # 添加过滤条件
            for filter_item in parsed["filters"]:
                where_conditions.append({
                    "field": "value_field",  # 需要根据上下文确定
                    "operator": filter_item["operator"],
                    "value": filter_item["value"]
                })
            
            # 构建GROUP BY
            group_by_fields = [
                self.field_mapping.get(dim["field"], dim["field"]) 
                for dim in parsed["dimensions"]
            ]
            
            # 构建ORDER BY
            order_by_fields = []
            if group_by_fields:
                order_by_fields.append({
                    "field": group_by_fields[0],
                    "direction": "asc"
                })
            
            # 构建计算字段
            calculations = []
            for calc in parsed["calculations"]:
                calc_spec = self._build_calculation_spec(calc)
                if calc_spec:
                    calculations.append(calc_spec)
            
            query_spec = QuerySpec(
                select_fields=select_fields,
                from_table=table_name,
                where_conditions=where_conditions,
                group_by_fields=group_by_fields,
                order_by_fields=order_by_fields,
                aggregations=aggregations,
                calculations=calculations
            )
            
            print(f"🔧 查询规格构建完成:")
            print(f"   表名: {table_name}")
            print(f"   选择字段: {select_fields}")
            print(f"   聚合函数: {[f\"{a['function']}({a['field']})\" for a in aggregations]}")
            print(f"   分组字段: {group_by_fields}")
            print(f"   条件数量: {len(where_conditions)}")
            
            return query_spec
            
        except Exception as e:
            print(f"❌ 查询规格构建失败: {e}")
            raise
    
    def _build_time_condition(self, time_range: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """构建时间条件"""
        try:
            if time_range["type"] == "relative":
                # 计算相对时间
                if time_range["unit"] == "month":
                    start_date = datetime.now() - timedelta(days=time_range["value"] * 30)
                elif time_range["unit"] == "year":
                    start_date = datetime.now() - timedelta(days=time_range["value"] * 365)
                else:
                    return None
                
                return {
                    "field": "date",
                    "operator": ">=",
                    "value": start_date.strftime("%Y-%m-%d")
                }
            
            elif time_range["type"] == "current":
                # 当前周期
                now = datetime.now()
                if time_range["unit"] == "month":
                    start_date = now.replace(day=1)
                elif time_range["unit"] == "quarter":
                    quarter = (now.month - 1) // 3 + 1
                    start_month = (quarter - 1) * 3 + 1
                    start_date = now.replace(month=start_month, day=1)
                else:
                    return None
                
                return {
                    "field": "date", 
                    "operator": ">=",
                    "value": start_date.strftime("%Y-%m-%d")
                }
            
            return None
            
        except Exception:
            return None
    
    def _build_calculation_spec(self, calculation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """构建计算规格"""
        calc_type = calculation["type"]
        
        if calc_type == "yoy_growth":
            return {
                "type": "year_over_year_growth",
                "formula": "(current_value - previous_year_value) / previous_year_value * 100",
                "requires_historical_data": True
            }
        elif calc_type == "mom_growth":
            return {
                "type": "month_over_month_growth", 
                "formula": "(current_value - previous_month_value) / previous_month_value * 100",
                "requires_historical_data": True
            }
        elif calc_type == "average":
            return {
                "type": "average",
                "function": calculation["function"]
            }
        elif calc_type == "percentage":
            return {
                "type": "percentage",
                "formula": "value / total * 100"
            }
        
        return None


class DataQueryExecutor:
    """数据查询执行器"""
    
    def __init__(self):
        self.data_agent = EnhancedDataQueryAgent()
        self.validation_tool = DataValidationTool()
        self.transform_tool = DataTransformationTool()
    
    async def execute_query(
        self, 
        context: PlaceholderContext, 
        query_spec: QuerySpec
    ) -> DataResult:
        """执行数据查询"""
        try:
            processing_log = []
            processing_log.append(f"开始执行查询: {context.original_placeholder}")
            
            # 1. 构建语义查询请求
            semantic_request = self._build_semantic_request(context, query_spec)
            processing_log.append(f"构建语义查询请求完成")
            
            # 2. 执行查询
            query_result = await self.data_agent.execute_semantic_query(semantic_request)
            processing_log.append(f"数据库查询执行完成")
            
            if not query_result.success:
                return DataResult(
                    success=False,
                    data=[],
                    row_count=0,
                    columns=[],
                    query_info={},
                    data_quality={},
                    processing_log=processing_log,
                    error_message=query_result.error_message
                )
            
            # 3. 提取数据
            raw_data = query_result.data.results if hasattr(query_result.data, 'results') else []
            processing_log.append(f"获取原始数据: {len(raw_data)} 条记录")
            
            # 4. 数据验证
            validation_result = await self._validate_data(raw_data)
            processing_log.append(f"数据验证完成: 质量分数 {validation_result.get('quality_score', 0):.2f}")
            
            # 5. 数据处理和转换
            processed_data = await self._process_data(raw_data, query_spec)
            processing_log.append(f"数据处理完成: {len(processed_data)} 条记录")
            
            # 6. 应用计算
            final_data = await self._apply_calculations(processed_data, query_spec.calculations)
            processing_log.append(f"计算应用完成")
            
            # 7. 构建结果
            columns = list(final_data[0].keys()) if final_data else []
            
            result = DataResult(
                success=True,
                data=final_data,
                row_count=len(final_data),
                columns=columns,
                query_info={
                    "original_placeholder": context.original_placeholder,
                    "table_name": query_spec.from_table,
                    "execution_time": query_result.metadata.get('execution_time', 0) if hasattr(query_result, 'metadata') else 0
                },
                data_quality=validation_result,
                processing_log=processing_log
            )
            
            print(f"✅ 查询执行成功:")
            print(f"   数据行数: {result.row_count}")
            print(f"   数据列数: {len(result.columns)}")
            print(f"   数据质量: {validation_result.get('quality_score', 0):.2f}/1.0")
            
            return result
            
        except Exception as e:
            print(f"❌ 查询执行失败: {e}")
            return DataResult(
                success=False,
                data=[],
                row_count=0,
                columns=[],
                query_info={},
                data_quality={},
                processing_log=processing_log,
                error_message=str(e)
            )
    
    def _build_semantic_request(
        self, 
        context: PlaceholderContext, 
        query_spec: QuerySpec
    ) -> SemanticQueryRequest:
        """构建语义查询请求"""
        
        # 构建自然语言查询描述
        query_parts = []
        
        # 添加查询目标
        if query_spec.aggregations:
            metrics = [f"{agg['function']}({agg['field']})" for agg in query_spec.aggregations]
            query_parts.append(f"计算 {', '.join(metrics)}")
        
        # 添加数据来源
        query_parts.append(f"从 {query_spec.from_table} 表")
        
        # 添加分组
        if query_spec.group_by_fields:
            query_parts.append(f"按 {', '.join(query_spec.group_by_fields)} 分组")
        
        # 添加条件
        if query_spec.where_conditions:
            conditions = [f"{cond.get('field', '')} {cond.get('operator', '')} {cond.get('value', '')}" 
                         for cond in query_spec.where_conditions]
            query_parts.append(f"条件: {', '.join(conditions)}")
        
        natural_query = "，".join(query_parts)
        
        return SemanticQueryRequest(
            query=natural_query,
            data_source=context.data_source,
            natural_language=True,
            semantic_enhancement=True,
            intent_analysis=True,
            query_optimization=True,
            context={
                "table_name": query_spec.from_table,
                "select_fields": query_spec.select_fields,
                "aggregations": query_spec.aggregations,
                "group_by": query_spec.group_by_fields,
                "where_conditions": query_spec.where_conditions
            }
        )
    
    async def _validate_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证数据质量"""
        try:
            validation_result = await self.validation_tool.execute(
                data,
                context={"validation_rules": ["not_empty", "type_consistency", "completeness"]}
            )
            
            if validation_result.success:
                return validation_result.data
            else:
                return {"quality_score": 0.5, "issues": [validation_result.error_message]}
                
        except Exception:
            return {"quality_score": 0.5, "issues": ["验证过程异常"]}
    
    async def _process_data(
        self, 
        data: List[Dict[str, Any]], 
        query_spec: QuerySpec
    ) -> List[Dict[str, Any]]:
        """处理数据"""
        try:
            # 数据清理和转换
            transform_result = await self.transform_tool.execute(
                data,
                context={
                    "operations": ["clean_nulls", "standardize_formats"],
                    "target_schema": {
                        field: {"type": "auto_detect"} for field in query_spec.select_fields
                    }
                }
            )
            
            if transform_result.success:
                return transform_result.data.get('transformed_data', data)
            else:
                return data
                
        except Exception:
            return data
    
    async def _apply_calculations(
        self, 
        data: List[Dict[str, Any]], 
        calculations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """应用计算"""
        try:
            if not calculations:
                return data
            
            # 这里实现具体的计算逻辑
            # 例如同比增长率、环比增长率等
            
            # 示例：简单的百分比计算
            for calc in calculations:
                if calc["type"] == "percentage":
                    total = sum(float(row.get("amount", 0)) for row in data)
                    for row in data:
                        if total > 0:
                            row["percentage"] = round(float(row.get("amount", 0)) / total * 100, 2)
                        else:
                            row["percentage"] = 0
            
            return data
            
        except Exception:
            return data


class PlaceholderProcessor:
    """占位符处理器 - 主控制器"""
    
    def __init__(self):
        self.parser = PlaceholderParser()
        self.query_builder = QueryBuilder()
        self.query_executor = DataQueryExecutor()
    
    async def process_placeholder(self, placeholder_text: str) -> DataResult:
        """处理占位符的完整流程"""
        try:
            print(f"🎯 开始处理占位符: {placeholder_text}")
            print("=" * 50)
            
            # 步骤1: 解析占位符
            print("📝 步骤1: 解析占位符内容...")
            context = await self.parser.parse_placeholder(placeholder_text)
            
            # 步骤2: 构建查询规格
            print("\n🔧 步骤2: 构建查询规格...")
            query_spec = await self.query_builder.build_query_spec(context)
            
            # 步骤3: 执行数据查询
            print("\n🚀 步骤3: 执行数据查询...")
            result = await self.query_executor.execute_query(context, query_spec)
            
            # 步骤4: 结果总结
            print(f"\n✅ 处理完成!")
            if result.success:
                print(f"   📊 成功获取 {result.row_count} 条数据记录")
                print(f"   📋 包含字段: {', '.join(result.columns)}")
                print(f"   🎯 数据质量分数: {result.data_quality.get('quality_score', 0):.2f}")
                
                # 显示数据样例
                if result.data:
                    print(f"   📄 数据样例:")
                    for i, row in enumerate(result.data[:2], 1):
                        print(f"      行{i}: {row}")
            else:
                print(f"   ❌ 处理失败: {result.error_message}")
            
            return result
            
        except Exception as e:
            print(f"❌ 占位符处理异常: {e}")
            return DataResult(
                success=False,
                data=[],
                row_count=0,
                columns=[],
                query_info={"error": str(e)},
                data_quality={},
                processing_log=[f"处理异常: {e}"],
                error_message=str(e)
            )
    
    async def process_multiple_placeholders(
        self, 
        placeholder_list: List[str]
    ) -> List[DataResult]:
        """批量处理多个占位符"""
        results = []
        
        print(f"🚀 开始批量处理 {len(placeholder_list)} 个占位符")
        print("=" * 60)
        
        for i, placeholder in enumerate(placeholder_list, 1):
            print(f"\n【占位符 {i}/{len(placeholder_list)}】")
            result = await self.process_placeholder(placeholder)
            results.append(result)
            
            # 显示处理进度
            success_count = sum(1 for r in results if r.success)
            print(f"   当前进度: {i}/{len(placeholder_list)} (成功: {success_count})")
        
        print(f"\n🎉 批量处理完成!")
        print(f"   总计: {len(results)} 个占位符")
        print(f"   成功: {sum(1 for r in results if r.success)} 个") 
        print(f"   失败: {sum(1 for r in results if not r.success)} 个")
        
        return results


async def demo_placeholder_processing():
    """演示占位符处理功能"""
    processor = PlaceholderProcessor()
    
    # 测试占位符示例
    test_placeholders = [
        "{{销售数据分析:查询最近3个月的销售额,按地区分组,包含同比增长率}}",
        "{{客户分析:统计本年度客户数,按客户类型分组,计算平均客单价}}",
        "{{产品分析:获取最近6个月产品销售量,按产品类别分组,包含占比}}",
        "{{订单分析:查询本季度订单数据,按月份分组,计算完成率}}"
    ]
    
    # 单个占位符处理演示
    print("🎯 单个占位符处理演示:")
    result = await processor.process_placeholder(test_placeholders[0])
    
    # 批量处理演示
    print(f"\n" + "="*60)
    print("🚀 批量占位符处理演示:")
    results = await processor.process_multiple_placeholders(test_placeholders)
    
    return results


if __name__ == "__main__":
    asyncio.run(demo_placeholder_processing())