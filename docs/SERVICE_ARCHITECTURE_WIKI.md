# AutoReportAI 服务架构开发者Wiki

## 📋 概述

AutoReportAI采用**领域驱动设计(DDD)**架构，以**React Agent**作为核心智能代理系统。本文档为开发者提供完整的服务架构说明、API接口指南和开发最佳实践。

---

## 🏗️ 整体架构

### 架构原则 - DDD v2.0

1. **领域驱动设计** - 严格按照DDD架构分层，清晰的职责边界
2. **用户中心化** - 所有服务都需要`user_id`参数进行个性化处理  
3. **智能代理集成** - Agent系统作为基础设施层技术服务
4. **业务流驱动** - 业务逻辑通过placeholder和tasks调用agents

### DDD v2.0 目录结构

```
backend/app/services/
├── application/           # 应用层 - 工作流编排与事务协调
│   ├── base_application_service.py  # 应用服务基类
│   ├── tasks/            # 任务应用服务
│   ├── templates/        # 模板应用服务  
│   ├── placeholders/     # 占位符应用服务
│   └── factories.py      # DDD工厂方法
├── domain/               # 领域层 - 纯业务逻辑
│   ├── placeholder/      # 占位符领域服务
│   │   └── services/     # 领域服务
│   ├── template/         # 模板领域服务
│   ├── tasks/           # 任务领域服务
│   │   └── services/     # 任务执行领域服务
│   └── base_domain_service.py  # 领域服务基类
├── infrastructure/       # 基础设施层 - 技术实现
│   ├── agents/          # Agent系统（技术服务）
│   │   ├── config/      # Agent配置
│   │   ├── core/        # 核心Agent组件
│   │   ├── llm_service.py  # LLM服务
│   │   └── main.py      # Agent主入口
│   ├── llm/             # LLM基础设施
│   ├── cache/           # 缓存系统
│   └── storage/         # 存储服务
└── data/                # 数据层 - 持久化管理
    ├── repositories/    # 数据访问仓库
    ├── models/          # 数据模型
    └── schemas/         # Schema服务
```

---

## 🎯 各层级详细说明

### 应用层 (Application Layer) - DDD v2.0

**职责**: 业务工作流编排，事务协调，领域服务组合

#### 核心应用服务

| 服务 | 文件路径 | 职责 | API模式 |
|------|----------|------|---------|
| **任务应用服务** | `application/tasks/task_application_service.py` | 任务执行工作流编排 | `async def analyze_task_with_domain_services()` |
| **基础应用服务** | `application/base_application_service.py` | 统一事务处理和事件发布 | `BaseApplicationService`, `TransactionalApplicationService` |
| **应用服务工厂** | `application/factories.py` | DDD架构下的服务创建 | 工厂方法模式 |

#### DDD v2.0 工厂模式

```python
# DDD v2.0 工厂方法 - 统一架构
from app.services.application.factories import (
    create_task_application_service,
    create_placeholder_domain_service,
    create_template_domain_service
)

# 使用示例 - 严格DDD分层
task_service = create_task_application_service(db, user_id="user123")
placeholder_domain = create_placeholder_domain_service(db, user_id="user123")
```

### 领域层 (Domain Layer)

**职责**: 实现核心业务逻辑和领域特定规则

#### 核心领域

##### 1. 占位符领域 (`domain/placeholder/`)

**核心服务**: `IntelligentPlaceholderService`

```python
# API接口
class IntelligentPlaceholderService:
    async def analyze_placeholder_with_dag(
        self, 
        placeholder_text: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]
    
    async def batch_process_placeholders(
        self,
        placeholders: List[Dict[str, Any]],
        processing_options: Dict[str, Any]
    ) -> Dict[str, Any]
```

**子服务**:
- `parsers/`: 语法解析器(JSON、SQL、表达式)
- `semantic/`: 语义分析服务
- `context/`: 上下文工程
- `weight/`: 权重管理  
- `cache/`: 占位符缓存
- `realtime/`: 实时通知

##### 2. 模板领域 (`domain/template/`)

**核心服务**: `TemplateDomainService` + `TemplateService`

```python
# API接口
class TemplateService:
    async def create_template(
        self,
        user_id: UUID,
        name: str,
        content: str,
        description: str = None,
        is_public: bool = False,
        auto_generate_placeholders: bool = True
    ) -> Tuple[Template, Dict[str, Any]]
    
    async def create_template_with_sql_generation(
        self,
        user_id: UUID,
        name: str,
        content: str,
        data_source_id: str = None
    ) -> Tuple[Template, Dict[str, Any]]
```

