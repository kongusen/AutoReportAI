"""
文件存储服务 - 基于React Agent系统
提供文件存储和管理的基础设施服务
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from io import BytesIO
import uuid

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
    
    def upload_file(
        self,
        file_data: BytesIO,
        original_filename: str,
        file_type: str = "general",
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """上传文件 - 兼容API期望的接口"""
        try:
            # 生成唯一文件名
            file_extension = os.path.splitext(original_filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # 确保目录存在
            category_path = os.path.join(self.base_path, file_type)
            os.makedirs(category_path, exist_ok=True)
            
            # 完整文件路径
            file_path = os.path.join(category_path, unique_filename)
            
            # 写入文件
            file_data.seek(0)  # 重置指针
            with open(file_path, 'wb') as f:
                f.write(file_data.read())
            
            file_size = os.path.getsize(file_path)
            
            return {
                "success": True,
                "file_id": str(uuid.uuid4()),
                "filename": unique_filename,
                "original_filename": original_filename,
                "file_path": os.path.join(file_type, unique_filename),  # 相对路径用于存储
                "file_type": file_type,
                "content_type": content_type,
                "size": file_size,
                "uploaded_at": datetime.now().isoformat(),
                "backend": "local"
            }
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def file_exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        try:
            full_path = os.path.join(self.base_path, file_path) if not os.path.isabs(file_path) else file_path
            return os.path.exists(full_path)
        except Exception:
            return False
    
    def download_file(self, file_path: str) -> tuple[bytes, str]:
        """下载文件"""
        try:
            full_path = os.path.join(self.base_path, file_path) if not os.path.isabs(file_path) else file_path
            
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            with open(full_path, 'rb') as f:
                data = f.read()
            
            return data, "local"
        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            raise
    
    def get_download_url(self, file_path: str, expires: int = 3600) -> str:
        """获取文件下载URL（本地存储返回相对路径）"""
        # 本地存储直接返回API路径
        return f"/api/v1/files/download/{file_path}"
    
    def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        try:
            full_path = os.path.join(self.base_path, file_path) if not os.path.isabs(file_path) else file_path
            
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"文件已删除: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"文件删除失败: {e}")
            return False
    
    def list_files(self, file_type: str = "", limit: int = 100) -> list[Dict[str, Any]]:
        """列出文件"""
        try:
            files = []
            
            if file_type:
                search_path = os.path.join(self.base_path, file_type)
            else:
                search_path = self.base_path
            
            if not os.path.exists(search_path):
                return []
            
            count = 0
            for root, dirs, filenames in os.walk(search_path):
                for filename in filenames:
                    if count >= limit:
                        break
                    
                    file_full_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_full_path, self.base_path)
                    
                    stat_info = os.stat(file_full_path)
                    
                    files.append({
                        "filename": filename,
                        "file_path": relative_path,
                        "file_type": os.path.basename(root) if root != self.base_path else "general",
                        "size": stat_info.st_size,
                        "created_at": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        "backend": "local"
                    })
                    count += 1
                
                if count >= limit:
                    break
            
            return files
        except Exception as e:
            logger.error(f"列出文件失败: {e}")
            return []
    
    def get_storage_status(self) -> Dict[str, Any]:
        """获取存储状态"""
        try:
            total_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(self.base_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
                    file_count += 1
            
            return {
                "backend_type": "local",
                "base_path": self.base_path,
                "total_files": file_count,
                "total_size": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "available_space": "unlimited",  # 本地存储
                "status": "healthy"
            }
        except Exception as e:
            logger.error(f"获取存储状态失败: {e}")
            return {
                "backend_type": "local",
                "status": "error",
                "error": str(e)
            }
    
    def sync_files(self, source: str, target: str) -> Dict[str, Any]:
        """同步文件（本地存储内部文件移动）"""
        try:
            source_path = os.path.join(self.base_path, source)
            target_path = os.path.join(self.base_path, target)
            
            if not os.path.exists(source_path):
                raise FileNotFoundError(f"源路径不存在: {source}")
            
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            if os.path.isdir(source_path):
                import shutil
                shutil.copytree(source_path, target_path, dirs_exist_ok=True)
            else:
                import shutil
                shutil.copy2(source_path, target_path)
            
            return {
                "success": True,
                "source": source,
                "target": target,
                "sync_type": "local_copy"
            }
        except Exception as e:
            logger.error(f"文件同步失败: {e}")
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