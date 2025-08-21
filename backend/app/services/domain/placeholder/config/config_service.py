"""
Placeholder Configuration Service

整合并重构原placeholder_config_service.py的功能，提供统一的配置管理
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.template_placeholder import TemplatePlaceholder
from ..core.exceptions import PlaceholderConfigError
from ..core.constants import DEFAULT_PLACEHOLDER_CONFIG
from .validation import PlaceholderConfigValidator

logger = logging.getLogger(__name__)


class PlaceholderConfigService:
    """
    统一的占位符配置服务
    
    整合原有的配置管理功能，提供更完善的配置操作
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.validator = PlaceholderConfigValidator()
    
    async def get_placeholder_configs(
        self, 
        template_id: str,
        include_inactive: bool = False,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取模板的占位符配置
        
        Args:
            template_id: 模板ID
            include_inactive: 是否包含非活跃占位符
            include_metadata: 是否包含元数据
            
        Returns:
            占位符配置列表
        """
        try:
            query = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.template_id == template_id
            )
            
            if not include_inactive:
                query = query.filter(TemplatePlaceholder.is_active == True)
            
            placeholders = query.order_by(TemplatePlaceholder.execution_order).all()
            
            configs = []
            for p in placeholders:
                config = self._build_placeholder_config(p, include_metadata)
                configs.append(config)
            
            return configs
            
        except Exception as e:
            logger.error(f"获取占位符配置失败: {template_id}, 错误: {e}")
            raise PlaceholderConfigError(f"获取配置失败: {str(e)}")
    
    async def get_placeholder_config(
        self, 
        placeholder_id: str,
        include_metadata: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        获取单个占位符配置
        
        Args:
            placeholder_id: 占位符ID
            include_metadata: 是否包含元数据
            
        Returns:
            占位符配置或None
        """
        try:
            placeholder = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == UUID(placeholder_id)
            ).first()
            
            if not placeholder:
                return None
            
            return self._build_placeholder_config(placeholder, include_metadata)
            
        except Exception as e:
            logger.error(f"获取占位符配置失败: {placeholder_id}, 错误: {e}")
            raise PlaceholderConfigError(f"获取配置失败: {str(e)}")
    
    async def update_placeholder_config(
        self, 
        placeholder_id: str, 
        config_updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新占位符配置
        
        Args:
            placeholder_id: 占位符ID
            config_updates: 配置更新数据
            
        Returns:
            更新后的配置
        """
        try:
            # 验证配置更新
            validation_result = await self.validator.validate_config_update(config_updates)
            if not validation_result["valid"]:
                raise PlaceholderConfigError(
                    f"配置验证失败: {validation_result['errors']}"
                )
            
            # 获取占位符
            placeholder = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == UUID(placeholder_id)
            ).first()
            
            if not placeholder:
                raise PlaceholderConfigError(f"占位符不存在: {placeholder_id}")
            
            # 应用配置更新
            self._apply_config_updates(placeholder, config_updates)
            
            self.db.commit()
            
            return self._build_placeholder_config(placeholder, include_metadata=True)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新占位符配置失败: {placeholder_id}, 错误: {e}")
            raise PlaceholderConfigError(f"更新配置失败: {str(e)}")
    
    async def create_placeholder_config(
        self, 
        template_id: str, 
        config_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        创建新的占位符配置
        
        Args:
            template_id: 模板ID
            config_data: 配置数据
            
        Returns:
            创建的配置
        """
        try:
            # 验证配置数据
            validation_result = await self.validator.validate_new_config(config_data)
            if not validation_result["valid"]:
                raise PlaceholderConfigError(
                    f"配置验证失败: {validation_result['errors']}"
                )
            
            # 创建占位符对象
            placeholder = self._create_placeholder_from_config(template_id, config_data)
            
            self.db.add(placeholder)
            self.db.commit()
            
            return self._build_placeholder_config(placeholder, include_metadata=True)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建占位符配置失败: {template_id}, 错误: {e}")
            raise PlaceholderConfigError(f"创建配置失败: {str(e)}")
    
    async def delete_placeholder_config(self, placeholder_id: str) -> bool:
        """
        删除占位符配置
        
        Args:
            placeholder_id: 占位符ID
            
        Returns:
            是否删除成功
        """
        try:
            placeholder = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == UUID(placeholder_id)
            ).first()
            
            if not placeholder:
                return False
            
            self.db.delete(placeholder)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除占位符配置失败: {placeholder_id}, 错误: {e}")
            raise PlaceholderConfigError(f"删除配置失败: {str(e)}")
    
    async def get_execution_history(
        self, 
        placeholder_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取占位符执行历史
        
        Args:
            placeholder_id: 占位符ID
            limit: 限制记录数
            
        Returns:
            执行历史列表
        """
        try:
            # TODO: 实现执行历史查询逻辑
            # 这里需要与新的缓存系统和执行记录系统集成
            
            return []
            
        except Exception as e:
            logger.error(f"获取执行历史失败: {placeholder_id}, 错误: {e}")
            raise PlaceholderConfigError(f"获取执行历史失败: {str(e)}")
    
    async def test_placeholder_query(
        self, 
        placeholder_id: str, 
        data_source_id: str, 
        config_override: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        测试占位符查询
        
        Args:
            placeholder_id: 占位符ID
            data_source_id: 数据源ID
            config_override: 配置覆盖
            
        Returns:
            测试结果
        """
        try:
            # TODO: 实现查询测试逻辑
            # 这里需要与新的执行服务集成
            
            return {
                "success": True,
                "message": "查询测试功能待实现",
                "placeholder_id": placeholder_id,
                "data_source_id": data_source_id
            }
            
        except Exception as e:
            logger.error(f"测试占位符查询失败: {placeholder_id}, 错误: {e}")
            raise PlaceholderConfigError(f"查询测试失败: {str(e)}")
    
    async def reanalyze_placeholder(
        self, 
        placeholder_id: str, 
        data_source_id: str, 
        force_refresh: bool = True
    ) -> Dict[str, Any]:
        """
        重新分析占位符
        
        Args:
            placeholder_id: 占位符ID
            data_source_id: 数据源ID
            force_refresh: 是否强制刷新
            
        Returns:
            分析结果
        """
        try:
            # TODO: 实现重新分析逻辑
            # 这里需要与新的分析服务集成
            
            return {
                "success": True,
                "message": "重新分析功能待实现",
                "placeholder_id": placeholder_id,
                "data_source_id": data_source_id
            }
            
        except Exception as e:
            logger.error(f"重新分析占位符失败: {placeholder_id}, 错误: {e}")
            raise PlaceholderConfigError(f"重新分析失败: {str(e)}")
    
    def _build_placeholder_config(
        self, 
        placeholder: TemplatePlaceholder, 
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """构建占位符配置对象"""
        config = {
            # 基础信息
            "id": str(placeholder.id),
            "template_id": str(placeholder.template_id),
            "placeholder_name": placeholder.placeholder_name,
            "placeholder_text": placeholder.placeholder_text,
            "placeholder_type": placeholder.placeholder_type,
            "content_type": placeholder.content_type,
            
            # 配置信息
            "description": placeholder.description or "",
            "execution_order": placeholder.execution_order or 0,
            "is_active": placeholder.is_active,
            
            # 分析信息
            "agent_analyzed": placeholder.agent_analyzed,
            "analysis_confidence": placeholder.confidence_score or 0.0,
            
            # 数据库信息
            "target_database": placeholder.target_database,
            "target_table": placeholder.target_table,
            "required_fields": placeholder.required_fields,
            
            # SQL信息
            "suggested_sql": placeholder.generated_sql,
            "optimized_sql": placeholder.generated_sql,  # Using generated_sql as base
            "validation_sql": None,  # Field not available in current model
            
            # 默认值和格式
            "default_value": None,  # Field not available in current model
            "format_template": None,  # Field not available in current model
            
            # 时间信息
            "created_at": placeholder.created_at.isoformat() if placeholder.created_at else None,
            "updated_at": placeholder.updated_at.isoformat() if placeholder.updated_at else None,
        }
        
        # 包含元数据
        if include_metadata:
            config.update({
                "extraction_metadata": placeholder.extraction_metadata or {},
                "analysis_metadata": placeholder.analysis_metadata or {},
                "execution_metadata": placeholder.execution_metadata or {},
                "runtime_config": self._get_runtime_config(placeholder)
            })
        
        return config
    
    def _get_runtime_config(self, placeholder: TemplatePlaceholder) -> Dict[str, Any]:
        """获取运行时配置"""
        return {
            **DEFAULT_PLACEHOLDER_CONFIG,
            "placeholder_type": placeholder.placeholder_type,
            "content_type": placeholder.content_type,
            "enable_agent_analysis": placeholder.agent_analyzed,
        }
    
    def _apply_config_updates(
        self, 
        placeholder: TemplatePlaceholder, 
        updates: Dict[str, Any]
    ):
        """应用配置更新"""
        # 可更新的字段映射
        updatable_fields = {
            "placeholder_name": "placeholder_name",
            "placeholder_text": "placeholder_text", 
            "placeholder_type": "placeholder_type",
            "content_type": "content_type",
            "description": "description",
            "execution_order": "execution_order",
            "is_active": "is_active",
            "target_database": "target_database",
            "target_table": "target_table",
            "required_fields": "required_fields",
            "suggested_sql": "suggested_sql",
            "default_value": "default_value",
            "format_template": "format_template"
        }
        
        # 应用更新
        for field, attr in updatable_fields.items():
            if field in updates:
                setattr(placeholder, attr, updates[field])
        
        # 更新时间戳
        from datetime import datetime
        placeholder.updated_at = datetime.utcnow()
    
    def _create_placeholder_from_config(
        self, 
        template_id: str, 
        config_data: Dict[str, Any]
    ) -> TemplatePlaceholder:
        """从配置数据创建占位符"""
        from uuid import uuid4
        from datetime import datetime
        
        return TemplatePlaceholder(
            id=uuid4(),
            template_id=UUID(template_id),
            placeholder_name=config_data["placeholder_name"],
            placeholder_text=config_data.get("placeholder_text", ""),
            placeholder_type=config_data.get("placeholder_type", "text"),
            content_type=config_data.get("content_type", "text"),
            description=config_data.get("description", ""),
            execution_order=config_data.get("execution_order", 0),
            is_active=config_data.get("is_active", True),
            agent_analyzed=False,
            confidence_score=0.0,
            created_at=datetime.utcnow()
        )