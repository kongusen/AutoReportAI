# 增强Agent系统

一个完整的企业级Agent系统，提供智能化的数据处理、分析、内容生成和可视化能力，具备知识共享和协作学习功能。

## 🌟 系统特色

- **4个专业增强Agent**: 数据查询、内容生成、分析、可视化
- **智能编排**: 自动任务分解和Agent协调
- **知识共享**: 跨Agent学习和最佳实践积累
- **用户个性化**: 自适应用户偏好和行为模式
- **企业级安全**: 多级沙盒和权限控制
- **高性能**: 异步处理和缓存优化

## 📁 系统架构

```
agents/
├── base/                      # 基础Agent框架
├── enhanced/                  # 增强Agent实现
│   ├── enhanced_data_query_agent.py      # 语义查询Agent
│   ├── enhanced_content_generation_agent.py # 上下文内容生成Agent  
│   ├── enhanced_analysis_agent.py        # 机器学习分析Agent
│   └── enhanced_visualization_agent.py   # 智能可视化Agent
├── orchestration/            # 智能编排系统
│   └── smart_orchestrator.py
├── knowledge/               # 知识共享系统
│   ├── knowledge_base.py
│   └── knowledge_integration.py
├── security/               # 安全沙盒系统
├── tools/                  # 通用工具框架
└── examples/              # 使用示例
```

## 🚀 快速开始

### 1. 基础使用

```python
from app.services.agents.enhanced import (
    EnhancedDataQueryAgent,
    EnhancedContentGenerationAgent, 
    EnhancedAnalysisAgent,
    EnhancedVisualizationAgent
)

# 创建增强Agents
data_agent = EnhancedDataQueryAgent()
content_agent = EnhancedContentGenerationAgent()
analysis_agent = EnhancedAnalysisAgent()
viz_agent = EnhancedVisualizationAgent()
```

### 2. 智能编排使用

```python
from app.services.agents.orchestration import SmartOrchestrator, OrchestrationRequest

# 创建智能编排器
orchestrator = SmartOrchestrator()

# 注册Agents
orchestrator.register_agent("data_query", data_agent)
orchestrator.register_agent("analysis", analysis_agent)

# 执行复杂任务
request = OrchestrationRequest(
    user_request="分析销售数据并生成报告",
    context={"data_source": "sales_db"},
    execution_mode=ExecutionMode.PIPELINE
)

result = await orchestrator.orchestrate_request(request)
```

### 3. 知识共享使用

```python
from app.services.agents.knowledge import KnowledgeShareManager

# 创建知识管理器
knowledge_manager = KnowledgeShareManager()

# 分享知识
await knowledge_manager.share_knowledge(
    agent_id="data_query_agent",
    knowledge_type="best_practice",
    content={"optimization": "使用索引提升查询性能"},
    confidence=0.9
)

# 获取推荐
recommendations = await knowledge_manager.get_recommendations(
    agent_id="analysis_agent",
    context={"task_type": "trend_analysis"}
)
```

## 🎯 核心功能

### 增强数据查询Agent

**语义理解和智能查询**

- 自然语言查询解析
- 智能字段映射和联想
- 查询优化和性能提升
- 元数据管理和模式推断

```python
from app.services.agents.enhanced import SemanticQueryRequest

request = SemanticQueryRequest(
    query="显示上个月销售额最高的前10个产品",
    data_source="product_sales",
    natural_language=True,
    semantic_enhancement=True
)

result = await data_agent.execute_semantic_query(request)
```

### 增强内容生成Agent

**上下文管理和风格控制**

- 多轮对话上下文保持
- 风格一致性和个性化
- 内容质量检查和优化
- 用户偏好学习

```python
from app.services.agents.enhanced import ContextualContentRequest

request = ContextualContentRequest(
    content_type="analysis_report", 
    data=analysis_results,
    conversation_id="session_123",
    style_requirements={"tone": "professional", "formality": "high"},
    quality_criteria={"min_score": 0.8}
)

result = await content_agent.execute_contextual(request, user_id="user_001")
```

