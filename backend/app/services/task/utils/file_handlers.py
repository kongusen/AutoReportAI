"""
File Handlers

文件处理工具，负责：
- 报告文件管理
- 文件清理
- 文件验证
"""

import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class FileHandlers:
    """文件处理工具类"""
    
    def __init__(self):
        self.reports_dir = Path(settings.REPORTS_DIR) if hasattr(settings, 'REPORTS_DIR') else Path("reports")
        self.uploads_dir = Path(settings.UPLOADS_DIR) if hasattr(settings, 'UPLOADS_DIR') else Path("uploads")
        
        # 确保目录存在
        self.reports_dir.mkdir(exist_ok=True)
        self.uploads_dir.mkdir(exist_ok=True)
    
    def save_report_file(
        self,
        content: str,
        filename: str,
        task_id: int
    ) -> Optional[str]:
        """
        保存报告文件
        
        Args:
            content: 文件内容
            filename: 文件名
            task_id: 任务ID
            
        Returns:
            文件路径
        """
        try:
            # 创建任务目录
            task_dir = self.reports_dir / str(task_id)
            task_dir.mkdir(exist_ok=True)
            
            # 生成文件路径
            file_path = task_dir / filename
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"报告文件已保存 - 任务ID: {task_id}, 路径: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"保存报告文件失败 - 任务ID: {task_id}: {e}")
            return None
    
    def save_binary_file(
        self,
        data: bytes,
        filename: str,
        task_id: int
    ) -> Optional[str]:
        """
        保存二进制文件
        
        Args:
            data: 文件数据
            filename: 文件名
            task_id: 任务ID
            
        Returns:
            文件路径
        """
        try:
            # 创建任务目录
            task_dir = self.reports_dir / str(task_id)
            task_dir.mkdir(exist_ok=True)
            
            # 生成文件路径
            file_path = task_dir / filename
            
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(data)
            
            logger.info(f"二进制文件已保存 - 任务ID: {task_id}, 路径: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"保存二进制文件失败 - 任务ID: {task_id}: {e}")
            return None
    
    def get_report_file_path(self, task_id: int, filename: str) -> Optional[str]:
        """
        获取报告文件路径
        
        Args:
            task_id: 任务ID
            filename: 文件名
            
        Returns:
            文件路径
        """
        try:
            file_path = self.reports_dir / str(task_id) / filename
            
            if file_path.exists():
                return str(file_path)
            else:
                logger.warning(f"报告文件不存在 - 任务ID: {task_id}, 文件名: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"获取报告文件路径失败 - 任务ID: {task_id}: {e}")
            return None
    
    def delete_report_files(self, task_id: int) -> bool:
        """
        删除任务的所有报告文件
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否删除成功
        """
        try:
            task_dir = self.reports_dir / str(task_id)
            
            if task_dir.exists():
                shutil.rmtree(task_dir)
                logger.info(f"任务报告文件已删除 - 任务ID: {task_id}")
                return True
            else:
                logger.warning(f"任务报告目录不存在 - 任务ID: {task_id}")
                return True
                
        except Exception as e:
            logger.error(f"删除任务报告文件失败 - 任务ID: {task_id}: {e}")
            return False
    
    def cleanup_old_files(self, days: int = 30) -> int:
        """
        清理旧文件
        
        Args:
            days: 保留天数
            
        Returns:
            删除的文件数量
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            # 清理报告目录
            for task_dir in self.reports_dir.iterdir():
                if task_dir.is_dir():
                    try:
                        # 检查目录修改时间
                        dir_mtime = datetime.fromtimestamp(task_dir.stat().st_mtime)
                        
                        if dir_mtime < cutoff_date:
                            shutil.rmtree(task_dir)
                            deleted_count += 1
                            logger.info(f"已删除旧报告目录: {task_dir}")
                            
                    except Exception as e:
                        logger.warning(f"删除旧报告目录失败: {task_dir}, 错误: {e}")
            
            # 清理上传目录
            for file_path in self.uploads_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        # 检查文件修改时间
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        if file_mtime < cutoff_date:
                            file_path.unlink()
                            deleted_count += 1
                            logger.info(f"已删除旧上传文件: {file_path}")
                            
                    except Exception as e:
                        logger.warning(f"删除旧上传文件失败: {file_path}, 错误: {e}")
            
            logger.info(f"文件清理完成，共删除 {deleted_count} 个文件/目录")
            return deleted_count
            
        except Exception as e:
            logger.error(f"文件清理失败: {e}")
            return 0
    
    def get_file_size(self, file_path: str) -> Optional[int]:
        """
        获取文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件大小（字节）
        """
        try:
            path = Path(file_path)
            if path.exists():
                return path.stat().st_size
            else:
                return None
                
        except Exception as e:
            logger.error(f"获取文件大小失败: {file_path}, 错误: {e}")
            return None
    
    def validate_file_path(self, file_path: str) -> bool:
        """
        验证文件路径
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否有效
        """
        try:
            path = Path(file_path)
            
            # 检查路径是否在允许的目录内
            if not (path.is_relative_to(self.reports_dir) or path.is_relative_to(self.uploads_dir)):
                logger.warning(f"文件路径不在允许的目录内: {file_path}")
                return False
            
            # 检查文件是否存在
            if not path.exists():
                logger.warning(f"文件不存在: {file_path}")
                return False
            
            # 检查是否为文件
            if not path.is_file():
                logger.warning(f"路径不是文件: {file_path}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证文件路径失败: {file_path}, 错误: {e}")
            return False
    
    def get_task_files(self, task_id: int) -> List[str]:
        """
        获取任务的所有文件
        
        Args:
            task_id: 任务ID
            
        Returns:
            文件路径列表
        """
        try:
            task_dir = self.reports_dir / str(task_id)
            
            if not task_dir.exists():
                return []
            
            files = []
            for file_path in task_dir.iterdir():
                if file_path.is_file():
                    files.append(str(file_path))
            
            return files
            
        except Exception as e:
            logger.error(f"获取任务文件失败 - 任务ID: {task_id}: {e}")
            return []
    
    def copy_file(self, src_path: str, dst_path: str) -> bool:
        """
        复制文件
        
        Args:
            src_path: 源文件路径
            dst_path: 目标文件路径
            
        Returns:
            是否复制成功
        """
        try:
            src = Path(src_path)
            dst = Path(dst_path)
            
            if not src.exists():
                logger.error(f"源文件不存在: {src_path}")
                return False
            
            # 确保目标目录存在
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            # 复制文件
            shutil.copy2(src, dst)
            
            logger.info(f"文件复制成功: {src_path} -> {dst_path}")
            return True
            
        except Exception as e:
            logger.error(f"文件复制失败: {src_path} -> {dst_path}, 错误: {e}")
            return False
    
    def get_storage_usage(self) -> dict:
        """
        获取存储使用情况
        
        Returns:
            存储使用信息
        """
        try:
            reports_size = self._get_directory_size(self.reports_dir)
            uploads_size = self._get_directory_size(self.uploads_dir)
            total_size = reports_size + uploads_size
            
            return {
                "reports_size": reports_size,
                "uploads_size": uploads_size,
                "total_size": total_size,
                "reports_size_mb": reports_size / (1024 * 1024),
                "uploads_size_mb": uploads_size / (1024 * 1024),
                "total_size_mb": total_size / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"获取存储使用情况失败: {e}")
            return {
                "reports_size": 0,
                "uploads_size": 0,
                "total_size": 0,
                "reports_size_mb": 0,
                "uploads_size_mb": 0,
                "total_size_mb": 0
            }
    
    def _get_directory_size(self, directory: Path) -> int:
        """获取目录大小"""
        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.warning(f"计算目录大小失败: {directory}, 错误: {e}")
        
        return total_size
