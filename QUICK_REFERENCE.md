# AutoReportAI 快速参考指南

## 核心文件路径速查表

### Task任务队列相关
```
/backend/app/services/infrastructure/task_queue/
├─ tasks.py                          ⭐ execute_report_task() 主任务入口
├─ progress_recorder.py               🔔 TaskProgressRecorder WebSocket通知
├─ progress_manager.py                📊 进度管理
└─ task_runner.py                     🏃 任务运行器

/backend/app/core/
├─ task_config.py                     ⚙️  任务配置
├─ task_status_manager.py             📋 任务状态管理
└─ dependencies.py                    🔗 依赖注入
```

### 文档优化和生成相关
```
/backend/app/services/infrastructure/document/
├─ word_template_service.py           ⭐ WordTemplateService 文档处理
│  ├─ process_document_template()     📝 主处理方法
│  ├─ _replace_text_in_document()     🔄 占位符替换
│  ├─ _optimize_document_content_with_agent() 🤖 Agent优化
│  └─ _replace_chart_placeholders_with_agent() 📊 图表处理
├─ chart_placeholder_processor.py     📉 图表处理器
└─ word_generator_service.py          📄 Word生成

/backend/app/services/domain/reporting/
└─ word_generator_service.py          (备用Word生成器)
```

### 存储相关
```
/backend/app/services/infrastructure/storage/
├─ hybrid_storage_service.py          ⭐ HybridStorageService 混合存储
│  ├─ upload_file()                   📤 自动生成文件名上传
│  ├─ upload_with_key()               🔑 指定路径上传
│  ├─ download_file()                 📥 下载文件
│  └─ get_download_url()              🔗 获取预签名URL
├─ minio_storage_service.py           🪣 MinIO客户端
└─ file_storage_service.py            💾 本地文件存储
```

### 前端相关
```
/frontend/src/features/reports/
├─ reportStore.ts                     ⭐ 报告Zustand Store
│  ├─ downloadReport()                📥 单个下载
│  └─ batchDownloadReports()          📦 批量打包下载
└─ pages/reports/

/frontend/src/services/
└─ apiService.ts                      🔗 API服务
```

### API端点相关
```
/backend/app/api/endpoints/
├─ reports.py                         ⭐ 报告API
│  ├─ GET /reports/                   📋 列表
│  ├─ GET /reports/{id}/download      📥 单个下载
│  ├─ POST /reports/batch/zip         📦 批量打包
│  └─ DELETE /reports/{id}            🗑️  删除
└─ ...其他端点
```

---

## 关键方法速查

### 执行任务 (execute_report_task)
```python
# 文件: /backend/app/services/infrastructure/task_queue/tasks.py
# 行数: ~400-500 lines
# 触发: Celery任务 / 前端API

def execute_report_task(db, task_id, execution_context):
    """主报告生成任务"""
    # Phase 1: 初始化 Schema Context
    # Phase 2: 占位符分析 (Agent)
    # Phase 3: ETL 处理
    # Phase 4: 文档生成
    # Phase 5: 存储上传
    return execution_result

# 关键参数:
#   task_id: 任务ID
#   execution_context: {
#       trigger: "manual" | "scheduled",
#       schedule: "0 0 * * *",
#       recipients: ["user@example.com"],
#       time_window: {...}
#   }

# 返回值:
#   {
#       "status": "completed" | "failed",
#       "task_id": 1,
#       "result": {
#           "success": bool,
#           "report": {
#               "storage_path": "reports/.../report.docx",
#               "backend": "minio",
#               "size": 524288
#           }
#       }
#   }
```

### 文档处理 (process_document_template)
```python
# 文件: /backend/app/services/infrastructure/document/word_template_service.py
# 方法: WordTemplateService.process_document_template()
# 行数: ~67-140

async def process_document_template(
    template_path: str,
    placeholder_data: Dict[str, Any],
    output_path: str,
    container=None,
    use_agent_optimization: bool = True,  # ⭐ 关键参数
    use_agent_charts: bool = True
) -> Dict[str, Any]:
    """处理Word文档模板"""
    # 1. _replace_text_in_document() - 替换占位符
    # 2. _optimize_document_content_with_agent() - 优化内容
    # 3. _replace_chart_placeholders_with_agent() - 生成图表
    # 4. doc.save() - 保存文档
    return result

# 重要: 优化内容直接嵌入Word文件，没有显式回调
```

