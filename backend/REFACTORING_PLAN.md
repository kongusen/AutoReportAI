# Placeholder系统重构方案

## 🎯 重构目标

将 `placeholder_types.py` 和 `placeholder_system.py` 从基础设施层移动到业务层，利用我们新建的 `core/prompts` 系统，实现更清晰的架构分层。

## 📋 重构计划

### 1. placeholder_types.py 重构

**当前位置**: `app/services/infrastructure/agents/placeholder_types.py`
**目标位置**: `app/services/domain/placeholder/types.py`

**重构内容**:
- ✅ 业务枚举 (PlaceholderType, ChartType, TaskPriority)
- ✅ 请求/响应数据结构 (PlaceholderAnalysisRequest, SQLGenerationResult 等)
- ✅ 业务实体 (PlaceholderInfo, PlaceholderAgent)
- ❌ 移除基础设施相关的依赖

### 2. placeholder_system.py 重构

**当前位置**: `app/services/infrastructure/agents/placeholder_system.py`
**目标位置**: `app/services/application/placeholder/placeholder_service.py`

**重构策略**:
1. **简化核心逻辑**: 移除重复的prompt工程代码，使用 `core/prompts` 系统
2. **业务层定位**: 重新定位为应用服务，专注业务流程编排
3. **依赖关系清理**: 
   - 使用 `PromptManager` 替代内嵌的prompt逻辑
   - 使用 `AgentController` 进行任务编排
   - 使用 `ToolExecutor` 进行工具调用

### 3. 依赖更新

需要更新以下文件的导入：
- `app/services/application/tasks/task_application_service.py`
- 其他引用这些模块的文件

## 🏗️ 新架构设计

```
app/services/
├── domain/placeholder/
│   ├── types.py              # 从 placeholder_types.py 移动
│   ├── models.py             # 现有的领域模型
│   └── ...
├── application/placeholder/
│   ├── placeholder_service.py # 从 placeholder_system.py 重构
│   └── ...
└── infrastructure/agents/
    ├── core/
    │   ├── prompts/           # 我们新建的prompt工程系统
    │   ├── tools/
    │   └── ...
    └── ...
```

## 📊 重构优势

1. **清晰的分层**: 业务逻辑在业务层，基础设施在基础设施层
2. **代码复用**: 利用统一的 `core/prompts` 系统
3. **更好的测试**: 业务逻辑和基础设施分离，便于单元测试
4. **可维护性**: 减少重复代码，统一prompt管理
5. **扩展性**: 基于标准的prompt系统，便于后续功能扩展

## 🔄 实施步骤

1. **第一步**: 创建新的目录结构
2. **第二步**: 移动 `placeholder_types.py` 到领域层
3. **第三步**: 重构 `placeholder_system.py` 为应用服务
4. **第四步**: 更新依赖和导入
5. **第五步**: 运行测试验证重构结果

## ⚠️ 注意事项

- 保持向后兼容性，在重构过程中保留原有的接口
- 逐步迁移，避免一次性大规模改动
- 充分测试，确保业务功能不受影响