##### 3. 报告领域 (`domain/reporting/`)

**核心服务**: 
- `ReportGenerationDomainService`: 报告生成逻辑
- `WordGeneratorService`: Word文档生成  
- `QualityChecker`: 报告质量检查

##### 4. 数据源领域 (`domain/data_source/`)

**架构**: DDD实体模式
- `entities/`: 数据源实体(ConnectionEntity, DataSourceEntity)
- `services/`: 领域服务
- `value_objects/`: 值对象

### 基础设施层 (Infrastructure Layer)

**职责**: 提供技术基础设施和外部集成

#### AI服务 (`infrastructure/ai/`)

**React Agent系统**:

```python
# React Agent - 核心智能代理
from app.services.infrastructure.ai.agents import create_react_agent

agent = create_react_agent(user_id="user123")
await agent.initialize()
result = await agent.chat("分析销售数据")
```

**组件架构**:
- `agents/`: React Agent实现、DAG控制器、执行引擎
- `llm/`: LLM集成、智能选择器、客户端适配器  
- `tools/`: AI工具注册表、工厂模式、监控

**React Agent特性**:
- **用户个性化**: 基于用户偏好选择最佳模型
- **ReAct循环**: 实现思考→行动→观察推理模式
- **工具集成**: 丰富的工具生态系统
- **上下文管理**: 智能上下文缓存和传递

#### 缓存服务 (`infrastructure/cache/`)

**统一缓存管理器**:

```python
from app.services.infrastructure.cache import get_unified_cache_manager

cache = await get_unified_cache_manager()
await cache.set("key", data, ttl=3600)
result = await cache.get("key")
```

**缓存策略**:
- **内存缓存**: 高频访问数据  
- **Redis缓存**: 分布式共享缓存
- **上下文感知**: 智能缓存失效策略

### 数据层 (Data Layer)

**职责**: 数据访问和持久化管理

#### 连接器系统 (`data/connectors/`)

**支持的数据源**:
- **Doris**: 大数据OLAP连接器
- **SQL数据库**: PostgreSQL、MySQL等关系型数据库
- **API数据源**: RESTful API集成
- **CSV文件**: 文件数据处理

```python
# 连接器工厂使用
from app.services.data.connectors import create_connector

connector = create_connector(data_source_config)
await connector.connect()
result = await connector.execute_query(sql)
```

#### Schema服务 (`data/schemas/`)

**智能Schema分析**:

```python
# Schema分析服务
from app.services.data.schemas import create_schema_analysis_service

service = create_schema_analysis_service(db, user_id="user123")
analysis = await service.analyze_table_relationships(table_names)
```

---

## 🔌 API接口规范

### 统一API模式

所有服务遵循统一的API规范：

```python
# 标准服务接口
async def service_method(
    self,
    primary_params: Any,           # 主要业务参数
    user_id: str,                 # 必需: 用户ID
    context: Dict[str, Any] = None,  # 可选: 上下文信息
    options: Dict[str, Any] = None   # 可选: 处理选项
) -> Dict[str, Any]:               # 标准返回格式
    return {
        "success": bool,
        "data": Any,
        "message": str,
        "metadata": Dict[str, Any]
    }
```

### React Agent集成模式

所有需要智能处理的服务都可以集成React Agent：

```python
# React Agent集成标准模式
async def intelligent_service_method(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # 1. 创建用户专属Agent
        agent = create_react_agent(self.user_id)
        await agent.initialize()
        
        # 2. 构建智能提示
        prompt = f"执行{任务类型}: {task_data}"
        
        # 3. 执行并返回结果
        result = await agent.chat(prompt, context=task_data)
        
        return {
            "success": True,
            "data": result,
            "agent_used": True
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "agent_used": False
        }
```

---

## 🛠️ 开发指南

### 1. 创建新服务

#### Step 1: 确定服务层级

```python
# 应用层服务 - 工作流编排
class MyWorkflowService:
    def __init__(self, user_id: str):
        self.user_id = user_id

# 领域层服务 - 业务逻辑
class MyDomainService:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

# 基础设施层服务 - 技术实现
class MyInfrastructureService:
    def __init__(self):
        pass
```

#### Step 2: 集成React Agent (如需要)

```python
class IntelligentService:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._agent = None
    
    async def _get_agent(self):
        if self._agent is None:
            self._agent = create_react_agent(self.user_id)
            await self._agent.initialize()
        return self._agent
    
    async def process_intelligently(self, data):
        agent = await self._get_agent()
        return await agent.chat(f"处理数据: {data}")
```

#### Step 3: 添加工厂方法

