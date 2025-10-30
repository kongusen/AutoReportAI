# Changelog

## v0.5.0 (2025-10-30)

### 新增/特性

- Agents 体系重构：引入 `context_retriever`、`stage_aware_adapter`、工具模块分层（`tools/chart|data|schema|sql|time`）。
- SQL 能力增强：`generator`/`validator`/`executor`/`auto_fixer` 组合完善，支持更稳健的列校验与执行回退。
- 协调与消息：新增 `messaging/` 用于编排与调度扩展。

### 优化/重构

- Prompts 目录结构化：`prompts/system`、`prompts/templates`、`prompts/stages` 分离，提升可维护性。
- 运行时优化：`runtime` 与 `quality_scorer` 调整以匹配分阶段上下文检索流程。
- 前端细节：任务与模板占位符页面的小幅更新与状态处理优化。

### 修复

- 占位符接口小修，确保发布前行为一致性。
- Doris/Schema 相关检查流程若干健壮性修复（列存在性、字典缓存、检索链路）。

### 开发与运维

- dev 配置与脚本清理：移除过时文档与脚本，精简本地与容器启动配置（`autorport-dev/*`）。
- 规范提交与结构：大规模文档归档与清理，保持仓库精简。

### 影响说明（可能的注意点）

- Agents 相关内部接口发生重构，若有外部自定义调用需要对齐新的模块与入口。
- 本次清理删除了大量旧文档与脚本，如需历史参考请在标签 `v0.4.x` 范围内查阅。

---
如需更详细的技术背景与迁移指引，请参考 `backend/docs/` 中的架构与实现说明（保留的条目）以及源码内文档字符串。
