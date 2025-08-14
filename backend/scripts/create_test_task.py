#!/usr/bin/env python3
"""
创建测试任务用于验证调度功能
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import SessionLocal
from app.models.task import Task
from app.models.user import User
from app.models.template import Template
from app.models.data_source import DataSource


def create_test_template(db, user_id):
    """创建测试模板"""
    existing_template = db.query(Template).filter(
        Template.name == "AI测试报告模板"
    ).first()
    
    if existing_template:
        return existing_template
    
    template_content = """# AI测试报告

## 基本信息
- 报告生成时间: {{generation_time}}
- 数据统计日期: {{data_date}}

## 测试内容
这是一个用于测试xiaoai AI提供商的简单模板。

### 数据分析
{{data_analysis}}

### 总结
AI服务运行正常，可以进行报告生成。

---
*此报告由AutoReportAI自动生成*
"""
    
    template = Template(
        name="AI测试报告模板",
        content=template_content,
        description="用于测试AI提供商的简单模板",
        template_type="docx",
        is_active=True,
        user_id=user_id
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    print("✅ 已创建测试模板")
    return template


def create_test_data_source(db, user_id):
    """创建或获取测试数据源"""
    existing_ds = db.query(DataSource).filter(
        DataSource.name == "测试数据源"
    ).first()
    
    if existing_ds:
        return existing_ds
    
    # 如果没有数据源，返回现有的第一个数据源
    data_source = db.query(DataSource).first()
    if data_source:
        print(f"✅ 使用现有数据源: {data_source.name}")
        return data_source
    
    print("⚠️  未找到数据源，请先创建数据源")
    return None


def create_test_task(db, user_id):
    """创建测试任务"""
    # 获取或创建测试模板
    template = create_test_template(db, user_id)
    
    # 获取数据源
    data_source = create_test_data_source(db, user_id)
    if not data_source:
        return None
    
    # 检查是否已有测试任务
    existing_task = db.query(Task).filter(
        Task.name == "AI测试任务"
    ).first()
    
    if existing_task:
        print(f"✅ 测试任务已存在 (ID: {existing_task.id})")
        return existing_task
    
    # 计算下次执行时间（5分钟后）
    now = datetime.now()
    next_run = now + timedelta(minutes=5)
    cron_schedule = f"{next_run.minute} {next_run.hour} * * *"
    
    # 创建测试任务
    task = Task(
        name="AI测试任务",
        description="用于测试xiaoai AI提供商和调度功能的测试任务",
        template_id=template.id,
        data_source_id=data_source.id,
        schedule=cron_schedule,
        recipients=["test@example.com"],
        is_active=True,
        owner_id=user_id
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    print(f"✅ 已创建测试任务 (ID: {task.id})")
    print(f"📅 调度时间: {cron_schedule} ({next_run.strftime('%Y-%m-%d %H:%M:%S')})")
    
    return task


def main():
    print("🧪 正在创建测试任务...")
    
    db = SessionLocal()
    try:
        # 获取管理员用户
        admin_user = db.query(User).filter(User.username == 'admin').first()
        if not admin_user:
            print("❌ 未找到admin用户，请先运行 init_db.py")
            return
        
        # 创建测试任务
        task = create_test_task(db, admin_user.id)
        
        if task:
            print(f"\\n🎉 测试任务创建完成！")
            print(f"📝 任务名称: {task.name}")
            print(f"🆔 任务ID: {task.id}")
            print(f"📋 模板: {task.template.name}")
            print(f"🗄️  数据源: {task.data_source.name}")
            print(f"⏰ 调度: {task.schedule}")
            print(f"📬 接收者: {', '.join(task.recipients) if task.recipients else '无'}")
            
            print(f"\\n💡 提示:")
            print(f"  - 可以通过 API 手动执行: POST /api/v1/tasks/{task.id}/execute")
            print(f"  - 任务将在指定时间自动执行")
            print(f"  - 可以通过 GET /api/v1/tasks/{task.id}/status 查看状态")
        else:
            print("❌ 测试任务创建失败")
            
    except Exception as e:
        print(f"❌ 创建测试任务时出错: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()