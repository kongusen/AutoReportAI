# 前后端架构重构 - 可执行任务

## 任务配置

```yaml
spec_name: frontend-backend-restructure
version: 1.0
description: 前后端架构重构实施计划
```

## Phase 1: 项目清理和基础整理

### Task 1.2.1: 创建docs目录结构并移动文档文件

**Priority**: High
**Estimated Time**: 30 minutes
**Dependencies**: None

**Description**: 
整理项目根目录的文档文件，创建规范的docs目录结构

**Acceptance Criteria**:
- [ ] 创建docs/analysis/目录
- [ ] 移动所有TASK_*_COMPLETION_SUMMARY.md文件到docs/analysis/
- [ ] 移动FRONTEND_BACKEND_ANALYSIS.md等分析文档到docs/analysis/
- [ ] 更新README.md中的文档链接
- [ ] 验证所有文档文件已正确移动且链接有效

**Commands**:
```bash
# 创建目录结构
mkdir -p docs/analysis

# 移动文档文件
find . -maxdepth 1 -name "TASK_*_COMPLETION_SUMMARY.md" -exec mv {} docs/analysis/ \;
find . -maxdepth 1 -name "*_ANALYSIS.md" -exec mv {} docs/analysis/ \;
find . -maxdepth 1 -name "*_SUMMARY.md" -exec mv {} docs/analysis/ \;
mv INTELLIGENT_PLACEHOLDER_SYSTEM_COMPLETION.md docs/analysis/ 2>/dev/null || true

# 验证移动结果
ls -la docs/analysis/
```

**Validation**:
```bash
# 检查目录结构
test -d docs/analysis && echo "✅ docs/analysis directory created"

# 检查文件移动
ls docs/analysis/*.md | wc -l
```

---

### Task 1.2.2: 整理脚本文件

**Priority**: High  
**Estimated Time**: 20 minutes
**Dependencies**: Task 1.2.1

**Description**:
将项目根目录的脚本文件移动到backend/scripts/目录

**Acceptance Criteria**:
- [ ] 移动analyze_template.py到backend/scripts/
- [ ] 移动demo_quality_checker.py到backend/scripts/
- [ ] 移动intelligent_placeholder_system_demo.py到backend/scripts/
- [ ] 移动create_advanced_template.py到backend/scripts/
- [ ] 移动create_complaint_data_source.py到backend/scripts/
- [ ] 更新脚本文件的导入路径
- [ ] 验证移动后的脚本功能正常

**Commands**:
```bash
# 移动脚本文件
mv analyze_template.py backend/scripts/ 2>/dev/null || true
mv demo_quality_checker.py backend/scripts/ 2>/dev/null || true
mv intelligent_placeholder_system_demo.py backend/scripts/ 2>/dev/null || true
mv create_advanced_template.py backend/scripts/ 2>/dev/null || true
mv create_complaint_data_source.py backend/scripts/ 2>/dev/null || true

# 验证移动结果
ls -la backend/scripts/*.py
```

**Validation**:
```bash
# 检查脚本文件是否移动成功
test -f backend/scripts/analyze_template.py && echo "✅ analyze_template.py moved"
test -f backend/scripts/demo_quality_checker.py && echo "✅ demo_quality_checker.py moved"
```

---

### Task 1.3.1: 合并后端测试目录

**Priority**: High
**Estimated Time**: 45 minutes  
**Dependencies**: Task 1.2.2

**Description**:
统一后端测试目录结构，将backend/app/tests/中的测试文件迁移到backend/tests/unit/

**Acceptance Criteria**:
- [ ] 分析backend/app/tests/和backend/tests/中的测试文件重复情况
- [ ] 将backend/app/tests/中的测试文件迁移到backend/tests/unit/
- [ ] 更新测试文件中的导入路径
- [ ] 删除backend/app/tests/目录
- [ ] 更新测试配置文件中的路径引用
- [ ] 运行所有测试确保迁移后功能正常

**Commands**:
```bash
# 检查当前测试目录结构
echo "Current test structure:"
find backend -name "test_*.py" -o -name "*_test.py" | head -10

# 创建目标目录
mkdir -p backend/tests/unit

# 移动测试文件（如果存在）
if [ -d "backend/app/tests" ]; then
    find backend/app/tests -name "*.py" -exec cp {} backend/tests/unit/ \;
    echo "Test files copied to backend/tests/unit/"
fi
```

**Validation**:
```bash
# 运行测试验证
cd backend && python -m pytest tests/unit/ -v --tb=short
```

---

## Phase 2: 后端服务层重构

