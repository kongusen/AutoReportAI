# 代码贡献指南

非常感谢您对 AutoReportAI 项目的兴趣和贡献！我们欢迎所有形式的贡献，无论是报告问题、提交功能请求，还是直接贡献代码。

本指南旨在帮助您顺利地参与项目贡献。项目已完成全面的架构重构，采用现代化的分层架构设计，请务必阅读[架构指南](./architecture-guide.md)了解新的架构设计。

## 行为准则

我们致力于为所有参与者提供一个友好、安全和热情的环境。请在参与贡献前阅读并遵守我们的行为准则。

## 如何贡献

### 报告问题 (Bug Reports)

如果您发现了Bug，请通过 [GitHub Issues](https://github.com/your-org/AutoReportAI/issues) 提交报告。一个好的Bug报告应包含：
- **清晰的标题**: 简要描述问题。
- **复现步骤**: 详细说明如何复现问题。
- **预期行为**: 描述在没有Bug的情况下应该发生什么。
- **实际行为**: 描述实际发生了什么，并附上错误信息或截图。
- **环境信息**: 您的操作系统、浏览器、项目版本等。

### 功能建议 (Feature Requests)

如果您有新功能的想法，也欢迎通过 [GitHub Issues](https://github.com/your-org/AutoReportAI/issues) 提交。请详细描述：
- **问题描述**: 解释该功能要解决什么问题。
- **解决方案**: 描述您建议的功能如何解决这个问题。
- **替代方案**: 您是否考虑过其他解决方案或替代方案。

### 贡献代码

我们非常欢迎您直接贡献代码来修复Bug或实现新功能。

#### 1. Fork & Clone

首先，Fork本仓库到您自己的GitHub账户，然后Clone到本地。
```bash
git clone https://github.com/YOUR_USERNAME/AutoReportAI.git
cd AutoReportAI
git remote add upstream https://github.com/your-org/AutoReportAI.git
```

#### 2. 分支策略

我们使用基于 `main` 分支的特性分支工作流。
- 在开始开发前，请确保您的 `main` 分支与上游保持同步:
  ```bash
  git checkout main
  git pull upstream main
  ```
- 从 `main` 分支创建一个新的特性分支。请使用有意义的分支名。
  ```bash
  # 修复Bug
  git checkout -b fix/login-button-bug
  
  # 实现新功能
  git checkout -b feat/add-data-export
  
  # 文档修改
  git checkout -b docs/update-setup-guide
  ```

#### 3. 提交规范

我们遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/v1.0.0/) 规范。这有助于自动化生成更新日志和版本管理。
- **格式**: `<type>(<scope>): <subject>`
- **常用 `type`**:
  - `feat`: 新功能
  - `fix`: 修复Bug
  - `docs`: 文档变更
  - `style`: 代码风格调整（不影响代码逻辑）
  - `refactor`: 代码重构
  - `test`: 添加或修改测试
  - `chore`: 构建过程或辅助工具的变动
- **示例**:
  ```
  feat(api): add endpoint for data export
  fix(ui): correct alignment of header icons
  docs(readme): add setup instructions
  ```

#### 4. 架构规范

在新的架构下，请遵循以下开发规范：

**后端开发规范：**
- 新功能应放在相应的服务模块中（`app/services/`）
- API端点应使用依赖注入模式
- 使用统一的异常处理机制
- 遵循分层架构原则，避免跨层直接调用

**前端开发规范：**
- 组件应按功能分类放置在相应目录
- 使用TypeScript确保类型安全
- API调用应通过统一的API客户端
- 状态管理使用Context + useReducer模式

**测试要求：**
- 新功能必须包含单元测试
- 关键业务流程需要集成测试
- Bug修复必须包含回归测试
- 测试覆盖率不低于80%

#### 5. Pull Request (PR) 流程

1.  **完成开发**: 在您的特性分支上完成代码编写和测试。
2.  **保持同步**: 定期将上游 `main` 分支的变更合并到您的分支，以避免冲突。
    ```bash
    git fetch upstream
    git rebase upstream/main
    ```
3.  **代码质量**:
    - **后端**: 运行 `make format` 和 `make lint` 确保代码风格一致。
    - **前端**: 运行 `npm run format` 和 `npm run lint`。
4.  **架构合规性检查**:
    - 确保代码遵循新的分层架构
    - 验证服务模块正确组织
    - 检查依赖注入是否正确使用
5.  **测试**:
    - **后端**: 运行 `make test` 确保所有测试通过。
    - **前端**: 运行 `npm test`。
    - 验证测试覆盖率达到要求
6.  **提交PR**:
    - 将您的分支推送到您Fork的仓库: `git push origin feat/my-new-feature`
    - 在GitHub上发起Pull Request，目标分支为 `your-org/AutoReportAI` 的 `main` 分支。
    - **填写PR模板**: 清晰地描述您的变更、解决了什么问题，并链接相关的Issue。
7.  **代码审查**:
    - 项目维护者会审查您的代码，并可能提出修改建议。
    - 审查将重点关注架构合规性和代码质量。
    - 请积极响应审查意见并进行必要的修改。
8.  **合并**:
    - 一旦您的PR被批准，维护者会将其合并到 `main` 分支。恭喜您，您的贡献已成为项目的一部分！

## 代码审查清单

### 后端代码审查要点

**架构合规性：**
- [ ] 代码是否遵循分层架构原则
- [ ] 服务模块是否正确组织在相应目录
- [ ] 是否正确使用依赖注入模式
- [ ] 是否避免了跨层直接调用

**代码质量：**
- [ ] 是否遵循PEP 8代码风格
- [ ] 是否有适当的类型注解
- [ ] 是否使用了统一的异常处理
- [ ] 是否有充分的错误日志记录

**测试覆盖：**
- [ ] 是否包含单元测试
- [ ] 关键业务逻辑是否有集成测试
- [ ] 测试覆盖率是否达到80%以上
- [ ] 测试是否能独立运行

**API设计：**
- [ ] API端点是否遵循RESTful规范
- [ ] 是否有适当的输入验证
- [ ] 响应格式是否统一
- [ ] 是否更新了API文档

### 前端代码审查要点

**组件设计：**
- [ ] 组件是否按功能正确分类
- [ ] 是否遵循组件设计原则
- [ ] 是否有适当的Props类型定义
- [ ] 是否考虑了组件的可复用性

**代码质量：**
- [ ] 是否遵循ESLint和Prettier规则
- [ ] TypeScript类型定义是否完整
- [ ] 是否有适当的错误处理
- [ ] 是否考虑了性能优化

**状态管理：**
- [ ] 是否正确使用Context + useReducer
- [ ] 状态更新是否遵循不可变原则
- [ ] 是否避免了不必要的重渲染
- [ ] 副作用是否正确处理

**用户体验：**
- [ ] 是否有适当的加载状态
- [ ] 错误信息是否用户友好
- [ ] 是否考虑了无障碍访问
- [ ] 响应式设计是否正确

### 通用审查要点

**文档：**
- [ ] 是否更新了相关文档
- [ ] 代码注释是否充分且准确
- [ ] README是否需要更新
- [ ] 是否有必要的使用示例

**安全性：**
- [ ] 是否有输入验证和输出编码
- [ ] 是否正确处理了敏感数据
- [ ] 是否遵循了安全最佳实践
- [ ] 是否有适当的权限检查

**性能：**
- [ ] 是否考虑了性能影响
- [ ] 数据库查询是否优化
- [ ] 是否有不必要的网络请求
- [ ] 是否考虑了缓存策略

感谢您的贡献！ 