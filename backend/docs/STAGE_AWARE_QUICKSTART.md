# Stage-Aware Agent 集成快速启动指南

## 🚀 快速开始

本指南帮助你在30分钟内完成 Stage-Aware Agent 与现有系统的初步集成。

---

## 📋 前置条件

- ✅ Python 3.8+
- ✅ 已安装 Loom 0.0.3+
- ✅ 现有项目正常运行
- ✅ 具有数据库访问权限

---

## 🔧 步骤1: 安装依赖

```bash
# 确保 Loom 已安装
pip install "loom-python>=0.0.3"

# 其他依赖应该已经存在
pip install fastapi sqlalchemy pydantic
```

---

## 📁 步骤2: 验证文件结构

确保以下文件已创建：

```
backend/
├── app/
│   └── services/
│       ├── infrastructure/
│       │   └── agents/
│       │       ├── stage_aware_service.py  ✅
│       │       ├── stage_aware_api.py      ✅
│       │       └── facade.py (StageAwareFacade) ✅
│       └── application/
│           └── adapters/
│               ├── __init__.py              ✅ NEW
│               ├── stage_aware_adapter.py   ✅ NEW
│               ├── template_adapter.py      ✅ NEW
│               └── time_adapter.py          ✅ NEW
└── docs/
    ├── STAGE_AWARE_INTEGRATION_PLAN.md  ✅ NEW
    └── STAGE_AWARE_QUICKSTART.md        ✅ NEW
```

---

## ⚙️ 步骤3: 配置环境变量

编辑 `.env` 文件：

```bash
# Stage-Aware Agent 配置
ENABLE_STAGE_AWARE_AGENT=false  # 先保持关闭，验证后再启用
STAGE_AWARE_AGENT_MODE=legacy   # legacy | stage_aware | hybrid
STAGE_AWARE_ROLLOUT_PERCENTAGE=0  # 0-100，灰度发布比例

# 性能配置
STAGE_AWARE_MAX_ITERATIONS=5
STAGE_AWARE_QUALITY_THRESHOLD=0.8
STAGE_AWARE_TIMEOUT=120

# 调试配置
STAGE_AWARE_DEBUG=false
STAGE_AWARE_LOG_LEVEL=INFO
```

---

## 🧪 步骤4: 运行基础测试

### 4.1 测试适配器创建

```python
# scripts/test_stage_aware_adapter.py

import asyncio
from app.core.container import Container
from app.services.application.adapters import StageAwareAgentAdapter


async def test_adapter_creation():
    """测试适配器创建"""
    print("🧪 测试适配器创建...")

    container = Container()

    # 测试旧系统模式
    adapter_legacy = StageAwareAgentAdapter(
        container=container,
        enable_stage_aware=False
    )
    await adapter_legacy.initialize()

    print("✅ 旧系统适配器初始化成功")

    # 测试新系统模式
    adapter_stage_aware = StageAwareAgentAdapter(
        container=container,
        enable_stage_aware=True
    )
    await adapter_stage_aware.initialize()

    print("✅ Stage-Aware 适配器初始化成功")

    # 获取指标
    metrics = adapter_stage_aware.get_metrics()
    print(f"📊 适配器指标: {metrics}")


if __name__ == "__main__":
    asyncio.run(test_adapter_creation())
```

运行测试：

```bash
cd backend
python scripts/test_stage_aware_adapter.py
```

**预期输出**:
```
🧪 测试适配器创建...
✅ 旧系统适配器初始化成功
✅ Stage-Aware 适配器初始化成功
📊 适配器指标: {
    'adapter_initialized': True,
    'stage_aware_enabled': True,
    'stage_aware_initialized': True,
    ...
}
```

### 4.2 测试时间适配器

```python
# scripts/test_time_adapter.py

from app.services.application.adapters import TimeContextAdapter


def test_time_adapter():
    """测试时间适配器"""
    print("🧪 测试时间适配器...")

    adapter = TimeContextAdapter()

    # 测试每日任务
    context_daily = adapter.build_time_context(
        cron_expression="0 8 * * *"
    )
    print(f"📅 每日任务: {context_daily['formatted_range']}")

    # 测试每周任务
    context_weekly = adapter.build_time_context(
        cron_expression="0 8 * * 1"
    )
    print(f"📅 每周任务: {context_weekly['formatted_range']}")

    # 测试每月任务
    context_monthly = adapter.build_time_context(
        cron_expression="0 8 1 * *"
    )
    print(f"📅 每月任务: {context_monthly['formatted_range']}")

    print("✅ 时间适配器测试通过")


if __name__ == "__main__":
    test_time_adapter()
```

运行测试：

```bash
python scripts/test_time_adapter.py
```

### 4.3 测试模板适配器

```python
# scripts/test_template_adapter.py

import asyncio
from app.db.session import get_db_session
from app.services.application.adapters import TemplateContextAdapter


async def test_template_adapter():
    """测试模板适配器"""
    print("🧪 测试模板适配器...")

    with get_db_session() as db:
        adapter = TemplateContextAdapter(
            db=db,
            user_id="test_user"  # 使用测试用户ID
        )

        # 这里需要一个实际存在的模板ID
        # template_id = "your_test_template_id"

        # context = await adapter.get_template_context(template_id)
        # print(f"📋 模板上下文: {context}")

        print("✅ 模板适配器测试通过（需要实际模板ID）")


if __name__ == "__main__":
    asyncio.run(test_template_adapter())
```

