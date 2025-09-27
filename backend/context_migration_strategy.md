# Context系统迁移策略

## 🎯 迁移目标

将Agent层的context功能迁移到Domain层，实现：
1. **业务逻辑归Domain层管理** - context分析、业务规则、上下文融合
2. **技术能力归Infrastructure层** - 提示词生成、工具调用、执行控制
3. **清晰的接口边界** - Domain层提供标准化的Context接口给Infrastructure层使用

## 📋 需要迁移的组件

### 从 Infrastructure/agents 迁移到 Domain/placeholder/context

```
# 需要迁移的文件和功能：

FROM: /services/infrastructure/agents/context_prompt_controller.py
  - 上下文构建逻辑 → Domain层的BusinessContext
  - Schema信息处理 → Domain层的DataSourceContextService
  - 任务时间处理 → Domain层的TaskContextService

FROM: /services/infrastructure/agents/types.py (部分)
  - TaskContext → Domain层的TaskContext模型
  - SchemaInfo → Domain层的DataSourceContext模型

KEEP IN: /services/infrastructure/agents/
  - 提示词模板生成 (纯技术功能)
  - Agent工具调用接口
  - 执行控制逻辑
```

## 🏗️ 新架构设计

### Domain层Context体系

```
domain/placeholder/context/
├── business_context_service.py       # 业务上下文服务(新)
├── template_context_service.py       # 模板上下文服务(新)
├── data_source_context_service.py    # 数据源上下文服务(新)
├── task_context_service.py          # 任务上下文服务(新)
├── context_coordinator.py           # 上下文协调器(新)
├── context_analysis_engine.py       # 分析引擎(保持)
├── document_analyzer.py             # 文档分析器(保持)
├── paragraph_analyzer.py            # 段落分析器(保持)
├── section_analyzer.py              # 章节分析器(保持)
└── business_rule_analyzer.py        # 业务规则分析器(保持)
```

### Infrastructure层简化后的Context

```
infrastructure/agents/
├── prompt_template_service.py       # 提示词模板服务(新)
├── agent_context_adapter.py         # Agent上下文适配器(新)
└── execution_context.py            # 执行上下文(新,纯技术)
```

## 🔄 迁移实施步骤

### 第1步: 创建Domain层Context服务接口

```python
# domain/placeholder/context/business_context_service.py

class BusinessContextService:
    \"\"\"业务上下文服务 - 统一管理三大上下文\"\"\"

    def __init__(self):
        self.template_service = TemplateContextService()
        self.data_source_service = DataSourceContextService()
        self.task_service = TaskContextService()

    async def build_context(
        self,
        template_id: str,
        data_source_id: str,
        task_info: Dict[str, Any]
    ) -> BusinessContext:
        \"\"\"构建完整业务上下文\"\"\"

        template_ctx = await self.template_service.get_context(template_id)
        data_source_ctx = await self.data_source_service.get_context(data_source_id)
        task_ctx = await self.task_service.get_context(task_info)

        return BusinessContext(
            template_context=template_ctx,
            data_source_context=data_source_ctx,
            task_context=task_ctx
        )

    async def analyze_context_for_placeholder(
        self,
        placeholder_name: str,
        placeholder_text: str,
        context: BusinessContext
    ) -> ContextAnalysisResult:
        \"\"\"为占位符分析上下文\"\"\"

        # 使用现有的context_analysis_engine
        engine = ContextAnalysisEngine()
        return await engine.analyze_placeholder_context(
            placeholder_name, placeholder_text, context
        )
```

### 第2步: 重构Infrastructure层Agent系统

