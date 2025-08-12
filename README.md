<div align="center">
  <img src="https://raw.githubusercontent.com/user-attachments/assets/15ba393a-864a-4f1c-8af2-8b43834a3b04" width="150" alt="AutoReportAI Logo">
  <h1>AutoReportAI</h1>
  <p>
    <b>下一代 AI 驱动的智能报告生成系统</b>
  </p>
  <p>
    基于先进的 Agent 架构，AutoReportAI 将原始数据转换为专业的商业报告，提供端到端的智能化数据分析和报告生成解决方案。
  </p>

  <p>
    <a href="https://github.com/kongusen/AutoReportAI/stargazers"><img src="https://img.shields.io/github/stars/kongusen/AutoReportAI?style=flat-square" alt="GitHub stars"></a>
    <a href="https://github.com/kongusen/AutoReportAI/forks"><img src="https://img.shields.io/github/forks/kongusen/AutoReportAI?style=flat-square" alt="GitHub forks"></a>
    <a href="https://github.com/kongusen/AutoReportAI/issues"><img src="https://img.shields.io/github/issues/kongusen/AutoReportAI?style=flat-square" alt="GitHub issues"></a>
    <a href="./LICENSE"><img src="https://img.shields.io/github/license/kongusen/AutoReportAI?style=flat-square" alt="License"></a>
  </p>

  <p>
    <a href="https://github.com/kongusen/AutoReportAI/actions/workflows/ci-cd.yml"><img src="https://img.shields.io/github/actions/workflow/status/kongusen/AutoReportAI/ci-cd.yml?branch=main&label=CI%2FCD&style=flat-square" alt="CI/CD Pipeline"></a>
    <a href="https://github.com/kongusen/AutoReportAI/actions/workflows/quality.yml"><img src="https://img.shields.io/github/actions/workflow/status/kongusen/AutoReportAI/quality.yml?branch=main&label=Quality%20Gate&style=flat-square" alt="Quality Gate"></a>
    <a href="https://codecov.io/gh/kongusen/AutoReportAI"><img src="https://img.shields.io/codecov/c/github/kongusen/AutoReportAI?style=flat-square" alt="Code Coverage"></a>
  </p>

  <p>
    <a href="./README_EN.md">English</a> | <b>简体中文</b>
  </p>
</div>

---

## ✨ 核心特性

AutoReportAI 采用革命性的 **Agent 中心化架构**，将 AI 智能与企业级可靠性完美结合。

### 🤖 智能 Agent 系统
- **🎯 Agent 编排器**: 智能协调多个 Agent 完成复杂任务
- **📊 数据分析 Agent**: 高级统计分析、异常检测、预测分析
- **💡 内容生成 Agent**: AI 驱动的自然语言生成和商业洞察
- **🔍 数据查询 Agent**: 智能 SQL 生成和查询优化
- **📈 可视化 Agent**: 自动图表生成和数据可视化

### 🔄 完整的智能处理管道
- **模板分析**: 自动解析占位符和业务需求
- **数据源验证**: 连接测试和性能分析
- **智能 ETL**: AI 驱动的数据提取、转换、加载
- **深度分析**: 统计分析、趋势预测、异常检测
- **内容生成**: 从数据到自然语言的智能转换
- **报告组装**: 自动化的文档生成和质量保证

### 🎨 JSON 到自然语言转换
```python
# 输入冷冰冰的数据
json_data = [
    {"type": "VIP", "count": 150, "avg_spend": 8500, "contribution": 65.2}
]

# 输出温暖的商业语言
"根据本年度客户数据分析显示：VIP客户群体表现最为突出，共有150位客户，
人均消费8500元，贡献了65.2%的总收入..."
```

### 🚀 高级功能特性
- **🕒 智能任务调度**: 基于 Celery 的异步任务处理和实时监控
- **📊 多维度数据分析**: 描述性、诊断性、预测性分析
- **🔌 多 AI 提供商集成**: OpenAI、本地模型、自定义 AI 服务
- **👥 企业级用户管理**: RBAC 权限控制和审计跟踪
- **🌐 现代化 Web 界面**: Next.js + TypeScript 响应式设计
- **🔧 生产就绪部署**: Docker 容器化、CI/CD 流水线

## 🏛️ Agent 中心化架构