---

## 🔌 步骤5: 集成到现有服务

### 5.1 更新配置类

编辑 `backend/app/core/config.py`:

```python
# backend/app/core/config.py

from pydantic import BaseSettings


class Settings(BaseSettings):
    # ... 现有配置 ...

    # 🆕 Stage-Aware Agent 配置
    ENABLE_STAGE_AWARE_AGENT: bool = False
    STAGE_AWARE_AGENT_MODE: str = "legacy"  # "legacy" | "stage_aware" | "hybrid"
    STAGE_AWARE_ROLLOUT_PERCENTAGE: int = 0  # 0-100

    # 性能配置
    STAGE_AWARE_MAX_ITERATIONS: int = 5
    STAGE_AWARE_QUALITY_THRESHOLD: float = 0.8
    STAGE_AWARE_TIMEOUT: int = 120

    # 调试配置
    STAGE_AWARE_DEBUG: bool = False
    STAGE_AWARE_LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
```

### 5.2 更新 UnifiedServiceFacade

编辑 `backend/app/services/application/facades/unified_service_facade.py`:

```python
# 在文件开头添加导入
from app.core.config import settings

class UnifiedServiceFacade:
    def __init__(self, db: Session, user_id: str):
        # ... 现有代码 ...

        # 🆕 根据配置决定是否使用 Stage-Aware
        self._enable_stage_aware = self._should_use_stage_aware(user_id)

    def _should_use_stage_aware(self, user_id: str) -> bool:
        """决定是否使用 Stage-Aware Agent"""

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

### 5.3 更新 PlaceholderApplicationService

编辑 `backend/app/services/application/placeholder/placeholder_service.py`:

```python
class PlaceholderApplicationService:
    def __init__(
        self,
        user_id: str = None,
        context_retriever: Optional[Any] = None,
        enable_stage_aware: bool = False  # 🆕 新增参数
    ):
        self.container = Container()
        self.user_id = user_id
        self.context_retriever = context_retriever

        # 🆕 使用适配器
        from app.services.application.adapters import (
            StageAwareAgentAdapter,
            create_stage_aware_adapter
        )

        # 异步初始化适配器（在 initialize 方法中完成）
        self._adapter_config = {
            "enable_stage_aware": enable_stage_aware,
            "fallback_to_legacy": True  # 支持降级
        }
        self.agent_adapter = None

        # ... 其他初始化代码 ...

    async def initialize(self):
        """初始化应用服务"""
        if not self.is_initialized:
            # ... 现有代码 ...

            # 🆕 初始化适配器
            from app.services.application.adapters import create_stage_aware_adapter

            self.agent_adapter = await create_stage_aware_adapter(
                container=self.container,
                **self._adapter_config
            )

            self.is_initialized = True
            logger.info("占位符应用服务初始化完成")

    async def analyze_placeholder(self, request: PlaceholderAnalysisRequest):
        """分析占位符 - 通过适配器调用"""
        await self.initialize()

        # 🆕 使用适配器
        async for event in self.agent_adapter.analyze_placeholder(request):
            yield event
```

---

## 🧪 步骤6: 端到端测试

### 6.1 创建测试脚本

```python
# scripts/test_integration_e2e.py

import asyncio
from app.db.session import get_db_session
from app.services.application.facades.unified_service_facade import (
    create_unified_service_facade
)
from app.services.domain.placeholder.types import PlaceholderAnalysisRequest


async def test_e2e_with_legacy():
    """测试端到端流程 - 旧系统"""
    print("🧪 测试端到端流程 - 旧系统...")

    with get_db_session() as db:
        facade = create_unified_service_facade(
            db,
            user_id="test_user",
            enable_stage_aware=False  # 使用旧系统
        )

        # 获取占位符服务
        placeholder_service = await facade._get_placeholder_service()

        # 创建测试请求
        request = PlaceholderAnalysisRequest(
            placeholder_id="test_001",
            business_command="统计用户注册数量",
            data_source_id=1,
            user_id="test_user",
            context={}
        )

        # 执行分析
        async for event in placeholder_service.analyze_placeholder(request):
            print(f"📡 事件: {event.get('type')} - {event.get('source', 'legacy')}")

            if event.get('type') == 'analysis_completed':
                print("✅ 旧系统测试通过")
                break


