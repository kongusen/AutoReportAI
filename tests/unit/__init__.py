"""
单元测试套件
测试各个模块的独立功能，不依赖外部服务
"""

# 导入独立测试模块
from . import test_basic

__all__ = [
    "test_basic"
]