```mermaid
graph TD
    subgraph "用户界面层"
        A[Web Dashboard]
        B[API Gateway]
    end

    subgraph "Agent 编排层"
        C[智能管道编排器]
        D[任务状态管理]
        E[错误处理 & 重试]
    end

    subgraph "核心 Agent 系统"
        F[数据查询 Agent]
        G[分析 Agent] 
        H[内容生成 Agent]
        I[可视化 Agent]
        J[数据源 Agent]
    end

    subgraph "处理管道阶段"
        K[模板分析]
        L[占位符提取]
        M[数据验证]
        N[数据检索]
        O[深度分析]
        P[内容生成]
        Q[报告组装]
        R[质量保证]
    end

    subgraph "数据与存储层"
        S[(PostgreSQL)]
        T[(Redis Cache)]
        U[外部数据源]
        V[文件存储]
    end

    A --> B
    B --> C
    C --> D
    C --> E
    
    C --> F
    C --> G
    C --> H
    C --> I
    C --> J
    
    F --> K
    K --> L
    L --> M
    M --> N
    N --> O
    O --> P
    P --> Q
    Q --> R
    
    F --> S
    G --> T
    H --> S
    I --> V
    J --> U
```

### Agent 系统优势

#### 🎯 **并行处理能力**
- 多个 Agent 同时工作，显著提升处理效率
- 智能任务分解和依赖管理
- 资源优化和负载均衡

#### 🔄 **灵活的工作流**
- 标准模式: 平衡性能和资源使用
- 高性能模式: 大数据集快速处理  
- 内存优化模式: 流式处理和内存管理

#### 🛡️ **质量保证**
- 每个阶段都有内置验证
- 智能错误处理和恢复
- 详细的执行元数据追踪

## 🛠️ 技术栈

