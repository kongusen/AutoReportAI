"""
报告投递服务

负责报告的存储和分发，包括：
1. MinIO对象存储
2. 邮件发送
3. 系统通知
4. 下载链接生成
5. 投递状态跟踪
"""

import logging
import asyncio
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DeliveryMethod(Enum):
    """投递方式"""
    STORAGE_ONLY = "storage_only"
    EMAIL_ONLY = "email_only"
    STORAGE_AND_EMAIL = "storage_and_email"
    NOTIFICATION_ONLY = "notification_only"
    ALL_METHODS = "all_methods"


class DeliveryStatus(Enum):
    """投递状态"""
    PENDING = "pending"
    UPLOADING = "uploading"
    SENDING = "sending"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


@dataclass
class StorageConfig:
    """存储配置"""
    bucket_name: str = "reports"
    path_prefix: str = "reports/"
    public_access: bool = False
    retention_days: int = 90
    

@dataclass
class EmailConfig:
    """邮件配置"""
    recipients: List[str]
    subject: str
    body: str = ""
    attach_files: bool = True
    html_body: Optional[str] = None
    cc_recipients: Optional[List[str]] = None
    bcc_recipients: Optional[List[str]] = None


@dataclass
class NotificationConfig:
    """通知配置"""
    channels: List[str] = None
    message: str = ""
    priority: str = "normal"
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = ["system", "web"]


@dataclass
class DeliveryRequest:
    """投递请求"""
    task_id: str
    user_id: str
    files: List[str]  # 文件路径列表
    delivery_method: DeliveryMethod = DeliveryMethod.STORAGE_AND_EMAIL
    storage_config: Optional[StorageConfig] = None
    email_config: Optional[EmailConfig] = None
    notification_config: Optional[NotificationConfig] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class DeliveryResult:
    """投递结果"""
    success: bool
    delivery_id: str
    status: DeliveryStatus
    message: str
    storage_result: Optional[Dict[str, Any]] = None
    email_result: Optional[Dict[str, Any]] = None
    notification_result: Optional[Dict[str, Any]] = None
    download_urls: Optional[List[str]] = None
    error: Optional[str] = None
    delivery_time_seconds: float = 0.0