```python
# 在对应的工厂文件中添加
def create_my_service(user_id: str, db: Session = None):
    if not user_id:
        raise ValueError("user_id is required")
    return MyService(user_id, db)
```

### 2. 使用现有服务

#### 获取服务实例

```python
# 通过工厂获取
from app.services.application.factories import create_react_agent
agent = create_react_agent("user123")

# 通过统一门面获取
from app.services.application.facades import get_unified_service_facade
facade = await get_unified_service_facade(db, "user123")
```

#### 标准调用模式

```python
async def use_service_example():
    try:
        # 1. 获取服务
        service = create_some_service(user_id="user123", db=db)
        
        # 2. 调用服务方法
        result = await service.process_data(
            data=input_data,
            context={"task_type": "analysis"},
            options={"optimization": True}
        )
        
        # 3. 处理结果
        if result["success"]:
            return result["data"]
        else:
            handle_error(result["error"])
            
    except Exception as e:
        logger.error(f"Service call failed: {e}")
        raise
```

### 3. React Agent开发模式

#### 基础Agent使用

```python
# 创建用户专属Agent
agent = create_react_agent(user_id="user123")
await agent.initialize()

# 简单对话
result = await agent.chat("帮我分析数据")

# 复杂任务with上下文
result = await agent.chat(
    "生成SQL查询",
    context={
        "template_id": "template123",
        "data_source": "doris_cluster",
        "requirements": ["性能优化", "数据完整性"]
    }
)
```

#### 自定义Agent工具

```python
# 为Agent添加自定义工具
from app.services.infrastructure.ai.tools import AIToolsFactory

tools_factory = AIToolsFactory()
custom_tool = tools_factory.create_custom_tool(
    name="my_data_processor",
    description="处理特定格式数据",
    function=my_processing_function
)

agent = create_react_agent(user_id, tools=[custom_tool])
```

---

## 📊 服务API参考

### 应用层API

#### 工作流编排代理
```python
from app.services.application.agents import get_workflow_orchestration_agent

agent = await get_workflow_orchestration_agent()

# 编排报告生成工作流
result = await agent.orchestrate_report_generation(
    template_id="tmpl_123",
    data_source_ids=["ds_1", "ds_2"],
    execution_context={
        "user_id": "user123",
        "optimization_level": "high"
    }
)
```

#### 统一服务门面
```python
from app.services.application.facades import get_unified_service_facade

facade = await get_unified_service_facade(db, user_id="user123")

# 完整的模板处理流程
result = await facade.process_template_with_full_pipeline(
    template_id="tmpl_123",
    data_source_id="ds_1",
    options={
        "generate_sql": True,
        "cache_results": True,
        "notification": True
    }
)
```

### 领域层API

#### 占位符服务
```python
from app.services.domain.placeholder import get_intelligent_placeholder_service

service = await get_intelligent_placeholder_service(user_id="user123")

# DAG-based占位符分析
result = await service.analyze_placeholder_with_dag(
    placeholder_text="{{sales_total}}",
    context={
        "template_id": "tmpl_123",
        "data_source_id": "ds_1"
    }
)

# 批量处理占位符
batch_result = await service.batch_process_placeholders(
    placeholders=[...],
    processing_options={
        "parallel_execution": True,
        "error_handling": "continue"
    }
)
```

#### 模板服务
```python
from app.services.domain.template.template_service import TemplateService

service = TemplateService(db, user_id="user123")

# 创建带自动SQL生成的模板
template, analysis = await service.create_template_with_sql_generation(
    user_id=user_id,
    name="销售报告模板",
    content="模板内容...",
    data_source_id="ds_1"
)
```

### 基础设施层API

#### React Agent系统
```python
from app.services.infrastructure.ai.agents import create_react_agent

# 创建用户专属Agent
agent = create_react_agent(user_id="user123")
await agent.initialize()

# 智能对话
result = await agent.chat("分析Q3销售数据趋势")

# 带工具的复杂任务
result = await agent.chat_with_tools(
    "生成数据可视化图表",
    tools=["chart_generator", "data_analyzer"]
)
```

#### LLM智能选择器
```python
from app.services.infrastructure.ai.llm import get_llm_manager

manager = await get_llm_manager()

# 为用户选择最佳模型
best_model = await manager.select_best_model_for_user(
    user_id="user123",
    task_type="reasoning",
    complexity="high",
    constraints={"max_cost": 0.05}
)
```

### 数据层API

#### 连接器系统
```python
from app.services.data.connectors import create_connector

# 创建数据源连接
connector = create_connector(data_source_config)
await connector.connect()

# 执行查询
result = await connector.execute_query("SELECT * FROM sales")
await connector.disconnect()
```

