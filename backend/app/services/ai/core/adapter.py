from __future__ import annotations

import logging
from typing import Optional, Any, Dict

from sqlalchemy.orm import Session

from .interfaces import AIServiceInterface, AIResponse


class AIServiceAdapter(AIServiceInterface):
    """将现有 UnifiedAIService 适配为统一接口"""

    def __init__(self, db_session: Optional[Session] = None, user_id: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.db_session = db_session
        self.user_id = user_id

        # 延迟加载底层服务，避免导入时循环依赖
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service

        try:
            if self.user_id:
                from app.core.ai_service_factory import UserAIServiceFactory
                factory = UserAIServiceFactory()
                self._service = factory.get_user_ai_service(self.user_id)
            else:
                from app.services.ai.integration.ai_service_enhanced import EnhancedAIService
                self._service = EnhancedAIService(db=self.db_session)
        except Exception as e:
            self.logger.error(f"Initialize AI service failed: {e}")
            self._service = None

        return self._service

    async def complete(self, prompt: str, *, model: Optional[str] = None, **kwargs) -> AIResponse:
        try:
            service = self._get_service()
            if service is None:
                return AIResponse(success=False, text="", raw=None)

            # 优先使用 UnifiedAIService 的 analyze_with_context
            context: str = kwargs.get("context", "")
            task_type: str = kwargs.get("task_type", "generic")

            result_text = await service.analyze_with_context(
                context=context,
                prompt=prompt,
                task_type=task_type,
                use_cache=kwargs.get("use_cache", True),
                use_rate_limiter=kwargs.get("use_rate_limiter", True),
            )

            return AIResponse(success=True, text=result_text, raw=result_text)
        except Exception as e:
            self.logger.error(f"AI completion failed: {e}")
            return AIResponse(success=False, text="", raw={"error": str(e)})