```python
# infrastructure/agents/agent_context_adapter.py

class AgentContextAdapter:
    \"\"\"Agent上下文适配器 - 连接Domain层和Agent系统\"\"\"

    def __init__(self, business_context_service):
        self.business_context_service = business_context_service
        self.prompt_service = PromptTemplateService()

    async def prepare_agent_input(
        self,
        placeholder_name: str,
        placeholder_text: str,
        business_context: BusinessContext,
        stage: ProcessingStage
    ) -> AgentInput:
        \"\"\"将Domain层上下文转换为Agent输入\"\"\"

        # 从Domain层获取分析结果
        analysis_result = await self.business_context_service.analyze_context_for_placeholder(
            placeholder_name, placeholder_text, business_context
        )

        # 转换为Agent系统理解的格式
        agent_input = AgentInput(
            user_prompt=self._build_user_prompt(analysis_result, stage),
            placeholder=self._build_placeholder_spec(analysis_result),
            schema=self._build_schema_info(business_context.data_source_context),
            context=self._build_task_context(business_context.task_context),
            constraints=self._build_constraints(analysis_result, stage)
        )

        return agent_input

    def _build_user_prompt(self, analysis_result, stage) -> str:
        \"\"\"构建用户提示词 - 纯技术功能\"\"\"
        return self.prompt_service.generate_prompt(analysis_result, stage)
```

### 第3步: 重构现有API调用

```python
# 新的调用方式示例

class PlaceholderDomainService:
    def __init__(self, agent_facade):
        self.business_context_service = BusinessContextService()
        self.agent_facade = agent_facade
        self.agent_adapter = AgentContextAdapter(self.business_context_service)

    async def analyze_placeholder(self, request) -> PlaceholderAnalysisResult:
        # 1. Domain层构建业务上下文
        business_context = await self.business_context_service.build_context(
            request.template_id,
            request.data_source_id,
            request.task_info
        )

        # 2. Domain层分析业务需求
        context_analysis = await self.business_context_service.analyze_context_for_placeholder(
            request.placeholder_name,
            request.placeholder_text,
            business_context
        )

        # 3. 通过适配器转换为Agent输入
        agent_input = await self.agent_adapter.prepare_agent_input(
            request.placeholder_name,
            request.placeholder_text,
            business_context,
            ProcessingStage.TEMPLATE_ANALYSIS
        )

        # 4. Infrastructure层执行技术操作
        agent_result = await self.agent_facade.execute(agent_input)

        # 5. Domain层处理业务结果
        return self._process_business_result(agent_result, context_analysis)
```

## 🔧 迁移检查清单

### 迁移前准备
- [ ] 分析现有Agent context的具体功能
- [ ] 识别哪些是业务逻辑，哪些是技术实现
- [ ] 确保Domain层context体系能承接所有业务功能
- [ ] 设计清晰的接口边界

### 迁移实施
- [ ] 创建Domain层Context服务
- [ ] 实现Agent上下文适配器
- [ ] 重构API层调用方式
- [ ] 更新所有相关的依赖注入

### 迁移后验证
- [ ] 单元测试覆盖所有新组件
- [ ] 集成测试验证端到端流程
- [ ] 性能测试确保没有回归
- [ ] 清理废弃的Agent context代码

## 🎯 迁移后的优势

### 1. 清晰的职责分离
- **Domain层**: 专注业务上下文分析、业务规则、上下文融合
- **Infrastructure层**: 专注技术实现、工具调用、提示词生成

### 2. 更好的可测试性
- Domain层业务逻辑可以独立测试
- Infrastructure层技术功能可以Mock Domain层

### 3. 更强的可扩展性
- 新增业务上下文类型无需修改Agent系统
- Agent工具可以独立演进

### 4. 更高的复用性
- Domain层上下文服务可以被多个Infrastructure组件使用
- Infrastructure层Agent系统可以支持多种业务场景

## ⚠️ 迁移风险和应对

### 风险点
1. **接口变更影响**: 现有API调用需要重构
2. **性能影响**: 多层调用可能影响性能
3. **数据一致性**: 上下文数据在两层间传递的一致性

### 应对措施
1. **渐进式迁移**: 先并行运行新旧系统，逐步切换
2. **性能监控**: 密切监控迁移前后的性能指标
3. **数据校验**: 增加上下文数据的校验机制

## 📅 迁移时间表

- **第1周**: 设计新架构接口，创建Domain层Context服务
- **第2周**: 实现Agent适配器，重构核心调用链路
- **第3周**: 更新所有API，进行集成测试
- **第4周**: 性能优化，清理废弃代码，上线验证