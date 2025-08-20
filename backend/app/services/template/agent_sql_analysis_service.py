"""
Agent SQL Analysis Service

使用现有Agent系统分析占位符，生成对应的数据库查询SQL并持久化存储
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.template_placeholder import TemplatePlaceholder
from app.models.data_source import DataSource
from app.services.agents.multi_database_agent import MultiDatabaseAgent
from app.services.connectors.connector_factory import create_connector

logger = logging.getLogger(__name__)


class AgentSQLAnalysisService:
    """Agent SQL分析服务"""
    
    def __init__(self, db: Session, user_id: str = None):
        self.db = db
        self.user_id = user_id
        self.multi_db_agent = MultiDatabaseAgent(db_session=db, user_id=user_id)
        # 使用create_connector函数而不是工厂类
    
    async def analyze_placeholder_with_agent(
        self,
        placeholder_id: str,
        data_source_id: str,
        force_reanalyze: bool = False,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用Agent分析单个占位符，生成SQL查询
        
        Args:
            placeholder_id: 占位符ID
            data_source_id: 数据源ID  
            force_reanalyze: 是否强制重新分析
            
        Returns:
            分析结果
        """
        try:
            # 1. 获取占位符信息
            placeholder = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == placeholder_id
            ).first()
            
            if not placeholder:
                raise ValueError(f"占位符不存在: {placeholder_id}")
            
            # 2. 检查是否已分析（除非强制重新分析）
            if placeholder.agent_analyzed and not force_reanalyze:
                logger.info(f"占位符已分析，跳过: {placeholder.placeholder_name}")
                return await self._get_existing_analysis_result(placeholder)
            
            # 3. 获取数据源信息
            data_source = self.db.query(DataSource).filter(
                DataSource.id == data_source_id
            ).first()
            
            if not data_source:
                raise ValueError(f"数据源不存在: {data_source_id}")
            
            logger.info(f"开始Agent分析占位符: {placeholder.placeholder_name}")
            
            # 4. 使用Multi-Database Agent进行分析
            analysis_result = await self._perform_agent_analysis(placeholder, data_source, execution_context)
            
            # 5. 验证生成的SQL
            validation_result = await self._validate_generated_sql(
                analysis_result["generated_sql"], 
                data_source
            )
            
            # 6. 持久化分析结果
            await self._save_analysis_result(
                placeholder, 
                analysis_result, 
                validation_result
            )
            
            logger.info(f"Agent分析完成: {placeholder.placeholder_name}")
            
            return {
                "success": True,
                "placeholder_id": placeholder_id,
                "placeholder_name": placeholder.placeholder_name,
                "analysis_result": analysis_result,
                "validation_result": validation_result,
                "confidence_score": analysis_result.get("confidence_score", 0.0)
            }
            
        except Exception as e:
            logger.error(f"Agent分析失败: {placeholder_id}, 错误: {str(e)}")
            
            # 记录失败状态
            if 'placeholder' in locals():
                placeholder.confidence_score = 0.0
                placeholder.analyzed_at = datetime.now()
                self.db.commit()
            
            return {
                "success": False,
                "placeholder_id": placeholder_id,
                "error": str(e),
                "confidence_score": 0.0
            }
    
    async def batch_analyze_template_placeholders(
        self,
        template_id: str,
        data_source_id: str,
        force_reanalyze: bool = False,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        批量分析模板的所有占位符
        """
        try:
            # 1. 获取需要分析的占位符
            query = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.template_id == template_id,
                TemplatePlaceholder.is_active == True
            )
            
            if not force_reanalyze:
                query = query.filter(TemplatePlaceholder.agent_analyzed == False)
            
            placeholders = query.order_by(TemplatePlaceholder.execution_order).all()
            
            if not placeholders:
                return {
                    "success": True,
                    "template_id": template_id,
                    "total_placeholders": 0,
                    "analyzed_placeholders": 0,
                    "message": "没有需要分析的占位符"
                }
            
            logger.info(f"开始批量分析模板占位符: {template_id}, 数量: {len(placeholders)}")
            
            # 2. 逐个分析占位符
            analysis_results = []
            successful_count = 0
            
            for placeholder in placeholders:
                result = await self.analyze_placeholder_with_agent(
                    str(placeholder.id),
                    data_source_id,
                    force_reanalyze,
                    execution_context
                )
                
                analysis_results.append(result)
                
                if result["success"]:
                    successful_count += 1
            
            # 3. 汇总结果
            total_count = len(placeholders)
            success_rate = (successful_count / total_count) * 100 if total_count > 0 else 0
            
            logger.info(f"批量分析完成: {template_id}, 成功率: {success_rate:.1f}%")
            
            return {
                "success": True,
                "template_id": template_id,
                "total_placeholders": total_count,
                "analyzed_placeholders": successful_count,
                "success_rate": success_rate,
                "analysis_results": analysis_results,
                "summary": {
                    "successful": successful_count,
                    "failed": total_count - successful_count,
                    "avg_confidence": sum(r.get("confidence_score", 0) for r in analysis_results) / total_count
                }
            }
            
        except Exception as e:
            logger.error(f"批量分析失败: {template_id}, 错误: {str(e)}")
            return {
                "success": False,
                "template_id": template_id,
                "error": str(e),
                "total_placeholders": 0,
                "analyzed_placeholders": 0
            }
    
    async def _perform_agent_analysis(
        self,
        placeholder: TemplatePlaceholder,
        data_source: DataSource,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行Agent分析"""
        
        # 1. 准备Agent分析的输入数据
        agent_input = {
            "placeholder_name": placeholder.placeholder_name,
            "placeholder_type": placeholder.placeholder_type,
            "content_type": placeholder.content_type,
            "description": placeholder.description,
            "intent_analysis": placeholder.agent_config.get("intent_analysis", {}),
            "context_keywords": placeholder.agent_config.get("context_keywords", []),
            "data_source": {
                "id": str(data_source.id),
                "name": data_source.name,
                "source_type": data_source.source_type,
                "connection_config": self._get_safe_connection_config(data_source)
            }
        }
        
        # 2. 使用Multi-Database Agent进行分析
        try:
            # 获取数据库schema信息
            schema_info = await self._get_database_schema(data_source)
            agent_input["schema_info"] = schema_info
            
            # 调用Agent分析，传递执行上下文
            agent_result = await self.multi_db_agent.analyze_placeholder_requirements(agent_input, execution_context)
            
            # 3. 处理Agent返回结果
            if agent_result.get("success", False):
                return {
                    "target_database": agent_result.get("target_database", ""),
                    "target_table": agent_result.get("target_table", ""),
                    "required_fields": agent_result.get("required_fields", []),
                    "generated_sql": agent_result.get("generated_sql", ""),
                    "confidence_score": agent_result.get("confidence_score", 0.0),
                    "analysis_reasoning": agent_result.get("reasoning", ""),
                    "suggested_optimizations": agent_result.get("optimizations", []),
                    "estimated_execution_time": agent_result.get("estimated_time_ms", 0)
                }
            else:
                raise Exception(f"Agent分析失败: {agent_result.get('error', '未知错误')}")
                
        except Exception as e:
            logger.error(f"Agent分析执行失败: {str(e)}")
            
            # 降级到基于规则的SQL生成
            return await self._fallback_sql_generation(placeholder, data_source)
    
    async def _fallback_sql_generation(
        self,
        placeholder: TemplatePlaceholder,
        data_source: DataSource
    ) -> Dict[str, Any]:
        """降级到基于规则的SQL生成"""
        logger.warning(f"使用降级SQL生成: {placeholder.placeholder_name}")
        
        # 基于占位符名称和类型生成简单SQL
        intent = placeholder.agent_config.get("intent_analysis", {})
        placeholder_name = placeholder.placeholder_name.lower()
        
        # 尝试推断表名（基于关键词）
        schema_info = await self._get_database_schema(data_source)
        target_table = self._guess_target_table(placeholder_name, schema_info)
        
        # 生成基础SQL
        if intent.get("data_operation") == "count":
            sql = f"SELECT COUNT(*) as count FROM {target_table}"
        elif intent.get("data_operation") == "sum":
            sql = f"SELECT SUM(amount) as sum_value FROM {target_table}"
        elif intent.get("data_operation") == "average":
            sql = f"SELECT AVG(amount) as avg_value FROM {target_table}"
        elif intent.get("data_operation") == "list":
            sql = f"SELECT * FROM {target_table} LIMIT 100"
        else:
            sql = f"SELECT COUNT(*) as count FROM {target_table}"
        
        return {
            "target_database": data_source.doris_database or "default",
            "target_table": target_table,
            "required_fields": ["*"],
            "generated_sql": sql,
            "confidence_score": 0.3,  # 低置信度
            "analysis_reasoning": "基于规则的降级生成",
            "suggested_optimizations": [],
            "estimated_execution_time": 1000
        }
    
    async def _validate_generated_sql(
        self,
        sql: str,
        data_source: DataSource
    ) -> Dict[str, Any]:
        """验证生成的SQL并提供修正建议"""
        try:
            # 1. 基础语法检查
            syntax_check = self._check_sql_syntax(sql)
            if not syntax_check["valid"]:
                # 尝试自动修正语法错误
                corrected_sql = await self._attempt_sql_correction(sql, syntax_check["error"])
                return {
                    "valid": False,
                    "error_type": "syntax_error",
                    "original_sql": sql,
                    "corrected_sql": corrected_sql,
                    "error_message": syntax_check["error"],
                    "validated_at": datetime.now().isoformat()
                }
            
            # 2. 尝试执行EXPLAIN（不实际查询数据）
            connector = None
            try:
                connector = create_connector(data_source)
                await connector.connect()
                
                # 先尝试简单的表存在性检查
                table_check = await self._validate_table_existence(sql, connector)
                if not table_check["valid"]:
                    # 表不存在，尝试修正表名
                    corrected_sql = await self._fix_table_names(sql, connector)
                    return {
                        "valid": False,
                        "error_type": "table_not_found",
                        "original_sql": sql,
                        "corrected_sql": corrected_sql,
                        "error_message": table_check["error"],
                        "validated_at": datetime.now().isoformat()
                    }
                
                # 执行EXPLAIN查询验证
                explain_sql = f"EXPLAIN {sql}"
                explain_result = await connector.execute_query(explain_sql)
                
                return {
                    "valid": True,
                    "execution_plan": explain_result,
                    "estimated_cost": self._extract_cost_from_plan(explain_result),
                    "validated_at": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.warning(f"SQL验证执行失败: {str(e)}")
                
                # 尝试修正SQL错误
                corrected_sql = await self._attempt_runtime_correction(sql, str(e), data_source)
                
                return {
                    "valid": False,
                    "error_type": "execution_error",
                    "original_sql": sql,
                    "corrected_sql": corrected_sql,
                    "error_message": str(e),
                    "validated_at": datetime.now().isoformat()
                }
            
            finally:
                if connector:
                    try:
                        await connector.disconnect()
                    except Exception as e:
                        logger.warning(f"断开连接失败: {str(e)}")
                
        except Exception as e:
            logger.error(f"SQL验证失败: {str(e)}")
            return {
                "valid": False,
                "error_type": "validation_error",
                "error_message": str(e),
                "validated_at": datetime.now().isoformat()
            }
    
    async def _save_analysis_result(
        self,
        placeholder: TemplatePlaceholder,
        analysis_result: Dict[str, Any],
        validation_result: Dict[str, Any]
    ):
        """保存分析结果到数据库"""
        
        # 更新占位符记录
        placeholder.agent_analyzed = True
        placeholder.target_database = analysis_result.get("target_database", "")
        placeholder.target_table = analysis_result.get("target_table", "")
        placeholder.required_fields = analysis_result.get("required_fields", [])
        placeholder.generated_sql = analysis_result.get("generated_sql", "")
        placeholder.sql_validated = validation_result.get("valid", False)
        placeholder.confidence_score = analysis_result.get("confidence_score", 0.0)
        placeholder.analyzed_at = datetime.now()
        
        # 更新agent_config，保存分析详情
        if not placeholder.agent_config:
            placeholder.agent_config = {}
            
        placeholder.agent_config.update({
            "analysis_result": {
                "reasoning": analysis_result.get("analysis_reasoning", ""),
                "optimizations": analysis_result.get("suggested_optimizations", []),
                "estimated_time_ms": analysis_result.get("estimated_execution_time", 0)
            },
            "validation_result": validation_result,
            "last_analysis_at": datetime.now().isoformat()
        })
        
        self.db.commit()
        logger.info(f"分析结果已保存: {placeholder.placeholder_name}")
    
    def _get_safe_connection_config(self, data_source: DataSource) -> Dict[str, Any]:
        """获取安全的连接配置（不包含密码）"""
        config = {
            "host": getattr(data_source, 'doris_fe_hosts', []),
            "port": getattr(data_source, 'doris_query_port', 9030),
            "database": getattr(data_source, 'doris_database', 'default'),
            "username": getattr(data_source, 'doris_username', '')
        }
        return config
    
    async def _get_database_schema(self, data_source: DataSource) -> Dict[str, Any]:
        """获取数据库schema信息 - 使用增强的connector API方法"""
        try:
            # 首先尝试从缓存获取表结构
            cached_schema = self._get_cached_schema(data_source.id)
            if cached_schema and cached_schema.get("tables"):
                logger.info(f"使用缓存的表结构信息: {data_source.name}, 发现 {len(cached_schema.get('tables', []))} 个表")
                return cached_schema
            
            # 如果缓存中没有，则直接查询数据源
            logger.info(f"缓存中无表结构，使用增强的API查询数据源: {data_source.name}")
            connector = None
            try:
                connector = create_connector(data_source)
                await connector.connect()
                
                # 获取数据库列表 - 使用增强的API
                databases = await connector.get_databases()
                logger.info(f"获取到数据库列表: {databases}")
                
                # 获取表列表 - 使用增强的API，支持多层回退机制
                tables = await connector.get_tables()
                logger.info(f"获取到表列表: {tables}")
                
                # 获取表结构信息（前几个表作为示例）- 使用增强的API
                table_schemas = {}
                for table_name in tables[:15]:  # 增加到15个表，提升Agent分析质量
                    try:
                        # 使用增强的get_table_schema方法，包含更详细的字段信息
                        schema_info = await connector.get_table_schema(table_name)
                        table_schemas[table_name] = schema_info
                        
                        # 记录更详细的信息用于Agent分析
                        columns_count = len(schema_info.get('columns', []))
                        logger.info(f"获取表结构成功: {table_name}, 字段数量: {columns_count}")
                        
                        # 为Agent分析添加额外的表元数据
                        if 'metadata' not in table_schemas[table_name]:
                            table_schemas[table_name]['metadata'] = {}
                        table_schemas[table_name]['metadata'].update({
                            'columns_count': columns_count,
                            'table_type': schema_info.get('table_type', 'table'),
                            'business_relevance': self._assess_business_relevance(table_name, schema_info)
                        })
                        
                    except Exception as e:
                        logger.warning(f"获取表结构失败: {table_name}, {str(e)}")
                
                # 缓存表结构信息到数据库
                try:
                    await self._cache_schema_info(data_source.id, databases, tables, table_schemas)
                    logger.info(f"表结构信息已缓存到数据库: {len(tables)} 个表")
                except Exception as e:
                    logger.warning(f"缓存表结构信息失败: {e}")
                
                # 为Agent分析构建更完整的schema信息
                enhanced_schema = {
                    "databases": databases,
                    "tables": tables,
                    "table_schemas": table_schemas,
                    "schema_retrieved_at": datetime.now().isoformat(),
                    "source": "enhanced_api_query",
                    "quality_metrics": {
                        "total_tables": len(tables),
                        "tables_with_schema": len(table_schemas),
                        "schema_completion_rate": (len(table_schemas) / len(tables)) * 100 if tables else 0
                    }
                }
                
                logger.info(f"增强schema信息构建完成，表结构完整率: {enhanced_schema['quality_metrics']['schema_completion_rate']:.1f}%")
                return enhanced_schema
                
            finally:
                if connector:
                    try:
                        await connector.disconnect()
                    except Exception as e:
                        logger.warning(f"断开连接失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"获取数据库schema失败: {str(e)}")
            return {
                "databases": [],
                "tables": [],
                "table_schemas": {},
                "error": str(e)
            }
    
    def _get_cached_schema(self, data_source_id: str) -> Optional[Dict[str, Any]]:
        """从缓存获取表结构信息"""
        try:
            from app.models.table_schema import TableSchema
            
            # 查询缓存的表结构
            cached_tables = self.db.query(TableSchema).filter(
                TableSchema.data_source_id == data_source_id,
                TableSchema.is_active == True
            ).all()
            
            if not cached_tables:
                return None
            
            tables = []
            table_schemas = {}
            
            for table_schema in cached_tables:
                table_name = table_schema.table_name
                tables.append(table_name)
                
                # 从JSON字段获取列信息
                columns_info = table_schema.columns_info or []
                
                # 确保列信息格式一致
                formatted_columns = []
                for col_info in columns_info:
                    if isinstance(col_info, dict):
                        formatted_columns.append({
                            "name": col_info.get("name", ""),
                            "type": col_info.get("type", ""),
                            "nullable": col_info.get("nullable", True),
                            "key": col_info.get("key", ""),
                            "default": col_info.get("default", ""),
                            "extra": col_info.get("extra", "")
                        })
                
                table_schemas[table_name] = {
                    "table_name": table_name,
                    "columns": formatted_columns,
                    "total_columns": len(formatted_columns),
                    "estimated_rows": table_schema.estimated_row_count or 0,
                    "table_size": table_schema.table_size_bytes or 0,
                    "last_analyzed": table_schema.last_analyzed.isoformat() if table_schema.last_analyzed else None
                }
            
            return {
                "databases": ["default"],  # 默认数据库
                "tables": tables,
                "table_schemas": table_schemas,
                "schema_retrieved_at": datetime.now().isoformat(),
                "source": "cached"
            }
            
        except Exception as e:
            logger.error(f"从缓存获取表结构失败: {e}")
            return None
    
    async def _cache_schema_info(self, data_source_id: str, databases: List[str], tables: List[str], table_schemas: Dict[str, Any]):
        """缓存表结构信息到数据库"""
        try:
            from app.models.table_schema import TableSchema, ColumnSchema
            
            # 首先清理旧的缓存数据
            self.db.query(TableSchema).filter(
                TableSchema.data_source_id == data_source_id
            ).update({"is_active": False})
            
            # 保存新的表结构信息
            for table_name, schema_info in table_schemas.items():
                if "error" in schema_info:
                    continue
                    
                # 创建表结构记录
                columns_info = schema_info.get("columns", [])
                
                table_schema = TableSchema(
                    data_source_id=data_source_id,
                    table_name=table_name,
                    table_schema=None,  # 数据库schema名
                    table_catalog=None,  # 数据库catalog名
                    columns_info=columns_info,
                    primary_keys=[col.get("name") for col in columns_info if col.get("key") == "PRI"],
                    indexes=[],  # 可以后续更新
                    constraints=[],  # 可以后续更新
                    estimated_row_count=0,
                    table_size_bytes=0,
                    last_analyzed=datetime.now(),
                    is_active=True
                )
                
                self.db.add(table_schema)
                self.db.flush()  # 获取ID
            
            self.db.commit()
            logger.info(f"成功缓存 {len(table_schemas)} 个表的结构信息")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"缓存表结构信息失败: {e}")
            raise
    
    def _normalize_column_type(self, column_type: str) -> str:
        """标准化列类型"""
        if not column_type:
            return "UNKNOWN"
        
        column_type = column_type.upper()
        
        if "INT" in column_type or "BIGINT" in column_type:
            return "INTEGER"
        elif "VARCHAR" in column_type or "TEXT" in column_type or "STRING" in column_type:
            return "STRING"
        elif "DECIMAL" in column_type or "DOUBLE" in column_type or "FLOAT" in column_type:
            return "NUMERIC"
        elif "DATE" in column_type:
            return "DATE"
        elif "DATETIME" in column_type or "TIMESTAMP" in column_type:
            return "DATETIME"
        else:
            return column_type
    
    def _check_sql_syntax(self, sql: str) -> Dict[str, Any]:
        """基础SQL语法检查"""
        try:
            sql = sql.strip().upper()
            
            # 基础语法检查
            if not sql.startswith('SELECT'):
                return {"valid": False, "error": "SQL必须以SELECT开始"}
            
            if 'FROM' not in sql:
                return {"valid": False, "error": "缺少FROM子句"}
            
            # 检查危险操作
            dangerous_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER']
            for keyword in dangerous_keywords:
                if keyword in sql:
                    return {"valid": False, "error": f"包含危险关键词: {keyword}"}
            
            return {"valid": True}
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def _extract_cost_from_plan(self, explain_result: Any) -> float:
        """从执行计划中提取成本估算"""
        # 这里是简化实现，实际需要根据具体数据库的EXPLAIN格式解析
        return 1.0
    
    def _guess_target_table(self, placeholder_name: str, schema_info: Dict) -> str:
        """基于占位符名称猜测目标表"""
        tables = schema_info.get("tables", [])
        
        if not tables:
            logger.warning(f"没有找到可用表，占位符: {placeholder_name}")
            # 返回一个通用的虚拟表名，但实际执行时会被Doris连接器处理
            return "default_table"
        
        # 基于关键词匹配
        name_lower = placeholder_name.lower()
        
        # 投诉相关
        if any(keyword in name_lower for keyword in ['投诉', 'complaint', '举报']):
            for table in tables:
                if any(keyword in table.lower() for keyword in ['complaint', 'report', 'feedback']):
                    return table
        
        # 身份证相关
        if any(keyword in name_lower for keyword in ['身份证', 'id_card', 'identity']):
            for table in tables:
                if any(keyword in table.lower() for keyword in ['identity', 'id_card', 'person']):
                    return table
        
        # 手机号相关
        if any(keyword in name_lower for keyword in ['手机号', 'phone', 'mobile']):
            for table in tables:
                if any(keyword in table.lower() for keyword in ['phone', 'mobile', 'contact']):
                    return table
        
        # 旅行社相关
        if any(keyword in name_lower for keyword in ['旅行社', 'travel', 'agency']):
            for table in tables:
                if any(keyword in table.lower() for keyword in ['travel', 'agency', 'tour']):
                    return table
        
        # 用户相关
        if any(keyword in name_lower for keyword in ['用户', 'user', 'customer']):
            for table in tables:
                if any(keyword in table.lower() for keyword in ['user', 'customer', 'member']):
                    return table
        
        # 订单相关
        if any(keyword in name_lower for keyword in ['订单', 'order', 'booking']):
            for table in tables:
                if any(keyword in table.lower() for keyword in ['order', 'booking', 'reservation']):
                    return table
        
        # 统计相关 - 尝试找主要业务表
        if any(keyword in name_lower for keyword in ['统计', 'count', 'total']):
            # 优先选择看起来像主业务表的表名
            for table in tables:
                if any(keyword in table.lower() for keyword in ['main', 'primary', 'data', 'info']):
                    return table
        
        # 默认返回第一个表
        logger.info(f"使用默认表 {tables[0]} 作为占位符 {placeholder_name} 的目标表")
        return tables[0]
    
    def _assess_business_relevance(self, table_name: str, schema_info: Dict) -> float:
        """评估表的业务相关性分数"""
        relevance_score = 0.0
        table_lower = table_name.lower()
        
        # 基于表名的业务相关性
        business_keywords = {
            'complaint': 1.0, 'report': 0.9, 'feedback': 0.8,
            'user': 0.9, 'customer': 0.9, 'member': 0.8,
            'order': 0.9, 'booking': 0.8, 'reservation': 0.7,
            'travel': 0.8, 'agency': 0.7, 'tour': 0.7,
            'phone': 0.6, 'contact': 0.6, 'identity': 0.6,
            'data': 0.5, 'info': 0.5, 'main': 0.7
        }
        
        for keyword, score in business_keywords.items():
            if keyword in table_lower:
                relevance_score = max(relevance_score, score)
        
        # 基于字段数量调整分数
        columns_count = len(schema_info.get('columns', []))
        if columns_count > 10:
            relevance_score += 0.1
        elif columns_count > 5:
            relevance_score += 0.05
            
        return min(1.0, relevance_score)
    
    async def _attempt_sql_correction(self, sql: str, error_message: str) -> str:
        """尝试修正SQL语法错误"""
        corrected_sql = sql
        
        # 常见语法错误修正
        if "missing FROM" in error_message.lower():
            # 添加FROM子句
            if "SELECT" in sql and "FROM" not in sql:
                corrected_sql = sql.replace("SELECT", "SELECT * FROM default_table WHERE")
        
        elif "semicolon" in error_message.lower():
            # 移除多余的分号
            corrected_sql = sql.rstrip(';')
        
        elif "quote" in error_message.lower():
            # 修正引号问题
            corrected_sql = sql.replace("'", "\"")
        
        logger.info(f"SQL语法修正: {sql} -> {corrected_sql}")
        return corrected_sql
    
    async def _validate_table_existence(self, sql: str, connector) -> Dict[str, Any]:
        """验证SQL中的表是否存在"""
        try:
            import re
            # 简单的表名提取（可以改进）
            table_pattern = r'FROM\s+([\w_]+)'
            matches = re.findall(table_pattern, sql, re.IGNORECASE)
            
            if not matches:
                return {"valid": True}  # 没有找到表名，跳过检查
            
            tables = await connector.get_tables()
            for table_name in matches:
                if table_name not in tables:
                    return {
                        "valid": False,
                        "error": f"表 {table_name} 不存在",
                        "available_tables": tables[:10]  # 返回前10个可用表
                    }
            
            return {"valid": True}
            
        except Exception as e:
            logger.warning(f"表存在性检查失败: {e}")
            return {"valid": True}  # 检查失败时假设存在
    
    async def _fix_table_names(self, sql: str, connector) -> str:
        """修正SQL中的表名"""
        try:
            import re
            tables = await connector.get_tables()
            
            if not tables:
                return sql
            
            # 提取并替换表名
            def replace_table(match):
                original_table = match.group(1)
                # 查找最相似的表名
                best_match = self._find_similar_table(original_table, tables)
                logger.info(f"表名修正: {original_table} -> {best_match}")
                return f"FROM {best_match}"
            
            corrected_sql = re.sub(r'FROM\s+([\w_]+)', replace_table, sql, flags=re.IGNORECASE)
            return corrected_sql
            
        except Exception as e:
            logger.error(f"表名修正失败: {e}")
            return sql
    
    def _find_similar_table(self, target_table: str, available_tables: List[str]) -> str:
        """查找最相似的表名"""
        target_lower = target_table.lower()
        
        # 精确匹配
        for table in available_tables:
            if table.lower() == target_lower:
                return table
        
        # 包含匹配
        for table in available_tables:
            if target_lower in table.lower() or table.lower() in target_lower:
                return table
        
        # 返回第一个可用表作为默认值
        return available_tables[0] if available_tables else "default_table"
    
    async def _attempt_runtime_correction(self, sql: str, error_message: str, data_source: DataSource) -> str:
        """运行时错误修正"""
        corrected_sql = sql
        error_lower = error_message.lower()
        
        # 字段不存在错误
        if "column" in error_lower and "not found" in error_lower:
            # 替换为通配符查询
            corrected_sql = re.sub(r'SELECT\s+[^\s]+', 'SELECT *', sql, flags=re.IGNORECASE)
            logger.info(f"字段修正为通配符查询: {corrected_sql}")
        
        # 权限错误
        elif "access denied" in error_lower or "permission" in error_lower:
            # 简化查询，只查询基础信息
            corrected_sql = re.sub(r'SELECT\s+.*?FROM', 'SELECT COUNT(*) FROM', sql, flags=re.IGNORECASE)
            logger.info(f"权限问题修正为COUNT查询: {corrected_sql}")
        
        return corrected_sql
    
    async def _get_existing_analysis_result(self, placeholder: TemplatePlaceholder) -> Dict[str, Any]:
        """获取已存在的分析结果"""
        return {
            "success": True,
            "placeholder_id": str(placeholder.id),
            "placeholder_name": placeholder.placeholder_name,
            "analysis_result": {
                "target_database": placeholder.target_database,
                "target_table": placeholder.target_table,
                "required_fields": placeholder.required_fields,
                "generated_sql": placeholder.generated_sql,
                "confidence_score": placeholder.confidence_score,
                "analysis_reasoning": placeholder.agent_config.get("analysis_result", {}).get("reasoning", ""),
                "suggested_optimizations": placeholder.agent_config.get("analysis_result", {}).get("optimizations", []),
                "estimated_execution_time": placeholder.agent_config.get("analysis_result", {}).get("estimated_time_ms", 0)
            },
            "validation_result": placeholder.agent_config.get("validation_result", {}),
            "confidence_score": placeholder.confidence_score,
            "from_cache": True
        }