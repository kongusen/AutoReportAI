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
    
    def __init__(self, db: Session):
        self.db = db
        self.multi_db_agent = MultiDatabaseAgent()
        # 使用create_connector函数而不是工厂类
    
    async def analyze_placeholder_with_agent(
        self,
        placeholder_id: str,
        data_source_id: str,
        force_reanalyze: bool = False
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
            analysis_result = await self._perform_agent_analysis(placeholder, data_source)
            
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
        force_reanalyze: bool = False
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
                    force_reanalyze
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
        data_source: DataSource
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
            
            # 调用Agent分析
            agent_result = await self.multi_db_agent.analyze_placeholder_requirements(agent_input)
            
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
        """验证生成的SQL"""
        try:
            # 1. 基础语法检查
            syntax_check = self._check_sql_syntax(sql)
            if not syntax_check["valid"]:
                return {
                    "valid": False,
                    "error_type": "syntax_error",
                    "error_message": syntax_check["error"],
                    "validated_at": datetime.now().isoformat()
                }
            
            # 2. 尝试执行EXPLAIN（不实际查询数据）
            try:
                connector = self.connector_factory.get_connector(data_source)
                explain_sql = f"EXPLAIN {sql}"
                
                # 执行EXPLAIN查询
                explain_result = await connector.execute_query(explain_sql)
                
                return {
                    "valid": True,
                    "execution_plan": explain_result,
                    "estimated_cost": self._extract_cost_from_plan(explain_result),
                    "validated_at": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.warning(f"SQL EXPLAIN执行失败，但语法正确: {str(e)}")
                return {
                    "valid": True,  # 语法正确，但无法获取执行计划
                    "warning": f"无法获取执行计划: {str(e)}",
                    "validated_at": datetime.now().isoformat()
                }
                
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
        """获取数据库schema信息"""
        try:
            connector = self.connector_factory.get_connector(data_source)
            
            # 获取数据库列表
            databases = await connector.get_databases()
            
            # 获取表列表（当前数据库）
            tables = await connector.get_tables(data_source.doris_database or 'default')
            
            # 获取表结构信息（前几个表作为示例）
            table_schemas = {}
            for table_name in tables[:10]:  # 限制数量避免过多查询
                try:
                    columns = await connector.get_table_schema(table_name)
                    table_schemas[table_name] = columns
                except Exception as e:
                    logger.warning(f"获取表结构失败: {table_name}, {str(e)}")
            
            return {
                "databases": databases,
                "tables": tables,
                "table_schemas": table_schemas,
                "schema_retrieved_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取数据库schema失败: {str(e)}")
            return {
                "databases": [],
                "tables": [],
                "table_schemas": {},
                "error": str(e)
            }
    
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
            return "unknown_table"
        
        # 基于关键词匹配
        name_lower = placeholder_name.lower()
        
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
        
        # 默认返回第一个表
        return tables[0] if tables else "unknown_table"
    
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