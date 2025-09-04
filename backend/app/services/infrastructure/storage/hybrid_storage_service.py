"""
混合存储服务
根据配置自动选择本地存储或 MinIO 存储
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from io import BytesIO

from app.core.config import settings
from .file_storage_service import FileStorageService
from .minio_storage_service import MinIOStorageService, MINIO_AVAILABLE

logger = logging.getLogger(__name__)


class HybridStorageService:
    """混合存储服务，支持本地存储和 MinIO 存储"""
    
    def __init__(self):
        self.backend_type = self._determine_backend()
        self._storage_service = None
        
        logger.info(f"Initialized hybrid storage with backend: {self.backend_type}")
    
    def _determine_backend(self) -> str:
        """确定使用的存储后端"""
        # 如果强制使用本地存储
        if getattr(settings, 'FORCE_LOCAL_STORAGE', False):
            return "local"
        
        # 如果 MinIO 不可用，使用本地存储
        if not MINIO_AVAILABLE:
            logger.warning("MinIO not available, falling back to local storage")
            return "local"
        
        # 检查 MinIO 配置是否完整
        minio_config = {
            'endpoint': getattr(settings, 'MINIO_ENDPOINT', None),
            'access_key': getattr(settings, 'MINIO_ACCESS_KEY', None),
            'secret_key': getattr(settings, 'MINIO_SECRET_KEY', None),
            'bucket_name': getattr(settings, 'MINIO_BUCKET_NAME', None)
        }
        
        if all(minio_config.values()):
            return "minio"
        else:
            logger.warning("MinIO configuration incomplete, using local storage")
            return "local"
    
    @property
    def storage_service(self):
        """获取存储服务实例"""
        if self._storage_service is None:
            if self.backend_type == "minio":
                try:
                    self._storage_service = MinIOStorageService(
                        endpoint=settings.MINIO_ENDPOINT,
                        access_key=settings.MINIO_ACCESS_KEY,
                        secret_key=settings.MINIO_SECRET_KEY,
                        bucket_name=settings.MINIO_BUCKET_NAME,
                        secure=getattr(settings, 'MINIO_SECURE', False)
                    )
                except Exception as e:
                    logger.error(f"Failed to initialize MinIO storage: {e}")
                    logger.info("Falling back to local storage")
                    self.backend_type = "local"
                    self._storage_service = FileStorageService(
                        base_path=getattr(settings, 'LOCAL_STORAGE_PATH', 'storage')
                    )
            else:
                self._storage_service = FileStorageService(
                    base_path=getattr(settings, 'LOCAL_STORAGE_PATH', 'storage')
                )
        
        return self._storage_service
    
    def upload_file(
        self,
        file_data: BytesIO,
        original_filename: str,
        file_type: str = "general",
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """上传文件"""
        result = self.storage_service.upload_file(
            file_data, original_filename, file_type, content_type
        )
        result["backend"] = self.backend_type
        return result
    
    def file_exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        return self.storage_service.file_exists(file_path)
    
    def download_file(self, file_path: str) -> Tuple[bytes, str]:
        """下载文件"""
        return self.storage_service.download_file(file_path)
    
    def get_download_url(self, file_path: str, expires: int = 3600) -> str:
        """获取文件下载URL"""
        return self.storage_service.get_download_url(file_path, expires)
    
    def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        return self.storage_service.delete_file(file_path)
    
    def list_files(self, file_type: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """列出文件"""
        files = self.storage_service.list_files(file_type, limit)
        # 为每个文件添加后端信息
        for file_info in files:
            file_info["backend"] = self.backend_type
        return files
    
    def get_storage_status(self) -> Dict[str, Any]:
        """获取存储状态"""
        status = self.storage_service.get_storage_status()
        status["active_backend"] = self.backend_type
        return status
    
    def sync_files(self, source: str, target: str) -> Dict[str, Any]:
        """同步文件"""
        if self.backend_type == "local":
            return self.storage_service.sync_files(source, target)
        else:
            # MinIO 同步需要特殊处理
            raise NotImplementedError("MinIO sync not implemented yet")
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        result = self.storage_service.health_check()
        result["backend_type"] = self.backend_type
        return result
    
    def get_backend_info(self) -> Dict[str, Any]:
        """获取当前后端信息"""
        return {
            "backend_type": self.backend_type,
            "is_minio_available": MINIO_AVAILABLE,
            "force_local": getattr(settings, 'FORCE_LOCAL_STORAGE', False)
        }


# 全局实例
_hybrid_storage_service = None

def get_hybrid_storage_service() -> HybridStorageService:
    """获取混合存储服务实例"""
    global _hybrid_storage_service
    if _hybrid_storage_service is None:
        _hybrid_storage_service = HybridStorageService()
    return _hybrid_storage_service

# 为了向后兼容，保持原有接口
hybrid_storage_service = get_hybrid_storage_service()