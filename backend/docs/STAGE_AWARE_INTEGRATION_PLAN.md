# Stage-Aware Agent 与现有系统连接规划

## 📋 概述

本文档规划如何将重构后的 Stage-Aware Agent 系统与现有项目功能建立完整连接，实现渐进式迁移和无缝集成。

---

## 🎯 集成目标

### 核心目标
1. **无缝集成** - Stage-Aware Agent 与现有系统和谐共存
2. **渐进迁移** - 支持逐步从旧系统迁移到新系统
3. **功能增强** - 提供三阶段TT递归能力
4. **向后兼容** - 保持现有API和调用方式不变

### 性能目标
- SQL生成准确率：75% → 95%+
- LLM调用次数：5-7次 → 1-2次（减少70%）
- 总体耗时：~15分钟（50个占位符）→ ~5分钟（减少67%）
- Token消耗：减少60%

---

## 🏗️ 现有系统架构分析

### 调用链路
```
前端请求
    ↓
API端点 (/api/endpoints/placeholders.py)
    ↓
UnifiedServiceFacade (统一服务门面)
    ↓
PlaceholderApplicationService (应用服务)
    ↓
AgentService (旧的基础设施服务)
    ↓
LoomAgentFacade (旧的Agent门面)
    ↓
LoomAgentRuntime (执行引擎)
```

### Celery异步任务链路
```
定时触发/手动触发
    ↓
Celery Task (workflow_tasks.py)
    ↓
UnifiedServiceFacade
    ↓
PlaceholderApplicationService
    ↓
... (同上)
```

### 关键服务依赖
1. **Container** - 依赖注入容器
2. **TemplateService** - 模板和占位符配置
3. **UserDataSourceService** - 用户数据源配置
4. **IntelligentConfigManager** - LLM配置管理
5. **TimeInferenceService** - Cron表达式解析
6. **CacheService** - 模板和数据缓存
7. **SchemaContextRetriever** - 智能上下文检索

---

## 🚀 Stage-Aware Agent 架构

### 核心组件
```
StageAwareAgentService (新的服务封装)
    ↓
StageAwareFacade (三阶段门面)
    ↓
三阶段独立执行（每个阶段使用TT递归）
    ├─ SQL生成阶段 (execute_sql_generation_stage)
    ├─ 图表生成阶段 (execute_chart_generation_stage)
    └─ 文档生成阶段 (execute_document_generation_stage)
```

### 关键特性
- ✅ TT递归执行（Loom 0.0.3）
- ✅ 阶段感知的智能Prompt
- ✅ 智能上下文注入
- ✅ 质量评分和自动优化
- ✅ 事件流式反馈

---

## 📐 集成策略

### 策略1: 适配器模式（推荐）

**原理**: 创建适配器层，将 Stage-Aware Agent 适配到现有服务接口

**优势**:
- ✅ 最小化代码改动
- ✅ 保持现有API不变
- ✅ 支持配置驱动切换
- ✅ 便于A/B测试

**实施步骤**:

