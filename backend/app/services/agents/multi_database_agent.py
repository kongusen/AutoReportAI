"""
Multi-Database Agent

多数据库智能代理，负责分析占位符需求、选择目标表和生成SQL查询
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.services.connectors.base_connector import BaseConnector
from app.services.connectors.doris_connector import DorisConnector, DorisConfig
from app.core.ai_service_factory import UserAIServiceFactory

logger = logging.getLogger(__name__)


class MultiDatabaseAgent:
    """多数据库智能代理"""
    
    def __init__(self, db_session=None, user_id=None):
        """初始化多数据库代理"""
        self.db_session = db_session
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
        
        # 初始化AI服务
        try:
            from app.services.agents.core.ai_service import UnifiedAIService
            if user_id and db_session:
                from app.core.ai_service_factory import UserAIServiceFactory
                factory = UserAIServiceFactory()
                self.ai_service = factory.get_user_ai_service(user_id)
                self.logger.info(f"使用用户特定AI服务: {user_id}")
            else:
                self.ai_service = UnifiedAIService(db_session=db_session)
                self.logger.info("使用系统默认AI服务")
        except Exception as e:
            self.logger.warning(f"AI服务初始化失败: {e}")
            try:
                self.ai_service = UnifiedAIService(db_session=db_session)
                self.logger.info("回退到系统默认AI服务")
            except Exception as e2:
                self.logger.error(f"系统默认AI服务也失败: {e2}")
                self.ai_service = None
    
    async def analyze_placeholder_requirements(
        self, 
        agent_input: Dict[str, Any],
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分析占位符需求
        
        Args:
            agent_input: 包含占位符信息的字典
            execution_context: 可选执行上下文
        
        Returns:
            分析结果字典
        """
        start_time = datetime.now()
        
        try:
            placeholder_name = agent_input.get("placeholder_name", "")
            placeholder_type = agent_input.get("placeholder_type", "")
            data_source = agent_input.get("data_source", {})
            
            self.logger.info(f"🚀 开始Agent分析占位符: {placeholder_name}")
            self.logger.info(f"📊 占位符类型: {placeholder_type}, 数据源: {data_source.get('id', 'unknown')}")
            if execution_context:
                self.logger.debug(f"执行上下文: {execution_context}")
            
            # 1. 获取数据源结构信息
            self.logger.info("🔍 获取数据源结构信息...")
            enhanced_schema = await self._get_enhanced_schema(data_source)
            
            if not enhanced_schema:
                return {
                    "success": False,
                    "error": "无法获取数据源结构信息"
                }
            
            # 2. 执行AI语义分析
            self.logger.info("🧠 使用 ai_agent 分析模式")
            if self.user_id:
                self.logger.info(f"使用用户特定AI服务进行分析: {self.user_id}")
            else:
                self.logger.info("使用系统默认AI服务进行分析")
            
            semantic_analysis = await self._perform_ai_agent_analysis(
                placeholder_name, placeholder_type, enhanced_schema, data_source
            )
            
            if not semantic_analysis.get("success"):
                return {
                    "success": False,
                    "error": f"AI Agent分析失败: {semantic_analysis.get('error', '未知错误')}"
                }
            
            # 3. 执行智能目标选择
            self.logger.info("🎯 执行智能目标选择...")
            target_selection = await self._perform_intelligent_target_selection(
                semantic_analysis, enhanced_schema
            )
            
            if not target_selection.get("success"):
                return {
                    "success": False,
                    "error": f"智能目标选择失败: {target_selection.get('error', '未知错误')}"
                }
            
            # 4. 生成智能SQL
            self.logger.info("⚙️ 生成智能SQL...")
            generated_sql = await self._generate_intelligent_sql(
                semantic_analysis, target_selection, enhanced_schema
            )
            
            if not generated_sql:
                return {
                    "success": False,
                    "error": "AI SQL生成失败: AI服务未初始化，请提供有效的数据库会话"
                }
            
            # 5. 执行SQL质量验证和改进
            self.logger.info("🔧 执行SQL质量验证和改进...")
            final_sql = await self._self_validate_and_improve_sql(
                generated_sql, data_source.get("id"), target_selection
            )
            
            # 6. 构建分析元数据
            analysis_metadata = {
                "analysis_mode": "ai_agent",
                "intent": semantic_analysis.get("intent", "unknown"),
                "data_operation": semantic_analysis.get("data_operation", "unknown"),
                "relevant_tables_count": len(enhanced_schema.get("tables", [])),
                "analysis_duration_seconds": (datetime.now() - start_time).total_seconds(),
                "ai_service_used": "user_specific" if self.user_id else "system_default"
            }
            
            return {
                "success": True,
                "target_database": data_source.get("name", ""),
                "target_table": target_selection.get("table", ""),
                "required_fields": target_selection.get("fields", []),
                "generated_sql": final_sql,
                "confidence_score": semantic_analysis.get("confidence", 0.8),
                "reasoning": semantic_analysis.get("reasoning", []),
                "optimizations": semantic_analysis.get("optimizations", []),
                "estimated_time_ms": 100,
                "analysis_metadata": analysis_metadata
            }
            
        except Exception as e:
            self.logger.error(f"占位符需求分析失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_enhanced_schema(self, data_source: Dict[str, Any]) -> Dict[str, Any]:
        """获取增强的数据源schema信息"""
        try:
            data_source_id = data_source.get("id")
            source_type = data_source.get("source_type")
            
            # 创建连接器
            connector = await self._create_connector(data_source)
            if not connector:
                return None
            
            try:
                # 连接数据库
                await connector.connect()
                
                # 获取数据库和表信息
                databases = await connector.get_databases()
                tables = await connector.get_tables()
                
                # 获取表结构详情
                table_details = {}
                for table in tables:
                    try:
                        columns = await connector.get_table_columns(table)
                        table_details[table] = columns
                    except Exception as e:
                        self.logger.warning(f"获取表 {table} 结构失败: {e}")
                        table_details[table] = []
                
                return {
                    "source_type": source_type,
                    "databases": databases,
                    "tables": tables,
                    "table_details": table_details,
                    "total_tables": len(tables),
                    "total_columns": sum(len(cols) for cols in table_details.values())
                }
                
            finally:
                await connector.disconnect()
                
        except Exception as e:
            self.logger.error(f"获取增强schema失败: {e}")
            return None
    
    async def _create_connector(self, data_source: Dict[str, Any]) -> Optional[BaseConnector]:
        """创建数据库连接器"""
        try:
            source_type = data_source.get("source_type")
            
            if source_type == "doris":
                # 从数据库获取数据源详细信息
                from app.models.data_source import DataSource
                ds = self.db_session.query(DataSource).filter(
                    DataSource.id == data_source.get("id")
                ).first()
                
                if not ds:
                    return None
                
                config = DorisConfig(
                    source_type=ds.source_type,
                    name=ds.name,
                    fe_hosts=ds.doris_fe_hosts if isinstance(ds.doris_fe_hosts, list) else [ds.doris_fe_hosts],
                    query_port=ds.doris_query_port or 9030,
                    http_port=ds.doris_http_port or 8030,
                    database=ds.doris_database or "default",
                    username=ds.doris_username or "root",
                    password=ds.doris_password or ""
                )
                
                return DorisConnector(config)
            else:
                self.logger.warning(f"不支持的数据源类型: {source_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"创建连接器失败: {e}")
            return None
    
    async def _perform_ai_agent_analysis(
        self, 
        placeholder_name: str, 
        placeholder_type: str, 
        enhanced_schema: Dict, 
        data_source: Dict
    ) -> Dict[str, Any]:
        """执行AI代理分析"""
        try:
            if not self.ai_service:
                return {
                    "success": False,
                    "error": "AI服务未初始化，请提供有效的数据库会话"
                }
            
            # 构建分析上下文
            context = {
                "placeholder_name": placeholder_name,
                "placeholder_type": placeholder_type,
                "data_source": data_source,
                "schema_info": enhanced_schema
            }
            
            # 构建AI分析提示
            prompt = self._build_ai_analysis_prompt(context, enhanced_schema)
            
            # 执行AI分析
            response = await self.ai_service.analyze_with_context(
                context=str(context), prompt=prompt, task_type="placeholder_analysis"
            )
            
            self.logger.info(f"AI响应内容: {response[:200]}...")  # Debugging line
            
            if response:
                try:
                    ai_result = {"success": True, "data": json.loads(response)}
                    self.logger.info("AI响应JSON解析成功")
                except json.JSONDecodeError as e:
                    self.logger.warning(f"AI响应JSON解析失败: {e}")
                    self.logger.warning(f"AI响应原始内容: {response}")
                    
                    # 尝试从响应中提取JSON
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        try:
                            json_str = response[json_start:json_end]
                            ai_result = {"success": True, "data": json.loads(json_str)}
                            self.logger.info("从响应中提取JSON成功")
                        except json.JSONDecodeError:
                            self.logger.error("提取的JSON仍然无效")
                            ai_result = {"success": True, "data": {"intent": "statistical", "data_operation": "count", "reasoning": [response]}}
                    else:
                        ai_result = {"success": True, "data": {"intent": "statistical", "data_operation": "count", "reasoning": [response]}}
            else:
                ai_result = {"success": True, "data": {"intent": "statistical", "data_operation": "count", "reasoning": ["AI分析失败"]}}
            
            if ai_result.get("success"):
                analysis_data = ai_result.get("data", {})
                return {
                    "success": True,
                    "intent": analysis_data.get("intent", "statistical"),
                    "data_operation": analysis_data.get("data_operation", "count"),
                    "business_domain": analysis_data.get("business_domain", ""),
                    "target_metrics": analysis_data.get("target_metrics", []),
                    "time_dimension": analysis_data.get("time_dimension"),
                    "grouping_dimensions": analysis_data.get("grouping_dimensions", []),
                    "filters": analysis_data.get("filters", []),
                    "aggregations": analysis_data.get("aggregations", []),
                    "reasoning": analysis_data.get("reasoning", []),
                    "confidence": analysis_data.get("confidence", 0.8),
                    "optimizations": analysis_data.get("optimizations", [])
                }
            else:
                return {
                    "success": False,
                    "error": "AI分析失败"
                }
                
        except Exception as e:
            self.logger.error(f"AI代理分析失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_ai_analysis_prompt(self, context: Dict, enhanced_schema: Dict) -> str:
        """构建AI分析提示 - 优化版本"""
        placeholder_name = context.get("placeholder_name", "")
        placeholder_type = context.get("placeholder_type", "")
        data_source = context.get("data_source", {})
        
        # 构建表结构信息
        tables_info = []
        for table_name, columns in enhanced_schema.get("table_details", {}).items():
            table_info = f"表名: {table_name}\n字段: {', '.join([col.get('name', '') for col in columns])}"
            tables_info.append(table_info)
        
        tables_text = "\n\n".join(tables_info)
        
        prompt = f"""
你是一个专业的数据分析师。请分析以下占位符的业务需求，并返回JSON格式的分析结果。

占位符信息:
- 名称: {placeholder_name}
- 类型: {placeholder_type}
- 数据源: {data_source.get('name', 'unknown')}

数据库结构信息:
{tables_text}

请严格按照以下JSON格式返回分析结果，不要包含任何其他文本：
{{
    "intent": "statistical",
    "data_operation": "count",
    "business_domain": "travel_service",
    "target_metrics": ["导游数量"],
    "time_dimension": null,
    "grouping_dimensions": [],
    "filters": ["city_id = '昆明'"],
    "aggregations": ["count"],
    "reasoning": ["根据占位符名称，目标是统计昆明注册的导游数量"],
    "confidence": 0.9,
    "optimizations": ["考虑建立索引在city_id字段上"]
}}

重要要求：
1. 只返回JSON对象，不要包含任何解释、注释或其他文本
2. 确保JSON语法完全正确
3. 字段名必须是数据库中实际存在的字段名
4. 聚合函数必须是标准的SQL聚合函数
请直接返回JSON对象，不要有任何前缀或后缀。
"""
        return prompt
    
    async def _perform_intelligent_target_selection(
        self, 
        semantic_analysis: Dict, 
        enhanced_schema: Dict
    ) -> Dict[str, Any]:
        """执行智能目标选择"""
        try:
            intent = semantic_analysis.get("intent", "statistical")
            business_domain = semantic_analysis.get("business_domain", "")
            target_metrics = semantic_analysis.get("target_metrics", [])
            
            # 基于语义分析筛选相关表
            relevant_tables = []
            for table_name, columns in enhanced_schema.get("table_details", {}).items():
                relevance_score = self._calculate_table_relevance(
                    table_name, columns, intent, business_domain, target_metrics
                )
                if relevance_score > 0.3:  # 相关性阈值
                    relevant_tables.append((table_name, relevance_score))
            
            # 按相关性排序
            relevant_tables.sort(key=lambda x: x[1], reverse=True)
            
            if relevant_tables:
                best_table = relevant_tables[0][0]
                self.logger.info(f"✅ 获取到 {len(relevant_tables)} 个相关表: {[t[0] for t in relevant_tables]}")
                
                # 选择最佳表的字段
                table_columns = enhanced_schema.get("table_details", {}).get(best_table, [])
                selected_fields = self._select_relevant_fields(
                    table_columns, semantic_analysis
                )
                
                return {
                    "success": True,
                    "table": best_table,
                    "fields": selected_fields,
                    "field_mapping": {},
                    "relevance_score": relevant_tables[0][1],
                    "alternative_tables": [t[0] for t in relevant_tables[1:3]]
                }
            else:
                # 如果没有找到相关表，使用默认表
                default_table = list(enhanced_schema.get("table_details", {}).keys())[0] if enhanced_schema.get("table_details") else "default_table"
                self.logger.warning(f"未找到相关表，使用默认表: {default_table}")
                
                return {
                    "success": True,
                    "table": default_table,
                    "fields": [],
                    "field_mapping": {},
                    "relevance_score": 0.1,
                    "alternative_tables": []
                }
                
        except Exception as e:
            self.logger.error(f"智能目标选择失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_table_relevance(
        self, 
        table_name: str, 
        columns: List[Dict], 
        intent: str, 
        business_domain: str, 
        target_metrics: List[str]
    ) -> float:
        """计算表相关性分数"""
        score = 0.0
        
        # 基于表名的相关性
        table_name_lower = table_name.lower()
        if business_domain.lower() in table_name_lower:
            score += 0.4
        if any(metric.lower() in table_name_lower for metric in target_metrics):
            score += 0.3
        
        # 基于字段名的相关性
        column_names = [col.get("name", "").lower() for col in columns]
        for metric in target_metrics:
            if any(metric.lower() in col for col in column_names):
                score += 0.2
        
        return min(score, 1.0)
    
    def _select_relevant_fields(
        self, 
        columns: List[Dict], 
        semantic_analysis: Dict
    ) -> List[str]:
        """选择相关字段"""
        relevant_fields = []
        target_metrics = semantic_analysis.get("target_metrics", [])
        
        for column in columns:
            column_name = column.get("name", "").lower()
            if any(metric.lower() in column_name for metric in target_metrics):
                relevant_fields.append(column.get("name", ""))
        
        return relevant_fields
    
    async def _generate_intelligent_sql(
        self, 
        semantic_analysis: Dict, 
        target_selection: Dict, 
        enhanced_schema: Dict
    ) -> str:
        """基于语义分析和目标选择生成智能SQL - 优化版本"""
        try:
            # 首先尝试AI驱动的SQL生成
            ai_generated_sql = await self._generate_sql_with_ai(semantic_analysis, target_selection, enhanced_schema)
            if ai_generated_sql and self._validate_sql_syntax(ai_generated_sql):
                return ai_generated_sql
            
            # 如果AI生成失败或SQL无效，使用模板化生成
            table_name = self._sanitize_identifier(target_selection.get('table', 'default_table'))
            fields = target_selection.get('fields', [])
            field_mapping = target_selection.get('field_mapping', {})
            
            sql = self._generate_sql_by_template(semantic_analysis.get('intent', 'general'),
                                                semantic_analysis.get('data_operation', 'select'),
                                                table_name, fields, field_mapping)
            
            if not self._validate_sql_syntax(sql):
                self.logger.warning(f"生成的SQL语法无效，使用备用方案: {sql}")
                sql = self._generate_fallback_sql(table_name)
            
            return sql
            
        except Exception as e:
            self.logger.error(f"生成智能SQL失败: {e}")
            return self._generate_fallback_sql()
    
    async def _generate_sql_with_ai(
        self, 
        semantic_analysis: Dict, 
        target_selection: Dict, 
        enhanced_schema: Dict
    ) -> str:
        """使用AI生成SQL"""
        try:
            if not self.ai_service:
                return None
            
            prompt = self._build_sql_generation_prompt(semantic_analysis, target_selection, enhanced_schema)
            
            response = await self.ai_service.analyze_with_context(
                context="", prompt=prompt, task_type="sql_generation"
            )
            
            if response:
                sql = self._extract_sql_from_response(response)
                if sql and self._validate_sql_syntax(sql):
                    return sql
            
            return None
            
        except Exception as e:
            self.logger.error(f"AI SQL生成失败: {e}")
            return None
    
    def _build_sql_generation_prompt(
        self, 
        semantic_analysis: Dict, 
        target_selection: Dict, 
        enhanced_schema: Dict
    ) -> str:
        """构建SQL生成提示"""
        table_name = target_selection.get('table', '')
        fields = target_selection.get('fields', [])
        
        prompt = f"""
你是一个SQL专家。请根据以下信息生成标准的SQL查询语句：

分析结果:
- 意图: {semantic_analysis.get('intent', '')}
- 数据操作: {semantic_analysis.get('data_operation', '')}
- 业务领域: {semantic_analysis.get('business_domain', '')}
- 目标指标: {semantic_analysis.get('target_metrics', [])}
- 过滤条件: {semantic_analysis.get('filters', [])}
- 聚合函数: {semantic_analysis.get('aggregations', [])}

目标表: {table_name}
相关字段: {fields}

请生成一个标准的SQL查询语句，只返回SQL语句，不要包含任何解释或其他文本。
确保SQL语法完全正确。
"""
        return prompt
    
    def _extract_sql_from_response(self, response: str) -> str:
        """从AI响应中提取SQL"""
        # 查找SQL语句
        sql_patterns = [
            r'SELECT\s+.*?FROM\s+.*?(?:WHERE\s+.*?)?(?:GROUP BY\s+.*?)?(?:ORDER BY\s+.*?)?(?:LIMIT\s+\d+)?;?',
            r'SELECT\s+.*?FROM\s+.*?(?:WHERE\s+.*?)?(?:GROUP BY\s+.*?)?(?:ORDER BY\s+.*?)?(?:LIMIT\s+\d+)?',
        ]
        
        for pattern in sql_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(0).strip()
        
        return None
    
    def _generate_sql_by_template(
        self, 
        intent: str, 
        operation: str, 
        table_name: str, 
        fields: List[str], 
        field_mapping: Dict
    ) -> str:
        """基于模板生成SQL"""
        if operation == "count":
            return f"SELECT COUNT(*) as total_count FROM {table_name}"
        elif operation == "sum":
            if fields:
                field = fields[0]
                return f"SELECT SUM({field}) as total_sum FROM {table_name}"
            else:
                return f"SELECT COUNT(*) as total_count FROM {table_name}"
        else:
            return f"SELECT COUNT(*) as total_count FROM {table_name}"
    
    def _sanitize_identifier(self, identifier: str) -> str:
        """清理标识符"""
        # 移除特殊字符，只保留字母、数字和下划线
        return re.sub(r'[^a-zA-Z0-9_]', '', identifier)
    
    def _is_valid_field_name(self, field_name: str) -> bool:
        """检查字段名是否有效"""
        if not field_name:
            return False
        # 检查是否只包含字母、数字和下划线
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', field_name))
    
    def _clean_field_names(self, fields: List[str]) -> List[str]:
        """清理字段名列表"""
        cleaned_fields = []
        for field in fields:
            if self._is_valid_field_name(field):
                cleaned_fields.append(field)
        return cleaned_fields
    
    def _validate_sql_syntax(self, sql: str) -> bool:
        """验证SQL语法"""
        if not sql:
            return False
        
        sql_upper = sql.upper()
        
        # 基本语法检查
        if not sql_upper.startswith('SELECT'):
            return False
        
        if 'FROM' not in sql_upper:
            return False
        
        # 检查FROM后面是否有表名
        if not re.search(r'FROM\s+\w+', sql, re.IGNORECASE):
            return False
        
        # 检查是否有明显的语法错误
        if 'SELECTSELECT' in sql_upper or 'FROMFROM' in sql_upper:
            return False
        
        return True
    
    def _fix_sql_syntax_errors(self, sql: str, table_name: str = "default_table") -> str:
        """修复SQL语法错误"""
        if not sql:
            return f"SELECT COUNT(*) as total_count FROM {table_name}"
        
        # 修复常见的AI生成错误
        sql = re.sub(r'SELECT\s+([^F]+)FROM', r'SELECT \1 FROM', sql, flags=re.IGNORECASE)
        sql = re.sub(r'SELECT\s+([^F]+)T\s+([^F]+)FROM', r'SELECT \1 FROM', sql, flags=re.IGNORECASE)
        sql = re.sub(r'SELECT\s+([^F]+)OUNT\s*\(\s*\*\s*\)', r'SELECT COUNT(*)', sql, flags=re.IGNORECASE)
        
        # 确保基本结构正确
        if not sql.upper().startswith('SELECT'):
            sql = f"SELECT {sql}"
        
        # 检查是否缺少表名
        if 'FROM' in sql.upper() and not re.search(r'FROM\s+\w+', sql, re.IGNORECASE):
            # 如果FROM后面没有表名，添加表名
            sql = re.sub(r'FROM\s*$', f'FROM {table_name}', sql, flags=re.IGNORECASE)
        elif 'FROM' not in sql.upper():
            sql = f"{sql} FROM {table_name}"
        
        return sql
    
    def _generate_fallback_sql(self, table_name: str = "default_table") -> str:
        """生成备用SQL"""
        return f"SELECT COUNT(*) as total_count FROM {table_name}"
    
    async def _self_validate_and_improve_sql(
        self, 
        sql: str, 
        data_source_id: str, 
        target_selection: Dict
    ) -> str:
        """SQL质量验证和自我改进 - 增强版本"""
        try:
            # 初始语法检查
            table_name = target_selection.get('table', 'default_table')
            if not self._validate_sql_syntax(sql):
                sql = self._fix_sql_syntax_errors(sql, table_name)
                if not self._validate_sql_syntax(sql):
                    return self._generate_fallback_sql(table_name)
            
            # 字段名验证
            table_name = target_selection.get('table', 'default_table')
            fields = target_selection.get('fields', [])
            
            # 清理字段名
            cleaned_fields = self._clean_field_names(fields)
            if cleaned_fields != fields:
                self.logger.info(f"字段名已清理: {fields} -> {cleaned_fields}")
            
            # 最终语法检查
            if not self._validate_sql_syntax(sql):
                return self._generate_fallback_sql(table_name)
            
            return sql
            
        except Exception as e:
            self.logger.error(f"SQL验证和改进失败: {e}")
            return self._generate_fallback_sql(target_selection.get('table', 'default_table'))
