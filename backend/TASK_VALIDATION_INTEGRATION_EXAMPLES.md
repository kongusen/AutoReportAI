# 任务验证智能模式集成示例

## 概述

任务验证智能模式 (`execute_task_validation`) 是新的推荐方式，它结合了SQL验证和PTAV回退机制，实现真正的自动化运维。

## 集成示例

### 1. 任务执行服务集成

```python
# 在任务执行前使用智能验证
from app.services.infrastructure.agents.facade import AgentFacade
from app.services.infrastructure.agents.types import AgentInput

class TaskExecutionService:
    def __init__(self):
        self.agent_facade = AgentFacade(container)

    async def execute_scheduled_task(self, task_id: str):
        """定时任务执行 - 使用智能验证模式"""
        # 获取任务信息
        task = await self._get_task(task_id)

        # 构建Agent输入
        agent_input = AgentInput(
            user_prompt=f"执行任务: {task.name}",
            placeholder=PlaceholderInfo(
                description=task.description,
                type=task.task_type
            ),
            schema=await self._get_schema_info(task.data_source_id),
            context=TaskContext(
                task_time=int(datetime.now().timestamp()),
                timezone="Asia/Shanghai"
            ),
            # 关键：包含当前SQL用于验证
            task_driven_context={
                "current_sql": task.current_sql,  # 现有SQL
                "task_schedule": task.schedule,
                "last_execution": task.last_execution
            },
            user_id=task.user_id
        )

        # 🎯 使用智能验证模式 - 核心调用
        result = await self.agent_facade.execute_task_validation(agent_input)

        if result.success:
            # 更新任务的SQL（可能已被修正或重新生成）
            updated_sql = result.content
            await self._update_task_sql(task_id, updated_sql)

            # 记录验证结果
            validation_info = result.metadata
            logger.info(f"任务{task_id}验证成功: {validation_info.get('message')}")

            if validation_info.get('time_updated'):
                logger.info(f"时间属性已更新: {validation_info.get('time_range')}")

            if validation_info.get('generation_method') == 'ptav_fallback':
                logger.info(f"通过PTAV回退生成新SQL，原因: {validation_info.get('fallback_reason')}")

            return updated_sql
        else:
            logger.error(f"任务{task_id}验证失败: {result.metadata}")
            raise TaskValidationError(f"Task validation failed: {result.metadata}")
```

### 2. 报告生成服务集成

```python
class ReportGenerationService:
    async def generate_report(self, template_id: str, data_source_id: str, user_id: str):
        """报告生成 - 智能SQL验证 + 图表生成"""

        # 第一步：SQL验证和生成
        sql_input = AgentInput(
            user_prompt="生成报告数据查询",
            placeholder=PlaceholderInfo(
                description="报告数据查询",
                type="report_data"
            ),
            schema=await self._get_schema_info(data_source_id),
            task_driven_context={
                "template_id": template_id,
                "current_sql": await self._get_existing_sql(template_id),  # 可能为空
                "report_type": "comprehensive"
            },
            user_id=user_id
        )

        # 智能SQL验证/生成
        sql_result = await self.agent_facade.execute_task_validation(sql_input)

        if not sql_result.success:
            return {"error": "SQL生成失败", "details": sql_result.metadata}

        # 执行SQL获取数据
        data = await self._execute_sql(sql_result.content, data_source_id)

        # 第二步：图表生成（如果需要）
        if self._needs_chart(data):
            chart_input = AgentInput(
                user_prompt="生成数据图表",
                data_rows=data.get("rows", []),
                data_columns=data.get("columns", []),
                user_id=user_id
            )

            chart_result = await self.agent_facade.execute(chart_input, mode="report_chart_generation")

            return {
                "sql": sql_result.content,
                "data": data,
                "chart": chart_result.content if chart_result.success else None,
                "validation_info": sql_result.metadata
            }

        return {
            "sql": sql_result.content,
            "data": data,
            "validation_info": sql_result.metadata
        }
```

### 3. API端点集成示例

