"""
智能数据分析器 v2.0
===============================================

基于优化提示词系统的数据分析工具：
- 智能数据源探索和表结构分析
- 自动数据质量评估
- 智能字段映射和关系发现
- 数据统计和洞察生成
"""

import json
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator

from ..core.tools import IterativeTool, ToolContext, ToolResult, ToolResultType

logger = logging.getLogger(__name__)


class SmartDataAnalyzer(IterativeTool):
    """智能数据分析器"""
    
    def __init__(self):
        super().__init__(
            tool_name="smart_data_analyzer",
            tool_category="data_analysis"
        )
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        context: ToolContext
    ) -> AsyncGenerator[ToolResult, None]:
        """
        执行数据分析任务
        
        Args:
            input_data: 输入数据，包含分析类型等参数
            context: 工具执行上下文
        """
        
        yield self.create_progress_result("🔍 启动智能数据分析器")
        
        # 从input_data中提取参数
        analysis_type = input_data.get("analysis_type", "comprehensive")
        
        # 验证输入
        validation_result = await self.validate_input_enhanced(input_data)
        if not validation_result.get("valid", False):
            errors = validation_result.get("errors", ["输入验证失败"])
            yield self.create_error_result("; ".join(errors))
            return
        
        # 使用继承的迭代执行框架
        async for result in super().execute(input_data, context):
            yield result
    
    async def _validate_specific_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证数据分析特定输入"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # 验证分析类型
        analysis_type = input_data.get("analysis_type", "comprehensive")
        valid_types = ["table_structure", "data_quality", "relationship", "comprehensive"]
        
        if analysis_type not in valid_types:
            validation_result["valid"] = False
            validation_result["errors"].append(f"无效的分析类型: {analysis_type}")
            validation_result["suggestions"].append(f"支持的分析类型: {', '.join(valid_types)}")
        
        # 检查数据源信息（这将在执行时检查context）
        if not input_data.get("data_source_info"):
            validation_result["warnings"].append("未提供数据源信息，将尝试从上下文获取")
        
        return validation_result
    
    async def execute_single_iteration(
        self,
        input_data: Dict[str, Any],
        context: ToolContext,
        iteration: int
    ) -> AsyncGenerator[ToolResult, None]:
        """执行单次数据分析迭代"""
        
        analysis_type = input_data.get("analysis_type", "comprehensive")
        
        yield self.create_progress_result(
            f"🔍 第 {iteration + 1} 轮: 开始{analysis_type}分析",
            step="analysis",
            percentage=((iteration * 1) / self.max_iterations) * 100
        )
        
        # 根据分析类型选择执行方式
        if analysis_type == "table_structure":
            async for result in self._analyze_table_structure(context, **input_data):
                yield result
        elif analysis_type == "data_quality":
            async for result in self._analyze_data_quality(context, **input_data):
                yield result
        elif analysis_type == "relationship":
            async for result in self._analyze_relationships(context, **input_data):
                yield result
        elif analysis_type == "comprehensive":
            async for result in self._comprehensive_analysis(context, **input_data):
                yield result
        else:
            yield self.create_error_result(f"不支持的分析类型: {analysis_type}")
    
    async def _analyze_table_structure(
        self,
        context: ToolContext,
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """分析表结构"""
        
        yield self.create_progress_result("📊 开始表结构分析")
        
        try:
            # 获取数据源信息
            data_source_info = await self._ensure_data_source_info(context)
            if not data_source_info:
                yield self.create_error_result("无法获取数据源信息")
                return
            
            tables = data_source_info.get('tables', [])
            if not tables:
                yield self.create_error_result("数据源中没有可用的表")
                return
            
            yield self.create_progress_result(f"发现 {len(tables)} 个表，开始详细分析")
            
            # 分析每个表的结构
            table_analysis = []
            for i, table_name in enumerate(tables):
                yield self.create_progress_result(
                    f"分析表 {i+1}/{len(tables)}: {table_name}"
                )
                
                table_info = await self._analyze_single_table(
                    context, table_name, data_source_info
                )
                if table_info:
                    table_analysis.append(table_info)
            
            # 生成分析结果
            analysis_result = {
                "analysis_type": "table_structure",
                "data_source": {
                    "name": data_source_info.get('name', 'unknown'),
                    "type": data_source_info.get('type', 'unknown'),
                    "database": data_source_info.get('database', 'unknown')
                },
                "total_tables": len(tables),
                "analyzed_tables": len(table_analysis),
                "tables": table_analysis,
                "summary": self._generate_structure_summary(table_analysis),
                "recommendations": self._generate_structure_recommendations(table_analysis)
            }
            
            yield self.create_success_result(
                data=analysis_result,
                confidence=0.9,
                insights=[
                    f"分析了 {len(table_analysis)} 个表的结构",
                    f"发现 {sum(len(t.get('columns', [])) for t in table_analysis)} 个字段",
                    "表结构分析完成"
                ]
            )
            
        except Exception as e:
            self.logger.error(f"表结构分析异常: {e}")
            yield self.create_error_result(f"表结构分析失败: {str(e)}")
    
    async def _analyze_data_quality(
        self,
        context: ToolContext,
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """分析数据质量"""
        
        yield self.create_progress_result("🔎 开始数据质量分析")
        
        try:
            # 获取数据源信息
            data_source_info = await self._ensure_data_source_info(context)
            if not data_source_info:
                yield self.create_error_result("无法获取数据源信息")
                return
            
            # 生成数据质量分析提示词
            quality_prompt = self._build_data_quality_prompt(data_source_info, context)
            
            yield self.create_progress_result("🤖 AI分析数据质量模式")
            
            # 调用LLM进行数据质量分析
            quality_response = await self.ask_llm(
                prompt=quality_prompt,
                context=context,
                agent_type="data_analyst",
                task_type="data_quality_analysis"
            )
            
            # 解析分析结果
            quality_result = self._parse_quality_analysis(quality_response)
            
            if quality_result:
                yield self.create_success_result(
                    data={
                        "analysis_type": "data_quality",
                        "data_source": data_source_info.get('name', 'unknown'),
                        **quality_result
                    },
                    confidence=quality_result.get('confidence', 0.7),
                    insights=quality_result.get('insights', [])
                )
            else:
                yield self.create_error_result("数据质量分析结果解析失败")
                
        except Exception as e:
            self.logger.error(f"数据质量分析异常: {e}")
            yield self.create_error_result(f"数据质量分析失败: {str(e)}")
    
    async def _analyze_relationships(
        self,
        context: ToolContext,
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """分析表间关系"""
        
        yield self.create_progress_result("🔗 开始关系分析")
        
        try:
            # 获取数据源信息
            data_source_info = await self._ensure_data_source_info(context)
            if not data_source_info:
                yield self.create_error_result("无法获取数据源信息")
                return
            
            tables = data_source_info.get('tables', [])
            table_details = data_source_info.get('table_details', [])
            
            if len(tables) < 2:
                yield self.create_warning_result(
                    "表数量不足，无法进行关系分析",
                    data={"analysis_type": "relationship", "tables_count": len(tables)}
                )
                return
            
            # 生成关系分析提示词
            relationship_prompt = self._build_relationship_prompt(tables, table_details, context)
            
            yield self.create_progress_result("🤖 AI分析表间关系")
            
            # 调用LLM进行关系分析
            relationship_response = await self.ask_llm(
                prompt=relationship_prompt,
                context=context,
                agent_type="data_architect",
                task_type="relationship_analysis"
            )
            
            # 解析关系分析结果
            relationship_result = self._parse_relationship_analysis(relationship_response)
            
            if relationship_result:
                yield self.create_success_result(
                    data={
                        "analysis_type": "relationship",
                        "data_source": data_source_info.get('name', 'unknown'),
                        "tables_analyzed": len(tables),
                        **relationship_result
                    },
                    confidence=relationship_result.get('confidence', 0.7),
                    insights=relationship_result.get('insights', [])
                )
            else:
                yield self.create_error_result("关系分析结果解析失败")
                
        except Exception as e:
            self.logger.error(f"关系分析异常: {e}")
            yield self.create_error_result(f"关系分析失败: {str(e)}")
    
    async def _comprehensive_analysis(
        self,
        context: ToolContext,
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """综合分析"""
        
        yield self.create_progress_result("🚀 开始综合数据分析")
        
        comprehensive_result = {
            "analysis_type": "comprehensive",
            "components": {}
        }
        
        try:
            # 1. 表结构分析
            yield self.create_progress_result("第1步: 表结构分析")
            structure_results = []
            async for result in self._analyze_table_structure(context, **kwargs):
                structure_results.append(result)
                if result.type == ToolResultType.PROGRESS:
                    yield result
            
            if structure_results and structure_results[-1].type == ToolResultType.RESULT:
                comprehensive_result["components"]["structure"] = structure_results[-1].data
            
            # 2. 数据质量分析
            yield self.create_progress_result("第2步: 数据质量分析")
            quality_results = []
            async for result in self._analyze_data_quality(context, **kwargs):
                quality_results.append(result)
                if result.type == ToolResultType.PROGRESS:
                    yield result
            
            if quality_results and quality_results[-1].type == ToolResultType.RESULT:
                comprehensive_result["components"]["quality"] = quality_results[-1].data
            
            # 3. 关系分析
            yield self.create_progress_result("第3步: 表关系分析")
            relationship_results = []
            async for result in self._analyze_relationships(context, **kwargs):
                relationship_results.append(result)
                if result.type == ToolResultType.PROGRESS:
                    yield result
            
            if relationship_results and relationship_results[-1].type == ToolResultType.RESULT:
                comprehensive_result["components"]["relationships"] = relationship_results[-1].data
            
            # 4. 生成综合洞察
            yield self.create_progress_result("第4步: 生成综合洞察")
            comprehensive_insights = self._generate_comprehensive_insights(comprehensive_result)
            comprehensive_result["insights"] = comprehensive_insights
            comprehensive_result["summary"] = self._generate_comprehensive_summary(comprehensive_result)
            
            # 计算综合置信度
            confidences = []
            for component in comprehensive_result["components"].values():
                if isinstance(component, dict) and "confidence" in component:
                    confidences.append(component["confidence"])
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
            
            yield self.create_success_result(
                data=comprehensive_result,
                confidence=avg_confidence,
                insights=comprehensive_insights
            )
            
        except Exception as e:
            self.logger.error(f"综合分析异常: {e}")
            yield self.create_error_result(f"综合分析失败: {str(e)}")
    
    async def _ensure_data_source_info(self, context: ToolContext) -> Optional[Dict[str, Any]]:
        """确保获取到数据源信息"""
        
        if context.data_source_info:
            return context.data_source_info
        
        if context.data_source_id:
            # TODO: 从数据库获取数据源信息
            # 这里应该调用数据源服务获取详细信息
            self.logger.warning("需要实现从数据库获取数据源信息的逻辑")
            return None
        
        return None
    
    async def _analyze_single_table(
        self,
        context: ToolContext,
        table_name: str,
        data_source_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """分析单个表的结构"""
        
        try:
            # 从table_details中查找表信息
            table_details = data_source_info.get('table_details', [])
            table_info = None
            
            for detail in table_details:
                if detail.get('name') == table_name:
                    table_info = detail
                    break
            
            if not table_info:
                # 如果没有详细信息，创建基础信息
                table_info = {"name": table_name, "all_columns": []}
            
            # 分析字段类型和模式
            columns = table_info.get('all_columns', [])
            analyzed_columns = []
            
            for column in columns:
                if isinstance(column, str):
                    # 解析字段名和类型
                    if '(' in column and ')' in column:
                        parts = column.split('(')
                        field_name = parts[0].strip()
                        field_type = column[len(field_name):].strip()
                    else:
                        field_name = column.strip()
                        field_type = "unknown"
                    
                    analyzed_columns.append({
                        "name": field_name,
                        "type": field_type,
                        "category": self._categorize_field(field_name, field_type),
                        "business_meaning": self._infer_business_meaning(field_name)
                    })
            
            return {
                "name": table_name,
                "columns": analyzed_columns,
                "column_count": len(analyzed_columns),
                "estimated_rows": table_info.get('estimated_rows', 0),
                "business_category": self._categorize_table(table_name, analyzed_columns),
                "key_fields": self._identify_key_fields(analyzed_columns)
            }
            
        except Exception as e:
            self.logger.error(f"分析表 {table_name} 异常: {e}")
            return None
    
    def _categorize_field(self, field_name: str, field_type: str) -> str:
        """字段分类"""
        field_name_lower = field_name.lower()
        field_type_lower = field_type.lower()
        
        # 时间字段
        time_keywords = ['time', 'date', 'created', 'updated', 'modified', '_at', '_on']
        if any(keyword in field_name_lower for keyword in time_keywords):
            return "temporal"
        
        # ID字段
        if field_name_lower.endswith('_id') or field_name_lower == 'id':
            return "identifier"
        
        # 数值字段
        if any(keyword in field_type_lower for keyword in ['int', 'decimal', 'float', 'number', 'bigint']):
            return "numeric"
        
        # 文本字段
        if any(keyword in field_type_lower for keyword in ['varchar', 'text', 'char', 'string']):
            return "textual"
        
        return "other"
    
    def _categorize_table(self, table_name: str, columns: List[Dict[str, Any]]) -> str:
        """表分类"""
        table_name_lower = table_name.lower()
        
        # 事实表特征
        if any(prefix in table_name_lower for prefix in ['fact_', 'f_']):
            return "fact_table"
        
        # 维度表特征
        if any(prefix in table_name_lower for prefix in ['dim_', 'd_']):
            return "dimension_table"
        
        # ODS表特征
        if table_name_lower.startswith('ods_'):
            return "ods_table"
        
        # 业务表特征判断
        business_keywords = {
            'user': 'user_data',
            'customer': 'customer_data',
            'order': 'transaction_data',
            'product': 'product_data',
            'complain': 'service_data',
            'sales': 'sales_data'
        }
        
        for keyword, category in business_keywords.items():
            if keyword in table_name_lower:
                return category
        
        return "general_table"
    
    def _infer_business_meaning(self, field_name: str) -> str:
        """推断字段业务含义"""
        field_name_lower = field_name.lower()
        
        business_meanings = {
            'id': '唯一标识符',
            'name': '名称',
            'title': '标题',
            'content': '内容',
            'description': '描述',
            'status': '状态',
            'type': '类型',
            'category': '分类',
            'amount': '金额',
            'quantity': '数量',
            'price': '价格',
            'date': '日期',
            'time': '时间',
            'created': '创建时间',
            'updated': '更新时间',
            'user': '用户',
            'customer': '客户'
        }
        
        for keyword, meaning in business_meanings.items():
            if keyword in field_name_lower:
                return meaning
        
        return '待确定含义'
    
    def _identify_key_fields(self, columns: List[Dict[str, Any]]) -> List[str]:
        """识别关键字段"""
        key_fields = []
        
        for column in columns:
            field_name = column.get('name', '').lower()
            field_category = column.get('category', '')
            
            # ID字段通常是关键字段
            if field_category == 'identifier':
                key_fields.append(column.get('name', ''))
            
            # 时间字段通常是关键字段
            elif field_category == 'temporal':
                key_fields.append(column.get('name', ''))
            
            # 状态、类型字段通常是关键字段
            elif any(keyword in field_name for keyword in ['status', 'type', 'category']):
                key_fields.append(column.get('name', ''))
        
        return key_fields
    
    def _generate_structure_summary(self, table_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成结构分析摘要"""
        total_columns = sum(len(table.get('columns', [])) for table in table_analysis)
        
        # 统计字段类型分布
        field_categories = {}
        for table in table_analysis:
            for column in table.get('columns', []):
                category = column.get('category', 'other')
                field_categories[category] = field_categories.get(category, 0) + 1
        
        # 统计表类型分布
        table_categories = {}
        for table in table_analysis:
            category = table.get('business_category', 'general_table')
            table_categories[category] = table_categories.get(category, 0) + 1
        
        return {
            "total_tables": len(table_analysis),
            "total_columns": total_columns,
            "avg_columns_per_table": total_columns / len(table_analysis) if table_analysis else 0,
            "field_type_distribution": field_categories,
            "table_type_distribution": table_categories
        }
    
    def _generate_structure_recommendations(self, table_analysis: List[Dict[str, Any]]) -> List[str]:
        """生成结构分析建议"""
        recommendations = []
        
        # 检查表数量
        if len(table_analysis) < 3:
            recommendations.append("数据源表数量较少，建议确认是否完整")
        
        # 检查字段数量
        total_columns = sum(len(table.get('columns', [])) for table in table_analysis)
        if total_columns < 10:
            recommendations.append("总字段数量较少，建议检查表结构完整性")
        
        # 检查是否有时间字段
        has_time_field = any(
            any(col.get('category') == 'temporal' for col in table.get('columns', []))
            for table in table_analysis
        )
        if not has_time_field:
            recommendations.append("未发现时间字段，建议确认数据的时间维度")
        
        return recommendations
    
    def _build_data_quality_prompt(self, data_source_info: Dict[str, Any], context: ToolContext) -> str:
        """构建数据质量分析提示词"""
        
        tables = data_source_info.get('tables', [])
        table_details = data_source_info.get('table_details', [])
        
        prompt_parts = [
            "请分析以下数据源的数据质量：",
            "",
            f"数据源类型: {data_source_info.get('type', 'unknown')}",
            f"数据库: {data_source_info.get('database', 'unknown')}",
            f"表数量: {len(tables)}",
            "",
            "表结构信息:"
        ]
        
        for i, table_name in enumerate(tables[:5]):  # 最多显示5个表
            prompt_parts.append(f"{i+1}. {table_name}")
            
            # 查找表详情
            for detail in table_details:
                if detail.get('name') == table_name:
                    columns = detail.get('all_columns', [])[:10]  # 最多显示10个字段
                    prompt_parts.append(f"   字段: {', '.join(columns)}")
                    break
        
        if len(tables) > 5:
            prompt_parts.append(f"... 还有 {len(tables) - 5} 个表")
        
        prompt_parts.extend([
            "",
            "请从以下维度评估数据质量：",
            "1. 表名和字段命名规范性",
            "2. 数据结构合理性",
            "3. 可能的数据完整性问题",
            "4. 字段类型适当性",
            "5. 业务逻辑一致性",
            "",
            "请返回JSON格式结果：",
            """{
    "overall_score": 0.8,
    "quality_dimensions": {
        "naming_convention": {"score": 0.9, "issues": []},
        "data_structure": {"score": 0.8, "issues": []},
        "completeness": {"score": 0.7, "issues": []},
        "consistency": {"score": 0.8, "issues": []}
    },
    "recommendations": ["建议1", "建议2"],
    "confidence": 0.8,
    "insights": ["洞察1", "洞察2"]
}"""
        ])
        
        return "\n".join(prompt_parts)
    
    def _build_relationship_prompt(
        self,
        tables: List[str],
        table_details: List[Dict[str, Any]],
        context: ToolContext
    ) -> str:
        """构建关系分析提示词"""
        
        prompt_parts = [
            "请分析以下表之间的潜在关系：",
            "",
            f"表数量: {len(tables)}",
            ""
        ]
        
        # 显示表和关键字段
        for i, table_name in enumerate(tables):
            prompt_parts.append(f"{i+1}. {table_name}")
            
            # 查找表详情
            for detail in table_details:
                if detail.get('name') == table_name:
                    columns = detail.get('all_columns', [])
                    # 提取可能的关键字段
                    key_columns = [col for col in columns if 'id' in col.lower()][:5]
                    if key_columns:
                        prompt_parts.append(f"   关键字段: {', '.join(key_columns)}")
                    break
        
        prompt_parts.extend([
            "",
            "请分析：",
            "1. 表之间可能的主外键关系",
            "2. 业务关联关系",
            "3. 数据流向和依赖关系",
            "4. 可能的JOIN操作场景",
            "",
            "请返回JSON格式结果：",
            """{
    "relationships": [
        {
            "type": "foreign_key",
            "source_table": "table1",
            "source_field": "user_id", 
            "target_table": "table2",
            "target_field": "id",
            "confidence": 0.9,
            "reasoning": "外键关系说明"
        }
    ],
    "business_relationships": [
        {
            "tables": ["table1", "table2"],
            "relationship_type": "one_to_many",
            "business_meaning": "业务关系说明",
            "confidence": 0.8
        }
    ],
    "join_recommendations": [
        {
            "tables": ["table1", "table2"],
            "join_condition": "table1.id = table2.user_id",
            "use_case": "使用场景说明"
        }
    ],
    "confidence": 0.8,
    "insights": ["关系洞察1", "关系洞察2"]
}"""
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_quality_analysis(self, response: str) -> Optional[Dict[str, Any]]:
        """解析数据质量分析结果"""
        try:
            json_str = self._extract_json_from_response(response)
            if not json_str:
                return None
            
            result = json.loads(json_str)
            
            # 验证必需字段
            required_fields = ['overall_score', 'quality_dimensions']
            for field in required_fields:
                if field not in result:
                    self.logger.error(f"质量分析结果缺少字段: {field}")
                    return None
            
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"质量分析结果JSON解析失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"质量分析结果解析异常: {e}")
            return None
    
    def _parse_relationship_analysis(self, response: str) -> Optional[Dict[str, Any]]:
        """解析关系分析结果"""
        try:
            self.logger.info(f"开始解析关系分析响应，长度: {len(response)}")
            
            json_str = self._extract_json_from_response(response)
            if not json_str:
                self.logger.error("无法从响应中提取JSON字符串")
                self.logger.debug(f"响应内容前500字符: {response[:500]}")
                return self._create_fallback_relationship_result()
            
            self.logger.info(f"提取的JSON长度: {len(json_str)}")
            
            result = json.loads(json_str)
            
            # 验证必需字段
            required_fields = ['relationships']
            for field in required_fields:
                if field not in result:
                    self.logger.error(f"关系分析结果缺少字段: {field}")
                    # 尝试修复缺失字段
                    result = self._fix_missing_relationship_fields(result)
                    break
            
            self.logger.info("关系分析结果解析成功")
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"关系分析结果JSON解析失败: {e}")
            self.logger.debug(f"失败的JSON字符串: {json_str[:200] if json_str else 'None'}")
            
            # 尝试从原始响应中提取部分信息
            return self._extract_partial_relationship_info(response)
            
        except Exception as e:
            self.logger.error(f"关系分析结果解析异常: {e}")
            import traceback
            self.logger.debug(f"异常堆栈: {traceback.format_exc()}")
            return self._create_fallback_relationship_result()
    
    def _create_fallback_relationship_result(self) -> Dict[str, Any]:
        """创建后备关系分析结果"""
        return {
            "relationships": [],
            "business_relationships": [],
            "join_recommendations": [],
            "confidence": 0.3,
            "insights": ["关系分析遇到解析问题，返回基础结果"],
            "parsing_status": "fallback"
        }
    
    def _fix_missing_relationship_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """修复缺失的关系字段"""
        if 'relationships' not in result:
            result['relationships'] = []
        
        if 'business_relationships' not in result:
            result['business_relationships'] = []
        
        if 'join_recommendations' not in result:
            result['join_recommendations'] = []
        
        if 'confidence' not in result:
            result['confidence'] = 0.5
        
        if 'insights' not in result:
            result['insights'] = ["字段修复后的关系分析结果"]
        
        return result
    
    def _extract_partial_relationship_info(self, response: str) -> Optional[Dict[str, Any]]:
        """从原始响应中提取部分关系信息"""
        try:
            import re
            
            # 尝试使用正则表达式提取关系信息
            relationships = []
            insights = []
            
            # 查找可能的表关系描述
            table_patterns = [
                r'(\w+)\s*和\s*(\w+).*关系',
                r'(\w+)\s*→\s*(\w+)',
                r'(\w+)\s*关联\s*(\w+)'
            ]
            
            for pattern in table_patterns:
                matches = re.findall(pattern, response, re.IGNORECASE)
                for match in matches:
                    relationships.append({
                        "type": "inferred",
                        "source_table": match[0],
                        "target_table": match[1],
                        "confidence": 0.4,
                        "reasoning": "从文本中推断的关系"
                    })
            
            # 提取洞察信息
            insight_patterns = [
                r'建议.*?[。\n]',
                r'发现.*?[。\n]',
                r'可以.*?[。\n]'
            ]
            
            for pattern in insight_patterns:
                matches = re.findall(pattern, response, re.DOTALL)
                insights.extend(matches[:3])  # 最多3个洞察
            
            if not insights:
                insights = ["从文本分析中提取的基础关系信息"]
            
            return {
                "relationships": relationships,
                "business_relationships": [],
                "join_recommendations": [],
                "confidence": 0.4,
                "insights": insights,
                "parsing_status": "partial_extraction"
            }
            
        except Exception as e:
            self.logger.error(f"部分信息提取异常: {e}")
            return self._create_fallback_relationship_result()
    
    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """从响应中提取JSON字符串"""
        try:
            response = response.strip()
            
            # 移除markdown标记
            if response.startswith('```'):
                lines = response.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                response = '\n'.join(lines)
            
            # 尝试多种JSON提取策略
            
            # 策略1: 查找完整的JSON对象（平衡大括号）
            json_str = self._extract_balanced_json(response)
            if json_str and self._is_valid_json(json_str):
                return json_str
            
            # 策略2: 查找第一个JSON对象到最后一个大括号
            start = response.find('{')
            if start >= 0:
                # 从第一个{开始，找到匹配的}
                brace_count = 0
                end_pos = start
                
                for i in range(start, len(response)):
                    char = response[i]
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i
                            break
                
                if brace_count == 0:
                    json_str = response[start:end_pos+1]
                    if self._is_valid_json(json_str):
                        return json_str
            
            # 策略3: 尝试修复常见的JSON格式问题
            cleaned_response = self._clean_json_response(response)
            if cleaned_response and self._is_valid_json(cleaned_response):
                return cleaned_response
            
            return None
            
        except Exception as e:
            self.logger.error(f"JSON提取异常: {e}")
            return None
    
    def _extract_balanced_json(self, text: str) -> Optional[str]:
        """提取平衡的JSON对象"""
        try:
            start = text.find('{')
            if start == -1:
                return None
            
            brace_count = 0
            in_string = False
            escaped = False
            
            for i in range(start, len(text)):
                char = text[i]
                
                if escaped:
                    escaped = False
                    continue
                
                if char == '\\':
                    escaped = True
                    continue
                
                if char == '"' and not escaped:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        
                        if brace_count == 0:
                            return text[start:i+1]
            
            return None
            
        except Exception as e:
            self.logger.error(f"平衡JSON提取异常: {e}")
            return None
    
    def _clean_json_response(self, response: str) -> Optional[str]:
        """清理JSON响应中的常见问题"""
        try:
            import re
            
            # 移除注释
            response = re.sub(r'//.*?$', '', response, flags=re.MULTILINE)
            response = re.sub(r'/\*.*?\*/', '', response, flags=re.DOTALL)
            
            # 查找JSON对象
            start = response.find('{')
            if start == -1:
                return None
            
            # 移除trailing comma
            response = re.sub(r',\s*}', '}', response)
            response = re.sub(r',\s*]', ']', response)
            
            # 提取JSON部分
            json_str = self._extract_balanced_json(response[start:])
            
            return json_str
            
        except Exception as e:
            self.logger.error(f"JSON清理异常: {e}")
            return None
    
    def _is_valid_json(self, json_str: str) -> bool:
        """验证JSON字符串是否有效"""
        try:
            json.loads(json_str)
            return True
        except (json.JSONDecodeError, TypeError, ValueError):
            return False
    
    def _generate_comprehensive_insights(self, comprehensive_result: Dict[str, Any]) -> List[str]:
        """生成综合洞察"""
        insights = []
        components = comprehensive_result.get("components", {})
        
        # 结构分析洞察
        if "structure" in components:
            structure = components["structure"]
            table_count = structure.get("total_tables", 0)
            insights.append(f"数据源包含 {table_count} 个表")
            
            if "summary" in structure:
                summary = structure["summary"]
                avg_columns = summary.get("avg_columns_per_table", 0)
                insights.append(f"平均每表 {avg_columns:.1f} 个字段")
        
        # 质量分析洞察
        if "quality" in components:
            quality = components["quality"]
            overall_score = quality.get("overall_score", 0)
            insights.append(f"数据质量评分: {overall_score:.1f}")
        
        # 关系分析洞察
        if "relationships" in components:
            relationships = components["relationships"]
            rel_count = len(relationships.get("relationships", []))
            if rel_count > 0:
                insights.append(f"发现 {rel_count} 个潜在表关系")
        
        insights.append("综合数据分析完成")
        return insights
    
    def _generate_comprehensive_summary(self, comprehensive_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合摘要"""
        components = comprehensive_result.get("components", {})
        
        summary = {
            "analysis_completed": len(components),
            "total_components": 3  # 结构、质量、关系
        }
        
        if "structure" in components:
            structure = components["structure"]
            summary["tables_analyzed"] = structure.get("total_tables", 0)
            summary["total_columns"] = structure.get("total_columns", 0)
        
        if "quality" in components:
            quality = components["quality"]
            summary["quality_score"] = quality.get("overall_score", 0)
        
        if "relationships" in components:
            relationships = components["relationships"]
            summary["relationships_found"] = len(relationships.get("relationships", []))
        
        return summary