# Agent系统最佳实践指南

## 概述

本文档提供了AutoReportAI系统中Agent使用的最佳实践，包括数据库会话管理、性能优化、错误处理等核心方面。

## 数据库会话管理

### ✅ 正确的使用方式

#### 1. 在API路由中使用

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.agents.factory import create_agent, AgentType

async def analyze_data_endpoint(
    data: dict,
    db: Session = Depends(get_db)
):
    """正确的Agent使用方式：通过依赖注入获取数据库会话"""
    
    # 创建Agent实例，传入数据库会话
    agent = create_agent(AgentType.ANALYSIS, db_session=db)
    
    # 执行分析
    result = await agent.analyze_with_ai(
        context=str(data),
        prompt="请分析这些数据",
        task_type="data_analysis"
    )
    
    return result
```

#### 2. 在服务类中使用

```python
from app.services.agents.factory import create_agent, AgentType

class DataAnalysisService:
    def __init__(self, db: Session):
        self.db = db
        # 使用工厂模式创建Agent
        self.agent = create_agent(AgentType.ANALYSIS, db_session=db)
    
    async def analyze_business_data(self, data):
        return await self.agent.analyze_with_ai(
            context=str(data),
            prompt="分析业务数据趋势",
            task_type="business_analysis"
        )
```

#### 3. 在独立函数中使用

```python
from app.services.agents.core.session_manager import managed_session
from app.services.agents.factory import create_agent, AgentType

async def standalone_analysis():
    """独立分析函数的正确使用方式"""
    with managed_session() as db:
        agent = create_agent(AgentType.ANALYSIS, db_session=db)
        return await agent.analyze_with_ai(
            context="独立分析任务",
            prompt="执行独立分析",
            task_type="standalone_analysis"
        )
```

### ❌ 错误的使用方式

```python
# 错误：模块级创建（无数据库会话）
bad_agent = create_agent(AgentType.ANALYSIS)  # 这会导致AI服务不可用

# 错误：直接实例化而不使用工厂
from app.services.agents.base.base_analysis_agent import BaseAnalysisAgent
bad_agent = BaseAnalysisAgent()  # 没有数据库会话
```

## Agent工厂模式使用

### 基本使用

```python
from app.services.agents.factory import create_agent, AgentType, AgentCreationMode

# 创建基础分析Agent
agent = create_agent(
    agent_type=AgentType.ANALYSIS,
    db_session=db,
    creation_mode=AgentCreationMode.STATELESS  # 每次创建新实例
)

# 创建会话范围的Agent（同一会话复用）
agent = create_agent(
    agent_type=AgentType.SCHEMA_ANALYSIS,
    db_session=db,
    creation_mode=AgentCreationMode.SESSION_SCOPED
)
```

### 工厂配置

```python
from app.services.agents.factory import get_agent_factory, AgentFactoryConfig, AgentCreationMode

# 配置工厂
config = AgentFactoryConfig(
    creation_mode=AgentCreationMode.SESSION_SCOPED,
    enable_health_check=True,
    auto_session_management=True,
    enable_metrics=True
)

factory = get_agent_factory(config)
agent = factory.create_agent(AgentType.ANALYSIS, db_session=db)
```

## 性能优化最佳实践

### 1. 使用性能监控

```python
from app.services.agents.core.performance_monitor import performance_context

async def heavy_analysis_task():
    with performance_context("heavy_analysis"):
        # 执行耗时操作
        result = await agent.analyze_with_ai(...)
        return result
```

### 2. 智能缓存使用

```python
# AI响应自动缓存
result = await agent.analyze_with_ai(
    context=context,
    prompt=prompt,
    task_type="analysis",
    use_cache=True  # 默认启用缓存
)

# 查询结果缓存
from app.services.agents.core.cache_manager import cache_query_result, get_cached_query_result

# 检查缓存
cached_result = get_cached_query_result(query, params)
if cached_result is None:
    result = execute_heavy_query(query, params)
    cache_query_result(query, result, params)
else:
    result = cached_result
```

### 3. 资源管理

```python
from app.services.agents.core.performance_monitor import get_performance_monitor

# 启动性能监控
monitor = get_performance_monitor()
monitor.start_monitoring()

# 手动优化系统资源
optimization_result = await optimize_system_performance()
```

## 健康检查和错误处理

### 1. Agent健康检查

```python
from app.services.agents.core.health_monitor import get_health_monitor

# 注册Agent健康检查
monitor = get_health_monitor()
monitor.register_agent_checker(agent)

# 执行系统健康检查
health_summary = await perform_system_health_check()
```

### 2. 错误处理模式

```python
import logging
from app.services.agents.core.performance_monitor import performance_context

logger = logging.getLogger(__name__)

async def robust_agent_operation():
    try:
        with performance_context("agent_operation"):
            # 检查Agent健康状态
            if hasattr(agent, 'health_check'):
                health = await agent.health_check()
                if not health.get("healthy", False):
                    logger.warning("Agent报告不健康状态")
            
            # 执行主要操作
            result = await agent.analyze_with_ai(
                context=context,
                prompt=prompt,
                task_type="robust_analysis"
            )
            
            return result
            
    except RuntimeError as e:
        if "AI服务未初始化" in str(e):
            logger.error("数据库会话问题，尝试重新初始化")
            # 重新创建Agent实例
            agent = create_agent(AgentType.ANALYSIS, db_session=db)
            # 重试操作
            return await agent.analyze_with_ai(context, prompt, "retry_analysis")
        raise
    except Exception as e:
        logger.error(f"Agent操作失败: {e}")
        # 记录性能问题
        raise
