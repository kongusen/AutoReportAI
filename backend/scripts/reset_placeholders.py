"""
重置占位符状态，强制重新分析和生成SQL

这个脚本用于在启用Context Retriever后，重置所有占位符的分析状态，
让系统使用新的schema信息重新生成SQL。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.template_placeholder import TemplatePlaceholder
from app.models.template import Template
from app.models.data_source import DataSource


def reset_placeholders_for_template(
    db: Session,
    template_id: str = None,
    data_source_id: str = None,
    dry_run: bool = False
):
    """
    重置占位符状态

    Args:
        db: 数据库会话
        template_id: 可选，特定模板ID
        data_source_id: 可选，特定数据源ID
        dry_run: 是否为演练模式（不实际修改数据库）
    """

    # 构建查询
    query = db.query(TemplatePlaceholder)

    if template_id:
        query = query.filter(TemplatePlaceholder.template_id == template_id)

    # 只重置已分析的占位符
    query = query.filter(TemplatePlaceholder.agent_analyzed == True)

    placeholders = query.all()

    if not placeholders:
        print("❌ 没有找到需要重置的占位符")
        return

    print(f"\n📋 找到 {len(placeholders)} 个需要重置的占位符")

    # 按模板分组显示
    templates_map = {}
    for ph in placeholders:
        if ph.template_id not in templates_map:
            template = db.query(Template).filter(Template.id == ph.template_id).first()
            templates_map[ph.template_id] = {
                'name': template.name if template else 'Unknown',
                'placeholders': []
            }
        templates_map[ph.template_id]['placeholders'].append(ph)

    # 显示详细信息
    for template_id, info in templates_map.items():
        print(f"\n📄 模板: {info['name']} (ID: {template_id})")
        print(f"   占位符数量: {len(info['placeholders'])}")

        for ph in info['placeholders'][:5]:  # 只显示前5个
            print(f"   • {ph.placeholder_name}")
            if ph.generated_sql:
                # 提取表名
                sql_preview = ph.generated_sql[:200].replace('\n', ' ')
                print(f"     SQL: {sql_preview}...")

        if len(info['placeholders']) > 5:
            print(f"   ... 还有 {len(info['placeholders']) - 5} 个占位符")

    if dry_run:
        print("\n⚠️  演练模式：不会实际修改数据库")
        print(f"✨ 将会重置 {len(placeholders)} 个占位符的以下字段：")
        print("   - agent_analyzed: False")
        print("   - sql_validated: False")
        print("   - generated_sql: None")
        print("   - target_table: None")
        print("   - target_database: None")
        return

    # 确认操作
    print(f"\n⚠️  即将重置 {len(placeholders)} 个占位符，这将：")
    print("   1. 清除现有的SQL")
    print("   2. 将分析状态设为未分析")
    print("   3. 下次执行时会使用新的schema重新生成SQL")

    confirm = input("\n是否继续？(yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ 操作已取消")
        return

    # 执行重置
    reset_count = 0
    for ph in placeholders:
        ph.agent_analyzed = False
        ph.sql_validated = False
        ph.generated_sql = None
        ph.target_table = None
        ph.target_database = None
        ph.confidence_score = 0.0
        reset_count += 1

    db.commit()
    print(f"\n✅ 成功重置 {reset_count} 个占位符")
    print("\n📝 下一步：")
    print("   1. 重启服务（如果需要）")
    print("   2. 重新执行报告生成任务")
    print("   3. 系统将使用Context Retriever提供的正确schema重新生成SQL")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='重置占位符状态，强制重新分析')
    parser.add_argument('--template-id', type=str, help='特定模板ID（可选）')
    parser.add_argument('--data-source-id', type=str, help='特定数据源ID（可选）')
    parser.add_argument('--dry-run', action='store_true', help='演练模式，不实际修改数据库')
    parser.add_argument('--list-templates', action='store_true', help='列出所有模板')

    args = parser.parse_args()

    db = SessionLocal()

    try:
        if args.list_templates:
            # 列出所有模板
            templates = db.query(Template).all()
            print("\n📋 可用的模板：")
            for t in templates:
                ph_count = db.query(TemplatePlaceholder).filter(
                    TemplatePlaceholder.template_id == t.id
                ).count()
                print(f"   • {t.name}")
                print(f"     ID: {t.id}")
                print(f"     占位符数量: {ph_count}")
                print()
            return

        reset_placeholders_for_template(
            db=db,
            template_id=args.template_id,
            data_source_id=args.data_source_id,
            dry_run=args.dry_run
        )

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
