# AutoReportAI MCP Server

基于AutoReportAI后端API的MCP工具服务器，提供完整的AI报告生成能力。

## 🎯 当前服务状态

✅ **后端服务**: http://localhost:8000 (运行中)  
✅ **MCP stdio服务**: 可用  
✅ **MCP SSE服务**: http://localhost:8001 (运行中)

## 功能特性

### 🔐 认证管理
- 多用户登录支持
- Session-based认证
- 自动token刷新
- 权限验证

### 📊 数据源管理
- SQL数据库连接 (PostgreSQL, MySQL, SQLite)
- CSV/Excel文件上传
- API数据源配置
- 连接测试和验证

### 📝 模板管理
- 文本模板创建和编辑
- 文件模板上传 (Word, Excel, HTML, PDF)
- 模板变量和占位符
- 模板预览功能

### ⚡ 任务管理
- 定时任务配置 (Cron表达式)
- 手动任务执行
- 任务状态监控
- 失败重试机制

### 📈 报告生成
- 即时报告生成
- 批量报告处理
- 报告历史查看
- 多格式输出支持

### 🤖 AI提供商配置
- OpenAI/GPT配置
- Claude配置
- 本地模型支持
- API密钥管理

### ⚙️ 系统设置
- 用户偏好配置
- 系统参数设置
- 邮件服务配置
- 存储配置

### 👥 用户管理
- 用户创建和管理
- 角色权限控制
- 用户资源隔离

## 项目结构

```
mcp-server/
├── main.py                    # MCP服务器主入口
├── requirements.txt           # Python依赖
├── config.py                  # 配置管理
├── auth.py                   # 认证管理器
├── client.py                 # API客户端基类
├── session.py                # 会话管理
├── tools/                    # MCP工具模块
│   ├── __init__.py
│   ├── auth_tools.py         # 认证相关工具
│   ├── data_source_tools.py  # 数据源管理工具
│   ├── template_tools.py     # 模板管理工具
│   ├── task_tools.py         # 任务管理工具
│   ├── report_tools.py       # 报告生成工具
│   ├── ai_provider_tools.py  # AI提供商配置工具
│   ├── settings_tools.py     # 系统设置工具
│   ├── user_tools.py         # 用户管理工具
│   └── workflow_tools.py     # 工作流组合工具
├── utils/                    # 工具函数
│   ├── __init__.py
│   ├── helpers.py           # 辅助函数
│   ├── validators.py        # 数据验证
│   └── formatters.py        # 数据格式化
└── tests/                   # 测试文件
    ├── __init__.py
    └── test_tools.py
```

## 📋 LLM侧配置方案

### 方案一：stdio模式 (推荐)

**优点**: 
- ✅ 稳定可靠
- ✅ 低延迟 
- ✅ 标准MCP协议
- ✅ 适合本地开发

**配置方法**:
1. 将以下配置添加到你的MCP客户端配置文件中：

```json
{
  "mcpServers": {
    "autoreport": {
      "command": "python",
      "args": ["/Users/shan/work/uploads/AutoReportAI/mcp-server/main.py"],
      "cwd": "/Users/shan/work/uploads/AutoReportAI/mcp-server",
      "env": {
        "PYTHONPATH": "/Users/shan/work/uploads/AutoReportAI/mcp-server",
        "BACKEND_BASE_URL": "http://localhost:8000/api/v1",
        "DEFAULT_ADMIN_USERNAME": "admin",
        "DEFAULT_ADMIN_PASSWORD": "password"
      }
    }
  }
}
```

**启动方式**:
```bash
# 确保后端服务运行
cd /Users/shan/work/uploads/AutoReportAI/backend
source venv/bin/activate
PYTHONPATH=$PWD uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# MCP会自动启动，无需手动启动
```

### 方案二：SSE模式

**优点**:
- ✅ 支持网络访问
- ✅ 可以远程部署
- ✅ HTTP/REST接口
- ✅ 易于调试

**配置方法**:
1. 如果你的LLM支持SSE传输，使用以下配置：

```json
{
  "mcpServers": {
    "autoreport-sse": {
      "url": "http://localhost:8001",
      "transport": "sse"
    }
  }
}
```

2. 如果不支持SSE，可以直接使用HTTP API：

```bash
# 调用工具示例
curl -X POST http://localhost:8001/tools/mcp_login \
  -H "Content-Type: application/json" \
  -d '{"arguments": {}}'

# 获取数据源列表
curl -X POST http://localhost:8001/tools/mcp_list_data_sources \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"limit": 10}}'
```

**启动方式**:
```bash
# 启动后端服务
cd /Users/shan/work/uploads/AutoReportAI/backend
source venv/bin/activate 
PYTHONPATH=$PWD uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# 启动SSE服务器
cd /Users/shan/work/uploads/AutoReportAI/mcp-server
source venv/bin/activate
python sse_server.py &
```

### 方案三：Claude Desktop

**适用于**: Claude Desktop应用

