"""
Template 层工厂

提供占位符提取器与相关依赖的构造，避免 `template` 直接依赖 `placeholder` 子模块细节，
用于打破 `template ↔ placeholder` 的循环依赖。
"""

from __future__ import annotations

from typing import Any
from sqlalchemy.orm import Session

from app.services.application.interfaces.extraction_interfaces import PlaceholderExtractorInterface


def create_placeholder_extractor_for_template(db: Session) -> PlaceholderExtractorInterface:
    """为 Template 层提供占位符提取器实例。

    通过统一的入口间接依赖 `app.services.placeholder`，避免 `template` 深入依赖其实现细节。
    """
    # 延迟导入，避免在导入期触发循环依赖
    from app.services.domain.placeholder import create_placeholder_extractor
    from app.services.domain.template.services.template_domain_service import TemplateParser
    parser = TemplateParser()
    return create_placeholder_extractor(db, template_parser=parser)


