"""
文件管理API接口

提供文件上传、下载、删除和管理功能
支持MinIO和本地存储的统一接口
"""

import logging
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.core.config import settings
from app.models.user import User
from app.services.storage.file_storage_service import file_storage_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=Dict[str, Any])
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form("general"),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    上传文件到存储系统
    
    支持的文件类型:
    - general: 一般文件
    - template: 模板文件
    - report: 报告文件
    - upload: 用户上传文件
    """
    try:
        # 检查文件大小
        if file.size and file.size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件大小超过限制 {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.1f}MB"
            )
        
        # 检查文件类型
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 读取文件内容
        file_content = await file.read()
        file_stream = BytesIO(file_content)
        
        # 上传文件
        file_info = file_storage_service.upload_file(
            file_data=file_stream,
            original_filename=file.filename,
            file_type=file_type,
            content_type=file.content_type
        )
        
        # 添加用户信息
        file_info["uploaded_by"] = current_user.id
        
        logger.info(f"用户 {current_user.id} 上传文件成功: {file.filename}")
        
        return {
            "success": True,
            "message": "文件上传成功",
            "data": file_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.get("/download/{file_path:path}")
async def download_file(
    file_path: str,
    current_user: User = Depends(get_current_active_user)
) -> StreamingResponse:
    """
    下载文件
    
    Args:
        file_path: 文件路径
    """
    try:
        # 检查文件是否存在
        if not file_storage_service.file_exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 下载文件
        file_data, backend_type = file_storage_service.download_file(file_path)
        
        # 获取文件名
        filename = file_path.split("/")[-1]
        
        # 确定Content-Type
        content_type = "application/octet-stream"
        if filename.endswith(".docx"):
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.endswith(".pdf"):
            content_type = "application/pdf"
        elif filename.endswith(".xlsx"):
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif filename.endswith(".csv"):
            content_type = "text/csv"
        
        # 创建流式响应
        file_stream = BytesIO(file_data)
        
        logger.info(f"用户 {current_user.id} 下载文件: {file_path}")
        
        return StreamingResponse(
            BytesIO(file_data),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Storage-Backend": backend_type
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件下载失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")


@router.get("/url/{file_path:path}")
async def get_file_url(
    file_path: str,
    expires: int = 3600,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    获取文件访问URL
    
    Args:
        file_path: 文件路径
        expires: URL有效期（秒），默认1小时
    """
    try:
        # 检查文件是否存在
        if not file_storage_service.file_exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 获取访问URL
        download_url = file_storage_service.get_download_url(file_path, expires)
        
        return {
            "success": True,
            "data": {
                "file_path": file_path,
                "download_url": download_url,
                "expires_in": expires
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件URL失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件URL失败: {str(e)}")


@router.delete("/{file_path:path}")
async def delete_file(
    file_path: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    删除文件
    
    Args:
        file_path: 文件路径
    """
    try:
        # 检查文件是否存在
        if not file_storage_service.file_exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 删除文件
        success = file_storage_service.delete_file(file_path)
        
        if success:
            logger.info(f"用户 {current_user.id} 删除文件: {file_path}")
            return {
                "success": True,
                "message": "文件删除成功"
            }
        else:
            raise HTTPException(status_code=500, detail="文件删除失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件删除失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件删除失败: {str(e)}")


@router.get("/list")
async def list_files(
    file_type: str = "",
    limit: int = 100,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    列出文件
    
    Args:
        file_type: 文件类型筛选
        limit: 返回数量限制
    """
    try:
        files = file_storage_service.list_files(file_type, limit)
        
        return {
            "success": True,
            "data": {
                "files": files,
                "total": len(files),
                "file_type": file_type,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"列出文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"列出文件失败: {str(e)}")


@router.get("/status")
async def get_storage_status(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    获取存储系统状态
    """
    try:
        status = file_storage_service.get_storage_status()
        
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        logger.error(f"获取存储状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取存储状态失败: {str(e)}")


@router.post("/sync")
async def sync_files(
    source: str = "local",
    target: str = "minio",
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    同步文件从一个存储后端到另一个
    
    Args:
        source: 源存储后端 ("local" 或 "minio")
        target: 目标存储后端 ("local" 或 "minio")
    """
    try:
        # 验证参数
        if source not in ["local", "minio"] or target not in ["local", "minio"]:
            raise HTTPException(
                status_code=400, 
                detail="source和target必须是'local'或'minio'"
            )
        
        if source == target:
            raise HTTPException(status_code=400, detail="源和目标不能相同")
        
        # 执行同步
        result = file_storage_service.sync_files(source, target)
        
        logger.info(f"用户 {current_user.id} 执行文件同步: {source} -> {target}")
        
        return {
            "success": True,
            "message": "文件同步完成",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件同步失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件同步失败: {str(e)}")


@router.post("/batch-upload")
async def batch_upload_files(
    files: List[UploadFile] = File(...),
    file_type: str = Form("general"),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    批量上传文件
    
    Args:
        files: 文件列表
        file_type: 文件类型
    """
    try:
        uploaded_files = []
        failed_files = []
        
        total_size = sum(file.size or 0 for file in files)
        if total_size > settings.MAX_UPLOAD_SIZE * len(files):
            raise HTTPException(
                status_code=413,
                detail="批量上传总大小超过限制"
            )
        
        for file in files:
            try:
                if not file.filename:
                    failed_files.append({
                        "filename": "未知",
                        "error": "文件名不能为空"
                    })
                    continue
                
                # 读取文件内容
                file_content = await file.read()
                file_stream = BytesIO(file_content)
                
                # 上传文件
                file_info = file_storage_service.upload_file(
                    file_data=file_stream,
                    original_filename=file.filename,
                    file_type=file_type,
                    content_type=file.content_type
                )
                
                file_info["uploaded_by"] = current_user.id
                uploaded_files.append(file_info)
                
            except Exception as e:
                failed_files.append({
                    "filename": file.filename or "未知",
                    "error": str(e)
                })
        
        logger.info(f"用户 {current_user.id} 批量上传文件: 成功{len(uploaded_files)}个, 失败{len(failed_files)}个")
        
        return {
            "success": True,
            "message": f"批量上传完成: 成功{len(uploaded_files)}个, 失败{len(failed_files)}个",
            "data": {
                "uploaded_files": uploaded_files,
                "failed_files": failed_files,
                "total": len(files),
                "success_count": len(uploaded_files),
                "failed_count": len(failed_files)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量上传失败: {str(e)}")


@router.get("/exists/{file_path:path}")
async def check_file_exists(
    file_path: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    检查文件是否存在
    
    Args:
        file_path: 文件路径
    """
    try:
        exists = file_storage_service.file_exists(file_path)
        
        return {
            "success": True,
            "data": {
                "file_path": file_path,
                "exists": exists
            }
        }
        
    except Exception as e:
        logger.error(f"检查文件存在性失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"检查文件失败: {str(e)}")