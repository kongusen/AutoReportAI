"""
纯数据库驱动的LLM管理器 - React Agent系统核心
从数据库读取 LLM 服务器/模型，支持按任务阶段与复杂度的策略化选择
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .types import TaskRequirement, ModelSelection, LLMExecutionContext
from app.db.session import get_db_session
from app.crud.crud_llm_server import crud_llm_server
from app.crud.crud_llm_model import crud_llm_model
from app.models.llm_server import LLMModel, ModelType

logger = logging.getLogger(__name__)


class PureDatabaseLLMManager:
    """纯数据库驱动的LLM管理器"""
    
    def __init__(self):
        self.is_initialized = False
    
    async def initialize(self):
        """初始化管理器"""
        if not self.is_initialized:
            logger.info("初始化纯数据库LLM管理器")
            self.is_initialized = True
    
    async def select_best_model_for_user(
        self,
        user_id: str,
        task_type: str,
        complexity: str = "medium",
        constraints: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        stage: Optional[str] = None,
        output_kind: Optional[str] = None,
        tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """为用户选择最佳模型"""
        await self.initialize()

        constraints = constraints or {}
        need_json = constraints.get("json") is True

        # 记录模型选择上下文
        context = {
            "user_id": user_id,
            "task_type": task_type,
            "stage": stage,
            "complexity": complexity,
            "output_kind": output_kind,
            "tool_name": tool_name,
            "need_json": need_json,
            "agent_id": agent_id
        }

        logger.info(f"🤖 [ModelSelection] 开始模型选择: {context}")

        # 策略：智能确定期望的模型类型（default/think）
        desired_type = ModelType.DEFAULT.value
        strategy_reasons = []

        # 分析阶段用think模型 - 需要深度思考和规划
        if task_type in ("plan", "finalize"):
            desired_type = ModelType.THINK.value
            strategy_reasons.append("分析规划阶段")
        elif stage in ("plan", "finalize", "think", "analysis"):
            desired_type = ModelType.THINK.value
            strategy_reasons.append(f"深度分析阶段({stage})")

        # SQL生成根据复杂度智能选择
        elif tool_name == "sql.draft" or task_type == "sql_generation":
            # 简单统计用default，复杂分析用think
            context_info = str(context or {}).lower()
            if (complexity in ("low", "medium") and
                any(word in context_info for word in ["统计", "计数", "count", "sum", "总数"])):
                desired_type = ModelType.DEFAULT.value
                strategy_reasons.append("简单SQL生成任务")
            else:
                desired_type = ModelType.THINK.value
                strategy_reasons.append("复杂SQL分析任务")

        # 执行验证等操作用default模型
        elif tool_name in ("sql.validate", "sql.execute", "schema.get_columns", "schema.list_tables"):
            desired_type = ModelType.DEFAULT.value
            strategy_reasons.append(f"执行验证操作({tool_name})")

        # JSON输出需求：区分场景
        elif need_json or output_kind == "json":
            if stage in ("plan", "finalize") or task_type in ("plan", "finalize"):
                desired_type = ModelType.THINK.value
                strategy_reasons.append("分析阶段的结构化输出")
            else:
                desired_type = ModelType.DEFAULT.value
                strategy_reasons.append("执行阶段的结构化输出")

        # 高复杂度：只有分析任务才用think
        elif complexity in ("high", "complex"):
            if task_type in ("analysis", "planning", "reasoning"):
                desired_type = ModelType.THINK.value
                strategy_reasons.append("高复杂度分析任务")
            else:
                desired_type = ModelType.DEFAULT.value
                strategy_reasons.append("高复杂度执行任务")
        else:
            strategy_reasons.append("默认执行任务")

        logger.info(f"🎯 [ModelSelection] 选择策略: {desired_type} 模型，原因: {'; '.join(strategy_reasons)}")

        # 查询 DB 中活跃且健康的模型，优先当前用户的服务器
        with get_db_session() as db:
            # 如果user_id为None或"system"，直接查询全局健康模型，避免UUID转换错误
            if not user_id or user_id == "system":
                logger.info("🔄 [ModelSelection] 未提供用户ID或系统模式，直接查询全局健康模型")
                models = db.query(LLMModel).join(LLMModel.server).filter(
                    LLMModel.is_active == True,
                    LLMModel.is_healthy == True,
                    LLMModel.model_type == desired_type,
                    LLMModel.server.has(is_active=True, is_healthy=True)
                ).order_by(LLMModel.priority.asc(), LLMModel.id.asc()).all()

                user_models_count = 0  # 无用户ID时没有专属模型
            else:
                # 先找该用户的健康服务器上的健康模型
                models = db.query(LLMModel).join(LLMModel.server).filter(
                    LLMModel.is_active == True,
                    LLMModel.is_healthy == True,
                    LLMModel.model_type == desired_type,
                    LLMModel.server.has(is_active=True, is_healthy=True, user_id=user_id)
                ).order_by(LLMModel.priority.asc(), LLMModel.id.asc()).all()

                # 记录初始查询结果
                user_models_count = len(models)

            if models and user_id and user_id != "system":
                logger.info(f"🔍 [ModelSelection] 用户专属模型找到 {user_models_count} 个")
            elif not models and user_id and user_id != "system":
                logger.info("🔄 [ModelSelection] 用户专属模型未找到，回退到全局健康模型")

            # 若该用户无可用模型，回退到任意健康服务器
            if not models:
                models = db.query(LLMModel).join(LLMModel.server).filter(
                    LLMModel.is_active == True,
                    LLMModel.is_healthy == True,
                    LLMModel.model_type == desired_type,
                    LLMModel.server.has(is_active=True, is_healthy=True)
                ).order_by(LLMModel.priority.asc(), LLMModel.id.asc()).all()

                global_models_count = len(models)
                if models:
                    logger.info(f"🌐 [ModelSelection] 全局健康模型找到 {global_models_count} 个")
                else:
                    logger.warning(f"⚠️ [ModelSelection] 指定类型({desired_type})健康模型未找到，进一步回退")

            if not models:
                logger.warning(f"🚨 [ModelSelection] 没有健康的{desired_type}模型，回退到任意活跃模型")
                models = db.query(LLMModel).join(LLMModel.server).filter(
                    LLMModel.is_active == True,
                    LLMModel.server.has(is_active=True)
                ).order_by(LLMModel.priority.asc(), LLMModel.id.asc()).all()

                fallback_count = len(models)
                if models:
                    logger.warning(f"🆘 [ModelSelection] 回退模型找到 {fallback_count} 个")
                else:
                    logger.error("💥 [ModelSelection] 无任何可用模型!")

            if not models:
                logger.error(f"💥 [ModelSelection] 模型选择失败，context: {context}")
                return {
                    "model": None,
                    "provider": None,
                    "confidence": 0.0,
                    "reasoning": "没有可用的LLM模型",
                    "fallback_used": True,
                    "selection_context": context
                }

            m = models[0]
            s = m.server

            # 详细的选择结果日志
            selection_info = {
                "model_id": m.id,
                "model_name": m.name,
                "model_type": m.model_type,
                "server_id": s.id,
                "server_name": s.name,
                "provider_type": s.provider_type,
                "is_healthy": m.is_healthy,
                "is_user_owned": s.user_id == user_id,
                "priority": m.priority
            }

            confidence = 0.9 if m.model_type == ModelType.THINK.value else 0.8
            reasoning = f"选择{m.model_type}模型: {m.name} @ {s.name}"

            logger.info(f"✅ [ModelSelection] 模型选择完成: {selection_info}, confidence={confidence}")

            result = {
                "model_id": m.id,
                "server_id": s.id,
                "model": m.name,
                "provider": s.provider_type,
                "model_type": m.model_type,
                "server_name": s.name,
                "confidence": confidence,
                "reasoning": reasoning,
                "selection_context": context,
                "selection_info": selection_info,
                "fallback_used": user_models_count == 0
            }

            return result
    
    async def get_user_available_models(
        self,
        user_id: str,
        model_type: Optional[str] = None,
        provider_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取用户可用的模型列表"""
        await self.initialize()
        with get_db_session() as db:
            q = db.query(LLMModel).join(LLMModel.server).filter(
                LLMModel.is_active == True,
                LLMModel.server.has(is_active=True)
            )
            if provider_name:
                q = q.filter(LLMModel.provider_name == provider_name)
            models = q.order_by(LLMModel.priority.asc()).all()
            available = {m.name: {
                "provider": m.provider_name,
                "type": m.model_type,
                "server": m.server.name,
                "healthy": m.is_healthy
            } for m in models}
            return {
                "available_models": available,
                "total_count": len(available),
                "user_id": user_id
            }
    
    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户LLM偏好"""
        # 简单实现，实际应从数据库获取
        return {
            "preferred_provider": "anthropic",
            "max_cost_per_request": 0.05,
            "preferred_capabilities": ["reasoning", "analysis"]
        }
    
    def record_usage_feedback(
        self,
        user_id: str,
        model: str,
        provider: str,
        success: bool,
        satisfaction_score: float,
        actual_cost: Optional[float] = None,
        actual_latency: Optional[int] = None,
        agent_id: Optional[str] = None,
        task_type: Optional[str] = None
    ):
        """记录用户使用反馈"""
        logger.info(f"记录用户反馈: {user_id}, 模型: {model}, 满意度: {satisfaction_score}")
        # 实际实现应存储到数据库
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy",
            "healthy": True,
            "manager_type": "pure_database_driven",
            "available_models": len(self.available_models),
            "initialized": self.is_initialized
        }
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        with get_db_session() as db:
            total_models = db.query(LLMModel).count()
            return {
                "service_type": "pure_database_llm_manager",
                "version": "1.1.0",
                "capabilities": ["model_selection", "user_preferences", "usage_tracking"],
                "supported_providers": ["anthropic", "openai", "custom"],
                "total_models": total_models
            }


# 全局管理器实例
_pure_llm_manager = None

def get_pure_llm_manager() -> PureDatabaseLLMManager:
    """获取纯数据库LLM管理器实例"""
    global _pure_llm_manager
    if _pure_llm_manager is None:
        _pure_llm_manager = PureDatabaseLLMManager()
    return _pure_llm_manager


# 便捷接口函数
async def select_model_for_user(
    user_id: str,
    task_type: str,
    complexity: str = "medium",
    constraints: Optional[Dict[str, Any]] = None,
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """为用户选择模型"""
    manager = get_pure_llm_manager()
    return await manager.select_best_model_for_user(
        user_id, task_type, complexity, constraints, agent_id
    )


async def ask_agent(
    user_id: str,
    question: str,
    agent_type: str = "general",
    context: Optional[str] = None,
    task_type: str = "general",
    complexity: str = "medium"
) -> str:
    """Agent友好的问答接口"""
    try:
        # 延迟导入以避免循环导入
        from .model_executor import get_model_executor
        
        # 获取模型执行器
        executor = get_model_executor()
        
        # 构建任务需求
        task_requirement = TaskRequirement(
            complexity=complexity,
            domain=task_type,
            context_length=len(question) + (len(context) if context else 0),
            response_format="json",
            quality_level="high" if complexity in ["high", "complex"] else "medium"
        )
        
        # 构建完整的提示词
        full_prompt = question
        if context:
            full_prompt = f"上下文信息：{context}\n\n问题：{question}"
        
        # 执行模型调用（默认启用JSON结构化输出）
        result = await executor.execute_with_auto_selection(
            user_id=user_id,
            prompt=full_prompt,
            task_requirement=task_requirement,
            response_format={"type": "json_object"}
        )
        
        if result.get("success"):
            return result.get("result", "")
        else:
            logger.error(f"LLM调用失败: {result.get('error', 'Unknown error')}")
            return ""
            
    except Exception as e:
        logger.error(f"ask_agent调用失败: {e}")
        return ""
