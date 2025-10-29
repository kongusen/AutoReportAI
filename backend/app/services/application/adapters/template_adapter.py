"""
模板上下文适配器

将现有的模板服务适配到 Stage-Aware Agent 系统
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TemplateContextAdapter:
    """
    模板上下文适配器

    职责：
    1. 从现有模板服务获取模板信息
    2. 转换为 Stage-Aware Agent 所需的格式
    3. 提供占位符配置和约束信息
    """

    def __init__(self, db: Session, user_id: str):
        """
        初始化适配器

        Args:
            db: 数据库会话
            user_id: 用户ID
        """
        self.db = db
        self.user_id = user_id
        self.template_service = None

        logger.debug(f"🔧 [TemplateContextAdapter] 创建适配器 - 用户: {user_id}")

    async def get_template_context(
        self,
        template_id: str,
        include_placeholders: bool = True,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        获取模板上下文

        Args:
            template_id: 模板ID
            include_placeholders: 是否包含占位符信息
            include_metadata: 是否包含元数据

        Returns:
            模板上下文字典
        """
        try:
            # 延迟初始化模板服务
            if not self.template_service:
                from app.services.domain.template.template_service import TemplateService
                self.template_service = TemplateService(self.db, self.user_id)

            logger.info(f"📋 [TemplateContextAdapter] 获取模板上下文: {template_id}")

            # 获取模板和占位符配置
            template_data = await self.template_service.get_template_with_placeholders(
                template_id=template_id,
                user_id=self.user_id,
                include_inactive=False
            )

            if not template_data:
                raise ValueError(f"模板不存在或无权限: {template_id}")

            # 转换为 Stage-Aware 所需格式
            context = {
                "template_id": template_id,
                "template_name": template_data.get("name", ""),
                "template_type": template_data.get("type", "general"),
            }

            # 添加占位符信息
            if include_placeholders:
                placeholders = template_data.get("placeholders", [])
                context["placeholders"] = self._format_placeholders(placeholders)
                context["placeholder_count"] = len(placeholders)

            # 添加元数据
            if include_metadata:
                context["metadata"] = self._extract_metadata(template_data)

            logger.info(
                f"✅ [TemplateContextAdapter] 成功获取模板上下文: {template_id}, "
                f"占位符数: {context.get('placeholder_count', 0)}"
            )

            return context

        except Exception as e:
            logger.error(f"❌ [TemplateContextAdapter] 获取模板上下文失败: {e}")
            raise

    def _format_placeholders(self, placeholders: List[Dict]) -> List[Dict]:
        """
        格式化占位符信息

        Args:
            placeholders: 原始占位符列表

        Returns:
            格式化后的占位符列表
        """
        formatted = []

        for p in placeholders:
            formatted_p = {
                "name": p.get("name", ""),
                "text": p.get("text", ""),
                "type": p.get("type", "unknown"),
                "requirements": p.get("requirements", {}),
                "constraints": p.get("constraints", {}),
            }

            # 添加其他有用字段
            if "description" in p:
                formatted_p["description"] = p["description"]

            if "example" in p:
                formatted_p["example"] = p["example"]

            if "priority" in p:
                formatted_p["priority"] = p["priority"]

            formatted.append(formatted_p)

        return formatted

    def _extract_metadata(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取模板元数据

        Args:
            template_data: 原始模板数据

        Returns:
            元数据字典
        """
        metadata = {}

        # 提取有用的元数据字段
        metadata_fields = [
            "description",
            "category",
            "tags",
            "author",
            "version",
            "created_at",
            "updated_at",
        ]

        for field in metadata_fields:
            if field in template_data:
                metadata[field] = template_data[field]

        # 提取配置信息
        if "config" in template_data:
            metadata["config"] = template_data["config"]

        return metadata

    async def get_placeholder_config(
        self,
        template_id: str,
        placeholder_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取特定占位符的配置

        Args:
            template_id: 模板ID
            placeholder_name: 占位符名称

        Returns:
            占位符配置字典，如果不存在返回 None
        """
        try:
            template_context = await self.get_template_context(
                template_id=template_id,
                include_placeholders=True,
                include_metadata=False
            )

            placeholders = template_context.get("placeholders", [])
            for p in placeholders:
                if p.get("name") == placeholder_name:
                    return p

            logger.warning(
                f"⚠️ [TemplateContextAdapter] 占位符不存在: {placeholder_name} "
                f"in template {template_id}"
            )
            return None

        except Exception as e:
            logger.error(f"❌ [TemplateContextAdapter] 获取占位符配置失败: {e}")
            return None

    async def validate_placeholder(
        self,
        template_id: str,
        placeholder_name: str
    ) -> bool:
        """
        验证占位符是否存在于模板中

        Args:
            template_id: 模板ID
            placeholder_name: 占位符名称

        Returns:
            是否存在
        """
        config = await self.get_placeholder_config(template_id, placeholder_name)
        return config is not None


__all__ = ["TemplateContextAdapter"]
