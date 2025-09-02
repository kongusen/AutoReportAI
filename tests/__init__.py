"""
AutoReportAI 测试套件

组织结构:
- agent/: React Agent相关测试
- api/: API端点测试
- charts/: 图表生成测试
- docker/: Docker环境测试
- e2e/: 端到端测试
- integration/: 集成测试
- minio/: 对象存储测试
- performance/: 性能测试
- unit/: 单元测试
"""

__version__ = "1.0.0"
__all__ = [
    "agent",
    "api", 
    "charts",
    "docker",
    "e2e",
    "integration", 
    "minio",
    "performance",
    "unit"
]