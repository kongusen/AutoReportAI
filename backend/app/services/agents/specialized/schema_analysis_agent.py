"""
表结构分析Agent
专门用于分析数据库表结构的AI Agent，提供智能的表关系分析、业务语义识别和数据质量评估
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from ..base import BaseAnalysisAgent


class SchemaAnalysisAgent(BaseAnalysisAgent):
    """表结构分析Agent - 专注于数据库结构分析"""
    
    def __init__(self, db_session: Session = None, suppress_ai_warning: bool = False):
        super().__init__(db_session, suppress_ai_warning=suppress_ai_warning)
    
    async def analyze_schema_relationships(
        self, 
        schema_data: Dict[str, Any], 
        analysis_prompt: str
    ) -> Dict[str, Any]:
        """
        分析表结构关系
        
        Args:
            schema_data: 表结构数据
            analysis_prompt: 分析提示
            
        Returns:
            分析结果
        """
        # 验证数据
        if not self.validate_analysis_data(schema_data, ["tables", "total_tables"]):
            return self._get_error_result("无效的表结构数据", "relationship")
        
        # 构建上下文
        context = self._build_relationship_analysis_context(schema_data)
        
        # 使用基础分析功能
        result = await self.analyze_with_ai(
            context=context,
            prompt=analysis_prompt,
            task_type="schema_relationship_analysis",
            analysis_type="relationship"
        )
        
        return result
    
    async def analyze_business_semantics(
        self, 
        schema_data: Dict[str, Any], 
        analysis_prompt: str
    ) -> Dict[str, Any]:
        """
        分析业务语义
        
        Args:
            schema_data: 表结构数据
            analysis_prompt: 分析提示
            
        Returns:
            分析结果
        """
        # 验证数据
        if not self.validate_analysis_data(schema_data, ["tables", "total_tables"]):
            return self._get_error_result("无效的表结构数据", "semantic")
        
        # 构建上下文
        context = self._build_semantic_analysis_context(schema_data)
        
        # 使用基础分析功能
        result = await self.analyze_with_ai(
            context=context,
            prompt=analysis_prompt,
            task_type="business_semantic_analysis",
            analysis_type="semantic"
        )
        
        return result
    
    async def analyze_data_quality(
        self, 
        schema_data: Dict[str, Any], 
        analysis_prompt: str
    ) -> Dict[str, Any]:
        """
        分析数据质量
        
        Args:
            schema_data: 表结构数据
            analysis_prompt: 分析提示
            
        Returns:
            分析结果
        """
        # 验证数据
        if not self.validate_analysis_data(schema_data, ["tables", "total_tables"]):
            return self._get_error_result("无效的表结构数据", "quality")
        
        # 构建上下文
        context = self._build_quality_analysis_context(schema_data)
        
        # 使用基础分析功能
        result = await self.analyze_with_ai(
            context=context,
            prompt=analysis_prompt,
            task_type="data_quality_analysis",
            analysis_type="quality"
        )
        
        return result
    
    def _build_relationship_analysis_context(self, schema_data: Dict[str, Any]) -> str:
        """构建表关系分析上下文"""
        
        context = f"""
数据库表结构关系分析任务

数据库概览：
- 总表数: {schema_data['total_tables']}
- 分析目标: 识别表之间的外键关系、业务实体关系和数据流向关系

表结构信息：
"""
        
        for table in schema_data["tables"]:
            context += f"""
表名: {table['table_name']}
业务分类: {table.get('business_category', '未分类')}
预估行数: {table.get('estimated_row_count', '未知')}
列数: {len(table['columns'])}
主键列: {[col['column_name'] for col in table['columns'] if col['is_primary_key']]}
"""
        
        context += """
分析要求：
1. 基于命名约定识别外键关系
2. 基于业务逻辑识别实体关系
3. 评估关系置信度
4. 提供数据模型优化建议
"""
        
        return context
    
    def _build_semantic_analysis_context(self, schema_data: Dict[str, Any]) -> str:
        """构建业务语义分析上下文"""
        
        context = f"""