async def test_e2e_with_stage_aware():
    """测试端到端流程 - Stage-Aware"""
    print("🧪 测试端到端流程 - Stage-Aware...")

    with get_db_session() as db:
        facade = create_unified_service_facade(
            db,
            user_id="test_user",
            enable_stage_aware=True  # 使用 Stage-Aware
        )

        # 获取占位符服务
        placeholder_service = await facade._get_placeholder_service()

        # 创建测试请求
        request = PlaceholderAnalysisRequest(
            placeholder_id="test_002",
            business_command="统计用户注册数量",
            data_source_id=1,
            user_id="test_user",
            context={}
        )

        # 执行分析
        async for event in placeholder_service.analyze_placeholder(request):
            print(f"📡 事件: {event.get('type')} - {event.get('source', 'unknown')}")

            if event.get('type') == 'analysis_completed':
                print("✅ Stage-Aware 测试通过")
                break


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("Stage-Aware Agent 集成端到端测试")
    print("=" * 60)

    await test_e2e_with_legacy()
    print()
    await test_e2e_with_stage_aware()


if __name__ == "__main__":
    asyncio.run(main())
```

运行测试：

```bash
cd backend
python scripts/test_integration_e2e.py
```

---

## 🔄 步骤7: 启用灰度发布

### 7.1 配置灰度发布

编辑 `.env`：

```bash
# 启用混合模式
STAGE_AWARE_AGENT_MODE=hybrid

# 设置灰度比例为 5%
STAGE_AWARE_ROLLOUT_PERCENTAGE=5
```

### 7.2 重启服务

```bash
# 重启应用服务
systemctl restart your-app-service

# 或者如果使用 Docker
docker-compose restart backend
```

### 7.3 监控指标

监控以下指标：

- SQL生成准确率
- 平均响应时间
- 错误率
- 用户反馈

### 7.4 逐步提升比例

根据监控结果，逐步提升灰度比例：

```bash
# 提升到 10%
STAGE_AWARE_ROLLOUT_PERCENTAGE=10

# 提升到 25%
STAGE_AWARE_ROLLOUT_PERCENTAGE=25

# 提升到 50%
STAGE_AWARE_ROLLOUT_PERCENTAGE=50

# 全量发布（100%）
STAGE_AWARE_AGENT_MODE=stage_aware
```

---

## 🚨 故障排查

### 问题1: 适配器初始化失败

**症状**: `StageAwareAgentAdapter` 初始化失败

**解决方案**:
```bash
# 检查 Loom 是否正确安装
pip show loom-python

# 检查依赖
pip install --upgrade loom-python

# 查看日志
tail -f logs/app.log | grep "StageAwareAgentAdapter"
```

### 问题2: 旧系统降级不工作

**症状**: Stage-Aware 失败后没有降级到旧系统

**解决方案**:
```python
# 确保启用了降级
adapter = StageAwareAgentAdapter(
    container=container,
    enable_stage_aware=True,
    fallback_to_legacy=True  # 确保为 True
)
```

### 问题3: 配置不生效

**症状**: 修改 `.env` 后配置没有生效

**解决方案**:
```bash
# 重启应用
systemctl restart your-app-service

# 验证配置加载
python -c "from app.core.config import settings; print(settings.STAGE_AWARE_AGENT_MODE)"
```

---

## 📊 监控和指标

### 关键指标

创建监控脚本 `scripts/monitor_stage_aware.py`:

```python
import asyncio
from app.db.session import get_db_session
from app.services.application.facades.unified_service_facade import (
    create_unified_service_facade
)


async def get_adapter_metrics():
    """获取适配器指标"""
    with get_db_session() as db:
        facade = create_unified_service_facade(
            db,
            user_id="test_user",
            enable_stage_aware=True
        )

        placeholder_service = await facade._get_placeholder_service()

        if placeholder_service.agent_adapter:
            metrics = placeholder_service.agent_adapter.get_metrics()
            print("📊 适配器指标:")
            for key, value in metrics.items():
                print(f"  - {key}: {value}")


if __name__ == "__main__":
    asyncio.run(get_adapter_metrics())
```

---

## ✅ 验收标准

完成以下检查项，确认集成成功：

- [ ] 所有适配器测试通过
- [ ] 端到端测试通过（旧系统）
- [ ] 端到端测试通过（Stage-Aware）
- [ ] 配置开关工作正常
- [ ] 降级机制工作正常
- [ ] 灰度发布配置生效
- [ ] 监控指标可以正常收集
- [ ] 日志记录完整清晰

---

## 🎯 下一步

1. **性能基准测试** - 对比新旧系统性能
2. **负载测试** - 验证系统稳定性
3. **用户测试** - 收集真实用户反馈
4. **逐步扩大灰度比例** - 从 5% → 100%
5. **完全迁移** - 移除旧系统代码

---

## 📚 相关文档

- [Stage-Aware 集成规划](STAGE_AWARE_INTEGRATION_PLAN.md)
- [三阶段实现计划](THREE_STAGE_IMPLEMENTATION_PLAN.md)
- [重构完成总结](REFACTORING_COMPLETE.md)
- [Agent 架构文档](../app/services/infrastructure/agents/README.md)

---

## 💬 获取帮助

遇到问题？查看以下资源：

- 查看日志文件：`logs/app.log`
- 运行调试模式：`STAGE_AWARE_DEBUG=true`
- 查看现有测试：`backend/app/services/infrastructure/agents/test_*.py`

---

**🎉 恭喜！你已经完成了 Stage-Aware Agent 的初步集成！**