#### Phase 1: 创建适配器服务
```python
# backend/app/services/application/adapters/stage_aware_adapter.py

class StageAwareAgentAdapter:
    """
    Stage-Aware Agent 适配器

    将 Stage-Aware Agent 适配到现有 PlaceholderApplicationService 接口
    """

    def __init__(self, container, enable_stage_aware: bool = False):
        self.container = container
        self.enable_stage_aware = enable_stage_aware

        # 新系统
        self.stage_aware_service = None

        # 旧系统（兼容）
        self.legacy_agent_service = None

    async def initialize(self):
        """初始化服务"""
        if self.enable_stage_aware:
            # 初始化新的 Stage-Aware 系统
            from app.services.infrastructure.agents.stage_aware_service import (
                create_stage_aware_agent_service
            )
            self.stage_aware_service = await create_stage_aware_agent_service(
                self.container
            )
        else:
            # 初始化旧系统
            from app.services.infrastructure.agents import AgentService
            self.legacy_agent_service = AgentService(
                container=self.container
            )

    async def analyze_placeholder(self, request):
        """分析占位符（适配接口）"""
        if self.enable_stage_aware:
            return await self._analyze_with_stage_aware(request)
        else:
            return await self._analyze_with_legacy(request)

    async def _analyze_with_stage_aware(self, request):
        """使用 Stage-Aware Agent 分析"""
        async for event in self.stage_aware_service.generate_sql_with_tt_recursion(
            placeholder=request.business_command,
            data_source_id=request.data_source_id,
            user_id=request.user_id,
            task_context=request.context,
            template_context=getattr(request, 'template_context', None)
        ):
            # 转换事件格式为现有系统格式
            yield self._convert_event_format(event)

    async def _analyze_with_legacy(self, request):
        """使用旧系统分析（兼容）"""
        # 调用旧的 AgentService
        async for event in self.legacy_agent_service.analyze_placeholder(request):
            yield event

    def _convert_event_format(self, stage_aware_event):
        """转换事件格式"""
        # 将 Stage-Aware 的事件格式转换为现有系统的格式
        return {
            "type": stage_aware_event.event_type,
            "stage": stage_aware_event.stage.value if stage_aware_event.stage else None,
            "data": stage_aware_event.data,
            "timestamp": stage_aware_event.timestamp
        }
```

#### Phase 2: 修改 PlaceholderApplicationService
```python
# backend/app/services/application/placeholder/placeholder_service.py

class PlaceholderApplicationService:
    def __init__(self, user_id: str = None, enable_stage_aware: bool = False):
        self.container = Container()
        self.user_id = user_id

        # 🆕 使用适配器
        from app.services.application.adapters.stage_aware_adapter import (
            StageAwareAgentAdapter
        )
        self.agent_adapter = StageAwareAgentAdapter(
            container=self.container,
            enable_stage_aware=enable_stage_aware  # 配置驱动
        )

        # ... 其他初始化代码 ...

    async def analyze_placeholder(self, request):
        """分析占位符 - 通过适配器调用"""
        await self.agent_adapter.initialize()

        async for event in self.agent_adapter.analyze_placeholder(request):
            yield event
```

#### Phase 3: 添加配置开关
```python
# backend/app/core/config.py

class Settings(BaseSettings):
    # ... 现有配置 ...

    # 🆕 Stage-Aware Agent 配置
    ENABLE_STAGE_AWARE_AGENT: bool = False  # 默认关闭，渐进启用
    STAGE_AWARE_AGENT_MODE: str = "hybrid"  # "legacy" | "stage_aware" | "hybrid"

    # A/B 测试配置
    STAGE_AWARE_ROLLOUT_PERCENTAGE: int = 0  # 0-100，灰度发布百分比
```

#### Phase 4: 更新 UnifiedServiceFacade
```python
# backend/app/services/application/facades/unified_service_facade.py

class UnifiedServiceFacade:
    def __init__(self, db: Session, user_id: str):
        # ... 现有代码 ...

        # 🆕 根据配置选择 Agent 模式
        from app.core.config import settings
        self._enable_stage_aware = self._should_use_stage_aware(user_id)

    def _should_use_stage_aware(self, user_id: str) -> bool:
        """决定是否使用 Stage-Aware Agent"""
        from app.core.config import settings

        if settings.STAGE_AWARE_AGENT_MODE == "legacy":
            return False
        elif settings.STAGE_AWARE_AGENT_MODE == "stage_aware":
            return True
        elif settings.STAGE_AWARE_AGENT_MODE == "hybrid":
            # A/B 测试逻辑
            import hashlib
            user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            percentage = user_hash % 100
            return percentage < settings.STAGE_AWARE_ROLLOUT_PERCENTAGE

        return False

    async def _get_placeholder_service(self):
        """获取占位符服务"""
        if self._placeholder_service is None:
            from app.services.application.placeholder.placeholder_service import (
                PlaceholderApplicationService
            )
            self._placeholder_service = PlaceholderApplicationService(
                user_id=self.user_id,
                enable_stage_aware=self._enable_stage_aware  # 🆕 传递配置
            )
            await self._placeholder_service.initialize()

        return self._placeholder_service
```

---

## 🔗 基础服务连接

### 1. 模板服务连接

