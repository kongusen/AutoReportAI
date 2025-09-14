"""
用户配置辅助工具
===========================

为多用户系统提供用户相关的配置管理，包括模型选择、权限验证等。
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.crud.crud_user import crud_user
from app.crud.crud_llm_model import crud_llm_model
from app.crud.crud_llm_server import crud_llm_server
from app.models.user_llm_preference import UserLLMPreference

logger = logging.getLogger(__name__)


class UserConfigHelper:
    """用户配置辅助类"""
    
    @staticmethod
    def validate_user_id(user_id: str, db: Optional[Session] = None) -> bool:
        """验证用户ID是否有效"""
        if not user_id or user_id == "system":
            return False
            
        should_close_db = db is None
        if db is None:
            db = SessionLocal()
            
        try:
            # 检查用户是否存在
            user = crud_user.get(db, id=user_id)
            return user is not None
        except Exception as e:
            logger.error(f"验证用户ID失败: {e}")
            return False
        finally:
            if should_close_db:
                db.close()
    
    @staticmethod
    def get_user_llm_config(user_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
        """获取用户的LLM配置信息"""
        should_close_db = db is None
        if db is None:
            db = SessionLocal()
            
        try:
            # 检查用户偏好
            preference = db.query(UserLLMPreference).filter_by(user_id=user_id).first()
            
            if not preference:
                logger.info(f"用户 {user_id} 没有LLM偏好配置，使用默认配置")
                return {
                    'has_config': False,
                    'default_server_id': None,
                    'default_model_name': None,
                    'needs_setup': True
                }
            
            return {
                'has_config': True,
                'default_server_id': preference.default_llm_server_id,
                'default_model_name': preference.default_model_name,
                'preferred_temperature': preference.preferred_temperature,
                'max_tokens_limit': preference.max_tokens_limit,
                'needs_setup': False
            }
            
        except Exception as e:
            logger.error(f"获取用户LLM配置失败: {e}")
            return {'has_config': False, 'needs_setup': True, 'error': str(e)}
        finally:
            if should_close_db:
                db.close()
    
    @staticmethod
    def ensure_user_has_models(user_id: str, db: Optional[Session] = None) -> bool:
        """确保用户有可用的模型配置"""
        should_close_db = db is None
        if db is None:
            db = SessionLocal()
            
        try:
            # 检查用户是否已有配置
            config = UserConfigHelper.get_user_llm_config(user_id, db)
            if config.get('has_config'):
                return True
            
            logger.info(f"为用户 {user_id} 设置默认模型配置")
            
            # 查找可用的服务器和模型
            servers = crud_llm_server.get_multi_by_filter(
                db, is_active=True, is_healthy=True
            )
            
            if not servers:
                logger.warning("系统中没有可用的LLM服务器")
                return False
            
            # 使用第一个可用服务器
            default_server = servers[0]
            
            # 查找该服务器上的可用模型
            models = crud_llm_model.get_models_by_filter(
                db, server_id=default_server.id, is_active=True, is_healthy=True
            )
            
            if not models:
                logger.warning(f"服务器 {default_server.name} 上没有可用的模型")
                return False
            
            # 使用第一个可用模型
            default_model = models[0]
            
            # 创建用户偏好
            preference = UserLLMPreference(
                user_id=user_id,
                default_llm_server_id=default_server.id,
                default_model_name=default_model.name
            )
            db.add(preference)
            
            # 确保服务器与用户关联
            if not default_server.user_id:
                default_server.user_id = user_id
            
            db.commit()
            
            logger.info(f"成功为用户 {user_id} 配置默认模型: {default_model.name}")
            return True
            
        except Exception as e:
            logger.error(f"设置用户默认模型配置失败: {e}")
            db.rollback()
            return False
        finally:
            if should_close_db:
                db.close()
    
    @staticmethod
    def get_fallback_user_id(db: Optional[Session] = None) -> Optional[str]:
        """获取备用用户ID（通常是第一个admin用户）"""
        should_close_db = db is None
        if db is None:
            db = SessionLocal()
            
        try:
            # 查找admin用户
            admin_users = db.query(crud_user.model).filter_by(is_superuser=True).limit(1).all()
            if admin_users:
                return str(admin_users[0].id)
            
            # 如果没有admin，使用第一个用户
            users = crud_user.get_multi(db, limit=1)
            if users:
                return str(users[0].id)
                
            return None
            
        except Exception as e:
            logger.error(f"获取备用用户ID失败: {e}")
            return None
        finally:
            if should_close_db:
                db.close()


def ensure_user_can_use_llm(user_id: Optional[str]) -> Optional[str]:
    """
    确保用户能够使用LLM服务
    
    Args:
        user_id: 用户ID，可以为None
        
    Returns:
        可用的用户ID，如果无法提供LLM服务则返回None
    """
    helper = UserConfigHelper()
    
    # 如果没有提供用户ID，尝试获取备用用户ID
    if not user_id or user_id == "system":
        logger.info("未提供用户ID，尝试使用备用用户")
        user_id = helper.get_fallback_user_id()
        if not user_id:
            logger.error("无法找到可用的用户ID")
            return None
    
    # 验证用户ID
    if not helper.validate_user_id(user_id):
        logger.error(f"用户ID {user_id} 无效")
        return None
    
    # 确保用户有模型配置
    if not helper.ensure_user_has_models(user_id):
        logger.error(f"无法为用户 {user_id} 配置LLM模型")
        return None
    
    return user_id


__all__ = ["UserConfigHelper", "ensure_user_can_use_llm"]