| 分类 | 技术 |
|------|------|
| **后端架构** | ![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?logo=python&style=flat-square) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg?logo=fastapi&style=flat-square) ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-orange.svg?style=flat-square) |
| **Agent 系统** | ![Celery](https://img.shields.io/badge/Celery-5.3+-green.svg?style=flat-square) ![Redis](https://img.shields.io/badge/Redis-7.0+-red.svg?logo=redis&style=flat-square) ![WebSocket](https://img.shields.io/badge/WebSocket-Real--time-blue.svg?style=flat-square) |
| **AI 集成** | ![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-blue.svg?logo=openai&style=flat-square) ![Local Models](https://img.shields.io/badge/Local_Models-Supported-green.svg?style=flat-square) ![Agents](https://img.shields.io/badge/Multi--Agent-System-purple.svg?style=flat-square) |
| **数据处理** | ![Pandas](https://img.shields.io/badge/Pandas-2.0+-green.svg?logo=pandas&style=flat-square) ![NumPy](https://img.shields.io/badge/NumPy-1.24+-blue.svg?logo=numpy&style=flat-square) ![Scikit](https://img.shields.io/badge/Scikit--Learn-1.3+-orange.svg?style=flat-square) |
| **前端界面** | ![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg?logo=next.js&style=flat-square) ![TypeScript](https://img.shields.io/badge/TypeScript-5+-blue.svg?logo=typescript&style=flat-square) ![Tailwind](https://img.shields.io/badge/Tailwind-3+-cyan.svg?logo=tailwind-css&style=flat-square) |
| **部署运维** | ![Docker](https://img.shields.io/badge/Docker-24+-blue.svg?logo=docker&style=flat-square) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg?logo=postgresql&style=flat-square) ![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-green.svg?style=flat-square) |

## 🚀 快速开始

### 1. 环境要求

- [Docker](https://www.docker.com/get-started/) & Docker Compose (v2.0+)
- [Python 3.11+](https://www.python.org/downloads/) 
- [Node.js 18+](https://nodejs.org/) & npm
- [Redis](https://redis.io/) (用于 Agent 协调)

### 2. 克隆和初始化

```bash
# 克隆项目
git clone https://github.com/kongusen/AutoReportAI.git
cd AutoReportAI

# 启动基础设施（数据库和 Redis）
docker-compose up -d

# 创建环境配置
cp backend/.env.example backend/.env
# 编辑 backend/.env 添加必要的配置
```

### 3. 后端 Agent 系统启动

```bash
cd backend

# 创建 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements/development.txt

# 初始化数据库和 Agent 系统
make dev-setup  # 一键设置所有组件

# 启动 API 服务器
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Agent 工作器启动

```bash
# 在新终端中启动 Celery Agent 工作器
cd backend
source venv/bin/activate

# 启动 Agent 编排器
celery -A app.core.worker worker --loglevel=info --concurrency=4

# 启动任务调度器
python scheduler/main.py
```

### 5. 前端界面启动

```bash
# 安装前端依赖
npm install --prefix frontend

# 启动开发服务器
npm run dev --prefix frontend
```

### 6. 访问应用

- **🌐 Web 应用**: `http://localhost:3000`
- **📚 API 文档**: `http://localhost:8000/docs`
- **🤖 Agent 监控**: `http://localhost:3000/admin/agents`

**默认管理员账号**:
- **邮箱**: `admin@example.com`
- **密码**: `password`

## 📊 Agent 系统详解

### 智能处理管道

#### 1. 标准处理流程
```python
# 创建智能处理上下文
from app.services.agents.core.intelligent_pipeline_orchestrator import PipelineContext

context = PipelineContext(
    template_id="your_template_id",
    data_source_id="your_datasource_id", 
    user_id="user_id",
    optimization_level="standard"  # standard | high_performance | memory_optimized
)

# 执行智能管道
result = await pipeline_orchestrator.execute(context)
```

#### 2. 高性能模式
```python
# 高性能处理配置
context = PipelineContext(
    template_id="template_id",
    data_source_id="datasource_id",
    optimization_level="high_performance",
    batch_size=5000,  # 小批次快速处理
    enable_caching=True
)
```

#### 3. 内存优化模式
```python
# 大数据集内存优化
context = PipelineContext(
    template_id="template_id", 
    data_source_id="datasource_id",
    optimization_level="memory_optimized",
    batch_size=1000,  # 极小批次
    custom_config={
        "streaming_mode": True,
        "memory_threshold": 0.8
    }
)
```

### Agent 类型和功能

#### 🔍 **增强数据源 Agent**
```python
from app.services.agents.enhanced.enhanced_data_source_agent import enhanced_data_source_agent

# 深度数据源分析
result = await enhanced_data_source_agent.execute({
    "data_source_id": "your_ds_id",
    "analysis_mode": "comprehensive",  # quick | standard | comprehensive | deep
    "target_tables": ["customers", "orders"]
})

# 获取分析结果
schema_info = result.data.schema_info
data_profiles = result.data.data_profiles  # 数据质量分析
query_optimizations = result.data.query_optimizations  # 查询优化建议
security_assessment = result.data.security_assessment  # 安全评估
```

#### 📊 **增强分析管道 Agent**
```python
from app.services.agents.enhanced.enhanced_analysis_pipeline import enhanced_analysis_pipeline

# 综合数据分析
result = await enhanced_analysis_pipeline.execute({
    "data": your_dataframe,
    "analysis_types": ["descriptive", "diagnostic", "predictive", "anomaly_detection"],
    "insight_level": "advanced"  # basic | intermediate | advanced | expert
})

# 获取分析结果
statistical_summary = result.data.statistical_summary
correlation_analysis = result.data.correlation_analysis
trend_analysis = result.data.trend_analysis
anomaly_detection = result.data.anomaly_detection
predictive_insights = result.data.predictive_insights
```

### JSON 到自然语言转换

#### 基础使用
```python
from app.services.agents.core.data_to_text_converter import DataToTextConverter

converter = DataToTextConverter()

# JSON 数据转自然语言
json_data = [
    {"type": "VIP", "count": 150, "avg_spend": 8500, "contribution": 65.2},
    {"type": "普通", "count": 1200, "avg_spend": 2300, "contribution": 28.5}
]

natural_text = await converter.convert_placeholder_result(
    placeholder="{{客户分析:统计各客户类型数量和消费}}",
    data=json_data,
    template_context={"report_date": "2024年3月"},
    style="business_report"  # business_report | casual | technical
)
```

#### 输出示例
**输入数据**: `[{"type": "VIP", "count": 150, "avg_spend": 8500}]`

**输出文本**: 
> "根据2024年3月客户数据分析显示：VIP客户群体表现突出，共有150位客户，人均消费8500元，展现出强劲的消费实力。数据表明VIP客户价值密度较高，建议继续深耕此类客户群体。"

## 🎯 应用场景

### 1. 智能日报生成
```python
# 每日自动生成销售报告
daily_pipeline = PipelineContext(
    template_id="daily_sales_template",
    data_source_id="sales_db",
    optimization_level="standard",
    custom_config={
        "report_type": "daily",
        "auto_insights": True
    }
)
```

### 2. 异常检测报告
```python
# 自动检测并报告数据异常
anomaly_analysis = await enhanced_analysis_pipeline.execute({
    "data": recent_data,
    "analysis_types": ["anomaly_detection"],
    "insight_level": "expert"
})
```

### 3. 客户分析洞察
```python
# 深度客户行为分析
customer_insights = await enhanced_analysis_pipeline.execute({
    "data": customer_data,
    "analysis_types": ["descriptive", "predictive", "exploratory"],
    "target_column": "customer_value"
})
```

## 📊 项目结构

```
AutoReportAI/
├── backend/                           # 后端服务
│   ├── app/
│   │   ├── services/
│   │   │   ├── agents/               # 🤖 核心 Agent 系统
│   │   │   │   ├── base.py          # Agent 基础框架
│   │   │   │   ├── orchestrator.py  # Agent 编排器
│   │   │   │   ├── core/            # 核心组件
│   │   │   │   │   ├── intelligent_pipeline_orchestrator.py
│   │   │   │   │   └── placeholder_processor.py
│   │   │   │   ├── enhanced/        # 增强 Agent
│   │   │   │   │   ├── enhanced_data_source_agent.py
│   │   │   │   │   ├── enhanced_analysis_pipeline.py
│   │   │   │   │   └── enhanced_content_generation_agent.py
│   │   │   │   └── examples/        # 使用示例
│   │   │   ├── data_processing/     # 数据处理服务
│   │   │   ├── ai_integration/      # AI 服务集成
│   │   │   └── report_generation/   # 报告生成
│   │   ├── api/                     # API 端点
│   │   ├── models/                  # 数据模型
│   │   └── core/                    # 核心配置
│   └── tests/                       # 测试套件
├── frontend/                        # 前端界面
├── scheduler/                       # 任务调度器
└── docs/                           # 文档
    ├── AGENTS_CENTERED_ARCHITECTURE.md
    ├── AI_REPORT_GENERATION_SYSTEM_DESIGN.md
    └── JSON_TO_NATURAL_TEXT_GUIDE.md
```

## 📈 性能优化

### Agent 并行处理
- **并发执行**: 多个 Agent 同时工作
- **智能调度**: 基于任务类型和资源的动态分配
- **缓存机制**: 智能缓存分析结果和查询数据

### 资源优化
- **批处理**: 大数据集分批处理
- **流式处理**: 内存优化的数据流处理
- **弹性扩展**: 支持水平扩展和负载均衡

### 质量保证
- **实时监控**: Agent 执行状态和性能监控
- **错误恢复**: 自动重试和降级机制
- **质量评分**: 每个处理阶段的质量评估

## 🧪 测试策略

我们采用多层次测试确保系统可靠性：

```bash
# Agent 系统测试
make test-agents           # Agent 功能测试
make test-pipeline        # 处理管道测试
make test-integration     # 集成测试

# 性能测试
make test-performance     # 性能基准测试
make test-load           # 负载测试

# 完整测试套件
make test-all            # 所有测试
make test-coverage       # 覆盖率报告
```

## 🚀 部署方案

### 开发环境
```bash
# 本地开发（推荐）
make dev-setup
make start-dev
```

### 生产环境
```bash
# Docker 容器化部署
docker-compose -f docker-compose.prod.yml up -d

# Kubernetes 部署
kubectl apply -f k8s/
```

### 扩展配置
```yaml
# docker-compose.prod.yml
services:
  agent-workers:
    image: autoreportai:latest
    deploy:
      replicas: 4  # 多个 Agent 工作器
    environment:
      - CELERY_WORKER_TYPE=agent
      - OPTIMIZATION_LEVEL=high_performance
```

## 📚 文档资源

- **[Agent 架构文档](AGENTS_CENTERED_ARCHITECTURE.md)**: 完整的 Agent 系统架构说明
- **[AI 报告生成设计](AI_REPORT_GENERATION_SYSTEM_DESIGN.md)**: 详细的系统设计文档  
- **[JSON 转自然语言指南](JSON_TO_NATURAL_TEXT_GUIDE.md)**: 数据到文本转换完整指南
- **[API 文档](http://localhost:8000/docs)**: 完整的 REST API 文档

## 🤝 贡献指南

我们欢迎社区贡献！

### 开发流程
1. Fork 项目并创建特性分支
2. 完成 Agent 系统本地设置
3. 为新功能编写测试（包括 Agent 测试）
4. 确保所有测试通过
5. 提交 Pull Request

### Agent 开发
```python
# 创建自定义 Agent
from app.services.agents.base import BaseAgent, AgentConfig, AgentResult

class CustomAgent(BaseAgent):
    async def execute(self, input_data, context=None):
        # 实现您的 Agent 逻辑
        return AgentResult(
            success=True,
            agent_id=self.agent_id,
            data=result_data
        )
```

## 🔮 路线图

### 即将发布 (v2.1)
- **🔄 实时处理**: 流式数据处理 Agent
- **🌐 云端 Agent**: 分布式 Agent 集群
- **📱 移动端**: 移动设备 Agent 监控

### 未来计划 (v2.2+)
- **🧠 自学习 Agent**: 基于历史数据的智能优化
- **🔗 Agent 市场**: 第三方 Agent 插件生态
- **🌍 多语言支持**: 国际化 Agent 系统

## 📄 开源协议

本项目基于 MIT 协议开源。详见 [LICENSE](./LICENSE) 文件。

---

<div align="center">
  <p><b>🤖 由 AI Agent 驱动，为智能化而生</b></p>
  <p>AutoReportAI - 让数据变成洞察，让洞察变成行动</p>
  <br>
  <p>
    <a href="https://github.com/kongusen/AutoReportAI">⭐ 给我们一个 Star</a> |
    <a href="https://github.com/kongusen/AutoReportAI/issues">🐛 报告问题</a> |
    <a href="https://github.com/kongusen/AutoReportAI/discussions">💬 参与讨论</a>
  </p>
</div>