"""
数据验证服务模块

包含独立的SQL验证功能，用于验证占位符SQL并返回真实数据
"""

from .sql_validation_service import sql_validation_service, SQLValidationService

__all__ = ["sql_validation_service", "SQLValidationService"]