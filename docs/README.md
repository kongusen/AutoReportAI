# AutoReportAI 项目文档

欢迎来到 AutoReportAI 项目文档中心！本项目是一个基于 DAG (有向无环图) 架构的智能报告生成系统。

## 📚 文档导航

### 🏗️ 架构设计
- [DAG架构设计](./AGENTS_DAG_ARCHITECTURE.md) - 核心DAG架构说明
- [架构对比分析](./ARCHITECTURE_COMPARISON_ANALYSIS.md) - 新旧架构对比
- [占位符架构重设计](./PLACEHOLDER_ARCHITECTURE_REDESIGN.md) - 占位符系统设计
- [React智能代理设计](./REACT_AGENT_SYSTEM_DESIGN.md) - 智能代理系统设计

### 🔧 开发指南
- [API使用指南](./api-guide.md) - RESTful API接口文档
- [开发环境搭建](./development-setup.md) - 本地开发环境配置
- [部署指南](./deployment-guide.md) - 生产环境部署说明

### 📝 使用示例
- [代理输出控制示例](./AGENTS_OUTPUT_CONTROL_EXAMPLES.md) - DAG代理输出控制
- [任务周期配置示例](./TASK_PERIOD_CONFIG_EXAMPLES.md) - 任务时间配置

### 🧪 测试文档
- [测试指南](./testing-guide.md) - 单元测试和集成测试
- [性能测试](./performance-testing.md) - 系统性能评估

### 🔒 安全文档
- [安全策略](./security-policy.md) - 系统安全设计
- [权限管理](./permission-management.md) - 用户权限控制

## 🎯 项目概述

AutoReportAI 是一个智能报告生成系统，采用纯 DAG (Directed Acyclic Graph) 架构设计，提供：

- **智能占位符分析**：基于上下文的智能占位符解析和SQL生成
- **DAG代理编排**：灵活的任务编排和执行引擎
- **多数据源支持**：支持 Doris、MySQL、PostgreSQL 等多种数据源
- **实时图表生成**：支持柱状图、饼图、折线图等多种图表类型
- **模板管理**：Word 文档模板智能解析和处理
- **任务调度**：支持定时任务和事件驱动任务

## 🚀 快速开始

1. **环境要求**
   - Python 3.11+
   - Docker & Docker Compose
   - PostgreSQL 数据库
   - Redis 缓存

2. **启动开发环境**
   ```bash
   # 克隆项目
   git clone <repository-url>
   cd AutoReportAI
   
   # 启动后端服务
   cd backend
   pip install -r requirements.txt
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   
   # 启动前端服务
   cd frontend
   npm install
   npm run dev
   ```

3. **访问系统**
   - 后端API：http://localhost:8000
   - API文档：http://localhost:8000/docs
   - 前端界面：http://localhost:3000

## 🛠️ 核心组件

### DAG架构核心
- **IntelligentPlaceholderService**：智能占位符处理服务
- **ReactIntelligentAgent**：React模式智能代理
- **BackgroundController**：DAG编排控制器
- **ContextEngine**：上下文工程引擎

### 数据处理
- **DataSourceService**：多数据源连接管理
- **SchemaAnalysisService**：数据库模式分析
- **VisualizationService**：图表生成服务

### 模板系统
- **TemplateService**：模板管理服务
- **PlaceholderParser**：占位符解析器
- **ReportGenerator**：报告生成器

## 📋 项目状态

当前版本：v2.0.0  
架构状态：纯DAG架构 ✅  
主要功能：完整实现 ✅  
文档状态：持续更新 📝  

## 🤝 贡献指南

我们欢迎社区贡献！请参阅 [贡献指南](./contributing.md) 了解如何参与项目开发。

## 📄 许可证

本项目采用 MIT 许可证，详见 [LICENSE](../LICENSE) 文件。

## 📞 联系我们

如有问题或建议，请通过以下方式联系：

- 提交 GitHub Issue
- 发送邮件至 [your-email@domain.com]
- 加入我们的讨论群

---

*最后更新：2025-08-29*