**配置文件位置**:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`

**配置内容**:
```json
{
  "mcpServers": {
    "autoreport": {
      "command": "/Users/shan/work/uploads/AutoReportAI/mcp-server/venv/bin/python",
      "args": ["/Users/shan/work/uploads/AutoReportAI/mcp-server/main.py"],
      "cwd": "/Users/shan/work/uploads/AutoReportAI/mcp-server",
      "env": {
        "BACKEND_BASE_URL": "http://localhost:8000/api/v1",
        "DEFAULT_ADMIN_USERNAME": "admin", 
        "DEFAULT_ADMIN_PASSWORD": "password"
      }
    }
  }
}
```

## 安装和运行

### 环境要求
- Python 3.8+
- FastMCP库
- httpx库

### 安装依赖
```bash
cd mcp-server
pip install -r requirements.txt
```

### 环境变量配置
```bash
# 后端API配置
export BACKEND_BASE_URL="http://localhost:8000/api/v1"

# 默认管理员账户
export DEFAULT_ADMIN_USERNAME="admin"
export DEFAULT_ADMIN_PASSWORD="password"

# MCP服务器配置
export MCP_SERVER_HOST="localhost"
export MCP_SERVER_PORT="8001"
```

### 运行服务器
```bash
# 方式1: 使用启动器（推荐）
python run.py

# 方式2: 直接启动
python main.py
```

### 运行测试
```bash
python test_mcp.py
```

## 实现状态

### ✅ 已实现
- 认证管理: 完整实现，包括登录、登出、用户信息获取
- 数据源管理: 完整实现，支持SQL、API、CSV数据源
- 会话管理: 自动会话管理和清理
- 错误处理: 完整的错误处理和响应格式化
- 配置管理: 环境变量配置和验证
- 测试套件: 完整的功能测试

### ⏳ 待实现
- 模板管理工具 (template_tools.py)
- 任务管理工具 (task_tools.py)  
- 报告生成工具 (report_tools.py)
- AI提供商配置工具 (ai_provider_tools.py)
- 系统设置工具 (settings_tools.py)
- 用户管理工具 (user_tools.py)
- 工作流组合工具 (workflow_tools.py)

## 🛠 可用工具说明

配置完成后，LLM将可以使用以下42个工具：

### 认证类 (7个)
- `mcp_login` - 用户登录
- `mcp_logout` - 用户登出  
- `mcp_get_current_user` - 获取当前用户
- `mcp_switch_user` - 切换用户
- `mcp_list_sessions` - 列出会话
- `mcp_refresh_session` - 刷新会话
- `mcp_get_session_status` - 会话状态

### 数据源类 (9个)
- `mcp_list_data_sources` - 列出数据源
- `mcp_create_sql_data_source` - 创建SQL数据源
- `mcp_create_api_data_source` - 创建API数据源
- `mcp_upload_csv_data_source` - 上传CSV数据源
- `mcp_test_data_source` - 测试数据源
- `mcp_sync_data_source` - 同步数据源
- `mcp_get_data_source_preview` - 预览数据源
- `mcp_update_data_source` - 更新数据源
- `mcp_delete_data_source` - 删除数据源

### 模板类 (8个)
- `mcp_list_templates` - 列出模板
- `mcp_create_text_template` - 创建文本模板
- `mcp_upload_template_file` - 上传模板文件
- `mcp_get_template` - 获取模板
- `mcp_update_template` - 更新模板
- `mcp_delete_template` - 删除模板
- `mcp_duplicate_template` - 复制模板
- `mcp_preview_template` - 预览模板

### 任务类 (10个)
- `mcp_list_tasks` - 列出任务
- `mcp_create_task` - 创建任务
- `mcp_get_task` - 获取任务
- `mcp_update_task` - 更新任务
- `mcp_run_task` - 运行任务
- `mcp_enable_task` - 启用任务
- `mcp_disable_task` - 禁用任务
- `mcp_delete_task` - 删除任务
- `mcp_get_task_logs` - 获取任务日志
- `mcp_get_task_status` - 获取任务状态

### 报告类 (8个)
- `mcp_generate_report` - 生成报告
- `mcp_list_reports` - 列出报告
- `mcp_get_report` - 获取报告
- `mcp_download_report` - 下载报告
- `mcp_regenerate_report` - 重新生成报告
- `mcp_delete_report` - 删除报告
- `mcp_get_report_content` - 获取报告内容
- `mcp_batch_generate_reports` - 批量生成报告

## MCP工具列表

### 认证工具
- `login` - 用户登录
- `logout` - 用户登出
- `get_current_user` - 获取当前用户信息
- `switch_user` - 切换用户（管理员）

### 数据源工具
- `list_data_sources` - 列出数据源
- `create_sql_data_source` - 创建SQL数据源
- `create_api_data_source` - 创建API数据源
- `upload_csv_data_source` - 上传CSV数据源
- `test_data_source` - 测试数据源连接
- `sync_data_source` - 同步数据源数据
- `delete_data_source` - 删除数据源

### 模板工具
- `list_templates` - 列出模板
- `create_text_template` - 创建文本模板
- `upload_template_file` - 上传模板文件
- `preview_template` - 预览模板
- `duplicate_template` - 复制模板
- `delete_template` - 删除模板

### 任务工具
- `list_tasks` - 列出任务
- `create_task` - 创建任务
- `update_task` - 更新任务
- `run_task` - 运行任务
- `enable_task` - 启用任务
- `disable_task` - 禁用任务
- `delete_task` - 删除任务
- `get_task_logs` - 获取任务日志

### 报告工具
- `generate_report` - 生成报告
- `list_reports` - 列出报告历史
- `download_report` - 下载报告
- `regenerate_report` - 重新生成报告
- `delete_report` - 删除报告

### AI提供商工具
- `list_ai_providers` - 列出AI提供商
- `create_ai_provider` - 创建AI提供商配置
- `update_ai_provider` - 更新AI提供商
- `test_ai_provider` - 测试AI提供商连接
- `delete_ai_provider` - 删除AI提供商

### 系统设置工具
- `get_system_settings` - 获取系统设置
- `update_system_settings` - 更新系统设置
- `get_email_settings` - 获取邮件设置
- `update_email_settings` - 更新邮件设置
- `test_email_settings` - 测试邮件配置

### 用户管理工具
- `list_users` - 列出用户（管理员）
- `create_user` - 创建用户（管理员）
- `update_user` - 更新用户信息
- `delete_user` - 删除用户（管理员）
- `reset_user_password` - 重置用户密码（管理员）

### 工作流工具
- `create_complete_workflow` - 创建完整工作流
- `setup_daily_report` - 设置日报工作流
- `setup_weekly_report` - 设置周报工作流
- `bulk_import_data_sources` - 批量导入数据源
- `migrate_templates` - 迁移模板

## 🔧 测试验证

### 1. 测试连接
```bash
# stdio模式 - 直接运行
cd /Users/shan/work/uploads/AutoReportAI/mcp-server
source venv/bin/activate
python main.py

