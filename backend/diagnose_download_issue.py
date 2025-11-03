#!/usr/bin/env python3
"""
诊断下载问题的脚本
用于检查MinIO存储、数据库记录和下载接口
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import get_db_session
from app.models.report_history import ReportHistory
from app.models.task import Task
from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_latest_report():
    """检查最新的report记录"""
    with get_db_session() as db:
        # 获取最近的5条report记录
        reports = db.query(ReportHistory).order_by(
            ReportHistory.id.desc()
        ).limit(5).all()

        logger.info(f"\n{'='*80}")
        logger.info(f"📋 最近的5条报告记录:")
        logger.info(f"{'='*80}\n")

        for i, report in enumerate(reports, 1):
            logger.info(f"[{i}] Report ID: {report.id}")
            logger.info(f"    Task ID: {report.task_id}")
            logger.info(f"    Status: {report.status}")
            logger.info(f"    File Path: {report.file_path}")
            logger.info(f"    File Size: {report.file_size} bytes")
            logger.info(f"    Generated At: {report.generated_at}")

            # 检查关联的task
            if report.task:
                logger.info(f"    Task Name: {report.task.name}")
                logger.info(f"    Task Owner: {report.task.owner_id}")

            # 检查文件是否存在
            if report.file_path:
                storage = get_hybrid_storage_service()
                file_exists = storage.file_exists(report.file_path)
                logger.info(f"    ✅ 文件存在于存储: {file_exists}")

                # 尝试下载文件
                if file_exists:
                    try:
                        file_data, backend = storage.download_file(report.file_path)
                        actual_size = len(file_data)
                        logger.info(f"    ✅ 文件可下载: 大小={actual_size} bytes, 后端={backend}")

                        # 检查文件内容
                        if actual_size > 0:
                            # 检查是否是有效的docx文件（PK头部）
                            if file_data[:2] == b'PK':
                                logger.info(f"    ✅ 文件是有效的ZIP/DOCX格式")
                            else:
                                logger.warning(f"    ⚠️  文件头部: {file_data[:10]}")
                        else:
                            logger.error(f"    ❌ 文件大小为0")

                    except Exception as e:
                        logger.error(f"    ❌ 文件下载失败: {e}")
            else:
                logger.warning(f"    ⚠️  没有file_path")

            logger.info("")


def check_minio_files():
    """检查MinIO中的文件列表"""
    logger.info(f"\n{'='*80}")
    logger.info(f"📦 MinIO存储中的文件:")
    logger.info(f"{'='*80}\n")

    storage = get_hybrid_storage_service()
    backend_info = storage.get_backend_info()

    logger.info(f"存储后端类型: {backend_info['backend_type']}")
    logger.info(f"MinIO可用: {backend_info['is_minio_available']}")
    logger.info(f"强制本地: {backend_info.get('force_local', False)}")
    logger.info("")

    # 列出reports目录下的文件
    files = storage.list_files(file_type="reports", limit=10)

    logger.info(f"找到 {len(files)} 个报告文件:")
    for i, file_info in enumerate(files, 1):
        logger.info(f"[{i}] {file_info.get('file_path')}")
        logger.info(f"    大小: {file_info.get('size', 0)} bytes")
        logger.info(f"    后端: {file_info.get('backend', 'unknown')}")
        logger.info(f"    创建时间: {file_info.get('created_at')}")
        logger.info("")


def check_task_execution_results():
    """检查Task执行结果"""
    logger.info(f"\n{'='*80}")
    logger.info(f"🔍 检查Task执行结果:")
    logger.info(f"{'='*80}\n")

    with get_db_session() as db:
        from app.models.task import TaskExecution

        # 获取最近的5条执行记录
        executions = db.query(TaskExecution).order_by(
            TaskExecution.id.desc()
        ).limit(5).all()

        for i, execution in enumerate(executions, 1):
            logger.info(f"[{i}] Execution ID: {execution.id}")
            logger.info(f"    Task ID: {execution.task_id}")
            logger.info(f"    Status: {execution.execution_status}")

            # 检查execution_result中的report信息
            result = execution.execution_result or {}
            report_info = result.get('report', {})

            if report_info:
                logger.info(f"    Report Storage Path: {report_info.get('storage_path')}")
                logger.info(f"    Report Backend: {report_info.get('backend')}")
                logger.info(f"    Report Size: {report_info.get('size')} bytes")
                logger.info(f"    Friendly Name: {report_info.get('friendly_name')}")
            else:
                logger.warning(f"    ⚠️  没有report信息")

            logger.info("")


def test_download_api():
    """测试下载API的逻辑"""
    logger.info(f"\n{'='*80}")
    logger.info(f"🧪 测试下载API逻辑:")
    logger.info(f"{'='*80}\n")

    with get_db_session() as db:
        # 获取最新的completed report
        report = db.query(ReportHistory).filter(
            ReportHistory.status == 'completed'
        ).order_by(ReportHistory.id.desc()).first()

        if not report:
            logger.error("❌ 没有找到completed状态的报告")
            return

        logger.info(f"测试报告 ID: {report.id}")
        logger.info(f"文件路径: {report.file_path}")
        logger.info(f"状态: {report.status}")
        logger.info("")

        # 模拟下载接口的逻辑
        if not report.file_path:
            logger.error("❌ 报告没有file_path")
            return

        storage = get_hybrid_storage_service()

        # 检查文件是否存在
        if not storage.file_exists(report.file_path):
            logger.error(f"❌ 文件不存在于存储系统: {report.file_path}")
            return

        logger.info("✅ 文件存在于存储系统")

        # 尝试下载
        try:
            file_data, backend_type = storage.download_file(report.file_path)
            logger.info(f"✅ 文件下载成功")
            logger.info(f"   大小: {len(file_data)} bytes")
            logger.info(f"   后端: {backend_type}")

            # 检查文件头
            if len(file_data) > 10:
                logger.info(f"   文件头: {file_data[:10]}")
                if file_data[:2] == b'PK':
                    logger.info("   ✅ 有效的DOCX文件格式")
                else:
                    logger.warning("   ⚠️  不是标准的DOCX格式")

            # 模拟生成文件名
            if report.task:
                task_name = report.task.name
            else:
                task_name = f"报告_{report.id}"

            from datetime import datetime
            date_str = report.generated_at.strftime("%Y-%m-%d") if report.generated_at else datetime.now().strftime("%Y-%m-%d")
            file_ext = report.file_path.split('.')[-1] if '.' in report.file_path else 'docx'
            filename = f"{date_str}-{task_name}.{file_ext}"

            logger.info(f"   生成的文件名: {filename}")

            # 模拟Content-Disposition
            from urllib.parse import quote
            ascii_filename = filename.encode('ascii', 'ignore').decode('ascii')
            encoded_filename = quote(filename)

            logger.info(f"   ASCII文件名: {ascii_filename}")
            logger.info(f"   编码后文件名: {encoded_filename}")
            logger.info(f"   Content-Disposition: attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}")

        except Exception as e:
            logger.error(f"❌ 下载失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    try:
        print("\n" + "="*80)
        print("🔍 AutoReportAI 下载问题诊断工具")
        print("="*80 + "\n")

        # 运行所有检查
        check_latest_report()
        check_minio_files()
        check_task_execution_results()
        test_download_api()

        print("\n" + "="*80)
        print("✅ 诊断完成！")
        print("="*80 + "\n")

    except Exception as e:
        logger.error(f"❌ 诊断过程出错: {e}")
        import traceback
        traceback.print_exc()