### Agent优化 (_optimize_document_content_with_agent)
```python
# 文件: /backend/app/services/infrastructure/document/word_template_service.py
# 方法: _optimize_document_content_with_agent()
# 行数: ~286-446

async def _optimize_document_content_with_agent(doc, data, container, user_id):
    """使用Agent优化文档内容"""
    for paragraph in doc.paragraphs:
        if contains_data_values(paragraph):
            # 调用Agent优化此段落
            optimized = await agent.generate_document(
                paragraph_context=paragraph.text,
                placeholder_data=related_data
            )
            # 更新段落文本
            paragraph.runs[0].text = optimized
    
    # 返回: 无，直接修改doc对象

# Agent响应处理:
#   - JSON格式: 解析 .optimized_paragraph / .result / .text / .content
#   - Markdown: 移除 ``` 标记
#   - 保持格式: 仅更新文本，保留run格式
```

### 存储上传 (upload_with_key)
```python
# 文件: /backend/app/services/infrastructure/storage/hybrid_storage_service.py
# 方法: HybridStorageService.upload_with_key()
# 行数: ~128-150

def upload_with_key(
    file_data: BytesIO,
    object_name: str,
    content_type: str = None
) -> Dict[str, Any]:
    """上传文件到存储"""
    # MinIO优先，失败回退本地存储
    return {
        "file_path": "reports/tenant_id/slug/report.docx",
        "backend": "minio" | "local_fallback",
        "size": 524288
    }
```

### 前端下载 (downloadReport)
```typescript
// 文件: /frontend/src/features/reports/reportStore.ts
// 方法: downloadReport()
// 行数: ~134-176

async downloadReport(id: string): Promise<void> {
    // 1. GET /reports/{id}/download
    // 2. 获取 content-disposition header
    // 3. 解析文件名 (RFC 5987)
    // 4. 创建ObjectURL → <a> → 点击下载
    // 5. 清理资源
}
```

---

## 数据流向快速查询

### 占位符数据流
```
Template {{sales_amount}}
    ↓
placeholder_scan()
    ↓
Agent生成SQL: "SELECT SUM(amount) FROM sales"
    ↓
execute_query()
    ↓
DataFrame → extract_value()
    ↓
placeholder_render_data["sales_amount"] = 150000
    ↓
_replace_text_in_document()
    ↓
Word文本: "{{sales_amount}}" → "150000"
```

### 优化流程
```
_replace_text_in_document() (已完成替换)
    ↓
_optimize_document_content_with_agent()
    ├─ 检查段落 contains "150000"?
    ├─ YES → 调用Agent
    ├─ Agent: 优化段落文字
    └─ 更新: p.runs[0].text = optimized_text
    ↓
doc.save() (优化内容已保存)
    ↓
upload_with_key() (上传优化后的文件)
    ↓
ReportHistory.file_path (保存路径)
    ↓
前端下载 (获取优化后的文件)
```

---

## 关键配置参数

### MinIO配置
```python
# /backend/app/core/config.py
MINIO_ENDPOINT = "minio-server:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_BUCKET_NAME = "autoreport"
MINIO_SECURE = False
FORCE_LOCAL_STORAGE = False
```

### Task配置
```python
# /backend/app/core/task_config.py
TaskExecutionConfig:
  processing_mode = "INTELLIGENT"
  execution_timeout_seconds = 600
  agent_timeout_seconds = 120
  max_retries = 3
  max_context_tokens = 32000-64000
  enable_compression = True

# 容错配置
REPORT_MAX_FAILED_PLACEHOLDERS_FOR_DOC = 0
REPORT_ALLOW_QUALITY_ISSUES = False
```

### Word生成配置
```python
# /backend/app/services/infrastructure/document/word_template_service.py
chart_dpi = 150  # 图表分辨率
font_path = None  # 字体文件
use_agent_charts = True  # 使用Agent生成图表
use_agent_optimization = True  # 使用Agent优化内容
```

---

## 错误处理速查

### 占位符分析失败
```python
# 文件: /backend/app/services/infrastructure/task_queue/tasks.py
# 处理: 跳过失败占位符，继续处理下一个
# 结果: failed_placeholders 列表记录失败

failed_placeholders = ["placeholder_1", "placeholder_2"]
# 在ETL容错检查中处理
```

### ETL容错
```python
tolerance_passed = (
    len(failed_placeholders) <= max_failed_allowed and
    successful_count > 0
)

if tolerance_passed:
    # 注入占位提示，继续生成文档
    placeholder_render_data[failed] = "【占位提示：数据暂不可用】"
