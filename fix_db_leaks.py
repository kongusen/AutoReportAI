#!/usr/bin/env python3
"""
数据库连接泄漏修复脚本
自动将所有 `db = SessionLocal()` 替换为使用 context manager 的模式
"""

import os
import re
from pathlib import Path

# 需要修复的文件列表（从扫描结果中获取，排除已修复的）
FILES_TO_FIX = [
    "app/api/deps.py",
    "app/api/endpoints/agent_run.py",
    "app/api/endpoints/task_execution.py",
    "app/services/application/tasks/task_execution_service.py",
    "app/services/infrastructure/visualization/chart_generation_service.py",
    "app/services/infrastructure/agents/production_integration_service.py",
    "app/services/infrastructure/agents/production_auth_provider.py",
    "app/services/infrastructure/agents/production_config_provider.py",
    "app/services/infrastructure/agents/data_source_security_service.py",
    "app/services/infrastructure/document/word_export_service.py",
]

BASE_DIR = Path("/Users/shan/work/uploads/AutoReportAI/backend")

def check_file_needs_fix(file_path):
    """检查文件是否需要修复"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找裸露的 SessionLocal() 调用（不在 with 语句或 try-finally 中的）
    pattern = r'^\s+db\s*=\s*SessionLocal\(\)\s*$'
    matches = re.findall(pattern, content, re.MULTILINE)

    return len(matches) > 0, content

def suggest_fix(file_path):
    """为文件生成修复建议"""
    needs_fix, content = check_file_needs_fix(file_path)

    if not needs_fix:
        return None

    lines = content.split('\n')
    suggestions = []

    for i, line in enumerate(lines, 1):
        if re.match(r'^\s+db\s*=\s*SessionLocal\(\)\s*$', line):
            # 检查是否已经在 try-finally 块中
            context_before = '\n'.join(lines[max(0, i-5):i])
            context_after = '\n'.join(lines[i:min(len(lines), i+10)])

            if 'finally:' not in context_after or 'db.close()' not in context_after:
                suggestions.append({
                    'line': i,
                    'content': line,
                    'suggestion': '需要添加 try-finally 块或使用 get_db_session() context manager'
                })

    return suggestions

# 运行检查
print("=== 数据库连接泄漏检查报告 ===\n")

total_issues = 0
for file_rel in FILES_TO_FIX:
    file_path = BASE_DIR / file_rel

    if not file_path.exists():
        print(f"⚠️  文件不存在: {file_rel}")
        continue

    suggestions = suggest_fix(file_path)

    if suggestions:
        print(f"\n📁 {file_rel}")
        print(f"   发现 {len(suggestions)} 处潜在泄漏：")
        for sug in suggestions:
            print(f"   - 第 {sug['line']} 行: {sug['suggestion']}")
        total_issues += len(suggestions)
    else:
        print(f"✅ {file_rel} - 已正确处理")

print(f"\n\n总计发现 {total_issues} 处潜在泄漏点")
print("\n推荐修复模式：")
print("""
# 模式 1: 使用 get_db_session (推荐)
from app.db.session import get_db_session

with get_db_session() as db:
    # 使用 db
    result = db.query(...)
# 自动关闭

# 模式 2: 手动 try-finally
db = SessionLocal()
try:
    result = db.query(...)
finally:
    db.close()

# 模式 3: 条件关闭（当 db 可能作为参数传入时）
if db is None:
    db = SessionLocal()
    should_close = True
else:
    should_close = False

try:
    result = db.query(...)
finally:
    if should_close:
        db.close()
""")
