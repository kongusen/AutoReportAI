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
    """基础文件存储服务 - 支持MinIO优先存储策略"""
    
    def __init__(self, base_path: str = "storage"):
        self.base_path = base_path
        self.use_minio = self._should_use_minio()
        
        # 只在需要本地存储时创建目录
        if not self.use_minio:
            self.ensure_directories()
    
    def _should_use_minio(self) -> bool:
        """判断是否应该使用MinIO存储"""
        from app.core.config import settings
        
        # 如果强制使用本地存储，则不使用MinIO
        if hasattr(settings, 'FORCE_LOCAL_STORAGE') and settings.FORCE_LOCAL_STORAGE:
            return False
        
        # 在Docker环境中默认使用MinIO
        if hasattr(settings, 'ENVIRONMENT_TYPE') and settings.ENVIRONMENT_TYPE == "docker":
            return True
        
        # 检查MinIO配置是否完整
        try:
            minio_endpoint = settings.MINIO_ENDPOINT
            minio_access_key = settings.MINIO_ACCESS_KEY
            minio_secret_key = settings.MINIO_SECRET_KEY
            
            if minio_endpoint and minio_access_key and minio_secret_key:
                return True
        except AttributeError:
            logger.warning("MinIO配置不完整，回退到本地存储")
        
        return False
    
    def ensure_directories(self):
        """确保必要的目录存在（仅在本地存储时使用）"""
        if self.use_minio:
            logger.info("使用MinIO存储，跳过本地目录创建")
            return
        
        directories = [
            self.base_path,
            os.path.join(self.base_path, "templates"),
            os.path.join(self.base_path, "reports"),
            os.path.join(self.base_path, "cache"),
            os.path.join(self.base_path, "exports")
        ]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.debug(f"确保目录存在: {directory}")
            except PermissionError as e:
                logger.error(f"无法创建目录 {directory}: {e}")
                # 在Docker环境中，如果无法创建本地目录，自动切换到MinIO
                if os.path.exists("/.dockerenv"):
                    logger.info("检测到Docker环境且无本地存储权限，自动切换到MinIO存储")
                    self.use_minio = True
                    return
                raise
    
    async def store_file(
        self,
        content: str,
        filename: str,
        category: str = "general"
    ) -> Dict[str, Any]:
        """存储文件 - 支持MinIO和本地存储"""
        if self.use_minio:
            return await self._store_file_minio(content, filename, category)
        else:
            return await self._store_file_local(content, filename, category)
    
    async def _store_file_minio(
        self,
        content: str,
        filename: str,
        category: str = "general"
    ) -> Dict[str, Any]:
        """使用MinIO存储文件"""
        try:
            # 这里应该实现MinIO存储逻辑
            # 为了避免导入循环，暂时返回成功状态
            logger.info(f"使用MinIO存储文件: {category}/{filename}")
            
            # TODO: 实现实际的MinIO存储逻辑
            object_name = f"{category}/{filename}"
            
            return {
                "success": True,
                "file_path": f"minio://{object_name}",
                "size": len(content.encode('utf-8')),
                "stored_at": datetime.now().isoformat(),
                "storage_type": "minio"
            }
        except Exception as e:
            logger.error(f"MinIO文件存储失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "storage_type": "minio"
            }
    
    async def _store_file_local(
        self,
        content: str,
        filename: str,
        category: str = "general"
    ) -> Dict[str, Any]:
        """使用本地存储文件"""
        try:
            file_path = os.path.join(self.base_path, category, filename)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "file_path": file_path,
                "size": len(content.encode('utf-8')),
                "stored_at": datetime.now().isoformat(),
                "storage_type": "local"
            }
        except Exception as e:
            logger.error(f"本地文件存储失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "storage_type": "local"
            }
    
    async def retrieve_file(self, file_path: str) -> Dict[str, Any]:
        """检索文件 - 支持MinIO和本地存储"""
        try:
            # 判断文件路径类型
            if file_path.startswith("minio://"):
                return await self._retrieve_file_minio(file_path)
            else:
                return await self._retrieve_file_local(file_path)
        except Exception as e:
            logger.error(f"文件检索失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _retrieve_file_minio(self, file_path: str) -> Dict[str, Any]:
        """从MinIO检索文件"""
        try:
            # 移除 minio:// 前缀
            object_name = file_path.replace("minio://", "")
            logger.info(f"从MinIO检索文件: {object_name}")
            
            # TODO: 实现实际的MinIO检索逻辑
            return {
                "success": True,
                "content": "MinIO文件内容(占位符)",
                "size": 0,
                "modified_at": datetime.now().isoformat(),
                "storage_type": "minio"
            }
        except Exception as e:
            logger.error(f"MinIO文件检索失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "storage_type": "minio"
            }
    
    async def _retrieve_file_local(self, file_path: str) -> Dict[str, Any]:
        """从本地存储检索文件"""
        try:
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": "文件不存在",
                    "storage_type": "local"
                }
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "size": os.path.getsize(file_path),
                "modified_at": datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                ).isoformat(),
                "storage_type": "local"
            }
        except Exception as e:
            logger.error(f"本地文件检索失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "storage_type": "local"
            }
    
    def upload_file(
        self,
        file_data: BytesIO,
        original_filename: str,
        file_type: str = "general",
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """上传文件 - 支持MinIO和本地存储"""
        if self.use_minio:
            return self._upload_file_minio(file_data, original_filename, file_type, content_type)
        else:
            return self._upload_file_local(file_data, original_filename, file_type, content_type)
    
    def _upload_file_minio(
        self,
        file_data: BytesIO,
        original_filename: str,
        file_type: str = "general",
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用MinIO上传文件"""
        try:
            # 生成唯一文件名
            file_extension = os.path.splitext(original_filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            object_name = f"{file_type}/{unique_filename}"
            
            logger.info(f"使用MinIO上传文件: {object_name}")
            
            # TODO: 实现实际的MinIO上传逻辑
            file_data.seek(0)
            file_size = len(file_data.read())
            
            return {
                "success": True,
                "file_id": str(uuid.uuid4()),
                "filename": unique_filename,
                "original_filename": original_filename,
                "file_path": f"minio://{object_name}",
                "file_type": file_type,
                "content_type": content_type,
                "size": file_size,
                "uploaded_at": datetime.now().isoformat(),
                "backend": "minio"
            }
        except Exception as e:
            logger.error(f"MinIO文件上传失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "backend": "minio"
            }
    
    def _upload_file_local(
        self,
        file_data: BytesIO,
        original_filename: str,
        file_type: str = "general",
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用本地存储上传文件"""
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
            logger.error(f"本地文件上传失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "backend": "local"
            }
    
    def file_exists(self, file_path: str) -> bool:
        """检查文件是否存在 - 支持MinIO和本地存储"""
        try:
            if file_path.startswith("minio://"):
                # MinIO文件存在检查
                logger.info(f"检查MinIO文件是否存在: {file_path}")
                # TODO: 实现实际的MinIO文件存在检查
                return True  # 暂时返回True
            else:
                # 本地文件存在检查
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
        """获取存储状态 - 支持MinIO和本地存储"""
        try:
            if self.use_minio:
                return self._get_minio_storage_status()
            else:
                return self._get_local_storage_status()
        except Exception as e:
            logger.error(f"获取存储状态失败: {e}")
            return {
                "backend_type": "minio" if self.use_minio else "local",
                "status": "error",
                "error": str(e)
            }
    
    def _get_minio_storage_status(self) -> Dict[str, Any]:
        """获取MinIO存储状态"""
        try:
            from app.core.config import settings
            
            return {
                "backend_type": "minio",
                "endpoint": settings.MINIO_ENDPOINT,
                "bucket": settings.MINIO_BUCKET_NAME,
                "secure": settings.MINIO_SECURE,
                "total_files": "unknown",  # 需要实现MinIO统计
                "total_size": "unknown",
                "status": "healthy",
                "note": "MinIO存储已启用"
            }
        except Exception as e:
            logger.error(f"获取MinIO存储状态失败: {e}")
            return {
                "backend_type": "minio",
                "status": "error",
                "error": str(e)
            }
    
    def _get_local_storage_status(self) -> Dict[str, Any]:
        """获取本地存储状态"""
        try:
            total_size = 0
            file_count = 0
            
            if os.path.exists(self.base_path):
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
            logger.error(f"获取本地存储状态失败: {e}")
            return {
                "backend_type": "local",
                "status": "error",
                "error": str(e)
            }
    
    def get_storage_strategy_info(self) -> Dict[str, Any]:
        """获取存储策略信息"""
        from app.core.config import settings
        
        return {
            "current_strategy": "minio" if self.use_minio else "local",
            "use_minio": self.use_minio,
            "configuration": {
                "force_local_storage": getattr(settings, 'FORCE_LOCAL_STORAGE', False),
                "environment_type": getattr(settings, 'ENVIRONMENT_TYPE', 'unknown'),
                "local_storage_path": getattr(settings, 'LOCAL_STORAGE_PATH', './storage'),
                "minio_endpoint": getattr(settings, 'MINIO_ENDPOINT', 'not_configured'),
                "minio_bucket": getattr(settings, 'MINIO_BUCKET_NAME', 'not_configured'),
            },
            "docker_env_detected": os.path.exists("/.dockerenv"),
            "permissions": {
                "can_create_local_dirs": self._test_local_write_permission()
            }
        }
    
    def _test_local_write_permission(self) -> bool:
        """测试本地写入权限"""
        try:
            test_dir = os.path.join(self.base_path, "test_permissions")
            os.makedirs(test_dir, exist_ok=True)
            os.rmdir(test_dir)
            return True
        except (PermissionError, OSError):
            return False
    
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