"""
Cached Agent Orchestrator - V2 (基于统一上下文系统)

现在使用新的统一上下文系统，提供向后兼容性的同时
集成了智能上下文管理、渐进式优化和学习功能
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

# 新的统一上下文编排器
from .unified_context_orchestrator import get_unified_context_orchestrator, UnifiedContextOrchestrator

# 保留必要的传统导入以支持回退
from app.services.domain.placeholder.unified_cache_service import UnifiedCacheService
from app.services.domain.placeholder.execution_service import DataExecutionService
from app.services.domain.placeholder.models import (
    PlaceholderRequest, AgentExecutionResult, ResultSource
)
from app.services.data.connectors.connector_factory import create_connector
from app.services.domain.template.enhanced_template_parser import EnhancedTemplateParser
from app import crud, schemas

logger = logging.getLogger(__name__)


class CachedAgentOrchestrator:
    """
    缓存代理编排器 - V2版本 (基于统一上下文系统)
    
    现在委托给统一上下文编排器，提供向后兼容性
    同时集成了智能上下文管理、渐进式优化和学习功能
    """
    
    def __init__(
        self, 
        db: Session, 
        user_id: str = None,
        use_unified_system: bool = True,
        integration_mode: str = "intelligent"
    ):
        self.db = db
        self.user_id = user_id
        self.use_unified_system = use_unified_system
        self.integration_mode = integration_mode
        
        if use_unified_system:
            # 使用新的统一上下文编排器
            self.unified_orchestrator = get_unified_context_orchestrator(
                db=db,
                user_id=user_id,
                integration_mode=integration_mode,
                enable_caching=True
            )
            logger.info(f"CachedAgentOrchestrator V2 初始化，使用统一上下文系统，模式: {integration_mode}")
        else:
            # 回退到传统实现
            logger.warning("CachedAgentOrchestrator 使用传统模式 - 建议升级到统一上下文系统")
            self._init_traditional_services()
    
    def _init_traditional_services(self):
        """初始化传统服务（回退模式）"""
        self.cache_service = UnifiedCacheService(self.db)
        # Import here to avoid circular dependency
        from app.services.iaop.agents.specialized.sql_generation_agent import SQLGenerationAgent as PlaceholderSQLAnalyzer
        self.agent_service = PlaceholderSQLAnalyzer(db_session=self.db, user_id=self.user_id or "system")
        self.execution_service = DataExecutionService(self.db)
        # 直接使用IAOP专业化代理
        from app.services.iaop.agents.specialized.placeholder_parser_agent import PlaceholderParserAgent as PlaceholderSQLAgent
        self.ai_agent = PlaceholderSQLAgent()
        
        # 初始化模板解析器
        self.template_parser = EnhancedTemplateParser(db)
        
        # 连接器工厂函数可直接使用
        
        self.logger = logging.getLogger(__name__)
    
    async def _execute_phase1_analysis(
        self, 
        template_id: str, 
        data_source_id: str, 
        force_reanalyze: bool = False,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行阶段1：模板分析和Agent处理 - V2版本
        
        现在委托给统一上下文编排器处理，提供智能上下文管理
        """
        if self.use_unified_system:
            logger.info(f"使用统一上下文系统进行阶段1分析 - 模板: {template_id}")
            
            # 从执行上下文中提取目标期望和优化级别
            target_expectations = None
            optimization_level = self.integration_mode
            
            if execution_context:
                target_expectations = execution_context.get('target_expectations')
                optimization_level = execution_context.get('optimization_level', optimization_level)
            
            # 委托给统一上下文编排器
            return await self.unified_orchestrator.execute_enhanced_template_analysis(
                template_id=template_id,
                data_source_id=data_source_id,
                force_reanalyze=force_reanalyze,
                optimization_level=optimization_level,
                target_expectations=target_expectations
            )
        else:
            # 回退到传统实现
            return await self._execute_traditional_phase1_analysis(
                template_id, data_source_id, force_reanalyze, execution_context
            )
    
    async def _execute_traditional_phase1_analysis(
        self,
        template_id: str, 
        data_source_id: str, 
        force_reanalyze: bool = False,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        传统的阶段1分析实现（回退模式）
        """
        try:
            logger.info(f"使用传统模式进行阶段1分析 - 模板: {template_id}, 数据源: {data_source_id}")
            
            # 获取模板和数据源信息
            template = crud.template.get(self.db, id=template_id)
            data_source = crud.data_source.get(self.db, id=data_source_id)
            
            if not template:
                return {
                    "success": False,
                    "error": f"模板不存在: {template_id}",
                    "analyzed_placeholders": 0
                }
            
            if not data_source:
                return {
                    "success": False,
                    "error": f"数据源不存在: {data_source_id}",
                    "analyzed_placeholders": 0
                }
            
            # 获取需要Agent分析的占位符
            if force_reanalyze:
                # 如果强制重新分析，获取所有占位符配置
                placeholders = await self.template_parser.get_template_placeholder_configs(template_id)
            else:
                # 否则只获取未分析的占位符
                placeholders = await self.template_parser.get_unanalyzed_placeholders(template_id)
            if not placeholders:
                self.logger.info("没有需要Agent分析的占位符")
                return {
                    "success": True,
                    "message": "无需Agent分析",
                    "analyzed_placeholders": 0,
                    "cache_hit_rate": 1.0
                }
            
            # 分析每个占位符
            analyzed_count = 0
            cache_hits = 0
            total_placeholders = len(placeholders)
            
            for placeholder in placeholders:
                try:
                    # 创建占位符请求
                    request = PlaceholderRequest(
                        placeholder_id=placeholder.get("id", placeholder.get("name", "unknown")),
                        placeholder_name=placeholder.get("name", placeholder.get("placeholder_name", "unknown")),
                        placeholder_type=placeholder.get("type", placeholder.get("placeholder_type", "text")),
                        data_source_id=data_source_id,
                        user_id=self.user_id,
                        force_reanalyze=force_reanalyze,
                        metadata={
                            "template_id": template_id,
                            "execution_context": execution_context or {}
                        }
                    )
                    
                    # 检查缓存
                    if not force_reanalyze:
                        cache_entry = await self.cache_service.get_result(request)
                        if cache_entry:
                            cache_hits += 1
                            analyzed_count += 1
                            continue
                    
                    # 执行Agent分析
                    result = await self.agent_service.analyze_and_execute(request)
                    
                    if result.success:
                        # 保存到缓存
                        await self.cache_service.save_result(request, result)
                        analyzed_count += 1
                    else:
                        self.logger.warning(f"占位符分析失败: {placeholder.get('name')}, 错误: {result.error_message}")
                
                except Exception as e:
                    self.logger.error(f"处理占位符失败: {placeholder.get('name')}, 错误: {e}")
                    continue
            
            cache_hit_rate = cache_hits / total_placeholders if total_placeholders > 0 else 0
            
            self.logger.info(f"阶段1分析完成 - 成功: {analyzed_count}/{total_placeholders}, 缓存命中率: {cache_hit_rate:.1%}")
            
            return {
                "success": True,
                "message": f"成功分析 {analyzed_count} 个占位符",
                "analyzed_placeholders": analyzed_count,
                "total_placeholders": total_placeholders,
                "cache_hit_rate": cache_hit_rate
            }
            
        except Exception as e:
            self.logger.error(f"阶段1分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "analyzed_placeholders": 0
            }
    
    async def _execute_phase2_extraction_and_generation(
        self,
        template_id: str,
        data_source_id: str,
        user_id: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行阶段2：数据提取和报告生成
        
        Args:
            template_id: 模板ID
            data_source_id: 数据源ID
            user_id: 用户ID
            execution_context: 执行上下文
            
        Returns:
            包含提取结果的字典
        """
        try:
            self.logger.info(f"开始阶段2提取 - 模板: {template_id}, 数据源: {data_source_id}")
            
            # 获取所有占位符值
            placeholder_values = {}
            processed_placeholders = 0
            cache_hits = 0
            
            # 获取模板的所有占位符配置
            placeholders = await self.template_parser.get_template_placeholder_configs(template_id)
            total_placeholders = len(placeholders)
            
            if not placeholders:
                return {
                    "success": True,
                    "message": "模板中没有占位符",
                    "placeholder_values": {},
                    "processed_placeholders": 0,
                    "total_placeholders": 0,
                    "cache_hit_rate": 1.0
                }
            
            # 处理每个占位符
            for placeholder in placeholders:
                try:
                    placeholder_name = placeholder.get("name")
                    
                    # 创建请求
                    request = PlaceholderRequest(
                        placeholder_id=placeholder.get("id", placeholder_name),
                        placeholder_name=placeholder_name,
                        placeholder_type=placeholder.get("type", "unknown"),
                        data_source_id=data_source_id,
                        user_id=user_id,
                        metadata={
                            "template_id": template_id,
                            "execution_context": execution_context or {}
                        }
                    )
                    
                    # 尝试从缓存获取
                    cache_entry = await self.cache_service.get_result(request)
                    
                    if cache_entry and cache_entry.value:
                        # 使用统一缓存结果
                        cache_value = cache_entry.value
                        if isinstance(cache_value, dict):
                            # 新的缓存格式
                            placeholder_values[placeholder_name] = {
                                'value': cache_value.get('value', ''),
                                'raw_data': cache_value.get('raw_data', cache_value.get('value', '')),
                                'type': 'cached',
                                'source': 'cache_hit',
                                'confidence': cache_value.get('confidence', cache_entry.confidence)
                            }
                        else:
                            # 向后兼容的旧格式
                            placeholder_values[placeholder_name] = {
                                'value': cache_entry.value,
                                'raw_data': cache_entry.metadata.get('raw_data', cache_entry.value),
                                'type': 'cached',
                                'source': 'cache_hit',
                                'confidence': cache_entry.confidence
                            }
                        cache_hits += 1
                        processed_placeholders += 1
                    else:
                        # 执行新的分析和提取
                        try:
                            # 1. 先获取或生成SQL
                            analysis_result = await self.agent_service.analyze_and_execute(request)
                            
                            if analysis_result.success and analysis_result.raw_data:
                                # 如果Agent返回的是SQL，执行它
                                sql_query = analysis_result.raw_data
                                self.logger.info(f"执行SQL查询: {placeholder_name} -> {sql_query[:100]}...")
                                
                                # 2. 执行SQL查询获取真实数据
                                execution_result = await self.execution_service.execute_sql(data_source_id, sql_query)
                                
                                if execution_result.success:
                                    # 查询成功，使用真实数据
                                    placeholder_values[placeholder_name] = {
                                        "value": execution_result.formatted_value,
                                        "raw_data": execution_result.raw_data,
                                        "type": "data",
                                        "source": "sql_query",
                                        "sql": sql_query
                                    }
                                    self.logger.info(f"SQL查询成功: {placeholder_name} = {execution_result.formatted_value}")
                                    
                                    # 创建包含实际结果的缓存条目，确保数据可序列化
                                    serializable_raw_data = self._make_serializable(execution_result.raw_data)
                                    
                                    cache_result = AgentExecutionResult(
                                        success=True,
                                        formatted_value=execution_result.formatted_value,
                                        raw_data=serializable_raw_data,  # 保存可序列化的查询结果
                                        confidence=execution_result.confidence if hasattr(execution_result, 'confidence') else 0.9,
                                        execution_time_ms=execution_result.execution_time_ms if hasattr(execution_result, 'execution_time_ms') else 0,
                                        metadata={
                                            "sql_query": sql_query,  # SQL作为元数据保存
                                            "execution_source": "sql_execution",
                                            "row_count": getattr(execution_result, 'row_count', 0)
                                        }
                                    )
                                    # 保存实际查询结果到缓存
                                    await self.cache_service.save_result(request, cache_result)
                                else:
                                    # SQL执行失败，尝试提供智能默认值
                                    default_value = self._get_intelligent_default_value(placeholder_name, execution_result.error_message)
                                    
                                    if default_value:
                                        # 使用智能默认值
                                        placeholder_values[placeholder_name] = {
                                            "value": default_value,
                                            "raw_data": None,
                                            "type": "default",
                                            "source": "intelligent_fallback",
                                            "sql": sql_query,
                                            "note": f"数据源连接失败，使用默认值: {default_value}"
                                        }
                                        self.logger.warning(f"SQL查询失败，使用默认值: {placeholder_name} -> {default_value} (原因: {execution_result.error_message})")
                                        
                                        # 缓存默认值结果
                                        cache_result = AgentExecutionResult(
                                            success=True,  # 标记为成功，因为我们有默认值
                                            formatted_value=default_value,
                                            raw_data=None,
                                            confidence=0.3,  # 低置信度
                                            metadata={
                                                "sql_query": sql_query, 
                                                "execution_source": "intelligent_fallback",
                                                "original_error": execution_result.error_message
                                            }
                                        )
                                        await self.cache_service.save_result(request, cache_result)
                                    else:
                                        # 无法提供默认值，返回错误信息
                                        error_info = f"{{错误信息：{execution_result.error_message}}}"
                                        placeholder_values[placeholder_name] = {
                                            "value": error_info,
                                            "raw_data": None,
                                            "type": "error",
                                            "source": "sql_error",
                                            "sql": sql_query,
                                            "error": execution_result.error_message
                                        }
                                        self.logger.warning(f"SQL查询失败且无默认值: {placeholder_name} -> {execution_result.error_message}")
                                        
                                        # 保存错误结果到缓存
                                        cache_result = AgentExecutionResult(
                                            success=False,
                                            formatted_value=error_info,
                                            raw_data=None,
                                            error_message=execution_result.error_message,
                                            metadata={"sql_query": sql_query, "execution_source": "sql_execution"}
                                        )
                                        await self.cache_service.save_result(request, cache_result)
                            else:
                                # Agent分析失败，返回错误信息
                                error_info = f"{{错误信息：Agent分析失败 - {analysis_result.error_message or 'Unknown error'}}}"
                                placeholder_values[placeholder_name] = {
                                    "value": error_info,
                                    "raw_data": None,
                                    "type": "error",
                                    "source": "agent_error",
                                    "error": analysis_result.error_message or "Agent分析失败"
                                }
                                self.logger.warning(f"Agent分析失败: {placeholder_name} -> {analysis_result.error_message}")
                        
                        except Exception as e:
                            # 异常情况，返回错误信息
                            error_info = f"{{错误信息：执行异常 - {str(e)}}}"
                            placeholder_values[placeholder_name] = {
                                "value": error_info,
                                "raw_data": None,
                                "type": "error",
                                "source": "exception",
                                "error": str(e)
                            }
                            self.logger.error(f"占位符处理异常: {placeholder_name} -> {str(e)}")
                        
                        processed_placeholders += 1
                
                except Exception as e:
                    self.logger.warning(f"处理占位符失败: {placeholder.get('name')}, 错误: {e}")
                    continue
            
            cache_hit_rate = cache_hits / total_placeholders if total_placeholders > 0 else 0
            
            # 生成处理后的内容（用于后续报告生成）
            processed_content = f"成功处理 {processed_placeholders}/{total_placeholders} 个占位符"
            
            self.logger.info(f"阶段2提取完成 - 处理: {processed_placeholders}/{total_placeholders}, 缓存命中率: {cache_hit_rate:.1%}")
            
            return {
                "success": True,
                "message": f"成功提取 {processed_placeholders} 个占位符的数据",
                "placeholder_values": placeholder_values,
                "processed_placeholders": processed_placeholders,
                "total_placeholders": total_placeholders,
                "cache_hit_rate": cache_hit_rate,
                "processed_content": processed_content
            }
            
        except Exception as e:
            self.logger.error(f"阶段2提取失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "placeholder_values": {},
                "processed_placeholders": 0,
                "total_placeholders": 0,
                "cache_hit_rate": 0
            }
    
    async def execute(self, agent_input: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        通用执行方法（向后兼容）
        
        Args:
            agent_input: Agent输入参数
            context: 执行上下文
            
        Returns:
            执行结果字典
        """
        try:
            template_id = agent_input.get("template_id") or context.get("template_id")
            data_source_id = agent_input.get("data_source_id") or context.get("data_source_id")
            
            if not template_id or not data_source_id:
                return {
                    "success": False,
                    "error": "缺少必要的template_id或data_source_id参数"
                }
            
            # 执行完整的两阶段流程
            phase1_result = await self._execute_phase1_analysis(
                template_id, data_source_id, context.get("force_reanalyze", False), context
            )
            
            if not phase1_result.get("success"):
                return phase1_result
            
            phase2_result = await self._execute_phase2_extraction_and_generation(
                template_id, data_source_id, self.user_id, context
            )
            
            return {
                "success": phase2_result.get("success", False),
                "data": {
                    "results": {
                        "fetch_data": {
                            "success": phase2_result.get("success", False),
                            "data": {
                                "etl_instruction": "SELECT * FROM processed_placeholders",
                                "placeholder_values": phase2_result.get("placeholder_values", {}),
                                "processed_content": phase2_result.get("processed_content", "")
                            }
                        }
                    },
                    "phase1_result": phase1_result,
                    "phase2_result": phase2_result
                }
            }
            
        except Exception as e:
            self.logger.error(f"执行失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_intelligent_default_value(self, placeholder_name: str, error_message: str) -> Optional[str]:
        """根据占位符名称和错误类型提供智能默认值"""
        try:
            placeholder_lower = placeholder_name.lower()
            
            # 根据占位符类型提供默认值
            if "地区名称" in placeholder_name or "区域" in placeholder_name:
                return "云南省"
            elif "统计开始日期" in placeholder_name or "开始日期" in placeholder_name:
                from datetime import datetime
                current_date = datetime.now()
                return f"{current_date.year}-{current_date.month:02d}-01"
            elif "统计结束日期" in placeholder_name or "结束日期" in placeholder_name:
                from datetime import datetime
                current_date = datetime.now()
                return f"{current_date.year}-{current_date.month:02d}-{current_date.day:02d}"
            elif "报告年份" in placeholder_name or "年份" in placeholder_name:
                from datetime import datetime
                return str(datetime.now().year)
            elif "件数" in placeholder_name or "数量" in placeholder_name:
                if "投诉" in placeholder_name:
                    return "0"  # 投诉件数默认为0
            elif "占比" in placeholder_name or "百分比" in placeholder_name or "%" in placeholder_name:
                return "0.0%"
            elif "时长" in placeholder_name or "天数" in placeholder_name:
                return "0"
            elif "变化方向" in placeholder_name:
                return "持平"
            elif "同比" in placeholder_name:
                if "方向" in placeholder_name:
                    return "持平"
                elif "百分比" in placeholder_name:
                    return "0.0"
            
            # 如果是数据源连接问题，根据占位符类型提供更具体的默认值
            if "Both MySQL and HTTP API failed" in error_message or "connection" in error_message.lower():
                # 数据源连接失败的情况
                if "统计" in placeholder_name:
                    if "占比" in placeholder_name:
                        return "暂无数据"
                    elif "件数" in placeholder_name:
                        return "暂无数据"
                    else:
                        return "暂无数据"
                elif "周期" in placeholder_name:
                    return "暂无数据"
                elif "区域" in placeholder_name:
                    return "暂无数据"
            
            return None
        except Exception as e:
            self.logger.warning(f"生成智能默认值失败: {e}")
            return None
    
    def _make_serializable(self, data: Any) -> Any:
        """将数据转换为可JSON序列化的格式"""
        try:
            # 如果是DorisQueryResult对象
            if hasattr(data, 'data') and hasattr(data, 'execution_time'):
                # 提取pandas DataFrame并转换为列表
                df = data.data
                if hasattr(df, 'to_dict'):
                    # 将DataFrame转换为records格式的字典列表
                    return df.to_dict('records')
                else:
                    return str(data)  # 如果无法转换，返回字符串表示
            
            # 如果是pandas DataFrame
            elif hasattr(data, 'to_dict'):
                return data.to_dict('records')
            
            # 如果是pandas Series
            elif hasattr(data, 'to_list'):
                return data.to_list()
            
            # 如果是numpy数组
            elif hasattr(data, 'tolist'):
                return data.tolist()
            
            # 如果是基本数据类型
            elif isinstance(data, (str, int, float, bool, type(None))):
                return data
            
            # 如果是列表或元组
            elif isinstance(data, (list, tuple)):
                return [self._make_serializable(item) for item in data]
            
            # 如果是字典
            elif isinstance(data, dict):
                return {key: self._make_serializable(value) for key, value in data.items()}
            
            # 其他情况，转换为字符串
            else:
                return str(data)
                
        except Exception as e:
            self.logger.warning(f"数据序列化失败: {e}, 数据类型: {type(data)}")
            return str(data)  # 失败时返回字符串表示