**目标**: Stage-Aware Agent 能够获取用户配置的模板和占位符信息

**实施**:
```python
# backend/app/services/infrastructure/agents/adapters/template_adapter.py

class TemplateContextAdapter:
    """模板上下文适配器"""

    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.template_service = None

    async def get_template_context(
        self,
        template_id: str,
        include_placeholders: bool = True
    ) -> Dict[str, Any]:
        """获取模板上下文"""
        if not self.template_service:
            from app.services.domain.template.template_service import TemplateService
            self.template_service = TemplateService(self.db, self.user_id)

        # 获取模板和占位符配置
        template_data = await self.template_service.get_template_with_placeholders(
            template_id=template_id,
            user_id=self.user_id,
            include_inactive=False
        )

        # 转换为 Stage-Aware 所需格式
        return {
            "template_id": template_id,
            "template_name": template_data.get("name"),
            "template_type": template_data.get("type"),
            "placeholders": self._format_placeholders(
                template_data.get("placeholders", [])
            ) if include_placeholders else [],
            "metadata": template_data.get("metadata", {})
        }

    def _format_placeholders(self, placeholders: List[Dict]) -> List[Dict]:
        """格式化占位符信息"""
        return [
            {
                "name": p.get("name"),
                "text": p.get("text"),
                "type": p.get("type"),
                "requirements": p.get("requirements", {}),
                "constraints": p.get("constraints", {})
            }
            for p in placeholders
        ]
```

**集成到 Stage-Aware**:
```python
# backend/app/services/infrastructure/agents/facade.py (StageAwareFacade)

async def execute_sql_generation_stage(
    self,
    placeholder: str,
    data_source_id: int,
    user_id: str,
    template_id: Optional[str] = None,  # 🆕 新增参数
    **kwargs
) -> AsyncGenerator[AgentEvent, None]:
    """SQL生成阶段 - 支持模板上下文"""

    # 🆕 获取模板上下文
    template_context = {}
    if template_id:
        from app.db.session import get_db_session
        from .adapters.template_adapter import TemplateContextAdapter

        with get_db_session() as db:
            adapter = TemplateContextAdapter(db, user_id)
            template_context = await adapter.get_template_context(template_id)

    # 合并到任务上下文
    task_context = kwargs.get('task_context', {})
    task_context['template'] = template_context
    kwargs['task_context'] = task_context

    # 执行原有逻辑
    async for event in self._execute_stage(...):
        yield event
```

### 2. 数据源服务连接

**目标**: Stage-Aware Agent 能够获取用户配置的数据源连接信息

**实施**: 已通过 Container 实现，无需额外工作

```python
# 现有代码已支持
user_ds_service = self.container.user_data_source_service
data_source = await user_ds_service.get_user_data_source(user_id, data_source_id)
```

### 3. LLM配置服务连接

**目标**: Stage-Aware Agent 能够使用用户配置的LLM服务

**实施**: 已通过 LLMAdapter 实现，无需额外工作

```python
# backend/app/services/infrastructure/agents/llm_adapter.py

async def get_llm_adapter(container):
    """从Container获取LLM适配器"""
    llm_service = container.llm_service

    # 适配器自动使用用户配置的LLM
    return LoomLLMAdapter(llm_service)
```

### 4. 时间推断服务连接

**目标**: Stage-Aware Agent 能够解析Cron表达式并推断数据时间范围

**实施**:
```python
# backend/app/services/infrastructure/agents/adapters/time_adapter.py

class TimeContextAdapter:
    """时间上下文适配器"""

    def __init__(self):
        from app.services.data.template.time_inference_service import TimeInferenceService
        from app.utils.time_context import TimeContextManager

        self.time_inference = TimeInferenceService()
        self.time_manager = TimeContextManager()

    def build_time_context(
        self,
        cron_expression: Optional[str] = None,
        execution_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """构建时间上下文"""
        if not cron_expression:
            return {}

        # 使用现有服务推断时间范围
        time_context = self.time_manager.build_task_time_context(
            cron_expression=cron_expression,
            execution_time=execution_time
        )

        return {
            "period": time_context.get("period"),
            "start_date": time_context.get("start_date"),
            "end_date": time_context.get("end_date"),
            "cron_expression": cron_expression,
            "execution_time": execution_time or datetime.now()
        }
```