#### Schema分析
```python
from app.services.data.schemas import create_schema_analysis_service

service = create_schema_analysis_service(db, user_id="user123")

# 分析表关系
relationships = await service.analyze_table_relationships(
    table_names=["orders", "customers", "products"]
)

# 业务语义分析  
semantics = await service.analyze_business_semantics(
    table_name="orders",
    context={"business_domain": "ecommerce"}
)
```

---

## ⚙️ 配置和部署

### 环境配置

```bash
# 数据库配置
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Redis缓存
REDIS_URL=redis://localhost:6379/0

# AI模型配置
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker部署

```dockerfile
# 使用提供的多阶段Dockerfile
docker build -t autoreport-backend .

# 开发环境
docker build --target development -t autoreport-dev .

# 生产环境  
docker build --target production -t autoreport-prod .

# Celery Worker
docker build --target worker -t autoreport-worker .
```

---

## 🔍 调试和监控

### 服务健康检查

```python
# AI服务状态
from app.services.infrastructure.ai import get_ai_service_status
status = await get_ai_service_status()

# 整体服务状态  
from app.services import get_service_system_health
health = await get_service_system_health()
```

### 日志模式

```python
import logging

logger = logging.getLogger(__name__)

# 标准日志格式
logger.info(f"Service started for user {user_id}")
logger.error(f"Service failed: {error}", extra={"user_id": user_id})
```

### 性能监控

- 所有服务都集成了性能指标收集
- React Agent执行时间和成本跟踪
- 缓存命中率和效率监控
- 数据库查询性能分析

---

## 🚀 最佳实践

### 1. 服务设计原则

- **用户中心**: 所有服务都需要`user_id`参数
- **异步优先**: 使用`async/await`模式
- **错误处理**: 统一的错误返回格式
- **幂等性**: 确保服务调用的幂等性
- **缓存友好**: 合理使用缓存提升性能

### 2. React Agent使用原则

- **一用户一实例**: 每个用户创建独立的Agent实例
- **懒加载**: Agent按需初始化，避免资源浪费  
- **上下文传递**: 充分利用上下文提升Agent决策质量
- **成本控制**: 监控和控制AI调用成本

### 3. 依赖管理

- **层级依赖**: 严格遵循DDD层级依赖方向
- **循环依赖**: 使用懒加载和工厂模式避免循环依赖
- **接口隔离**: 通过接口抽象隔离具体实现

### 4. 测试策略

```python
# 单元测试
pytest tests/unit/services/

# 集成测试
pytest tests/integration/services/

# React Agent测试
pytest tests/ai/test_react_agent.py
```

---

## 📚 扩展开发

### 添加新的领域服务

1. 在`domain/`下创建新领域目录
2. 实现领域服务和实体
3. 添加到`domain/__init__.py`
4. 在`application/factories.py`中添加工厂方法

### 集成新的AI工具

1. 在`infrastructure/ai/tools/`下创建工具
2. 注册到`AIToolsRegistry`
3. 通过`AIToolsFactory`提供给React Agent

### 添加新的数据连接器

1. 在`data/connectors/`下实现连接器
2. 继承`BaseConnector`接口
3. 在`ConnectorFactory`中注册新类型

---

## 🆘 故障排除

### 常见问题

1. **user_id缺失**: 确保所有服务调用都传递了有效的`user_id`
2. **React Agent初始化失败**: 检查用户的LLM配置和API密钥
3. **循环导入**: 使用懒加载和`if TYPE_CHECKING`模式
4. **缓存问题**: 检查Redis连接和缓存键冲突

### 调试工具

```python
# 启用详细日志
import logging
logging.getLogger("app.services").setLevel(logging.DEBUG)

# React Agent调试模式
agent = create_react_agent(user_id, verbose=True)

# 服务状态检查
status = await get_ai_service_status()
print(f"Service health: {status['health_score']}")
```

---

## 📝 版本信息

- **架构版本**: DDD 2.0 with React Agent Integration  
- **React Agent版本**: v1.0 (纯数据库驱动)
- **API版本**: v1.0 (统一规范)
- **支持的Python版本**: 3.11+

---

## 🤝 贡献指南

1. **代码规范**: 遵循DDD架构模式和层级职责
2. **测试要求**: 新服务必须包含单元测试和集成测试
3. **文档要求**: 更新相关的API文档和Wiki
4. **React Agent集成**: 新的智能功能应该集成React Agent
5. **用户中心**: 所有新服务都应该支持用户个性化

此Wiki将随着系统演进持续更新。如有疑问请参考代码示例或联系架构团队。