### 增强分析Agent

**机器学习和高级分析**

- 预测建模和趋势分析
- 异常检测和模式挖掘
- 聚类分析和分类
- 自动特征工程

```python
from app.services.agents.enhanced import MLAnalysisRequest

request = MLAnalysisRequest(
    data=sales_data,
    analysis_type="comprehensive",
    target_variable="revenue",
    enable_feature_engineering=True,
    prediction_horizon=30
)

result = await analysis_agent.execute_ml_analysis(request)
```

### 增强可视化Agent

**智能推荐和自适应设计**

- 智能图表类型推荐
- 颜色和布局优化
- 数据故事化呈现
- 交互式设计建议

```python
from app.services.agents.enhanced import SmartVisualizationRequest

request = SmartVisualizationRequest(
    data=trend_data,
    chart_purpose="trend_analysis",
    target_audience="executives", 
    enable_smart_recommendations=True,
    enable_storytelling=True
)

result = await viz_agent.execute_smart_visualization(request)
```

## 🧠 智能编排系统

### 编排模式

**1. 顺序执行 (Sequential)**
```python
execution_mode = ExecutionMode.SEQUENTIAL
# Agent按顺序依次执行
```

**2. 并行执行 (Parallel)** 
```python
execution_mode = ExecutionMode.PARALLEL
# 多个Agent同时执行，适合独立任务
```

**3. 流水线执行 (Pipeline)**
```python
execution_mode = ExecutionMode.PIPELINE  
# Agent按依赖关系形成处理流水线
```

**4. 条件执行 (Conditional)**
```python
execution_mode = ExecutionMode.CONDITIONAL
# 基于条件动态选择执行路径
```

### 智能任务分解

```python
# 复杂用户请求自动分解
user_request = """
我需要分析客户流失情况：
1. 查询客户数据
2. 进行流失预测分析  
3. 生成分析报告
4. 创建可视化仪表板
"""

# 系统自动分解为4个子任务并编排执行
result = await orchestrator.orchestrate(user_request, context)
```

## 🔄 知识共享机制

### 知识类型

- **模式识别**: 用户行为和数据模式
- **最佳实践**: 优化的执行方案
- **性能洞察**: 提升性能的建议
- **协作模式**: Agent间协作优化

### 学习反馈循环

```python
# 1. 执行任务并收集数据
result = await agent.execute(request)

# 2. 记录执行结果和性能
await knowledge_manager.learn_from_interactions(user_id, [execution_data])

# 3. 生成洞察和推荐
insights = await knowledge_manager.generate_insights(agent_results)

# 4. 应用学习到的优化
recommendations = await knowledge_manager.get_recommendations(context)
```

### 跨Agent协作

```python
# 检测Agent间协作模式
collaboration_insights = await knowledge_manager.get_collaborative_insights([
    'data_query_agent',
    'analysis_agent', 
    'content_agent'
])

# 优化Agent参数
optimized_params = await knowledge_manager.optimize_agent_parameters(
    context, current_parameters
)
```

## 🔒 安全与性能

### 多级沙盒安全

```python
from app.services.agents.security import SandboxLevel

# 严格模式 - 受限的安全执行环境
sandbox_level = SandboxLevel.STRICT

# 标准模式 - 平衡安全性和功能性  
sandbox_level = SandboxLevel.STANDARD

# 宽松模式 - 更多权限但保持基本安全
sandbox_level = SandboxLevel.PERMISSIVE
```

### 性能优化特性

- **异步执行**: 所有Agent支持async/await
- **智能缓存**: 结果缓存和TTL管理
- **连接池**: 数据库连接复用
- **资源限制**: 内存和时间限制保护
- **监控指标**: 详细的性能监控

## 📊 监控和诊断

