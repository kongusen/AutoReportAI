"""
文件存储服务

支持MinIO对象存储和本地文件系统的混合存储机制
提供统一的文件上传、下载、删除接口，并支持降级机制
"""

import logging
import os
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

from minio import Minio
from minio.error import S3Error
from urllib3.exceptions import MaxRetryError

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageBackend:
    """存储后端基类"""
    
    def upload_file(self, file_data: BinaryIO, file_path: str, content_type: str = None) -> str:
        """上传文件"""
        raise NotImplementedError
    
    def download_file(self, file_path: str) -> bytes:
        """下载文件"""
        raise NotImplementedError
    
    def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        raise NotImplementedError
    
    def file_exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        raise NotImplementedError
    
    def get_file_url(self, file_path: str, expires: int = 3600) -> str:
        """获取文件访问URL"""
        raise NotImplementedError
    
    def list_files(self, prefix: str = "") -> List[str]:
        """列出文件"""
        raise NotImplementedError


class MinIOBackend(StorageBackend):
    """MinIO对象存储后端"""
    
    def __init__(self):
        self.client = None
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化MinIO客户端"""
        try:
            self.client = Minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            
            # 确保bucket存在
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"创建MinIO bucket: {self.bucket_name}")
            
            logger.info("MinIO客户端初始化成功")
            
        except Exception as e:
            logger.info(f"MinIO不可用，将使用本地文件存储: {str(e)}")
            self.client = None
    
    def is_available(self) -> bool:
        """检查MinIO是否可用"""
        if not self.client:
            return False
        
        try:
            # 尝试列出bucket来测试连接
            self.client.bucket_exists(self.bucket_name)
            return True
        except (S3Error, MaxRetryError, Exception) as e:
            logger.warning(f"MinIO不可用: {str(e)}")
            return False
    
    def upload_file(self, file_data: BinaryIO, file_path: str, content_type: str = None) -> str:
        """上传文件到MinIO"""
        if not self.is_available():
            raise Exception("MinIO服务不可用")
        
        try:
            # 重置文件指针
            file_data.seek(0)
            
            # 获取文件大小
            file_data.seek(0, 2)
            file_size = file_data.tell()
            file_data.seek(0)
            
            # 上传文件
            result = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=file_path,
                data=file_data,
                length=file_size,
                content_type=content_type or "application/octet-stream"
            )
            
            logger.info(f"文件上传到MinIO成功: {file_path}")
            return f"minio://{self.bucket_name}/{file_path}"
            
        except Exception as e:
            logger.error(f"文件上传到MinIO失败: {str(e)}")
            raise
    
    def download_file(self, file_path: str) -> bytes:
        """从MinIO下载文件"""
        if not self.is_available():
            raise Exception("MinIO服务不可用")
        
        try:
            response = self.client.get_object(self.bucket_name, file_path)
            data = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"从MinIO下载文件成功: {file_path}")
            return data
            
        except Exception as e:
            logger.error(f"从MinIO下载文件失败: {str(e)}")
            raise
    
    def delete_file(self, file_path: str) -> bool:
        """从MinIO删除文件"""
        if not self.is_available():
            return False
        
        try:
            self.client.remove_object(self.bucket_name, file_path)
            logger.info(f"从MinIO删除文件成功: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"从MinIO删除文件失败: {str(e)}")
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """检查MinIO中文件是否存在"""
        if not self.is_available():
            return False
        
        try:
            self.client.stat_object(self.bucket_name, file_path)
            return True
        except Exception:
            return False
    
    def get_file_url(self, file_path: str, expires: int = 3600) -> str:
        """获取MinIO文件的预签名URL"""
        if not self.is_available():
            raise Exception("MinIO服务不可用")
        
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=file_path,
                expires=timedelta(seconds=expires)
            )
            return url
            
        except Exception as e:
            logger.error(f"获取MinIO文件URL失败: {str(e)}")
            raise
    
    def list_files(self, prefix: str = "") -> List[str]:
        """列出MinIO中的文件"""
        if not self.is_available():
            return []
        
        try:
            objects = self.client.list_objects(
                self.bucket_name, 
                prefix=prefix, 
                recursive=True
            )
            return [obj.object_name for obj in objects]
            
        except Exception as e:
            logger.error(f"列出MinIO文件失败: {str(e)}")
            return []


class LocalFileSystemBackend(StorageBackend):
    """本地文件系统后端"""
    
    def __init__(self):
        self.base_path = Path(settings.LOCAL_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_full_path(self, file_path: str) -> Path:
        """获取文件的完整路径"""
        return self.base_path / file_path
    
    def upload_file(self, file_data: BinaryIO, file_path: str, content_type: str = None) -> str:
        """上传文件到本地文件系统"""
        try:
            full_path = self._get_full_path(file_path)
            
            # 确保目录存在
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            file_data.seek(0)
            with open(full_path, 'wb') as f:
                shutil.copyfileobj(file_data, f)
            
            logger.info(f"文件上传到本地成功: {full_path}")
            return f"local://{file_path}"
            
        except Exception as e:
            logger.error(f"文件上传到本地失败: {str(e)}")
            raise
    
    def download_file(self, file_path: str) -> bytes:
        """从本地文件系统下载文件"""
        try:
            full_path = self._get_full_path(file_path)
            
            if not full_path.exists():
                raise FileNotFoundError(f"文件不存在: {full_path}")
            
            with open(full_path, 'rb') as f:
                data = f.read()
            
            logger.info(f"从本地下载文件成功: {full_path}")
            return data
            
        except Exception as e:
            logger.error(f"从本地下载文件失败: {str(e)}")
            raise
    
    def delete_file(self, file_path: str) -> bool:
        """从本地文件系统删除文件"""
        try:
            full_path = self._get_full_path(file_path)
            
            if full_path.exists():
                full_path.unlink()
                logger.info(f"从本地删除文件成功: {full_path}")
                return True
            else:
                logger.warning(f"要删除的文件不存在: {full_path}")
                return False
                
        except Exception as e:
            logger.error(f"从本地删除文件失败: {str(e)}")
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """检查本地文件是否存在"""
        full_path = self._get_full_path(file_path)
        return full_path.exists()
    
    def get_file_url(self, file_path: str, expires: int = 3600) -> str:
        """获取本地文件的访问URL"""
        # 对于本地文件，返回API下载链接
        return f"{settings.API_BASE_URL}/api/v1/files/download/{file_path}"
    
    def list_files(self, prefix: str = "") -> List[str]:
        """列出本地文件"""
        try:
            prefix_path = self.base_path / prefix if prefix else self.base_path
            
            if not prefix_path.exists():
                return []
            
            files = []
            for file_path in prefix_path.rglob("*"):
                if file_path.is_file():
                    # 返回相对于base_path的路径
                    relative_path = file_path.relative_to(self.base_path)
                    files.append(str(relative_path))
            
            return files
            
        except Exception as e:
            logger.error(f"列出本地文件失败: {str(e)}")
            return []


class FileStorageService:
    """统一文件存储服务，支持MinIO和本地文件系统降级"""
    
    def __init__(self):
        self.minio_backend = MinIOBackend()
        self.local_backend = LocalFileSystemBackend()
        
        # 检查MinIO是否可用
        self.minio_available = self.minio_backend.is_available()
        
        if self.minio_available:
            logger.info("使用MinIO作为主存储后端")
        else:
            logger.warning("MinIO不可用，使用本地文件系统作为存储后端")
    
    def _get_backend(self) -> StorageBackend:
        """获取可用的存储后端"""
        if settings.FORCE_LOCAL_STORAGE:
            return self.local_backend
        
        if self.minio_available and self.minio_backend.is_available():
            return self.minio_backend
        else:
            return self.local_backend
    
    def _generate_file_path(self, original_filename: str, file_type: str = "general") -> str:
        """生成文件存储路径"""
        # 获取文件扩展名
        file_ext = Path(original_filename).suffix
        
        # 生成唯一文件名
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y/%m/%d")
        
        return f"{file_type}/{timestamp}/{unique_id}{file_ext}"
    
    def upload_file(
        self, 
        file_data: BinaryIO, 
        original_filename: str,
        file_type: str = "general",
        content_type: str = None
    ) -> Dict[str, Any]:
        """
        上传文件
        
        Args:
            file_data: 文件数据流
            original_filename: 原始文件名
            file_type: 文件类型 (report, template, upload等)
            content_type: MIME类型
            
        Returns:
            包含文件信息的字典
        """
        try:
            # 生成文件路径
            file_path = self._generate_file_path(original_filename, file_type)
            
            # 选择存储后端并上传
            backend = self._get_backend()
            storage_url = backend.upload_file(file_data, file_path, content_type)
            
            # 返回文件信息
            return {
                "file_id": str(uuid.uuid4()),
                "original_filename": original_filename,
                "file_path": file_path,
                "storage_url": storage_url,
                "storage_backend": "minio" if isinstance(backend, MinIOBackend) else "local",
                "file_type": file_type,
                "content_type": content_type,
                "upload_time": datetime.utcnow().isoformat(),
                "download_url": self.get_download_url(file_path)
            }
            
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}")
            raise
    
    def download_file(self, file_path: str) -> Tuple[bytes, str]:
        """
        下载文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            (文件数据, 存储后端类型)
        """
        try:
            backend = self._get_backend()
            
            # 首先尝试从主后端下载
            if isinstance(backend, MinIOBackend) and backend.is_available():
                try:
                    data = backend.download_file(file_path)
                    return data, "minio"
                except Exception as e:
                    logger.warning(f"从MinIO下载失败，尝试本地: {str(e)}")
                    # 降级到本地
                    backend = self.local_backend
            
            data = backend.download_file(file_path)
            backend_type = "minio" if isinstance(backend, MinIOBackend) else "local"
            return data, backend_type
            
        except Exception as e:
            logger.error(f"文件下载失败: {str(e)}")
            raise
    
    def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        try:
            success = False
            
            # 尝试从MinIO删除
            if self.minio_available:
                try:
                    success = self.minio_backend.delete_file(file_path) or success
                except Exception as e:
                    logger.warning(f"从MinIO删除文件失败: {str(e)}")
            
            # 尝试从本地删除
            try:
                success = self.local_backend.delete_file(file_path) or success
            except Exception as e:
                logger.warning(f"从本地删除文件失败: {str(e)}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        try:
            backend = self._get_backend()
            return backend.file_exists(file_path)
        except Exception:
            return False
    
    def get_download_url(self, file_path: str, expires: int = 3600) -> str:
        """获取文件下载URL"""
        try:
            backend = self._get_backend()
            return backend.get_file_url(file_path, expires)
        except Exception as e:
            logger.error(f"获取文件URL失败: {str(e)}")
            # 返回API下载链接作为备用
            return f"{settings.API_BASE_URL}/api/v1/files/download/{file_path}"
    
    def list_files(self, file_type: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """列出文件"""
        try:
            backend = self._get_backend()
            file_paths = backend.list_files(prefix=file_type)
            
            files = []
            for file_path in file_paths[:limit]:
                files.append({
                    "file_path": file_path,
                    "download_url": self.get_download_url(file_path),
                    "storage_backend": "minio" if isinstance(backend, MinIOBackend) else "local"
                })
            
            return files
            
        except Exception as e:
            logger.error(f"列出文件失败: {str(e)}")
            return []
    
    def get_storage_status(self) -> Dict[str, Any]:
        """获取存储状态"""
        return {
            "minio_available": self.minio_backend.is_available(),
            "local_available": True,  # 本地存储总是可用
            "current_backend": "minio" if (
                self.minio_available and 
                self.minio_backend.is_available() and 
                not settings.FORCE_LOCAL_STORAGE
            ) else "local",
            "force_local_storage": settings.FORCE_LOCAL_STORAGE
        }
    
    def sync_files(self, source: str = "local", target: str = "minio") -> Dict[str, Any]:
        """
        同步文件从一个存储后端到另一个
        
        Args:
            source: 源存储后端 ("local" 或 "minio")
            target: 目标存储后端 ("local" 或 "minio")
            
        Returns:
            同步结果统计
        """
        try:
            source_backend = self.local_backend if source == "local" else self.minio_backend
            target_backend = self.minio_backend if target == "minio" else self.local_backend
            
            if target == "minio" and not self.minio_backend.is_available():
                raise Exception("目标MinIO不可用")
            
            # 获取源文件列表
            source_files = source_backend.list_files()
            
            synced_count = 0
            failed_count = 0
            
            for file_path in source_files:
                try:
                    # 检查目标是否已存在
                    if target_backend.file_exists(file_path):
                        logger.info(f"文件已存在，跳过: {file_path}")
                        continue
                    
                    # 从源下载
                    file_data = source_backend.download_file(file_path)
                    
                    # 上传到目标
                    from io import BytesIO
                    target_backend.upload_file(
                        BytesIO(file_data),
                        file_path,
                        "application/octet-stream"
                    )
                    
                    synced_count += 1
                    logger.info(f"文件同步成功: {file_path}")
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"文件同步失败: {file_path}, 错误: {str(e)}")
            
            return {
                "source": source,
                "target": target,
                "total_files": len(source_files),
                "synced_count": synced_count,
                "failed_count": failed_count,
                "sync_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"文件同步失败: {str(e)}")
            raise


# 全局文件存储服务实例
file_storage_service = FileStorageService()