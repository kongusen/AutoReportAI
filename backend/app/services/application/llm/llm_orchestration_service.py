"""
LLM编排应用服务
===============

业务层面的LLM编排服务，提供统一的LLM任务执行接口。
基于用户友好的编排器门面，为应用层提供简洁的API。

架构位置: Application Layer (应用服务层)
职责: 封装业务逻辑，协调基础设施层组件，提供高级API
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import HTTPException

from app.services.infrastructure.agents.core.orchestrator_facade import get_orchestrator
from app.services.infrastructure.agents.core.user_config_helper import UserConfigHelper

logger = logging.getLogger(__name__)


class LLMOrchestrationService:
    """
    LLM编排应用服务
    
    提供高级的业务API：
    1. SQL查询生成
    2. 数据需求分析  
    3. 报告模板生成
    4. 用户LLM状态管理
    """
    
    def __init__(self):
        self._orchestrator = None
        self._helper = UserConfigHelper()
    
    async def _get_orchestrator(self):
        """获取编排器实例（懒加载）"""
        if self._orchestrator is None:
            self._orchestrator = await get_orchestrator()
        return self._orchestrator
    
    async def generate_sql_query(
        self, 
        user_id: str, 
        query_description: str,
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        生成SQL查询
        
        Args:
            user_id: 用户ID
            query_description: 查询描述，如"查询最近30天的订单数量"
            timeout_seconds: 超时时间
            
        Returns:
            包含生成的SQL和分析结果的字典
        """
        try:
            orchestrator = await self._get_orchestrator()
            
            # 构建专门的SQL生成任务描述
            task_description = f"基于以下描述生成SQL查询语句: {query_description}"
            
            result = await orchestrator.execute_llm_task(
                task_description=task_description,
                user_id=user_id,
                timeout_seconds=timeout_seconds
            )
            
            if not result.get('success'):
                raise HTTPException(
                    status_code=500,
                    detail=f"SQL生成失败: {result.get('error', '未知错误')}"
                )
            
            # 提取并格式化结果
            final_result = result.get('result', {})
            return {
                'success': True,
                'sql_query': final_result.get('generated_sql', ''),
                'explanation': final_result.get('llm_analysis', ''),
                'confidence': final_result.get('confidence', 0.8),
                'execution_time': result.get('execution_time', 0),
                'llm_participated': result.get('llm_participated', False)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"SQL查询生成失败: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"系统错误: {str(e)}"
            )
    
    async def analyze_data_requirements(
        self,
        user_id: str,
        business_question: str,
        context_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分析数据需求
        
        Args:
            user_id: 用户ID
            business_question: 业务问题，如"我想了解用户留存率趋势"
            context_info: 上下文信息（表结构、历史查询等）
            
        Returns:
            数据需求分析结果
        """
        try:
            orchestrator = await self._get_orchestrator()
            
            task_description = f"分析以下业务问题的数据需求: {business_question}"
            if context_info:
                task_description += f"\n上下文信息: {context_info}"
            
            result = await orchestrator.execute_llm_task(
                task_description=task_description,
                user_id=user_id
            )
            
            if not result.get('success'):
                raise HTTPException(
                    status_code=500,
                    detail=f"数据需求分析失败: {result.get('error')}"
                )
            
            final_result = result.get('result', {})
            return {
                'success': True,
                'analysis': final_result.get('llm_analysis', ''),
                'recommended_approach': final_result.get('message', ''),
                'confidence': final_result.get('confidence', 0.8)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"数据需求分析失败: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"分析错误: {str(e)}"
            )
    
    async def generate_report_template(
        self,
        user_id: str,
        report_type: str,
        data_sources: List[str],
        target_audience: str = "business_users"
    ) -> Dict[str, Any]:
        """
        生成报告模板
        
        Args:
            user_id: 用户ID
            report_type: 报告类型，如"销售分析"、"用户行为分析"
            data_sources: 数据源列表
            target_audience: 目标受众
            
        Returns:
            报告模板生成结果
        """
        try:
            orchestrator = await self._get_orchestrator()
            
            task_description = f"""
            生成{report_type}报告模板，要求：
            - 数据源: {', '.join(data_sources)}
            - 目标受众: {target_audience}
            - 包含关键指标和可视化建议
            """
            
            result = await orchestrator.execute_llm_task(
                task_description=task_description,
                user_id=user_id,
                timeout_seconds=90  # 报告生成可能需要更长时间
            )
            
            if not result.get('success'):
                raise HTTPException(
                    status_code=500,
                    detail=f"报告模板生成失败: {result.get('error')}"
                )
            
            final_result = result.get('result', {})
            return {
                'success': True,
                'template': final_result.get('llm_analysis', ''),
                'suggestions': final_result.get('structured_analysis', {}),
                'confidence': final_result.get('confidence', 0.8)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"报告模板生成失败: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"生成错误: {str(e)}"
            )
    
    async def check_user_llm_status(self, user_id: str) -> Dict[str, Any]:
        """
        检查用户LLM服务状态
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户LLM状态信息
        """
        try:
            orchestrator = await self._get_orchestrator()
            status = await orchestrator.get_user_llm_status(user_id)
            
            return {
                'user_id': user_id,
                'can_use_llm': status.get('can_use_llm', False),
                'has_config': status.get('llm_config', {}).get('has_config', False),
                'default_model': status.get('llm_config', {}).get('default_model_name', 'none'),
                'recommendations': status.get('recommendations', []),
                'needs_setup': status.get('llm_config', {}).get('needs_setup', True)
            }
            
        except Exception as e:
            logger.error(f"检查用户LLM状态失败: {e}")
            return {
                'user_id': user_id,
                'can_use_llm': False,
                'error': str(e),
                'needs_setup': True
            }
    
    async def setup_user_llm_if_needed(self, user_id: str) -> bool:
        """
        如果需要，为用户设置LLM配置
        
        Args:
            user_id: 用户ID
            
        Returns:
            设置是否成功
        """
        try:
            # 检查是否需要设置
            status = await self.check_user_llm_status(user_id)
            if not status.get('needs_setup', True):
                return True  # 已经配置好了
            
            orchestrator = await self._get_orchestrator()
            setup_result = await orchestrator.setup_user_llm(user_id)
            
            if setup_result.get('success'):
                logger.info(f"成功为用户 {user_id} 设置LLM配置")
                return True
            else:
                logger.warning(f"为用户 {user_id} 设置LLM配置失败: {setup_result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"用户LLM配置设置异常: {e}")
            return False


# 全局服务实例
_service_instance: Optional[LLMOrchestrationService] = None


def get_llm_orchestration_service() -> LLMOrchestrationService:
    """获取LLM编排服务实例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = LLMOrchestrationService()
    return _service_instance


__all__ = ["LLMOrchestrationService", "get_llm_orchestration_service"]