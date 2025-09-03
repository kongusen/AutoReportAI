## v0.2.0 (2025-09-03)

### Features
- 引入通知模块（模型/CRUD/API）并与前端设置页联动
- 新增模型执行、简单模型选择与统计API
- 完善 AI 基础设施：健康监控、限流、池化、执行引擎、SQL 生成与推理/质量/性能子系统
- 新增 React Agent 仪表盘与模板分析等前端页面与组件
- 增加开发环境目录 `autorport-dev/` 与相关脚本

### Refactor
- 重构 DDD 架构与智能代理系统分层（application/domain/infrastructure）
- 精简与替换旧版 agents/IAOP 相关模块
- 调整后端 API 与服务结构，统一任务/工作流/模板处理

### Chore
- 优化 `.gitignore`：忽略 `autorport-dev/data/` 等本地数据目录
- 新增 GitHub Actions 工作流与 pre-commit 配置

### Fixes
- 修复 WebSocket 连接逻辑与前端 API 客户端
- 修复部分端点/脚本与时间工具的兼容问题

### Docs
- 新增并更新：架构图、数据流、占位符到数据生成流程等技术文档

---

变更摘要来源：`git log` 自项目开始至标签 `v0.2.0` 的提交信息，按功能类型归纳整理。