### Task 2.1.1: 设计服务模块分组结构

**Priority**: High
**Estimated Time**: 15 minutes
**Dependencies**: Phase 1 completion

**Description**:
创建模块化服务架构的目录结构

**Acceptance Criteria**:
- [ ] 创建app/services/intelligent_placeholder/模块目录
- [ ] 创建app/services/report_generation/模块目录  
- [ ] 创建app/services/data_processing/模块目录
- [ ] 创建app/services/ai_integration/模块目录
- [ ] 创建app/services/notification/模块目录
- [ ] 确认目录结构创建正确且权限设置合适

**Commands**:
```bash
# 创建服务模块目录结构
mkdir -p backend/app/services/intelligent_placeholder
mkdir -p backend/app/services/report_generation
mkdir -p backend/app/services/data_processing
mkdir -p backend/app/services/ai_integration
mkdir -p backend/app/services/notification

# 创建__init__.py文件
touch backend/app/services/intelligent_placeholder/__init__.py
touch backend/app/services/report_generation/__init__.py
touch backend/app/services/data_processing/__init__.py
touch backend/app/services/ai_integration/__init__.py
touch backend/app/services/notification/__init__.py
```

**Validation**:
```bash
# 验证目录结构
tree backend/app/services/ || ls -la backend/app/services/*/
```

---

### Task 2.1.2: 重构智能占位符服务组

**Priority**: High
**Estimated Time**: 60 minutes
**Dependencies**: Task 2.1.1

**Description**:
将智能占位符相关服务文件重构到新的模块结构中

**Acceptance Criteria**:
- [ ] 将intelligent_placeholder_processor.py移动到intelligent_placeholder/processor.py
- [ ] 将intelligent_placeholder_adapter.py移动到intelligent_placeholder/adapter.py
- [ ] 将intelligent_field_matcher.py移动到intelligent_placeholder/matcher.py
- [ ] 创建intelligent_placeholder/__init__.py统一导出接口
- [ ] 更新相关导入引用
- [ ] 测试智能占位符服务模块导入和基本功能

**Commands**:
```bash
# 移动智能占位符服务文件
cd backend/app/services

# 检查源文件是否存在并移动
if [ -f "intelligent_placeholder_processor.py" ]; then
    mv intelligent_placeholder_processor.py intelligent_placeholder/processor.py
    echo "✅ Moved processor.py"
fi

if [ -f "intelligent_placeholder_adapter.py" ]; then
    mv intelligent_placeholder_adapter.py intelligent_placeholder/adapter.py
    echo "✅ Moved adapter.py"
fi

if [ -f "intelligent_field_matcher.py" ]; then
    mv intelligent_field_matcher.py intelligent_placeholder/matcher.py
    echo "✅ Moved matcher.py"
fi
```

**Post-Commands**:
```python
# 创建统一导出接口
cat > backend/app/services/intelligent_placeholder/__init__.py << 'EOF'
"""
智能占位符服务模块

提供智能占位符处理、适配和字段匹配功能
"""

try:
    from .processor import IntelligentPlaceholderProcessor
except ImportError:
    IntelligentPlaceholderProcessor = None

try:
    from .adapter import IntelligentPlaceholderAdapter
except ImportError:
    IntelligentPlaceholderAdapter = None

try:
    from .matcher import IntelligentFieldMatcher
except ImportError:
    IntelligentFieldMatcher = None

__all__ = [
    'IntelligentPlaceholderProcessor',
    'IntelligentPlaceholderAdapter', 
    'IntelligentFieldMatcher'
]
EOF
```

**Validation**:
```bash
# 测试模块导入
cd backend && python -c "
try:
    from app.services.intelligent_placeholder import *
    print('✅ 智能占位符模块导入成功')
except Exception as e:
    print(f'❌ 导入失败: {e}')
"
```

---

## 执行指南

### 如何执行这些任务

1. **单个任务执行**:
   ```bash
   # 执行特定任务
   kiro task run "Task 1.2.1"
   ```

2. **阶段性执行**:
   ```bash
   # 执行Phase 1的所有任务
   kiro task run --phase "Phase 1"
   ```

3. **验证任务状态**:
   ```bash
   # 检查任务状态
   kiro task status
   ```

### 任务依赖关系

- Phase 1 → Phase 2 → Phase 3
- 每个Phase内的任务按编号顺序执行
- 某些任务可以并行执行（标记为无依赖）

### 回滚策略

每个任务执行前会创建备份点，如果任务失败可以回滚：

```bash
# 回滚到任务执行前状态
kiro task rollback "Task 1.2.1"
```