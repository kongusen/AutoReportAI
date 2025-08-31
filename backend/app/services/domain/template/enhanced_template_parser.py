# TEMPORARILY DISABLED - Legacy IAOP dependencies removed
# This module needs to be refactored to use MCP orchestrator
# Original functionality moved to MCP-based implementation

raise NotImplementedError("This module is temporarily disabled after IAOP cleanup. Use MCP equivalent instead.")

# Original code below (commented out):
# """
# Enhanced Template Parser
# 
# 扩展现有TemplateParser，添加占位符持久化功能
# """
# 
# import logging
# import hashlib
# from datetime import datetime
# from typing import Dict, Any, List, Optional, Tuple
# from sqlalchemy.orm import Session
# from uuid import UUID
# 
# from app.models.template_placeholder import TemplatePlaceholder
# from app.services.domain.template.services.template_domain_service import TemplateParser
# # 使用模板层工厂获取占位符提取器，避免直接耦合
# from .factories import create_placeholder_extractor_for_template
# 
# logger = logging.getLogger(__name__)
# 
# 
# class EnhancedTemplateParser:
#     """增强版模板解析器 - 支持占位符持久化"""
#     
#     def __init__(self, db: Session):
#         self.db = db
#         self.base_parser = TemplateParser()
#         self.extraction_service = create_placeholder_extractor_for_template(db)
#     
#     async def parse_and_store_template_placeholders(
#         self,
#         template_id: str,
#         template_content: str,
#         force_reparse: bool = False
#     ) -> Dict[str, Any]:
#         """
#         解析模板并持久化占位符
#         
#         Args:
#             template_id: 模板ID
#             template_content: 模板内容
#             force_reparse: 是否强制重新解析
#             
#         Returns:
#             解析结果统计
#         """
#         try:
#             logger.info(f"开始解析模板占位符: {template_id}")
#             
#             # 1. 检查是否已存在占位符配置
#             if not force_reparse:
#                 existing_count = await self._count_existing_placeholders(template_id)
#                 if existing_count > 0:
#                     logger.info(f"模板已存在 {existing_count} 个占位符配置，跳过重新解析")
#                     return await self._get_existing_placeholder_info(template_id)
#             
#             # 2. 清理现有配置（如果是强制重新解析）
#             if force_reparse:
#                 await self._cleanup_existing_placeholders(template_id)
#             
#             # 3. 使用增强提取服务解析并存储
#             extraction_result = await self.extraction_service.extract_and_store_placeholders(
#                 template_id, template_content
#             )
#             
#             if not extraction_result["success"]:
#                 return extraction_result
#             
#             # 计算存储的占位符总数
#             stored_count = (
#                 extraction_result.get("new_placeholders", 0) + 
#                 extraction_result.get("updated_placeholders", 0)
#             )
#             
#             logger.info(f"模板解析完成: {template_id}, 提取 {stored_count} 个占位符")
#             
#             return {
#                 "success": True,
#                 "template_id": template_id,
#                 "total_placeholders": extraction_result["total_placeholders"],
#                 "stored_placeholders": stored_count,
#                 "new_placeholders": extraction_result.get("new_placeholders", 0),
#                 "updated_placeholders": extraction_result.get("updated_placeholders", 0),
#                 "skipped_placeholders": extraction_result.get("skipped_placeholders", 0),
#                 "message": "模板占位符解析并存储成功"
#             }
#             
#         except Exception as e:
#             logger.error(f"模板解析失败: {template_id}, 错误: {str(e)}")
#             return {
#                 "success": False,
#                 "template_id": template_id,
#                 "error": str(e),
#                 "total_placeholders": 0,
#                 "stored_placeholders": 0
#             }
#     
#     async def get_template_placeholder_configs(
#         self,
#         template_id: str,
#         include_analysis_status: bool = True
#     ) -> List[Dict[str, Any]]:
#         """获取模板的占位符配置"""
#         return await self.extraction_service.get_template_placeholders(
#             template_id, include_analysis_status
#         )
#     
#     async def get_unanalyzed_placeholders(self, template_id: str) -> List[Dict[str, Any]]:
#         """获取未被Agent分析的占位符"""
#         placeholders = self.db.query(TemplatePlaceholder).filter(
#             TemplatePlaceholder.template_id == template_id,
#             TemplatePlaceholder.is_active == True,
#             TemplatePlaceholder.agent_analyzed == False
#         ).order_by(TemplatePlaceholder.execution_order).all()
#         
#         return [
#             {
#                 "id": str(p.id),
#                 "name": p.placeholder_name,
#                 "text": p.placeholder_text,
#                 "type": p.placeholder_type,
#                 "content_type": p.content_type,
#                 "priority": p.agent_config.get("priority", 5),
#                 "complexity": p.agent_config.get("complexity", "medium"),
#                 "workflow_id": p.agent_workflow_id,
#                 "execution_order": p.execution_order
#             }
#             for p in placeholders
#         ]
#     
#     async def mark_placeholder_analyzed(
#         self,
#         placeholder_id: str,
#         analysis_result: Dict[str, Any]
#     ) -> bool:
#         """标记占位符已被Agent分析"""
#         try:
#             placeholder = self.db.query(TemplatePlaceholder).filter(
#                 TemplatePlaceholder.id == placeholder_id
#             ).first()
#             
#             if not placeholder:
#                 logger.error(f"占位符不存在: {placeholder_id}")
#                 return False
#             
#             # 更新分析结果
#             placeholder.agent_analyzed = True
#             placeholder.target_database = analysis_result.get("target_database", "")
#             placeholder.target_table = analysis_result.get("target_table", "")
#             placeholder.required_fields = analysis_result.get("required_fields", [])
#             placeholder.generated_sql = analysis_result.get("generated_sql", "")
#             placeholder.sql_validated = analysis_result.get("sql_validated", False)
#             placeholder.confidence_score = analysis_result.get("confidence_score", 0.0)
#             placeholder.analyzed_at = datetime.now()
#             
#             # 更新agent_config
#             if not placeholder.agent_config:
#                 placeholder.agent_config = {}
#             
#             placeholder.agent_config.update({
#                 "analysis_result": analysis_result,
#                 "analyzed_at": datetime.now().isoformat()
#             })
#             
#             self.db.commit()
#             
#             logger.info(f"占位符分析结果已保存: {placeholder.placeholder_name}")
#             return True
#             
#         except Exception as e:
#             self.db.rollback()
#             logger.error(f"保存占位符分析结果失败: {placeholder_id}, 错误: {str(e)}")
#             return False
#     
#     async def update_placeholder_execution_order(
#         self,
#         template_id: str,
#         placeholder_orders: List[Dict[str, Any]]
#     ) -> bool:
#         """更新占位符执行顺序"""
#         try:
#             for order_info in placeholder_orders:
#                 placeholder_id = order_info["placeholder_id"]
#                 new_order = order_info["execution_order"]
#                 
#                 placeholder = self.db.query(TemplatePlaceholder).filter(
#                     TemplatePlaceholder.id == placeholder_id,
#                     TemplatePlaceholder.template_id == template_id
#                 ).first()
#                 
#                 if placeholder:
#                     placeholder.execution_order = new_order
#             
#             self.db.commit()
#             logger.info(f"更新占位符执行顺序成功: {template_id}")
#             return True
#             
#         except Exception as e:
#             self.db.rollback()
#             logger.error(f"更新占位符执行顺序失败: {template_id}, 错误: {str(e)}")
#             return False
#     
#     async def get_placeholder_analysis_statistics(self, template_id: str) -> Dict[str, Any]:
#         """获取占位符分析统计"""
#         try:
#             # 总占位符数
#             total_placeholders = self.db.query(TemplatePlaceholder).filter(
#                 TemplatePlaceholder.template_id == template_id,
#                 TemplatePlaceholder.is_active == True
#             ).count()
#             
#             # 已分析占位符数
#             analyzed_placeholders = self.db.query(TemplatePlaceholder).filter(
#                 TemplatePlaceholder.template_id == template_id,
#                 TemplatePlaceholder.is_active == True,
#                 TemplatePlaceholder.agent_analyzed == True
#             ).count()
#             
#             # SQL已验证占位符数
#             validated_placeholders = self.db.query(TemplatePlaceholder).filter(
#                 TemplatePlaceholder.template_id == template_id,
#                 TemplatePlaceholder.is_active == True,
#                 TemplatePlaceholder.sql_validated == True
#             ).count()
#             
#             # 置信度统计
#             placeholders = self.db.query(TemplatePlaceholder).filter(
#                 TemplatePlaceholder.template_id == template_id,
#                 TemplatePlaceholder.is_active == True,
#                 TemplatePlaceholder.agent_analyzed == True
#             ).all()
#             
#             avg_confidence = 0.0
#             if placeholders:
#                 avg_confidence = sum(p.confidence_score for p in placeholders) / len(placeholders)
#             
#             # 分析进度
#             analysis_progress = 0
#             if total_placeholders > 0:
#                 analysis_progress = int((analyzed_placeholders / total_placeholders) * 100)
#             
#             return {
#                 "total_placeholders": total_placeholders,
#                 "analyzed_placeholders": analyzed_placeholders,
#                 "validated_placeholders": validated_placeholders,
#                 "unanalyzed_placeholders": total_placeholders - analyzed_placeholders,
#                 "analysis_progress": analysis_progress,
#                 "avg_confidence_score": round(avg_confidence, 2),
#                 "ready_for_execution": validated_placeholders == total_placeholders
#             }
#             
#         except Exception as e:
#             logger.error(f"获取占位符分析统计失败: {template_id}, 错误: {str(e)}")
#             return {
#                 "total_placeholders": 0,
#                 "analyzed_placeholders": 0,
#                 "validated_placeholders": 0,
#                 "unanalyzed_placeholders": 0,
#                 "analysis_progress": 0,
#                 "avg_confidence_score": 0.0,
#                 "ready_for_execution": False
#             }
#     
#     async def _count_existing_placeholders(self, template_id: str) -> int:
#         """统计现有占位符数量"""
#         return self.db.query(TemplatePlaceholder).filter(
#             TemplatePlaceholder.template_id == template_id,
#             TemplatePlaceholder.is_active == True
#         ).count()
#     
#     async def _get_existing_placeholder_info(self, template_id: str) -> Dict[str, Any]:
#         """获取现有占位符信息"""
#         placeholders = await self.get_template_placeholder_configs(template_id)
#         
#         type_distribution = {}
#         requires_analysis = 0
#         
#         for p in placeholders:
#             ptype = p.get("type", "unknown")
#             type_distribution[ptype] = type_distribution.get(ptype, 0) + 1
#             
#             if not p.get("agent_analyzed", False):
#                 requires_analysis += 1
#         
#         return {
#             "success": True,
#             "template_id": template_id,
#             "total_placeholders": len(placeholders),
#             "stored_placeholders": len(placeholders),
#             "placeholders": placeholders,
#             "type_distribution": type_distribution,
#             "requires_agent_analysis": requires_analysis,
#             "message": "使用现有占位符配置"
#         }
#     
#     async def _cleanup_existing_placeholders(self, template_id: str):
#         """清理现有占位符配置"""
#         try:
#             # 标记为非活跃而不是删除，保留历史数据
#             self.db.query(TemplatePlaceholder).filter(
#                 TemplatePlaceholder.template_id == template_id
#             ).update({"is_active": False})
#             
#             self.db.commit()
#             logger.info(f"清理现有占位符配置: {template_id}")
#             
#         except Exception as e:
#             self.db.rollback()
#             logger.error(f"清理占位符配置失败: {template_id}, 错误: {str(e)}")
#             raise
#     
#     def _count_requires_analysis(self, placeholders: List[Dict]) -> int:
#         """统计需要Agent分析的占位符数量"""
#         return len([p for p in placeholders if p.get("requires_analysis", True)])
#     
#     def generate_cache_key(
#         self,
#         placeholder_id: str,
#         data_source_id: str,
#         additional_params: Dict[str, Any] = None
#     ) -> str:
#         """生成缓存键"""
#         key_components = [placeholder_id, data_source_id]
#         
#         if additional_params:
#             # 对额外参数进行排序以确保一致性
#             sorted_params = sorted(additional_params.items())
#             key_components.append(str(sorted_params))
#         
#         key_string = ":".join(key_components)
#         return hashlib.md5(key_string.encode()).hexdigest()
#     
#     async def check_template_ready_for_execution(self, template_id: str) -> Dict[str, Any]:
#         """检查模板是否准备好执行"""
#         stats = await self.get_placeholder_analysis_statistics(template_id)
#         
#         # 检查所有占位符是否都已分析并验证
#         ready = (
#             stats["total_placeholders"] > 0 and
#             stats["analyzed_placeholders"] == stats["total_placeholders"] and
#             stats["validated_placeholders"] == stats["total_placeholders"]
#         )
#         
#         warnings = []
#         if stats["total_placeholders"] == 0:
#             warnings.append("模板中没有占位符")
#         elif stats["unanalyzed_placeholders"] > 0:
#             warnings.append(f"还有 {stats['unanalyzed_placeholders']} 个占位符未完成Agent分析")
#         elif stats["validated_placeholders"] < stats["analyzed_placeholders"]:
#             unvalidated_count = stats["analyzed_placeholders"] - stats["validated_placeholders"]
#             warnings.append(f"还有 {unvalidated_count} 个占位符的SQL未通过验证")
#         
#         if stats["avg_confidence_score"] < 0.5:
#             warnings.append(f"平均置信度较低: {stats['avg_confidence_score']}")
#         
#         return {
#             "ready": ready,
#             "statistics": stats,
#             "warnings": warnings,
#             "recommendations": self._generate_execution_recommendations(stats)
#         }
#     
#     def _generate_execution_recommendations(self, stats: Dict[str, Any]) -> List[str]:
#         """生成执行建议"""
#         recommendations = []
#         
#         if stats["unanalyzed_placeholders"] > 0:
#             recommendations.append("建议先运行Agent分析任务完成占位符分析")
#         
#         if stats["avg_confidence_score"] < 0.7:
#             recommendations.append("建议手动检查低置信度的占位符配置")
#         
#         if stats["ready_for_execution"]:
#             recommendations.append("模板已准备就绪，可以开始数据提取和报告生成")
#         
#         return recommendations
#     
#     async def analyze_template_placeholders(self, template_id: str) -> Dict[str, Any]:
#         """
#         分析模板占位符并使用IAOP Agent进行处理
#         
#         Args:
#             template_id: 模板ID
#             
#         Returns:
#             分析结果字典
#         """
#         try:
#             logger.info(f"开始分析模板占位符: {template_id}")
#             
#             # 1. 获取模板信息
#             from app import crud
#             template = crud.template.get(self.db, id=template_id)
#             if not template:
#                 return {
#                     'success': False,
#                     'error': f'模板不存在: {template_id}',
#                     'placeholders': []
#                 }
#             
#             # 2. 解析和存储占位符（如果还没有的话）
#             placeholder_result = await self.parse_and_store_template_placeholders(
#                 template_id, template.content, force_reparse=False
#             )
#             
#             if not placeholder_result.get('success'):
#                 return placeholder_result
#             
#             # 3. 获取需要分析的占位符
#             unanalyzed_placeholders = await self.get_unanalyzed_placeholders(template_id)
#             
#             if not unanalyzed_placeholders:
#                 logger.info(f"模板 {template_id} 的所有占位符都已分析完成")
#                 # 返回现有占位符信息
#                 existing_placeholders = await self.get_template_placeholder_configs(template_id)
#                 return {
#                     'success': True,
#                     'message': '所有占位符都已分析完成',
#                     'placeholders': existing_placeholders,
#                     'total_placeholders': len(existing_placeholders),
#                     'analyzed_placeholders': len(existing_placeholders),
#                     'unanalyzed_placeholders': 0
#                 }
#             
#             # 4. 使用IAOP Agent分析占位符
#             # REMOVED: IAOP PlaceholderParserAgent - Use MCP placeholder analyzer instead
#             # REMOVED: IAOP context - Use MCP context management instead
#             
#             analyzed_placeholders = []
#             analysis_errors = []
#             
#             # 创建Agent实例（不传递db_session参数）
#             parser_agent = PlaceholderParserAgent()
#             
#             # 为每个占位符执行分析
#             for placeholder_info in unanalyzed_placeholders:
#                 try:
#                     # 创建执行上下文
#                     context = EnhancedExecutionContext(
#                         session_id=f"analyze_{template_id}",
#                         user_id="system",
#                         task_id=placeholder_info['id']
#                     )
#                     
#                     # 设置必要的上下文数据
#                     context.set_context("template_content", template.content, ContextScope.REQUEST)
#                     context.set_context("data_source_context", {
#                         "template_id": template_id,
#                         "data_source_id": str(template.data_source_id) if template.data_source_id else None,
#                         "placeholder_info": placeholder_info
#                     }, ContextScope.REQUEST)
#                     
#                     # 执行Agent分析
#                     agent_result = await parser_agent.execute(context)
#                     
#                     if agent_result.get('success'):
#                         # 保存分析结果
#                         analysis_data = agent_result.get('data', {})
#                         placeholders_data = analysis_data.get('placeholders', [])
#                         
#                         if placeholders_data:
#                             # 取第一个占位符的分析结果（通常只有一个）
#                             placeholder_analysis = placeholders_data[0]
#                             
#                             # 标记占位符已分析
#                             await self.mark_placeholder_analyzed(
#                                 placeholder_info['id'],
#                                 {
#                                     'task_type': placeholder_analysis.get('task_type', 'unknown'),
#                                     'metric': placeholder_analysis.get('metric', ''),
#                                     'dimensions': placeholder_analysis.get('dimensions', []),
#                                     'time_range': placeholder_analysis.get('time_range'),
#                                     'filters': placeholder_analysis.get('filters', []),
#                                     'aggregation': placeholder_analysis.get('aggregation', 'sum'),
#                                     'confidence_score': placeholder_analysis.get('confidence', 0.0),
#                                     'table_mapping': placeholder_analysis.get('table_mapping', {}),
#                                     'generated_sql': '',  # SQL生成将在后续步骤完成
#                                     'sql_validated': False
#                                 }
#                             )
#                             
#                             analyzed_placeholders.append({
#                                 'id': placeholder_info['id'],
#                                 'name': placeholder_info['name'],
#                                 'analysis_result': placeholder_analysis,
#                                 'success': True
#                             })
#                         
#                     else:
#                         error_msg = agent_result.get('error', '分析失败')
#                         analysis_errors.append({
#                             'placeholder_id': placeholder_info['id'],
#                             'placeholder_name': placeholder_info['name'],
#                             'error': error_msg
#                         })
#                         logger.warning(f"占位符分析失败: {placeholder_info['name']} - {error_msg}")
#                 
#                 except Exception as e:
#                     error_msg = f"Agent执行异常: {str(e)}"
#                     analysis_errors.append({
#                         'placeholder_id': placeholder_info['id'],
#                         'placeholder_name': placeholder_info['name'],
#                         'error': error_msg
#                     })
#                     logger.error(f"占位符分析异常: {placeholder_info['name']} - {error_msg}")
#             
#             # 5. 计算分析结果统计
#             total_placeholders = len(unanalyzed_placeholders)
#             successful_analyses = len(analyzed_placeholders)
#             failed_analyses = len(analysis_errors)
#             
#             success = successful_analyses > 0  # 只要有成功分析的就算成功
#             
#             result = {
#                 'success': success,
#                 'message': f'占位符分析完成: 成功 {successful_analyses}/{total_placeholders}',
#                 'placeholders': analyzed_placeholders,
#                 'total_placeholders': total_placeholders,
#                 'analyzed_placeholders': successful_analyses,
#                 'failed_placeholders': failed_analyses,
#                 'errors': analysis_errors
#             }
#             
#             logger.info(f"模板占位符分析完成: {template_id}, 成功: {successful_analyses}, 失败: {failed_analyses}")
#             return result
#             
#         except Exception as e:
#             logger.error(f"模板占位符分析失败: {template_id}, 错误: {str(e)}")
#             return {
#                 'success': False,
#                 'error': f'分析失败: {str(e)}',
#                 'placeholders': [],
#                 'total_placeholders': 0,
#                 'analyzed_placeholders': 0
#             }
