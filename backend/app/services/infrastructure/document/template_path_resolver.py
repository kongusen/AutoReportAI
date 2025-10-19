"""
Template Path Resolver

Resolves a template_id to a local docx template path by downloading from MinIO (via HybridStorageService)
or reading from local storage, depending on configuration.
"""

import os
import tempfile
import logging
import atexit
import shutil
from typing import Optional, Dict, Any
from pathlib import Path

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 全局临时目录清理注册表
_temp_dirs_to_cleanup = set()


def _cleanup_temp_dirs():
    """清理所有注册的临时目录"""
    global _temp_dirs_to_cleanup
    for tmp_dir in _temp_dirs_to_cleanup:
        try:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
                logger.debug(f"已清理临时目录: {tmp_dir}")
        except Exception as e:
            logger.warning(f"清理临时目录失败 {tmp_dir}: {e}")
    _temp_dirs_to_cleanup.clear()


# 注册程序退出时的清理函数
atexit.register(_cleanup_temp_dirs)


def resolve_docx_template_path(db: Session, template_id: str) -> Dict[str, Any]:
    """Resolve template_id to a local docx path.

    Returns dict with keys: path, source, original_filename, storage_path, temp_dir

    Note: 调用方应该在使用完模板后调用 cleanup_template_temp_dir() 清理临时文件
    """
    from app import crud as crud_template
    from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service

    tpl = crud_template.template.get(db=db, id=template_id)
    if not tpl:
        raise ValueError(f"Template {template_id} not found in database")

    storage_path: Optional[str] = getattr(tpl, 'file_path', None)
    original_filename: Optional[str] = getattr(tpl, 'original_filename', None)
    if not storage_path:
        raise ValueError(f"Template {template_id} has no associated file_path")

    # Download from storage to temp file with retry
    storage = get_hybrid_storage_service()

    # 检查文件是否存在
    if not storage.file_exists(storage_path):
        raise FileNotFoundError(
            f"Template file not found in storage: {storage_path}. "
            f"The file may have been deleted. Please re-upload the template."
        )

    # 下载文件（带重试）
    max_retries = 3
    for attempt in range(max_retries):
        try:
            data, backend = storage.download_file(storage_path)
            logger.info(f"模板文件下载成功: {storage_path} (backend: {backend}, attempt: {attempt + 1})")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"模板下载失败 (attempt {attempt + 1}/{max_retries}): {e}，正在重试...")
                import time
                time.sleep(1 * (attempt + 1))  # 指数退避
            else:
                logger.error(f"模板下载失败，已重试 {max_retries} 次: {e}")
                raise RuntimeError(
                    f"Failed to download template from storage after {max_retries} attempts: {e}"
                )

    # Ensure docx
    ext = os.path.splitext(original_filename or '')[1].lower()
    if ext not in ('.docx', '.doc'):
        logger.warning(f"Template file is not docx/doc: {original_filename}")

    # 创建临时目录并注册清理
    tmp_dir = tempfile.mkdtemp(prefix=f"tpl_{template_id}_")
    _temp_dirs_to_cleanup.add(tmp_dir)

    local_path = os.path.join(tmp_dir, original_filename or 'template.docx')
    with open(local_path, 'wb') as f:
        f.write(data)

    logger.info(f"模板已保存到临时路径: {local_path}")

    return {
        'path': local_path,
        'source': backend,
        'original_filename': original_filename,
        'storage_path': storage_path,
        'temp_dir': tmp_dir,  # 返回临时目录路径，供清理使用
    }


def cleanup_template_temp_dir(template_meta: Dict[str, Any]):
    """清理模板临时目录

    Args:
        template_meta: resolve_docx_template_path() 返回的字典
    """
    global _temp_dirs_to_cleanup

    temp_dir = template_meta.get('temp_dir')
    if not temp_dir:
        return

    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.debug(f"已清理模板临时目录: {temp_dir}")

        # 从清理注册表中移除
        _temp_dirs_to_cleanup.discard(temp_dir)
    except Exception as e:
        logger.warning(f"清理模板临时目录失败 {temp_dir}: {e}")

