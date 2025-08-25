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
    
    def _extract_table_from_sql(self, sql: str) -> str:
        """从SQL中提取主要表名"""
        try:
            import re
            # 简单的表名提取，支持 FROM 和 JOIN 语句
            # 匹配 FROM table_name 或 FROM schema.table_name
            from_pattern = r'FROM\s+([`"]?)([^`"\s,()]+)\1'
            match = re.search(from_pattern, sql, re.IGNORECASE)
            if match:
                return match.group(2)
            return "未知表"
        except Exception:
            return "未知表"
    
    def _format_sample_data(self, sample_data: List[Dict[str, Any]]) -> str:
        """格式化样本数据为显示文本"""
        if not sample_data:
            return ""
        
        try:
            # 如果只有一行且只有一个值，直接返回该值
            if len(sample_data) == 1 and len(sample_data[0]) == 1:
                value = list(sample_data[0].values())[0]
                return str(value)
            
            # 如果是多行或多列，格式化为简洁的文本
            if len(sample_data) <= 3:
                formatted_parts = []
                for row in sample_data:
                    if len(row) == 1:
                        formatted_parts.append(str(list(row.values())[0]))
                    else:
                        formatted_parts.append(str(row))
                return "; ".join(formatted_parts)
            else:
                # 太多数据时只显示前几行
                return f"{len(sample_data)} 行数据"
        except Exception:
            return f"{len(sample_data)} 行数据"
    
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
            # 验证占位符ID格式
            try:
                from uuid import UUID
                placeholder_uuid = UUID(placeholder_id)
            except ValueError:
                return {
                    "success": False,
                    "error": "无效的占位符ID格式",
                    "error_message": "无效的占位符ID格式",  # 前端期望字段
                    "placeholder_id": placeholder_id,
                    "execution_status": "失败",
                    "execution_time": 0,
                    "execution_time_ms": 0,  # 前端期望字段
                    "execution_time_display": "0ms",
                    "row_count": 0,
                    "target_database": "未设置",
                    "target_table": "未设置",
                    "cache_ttl": "24小时",
                    "data": [],
                    "formatted_text": "",
                    "sql_executed": ""
                }
            
            # 获取占位符配置
            placeholder = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == placeholder_uuid
            ).first()
            
            if not placeholder:
                return {
                    "success": False,
                    "error": "占位符不存在",
                    "error_message": "占位符不存在",  # 前端期望字段
                    "placeholder_id": placeholder_id,
                    "execution_status": "失败",
                    "execution_time": 0,
                    "execution_time_ms": 0,  # 前端期望字段
                    "execution_time_display": "0ms",
                    "row_count": 0,
                    "target_database": "未设置",
                    "target_table": "未设置",
                    "cache_ttl": "24小时",
                    "data": [],
                    "formatted_text": "",
                    "sql_executed": ""
                }
            
            # 应用配置覆盖
            sql = placeholder.generated_sql
            if config_override and config_override.get("sql_query"):
                sql = config_override["sql_query"]
            
            if not sql:
                return {
                    "success": False,
                    "error": "没有可执行的SQL查询",
                    "error_message": "没有可执行的SQL查询",  # 前端期望字段
                    "placeholder_id": placeholder_id,
                    "execution_status": "失败",
                    "execution_time": 0,
                    "execution_time_ms": 0,  # 前端期望字段
                    "execution_time_display": "0ms",
                    "row_count": 0,
                    "target_database": "未设置",
                    "target_table": "未设置",
                    "cache_ttl": "24小时",
                    "data": [],
                    "formatted_text": "",
                    "sql_executed": ""
                }
            
            # 执行查询测试
            try:
                from app.services.data.connectors.connector_factory import create_connector
                from app.models.data_source import DataSource
                
                # 获取数据源
                data_source = self.db.query(DataSource).filter(
                    DataSource.id == data_source_id
                ).first()
                
                if not data_source:
                    return {
                        "success": False,
                        "error": "数据源不存在",
                        "error_message": "数据源不存在",  # 前端期望字段
                        "placeholder_id": placeholder_id,
                        "execution_status": "失败",
                        "execution_time": 0,
                        "execution_time_ms": 0,  # 前端期望字段
                        "execution_time_display": "0ms",
                        "row_count": 0,
                        "target_database": "未设置",
                        "target_table": "未设置",
                        "cache_ttl": "24小时",
                        "data": [],
                        "formatted_text": "",
                        "sql_executed": ""
                    }
                
                # 创建连接器并执行查询
                connector = create_connector(data_source)
                await connector.connect()
                
                # 添加LIMIT以避免大量数据返回
                test_sql = sql.rstrip('; \n\t')  # 移除末尾的分号和空白
                if 'LIMIT' not in test_sql.upper():
                    test_sql = f"{test_sql} LIMIT 10"
                
                result = await connector.execute_query(test_sql)
                await connector.disconnect()
                
                # 标准响应格式
                row_count = len(result.data) if hasattr(result, 'data') and not result.data.empty else 0
                sample_data = result.data.to_dict('records') if hasattr(result, 'data') and not result.data.empty else []
                execution_time_ms = int(result.execution_time * 1000) if hasattr(result, 'execution_time') else 0
                
                return {
                    "success": True,
                    "message": "查询测试成功",
                    "placeholder_id": placeholder_id,
                    "data_source_id": data_source_id,
                    "sql": test_sql,
                    "sql_executed": test_sql,  # 前端期望字段
                    # 前端期望的字段格式
                    "execution_status": "成功",
                    "execution_time": execution_time_ms,
                    "execution_time_ms": execution_time_ms,  # 前端期望字段
                    "execution_time_display": f"{result.execution_time:.3f}s" if hasattr(result, 'execution_time') else "< 1s",
                    "row_count": row_count,
                    "target_database": data_source.doris_database if data_source.doris_database else "默认数据库",
                    "target_table": self._extract_table_from_sql(test_sql),
                    "cache_ttl": "24小时",
                    # 前端期望的数据结构
                    "data": sample_data,  # 前端期望字段
                    "formatted_text": self._format_sample_data(sample_data),  # 前端期望字段
                    "result": {
                        "row_count": row_count,
                        "sample_data": sample_data,
                        "execution_time": f"{result.execution_time:.3f}s" if hasattr(result, 'execution_time') else "< 1s"
                    }
                }
                
            except Exception as exec_error:
                error_msg = str(exec_error)
                # 提供更友好的错误信息
                if "connection" in error_msg.lower() or "connect" in error_msg.lower():
                    friendly_error = "数据源连接失败，请检查数据源配置和网络连接"
                elif "authentication" in error_msg.lower() or "access denied" in error_msg.lower():
                    friendly_error = "数据源认证失败，请检查用户名和密码"
                elif "table" in error_msg.lower() and "not found" in error_msg.lower():
                    friendly_error = "SQL中引用的表不存在，请重新分析占位符"
                else:
                    friendly_error = f"查询执行失败: {error_msg}"
                
                return {
                    "success": False,
                    "error": friendly_error,
                    "error_message": friendly_error,  # 前端期望字段
                    "placeholder_id": placeholder_id,
                    "sql": sql,
                    "sql_executed": sql,  # 前端期望字段
                    "technical_details": error_msg,
                    # 前端期望的字段格式（失败状态）
                    "execution_status": "失败",
                    "execution_time": 0,
                    "execution_time_ms": 0,  # 前端期望字段
                    "execution_time_display": "0ms",
                    "row_count": 0,
                    "target_database": "未设置",
                    "target_table": "未设置",
                    "cache_ttl": "24小时",
                    # 前端期望的数据结构
                    "data": [],
                    "formatted_text": ""
                }
            
        except Exception as e:
            logger.error(f"测试占位符查询失败: {placeholder_id}, 错误: {e}")
            raise PlaceholderConfigError(f"查询测试失败: {str(e)}")
    
    async def validate_placeholder_sql(
        self, 
        placeholder_id: str, 
        data_source_id: str
    ) -> Dict[str, Any]:
        """
        验证占位符SQL查询
        
        Args:
            placeholder_id: 占位符ID
            data_source_id: 数据源ID
            
        Returns:
            验证结果
        """
        try:
            # 获取占位符配置
            placeholder = self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == placeholder_id
            ).first()
            
            if not placeholder:
                return {
                    "valid": False,
                    "error": "占位符不存在",
                    "error_type": "placeholder_not_found"
                }
            
            # 检查是否有生成的SQL
            if not placeholder.generated_sql:
                return {
                    "valid": False,
                    "error": "占位符没有生成的SQL查询",
                    "error_type": "no_sql_generated"
                }
            
            # 基本的SQL语法检查
            sql = placeholder.generated_sql.strip()
            if not sql.upper().startswith('SELECT'):
                return {
                    "valid": False,
                    "error": "SQL必须以SELECT开头",
                    "error_type": "invalid_sql_syntax",
                    "sql": sql
                }
            
            # 尝试连接数据源并验证SQL
            try:
                from app.services.data.connectors.doris_connector import DorisConnector
                from app.models.data_source import DataSource
                
                # 获取数据源配置
                data_source = self.db.query(DataSource).filter(
                    DataSource.id == data_source_id
                ).first()
                
                if not data_source:
                    return {
                        "valid": False,
                        "error": "数据源不存在",
                        "error_type": "data_source_not_found"
                    }
                
                # 创建连接器
                connector = DorisConnector.from_data_source(data_source)
                
                # 验证SQL（执行EXPLAIN或限制行数的查询）
                explain_sql = f"EXPLAIN {sql}"
                try:
                    # 首先尝试EXPLAIN
                    await connector.execute_query(explain_sql)
                    
                    # 如果EXPLAIN成功，尝试执行限制结果的查询
                    if 'LIMIT' not in sql.upper():
                        test_sql = f"{sql} LIMIT 1"
                    else:
                        test_sql = sql
                    
                    result = await connector.execute_query(test_sql)
                    
                    return {
                        "valid": True,
                        "message": "SQL验证成功",
                        "sql": sql,
                        "test_result": {
                            "row_count": len(result) if isinstance(result, list) else 1,
                            "sample_data": result[:3] if isinstance(result, list) else result
                        }
                    }
                    
                except Exception as exec_error:
                    error_msg = str(exec_error)
                    # 提供更友好的错误信息
                    if "connection" in error_msg.lower() or "connect" in error_msg.lower():
                        friendly_error = "数据源连接失败，请检查数据源配置和网络连接"
                    elif "authentication" in error_msg.lower() or "access denied" in error_msg.lower():
                        friendly_error = "数据源认证失败，请检查用户名和密码"
                    elif "table" in error_msg.lower() and "not found" in error_msg.lower():
                        friendly_error = "SQL中引用的表不存在，请重新分析占位符"
                    else:
                        friendly_error = f"SQL执行失败: {error_msg}"
                    
                    return {
                        "valid": False,
                        "error": friendly_error,
                        "error_type": "sql_execution_error",
                        "sql": sql,
                        "technical_details": error_msg
                    }
                    
            except Exception as conn_error:
                return {
                    "valid": False,
                    "error": f"数据源连接失败: {str(conn_error)}",
                    "error_type": "connection_error"
                }
            
        except Exception as e:
            logger.error(f"验证占位符SQL失败: {placeholder_id}, 错误: {e}")
            return {
                "valid": False,
                "error": f"验证过程出错: {str(e)}",
                "error_type": "validation_error"
            }
    
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
            
            # 分析信息 - 使用前端期望的字段名
            "agent_analyzed": placeholder.agent_analyzed,
            "confidence_score": placeholder.confidence_score or 0.0,  # 前端期望的字段名
            "sql_validated": placeholder.sql_validated,  # 前端期望的字段名
            
            # 数据库信息
            "target_database": placeholder.target_database,
            "target_table": placeholder.target_table,
            "required_fields": placeholder.required_fields,
            
            # SQL信息 - 使用前端期望的字段名
            "generated_sql": placeholder.generated_sql,  # 前端期望的字段名
            
            # ETL配置 - 前端期望的字段
            "cache_ttl_hours": placeholder.cache_ttl_hours or 24,
            "agent_config": placeholder.agent_config or {},
            "agent_workflow_id": placeholder.agent_workflow_id,
            
            # 时间信息
            "analyzed_at": placeholder.analyzed_at.isoformat() if placeholder.analyzed_at else None,
            "created_at": placeholder.created_at.isoformat() if placeholder.created_at else None,
            "updated_at": placeholder.updated_at.isoformat() if placeholder.updated_at else None,
        }
        
        # 包含元数据
        if include_metadata:
            config.update({
                "extraction_metadata": placeholder.agent_config or {},
                "analysis_metadata": {
                    "confidence_score": placeholder.confidence_score,
                    "analyzed_at": placeholder.analyzed_at.isoformat() if placeholder.analyzed_at else None,
                    "agent_analyzed": placeholder.agent_analyzed
                },
                "execution_metadata": {
                    "execution_order": placeholder.execution_order,
                    "cache_ttl_hours": placeholder.cache_ttl_hours,
                    "sql_validated": placeholder.sql_validated
                },
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