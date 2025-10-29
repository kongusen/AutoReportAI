"""
检查占位符 SQL 生成情况
"""
import sys
sys.path.insert(0, '/Users/shan/work/AutoReportAI/backend')

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.template_placeholder import TemplatePlaceholder

def check_placeholders():
    db: Session = SessionLocal()
    try:
        # 获取最近的模板占位符
        placeholders = db.query(TemplatePlaceholder).order_by(
            TemplatePlaceholder.created_at.desc()
        ).limit(10).all()
        
        print("=" * 80)
        print("占位符 SQL 状态检查")
        print("=" * 80)
        
        if not placeholders:
            print("❌ 未找到任何占位符")
            return
        
        total = 0
        has_sql = 0
        validated = 0
        
        for ph in placeholders:
            total += 1
            print(f"\n占位符 {total}: {ph.placeholder_name}")
            print(f"  模板ID: {ph.template_id}")
            print(f"  是否有SQL: {bool(ph.generated_sql)}")
            print(f"  SQL已验证: {ph.sql_validated}")
            print(f"  Agent已分析: {ph.agent_analyzed}")
            
            if ph.generated_sql:
                has_sql += 1
                print(f"  SQL (前100字符): {ph.generated_sql[:100]}...")
                
                # 检查是否有双重引号问题
                if "''" in ph.generated_sql or '""' in ph.generated_sql:
                    print(f"  ⚠️ SQL中检测到双重引号!")
            else:
                print(f"  ❌ 无 SQL")
            
            if ph.sql_validated:
                validated += 1
        
        print("\n" + "=" * 80)
        print(f"统计: 总共 {total} 个占位符")
        print(f"  有SQL: {has_sql} ({has_sql*100//total if total > 0 else 0}%)")
        print(f"  已验证: {validated} ({validated*100//total if total > 0 else 0}%)")
        print("=" * 80)
        
    finally:
        db.close()

if __name__ == "__main__":
    check_placeholders()