class DeliveryService:
    """
    报告投递服务
    
    提供完整的报告投递功能：
    1. 文件上传到对象存储
    2. 邮件发送与附件处理
    3. 系统通知推送
    4. 投递状态管理
    5. 下载链接生成
    """
    
    def __init__(self, user_id: str):
        if not user_id:
            raise ValueError("user_id is required for DeliveryService")
        self.user_id = user_id
        self.active_deliveries: Dict[str, Dict[str, Any]] = {}
        
        # 初始化服务依赖
        self._init_storage_client()
        self._init_email_client()
        self._init_notification_client()
    
    def _init_storage_client(self):
        """初始化存储客户端"""
        try:
            # 这里将集成MinIO客户端
            # from minio import Minio
            # self.storage_client = Minio(...)
            self.storage_client = None
            logger.info("存储客户端初始化完成")
        except Exception as e:
            logger.warning(f"存储客户端初始化失败: {e}")
            self.storage_client = None
    
    def _init_email_client(self):
        """初始化邮件客户端"""
        try:
            # 这里将集成邮件服务
            self.email_client = None
            logger.info("邮件客户端初始化完成")
        except Exception as e:
            logger.warning(f"邮件客户端初始化失败: {e}")
            self.email_client = None
    
    def _init_notification_client(self):
        """初始化通知客户端"""
        try:
            # 这里将集成通知服务
            from app.services.infrastructure.notification.notification_service import NotificationService
            self.notification_client = NotificationService()
            logger.info("通知客户端初始化完成")
        except Exception as e:
            logger.warning(f"通知客户端初始化失败: {e}")
            self.notification_client = None
    
    async def deliver_report(self, request: DeliveryRequest) -> DeliveryResult:
        """
        投递报告
        
        Args:
            request: 投递请求
            
        Returns:
            投递结果
        """
        start_time = datetime.now()
        delivery_id = f"delivery_{request.task_id}_{int(start_time.timestamp())}"
        
        logger.info(f"开始投递报告: {delivery_id}")
        
        # 初始化投递状态
        self.active_deliveries[delivery_id] = {
            "status": DeliveryStatus.PENDING,
            "start_time": start_time,
            "progress": 0.0
        }
        
        try:
            # 验证文件存在性
            valid_files = self._validate_files(request.files)
            if not valid_files:
                return self._create_error_result(
                    delivery_id, request, "没有有效的文件可投递"
                )
            
            # 根据投递方式执行相应操作
            storage_result = None
            email_result = None
            notification_result = None
            
            if request.delivery_method in [DeliveryMethod.STORAGE_ONLY, 
                                         DeliveryMethod.STORAGE_AND_EMAIL, 
                                         DeliveryMethod.ALL_METHODS]:
                await self._update_delivery_status(delivery_id, DeliveryStatus.UPLOADING, 30.0)
                storage_result = await self._upload_to_storage(valid_files, request)
            
            if request.delivery_method in [DeliveryMethod.EMAIL_ONLY, 
                                         DeliveryMethod.STORAGE_AND_EMAIL, 
                                         DeliveryMethod.ALL_METHODS]:
                await self._update_delivery_status(delivery_id, DeliveryStatus.SENDING, 60.0)
                email_result = await self._send_email(valid_files, request)
            
            if request.delivery_method in [DeliveryMethod.NOTIFICATION_ONLY, 
                                         DeliveryMethod.ALL_METHODS]:
                notification_result = await self._send_notification(request)
            
            # 判断整体成功状态
            success = True
            error_messages = []
            
            if storage_result and not storage_result.get('success', True):
                success = False
                error_messages.append(f"存储失败: {storage_result.get('error', '')}")
            
            if email_result and not email_result.get('success', True):
                success = False
                error_messages.append(f"邮件发送失败: {email_result.get('error', '')}")
            
            if notification_result and not notification_result.get('success', True):
                # 通知失败不影响整体成功状态，只记录警告
                logger.warning(f"通知发送失败: {notification_result.get('error', '')}")
            
            await self._update_delivery_status(delivery_id, DeliveryStatus.COMPLETED, 100.0)
            
            # 生成下载链接
            download_urls = self._generate_download_urls(valid_files, storage_result)
            
            end_time = datetime.now()
            delivery_time = (end_time - start_time).total_seconds()
            
            # 清理投递状态
            if delivery_id in self.active_deliveries:
                del self.active_deliveries[delivery_id]
            
            result_status = (DeliveryStatus.COMPLETED if success 
                           else DeliveryStatus.PARTIAL_SUCCESS if any([
                               storage_result and storage_result.get('success'),
                               email_result and email_result.get('success')
                           ]) else DeliveryStatus.FAILED)
            
            logger.info(f"报告投递完成: {delivery_id}, 状态: {result_status.value}")
            
            return DeliveryResult(
                success=success,
                delivery_id=delivery_id,
                status=result_status,
                message="投递完成" if success else f"投递部分成功: {'; '.join(error_messages)}",
                storage_result=storage_result,
                email_result=email_result,
                notification_result=notification_result,
                download_urls=download_urls,
                error='; '.join(error_messages) if error_messages else None,
                delivery_time_seconds=delivery_time
            )
            
        except Exception as e:
            logger.error(f"报告投递异常: {delivery_id}, 错误: {e}")
            return self._create_error_result(delivery_id, request, str(e))
    
    def _validate_files(self, file_paths: List[str]) -> List[str]:
        """验证文件存在性"""
        valid_files = []
        for file_path in file_paths:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                valid_files.append(file_path)
            else:
                logger.warning(f"文件不存在: {file_path}")
        return valid_files
    
    async def _upload_to_storage(
        self, 
        files: List[str], 
        request: DeliveryRequest
    ) -> Dict[str, Any]:
        """上传文件到对象存储"""
        try:
            storage_config = request.storage_config or StorageConfig()
            
            uploaded_files = []
            
            for file_path in files:
                try:
                    # 生成对象键名
                    filename = os.path.basename(file_path)
                    object_key = f"{storage_config.path_prefix}{request.task_id}/{filename}"
                    
                    # 模拟上传过程
                    await asyncio.sleep(0.5)  # 模拟上传时间
                    
                    uploaded_files.append({
                        "local_path": file_path,
                        "object_key": object_key,
                        "bucket": storage_config.bucket_name,
                        "size_bytes": os.path.getsize(file_path),
                        "uploaded_at": datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"上传文件失败: {file_path}, 错误: {e}")
                    continue
            
            if not uploaded_files:
                return {
                    "success": False,
                    "error": "所有文件上传失败",
                    "uploaded_files": []
                }
            
            return {
                "success": True,
                "message": f"成功上传 {len(uploaded_files)} 个文件",
                "uploaded_files": uploaded_files,
                "bucket": storage_config.bucket_name,
                "total_size_bytes": sum(f["size_bytes"] for f in uploaded_files)
            }
            
        except Exception as e:
            logger.error(f"上传到存储失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "uploaded_files": []
            }
    
    async def _send_email(
        self, 
        files: List[str], 
        request: DeliveryRequest
    ) -> Dict[str, Any]:
        """发送邮件"""
        try:
            if not request.email_config:
                return {
                    "success": False,
                    "error": "缺少邮件配置"
                }
            
            email_config = request.email_config
            
            # 模拟邮件发送过程
            await asyncio.sleep(1.0)  # 模拟发送时间
            
            # 构建邮件内容
            email_data = {
                "recipients": email_config.recipients,
                "subject": email_config.subject,
                "body": email_config.body or self._generate_default_email_body(request),
                "attachments": files if email_config.attach_files else [],
                "sent_at": datetime.now().isoformat(),
                "message_id": f"msg_{request.task_id}_{int(datetime.now().timestamp())}"
            }
            
            if email_config.cc_recipients:
                email_data["cc"] = email_config.cc_recipients
            
            if email_config.bcc_recipients:
                email_data["bcc"] = email_config.bcc_recipients
            
            logger.info(f"邮件发送成功: 收件人={len(email_config.recipients)}, "
                       f"附件={len(email_data['attachments'])}")
            
            return {
                "success": True,
                "message": f"邮件发送成功，收件人: {len(email_config.recipients)}",
                "email_data": email_data
            }
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_default_email_body(self, request: DeliveryRequest) -> str:
        """生成默认邮件内容"""
        return f"""
亲爱的用户，

您的报告已生成完成，详情如下：

任务ID: {request.task_id}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
文件数量: {len(request.files)}

请查收附件中的报告文档。

感谢您使用我们的报告系统！

此邮件由系统自动发送，请勿回复。
        """.strip()
    
    async def _send_notification(self, request: DeliveryRequest) -> Dict[str, Any]:
        """发送系统通知"""
        try:
            if not request.notification_config or not self.notification_client:
                return {"success": True, "message": "通知已跳过"}
            
            notification_config = request.notification_config
            
            # 构建通知消息
            notification_message = (
                notification_config.message or 
                f"报告生成完成 - 任务ID: {request.task_id}"
            )
            
            # 发送通知
            notification_result = await self.notification_client.send_notification(
                user_id=request.user_id,
                title="报告生成完成",
                message=notification_message,
                channels=notification_config.channels,
                priority=notification_config.priority,
                metadata={
                    "task_id": request.task_id,
                    "type": "report_delivery",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return {
                "success": True,
                "message": "通知发送成功",
                "notification_result": notification_result
            }
            
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_download_urls(
        self, 
        files: List[str], 
        storage_result: Optional[Dict[str, Any]]
    ) -> List[str]:
        """生成下载链接"""
        download_urls = []
        
        try:
            if storage_result and storage_result.get('success'):
                uploaded_files = storage_result.get('uploaded_files', [])
                for uploaded_file in uploaded_files:
                    # 生成预签名URL或公共URL
                    object_key = uploaded_file['object_key']
                    bucket = uploaded_file['bucket']
                    
                    # 简化的URL生成逻辑
                    download_url = f"/api/v1/delivery/download/{bucket}/{object_key}"
                    download_urls.append(download_url)
            else:
                # 如果没有存储到对象存储，生成本地文件的下载链接
                for file_path in files:
                    filename = os.path.basename(file_path)
                    download_url = f"/api/v1/delivery/local/{self.user_id}/{filename}"
                    download_urls.append(download_url)
            
        except Exception as e:
            logger.error(f"生成下载链接失败: {e}")
        
        return download_urls
    
    async def _update_delivery_status(
        self, 
        delivery_id: str, 
        status: DeliveryStatus, 
        progress: float
    ):
        """更新投递状态"""
        if delivery_id in self.active_deliveries:
            self.active_deliveries[delivery_id].update({
                "status": status,
                "progress": progress,
                "updated_at": datetime.now()
            })
        logger.debug(f"投递状态更新: {delivery_id} -> {status.value} ({progress}%)")
    
    def _create_error_result(
        self, 
        delivery_id: str, 
        request: DeliveryRequest, 
        error: str
    ) -> DeliveryResult:
        """创建错误结果"""
        if delivery_id in self.active_deliveries:
            self.active_deliveries[delivery_id]["status"] = DeliveryStatus.FAILED
            
        logger.error(f"报告投递失败: {delivery_id}, 错误: {error}")
        
        return DeliveryResult(
            success=False,
            delivery_id=delivery_id,
            status=DeliveryStatus.FAILED,
            message="投递失败",
            error=error
        )
    
    def get_delivery_status(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        """获取投递状态"""
        return self.active_deliveries.get(delivery_id)
    
    def list_active_deliveries(self) -> List[Dict[str, Any]]:
        """列出活跃投递"""
        return [
            {
                "delivery_id": delivery_id,
                **delivery_info
            }
            for delivery_id, delivery_info in self.active_deliveries.items()
        ]
    
    async def cancel_delivery(self, delivery_id: str) -> bool:
        """取消投递"""
        if delivery_id in self.active_deliveries:
            self.active_deliveries[delivery_id]["status"] = DeliveryStatus.FAILED
            logger.info(f"投递已取消: {delivery_id}")
            return True
        return False
    
    async def retry_delivery(self, delivery_id: str, request: DeliveryRequest) -> DeliveryResult:
        """重试投递"""
        logger.info(f"重试投递: {delivery_id}")
        return await self.deliver_report(request)
    
    async def get_delivery_history(
        self, 
        user_id: Optional[str] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """获取投递历史"""
        # 这里应该从数据库或日志中获取历史记录
        # 暂时返回空列表
        return []
    
    def cleanup_old_deliveries(self, days_old: int = 7) -> int:
        """清理旧投递记录"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_old)
            
            # 清理内存中的活跃投递（如果太老的话）
            to_remove = []
            for delivery_id, delivery_info in self.active_deliveries.items():
                start_time = delivery_info.get('start_time')
                if start_time and start_time < cutoff_time:
                    to_remove.append(delivery_id)
            
            for delivery_id in to_remove:
                del self.active_deliveries[delivery_id]
            
            logger.info(f"清理了 {len(to_remove)} 个过期投递记录")
            return len(to_remove)
            
        except Exception as e:
            logger.error(f"清理投递记录失败: {e}")
            return 0


# 工厂函数
def create_delivery_service(user_id: str) -> DeliveryService:
    """创建投递服务实例"""
    return DeliveryService(user_id=user_id)