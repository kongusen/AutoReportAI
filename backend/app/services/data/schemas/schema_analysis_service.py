"""
表结构分析服务
使用AI Agent进行智能的表结构分析，包括关系分析、业务语义识别和数据质量评估
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.table_schema import TableSchema, ColumnSchema, TableRelationship
# 直接使用IAOP核心平台
from app.services.iaop.integration.ai_service_adapter import IAOPAIService as EnhancedAIService
# 直接使用IAOP专业化代理
from app.services.iaop.agents.specialized.sql_generation_agent import SQLGenerationAgent as PlaceholderSQLAnalyzer
from app.services.iaop.agents.specialized.placeholder_parser_agent import PlaceholderParserAgent as PlaceholderSQLAgent
from .utils.relationship_analyzer import RelationshipAnalyzer


class SchemaAnalysisService:
    """表结构分析服务 - 基于AI Agent"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
        self.relationship_analyzer = RelationshipAnalyzer()
        self.ai_service = EnhancedAIService(db_session)
        self.analysis_agent = PlaceholderSQLAgent(db_session=db_session)
    
    async def analyze_table_relationships(self, data_source_id: str) -> Dict[str, Any]:
        """
        使用AI Agent分析表之间的关系
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            分析结果
        """
        try:
            # 获取所有表结构
            table_schemas = self.db_session.query(TableSchema).filter(
                and_(
                    TableSchema.data_source_id == data_source_id,
                    TableSchema.is_active == True
                )
            ).all()
            
            if not table_schemas:
                return {"success": False, "error": "未找到表结构信息"}
            
            # 准备表结构数据供Agent分析
            schema_data = await self._prepare_schema_data_for_agent(table_schemas)
            
            # 使用AI Agent分析表关系
            agent_analysis = await self._analyze_relationships_with_agent(schema_data)
            
            # 结合传统规则分析和AI分析结果
            relationships = await self._merge_relationship_analysis(
                table_schemas, data_source_id, agent_analysis
            )
            
            return {
                "success": True,
                "message": f"成功分析 {len(relationships)} 个表关系",
                "relationships_count": len(relationships),
                "relationships": relationships,
                "agent_insights": agent_analysis.get("insights", [])
            }
            
        except Exception as e:
            self.logger.error(f"AI Agent分析表关系失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _prepare_schema_data_for_agent(self, table_schemas: List[TableSchema]) -> Dict[str, Any]:
        """准备表结构数据供AI Agent分析"""
        
        schema_data = {
            "tables": [],
            "total_tables": len(table_schemas),
            "analysis_context": "表关系分析"
        }
        
        for table_schema in table_schemas:
            # 获取表的列信息
            columns = self.db_session.query(ColumnSchema).filter(
                ColumnSchema.table_schema_id == table_schema.id
            ).all()
            
            table_info = {
                "table_name": table_schema.table_name,
                "business_category": table_schema.business_category,
                "estimated_row_count": table_schema.estimated_row_count,
                "columns": []
            }
            
            for column in columns:
                column_info = {
                    "column_name": column.column_name,
                    "data_type": column.normalized_type.value,
                    "is_primary_key": column.is_primary_key,
                    "is_nullable": column.is_nullable,
                    "business_name": column.business_name,
                    "semantic_category": column.semantic_category
                }
                table_info["columns"].append(column_info)
            
            schema_data["tables"].append(table_info)
        
        return schema_data
    
    async def _analyze_relationships_with_agent(self, schema_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用AI Agent分析表关系"""
        
        # 构建分析提示
        analysis_prompt = self._build_relationship_analysis_prompt(schema_data)
        
        try:
            # 使用AI Agent进行分析
            agent_response = await self.analysis_agent.analyze_schema_relationships(
                schema_data, analysis_prompt
            )
            
            return {
                "relationships": agent_response.get("relationships", []),
                "insights": agent_response.get("insights", []),
                "confidence_scores": agent_response.get("confidence_scores", {}),
                "recommendations": agent_response.get("recommendations", [])
            }
            
        except Exception as e:
            self.logger.error(f"AI Agent分析失败: {e}")
            return {
                "relationships": [],
                "insights": [f"AI分析失败: {str(e)}"],
                "confidence_scores": {},
                "recommendations": ["建议检查AI服务配置"]
            }
    
    def _build_relationship_analysis_prompt(self, schema_data: Dict[str, Any]) -> str:
        """构建表关系分析提示"""
        
        prompt = f"""
请分析以下数据库表结构，识别表之间的潜在关系：

数据库包含 {schema_data['total_tables']} 个表：

"""
        
        for table in schema_data["tables"]:
            prompt += f"""
表名: {table['table_name']}
业务分类: {table.get('business_category', '未分类')}
预估行数: {table.get('estimated_row_count', '未知')}
列信息:
"""
            
            for column in table["columns"]:
                prompt += f"  - {column['column_name']} ({column['data_type']})"
                if column['is_primary_key']:
                    prompt += " [主键]"
                if column['business_name']:
                    prompt += f" [业务名: {column['business_name']}]"
                if column['semantic_category']:
                    prompt += f" [语义: {column['semantic_category']}]"
                prompt += "\n"
        
        prompt += """
请分析并返回以下信息：
1. 表之间的外键关系（基于命名约定和业务逻辑）
2. 业务实体关系（如用户-订单、产品-库存等）
3. 数据流向关系（如日志表、配置表等）
4. 关系置信度和建议
5. 潜在的数据模型优化建议

请以JSON格式返回分析结果。
"""
        
        return prompt
    
    async def _merge_relationship_analysis(
        self, 
        table_schemas: List[TableSchema], 
        data_source_id: str, 
        agent_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """合并传统规则分析和AI分析结果"""
        
        relationships = []
        
        # 获取AI分析的关系
        ai_relationships = agent_analysis.get("relationships", [])
        
        # 结合传统规则分析
        for i, source_table in enumerate(table_schemas):
            for j, target_table in enumerate(table_schemas):
                if i != j:
                    # 传统规则分析
                    rule_relationships = self._find_relationships(source_table, target_table)
                    
                    # AI分析的关系
                    ai_rel = self._find_ai_relationship(
                        source_table.table_name, 
                        target_table.table_name, 
                        ai_relationships
                    )
                    
                    # 合并分析结果
                    merged_rel = self._merge_relationship_results(
                        rule_relationships, ai_rel, source_table, target_table
                    )
                    
                    for rel in merged_rel:
                        # 检查关系是否已存在
                        existing_rel = self.db_session.query(TableRelationship).filter(
                            and_(
                                TableRelationship.data_source_id == data_source_id,
                                TableRelationship.source_table_id == source_table.id,
                                TableRelationship.target_table_id == target_table.id,
                                TableRelationship.source_column == rel["source_column"],
                                TableRelationship.target_column == rel["target_column"]
                            )
                        ).first()
                        
                        if not existing_rel:
                            # 创建新关系
                            table_relationship = TableRelationship(
                                data_source_id=data_source_id,
                                source_table_id=source_table.id,
                                target_table_id=target_table.id,
                                relationship_type=rel["type"],
                                source_column=rel["source_column"],
                                target_column=rel["target_column"],
                                confidence_score=rel["confidence"],
                                business_description=rel.get("description", "")
                            )
                            self.db_session.add(table_relationship)
                            relationships.append(rel)
        
        self.db_session.commit()
        return relationships
    
    def _find_ai_relationship(
        self, 
        source_table_name: str, 
        target_table_name: str, 
        ai_relationships: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """查找AI分析的关系"""
        
        for rel in ai_relationships:
            if (rel.get("source_table") == source_table_name and 
                rel.get("target_table") == target_table_name):
                return rel
        return None
    
    def _merge_relationship_results(
        self, 
        rule_relationships: List[Dict[str, Any]], 
        ai_relationship: Optional[Dict[str, Any]], 
        source_table: TableSchema, 
        target_table: TableSchema
    ) -> List[Dict[str, Any]]:
        """合并规则分析和AI分析结果"""
        
        merged_relationships = []
        
        # 添加规则分析结果
        for rel in rule_relationships:
            merged_relationships.append(rel)
        
        # 添加AI分析结果（如果AI发现了规则分析没有发现的关系）
        if ai_relationship:
            ai_rel = {
                "source_column": ai_relationship.get("source_column", ""),
                "target_column": ai_relationship.get("target_column", ""),
                "type": ai_relationship.get("relationship_type", "unknown"),
                "confidence": ai_relationship.get("confidence", 0.6),
                "description": ai_relationship.get("description", "")
            }
            
            # 检查是否与规则分析结果重复
            is_duplicate = any(
                rel["source_column"] == ai_rel["source_column"] and 
                rel["target_column"] == ai_rel["target_column"]
                for rel in rule_relationships
            )
            
            if not is_duplicate:
                merged_relationships.append(ai_rel)
        
        return merged_relationships
    
    async def analyze_business_semantics(self, data_source_id: str) -> Dict[str, Any]:
        """
        使用AI Agent分析业务语义
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            分析结果
        """
        try:
            # 获取所有表结构
            table_schemas = self.db_session.query(TableSchema).filter(
                and_(
                    TableSchema.data_source_id == data_source_id,
                    TableSchema.is_active == True
                )
            ).all()
            
            if not table_schemas:
                return {"success": False, "error": "未找到表结构信息"}
            
            # 准备数据供Agent分析
            schema_data = await self._prepare_schema_data_for_agent(table_schemas)
            
            # 使用AI Agent分析业务语义
            semantic_analysis = await self._analyze_semantics_with_agent(schema_data)
            
            # 更新表结构的业务信息
            await self._update_business_semantics(table_schemas, semantic_analysis)
            
            return {
                "success": True,
                "message": "AI Agent业务语义分析完成",
                "analysis": semantic_analysis
            }
            
        except Exception as e:
            self.logger.error(f"AI Agent分析业务语义失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _analyze_semantics_with_agent(self, schema_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用AI Agent分析业务语义"""
        
        # 构建语义分析提示
        semantic_prompt = self._build_semantic_analysis_prompt(schema_data)
        
        try:
            # 使用AI Agent进行语义分析
            agent_response = await self.analysis_agent.analyze_business_semantics(
                schema_data, semantic_prompt
            )
            
            return {
                "business_categories": agent_response.get("business_categories", {}),
                "semantic_patterns": agent_response.get("semantic_patterns", {}),
                "data_entities": agent_response.get("data_entities", []),
                "domain_insights": agent_response.get("domain_insights", []),
                "naming_conventions": agent_response.get("naming_conventions", {})
            }
            
        except Exception as e:
            self.logger.error(f"AI Agent语义分析失败: {e}")
            return {
                "business_categories": {},
                "semantic_patterns": {},
                "data_entities": [],
                "domain_insights": [f"AI分析失败: {str(e)}"],
                "naming_conventions": {}
            }
    
    def _build_semantic_analysis_prompt(self, schema_data: Dict[str, Any]) -> str:
        """构建业务语义分析提示"""
        
        prompt = f"""
请分析以下数据库表结构的业务语义：

数据库包含 {schema_data['total_tables']} 个表，请从业务角度进行分析：

"""
        
        for table in schema_data["tables"]:
            prompt += f"""
表名: {table['table_name']}
列信息:
"""
            
            for column in table["columns"]:
                prompt += f"  - {column['column_name']} ({column['data_type']})"
                if column['business_name']:
                    prompt += f" [业务名: {column['business_name']}]"
                if column['semantic_category']:
                    prompt += f" [语义: {column['semantic_category']}]"
                prompt += "\n"
        
        prompt += """
请分析并返回以下信息：
1. 每个表的业务分类（如：用户管理、订单管理、产品管理等）
2. 每个列的业务语义（如：ID标识、名称、时间、状态等）
3. 业务实体关系（如：用户、订单、产品等核心实体）
4. 命名规范和约定
5. 业务域划分建议
6. 数据治理建议

请以JSON格式返回分析结果。
"""
        
        return prompt
    
    async def _update_business_semantics(
        self, 
        table_schemas: List[TableSchema], 
        semantic_analysis: Dict[str, Any]
    ):
        """更新表结构的业务语义信息"""
        
        business_categories = semantic_analysis.get("business_categories", {})
        semantic_patterns = semantic_analysis.get("semantic_patterns", {})
        
        for table_schema in table_schemas:
            # 更新表业务分类
            if table_schema.table_name in business_categories:
                table_schema.business_category = business_categories[table_schema.table_name]
            
            # 更新列业务语义
            columns = self.db_session.query(ColumnSchema).filter(
                ColumnSchema.table_schema_id == table_schema.id
            ).all()
            
            for column in columns:
                # 查找列的业务语义
                column_semantic = self._find_column_semantic(
                    table_schema.table_name, 
                    column.column_name, 
                    semantic_patterns
                )
                
                if column_semantic:
                    column.business_name = column_semantic.get("business_name", column.business_name)
                    column.semantic_category = column_semantic.get("semantic_category", column.semantic_category)
                    column.business_description = column_semantic.get("description", column.business_description)
        
        self.db_session.commit()
    
    def _find_column_semantic(
        self, 
        table_name: str, 
        column_name: str, 
        semantic_patterns: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """查找列的业务语义"""
        
        table_patterns = semantic_patterns.get(table_name, {})
        return table_patterns.get(column_name)
    
    async def analyze_data_quality(self, data_source_id: str) -> Dict[str, Any]:
        """
        使用AI Agent分析数据质量
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            分析结果
        """
        try:
            # 获取所有表结构
            table_schemas = self.db_session.query(TableSchema).filter(
                and_(
                    TableSchema.data_source_id == data_source_id,
                    TableSchema.is_active == True
                )
            ).all()
            
            if not table_schemas:
                return {"success": False, "error": "未找到表结构信息"}
            
            # 准备数据供Agent分析
            schema_data = await self._prepare_schema_data_for_agent(table_schemas)
            
            # 使用AI Agent分析数据质量
            quality_analysis = await self._analyze_data_quality_with_agent(schema_data)
            
            # 结合传统规则分析
            traditional_quality = await self._analyze_data_quality_traditional(table_schemas)
            
            # 合并分析结果
            merged_quality = self._merge_quality_analysis(quality_analysis, traditional_quality)
            
            return {
                "success": True,
                "message": "AI Agent数据质量分析完成",
                "analysis": merged_quality
            }
            
        except Exception as e:
            self.logger.error(f"AI Agent分析数据质量失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _analyze_data_quality_with_agent(self, schema_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用AI Agent分析数据质量"""
        
        # 构建数据质量分析提示
        quality_prompt = self._build_quality_analysis_prompt(schema_data)
        
        try:
            # 使用AI Agent进行质量分析
            agent_response = await self.analysis_agent.analyze_data_quality(
                schema_data, quality_prompt
            )
            
            return {
                "overall_score": agent_response.get("overall_score", 0.0),
                "table_quality": agent_response.get("table_quality", []),
                "recommendations": agent_response.get("recommendations", []),
                "quality_insights": agent_response.get("quality_insights", []),
                "best_practices": agent_response.get("best_practices", [])
            }
            
        except Exception as e:
            self.logger.error(f"AI Agent质量分析失败: {e}")
            return {
                "overall_score": 0.0,
                "table_quality": [],
                "recommendations": [f"AI分析失败: {str(e)}"],
                "quality_insights": [],
                "best_practices": []
            }
    
    def _build_quality_analysis_prompt(self, schema_data: Dict[str, Any]) -> str:
        """构建数据质量分析提示"""
        
        prompt = f"""
请分析以下数据库表结构的数据质量：

数据库包含 {schema_data['total_tables']} 个表，请从数据质量角度进行分析：

"""
        
        for table in schema_data["tables"]:
            prompt += f"""
表名: {table['table_name']}
预估行数: {table.get('estimated_row_count', '未知')}
列信息:
"""
            
            for column in table["columns"]:
                prompt += f"  - {column['column_name']} ({column['data_type']})"
                if column['is_primary_key']:
                    prompt += " [主键]"
                if not column['is_nullable']:
                    prompt += " [非空]"
                prompt += "\n"
        
        prompt += """
请分析并返回以下信息：
1. 每个表的数据质量评分（0-100分）
2. 数据质量问题（如：缺少主键、命名不规范、数据类型不合理等）
3. 数据质量改进建议
4. 最佳实践建议
5. 数据治理建议

请以JSON格式返回分析结果。
"""
        
        return prompt
    
    async def _analyze_data_quality_traditional(self, table_schemas: List[TableSchema]) -> Dict[str, Any]:
        """传统规则分析数据质量"""
        
        quality_result = {
            "overall_score": 0.0,
            "table_quality": [],
            "recommendations": []
        }
        
        total_score = 0.0
        table_count = len(table_schemas)
        
        for table_schema in table_schemas:
            table_quality = self._analyze_table_quality(table_schema)
            quality_result["table_quality"].append(table_quality)
            total_score += table_quality["score"]
        
        # 计算总体质量分数
        if table_count > 0:
            quality_result["overall_score"] = total_score / table_count
        
        # 生成建议
        quality_result["recommendations"] = self._generate_quality_recommendations(
            quality_result["table_quality"]
        )
        
        return quality_result
    
    def _merge_quality_analysis(
        self, 
        ai_quality: Dict[str, Any], 
        traditional_quality: Dict[str, Any]
    ) -> Dict[str, Any]:
        """合并AI分析和传统分析结果"""
        
        merged_quality = {
            "overall_score": (ai_quality.get("overall_score", 0) + traditional_quality.get("overall_score", 0)) / 2,
            "table_quality": [],
            "recommendations": [],
            "quality_insights": ai_quality.get("quality_insights", []),
            "best_practices": ai_quality.get("best_practices", [])
        }
        
        # 合并表质量分析
        ai_table_quality = {tq.get("table_name"): tq for tq in ai_quality.get("table_quality", [])}
        traditional_table_quality = {tq.get("table_name"): tq for tq in traditional_quality.get("table_quality", [])}
        
        for table_name in set(ai_table_quality.keys()) | set(traditional_table_quality.keys()):
            ai_tq = ai_table_quality.get(table_name, {})
            traditional_tq = traditional_table_quality.get(table_name, {})
            
            merged_tq = {
                "table_name": table_name,
                "score": (ai_tq.get("score", 0) + traditional_tq.get("score", 0)) / 2,
                "factors": traditional_tq.get("factors", []) + ai_tq.get("factors", []),
                "ai_insights": ai_tq.get("insights", [])
            }
            merged_quality["table_quality"].append(merged_tq)
        
        # 合并建议
        merged_quality["recommendations"] = (
            traditional_quality.get("recommendations", []) + 
            ai_quality.get("recommendations", [])
        )
        
        return merged_quality
    
    # 保留原有的传统分析方法作为备用
    def _find_relationships(
        self, 
        source_table: TableSchema, 
        target_table: TableSchema
    ) -> List[Dict[str, Any]]:
        """查找两个表之间的潜在关系（传统规则方法）"""
        
        relationships = []
        
        # 获取表的列信息
        source_columns = self.db_session.query(ColumnSchema).filter(
            ColumnSchema.table_schema_id == source_table.id
        ).all()
        
        target_columns = self.db_session.query(ColumnSchema).filter(
            ColumnSchema.table_schema_id == target_table.id
        ).all()
        
        # 查找外键关系（基于命名约定）
        for source_col in source_columns:
            for target_col in target_columns:
                # 检查是否是外键关系
                if self._is_foreign_key_relationship(source_col, target_col, source_table, target_table):
                    relationships.append({
                        "source_column": source_col.column_name,
                        "target_column": target_col.column_name,
                        "type": "one_to_many",
                        "confidence": 0.8,
                        "description": f"{source_table.table_name}.{source_col.column_name} -> {target_table.table_name}.{target_col.column_name}"
                    })
        
        return relationships
    
    def _is_foreign_key_relationship(
        self, 
        source_col: ColumnSchema, 
        target_col: ColumnSchema,
        source_table: TableSchema,
        target_table: TableSchema
    ) -> bool:
        """判断两个列是否构成外键关系（传统规则方法）"""
        
        # 简单的命名约定检查
        source_name = source_col.column_name.lower()
        target_name = target_col.column_name.lower()
        
        # 检查是否是ID字段
        if "id" in source_name and "id" in target_name:
            # 检查表名是否在字段名中
            source_table_name = source_table.table_name.lower()
            target_table_name = target_table.table_name.lower()
            
            if (source_table_name in source_name and 
                target_table_name in target_name and
                source_col.normalized_type == target_col.normalized_type):
                return True
        
        # 检查常见的外键命名模式
        fk_patterns = [
            (f"{target_table.table_name.lower()}_id", "id"),
            (f"{target_table.table_name.lower()}_key", "key"),
            (f"{target_table.table_name.lower()}_pk", "pk")
        ]
        
        for fk_pattern, pk_pattern in fk_patterns:
            if (source_name == fk_pattern and target_name == pk_pattern and
                source_col.normalized_type == target_col.normalized_type):
                return True
        
        return False
    
    def _analyze_table_quality(self, table_schema: TableSchema) -> Dict[str, Any]:
        """分析单个表的数据质量（传统规则方法）"""
        
        columns = self.db_session.query(ColumnSchema).filter(
            ColumnSchema.table_schema_id == table_schema.id
        ).all()
        
        # 计算质量分数
        score = 0.0
        factors = []
        
        # 主键检查
        has_primary_key = any(col.is_primary_key for col in columns)
        if has_primary_key:
            score += 20
            factors.append("有主键")
        else:
            factors.append("缺少主键")
        
        # 命名规范检查
        naming_score = self._check_naming_convention(table_schema, columns)
        score += naming_score
        factors.append(f"命名规范: {naming_score/10:.1f}/10")
        
        # 数据类型合理性检查
        type_score = self._check_data_type_reasonableness(columns)
        score += type_score
        factors.append(f"数据类型: {type_score/10:.1f}/10")
        
        return {
            "table_name": table_schema.table_name,
            "score": score,
            "factors": factors,
            "column_count": len(columns)
        }
    
    def _check_naming_convention(self, table_schema: TableSchema, columns: List[ColumnSchema]) -> float:
        """检查命名规范（传统规则方法）"""
        
        score = 0.0
        
        # 检查表名
        table_name = table_schema.table_name
        if table_name and len(table_name) > 0:
            score += 2.0
        
        # 检查列名
        for column in columns:
            col_name = column.column_name
            if col_name and len(col_name) > 0:
                score += 1.0
        
        return min(score, 10.0)
    
    def _check_data_type_reasonableness(self, columns: List[ColumnSchema]) -> float:
        """检查数据类型合理性（传统规则方法）"""
        
        score = 0.0
        
        for column in columns:
            # 检查是否有合理的数据类型
            if column.normalized_type.value != "unknown":
                score += 1.0
        
        return min(score, 10.0)
    
    def _generate_quality_recommendations(self, table_quality: List[Dict[str, Any]]) -> List[str]:
        """生成质量改进建议（传统规则方法）"""
        
        recommendations = []
        
        # 分析低分表
        low_score_tables = [tq for tq in table_quality if tq["score"] < 50]
        if low_score_tables:
            recommendations.append(f"发现 {len(low_score_tables)} 个低质量表，建议优化表结构设计")
        
        # 分析缺少主键的表
        no_pk_tables = [tq for tq in table_quality if "缺少主键" in tq["factors"]]
        if no_pk_tables:
            recommendations.append(f"发现 {len(no_pk_tables)} 个表缺少主键，建议添加主键约束")
        
        return recommendations