**集成**:
```python
# 在 StageAwareFacade 中使用
from .adapters.time_adapter import TimeContextAdapter

time_adapter = TimeContextAdapter()
time_context = time_adapter.build_time_context(
    cron_expression=task_context.get("cron_expression"),
    execution_time=task_context.get("execution_time")
)

# 注入到 Prompt
task_context['time_window'] = time_context
```

### 5. 缓存服务连接

**目标**: Stage-Aware Agent 能够使用模板缓存、Schema缓存等

**实施**: 已通过 SchemaContextRetriever 和 CacheService 实现

---

## 🎯 三阶段Pipeline连接

### Stage 1: SQL生成阶段

**现有流程**:
```
PlaceholderApplicationService.analyze_placeholder()
    → AgentService.analyze()
    → LoomAgentFacade.analyze_placeholder()
    → 返回 SQL
```

**新流程**:
```
PlaceholderApplicationService.analyze_placeholder()
    → StageAwareAgentAdapter.analyze_placeholder()
    → StageAwareAgentService.generate_sql_with_tt_recursion()
    → StageAwareFacade.execute_sql_generation_stage()
    → 返回 SQL (使用TT递归优化)
```

**连接点**:
- 输入: `placeholder`, `data_source_id`, `user_id`, `task_context`
- 输出: `sql`, `reasoning`, `quality_score`, `iterations_used`

### Stage 2: 图表生成阶段

**现有流程**:
```
ChartService.generate_chart_config()
    → 基于规则的图表选择
    → 返回图表配置
```

**新流程**:
```
StageAwareAgentService.generate_chart_with_tt_recursion()
    → StageAwareFacade.execute_chart_generation_stage()
    → 智能分析数据特征
    → 推荐最佳图表类型
    → 返回优化的图表配置
```

**连接点**:
- 输入: `etl_data`, `chart_placeholder`, `user_id`
- 输出: `chart_config`, `chart_type`, `reasoning`

### Stage 3: 文档生成阶段

**现有流程**:
```
DocumentService.generate_document()
    → 简单模板替换
    → 返回文档
```

**新流程**:
```
StageAwareAgentService.generate_document_with_tt_recursion()
    → StageAwareFacade.execute_document_generation_stage()
    → 智能生成流畅文本
    → 返回优化的文档内容
```

**连接点**:
- 输入: `paragraph_context`, `placeholder_data`, `user_id`
- 输出: `document_text`, `reasoning`

---

## 📊 Celery任务集成

### 更新 workflow_tasks.py

```python
# backend/app/services/application/tasks/workflow_tasks.py

@celery_app.task(bind=True, name='generate_report_with_stage_aware')
def generate_report_with_stage_aware(
    self,
    task_id: str,
    data_source_ids: List[str],
    execution_context: Optional[Dict[str, Any]] = None,
    use_stage_aware: bool = True  # 🆕 控制是否使用 Stage-Aware
) -> Dict[str, Any]:
    """
    使用 Stage-Aware Agent 生成报告
    """
    try:
        from app.db.session import get_db_session
        from app import crud
        from app.services.application.facades.unified_service_facade import (
            create_unified_service_facade
        )

        with get_db_session() as db:
            task_obj = crud.task.get(db, id=int(task_id))
            if not task_obj:
                raise ValueError(f"任务不存在: {task_id}")

            user_id = str(task_obj.owner_id)
            template_id = str(task_obj.template_id)
            ds_id = str(task_obj.data_source_id)
            cron_expr = task_obj.schedule

            # 🆕 创建 Facade 时指定是否使用 Stage-Aware
            facade = create_unified_service_facade(
                db,
                user_id,
                enable_stage_aware=use_stage_aware  # 传递配置
            )

            import asyncio
            assembled = asyncio.run(
                facade.generate_report_v2(
                    template_id=template_id,
                    data_source_id=ds_id,
                    schedule={'cron_expression': cron_expr} if cron_expr else None,
                    execution_time=datetime.now().isoformat(),
                )
            )

            return {
                'success': True,
                'task_id': task_id,
                'agent_mode': 'stage_aware' if use_stage_aware else 'legacy',
                'assembled': assembled,
            }

    except Exception as e:
        logger.error(f"报告生成失败: {e}")
        return {
            'success': False,
            'task_id': task_id,
            'error': str(e),
        }
```

