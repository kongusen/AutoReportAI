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

from app.services.data.connectors.base_connector import BaseConnector
from app.services.data.connectors.doris_connector import DorisConnector, DorisConfig
from app.core.ai_service_factory import UserAIServiceFactory
from app.services.ai.core import PromptContextBuilder, AIServiceAdapter

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
            
            # 2. 执行AI语义分析（上下文工程构建提示）
            self.logger.info("🧠 使用 ai_agent 分析模式 + 上下文工程")
            if self.user_id:
                self.logger.info(f"使用用户特定AI服务进行分析: {self.user_id}")
            else:
                self.logger.info("使用系统默认AI服务进行分析")
            
            # 构建上下文与提示
            ctx_builder = PromptContextBuilder()
            ctx_builder.with_user(self.user_id or "system") 
            ds_name = data_source.get("name", "")
            table_count = len(enhanced_schema.get("tables", [])) if enhanced_schema else 0
            ctx_builder.with_data_source_summary(f"数据源 {ds_name}，包含 {table_count} 张表")
            # 加入部分 schema 亮点
            for table_name, details in list(enhanced_schema.get("table_details", {}).items())[:5]:
                columns = details.get("columns", [])
                sample_cols = ", ".join([c.get("name", "") for c in columns[:5]])
                ctx_builder.add_schema_highlight(f"{table_name}: {sample_cols}")

            ctx_builder.with_task_hint("占位符语义分析与SQL生成建议")
            ctx_builder.add_constraint("必须基于提供的真实表结构")
            ctx_builder.add_constraint("严格输出JSON，不要多余文本")

            user_prompt = (
                f"占位符: {placeholder_name}\n"
                f"类型: {placeholder_type or 'unknown'}\n"
            )
            built_prompt = ctx_builder.build_prompt(user_prompt)

            # 通过统一适配器调用
            ai = AIServiceAdapter(db_session=self.db_session, user_id=self.user_id)
            ai_resp = await ai.complete(
                prompt=built_prompt,
                task_type="placeholder_analysis",
                context="",
            )
            if ai_resp.success and ai_resp.text:
                # 回用现有解析逻辑
                semantic_analysis = await self._parse_ai_response_to_semantic(ai_resp.text, enhanced_schema)
            else:
                semantic_analysis = {"success": False, "error": "AI 调用失败"}
            
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
    
    async def _parse_ai_response_to_semantic(self, response_text: str, enhanced_schema: Dict[str, Any]) -> Dict[str, Any]:
        """将AI返回的文本解析为语义分析结构。

        兼容纯JSON、markdown代码块包裹JSON、以及文本中夹杂JSON的情况。
        """
        try:
            content = response_text or ""
            content = content.strip()

            # 1) 直接解析
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # 2) 尝试提取```json```代码块
                if "```json" in content:
                    start_marker = "```json"
                    end_marker = "```"
                    start_idx = content.find(start_marker)
                    if start_idx != -1:
                        start_idx += len(start_marker)
                        end_idx = content.find(end_marker, start_idx)
                        if end_idx != -1:
                            block = content[start_idx:end_idx].strip()
                            try:
                                data = json.loads(block)
                            except Exception:
                                data = None
                        else:
                            data = None
                    else:
                        data = None
                else:
                    data = None

                # 3) 从全文提取第一个JSON大括号片段
                if data is None:
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        try:
                            json_str = content[json_start:json_end]
                            data = json.loads(json_str)
                        except Exception:
                            data = None

            if not data:
                return {"success": False, "error": "无法解析AI响应为JSON"}

            # 兼容包含“分析结果”的结构
            analysis = data.get("分析结果", data)

            return {
                "success": True,
                "intent": analysis.get("intent", "statistical"),
                "data_operation": analysis.get("data_operation", "count"),
                "business_domain": analysis.get("business_domain", ""),
                "target_table": analysis.get("target_table", ""),
                "target_fields": analysis.get("target_fields", []),
                "target_metrics": analysis.get("target_metrics", []),
                "time_dimension": analysis.get("time_dimension"),
                "grouping_dimensions": analysis.get("grouping_dimensions", []),
                "filters": analysis.get("filters", []),
                "aggregations": analysis.get("aggregations", []),
                "reasoning": data.get("reasoning", analysis.get("reasoning", [])),
                "optimizations": analysis.get("optimizations", []),
                "confidence": analysis.get("confidence", 0.8),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_enhanced_schema(self, data_source: Dict[str, Any]) -> Dict[str, Any]:
        """从缓存中获取增强的数据源schema信息"""
        try:
            data_source_id = data_source.get("id")
            source_type = data_source.get("source_type")
            
            if not data_source_id or not self.db_session:
                self.logger.error("缺少数据源ID或数据库会话")
                return None
            
            # 使用SchemaQueryService获取缓存的表结构信息
            from app.services.data.schemas.schema_query_service import SchemaQueryService
            schema_service = SchemaQueryService(self.db_session)
            
            # 获取所有表结构
            table_schemas = schema_service.get_table_schemas(data_source_id)
            
            if not table_schemas:
                self.logger.warning(f"数据源 {data_source_id} 没有缓存的表结构信息，请先执行表结构发现")
                return None
            
            # 构建表结构详情
            table_details = {}
            tables = []
            
            for table_schema in table_schemas:
                table_name = table_schema.table_name
                tables.append(table_name)
                
                # 获取表的列信息
                columns = schema_service.get_table_columns(table_schema.id)
                column_details = []
                
                for column in columns:
                    column_info = {
                        "name": column.column_name,
                        "type": column.column_type,
                        "normalized_type": column.normalized_type if column.normalized_type else "unknown",
                        "nullable": column.is_nullable,
                        "primary_key": column.is_primary_key,
                        "business_name": column.business_name,  # 业务中文名
                        "business_description": column.business_description,  # 业务描述
                        "semantic_category": column.semantic_category,  # 语义分类
                        "sample_values": column.sample_values,  # 样本值
                        "data_patterns": column.data_patterns  # 数据模式
                    }
                    column_details.append(column_info)
                
                table_details[table_name] = {
                    "columns": column_details,
                    "business_category": table_schema.business_category,  # 表的业务分类
                    "data_freshness": table_schema.data_freshness,  # 数据新鲜度
                    "update_frequency": table_schema.update_frequency,  # 更新频率
                    "estimated_row_count": table_schema.estimated_row_count,  # 预估行数
                    "data_quality_score": table_schema.data_quality_score,  # 数据质量评分
                    "table_size_bytes": table_schema.table_size_bytes  # 表大小
                }
            
            return {
                "source_type": source_type,
                "tables": tables,
                "table_details": table_details,
                "total_tables": len(tables),
                "total_columns": sum(len(details["columns"]) for details in table_details.values()),
                "schema_metadata": {
                    "business_categories": list(set([t.business_category for t in table_schemas if t.business_category])),
                    "semantic_categories": schema_service.get_semantic_categories(data_source_id),
                    "data_quality_avg": sum([t.data_quality_score or 0 for t in table_schemas]) / len(table_schemas) if table_schemas else 0
                }
            }
                
        except Exception as e:
            self.logger.error(f"从缓存获取增强schema失败: {e}")
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
                    
                    # 尝试从响应中提取JSON（处理markdown包装）
                    # 先尝试移除markdown代码块标记
                    json_content = response
                    if "```json" in response:
                        # 提取markdown代码块中的JSON
                        start_marker = "```json"
                        end_marker = "```"
                        start_idx = response.find(start_marker)
                        if start_idx != -1:
                            start_idx += len(start_marker)
                            end_idx = response.find(end_marker, start_idx)
                            if end_idx != -1:
                                json_content = response[start_idx:end_idx].strip()
                    
                    # 现在尝试解析清理后的JSON
                    json_start = json_content.find('{')
                    json_end = json_content.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        try:
                            json_str = json_content[json_start:json_end]
                            ai_result = {"success": True, "data": json.loads(json_str)}
                            self.logger.info("从响应中提取JSON成功")
                        except json.JSONDecodeError as e2:
                            self.logger.error(f"提取的JSON仍然无效: {e2}")
                            self.logger.error(f"尝试解析的JSON: {json_str[:200]}...")
                            ai_result = {"success": True, "data": {"intent": "statistical", "data_operation": "count", "reasoning": [response]}}
                    else:
                        ai_result = {"success": True, "data": {"intent": "statistical", "data_operation": "count", "reasoning": [response]}}
            else:
                ai_result = {"success": True, "data": {"intent": "statistical", "data_operation": "count", "reasoning": ["AI分析失败"]}}
            
            if ai_result.get("success"):
                analysis_data = ai_result.get("data", {})
                
                # 从"分析结果"中提取信息，如果不存在则从根级别提取
                analysis_result = analysis_data.get("分析结果", analysis_data)
                
                return {
                    "success": True,
                    "intent": analysis_result.get("intent", "statistical"),
                    "data_operation": analysis_result.get("data_operation", "count"),
                    "business_domain": analysis_result.get("business_domain", ""),
                    "target_table": analysis_result.get("target_table", ""),  # 添加目标表
                    "target_fields": analysis_result.get("target_fields", []),  # 添加目标字段
                    "target_metrics": analysis_result.get("target_metrics", []),
                    "time_dimension": analysis_result.get("time_dimension"),
                    "grouping_dimensions": analysis_result.get("grouping_dimensions", []),
                    "filters": analysis_result.get("filters", []),
                    "aggregations": analysis_result.get("aggregations", []),
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
        """构建AI分析提示 - 基于真实缓存schema的多轮思考分析"""
        placeholder_name = context.get("placeholder_name", "")
        placeholder_type = context.get("placeholder_type", "")
        data_source = context.get("data_source", {})
        
        # 基于真实缓存的表结构构建详细信息
        tables_info = []
        business_mappings = []
        
        for table_name, table_data in enhanced_schema.get("table_details", {}).items():
            columns = table_data.get("columns", [])
            business_category = table_data.get("business_category", "")
            estimated_rows = table_data.get("estimated_row_count", 0)
            
            # 构建列信息，包含业务含义
            column_descriptions = []
            for col in columns[:15]:  # 限制列数避免提示词过长
                col_desc = col.get("name", "")
                if col.get("business_name"):
                    col_desc += f" ({col['business_name']})"
                if col.get("semantic_category"):
                    col_desc += f" [{col['semantic_category']}]"
                column_descriptions.append(col_desc)
            
            table_info = f"""表名: {table_name}
业务分类: {business_category or '未分类'}
记录数: 约{estimated_rows:,}条
关键字段: {', '.join(column_descriptions)}"""
            tables_info.append(table_info)
            
            # 构建业务映射关系
            if business_category:
                business_mappings.append(f"- {business_category}相关数据 → {table_name}表")
            
            # 基于列的业务名称和语义分类构建映射
            for col in columns:
                if col.get("business_name") or col.get("semantic_category"):
                    business_name = col.get("business_name", col.get("name", ""))
                    semantic_cat = col.get("semantic_category", "")
                    if business_name:
                        business_mappings.append(f"- '{business_name}'{f'({semantic_cat})' if semantic_cat else ''} → {table_name}.{col.get('name', '')}")
        
        tables_text = "\n\n".join(tables_info)
        business_mappings_text = "\n".join(list(set(business_mappings))[:20])  # 去重并限制数量
        
        # 获取业务领域信息
        schema_metadata = enhanced_schema.get("schema_metadata", {})
        business_categories = schema_metadata.get("business_categories", [])
        semantic_categories = schema_metadata.get("semantic_categories", [])
        
        prompt = f"""
你是专业的数据分析AI，需要分析中文占位符的业务需求并选择最合适的数据表。请进行多轮思考分析。

【数据源概况】
- 数据源: {data_source.get('name', 'unknown')}
- 业务领域: {', '.join(business_categories) if business_categories else '通用业务'}
- 语义分类: {', '.join(semantic_categories[:10]) if semantic_categories else '未分类'}
- 表总数: {enhanced_schema.get('total_tables', 0)}
- 字段总数: {enhanced_schema.get('total_columns', 0)}

【当前分析任务】
占位符: {placeholder_name}
类型: {placeholder_type}

【可用数据表详情】
{tables_text}

【业务语义映射】
{business_mappings_text}

【分析要求】
请按以下步骤进行多轮思考：

1. 【语义理解】- 分析占位符的中文含义，识别关键业务概念
2. 【表选择】- 基于真实表结构和业务分类，选择最合适的数据表
3. 【字段映射】- 根据列的业务名称和语义分类，确定目标字段
4. 【操作确定】- 确定需要的数据操作（统计、去重、聚合等）
5. 【结果验证】- 验证选择的表和字段是否能满足业务需求

请严格按以下JSON格式返回分析结果：

{{
    "思考过程": {{
        "语义理解": "对占位符中文含义的理解",
        "关键概念": ["识别出的业务概念1", "概念2"],
        "表选择推理": "为什么选择这个表的详细推理",
        "字段匹配": "字段选择的依据",
        "操作确定": "数据操作类型的确定理由"
    }},
    "分析结果": {{
        "intent": "statistical/analytical/reporting",
        "data_operation": "count/sum/avg/count_distinct/group_by等",
        "business_domain": "业务领域",
        "target_table": "选定的目标表名",
        "target_fields": ["字段1", "字段2"],
        "target_metrics": ["指标1", "指标2"],
        "time_dimension": "时间维度字段或null",
        "grouping_dimensions": ["分组字段"],
        "filters": ["过滤条件"],
        "aggregations": ["聚合操作"],
        "confidence": 0.0-1.0,
        "reasoning": ["详细推理步骤"],
        "optimizations": ["性能优化建议"]
    }}
}}

【关键要求】
1. 仔细理解中文占位符的业务含义
2. 选择最符合业务逻辑的数据表  
3. 只返回JSON，不要任何其他文本
4. confidence值应反映分析的确定程度
5. 特别注意"去重"、"同比"、"占比"等统计需求的准确理解
"""
        return prompt
    
    
    async def _perform_intelligent_target_selection(
        self, 
        semantic_analysis: Dict, 
        enhanced_schema: Dict
    ) -> Dict[str, Any]:
        """基于AI分析结果执行目标选择"""
        try:
            # 从AI分析结果中获取目标表
            if "分析结果" in semantic_analysis:
                analysis_result = semantic_analysis["分析结果"]
                target_table = analysis_result.get("target_table")
                target_fields = analysis_result.get("target_fields", [])
            else:
                # 兼容老格式
                target_table = semantic_analysis.get("target_table")
                target_fields = semantic_analysis.get("target_fields", [])
            
            if target_table:
                # 验证目标表是否存在
                if target_table in enhanced_schema.get("table_details", {}):
                    self.logger.info(f"✅ AI选择的目标表: {target_table}")
                    
                    return {
                        "success": True,
                        "table": target_table,
                        "fields": target_fields,
                        "field_mapping": {},
                        "relevance_score": semantic_analysis.get("confidence", 0.8),
                        "alternative_tables": []
                    }
                else:
                    self.logger.warning(f"AI选择的表 {target_table} 不存在，使用第一个可用表")
            
            # 如果AI没有指定表或表不存在，使用第一个可用表
            available_tables = list(enhanced_schema.get("table_details", {}).keys())
            if available_tables:
                fallback_table = available_tables[0]
                self.logger.info(f"使用备用表: {fallback_table}")
                
                return {
                    "success": True,
                    "table": fallback_table,
                    "fields": target_fields,
                    "field_mapping": {},
                    "relevance_score": 0.5,
                    "alternative_tables": available_tables[1:3]
                }
            else:
                return {
                    "success": False,
                    "error": "没有可用的数据表"
                }
                
        except Exception as e:
            self.logger.error(f"目标选择失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    
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
        
        # 获取表的详细结构信息
        table_details = enhanced_schema.get('table_details', {}).get(table_name, {})
        columns = table_details.get('columns', [])
        
        # 构建列信息
        column_info = []
        for col in columns[:10]:  # 限制列数避免prompt过长
            col_name = col.get('name', '')
            col_type = col.get('type', '')
            business_name = col.get('business_name', '')
            column_info.append(f"{col_name} ({col_type}){f' - {business_name}' if business_name else ''}")
        
        data_operation = semantic_analysis.get('data_operation', '')
        time_dimension = semantic_analysis.get('time_dimension')
        grouping_dims = semantic_analysis.get('grouping_dimensions', [])
        filters = semantic_analysis.get('filters', [])
        aggregations = semantic_analysis.get('aggregations', [])
        
        prompt = f"""
你是一个SQL专家。请根据业务需求生成精确的SQL查询语句。

【业务需求分析】
- 业务意图: {semantic_analysis.get('intent', '')}
- 数据操作类型: {data_operation}
- 业务领域: {semantic_analysis.get('business_domain', '')}
- 目标指标: {semantic_analysis.get('target_metrics', [])}

【目标表结构】
表名: {table_name}
可用字段: {chr(10).join(column_info)}

【查询要求】
- 时间维度字段: {time_dimension or '无'}
- 分组维度: {grouping_dims}
- 过滤条件: {filters}
- 聚合函数: {aggregations}

【特殊业务逻辑处理】
根据data_operation类型生成相应SQL:
- count: 统计总数
- count_distinct: 去重统计
- compare_yoy: 同比对比(需要当前期间和去年同期数据)
- percentage: 计算占比(需要子查询或分组)
- group_by: 分组统计
- time_series: 时间序列分析

请严格按照以下要求生成SQL:

1. 必须是完整、语法正确的SELECT语句
2. 根据业务需求选择合适的字段和聚合函数  
3. 如果涉及时间对比，需要包含时间范围条件
4. 如果涉及占比计算，需要使用子查询或窗口函数
5. 字段名必须来自上面提供的表结构，不要使用虚构的字段名
6. 对于"去重"需求，使用COUNT(DISTINCT field_name)
7. 对于"同比"需求，包含当前期间和去年同期的子查询对比
8. 只返回一条完整的SQL语句，不要解释文本

注意：请仔细检查字段名的正确性和SQL语法完整性。

生成的SQL:
"""
        return prompt
    
    def _extract_sql_from_response(self, response: str) -> str:
        """从AI响应中提取SQL"""
        if not response:
            return None
            
        # 清理响应内容
        response = response.strip()
        
        # 1. 如果响应本身就是SQL语句
        if response.upper().startswith('SELECT'):
            return response
        
        # 2. 查找标记后的SQL
        markers = ['SQL:', 'sql:', '```sql', '```', 'SELECT']
        for marker in markers:
            if marker in response:
                start_idx = response.find(marker)
                if start_idx != -1:
                    sql_content = response[start_idx + len(marker):].strip()
                    # 移除结尾的代码块标记
                    if sql_content.endswith('```'):
                        sql_content = sql_content[:-3].strip()
                    
                    # 如果找到的内容以SELECT开始，返回它
                    if sql_content.upper().startswith('SELECT'):
                        return sql_content
        
        # 3. 使用正则表达式查找SQL模式
        sql_patterns = [
            # 完整SQL模式（包含子查询）
            r'SELECT\s+(?:(?:(?!SELECT|FROM).)*(?:\([^)]*\))*)*\s+FROM\s+\w+(?:\s+(?:WHERE|GROUP\s+BY|HAVING|ORDER\s+BY|LIMIT|UNION)(?:(?!SELECT|$).)*)*',
            # 简单SQL模式  
            r'SELECT\s+.*?FROM\s+\w+(?:\s+.*?)?(?:;|$)',
        ]
        
        for pattern in sql_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                sql = match.group(0).strip()
                # 移除末尾的分号和多余空格
                if sql.endswith(';'):
                    sql = sql[:-1].strip()
                return sql
        
        return None
    
    def _generate_sql_by_template(
        self, 
        intent: str, 
        operation: str, 
        table_name: str, 
        fields: List[str], 
        field_mapping: Dict
    ) -> str:
        """基于模板生成SQL - 增强版本支持复杂业务逻辑"""
        
        # 根据数据操作类型生成相应的SQL
        if operation == "count":
            return f"SELECT COUNT(*) as total_count FROM {table_name}"
        elif operation == "count_distinct":
            # 去重统计
            if fields:
                field = fields[0]
                return f"SELECT COUNT(DISTINCT {field}) as distinct_count FROM {table_name}"
            return f"SELECT COUNT(DISTINCT id) as distinct_count FROM {table_name}"
        elif operation == "compare_yoy":
            # 同比对比 - 简化版本，需要时间字段
            time_field = "dt"  # 假设时间字段为dt
            return f"""SELECT 
    COUNT(*) as current_count,
    (SELECT COUNT(*) FROM {table_name} WHERE {time_field} LIKE CONCAT(YEAR(CURDATE())-1, '%')) as last_year_count,
    ROUND((COUNT(*) - (SELECT COUNT(*) FROM {table_name} WHERE {time_field} LIKE CONCAT(YEAR(CURDATE())-1, '%'))) / 
          (SELECT COUNT(*) FROM {table_name} WHERE {time_field} LIKE CONCAT(YEAR(CURDATE())-1, '%')) * 100, 2) as yoy_change_pct
FROM {table_name} 
WHERE {time_field} LIKE CONCAT(YEAR(CURDATE()), '%')"""
        elif operation == "percentage":
            # 占比计算
            if fields and len(fields) >= 2:
                numerator_field = fields[0]
                return f"""SELECT 
    {numerator_field},
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {table_name}), 2) as percentage
FROM {table_name}
GROUP BY {numerator_field}"""
            return f"""SELECT 
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {table_name}), 2) as percentage
FROM {table_name}"""
        elif operation == "group_by":
            # 分组统计
            if fields:
                group_field = fields[0]
                return f"""SELECT 
    {group_field},
    COUNT(*) as count
FROM {table_name}
GROUP BY {group_field}
ORDER BY count DESC"""
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
        """修复SQL语法错误 - 增强版本"""
        if not sql:
            return f"SELECT COUNT(*) as total_count FROM {table_name}"
        
        original_sql = sql
        
        # 检查是否是严重损坏的SQL（包含明显的语法错误）
        if self._is_severely_corrupted_sql(sql):
            self.logger.warning(f"检测到严重损坏的SQL，使用fallback: {sql[:100]}...")
            return f"SELECT COUNT(*) as total_count FROM {table_name}"
        
        # 修复常见的AI生成错误
        sql = re.sub(r'SELECT\s+([^F]+)FROM', r'SELECT \1 FROM', sql, flags=re.IGNORECASE)
        sql = re.sub(r'SELECT\s+([^F]+)T\s+([^F]+)FROM', r'SELECT \1 FROM', sql, flags=re.IGNORECASE)
        sql = re.sub(r'SELECT\s+([^F]+)OUNT\s*\(\s*\*\s*\)', r'SELECT COUNT(*)', sql, flags=re.IGNORECASE)
        
        # 修复字段名拼接错误
        sql = re.sub(r'SELEid', 'SELECT id', sql, flags=re.IGNORECASE)
        sql = re.sub(r's_idT\s+id', 's_id', sql, flags=re.IGNORECASE)
        sql = re.sub(r's_idOUNT', 'COUNT', sql, flags=re.IGNORECASE)
        
        # 确保基本结构正确
        if not sql.upper().startswith('SELECT'):
            sql = f"SELECT {sql}"
        
        # 检查是否缺少表名
        if 'FROM' in sql.upper() and not re.search(r'FROM\s+\w+', sql, re.IGNORECASE):
            # 如果FROM后面没有表名，添加表名
            sql = re.sub(r'FROM\s*$', f'FROM {table_name}', sql, flags=re.IGNORECASE)
        elif 'FROM' not in sql.upper():
            sql = f"{sql} FROM {table_name}"
        
        # 最后验证修复结果
        if not self._validate_sql_syntax(sql):
            self.logger.warning(f"SQL修复失败，使用fallback。原始: {original_sql[:50]}...")
            return f"SELECT COUNT(*) as total_count FROM {table_name}"
        
        return sql
    
    def _is_severely_corrupted_sql(self, sql: str) -> bool:
        """检查SQL是否严重损坏"""
        if not sql:
            return True
            
        # 检查明显的语法错误模式（只检查严重的结构性错误）
        corruption_patterns = [
            r'SELEid',  # SELECT被破坏
            r's_idT\s+id',  # 字段名拼接错误  
            r's_idOUNT',  # COUNT被破坏
            r'SELECT\s+[^F]*T\s+[^F]*COUNT',  # 字段名和COUNT混杂
            r'SELECTSELECT',  # 重复的SELECT
            r'FROMFROM',  # 重复的FROM
        ]
        
        for pattern in corruption_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                return True
        
        # 检查基本结构完整性
        sql_upper = sql.upper()
        if 'SELECT' not in sql_upper or 'FROM' not in sql_upper:
            return True
            
        return False
    
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