```python
# 在API端点中使用
@router.post("/tasks/{task_id}/execute")
async def execute_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """执行任务API - 使用智能验证"""
    try:
        task = get_task_by_id(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # 构建Agent输入
        agent_input = AgentInput(
            user_prompt=f"执行任务: {task.name}",
            placeholder=PlaceholderInfo(
                description=task.description,
                type=task.task_type
            ),
            schema=await get_schema_from_data_source(task.data_source_id),
            task_driven_context={
                "current_sql": task.sql_content,  # 现有SQL
                "task_id": task_id,
                "execution_context": "api_trigger"
            },
            user_id=str(current_user.id)
        )

        # 使用智能验证
        facade = AgentFacade(container)
        result = await facade.execute_task_validation(agent_input)

        if result.success:
            # 更新任务SQL
            task.sql_content = result.content
            task.last_validated = datetime.utcnow()
            db.commit()

            return {
                "success": True,
                "sql": result.content,
                "validation_info": result.metadata,
                "message": "任务执行成功"
            }
        else:
            return {
                "success": False,
                "error": result.metadata.get("error"),
                "validation_info": result.metadata
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 4. 统一调用方式

为了简化调用，可以创建一个统一的工具函数：

```python
# utils/agent_helper.py
async def execute_task_with_validation(
    task_context: dict,
    user_id: str,
    facade: AgentFacade = None
) -> dict:
    """
    统一的任务验证执行工具函数

    Args:
        task_context: 包含任务相关信息的字典
        user_id: 用户ID
        facade: Agent门面实例（可选）

    Returns:
        统一格式的执行结果
    """
    if not facade:
        facade = AgentFacade(container)

    agent_input = AgentInput(
        user_prompt=task_context.get("description", "执行任务"),
        placeholder=PlaceholderInfo(
            description=task_context.get("description", ""),
            type=task_context.get("type", "general")
        ),
        schema=task_context.get("schema"),
        task_driven_context=task_context.get("context", {}),
        user_id=user_id
    )

    result = await facade.execute_task_validation(agent_input)

    return {
        "success": result.success,
        "sql": result.content if result.success else None,
        "error": result.metadata.get("error") if not result.success else None,
        "validation_info": result.metadata,
        "time_updated": result.metadata.get("time_updated", False),
        "generation_method": result.metadata.get("generation_method", "validation"),
        "fallback_reason": result.metadata.get("fallback_reason")
    }

# 使用示例
result = await execute_task_with_validation(
    task_context={
        "description": "生成销售报表",
        "type": "report",
        "schema": schema_info,
        "context": {
            "current_sql": existing_sql,
            "data_source_id": "ds_001"
        }
    },
    user_id="user_123"
)

if result["success"]:
    print(f"SQL: {result['sql']}")
    if result["time_updated"]:
        print("时间属性已更新")
    if result["generation_method"] == "ptav_fallback":
        print(f"通过回退模式生成，原因: {result['fallback_reason']}")
```

## 关键特性总结

1. **自动检测**: 自动检测是否存在SQL，无需手动判断
2. **时间智能**: 自动更新SQL中的时间属性（如日期范围）
3. **智能回退**: SQL缺失或不可修复时自动生成新SQL
4. **详细反馈**: 提供详细的验证信息和执行结果
5. **统一接口**: 一个方法处理所有任务验证场景

## 监控和调试

```python
# 监控验证结果
def log_validation_result(result: dict):
    if result["success"]:
        logger.info(f"任务验证成功: {result['validation_info'].get('message')}")

        if result["time_updated"]:
            logger.info(f"时间属性更新: {result['validation_info'].get('time_range')}")

        if result["generation_method"] == "ptav_fallback":
            logger.warning(f"使用回退模式生成SQL: {result['fallback_reason']}")

    else:
        logger.error(f"任务验证失败: {result['error']}")
        logger.error(f"验证详情: {result['validation_info']}")
```

这个智能验证模式是生产环境的最佳实践，它实现了真正的自动化运维，确保任务的SQL始终保持健康和时效性。