---

## 🧪 测试和验证

### 单元测试
```python
# backend/tests/integration/test_stage_aware_integration.py

import pytest
from app.core.container import Container
from app.services.application.adapters.stage_aware_adapter import (
    StageAwareAgentAdapter
)

@pytest.mark.asyncio
async def test_stage_aware_adapter_sql_generation():
    """测试 Stage-Aware 适配器 SQL 生成"""
    container = Container()
    adapter = StageAwareAgentAdapter(
        container=container,
        enable_stage_aware=True
    )
    await adapter.initialize()

    # 模拟请求
    from app.services.domain.placeholder.types import PlaceholderAnalysisRequest
    request = PlaceholderAnalysisRequest(
        placeholder_id="test_001",
        business_command="统计用户注册数",
        data_source_id=1,
        user_id="test_user"
    )

    # 执行分析
    result = None
    async for event in adapter.analyze_placeholder(request):
        if event.get("type") == "sql_generated":
            result = event.get("data", {}).get("sql")
            break

    assert result is not None
    assert "SELECT" in result.upper()
```

### 集成测试
```python
@pytest.mark.asyncio
async def test_unified_facade_with_stage_aware():
    """测试 UnifiedServiceFacade 集成 Stage-Aware"""
    from app.db.session import get_db_session
    from app.services.application.facades.unified_service_facade import (
        create_unified_service_facade
    )

    with get_db_session() as db:
        facade = create_unified_service_facade(
            db,
            user_id="test_user",
            enable_stage_aware=True
        )

        result = await facade.generate_report_v2(
            template_id="test_template",
            data_source_id="1",
            schedule={"cron_expression": "0 0 * * *"},
            execution_time=datetime.now().isoformat()
        )

        assert result["success"] is True
```

### A/B测试验证
```bash
# 设置环境变量启用灰度发布
export STAGE_AWARE_AGENT_MODE="hybrid"
export STAGE_AWARE_ROLLOUT_PERCENTAGE=20  # 20%用户使用新系统

# 运行测试
python scripts/test_ab_deployment.py
```

---

## 📈 部署计划

### Phase 1: 开发环境验证（1周）
- [ ] 创建适配器服务
- [ ] 集成到 PlaceholderApplicationService
- [ ] 添加配置开关
- [ ] 编写单元测试和集成测试
- [ ] 开发环境验证

### Phase 2: 测试环境部署（1周）
- [ ] 部署到测试环境
- [ ] 配置 `ENABLE_STAGE_AWARE_AGENT=True`
- [ ] 执行完整的集成测试套件
- [ ] 性能基准测试
- [ ] Bug修复和优化

### Phase 3: 灰度发布（2-4周）
- [ ] 配置 `STAGE_AWARE_AGENT_MODE=hybrid`
- [ ] 设置 `STAGE_AWARE_ROLLOUT_PERCENTAGE=5`（5%用户）
- [ ] 监控关键指标：准确率、耗时、错误率
- [ ] 逐步提升到 10% → 25% → 50% → 100%
- [ ] 每个阶段观察 3-7 天

### Phase 4: 全量发布（1周）
- [ ] 配置 `STAGE_AWARE_AGENT_MODE=stage_aware`
- [ ] 所有用户使用新系统
- [ ] 监控系统稳定性
- [ ] 收集用户反馈
- [ ] 持续优化

### Phase 5: 清理旧代码（1周）
- [ ] 移除旧的 AgentService 代码
- [ ] 移除适配器层（直接使用 Stage-Aware）
- [ ] 清理配置开关
- [ ] 更新文档

---

## 🔧 配置管理