```

## 多Agent协作模式

### 1. Pipeline模式

```python
async def multi_agent_pipeline(data, db_session):
    """多Agent流水线处理"""
    
    # 第一阶段：数据发现
    discovery_agent = create_agent(AgentType.SCHEMA_ANALYSIS, db_session=db_session)
    schema_info = await discovery_agent.discover_data_structure(data)
    
    # 第二阶段：数据查询
    query_agent = create_agent(AgentType.DATA_QUERY, db_session=db_session)
    query_results = await query_agent.execute_intelligent_query(schema_info)
    
    # 第三阶段：内容生成
    content_agent = create_agent(AgentType.CONTENT_GENERATION, db_session=db_session)
    report = await content_agent.generate_report(query_results)
    
    # 第四阶段：可视化
    viz_agent = create_agent(AgentType.VISUALIZATION, db_session=db_session)
    charts = await viz_agent.create_visualizations(query_results)
    
    return {
        "report": report,
        "visualizations": charts,
        "metadata": schema_info
    }
```

### 2. 并行处理模式

```python
import asyncio

async def parallel_agent_processing(tasks, db_session):
    """并行Agent处理"""
    
    async def process_single_task(task):
        agent = create_agent(
            AgentType.ANALYSIS,
            db_session=db_session,
            creation_mode=AgentCreationMode.STATELESS
        )
        return await agent.analyze_with_ai(
            context=task["context"],
            prompt=task["prompt"],
            task_type=task["type"]
        )
    
    # 并行执行多个任务
    results = await asyncio.gather(
        *[process_single_task(task) for task in tasks],
        return_exceptions=True
    )
    
    return results
```

## 配置和部署建议

### 1. 性能调优配置

```python
from app.services.agents.core.performance_monitor import ResourceThresholds

# 性能阈值配置
thresholds = ResourceThresholds(
    max_cpu_percent=80.0,
    max_memory_percent=85.0,
    max_active_sessions=50,
    max_ai_pool_size=20,
    max_response_time_ms=5000.0,
    max_error_rate=0.05
)

# 启动监控
monitor = get_performance_monitor()
monitor.thresholds = thresholds
monitor.start_monitoring()
```

### 2. 缓存策略配置

```python
from app.services.agents.core.cache_manager import get_cache_manager
from datetime import timedelta

# 启动缓存清理任务
cache_manager = get_cache_manager()
cache_manager.start_cleanup_task()

# 自定义缓存TTL
cache_ai_response(
    response=response,
    prompt=prompt,
    ttl=timedelta(hours=2)  # 2小时过期
)
```

## 监控和调试

### 1. 性能监控

```python
# 获取性能摘要
monitor = get_performance_monitor()
summary = monitor.get_performance_summary()

# 获取缓存统计
cache_manager = get_cache_manager()
cache_stats = cache_manager.get_global_stats()

# 获取工厂统计
factory = get_agent_factory()
factory_stats = factory.get_factory_stats()
```

### 2. 健康检查

```python
# 系统整体健康检查
health_monitor = get_health_monitor()
health_summary = health_monitor.get_system_health_summary()

# 特定组件健康检查
db_health = await health_monitor.check_component("database")
ai_health = await health_monitor.check_component("ai_service")
```

### 3. 日志配置

```python
import logging

# 配置Agent相关日志
logging.getLogger("app.services.agents").setLevel(logging.INFO)
logging.getLogger("app.services.agents.core.performance_monitor").setLevel(logging.DEBUG)
logging.getLogger("app.services.agents.core.cache_manager").setLevel(logging.INFO)
```

## 常见问题和解决方案

### 1. "未提供数据库会话，AI服务将不可用"

**原因**: Agent创建时没有提供有效的数据库会话

**解决方案**:
```python
# 确保通过依赖注入或上下文管理器获取数据库会话
with managed_session() as db:
    agent = create_agent(AgentType.ANALYSIS, db_session=db)
```

### 2. 内存使用过高

**原因**: 缓存积累或Agent实例未正确释放

**解决方案**:
```python
# 手动清理缓存
cache_manager = get_cache_manager()
cache_manager.clear_all_caches()

# 优化内存
monitor = get_performance_monitor()
monitor.optimizer.optimize_memory(force_gc=True)
```

### 3. 响应时间过长

**原因**: 缓存未命中或系统资源不足

**解决方案**:
```python
# 预热缓存
await agent.analyze_with_ai(common_context, common_prompt, "preload")

# 使用性能监控定位问题
with performance_context("slow_operation"):
    result = await slow_operation()
```

## 总结

遵循这些最佳实践可以确保：

1. **稳定性**: 正确的数据库会话管理避免运行时错误
2. **性能**: 智能缓存和监控确保系统高效运行
3. **可维护性**: 工厂模式和健康检查简化运维
4. **可扩展性**: 模块化设计支持系统扩展

记住始终通过工厂模式创建Agent，确保数据库会话正确传递，并利用内置的监控和缓存功能来优化性能。