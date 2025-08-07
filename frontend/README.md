# AutoReportAI Frontend

基于 Next.js 14 构建的智能报告生成平台前端应用。

## 技术栈

- **框架**: Next.js 14 + React 18 + TypeScript
- **样式**: Tailwind CSS + Headless UI
- **状态管理**: Zustand
- **HTTP客户端**: Axios
- **实时通信**: WebSocket
- **表单处理**: React Hook Form + Zod
- **图标**: Lucide React

## 设计理念

采用极简主义设计风格，黑白灰配色方案，注重用户体验和性能优化。

## 项目结构

```
src/
├── app/                 # Next.js App Router
│   ├── (auth)/         # 认证页面组
│   ├── dashboard/      # 仪表板
│   ├── data-sources/   # 数据源管理
│   ├── templates/      # 模板管理
│   ├── tasks/         # 任务管理
│   └── reports/       # 报告中心
├── components/        # 组件目录
│   ├── ui/           # 基础UI组件
│   ├── layout/       # 布局组件
│   ├── providers/    # Context提供者
│   └── forms/        # 表单组件
├── lib/              # 工具库
├── stores/           # 状态管理
├── services/         # API服务
├── types/            # TypeScript类型
├── hooks/            # 自定义hooks
└── utils/            # 工具函数
```

## 快速开始

1. **安装依赖**
   ```bash
   npm install
   ```

2. **环境配置**
   ```bash
   cp .env.example .env.local
   # 编辑 .env.local 配置后端API地址
   ```

3. **启动开发服务器**
   ```bash
   npm run dev
   ```

4. **构建生产版本**
   ```bash
   npm run build
   npm start
   ```

## 功能特性

### ✅ 已实现功能

- 🔐 用户认证（登录/注册/登出）
- 📊 仪表板概览
- 💾 数据源管理（支持 SQL、Doris、API、CSV、推送）
- 📄 模板管理和编辑
- ⏰ 任务调度和管理
- 📈 报告生成和查看
- 🔔 实时通知系统
- 🎨 极简UI组件库

### 🚀 核心特性

- **响应式设计**: 完美适配桌面端、平板和移动设备
- **实时通信**: WebSocket连接，实时任务进度和系统通知
- **类型安全**: 完整的TypeScript类型定义
- **状态管理**: 轻量级Zustand状态管理
- **错误处理**: 统一的错误处理和用户反馈
- **加载状态**: 优雅的加载动画和反馈

## 开发指南

### 代码规范

- 使用TypeScript进行类型检查
- 遵循ESLint配置的代码规范
- 组件采用函数式组件 + Hooks
- 使用Tailwind CSS进行样式开发

### 组件开发

- 基础UI组件位于 `components/ui/`
- 业务组件按功能模块组织
- 使用复合组件模式构建复杂UI

### 状态管理

- 认证状态：`useAuthStore`
- 业务数据：按模块拆分Store
- UI状态：本地状态优先

### API集成

- 统一的API客户端配置
- 自动token管理和刷新
- 统一的错误处理机制

## 部署说明

### 环境变量

```env
NEXT_PUBLIC_API_URL=https://api.autoreportai.com/api/v1
NEXT_PUBLIC_WS_URL=wss://api.autoreportai.com/ws
```

### Docker部署

```bash
docker build -t autoreportai-frontend .
docker run -p 3000:3000 autoreportai-frontend
```

### Vercel部署

直接连接Git仓库，自动部署。

## 许可证

MIT License