# SSE模式 - HTTP测试
curl http://localhost:8001/health
curl -X POST http://localhost:8001/quick_setup
```

### 2. 功能测试
```bash
# 登录测试
curl -X POST http://localhost:8001/tools/mcp_login \
  -H "Content-Type: application/json" \
  -d '{"arguments": {}}'

# 获取工具列表
curl http://localhost:8001/tools
```

## 使用示例

### 基本工作流
```python
# 1. 登录
login(username="admin", password="password")

# 2. 创建数据源
create_sql_data_source(
    name="销售数据库",
    connection_string="postgresql://user:pass@localhost:5432/sales"
)

# 3. 创建模板
create_text_template(
    name="销售日报",
    content="今日销售额：{{total_sales}}，订单数：{{order_count}}"
)

# 4. 创建定时任务
create_task(
    name="每日销售报告",
    template_id="template-uuid",
    data_source_id="datasource-uuid",
    schedule="0 9 * * *",  # 每天9点执行
    recipients="manager@company.com"
)
```

### AI配置示例
```python
# 配置OpenAI
create_ai_provider(
    name="OpenAI GPT-4",
    provider_type="openai",
    api_key="sk-...",
    model="gpt-4",
    max_tokens=4000
)

# 配置Claude
create_ai_provider(
    name="Anthropic Claude",
    provider_type="anthropic",
    api_key="sk-ant-...",
    model="claude-3-sonnet-20240229"
)
```

### 📝 使用示例（LLM中使用）

一旦配置完成，你可以在LLM中这样使用：

```
用户：请帮我登录AutoReportAI系统
助手：我来帮你登录AutoReportAI系统
[调用 mcp_login 工具]

用户：创建一个名为"销售数据"的API数据源
助手：我来为你创建API数据源
[调用 mcp_create_api_data_source 工具]

用户：生成一份销售报告
助手：我来生成销售报告
[调用 mcp_generate_report 工具]
```

## 安全特性

- 🔐 基于Session的用户认证
- 🛡️ 用户资源隔离
- 🔑 API密钥安全存储
- 📝 操作审计日志
- ⚡ 自动token刷新

## ⚠️ 注意事项

1. **路径配置**: 确保所有路径都是绝对路径
2. **环境变量**: 后端服务地址必须正确
3. **权限设置**: 确保Python脚本有执行权限
4. **端口冲突**: 确保8000和8001端口未被占用
5. **依赖安装**: 确保虚拟环境中的依赖完整

## 🆘 故障排除

### 常见问题
1. **连接失败**: 检查后端服务是否运行在8000端口
2. **工具不可用**: 检查MCP服务器日志
3. **权限错误**: 检查文件路径和Python环境
4. **端口占用**: 使用lsof检查端口占用情况

### 日志查看
```bash
# 查看后端日志
docker-compose logs backend

# 查看MCP服务器日志  
tail -f /Users/shan/work/uploads/AutoReportAI/mcp-server/mcp-server.log
```

## 扩展性

MCP服务器采用模块化设计，可以轻松添加新的工具和功能：

1. 在 `tools/` 目录下添加新的工具文件
2. 在 `main.py` 中注册新的工具模块
3. 添加相应的测试用例

## License

MIT License