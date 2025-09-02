"""
文件存储服务 - 基于React Agent系统
提供文件存储和管理的基础设施服务
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FileStorageService:
    """基础文件存储服务"""
    
    def __init__(self, base_path: str = "storage"):
        self.base_path = base_path
        self.ensure_directories()
    
    def ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.base_path,
            os.path.join(self.base_path, "templates"),
            os.path.join(self.base_path, "reports"),
            os.path.join(self.base_path, "cache"),
            os.path.join(self.base_path, "exports")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    async def store_file(
        self,
        content: str,
        filename: str,
        category: str = "general"
    ) -> Dict[str, Any]:
        """存储文件"""
        try:
            file_path = os.path.join(self.base_path, category, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "file_path": file_path,
                "size": len(content.encode('utf-8')),
                "stored_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"文件存储失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def retrieve_file(self, file_path: str) -> Dict[str, Any]:
        """检索文件"""
        try:
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": "文件不存在"
                }
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "size": os.path.getsize(file_path),
                "modified_at": datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                ).isoformat()
            }
        except Exception as e:
            logger.error(f"文件检索失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查存储目录是否可访问
            test_file = os.path.join(self.base_path, ".health_check")
            with open(test_file, 'w') as f:
                f.write("health_check")
            
            # 清理测试文件
            if os.path.exists(test_file):
                os.remove(test_file)
            
            return {
                "status": "healthy",
                "message": "File storage service operational",
                "base_path": self.base_path
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# 全局实例
_file_storage_service = None

def get_file_storage_service() -> FileStorageService:
    """获取文件存储服务实例"""
    global _file_storage_service
    if _file_storage_service is None:
        _file_storage_service = FileStorageService()
    return _file_storage_service

# React Agent架构全局实例
file_storage_service = get_file_storage_service()