### 环境变量配置
```bash
# .env

# Stage-Aware Agent 配置
ENABLE_STAGE_AWARE_AGENT=false  # 主开关
STAGE_AWARE_AGENT_MODE=legacy   # legacy | stage_aware | hybrid
STAGE_AWARE_ROLLOUT_PERCENTAGE=0  # 0-100

# 性能配置
STAGE_AWARE_MAX_ITERATIONS=5
STAGE_AWARE_QUALITY_THRESHOLD=0.8
STAGE_AWARE_TIMEOUT=120  # 秒

# 调试配置
STAGE_AWARE_DEBUG=false
STAGE_AWARE_LOG_LEVEL=INFO
```

### 数据库配置（可选）
```sql
-- 用户级别的 Agent 配置
CREATE TABLE user_agent_config (
    user_id VARCHAR(255) PRIMARY KEY,
    enable_stage_aware BOOLEAN DEFAULT FALSE,
    agent_mode VARCHAR(50) DEFAULT 'legacy',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 模板级别的 Agent 配置
CREATE TABLE template_agent_config (
    template_id VARCHAR(255) PRIMARY KEY,
    enable_stage_aware BOOLEAN DEFAULT FALSE,
    preferred_stage_config JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 📊 监控和指标

### 关键指标
```python
# backend/app/services/monitoring/stage_aware_metrics.py

class StageAwareMetrics:
    """Stage-Aware Agent 监控指标"""

    @staticmethod
    def record_request(user_id: str, mode: str):
        """记录请求"""
        # Prometheus/Grafana 集成
        pass

    @staticmethod
    def record_performance(
        user_id: str,
        stage: str,
        duration_ms: int,
        iterations: int,
        quality_score: float
    ):
        """记录性能指标"""
        pass

    @staticmethod
    def record_error(user_id: str, stage: str, error_type: str):
        """记录错误"""
        pass
```

### Grafana 仪表板
- SQL生成阶段平均耗时
- 图表生成阶段平均耗时
- 文档生成阶段平均耗时
- TT递归迭代次数分布
- 质量评分分布
- 错误率趋势
- 新旧系统对比

---

## 🎯 成功标准

### 功能标准
- ✅ 所有现有API接口保持兼容
- ✅ 支持配置驱动的系统切换
- ✅ 三阶段Pipeline正常工作
- ✅ 事件流式反馈正常
- ✅ 错误处理和降级机制完善

### 性能标准
- ✅ SQL生成准确率 ≥ 95%
- ✅ LLM调用次数减少 ≥ 60%
- ✅ 总体耗时减少 ≥ 50%
- ✅ Token消耗减少 ≥ 50%
- ✅ 系统稳定性 ≥ 99.9%

### 用户体验标准
- ✅ 响应时间无明显增加
- ✅ 错误率无明显增加
- ✅ 用户满意度提升
- ✅ 支持流式反馈提升体验

---

## 🔄 回滚计划

### 快速回滚
```bash
# 立即切换回旧系统
export STAGE_AWARE_AGENT_MODE=legacy

# 或者通过配置文件
python scripts/rollback_to_legacy.py
```

### 数据迁移回滚
如果使用了新的数据模型，需要准备数据回滚脚本：
```sql
-- 回滚数据结构（如果需要）
-- ... 回滚 SQL ...
```

---

## 📚 相关文档

- [Stage-Aware Agent 架构文档](README.md)
- [三阶段实现计划](THREE_STAGE_IMPLEMENTATION_PLAN.md)
- [重构完成总结](REFACTORING_COMPLETE.md)
- [API使用指南](stage_aware_api.py)

---

## 📝 总结

本规划采用**适配器模式 + 配置驱动 + 渐进迁移**的策略，确保 Stage-Aware Agent 与现有系统的无缝集成。通过灰度发布和A/B测试，逐步验证新系统的稳定性和性能提升，最终实现平滑迁移。

**关键优势**:
- ✅ 最小化风险 - 支持快速回滚
- ✅ 无缝集成 - 保持现有API不变
- ✅ 灵活切换 - 配置驱动的系统选择
- ✅ 渐进迁移 - 逐步提升使用比例
- ✅ 充分验证 - 完善的测试和监控

**预期成果**:
- 🎯 SQL生成准确率提升至95%+
- ⚡ 总体耗时减少67%
- 💰 Token消耗减少60%
- 🚀 用户体验显著提升
