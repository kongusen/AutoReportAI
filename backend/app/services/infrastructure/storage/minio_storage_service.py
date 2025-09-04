"""
MinIO 对象存储服务
提供与 MinIO 兼容的 S3 对象存储功能
"""

import os
import logging
import uuid
from io import BytesIO
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    logger.warning("MinIO client not available. Please install: pip install minio")
    MINIO_AVAILABLE = False


class MinIOStorageService:
    """MinIO 对象存储服务"""
    
    def __init__(
        self,
        endpoint: str = "localhost:9000",
        access_key: str = "minioadmin", 
        secret_key: str = "minioadmin",
        bucket_name: str = "autoreport",
        secure: bool = False
    ):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.secure = secure
        self._client = None
        
        if not MINIO_AVAILABLE:
            raise RuntimeError("MinIO client is not available. Install with: pip install minio")
    
    @property
    def client(self) -> Minio:
        """获取 MinIO 客户端实例"""
        if self._client is None:
            try:
                self._client = Minio(
                    self.endpoint,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    secure=self.secure
                )
                # 确保存储桶存在
                self._ensure_bucket()
            except Exception as e:
                logger.error(f"Failed to initialize MinIO client: {e}")
                raise
        
        return self._client
    
    def _ensure_bucket(self):
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Failed to create bucket {self.bucket_name}: {e}")
            raise
    
    def upload_file(
        self,
        file_data: BytesIO,
        original_filename: str,
        file_type: str = "general",
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """上传文件到 MinIO"""
        try:
            # 生成唯一文件名
            file_id = str(uuid.uuid4())
            file_extension = os.path.splitext(original_filename)[1]
            filename = f"{file_id}{file_extension}"
            
            # 构建对象键
            object_name = f"{file_type}/{filename}"
            
            # 重置文件指针
            file_data.seek(0)
            file_size = len(file_data.getvalue())
            
            # 上传到 MinIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type or 'application/octet-stream'
            )
            
            logger.info(f"File uploaded to MinIO: {object_name}")
            
            return {
                "file_id": file_id,
                "filename": filename,
                "original_filename": original_filename,
                "file_path": object_name,
                "file_type": file_type,
                "content_type": content_type,
                "size": file_size,
                "uploaded_at": datetime.now().isoformat(),
                "backend": "minio"
            }
            
        except S3Error as e:
            logger.error(f"MinIO upload failed: {e}")
            raise
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            raise
    
    def file_exists(self, object_name: str) -> bool:
        """检查文件是否存在"""
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            raise
    
    def download_file(self, object_name: str) -> Tuple[bytes, str]:
        """下载文件"""
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            
            return data, "minio"
            
        except S3Error as e:
            logger.error(f"MinIO download failed: {e}")
            raise
        except Exception as e:
            logger.error(f"File download failed: {e}")
            raise
    
    def get_download_url(self, object_name: str, expires: int = 3600) -> str:
        """获取预签名下载URL"""
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=timedelta(seconds=expires)
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise
    
    def delete_file(self, object_name: str) -> bool:
        """删除文件"""
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"File deleted from MinIO: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"MinIO delete failed: {e}")
            return False
    
    def list_files(self, prefix: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """列出文件"""
        try:
            files = []
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True
            )
            
            count = 0
            for obj in objects:
                if count >= limit:
                    break
                    
                # 获取对象元数据
                stat = self.client.stat_object(self.bucket_name, obj.object_name)
                
                files.append({
                    "filename": os.path.basename(obj.object_name),
                    "file_path": obj.object_name,
                    "file_type": obj.object_name.split('/')[0] if '/' in obj.object_name else 'general',
                    "size": obj.size,
                    "content_type": stat.content_type,
                    "created_at": obj.last_modified.isoformat() if obj.last_modified else None,
                    "modified_at": obj.last_modified.isoformat() if obj.last_modified else None,
                    "etag": obj.etag
                })
                count += 1
            
            return files
            
        except S3Error as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def get_storage_status(self) -> Dict[str, Any]:
        """获取存储状态"""
        try:
            # MinIO 不直接提供总使用量，需要遍历计算
            total_size = 0
            file_count = 0
            
            try:
                objects = self.client.list_objects(self.bucket_name, recursive=True)
                for obj in objects:
                    total_size += obj.size
                    file_count += 1
            except S3Error:
                # 如果桶不存在或无权限，返回基本信息
                pass
            
            return {
                "backend_type": "minio",
                "endpoint": self.endpoint,
                "bucket_name": self.bucket_name,
                "total_files": file_count,
                "total_size": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "status": "healthy"
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage status: {e}")
            return {
                "backend_type": "minio",
                "status": "error",
                "error": str(e)
            }
    
    def sync_files(self, source: str, target: str) -> Dict[str, Any]:
        """文件同步（MinIO 到其他存储后端）"""
        # 这个功能需要与其他存储后端协调实现
        raise NotImplementedError("MinIO sync functionality not implemented yet")
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 尝试访问桶信息
            self.client.bucket_exists(self.bucket_name)
            
            return {
                "status": "healthy",
                "message": "MinIO storage service operational",
                "endpoint": self.endpoint,
                "bucket": self.bucket_name
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }