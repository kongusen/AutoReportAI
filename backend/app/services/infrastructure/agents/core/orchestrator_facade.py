"""
用户友好的编排器门面
=====================

为多用户系统提供简洁的编排器接口，自动处理用户配置和模型选择。
"""

import logging
from typing import Dict, Any, Optional, List
from .main import AgentCoordinator
from .user_config_helper import UserConfigHelper, ensure_user_can_use_llm

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    """用户友好的LLM编排器门面"""
    
    def __init__(self):
        self.coordinator = AgentCoordinator()
        self.helper = UserConfigHelper()
        self._started = False
    
    async def start(self):
        """启动编排器"""
        if not self._started:
            await self.coordinator.start()
            self._started = True
            logger.info("LLM编排器已启动")
    
    async def stop(self):
        """停止编排器"""
        if self._started:
            await self.coordinator.stop()
            self._started = False
            logger.info("LLM编排器已停止")
    
    async def execute_llm_task(
        self,
        task_description: str,
        user_id: Optional[str] = None,
        timeout_seconds: int = 60,
        enable_streaming: bool = True
    ) -> Dict[str, Any]:
        """
        执行LLM任务（使用六步编排）
        
        Args:
            task_description: 任务描述
            user_id: 用户ID，如果未提供将自动选择可用用户
            timeout_seconds: 超时时间（秒）
            enable_streaming: 是否启用流式处理
            
        Returns:
            任务执行结果
        """
        if not self._started:
            await self.start()
        
        # 准备用户上下文
        execution_context = await self._prepare_user_context(user_id)
        if not execution_context['success']:
            return {
                'success': False,
                'error': execution_context['error'],
                'user_context': execution_context
            }
        
        try:
            # 执行任务
            result = await self.coordinator.execute_task(
                task_description=task_description,
                user_id=execution_context['user_id'],
                timeout_seconds=timeout_seconds,
                use_six_stage_orchestration=True,
                enable_streaming=enable_streaming
            )
            
            # 增强结果信息
            result['user_context'] = execution_context
            result['orchestration_method'] = 'six_stage_llm'
            
            return result
            
        except Exception as e:
            logger.error(f"LLM任务执行失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_context': execution_context
            }
    
    async def execute_simple_task(
        self,
        task_description: str,
        user_id: Optional[str] = None,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        执行简单任务（无LLM推理）
        
        Args:
            task_description: 任务描述
            user_id: 用户ID
            timeout_seconds: 超时时间
            
        Returns:
            任务执行结果
        """
        if not self._started:
            await self.start()
        
        try:
            result = await self.coordinator.execute_task(
                task_description=task_description,
                user_id=user_id,
                timeout_seconds=timeout_seconds,
                use_six_stage_orchestration=False,
                enable_streaming=False
            )
            
            result['orchestration_method'] = 'simple'
            return result
            
        except Exception as e:
            logger.error(f"简单任务执行失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'orchestration_method': 'simple'
            }
    
    async def get_user_llm_status(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户的LLM使用状态
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户LLM状态信息
        """
        try:
            # 验证用户
            is_valid = self.helper.validate_user_id(user_id)
            if not is_valid:
                return {
                    'valid_user': False,
                    'error': '用户ID无效'
                }
            
            # 获取配置
            config = self.helper.get_user_llm_config(user_id)
            
            # 检查是否能使用LLM
            can_use_llm = ensure_user_can_use_llm(user_id) is not None
            
            return {
                'valid_user': True,
                'can_use_llm': can_use_llm,
                'llm_config': config,
                'recommendations': self._get_user_recommendations(config)
            }
            
        except Exception as e:
            logger.error(f"获取用户LLM状态失败: {e}")
            return {
                'valid_user': False,
                'error': str(e)
            }
    
    async def setup_user_llm(self, user_id: str) -> Dict[str, Any]:
        """
        为用户设置LLM配置
        
        Args:
            user_id: 用户ID
            
        Returns:
            设置结果
        """
        try:
            success = self.helper.ensure_user_has_models(user_id)
            if success:
                config = self.helper.get_user_llm_config(user_id)
                return {
                    'success': True,
                    'message': '用户LLM配置设置成功',
                    'config': config
                }
            else:
                return {
                    'success': False,
                    'error': '无法为用户设置LLM配置'
                }
                
        except Exception as e:
            logger.error(f"设置用户LLM配置失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        if not self._started:
            return {'status': 'stopped'}
        
        status = await self.coordinator.get_system_status()
        status['orchestrator_type'] = 'llm_orchestrator_facade'
        return status
    
    async def _prepare_user_context(self, user_id: Optional[str]) -> Dict[str, Any]:
        """准备用户执行上下文"""
        try:
            # 确保用户能使用LLM
            execution_user_id = ensure_user_can_use_llm(user_id)
            
            if not execution_user_id:
                return {
                    'success': False,
                    'error': '无法为用户配置LLM服务',
                    'provided_user_id': user_id,
                    'user_id': None
                }
            
            # 获取用户配置
            config = self.helper.get_user_llm_config(execution_user_id)
            
            return {
                'success': True,
                'user_id': execution_user_id,
                'provided_user_id': user_id,
                'used_fallback': execution_user_id != user_id,
                'config': config
            }
            
        except Exception as e:
            logger.error(f"准备用户上下文失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'provided_user_id': user_id,
                'user_id': None
            }
    
    def _get_user_recommendations(self, config: Dict[str, Any]) -> List[str]:
        """获取用户配置建议"""
        recommendations = []
        
        if not config.get('has_config'):
            recommendations.append('建议配置默认LLM模型以获得更好的体验')
        
        if config.get('needs_setup'):
            recommendations.append('需要完成LLM服务设置')
        
        if not config.get('default_model_name'):
            recommendations.append('建议选择默认模型')
        
        if not recommendations:
            recommendations.append('LLM配置正常，可以开始使用')
        
        return recommendations


# 全局实例
_orchestrator_instance: Optional[LLMOrchestrator] = None


async def get_orchestrator() -> LLMOrchestrator:
    """获取全局编排器实例"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = LLMOrchestrator()
    return _orchestrator_instance


async def cleanup_orchestrator():
    """清理全局编排器实例"""
    global _orchestrator_instance
    if _orchestrator_instance:
        await _orchestrator_instance.stop()
        _orchestrator_instance = None


__all__ = ["LLMOrchestrator", "get_orchestrator", "cleanup_orchestrator"]