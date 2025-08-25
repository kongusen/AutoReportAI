"""
占位符分析门面服务

为任务板块和模版占位符分析板块提供统一的调用接口
支持两种调用场景：
1. 上传模版后在占位符页面主动调用分析
2. 在任务中判断有没有存储的SQL，没有则调用分析，有则直接ETL
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy.orm import Session

from ..agents.placeholder_sql_agent import (
    PlaceholderSQLAnalyzer, PlaceholderAnalysisResult, PlaceholderAnalysisRequest
)

logger = logging.getLogger(__name__)


@dataclass
class PlaceholderAnalysisContext:
    """占位符分析上下文"""
    source: str  # "template_page" | "task_execution"
    user_id: str
    template_id: Optional[str] = None
    task_id: Optional[str] = None
    additional_context: Optional[Dict[str, Any]] = None


class PlaceholderAnalysisFacade:
    """占位符分析门面服务 - 统一的调用接口"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.logger = logging.getLogger(__name__)
    
    # ====== 模版占位符分析板块调用接口 ======
    
    async def analyze_template_placeholders(self, 
                                          template_id: str,
                                          user_id: str,
                                          force_reanalyze: bool = False) -> Dict[str, Any]:
        """
        模版上传后，在占位符页面主动调用分析
        
        Args:
            template_id: 模版ID
            user_id: 用户ID
            force_reanalyze: 是否强制重新分析
            
        Returns:
            分析结果摘要
        """
        
        self.logger.info(f"🎯 开始分析模版占位符: template_id={template_id}, user_id={user_id}")
        
        try:
            # 获取模版的所有占位符
            placeholders = await self._get_template_placeholders(template_id)
            if not placeholders:
                return {
                    "success": False,
                    "message": "模版中没有找到占位符",
                    "total_count": 0,
                    "analyzed_count": 0,
                    "results": []
                }
            
            # 获取模版关联的数据源
            data_source_id = await self._get_template_data_source(template_id)
            if not data_source_id:
                return {
                    "success": False,
                    "message": "模版没有关联数据源",
                    "total_count": len(placeholders),
                    "analyzed_count": 0,
                    "results": []
                }
            
            # 创建分析器
            analyzer = PlaceholderSQLAnalyzer(db_session=self.db, user_id=user_id)
            
            # 批量分析占位符
            analysis_requests = []
            for placeholder in placeholders:
                analysis_requests.append({
                    'placeholder_id': placeholder['id'],
                    'placeholder_text': placeholder['placeholder_name'],
                    'placeholder_type': placeholder['placeholder_type'],
                    'data_source_id': data_source_id,
                    'template_id': template_id,
                    'template_context': {
                        'template_id': template_id,
                        'analysis_source': 'template_page'
                    },
                    'force_reanalyze': force_reanalyze
                })
            
            results = await analyzer.batch_analyze(analysis_requests)
            
            # 统计结果
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]
            
            self.logger.info(f"✅ 模版占位符分析完成: 成功={len(successful_results)}, 失败={len(failed_results)}")
            
            return {
                "success": True,
                "message": f"成功分析 {len(successful_results)}/{len(results)} 个占位符",
                "total_count": len(results),
                "analyzed_count": len(successful_results),
                "failed_count": len(failed_results),
                "results": [r.to_dict() for r in results],
                "summary": self._generate_analysis_summary(results)
            }
            
        except Exception as e:
            self.logger.error(f"模版占位符分析失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"分析失败: {str(e)}",
                "total_count": 0,
                "analyzed_count": 0,
                "results": []
            }
    
    async def get_template_placeholder_status(self, template_id: str) -> Dict[str, Any]:
        """
        获取模版占位符的分析状态
        
        Args:
            template_id: 模版ID
            
        Returns:
            占位符状态摘要
        """
        
        try:
            placeholders = await self._get_template_placeholders(template_id)
            if not placeholders:
                return {
                    "total_count": 0,
                    "analyzed_count": 0,
                    "pending_count": 0,
                    "error_count": 0,
                    "placeholders": []
                }
            
            placeholder_statuses = []
            analyzed_count = 0
            error_count = 0
            
            for placeholder in placeholders:
                # 检查是否已有分析结果
                analyzer = PlaceholderSQLAnalyzer(db_session=self.db)
                stored_result = await analyzer.check_stored_sql(placeholder['id'])
                
                status = {
                    "placeholder_id": placeholder['id'],
                    "placeholder_name": placeholder['placeholder_name'],
                    "placeholder_type": placeholder['placeholder_type'],
                    "has_sql": stored_result.get('has_sql', False),
                    "last_analysis_at": stored_result.get('last_analysis_at'),
                    "confidence": stored_result.get('confidence', 0.0),
                    "target_table": stored_result.get('target_table')
                }
                
                if stored_result.get('has_sql'):
                    analyzed_count += 1
                    status['status'] = 'analyzed'
                elif stored_result.get('error'):
                    error_count += 1
                    status['status'] = 'error'
                    status['error'] = stored_result.get('error')
                else:
                    status['status'] = 'pending'
                
                placeholder_statuses.append(status)
            
            return {
                "total_count": len(placeholders),
                "analyzed_count": analyzed_count,
                "pending_count": len(placeholders) - analyzed_count - error_count,
                "error_count": error_count,
                "placeholders": placeholder_statuses
            }
            
        except Exception as e:
            self.logger.error(f"获取占位符状态失败: {e}")
            return {
                "total_count": 0,
                "analyzed_count": 0,
                "pending_count": 0,
                "error_count": 0,
                "placeholders": [],
                "error": str(e)
            }
    
    # ====== 任务执行板块调用接口 ======
    
    async def ensure_placeholder_sql_for_task(self, 
                                            placeholder_id: str,
                                            user_id: str,
                                            task_id: str = None) -> Dict[str, Any]:
        """
        任务执行时确保占位符有可用的SQL
        
        业务逻辑：
        1. 首先检查是否已有存储的SQL
        2. 如果有，直接返回用于ETL
        3. 如果没有，调用分析生成SQL
        
        Args:
            placeholder_id: 占位符ID
            user_id: 用户ID
            task_id: 任务ID（可选）
            
        Returns:
            SQL及其相关信息
        """
        
        self.logger.info(f"🔍 任务执行检查占位符SQL: placeholder_id={placeholder_id}, task_id={task_id}")
        
        try:
            # 创建分析器
            analyzer = PlaceholderSQLAnalyzer(db_session=self.db, user_id=user_id)
            
            # 1. 首先检查已存储的SQL
            stored_result = await analyzer.check_stored_sql(placeholder_id)
            
            if stored_result.get('has_sql') and stored_result.get('sql'):
                self.logger.info(f"✅ 找到已存储的SQL: {placeholder_id}")
                return {
                    "success": True,
                    "source": "stored",
                    "sql": stored_result['sql'],
                    "confidence": stored_result.get('confidence', 0.8),
                    "target_table": stored_result.get('target_table'),
                    "last_analysis_at": stored_result.get('last_analysis_at'),
                    "needs_analysis": False
                }
            
            # 2. 没有存储的SQL，需要分析生成
            self.logger.info(f"🔄 没有存储SQL，开始分析: {placeholder_id}")
            
            # 获取占位符信息
            placeholder_info = await self._get_placeholder_info(placeholder_id)
            if not placeholder_info:
                return {
                    "success": False,
                    "error": "找不到占位符信息",
                    "needs_analysis": False
                }
            
            # 执行分析
            result = await analyzer.analyze_placeholder(
                placeholder_id=placeholder_id,
                placeholder_text=placeholder_info['placeholder_name'],
                data_source_id=placeholder_info['data_source_id'],
                placeholder_type=placeholder_info['placeholder_type'],
                template_id=placeholder_info.get('template_id'),
                template_context={
                    'task_id': task_id,
                    'analysis_source': 'task_execution'
                },
                force_reanalyze=False
            )
            
            if result.success and result.generated_sql:
                self.logger.info(f"✅ 生成新的SQL: {placeholder_id}")
                return {
                    "success": True,
                    "source": "generated",
                    "sql": result.generated_sql,
                    "confidence": result.confidence,
                    "target_table": result.target_table,
                    "semantic_type": result.semantic_type,
                    "explanation": result.explanation,
                    "analysis_timestamp": result.analysis_timestamp.isoformat(),
                    "needs_analysis": False
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message or "SQL生成失败",
                    "needs_analysis": True
                }
                
        except Exception as e:
            self.logger.error(f"确保占位符SQL失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "needs_analysis": True
            }
    
    async def batch_ensure_placeholders_sql_for_task(self, 
                                                   placeholder_ids: List[str],
                                                   user_id: str,
                                                   task_id: str = None) -> Dict[str, Any]:
        """
        批量确保任务中的占位符都有可用的SQL
        
        Args:
            placeholder_ids: 占位符ID列表
            user_id: 用户ID 
            task_id: 任务ID（可选）
            
        Returns:
            批量处理结果
        """
        
        self.logger.info(f"🔍 批量检查任务占位符SQL: count={len(placeholder_ids)}, task_id={task_id}")
        
        results = []
        ready_count = 0
        need_analysis_count = 0
        
        for placeholder_id in placeholder_ids:
            try:
                result = await self.ensure_placeholder_sql_for_task(
                    placeholder_id, user_id, task_id
                )
                results.append({
                    "placeholder_id": placeholder_id,
                    **result
                })
                
                if result.get('success'):
                    ready_count += 1
                else:
                    need_analysis_count += 1
                    
            except Exception as e:
                self.logger.error(f"处理占位符 {placeholder_id} 失败: {e}")
                results.append({
                    "placeholder_id": placeholder_id,
                    "success": False,
                    "error": str(e),
                    "needs_analysis": True
                })
                need_analysis_count += 1
        
        return {
            "total_count": len(placeholder_ids),
            "ready_count": ready_count,
            "need_analysis_count": need_analysis_count,
            "all_ready": need_analysis_count == 0,
            "results": results
        }
    
    # ====== 私有方法 ======
    
    async def _get_template_placeholders(self, template_id: str) -> List[Dict[str, Any]]:
        """获取模版的所有占位符"""
        
        try:
            from app.models.template_placeholder import TemplatePlaceholder
            
            placeholders = (
                self.db.query(TemplatePlaceholder)
                .filter(TemplatePlaceholder.template_id == template_id)
                .all()
            )
            
            return [
                {
                    'id': p.id,
                    'placeholder_name': p.placeholder_name,
                    'placeholder_type': p.placeholder_type,
                    'template_id': p.template_id
                }
                for p in placeholders
            ]
            
        except Exception as e:
            self.logger.error(f"获取模版占位符失败: {e}")
            return []
    
    async def _get_template_data_source(self, template_id: str) -> Optional[str]:
        """获取模版关联的数据源ID"""
        
        try:
            from app.models.template import Template
            
            template = (
                self.db.query(Template)
                .filter(Template.id == template_id)
                .first()
            )
            
            return template.data_source_id if template else None
            
        except Exception as e:
            self.logger.error(f"获取模版数据源失败: {e}")
            return None
    
    async def _get_placeholder_info(self, placeholder_id: str) -> Optional[Dict[str, Any]]:
        """获取占位符信息"""
        
        try:
            from app.models.template_placeholder import TemplatePlaceholder
            from app.models.template import Template
            
            placeholder = (
                self.db.query(TemplatePlaceholder)
                .join(Template, TemplatePlaceholder.template_id == Template.id)
                .filter(TemplatePlaceholder.id == placeholder_id)
                .first()
            )
            
            if placeholder:
                return {
                    'id': placeholder.id,
                    'placeholder_name': placeholder.placeholder_name,
                    'placeholder_type': placeholder.placeholder_type,
                    'template_id': placeholder.template_id,
                    'data_source_id': placeholder.template.data_source_id
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取占位符信息失败: {e}")
            return None
    
    def _generate_analysis_summary(self, results: List[PlaceholderAnalysisResult]) -> Dict[str, Any]:
        """生成分析结果摘要"""
        
        summary = {
            "semantic_types": {},
            "confidence_distribution": {"high": 0, "medium": 0, "low": 0},
            "target_tables": {},
            "common_issues": []
        }
        
        for result in results:
            if not result.success:
                continue
            
            # 统计语义类型
            if result.semantic_type:
                summary["semantic_types"][result.semantic_type] = \
                    summary["semantic_types"].get(result.semantic_type, 0) + 1
            
            # 统计置信度分布
            if result.confidence >= 0.8:
                summary["confidence_distribution"]["high"] += 1
            elif result.confidence >= 0.6:
                summary["confidence_distribution"]["medium"] += 1
            else:
                summary["confidence_distribution"]["low"] += 1
            
            # 统计目标表
            if result.target_table:
                summary["target_tables"][result.target_table] = \
                    summary["target_tables"].get(result.target_table, 0) + 1
        
        return summary


# 便捷的工厂函数
def create_placeholder_analysis_facade(db_session: Session) -> PlaceholderAnalysisFacade:
    """创建占位符分析门面服务实例"""
    return PlaceholderAnalysisFacade(db_session)