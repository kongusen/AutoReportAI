#!/usr/bin/env python3
"""
清理孤立的模板记录
检查数据库中的所有模板记录，删除在MinIO存储中不存在的模板记录
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# 设置环境变量
os.environ.setdefault('APP_ENV', 'development')

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import SessionLocal
from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service

def normalize_path(file_path: str) -> str:
    """标准化文件路径 - 去掉minio://前缀"""
    if file_path.startswith("minio://"):
        return file_path[8:]
    return file_path

def cleanup_orphan_templates(db: Session, dry_run: bool = True):
    """
    清理孤立的模板记录

    Args:
        db: 数据库会话
        dry_run: 如果为True，只显示将要删除的记录，不实际删除
    """
    storage = get_hybrid_storage_service()

    # 直接使用SQL查询所有模板
    query = text("""
        SELECT id, name, file_path, original_filename, created_at
        FROM templates
        ORDER BY created_at DESC
    """)
    result = db.execute(query)
    templates = result.fetchall()

    print(f"\n{'='*80}")
    print(f"检查 {len(templates)} 个模板记录...")
    print(f"模式: {'DRY RUN（仅检查）' if dry_run else '实际删除'}")
    print(f"{'='*80}\n")

    orphan_templates = []
    valid_templates = []

    for template in templates:
        # 从SQL查询结果中获取字段（Row对象）
        template_id = str(template.id)
        template_name = template.name
        file_path = template.file_path
        original_filename = template.original_filename or ''

        if not file_path:
            print(f"⚠️  模板 [{template_name}] (ID: {template_id}) 没有 file_path，跳过")
            continue

        # 标准化路径
        normalized_path = normalize_path(file_path)

        # 检查文件是否存在
        try:
            exists = storage.file_exists(file_path)
            if exists:
                valid_templates.append({
                    'id': template_id,
                    'name': template_name,
                    'file_path': file_path,
                    'normalized_path': normalized_path
                })
                print(f"✓ 模板 [{template_name}] - 文件存在: {normalized_path}")
            else:
                orphan_templates.append({
                    'id': template_id,
                    'name': template_name,
                    'file_path': file_path,
                    'normalized_path': normalized_path,
                    'original_filename': original_filename
                })
                print(f"✗ 模板 [{template_name}] - 文件不存在: {normalized_path}")
        except Exception as e:
            orphan_templates.append({
                'id': template_id,
                'name': template_name,
                'file_path': file_path,
                'normalized_path': normalized_path,
                'original_filename': original_filename
            })
            print(f"✗ 模板 [{template_name}] - 检查失败: {e}")

    # 输出统计信息
    print(f"\n{'='*80}")
    print(f"检查完成:")
    print(f"  - 有效模板: {len(valid_templates)} 个")
    print(f"  - 孤立模板: {len(orphan_templates)} 个")
    print(f"{'='*80}\n")

    if orphan_templates:
        print("以下孤立模板将被删除:")
        print(f"{'序号':<6} {'模板ID':<38} {'模板名称':<20} {'文件路径'}")
        print("-" * 120)
        for idx, orphan in enumerate(orphan_templates, 1):
            print(f"{idx:<6} {orphan['id']:<38} {orphan['name']:<20} {orphan['normalized_path']}")

        if not dry_run:
            print(f"\n开始删除 {len(orphan_templates)} 个孤立模板...")
            deleted_count = 0
            for orphan in orphan_templates:
                try:
                    # 使用SQL直接删除
                    delete_query = text("DELETE FROM templates WHERE id = :template_id")
                    db.execute(delete_query, {"template_id": orphan['id']})
                    deleted_count += 1
                    print(f"✓ 已删除: {orphan['name']} (ID: {orphan['id']})")
                except Exception as e:
                    print(f"✗ 删除失败: {orphan['name']} (ID: {orphan['id']}) - {e}")

            db.commit()
            print(f"\n成功删除 {deleted_count} 个孤立模板记录")
        else:
            print("\n[DRY RUN] 未执行实际删除。如需删除，请使用 --confirm 参数")
    else:
        print("✓ 没有发现孤立模板，数据库与存储一致")

    return {
        'total': len(templates),
        'valid': len(valid_templates),
        'orphan': len(orphan_templates),
        'orphan_list': orphan_templates
    }

def main():
    import argparse

    parser = argparse.ArgumentParser(description='清理孤立的模板记录')
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='确认删除孤立模板（默认只进行检查，不实际删除）'
    )

    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = cleanup_orphan_templates(db, dry_run=not args.confirm)

        print(f"\n{'='*80}")
        print("清理完成!")
        print(f"{'='*80}")

        return 0 if result['orphan'] == 0 else 1

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