### 健康检查

```python
# Agent健康检查
health = await agent.health_check()
print(f"Agent状态: {health['healthy']}")
print(f"性能指标: {health['performance_metrics']}")

# 系统整体健康检查
system_health = await orchestrator.get_system_health()
```

### 统计信息

```python
# 知识库统计
stats = await knowledge_manager.get_knowledge_statistics()
print(f"总知识项: {stats['total_knowledge_items']}")
print(f"平均置信度: {stats['avg_confidence']}")

# Agent使用统计
usage_stats = await agent.get_usage_statistics()
```

## 🔧 配置和定制

### Agent配置

```python
from app.services.agents.base import AgentConfig, AgentType

config = AgentConfig(
    agent_id="custom_agent",
    agent_type=AgentType.ANALYSIS,
    name="Custom Analysis Agent",
    timeout_seconds=120,
    enable_caching=True,
    cache_ttl_seconds=1800
)

agent = EnhancedAnalysisAgent(config)
```

### 工具扩展

```python
from app.services.agents.tools import BaseTool, tool_registry

class CustomTool(BaseTool):
    async def execute(self, input_data, context=None):
        # 自定义工具逻辑
        return result

# 注册工具
tool_registry.register("custom_tool", CustomTool())
```

## 📈 最佳实践

### 1. Agent选择指南

- **数据查询**: 复杂查询、语义搜索、数据探索
- **内容生成**: 报告生成、多轮对话、个性化内容  
- **数据分析**: 机器学习、统计分析、模式挖掘
- **可视化**: 图表生成、仪表板、数据故事

### 2. 性能优化建议

- 使用合适的缓存策略
- 合理设置超时时间
- 启用并行执行when possible
- 监控资源使用情况

### 3. 安全最佳实践

- 选择合适的沙盒级别
- 验证输入数据
- 限制资源访问
- 定期安全审计

## 🐛 故障排除

### 常见问题

**1. Agent执行超时**
```python
# 增加超时时间
config.timeout_seconds = 300
```

**2. 内存不足**
```python
# 限制数据大小或增加内存限制
sandbox_config.memory_limit = 100  # MB
```

**3. 知识库性能问题**
```python
# 清理旧知识
await knowledge_manager.cleanup_old_knowledge(days_threshold=90)
```

### 调试模式

```python
# 启用详细日志
import logging
logging.getLogger("agents").setLevel(logging.DEBUG)

# 禁用缓存进行调试
config.enable_caching = False
```

## 🚀 部署指南

### 环境要求

```bash
# 安装依赖
pip install -r requirements.txt

# 需要的Python包
- asyncio
- pandas
- numpy  
- scikit-learn
- sqlite3
- jieba (中文分词)
```

### 数据库初始化

```python
from app.services.agents.knowledge import KnowledgeShareManager

# 自动创建知识库数据库
knowledge_manager = KnowledgeShareManager(db_path="production.db")
```

### 生产配置

```python
# 生产环境推荐配置
PRODUCTION_CONFIG = {
    "timeout_seconds": 60,
    "enable_caching": True, 
    "cache_ttl_seconds": 3600,
    "max_concurrent_agents": 10,
    "knowledge_cleanup_interval": 86400,  # 24小时
    "sandbox_level": SandboxLevel.STANDARD
}
```

## 🤝 贡献指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🎯 路线图

### 即将推出

- [ ] 图形化Agent编排界面
- [ ] 更多机器学习算法支持
- [ ] 实时数据流处理
- [ ] 多语言自然语言处理
- [ ] 云原生部署支持

### 长期规划

- [ ] 联邦学习支持
- [ ] 图数据库集成
- [ ] 自动化Agent优化
- [ ] 企业级权限管理
- [ ] 多租户支持

---

## 💬 支持

如有问题或建议，请提交Issue或联系开发团队。

**Happy Coding with Enhanced Agent System! 🎉**