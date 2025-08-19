"""
Cached Agent Orchestrator

扩展现有AgentOrchestrator，添加占位符缓存和两阶段执行支持
"""

import asyncio
import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.template_placeholder import TemplatePlaceholder, PlaceholderValue
from app.models.data_source import DataSource
from app.services.template.enhanced_template_parser import EnhancedTemplateParser
from app.services.template.agent_sql_analysis_service import AgentSQLAnalysisService
from .orchestrator import AgentOrchestrator, WorkflowResult, AgentResult

logger = logging.getLogger(__name__)


class CachedAgentOrchestrator(AgentOrchestrator):
    """支持缓存的Agent编排器"""
    
    def __init__(self, db: Session):
        super().__init__()
        self.db = db
        self.template_parser = EnhancedTemplateParser(db)
        self.sql_analysis_service = AgentSQLAnalysisService(db)
    
    async def execute_two_phase_pipeline(
        self,
        template_id: str,
        data_source_id: str,
        user_id: str,
        force_reanalyze: bool = False
    ) -> Dict[str, Any]:
        """
        执行两阶段流水线
        
        阶段1: Agent分析生成SQL（首次执行或强制重新分析时）
        阶段2: 数据提取和报告生成（每次执行）
        """
        try:
            logger.info(f"开始两阶段流水线执行: {template_id}")
            
            # 检查模板准备状态
            readiness_check = await self.template_parser.check_template_ready_for_execution(template_id)
            
            phase1_result = None
            
            # 阶段1: Agent分析（如果需要）
            if not readiness_check["ready"] or force_reanalyze:
                logger.info("执行阶段1: Agent分析生成SQL")
                phase1_result = await self._execute_phase1_analysis(
                    template_id, data_source_id, force_reanalyze
                )
                
                if not phase1_result["success"]:
                    return {
                        "success": False,
                        "phase": "analysis",
                        "error": phase1_result["error"],
                        "phase1_result": phase1_result
                    }
            
            # 阶段2: 数据提取和报告生成
            logger.info("执行阶段2: 数据提取和报告生成")
            phase2_result = await self._execute_phase2_extraction_and_generation(
                template_id, data_source_id, user_id
            )
            
            return {
                "success": phase2_result["success"],
                "phase": "extraction_and_generation",
                "phase1_result": phase1_result,
                "phase2_result": phase2_result,
                "total_execution_time": (
                    phase1_result.get("execution_time", 0) if phase1_result else 0
                ) + phase2_result.get("execution_time", 0)
            }
            
        except Exception as e:
            logger.error(f"两阶段流水线执行失败: {template_id}, 错误: {str(e)}")
            return {
                "success": False,
                "phase": "unknown",
                "error": str(e)
            }
    
    async def _execute_phase1_analysis(
        self,
        template_id: str,
        data_source_id: str,
        force_reanalyze: bool = False,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """阶段1: Agent分析生成SQL"""
        start_time = datetime.now()
        
        try:
            # 批量分析模板的所有占位符，传递执行时间上下文
            analysis_result = await self.sql_analysis_service.batch_analyze_template_placeholders(
                template_id, data_source_id, force_reanalyze, execution_context
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if analysis_result["success"]:
                logger.info(f"阶段1完成: 成功分析 {analysis_result['analyzed_placeholders']} 个占位符")
                
                return {
                    "success": True,
                    "template_id": template_id,
                    "data_source_id": data_source_id,
                    "analyzed_placeholders": analysis_result["analyzed_placeholders"],
                    "total_placeholders": analysis_result["total_placeholders"],
                    "success_rate": analysis_result["success_rate"],
                    "execution_time": execution_time,
                    "analysis_details": analysis_result["analysis_results"]
                }
            else:
                return {
                    "success": False,
                    "error": analysis_result.get("error", "Agent分析失败"),
                    "execution_time": execution_time
                }
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"阶段1执行失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time
            }
    
    async def _execute_phase2_extraction_and_generation(
        self,
        template_id: str,
        data_source_id: str,
        user_id: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """阶段2: 数据提取和报告生成"""
        start_time = datetime.now()
        
        try:
            # 1. 获取占位符配置
            placeholders = await self.template_parser.get_template_placeholder_configs(template_id)
            
            if not placeholders:
                return {
                    "success": False,
                    "error": "没有找到占位符配置",
                    "execution_time": 0
                }
            
            # 2. 获取或计算占位符值（带缓存），传递执行上下文
            placeholder_values = await self._get_or_compute_placeholder_values(
                placeholders, data_source_id, execution_context
            )
            
            # 3. 生成最终内容
            processed_content = await self._generate_final_content(
                template_id, placeholder_values
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "template_id": template_id,
                "data_source_id": data_source_id,
                "processed_placeholders": len([v for v in placeholder_values.values() if v["success"]]),
                "total_placeholders": len(placeholders),
                "cache_hit_rate": self._calculate_cache_hit_rate(placeholder_values),
                "processed_content": processed_content,
                "placeholder_values": placeholder_values,
                "execution_time": execution_time
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"阶段2执行失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time
            }
    
    async def _get_or_compute_placeholder_values(
        self,
        placeholders: List[Dict[str, Any]],
        data_source_id: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """获取或计算占位符值（带缓存）"""
        placeholder_values = {}
        
        for placeholder in placeholders:
            placeholder_id = placeholder["id"]
            placeholder_name = placeholder["name"]
            
            try:
                # 1. 尝试从缓存获取
                cached_value = await self._get_cached_placeholder_value(
                    placeholder_id, data_source_id
                )
                
                if cached_value:
                    logger.debug(f"缓存命中: {placeholder_name}")
                    placeholder_values[placeholder_name] = {
                        "success": True,
                        "value": cached_value["formatted_text"],
                        "source": "cache",
                        "execution_time_ms": 0,
                        "cache_hit": True
                    }
                    
                    # 更新缓存命中统计
                    await self._update_cache_hit_stats(placeholder_id)
                else:
                    # 2. 缓存未命中，执行数据查询
                    logger.debug(f"缓存未命中，执行查询: {placeholder_name}")
                    computed_value = await self._compute_placeholder_value(
                        placeholder, data_source_id
                    )
                    
                    placeholder_values[placeholder_name] = computed_value
                    
                    # 3. 保存到缓存，包含时间上下文
                    if computed_value["success"]:
                        await self._save_placeholder_value_to_cache(
                            placeholder_id, data_source_id, computed_value, execution_context
                        )
                
            except Exception as e:
                logger.error(f"处理占位符值失败: {placeholder_name}, 错误: {str(e)}")
                placeholder_values[placeholder_name] = {
                    "success": False,
                    "value": f"处理失败: {str(e)}",
                    "source": "error",
                    "execution_time_ms": 0,
                    "cache_hit": False
                }
        
        return placeholder_values
    
    async def _get_cached_placeholder_value(
        self,
        placeholder_id: str,
        data_source_id: str
    ) -> Optional[Dict[str, Any]]:
        """从缓存获取占位符值"""
        try:
            # 生成缓存键
            cache_key = self.template_parser.generate_cache_key(placeholder_id, data_source_id)
            
            # 查询有效缓存
            cached_value = self.db.query(PlaceholderValue).filter(
                PlaceholderValue.placeholder_id == placeholder_id,
                PlaceholderValue.data_source_id == data_source_id,
                PlaceholderValue.cache_key == cache_key,
                PlaceholderValue.success == True,
                PlaceholderValue.expires_at > datetime.now()
            ).first()
            
            if cached_value:
                return {
                    "formatted_text": cached_value.formatted_text,
                    "raw_result": cached_value.raw_query_result,
                    "processed_value": cached_value.processed_value,
                    "execution_time_ms": cached_value.execution_time_ms,
                    "created_at": cached_value.created_at
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取缓存值失败: {placeholder_id}, 错误: {str(e)}")
            return None
    
    async def _compute_placeholder_value(
        self,
        placeholder: Dict[str, Any],
        data_source_id: str
    ) -> Dict[str, Any]:
        """计算占位符值"""
        start_time = datetime.now()
        
        try:
            placeholder_id = placeholder["id"]
            placeholder_name = placeholder["name"]
            generated_sql = placeholder.get("generated_sql")
            
            if not generated_sql:
                return {
                    "success": False,
                    "value": "未生成SQL查询",
                    "source": "error",
                    "execution_time_ms": 0,
                    "cache_hit": False
                }
            
            # 获取数据源连接
            data_source = self.db.query(DataSource).filter(
                DataSource.id == data_source_id
            ).first()
            
            if not data_source:
                return {
                    "success": False,
                    "value": "数据源不存在",
                    "source": "error",
                    "execution_time_ms": 0,
                    "cache_hit": False
                }
            
            # 执行SQL查询
            from app.services.connectors.connector_factory import create_connector
            connector = create_connector(data_source)
            
            query_result = await connector.execute_query(generated_sql)
            
            # 处理查询结果
            formatted_text = self._format_query_result(query_result, placeholder)
            
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return {
                "success": True,
                "value": formatted_text,
                "source": "query",
                "execution_time_ms": execution_time_ms,
                "cache_hit": False,
                "raw_result": query_result,
                "sql_executed": generated_sql
            }
            
        except Exception as e:
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"计算占位符值失败: {placeholder.get('name', 'unknown')}, 错误: {str(e)}")
            
            return {
                "success": False,
                "value": f"查询失败: {str(e)}",
                "source": "error",
                "execution_time_ms": execution_time_ms,
                "cache_hit": False
            }
    
    def _format_query_result(
        self,
        query_result: Any,
        placeholder: Dict[str, Any]
    ) -> str:
        """格式化查询结果"""
        try:
            if not query_result:
                return "无数据"
            
            # 如果是列表格式
            if isinstance(query_result, list):
                if not query_result:
                    return "无数据"
                
                # 单行单列结果（常见的统计查询）
                if len(query_result) == 1 and isinstance(query_result[0], dict):
                    first_row = query_result[0]
                    if len(first_row) == 1:
                        # 单个统计值
                        value = list(first_row.values())[0]
                        return str(value)
                    else:
                        # 多列，选择第一个值或拼接
                        return str(list(first_row.values())[0])
                
                # 多行结果
                return f"共 {len(query_result)} 条记录"
            
            # 如果是字典格式
            elif isinstance(query_result, dict):
                if "count" in query_result:
                    return str(query_result["count"])
                elif "value" in query_result:
                    return str(query_result["value"])
                else:
                    return str(list(query_result.values())[0])
            
            # 其他格式
            return str(query_result)
            
        except Exception as e:
            logger.error(f"格式化查询结果失败: {str(e)}")
            return f"格式化失败: {str(e)}"
    
    async def _save_placeholder_value_to_cache(
        self,
        placeholder_id: str,
        data_source_id: str,
        computed_value: Dict[str, Any],
        execution_context: Optional[Dict[str, Any]] = None
    ):
        """保存占位符值到缓存"""
        try:
            # 获取占位符配置
            placeholder = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == placeholder_id
            ).first()
            
            if not placeholder:
                return
            
            # 生成缓存键
            cache_key = self.template_parser.generate_cache_key(placeholder_id, data_source_id)
            
            # 计算过期时间
            expires_at = datetime.now() + timedelta(hours=placeholder.cache_ttl_hours)
            
            # 处理查询结果，确保可以JSON序列化
            raw_result = computed_value.get("raw_result")
            serializable_result = self._make_result_serializable(raw_result)
            
            # 准备时间相关字段
            execution_time = None
            report_period = None
            period_start = None
            period_end = None
            sql_parameters_snapshot = None
            execution_batch_id = None
            version_hash = None
            
            if execution_context:
                execution_time = datetime.fromisoformat(execution_context["execution_time"]) if execution_context.get("execution_time") else None
                report_period = execution_context.get("report_period")
                period_start = datetime.fromisoformat(execution_context["period_start"]) if execution_context.get("period_start") else None
                period_end = datetime.fromisoformat(execution_context["period_end"]) if execution_context.get("period_end") else None
                sql_parameters_snapshot = execution_context.get("sql_parameters", {})
                
                # 生成执行批次ID（同一次任务执行的所有占位符共享）
                import hashlib
                batch_components = f"{execution_time}_{report_period}_{placeholder_id}"
                execution_batch_id = hashlib.md5(batch_components.encode()).hexdigest()[:16]
                
                # 生成版本哈希（基于SQL+参数+时间）
                sql_executed = computed_value.get("sql_executed", "")
                version_components = f"{sql_executed}_{str(sql_parameters_snapshot)}_{execution_time}"
                version_hash = hashlib.sha256(version_components.encode()).hexdigest()
                
                # 标记旧版本为非最新
                self.db.query(PlaceholderValue).filter(
                    PlaceholderValue.placeholder_id == placeholder_id,
                    PlaceholderValue.is_latest_version == True
                ).update({"is_latest_version": False})
                
                logger.info(f"设置执行上下文 - 批次ID: {execution_batch_id}, 版本哈希: {version_hash}")
            
            # 创建缓存记录，包含时间相关字段
            cache_record = PlaceholderValue(
                placeholder_id=placeholder_id,
                data_source_id=data_source_id,
                raw_query_result=serializable_result,
                processed_value={"formatted_text": computed_value["value"]},
                formatted_text=computed_value["value"],
                execution_sql=computed_value.get("sql_executed"),
                execution_time_ms=computed_value["execution_time_ms"],
                row_count=self._extract_row_count(raw_result),
                success=computed_value["success"],
                cache_key=cache_key,
                expires_at=expires_at,
                hit_count=0,
                # 时间相关字段
                execution_time=execution_time,
                report_period=report_period,
                period_start=period_start,
                period_end=period_end,
                sql_parameters_snapshot=sql_parameters_snapshot,
                execution_batch_id=execution_batch_id,
                version_hash=version_hash,
                is_latest_version=True
            )
            
            self.db.add(cache_record)
            self.db.commit()
            
            logger.debug(f"占位符值已缓存: {placeholder.placeholder_name}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存占位符值到缓存失败: {placeholder_id}, 错误: {str(e)}")
    
    async def _update_cache_hit_stats(self, placeholder_id: str):
        """更新缓存命中统计"""
        try:
            cache_record = self.db.query(PlaceholderValue).filter(
                PlaceholderValue.placeholder_id == placeholder_id,
                PlaceholderValue.expires_at > datetime.now()
            ).first()
            
            if cache_record:
                cache_record.hit_count += 1
                cache_record.last_hit_at = datetime.now()
                self.db.commit()
                
        except Exception as e:
            logger.error(f"更新缓存命中统计失败: {placeholder_id}, 错误: {str(e)}")
    
    async def _generate_final_content(
        self,
        template_id: str,
        placeholder_values: Dict[str, Dict[str, Any]]
    ) -> str:
        """生成最终内容"""
        try:
            # 获取模板内容
            from app.models.template import Template
            template = self.db.query(Template).filter(Template.id == template_id).first()
            
            if not template:
                return "模板不存在"
            
            # 检查模板类型和内容格式
            template_type = getattr(template, 'template_type', 'text')
            template_content = getattr(template, 'content', '') or ''
            
            # 处理二进制模板文件（如DOCX）
            if template_type == 'docx' and template_content:
                # 检查是否是hex编码的二进制内容
                if all(c in '0123456789ABCDEFabcdef' for c in template_content.replace(' ', '').replace('\n', '')):
                    # 是hex编码的二进制内容，不能直接处理占位符
                    processed_placeholders = len([v for v in placeholder_values.values() if v.get("success", False)])
                    failed_placeholders = len(placeholder_values) - processed_placeholders
                    
                    summary_parts = [f"Word模板处理完成"]
                    if processed_placeholders > 0:
                        summary_parts.append(f"成功处理 {processed_placeholders} 个占位符")
                    if failed_placeholders > 0:
                        summary_parts.append(f"{failed_placeholders} 个占位符处理失败")
                    
                    return "，".join(summary_parts)
                else:
                    # 文本格式的DOCX内容（少见情况）
                    template_content = template_content
            
            # 对于文本类型模板，进行占位符替换
            if template_type in ['text', 'html'] and template_content:
                # 替换占位符
                for placeholder_name, value_info in placeholder_values.items():
                    # 支持多种占位符格式
                    placeholder_patterns = [
                        f"{{{{{placeholder_name}}}}}",  # {{占位符}}
                        f"{{{placeholder_name}}}",      # {占位符}
                    ]
                    
                    replacement_value = value_info["value"]
                    
                    for pattern in placeholder_patterns:
                        if pattern in template_content:
                            template_content = template_content.replace(pattern, str(replacement_value))
            
            # 生成处理摘要
            processed_placeholders = len([v for v in placeholder_values.values() if v.get("success", False)])
            failed_placeholders = len(placeholder_values) - processed_placeholders
            
            summary_parts = [f"模板处理完成"]
            if processed_placeholders > 0:
                summary_parts.append(f"成功处理 {processed_placeholders} 个占位符")
            if failed_placeholders > 0:
                summary_parts.append(f"{failed_placeholders} 个占位符处理失败")
            
            return "，".join(summary_parts)
            
        except Exception as e:
            logger.error(f"生成最终内容失败: {template_id}, 错误: {str(e)}")
            return f"内容生成失败: {str(e)}"
    
    def _calculate_cache_hit_rate(self, placeholder_values: Dict[str, Dict[str, Any]]) -> float:
        """计算缓存命中率"""
        total_placeholders = len(placeholder_values)
        if total_placeholders == 0:
            return 0.0
        
        cache_hits = len([v for v in placeholder_values.values() if v.get("cache_hit", False)])
        return round((cache_hits / total_placeholders) * 100, 2)
    
    def _make_result_serializable(self, result: Any) -> Any:
        """将查询结果转换为可JSON序列化的格式"""
        try:
            if result is None:
                return None
            
            # 如果是DorisQueryResult对象，提取可序列化的部分
            if hasattr(result, 'data') and hasattr(result, 'execution_time'):
                # 这是DorisQueryResult对象
                data_dict = []
                if hasattr(result.data, 'to_dict'):
                    # pandas DataFrame
                    data_dict = result.data.to_dict('records')
                elif hasattr(result.data, '__iter__'):
                    # 其他可迭代对象
                    data_dict = list(result.data)
                
                return {
                    "data": data_dict,
                    "execution_time": float(result.execution_time),
                    "rows_scanned": getattr(result, 'rows_scanned', 0),
                    "bytes_scanned": getattr(result, 'bytes_scanned', 0),
                    "is_cached": getattr(result, 'is_cached', False),
                    "query_id": getattr(result, 'query_id', ''),
                    "fe_host": getattr(result, 'fe_host', '')
                }
            
            # 如果是pandas DataFrame
            if hasattr(result, 'to_dict'):
                return result.to_dict('records')
            
            # 如果是普通的list/dict，直接返回
            if isinstance(result, (list, dict, str, int, float, bool)):
                return result
            
            # 其他情况转换为字符串
            return str(result)
            
        except Exception as e:
            logger.warning(f"序列化查询结果失败: {e}")
            return {"error": "序列化失败", "original_type": str(type(result))}

    def _extract_row_count(self, raw_result: Any) -> int:
        """从原始结果中提取行数"""
        try:
            # 如果是DorisQueryResult对象
            if hasattr(raw_result, 'data'):
                if hasattr(raw_result.data, '__len__'):
                    return len(raw_result.data)
                return getattr(raw_result, 'rows_scanned', 0)
            
            if isinstance(raw_result, list):
                return len(raw_result)
            elif isinstance(raw_result, dict) and "count" in raw_result:
                return int(raw_result["count"])
            else:
                return 1
        except:
            return 0
    
    async def invalidate_template_cache(self, template_id: str) -> int:
        """清除模板相关的所有缓存"""
        try:
            # 获取模板的所有占位符
            placeholders = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.template_id == template_id,
                TemplatePlaceholder.is_active == True
            ).all()
            
            invalidated_count = 0
            
            for placeholder in placeholders:
                # 设置缓存过期
                result = self.db.query(PlaceholderValue).filter(
                    PlaceholderValue.placeholder_id == placeholder.id,
                    PlaceholderValue.expires_at > datetime.now()
                ).update({"expires_at": datetime.now()})
                
                invalidated_count += result
            
            self.db.commit()
            
            logger.info(f"清除模板缓存: {template_id}, 清除 {invalidated_count} 条缓存")
            return invalidated_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"清除模板缓存失败: {template_id}, 错误: {str(e)}")
            return 0