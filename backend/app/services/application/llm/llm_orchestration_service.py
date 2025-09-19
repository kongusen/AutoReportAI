"""
LLM编排应用服务 - 暂时禁用版本
===============

暂时禁用此服务，因为依赖的模块尚未实现：
- orchestrator_facade
- user_config_helper

TODO: 在后续开发中重新实现这些依赖模块
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class LLMOrchestrationService:
    """
    LLM编排应用服务 - 暂时禁用
    
    TODO: 需要实现 orchestrator_facade 和 user_config_helper 模块后重新启用
    """
    
    def __init__(self):
        """初始化服务"""
        logger.warning("LLMOrchestrationService 暂时禁用，需要实现依赖模块")
    
    async def generate_sql_query(
        self, 
        user_id: str, 
        query_description: str,
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """生成SQL查询 - 暂时禁用"""
        return {
            "success": False,
            "error": "LLM编排服务暂时不可用，需要实现依赖模块",
            "sql_query": None,
            "analysis": None
        }
    
    async def analyze_data_requirements(
        self,
        user_id: str,
        business_question: str,
        context_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """分析数据需求 - 暂时禁用"""
        return {
            "success": False,
            "error": "LLM编排服务暂时不可用，需要实现依赖模块",
            "requirements": None
        }
    
    async def generate_report_template(
        self,
        user_id: str,
        template_requirements: str,
        data_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成报告模板 - 暂时禁用"""
        return {
            "success": False,
            "error": "LLM编排服务暂时不可用，需要实现依赖模块",
            "template": None
        }
    
    def get_user_llm_status(self, user_id: str) -> Dict[str, Any]:
        """获取用户LLM状态 - 暂时禁用"""
        return {
            "success": False,
            "error": "LLM编排服务暂时不可用，需要实现依赖模块",
            "status": None
        }
    
    async def reset_user_llm_state(self, user_id: str) -> Dict[str, Any]:
        """重置用户LLM状态 - 暂时禁用"""
        return {
            "success": False,
            "error": "LLM编排服务暂时不可用，需要实现依赖模块",
            "result": None
        }


# 全局服务实例（单例模式）
_orchestration_service = None


def get_llm_orchestration_service() -> LLMOrchestrationService:
    """获取LLM编排服务实例（单例）"""
    global _orchestration_service
    if _orchestration_service is None:
        _orchestration_service = LLMOrchestrationService()
    return _orchestration_service