数据库业务语义分析任务

数据库概览：
- 总表数: {schema_data['total_tables']}
- 分析目标: 识别业务分类、字段语义和命名规范

表结构信息：
"""
        
        for table in schema_data["tables"]:
            context += f"""
表名: {table['table_name']}
列信息:
"""
            
            for column in table["columns"]:
                context += f"  - {column['column_name']} ({column['data_type']})"
                if column['business_name']:
                    context += f" [业务名: {column['business_name']}]"
                if column['semantic_category']:
                    context += f" [语义: {column['semantic_category']}]"
                context += "\n"
        
        context += """
分析要求：
1. 识别每个表的业务分类
2. 识别每个字段的业务语义
3. 分析命名规范和约定
4. 提供业务域划分建议
"""
        
        return context
    
    def _build_quality_analysis_context(self, schema_data: Dict[str, Any]) -> str:
        """构建数据质量分析上下文"""
        
        context = f"""
数据库数据质量分析任务

数据库概览：
- 总表数: {schema_data['total_tables']}
- 分析目标: 评估数据质量并提供改进建议

表结构信息：
"""
        
        for table in schema_data["tables"]:
            context += f"""
表名: {table['table_name']}
预估行数: {table.get('estimated_row_count', '未知')}
列数: {len(table['columns'])}
主键列: {[col['column_name'] for col in table['columns'] if col['is_primary_key']]}
非空列: {[col['column_name'] for col in table['columns'] if not col['is_nullable']]}
"""
        
        context += """
分析要求：
1. 评估每个表的数据质量评分
2. 识别数据质量问题
3. 提供改进建议
4. 推荐最佳实践
"""
        
        return context
    
    async def get_schema_analysis_summary(self, schema_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取表结构分析摘要
        
        Args:
            schema_data: 表结构数据
            
        Returns:
            分析摘要
        """
        summary_prompt = f"""
请对以下数据库表结构进行简要分析：

数据库包含 {schema_data['total_tables']} 个表：

"""
        
        for table in schema_data["tables"][:5]:  # 只显示前5个表
            summary_prompt += f"- {table['table_name']} ({len(table['columns'])} 列)\n"
        
        if len(schema_data["tables"]) > 5:
            summary_prompt += f"... 还有 {len(schema_data['tables']) - 5} 个表\n"
        
        summary_prompt += """
请提供：
1. 数据库整体特征
2. 主要业务域
3. 数据复杂度评估
4. 关键发现和建议
"""
        
        return await self.get_analysis_summary(schema_data, summary_prompt)
    
    async def comprehensive_schema_analysis(self, schema_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        综合表结构分析
        
        Args:
            schema_data: 表结构数据
            
        Returns:
            综合分析结果
        """
        # 验证数据
        if not self.validate_analysis_data(schema_data, ["tables", "total_tables"]):
            return {"error": "无效的表结构数据", "success": False}
        
        results = {}
        
        # 1. 关系分析
        relationship_prompt = self._build_relationship_analysis_context(schema_data) + "\n请分析表关系。"
        results["relationships"] = await self.analyze_schema_relationships(schema_data, relationship_prompt)
        
        # 2. 语义分析
        semantic_prompt = self._build_semantic_analysis_context(schema_data) + "\n请分析业务语义。"
        results["semantics"] = await self.analyze_business_semantics(schema_data, semantic_prompt)
        
        # 3. 质量分析
        quality_prompt = self._build_quality_analysis_context(schema_data) + "\n请分析数据质量。"
        results["quality"] = await self.analyze_data_quality(schema_data, quality_prompt)
        
        # 4. 摘要
        results["summary"] = await self.get_schema_analysis_summary(schema_data)
        
        return {
            "success": True,
            "analysis_results": results,
            "total_tables": schema_data['total_tables'],
            "total_columns": sum(len(table['columns']) for table in schema_data['tables'])
        }
