"""
Placeholder Configuration Service

占位符配置管理服务，提供占位符的配置和管理功能
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.template_placeholder import TemplatePlaceholder

logger = logging.getLogger(__name__)


class PlaceholderConfigService:
    """占位符配置服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_placeholder_configs(
        self, 
        template_id: str,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """获取模板的占位符配置"""
        try:
            query = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.template_id == template_id
            )
            
            if not include_inactive:
                query = query.filter(TemplatePlaceholder.is_active == True)
            
            placeholders = query.order_by(TemplatePlaceholder.execution_order).all()
            
            return [
                {
                    "id": str(p.id),
                    "name": p.placeholder_name,
                    "text": p.placeholder_text,
                    "type": p.placeholder_type,
                    "content_type": p.content_type,
                    "agent_analyzed": p.agent_analyzed,
                    "target_database": p.target_database,
                    "target_table": p.target_table,
                    "required_fields": p.required_fields,
                    "generated_sql": p.generated_sql,
                    "sql_validated": p.sql_validated,
                    "confidence_score": p.confidence_score,
                    "execution_order": p.execution_order,
                    "cache_ttl_hours": p.cache_ttl_hours,
                    "agent_config": p.agent_config,
                    "is_active": p.is_active,
                    "analyzed_at": p.analyzed_at.isoformat() if p.analyzed_at else None,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                }
                for p in placeholders
            ]
            
        except Exception as e:
            logger.error(f"获取占位符配置失败: {template_id}, 错误: {str(e)}")
            return []
    
    async def update_placeholder_config(
        self,
        placeholder_id: str,
        config_updates: Dict[str, Any]
    ) -> bool:
        """更新占位符配置"""
        try:
            placeholder = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == placeholder_id
            ).first()
            
            if not placeholder:
                logger.error(f"占位符不存在: {placeholder_id}")
                return False
            
            # 更新允许的字段
            allowed_fields = [
                'placeholder_name', 'placeholder_text', 'placeholder_type',
                'content_type', 'execution_order', 'cache_ttl_hours',
                'agent_config', 'is_active'
            ]
            
            for field, value in config_updates.items():
                if field in allowed_fields and hasattr(placeholder, field):
                    setattr(placeholder, field, value)
            
            self.db.commit()
            logger.info(f"占位符配置更新成功: {placeholder_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新占位符配置失败: {placeholder_id}, 错误: {str(e)}")
            return False
    
    async def delete_placeholder_config(self, placeholder_id: str) -> bool:
        """删除占位符配置（软删除）"""
        try:
            placeholder = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == placeholder_id
            ).first()
            
            if not placeholder:
                logger.error(f"占位符不存在: {placeholder_id}")
                return False
            
            # 软删除：设置为非活跃
            placeholder.is_active = False
            self.db.commit()
            
            logger.info(f"占位符配置删除成功: {placeholder_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除占位符配置失败: {placeholder_id}, 错误: {str(e)}")
            return False

    async def test_placeholder_query(
        self,
        placeholder_id: str,
        data_source_id: str,
        config_override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """测试占位符查询"""
        try:
            # 获取占位符配置
            placeholder = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == placeholder_id
            ).first()
            
            if not placeholder:
                return {
                    "success": False,
                    "error": "占位符不存在"
                }
            
            # 如果没有生成的SQL，返回错误
            if not placeholder.generated_sql:
                return {
                    "success": False,
                    "error": "占位符尚未分析，没有可执行的SQL"
                }
            
            # 使用Agent进行查询测试
            from app.services.agents.orchestration.cached_orchestrator import CachedAgentOrchestrator
            
            orchestrator = CachedAgentOrchestrator(self.db)
            test_result = await orchestrator._execute_single_placeholder_query(
                placeholder_id=placeholder_id,
                data_source_id=data_source_id,
                sql_override=config_override.get("sql") if config_override else None
            )
            
            return {
                "success": test_result.get("success", False),
                "data": test_result.get("data"),
                "execution_time": test_result.get("execution_time_ms", 0),
                "row_count": test_result.get("row_count", 0),
                "sql_executed": test_result.get("sql_executed"),
                "error": test_result.get("error") if not test_result.get("success") else None
            }
            
        except Exception as e:
            logger.error(f"测试占位符查询失败: {placeholder_id}, 错误: {str(e)}")
            return {
                "success": False,
                "error": f"查询测试失败: {str(e)}"
            }

    async def get_execution_history(
        self,
        placeholder_id: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """获取占位符执行历史"""
        try:
            # 从缓存表中获取执行历史
            from app.models.template_placeholder import PlaceholderValue
            
            history_records = self.db.query(PlaceholderValue).filter(
                PlaceholderValue.placeholder_id == placeholder_id
            ).order_by(
                PlaceholderValue.created_at.desc()
            ).limit(limit).all()
            
            history_data = []
            for record in history_records:
                history_data.append({
                    "id": str(record.id),
                    "executed_at": record.created_at.isoformat() if record.created_at else None,
                    "success": record.success,
                    "execution_time_ms": record.execution_time_ms,
                    "row_count": record.row_count,
                    "sql_executed": record.execution_sql,
                    "result_preview": str(record.formatted_text)[:200] if record.formatted_text else None,
                    "cache_hit": record.hit_count > 0,
                    "expires_at": record.expires_at.isoformat() if record.expires_at else None
                })
            
            return {
                "success": True,
                "history": history_data,
                "total_count": len(history_data)
            }
            
        except Exception as e:
            logger.error(f"获取占位符执行历史失败: {placeholder_id}, 错误: {str(e)}")
            return {
                "success": False,
                "error": f"获取执行历史失败: {str(e)}",
                "history": [],
                "total_count": 0
            }

    async def reanalyze_placeholder(
        self,
        placeholder_id: str,
        data_source_id: str,
        force_refresh: bool = True
    ) -> Dict[str, Any]:
        """重新分析占位符"""
        try:
            # 获取占位符配置
            placeholder = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == placeholder_id
            ).first()
            
            if not placeholder:
                return {
                    "success": False,
                    "error": "占位符不存在"
                }
            
            # 使用Agent进行重新分析
            from app.services.agents.orchestration.cached_orchestrator import CachedAgentOrchestrator
            
            orchestrator = CachedAgentOrchestrator(self.db)
            
            # 构建分析请求
            analysis_request = {
                "placeholder_text": placeholder.placeholder_text,
                "placeholder_type": placeholder.placeholder_type,
                "content_type": placeholder.content_type
            }
            
            # 执行分析
            analysis_result = await orchestrator._analyze_placeholder_with_agent(
                placeholder_id=placeholder_id,
                data_source_id=data_source_id,
                placeholder_config=analysis_request,
                force_reanalyze=force_refresh
            )
            
            if analysis_result.get("success"):
                # 更新占位符配置
                updates = {}
                if "generated_sql" in analysis_result:
                    updates["generated_sql"] = analysis_result["generated_sql"]
                    updates["sql_validated"] = True
                if "confidence_score" in analysis_result:
                    updates["confidence_score"] = analysis_result["confidence_score"]
                if "target_database" in analysis_result:
                    updates["target_database"] = analysis_result["target_database"]
                if "target_table" in analysis_result:
                    updates["target_table"] = analysis_result["target_table"]
                
                # 更新数据库记录
                if updates:
                    await self.update_placeholder_config(placeholder_id, updates)
            
            return {
                "success": analysis_result.get("success", False),
                "generated_sql": analysis_result.get("generated_sql"),
                "confidence_score": analysis_result.get("confidence_score"),
                "target_database": analysis_result.get("target_database"),
                "target_table": analysis_result.get("target_table"),
                "analysis_details": analysis_result.get("analysis_details"),
                "error": analysis_result.get("error") if not analysis_result.get("success") else None
            }
            
        except Exception as e:
            logger.error(f"重新分析占位符失败: {placeholder_id}, 错误: {str(e)}")
            return {
                "success": False,
                "error": f"重新分析失败: {str(e)}"
            }