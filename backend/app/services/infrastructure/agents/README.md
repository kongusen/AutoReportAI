# Loom 集成版 Agent 系统

本目录承载基于 `loom-agent` 框架的全新运行时实现，用于逐步替换
`app/services/infrastructure/agents` 下面的旧版 Agent。  
核心目标是复用 Loom 的可靠执行循环和工具编排，同时保持与现有
`AgentFacade` API 的兼容性，便于平滑迁移。

## 关键组件

- `config.py`：定义 LLM 与运行时配置数据类，支持通过 `resolve_runtime_config`
  叠加覆盖。
- `runtime.py`：构建 Loom `Agent` 实例并缓存工具，支持 mock/OpenAI 等多种配置。
- `tools/__init__.py`：将旧工具 (`execute` 方法) 自动包装成 Loom `BaseTool`。
- `compat.py`：把旧版 `AgentInput/AgentOutput` 与新的 `AgentRequest/AgentResponse`
  互转，补充阶段、可用工具、系统配置等上下文。
- `prompts.py`：按阶段 (模板、任务、图表) 生成系统提示词，指导 Loom Agent 选择
  合适工具并产出结构化结果。
- `facade.py`：新的 `LoomAgentFacade`，提供 `execute`、`execute_task_validation`，
  并兼容 `configure_auth`/`configure_system`。
- `service.py`：对外暴露 `LoomAgentService`，保持与旧 `AgentFacade` 相同的调用习惯。
- `tests/`: 覆盖运行时、兼容层、系统提示的单元测试，确保迁移过程中行为稳定。

## 集成方式

```python
from app.services.infrastructure.agents import AgentService

service = AgentService(container=my_container)
# (可选) 配置认证、系统参数
service.configure_auth(auth_context)
service.configure_system(config_loader=my_loader)

# 与旧接口保持一致
result = await service.execute(agent_input)
validation_result = await service.execute_task_validation(agent_input)
```

## 下一步

1. 在业务代码中切换至 `LoomAgentService`。
2. 补充端到端集成测试，验证真实数据源与 LLM 联动。
3. 按阶段迁移旧目录下的 orchestrator/planner 等模块，并最终删除兼容层。