else:
    # 不生成文档
    should_generate_document = False
```

### 存储容错
```python
try:
    result = minio.upload_with_key()
except Exception:
    # MinIO失败 → 回退本地存储
    result = local_storage.upload_file()
    result["backend"] = "local_fallback"
```

---

## 常用查询

### 查找占位符优化相关代码
```bash
grep -r "_optimize_document_content_with_agent" /backend
grep -r "agent.generate_document" /backend
grep -r "optimized_paragraph\|optimized_text" /backend
```

### 查找文档生成相关代码
```bash
grep -r "process_document_template" /backend
grep -r "word_template_service" /backend
grep -r "WordTemplateService" /backend
```

### 查找存储相关代码
```bash
grep -r "upload_with_key\|upload_file" /backend
grep -r "HybridStorageService\|MinIOStorageService" /backend
grep -r "file_path.*reports" /backend
```

### 查找前端下载相关代码
```bash
grep -r "downloadReport\|download_report" /frontend
grep -r "GET.*download" /backend/app/api
```

---

## 快速调试技巧

### 1. 跟踪占位符优化流程
```python
# 在 _optimize_document_content_with_agent() 中添加日志
logger.info(f"🤖 优化段落: {paragraph.text[:50]}...")
logger.info(f"📝 优化结果: {optimized_text[:50]}...")

# 检查是否进入优化函数
# 检查是否成功调用Agent
# 检查Agent返回值格式
```

### 2. 跟踪文档上传流程
```python
# 在 upload_with_key() 中检查
logger.info(f"📤 上传文件: {object_name}")
logger.info(f"✅ 上传成功: {result['backend']}")

# 检查file_path是否正确保存到数据库
# 检查MinIO是否真的成功上传
```

### 3. 跟踪前端下载流程
```typescript
// 在 downloadReport() 中添加日志
console.log("Downloading report:", id);
console.log("Response headers:", response.headers);
console.log("File name:", fileName);

// 检查是否成功获取blob
// 检查文件名是否正确解析
// 检查是否真的发起下载
```

### 4. 检查Word文档是否被优化
```python
# 方法1: 检查日志中的 "段落优化成功" 消息
# 方法2: 使用python-docx读取生成的DOCX检查内容
from docx import Document
doc = Document("/path/to/generated_report.docx")
for p in doc.paragraphs:
    print(p.text)

# 检查段落文本是否被优化 (不是简单替换)
```

---

## 常见问题

### Q: 优化内容为什么没有出现在下载的文件中?
**A:** 检查:
1. `use_agent_optimization` 是否为 True
2. `_optimize_document_content_with_agent()` 是否被调用
3. Agent是否返回有效内容
4. `p.runs[0].text` 是否被正确更新
5. `doc.save()` 是否在所有修改后执行

### Q: 为什么有些占位符没有被优化?
**A:** 检查:
1. 段落文本是否包含数据值
2. `if has_data_value and related_placeholders:` 条件是否满足
3. 数据值长度是否 >= 2 (避免匹配单个字符)
4. 占位符是否被跳过 (图表占位符等)

### Q: MinIO上传失败怎么办?
**A:** 自动回退:
1. MinIO失败 → 记录日志
2. 自动回退本地存储
3. 返回 `backend: "local_fallback"`
4. 报告仍能生成和下载

### Q: 前端下载时文件名乱码怎么办?
**A:** 检查:
1. 后端是否返回正确的 content-disposition header
2. 文件名是否使用 RFC 5987 格式 (`filename*=UTF-8''...`)
3. 前端是否正确解析 filename* 和 filename 字段
4. 浏览器编码设置

---

## 性能优化建议

### 占位符优化性能
```python
# 当前: 遍历所有段落，逐个优化
# 优化建议:
# 1. 并行处理多个段落 (asyncio.gather)
# 2. 缓存Agent响应
# 3. 批量处理相似段落
# 4. 设置超时时间
```

### 存储性能
```python
# 当前: 每个文件单独上传
# 优化建议:
# 1. 使用分片上传 (大文件)
# 2. 启用压缩
# 3. 并行上传多个文件
# 4. 使用CDN加速下载
```

### Task执行性能
```python
# 当前: 串行处理各阶段
# 优化建议:
# 1. 占位符分析可并行化
# 2. 多个SQL可并行执行
# 3. Agent调用可使用连接池
# 4. 使用缓存避免重复查询
```

