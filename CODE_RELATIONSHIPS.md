# AutoReportAI 核心代码关系和数据流向详细解析

## 一、组件依赖关系图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         前端 (Next.js)                             │
│  reportStore.ts                                                     │
│   └─ downloadReport() → GET /reports/{id}/download                 │
│   └─ batchDownloadReports() → POST /reports/batch/zip              │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │  FastAPI Routes  │
                    │  /reports.py     │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ ReportHistory │  │ ReportService    │  │ HybridStorage    │
│ (数据库)      │  │ (业务逻辑)       │  │ (文件存储)       │
└───────────────┘  └──────┬───────────┘  └────────┬─────────┘
                           │                       │
        ┌──────────────────┴───────────┐          │
        │                              │          │
        ▼                              ▼          ▼
┌──────────────────┐         ┌──────────────────────┐
│ Task执行 (Celery)│         │ MinIO / Local        │
│ execute_report   │         │ FileStorage          │
│     _task()      │         └──────────────────────┘
└────────┬─────────┘
         │
    ┌────┴─────────────────────────────┐
    │                                  │
    ▼                                  ▼
┌─────────────────────┐      ┌──────────────────────┐
│ PlaceholderSystem   │      │ WordTemplateService  │
│ (Agent分析)         │      │ (文档处理)           │
└─────────────────────┘      └──────────┬───────────┘
                                        │
                        ┌───────────────┴────────────────┐
                        │                                │
                        ▼                                ▼
                ┌──────────────────┐        ┌────────────────────┐
                │ 文本替换         │        │ Agent优化           │
                │ (占位符)         │        │ (内容改进)         │
                └──────────────────┘        └────────────────────┘
                        │
                        └────────────────┬─────────────────┐
                                        │                 │
                                        ▼                 ▼
                                ┌──────────────┐  ┌────────────────┐
                                │ 图表生成      │  │ Word保存       │
                                │              │  │                │
                                └──────────────┘  └────────┬───────┘
                                                           │
                                                  ┌────────▼────────┐
                                                  │ Upload to MinIO  │
                                                  │ (storage upload) │
                                                  └─────────────────┘
```

---

## 二、主要数据流向

### 2.1 Task执行数据流

```
Input:
{
    "task_id": 1,
    "template_id": "uuid",
    "data_source_id": "uuid",
    "user_id": "uuid"
}
    │
    ▼
execute_report_task(task_id, execution_context)
    │
    ├─ Phase 1: 初始化 (0-20%)
    │  ├─ load_schema_context()
    │  ├─ init_placeholder_system()
    │  └─ load_time_context()
    │
    ├─ Phase 2: 占位符分析 (20-65%)
    │  ├─ scan_placeholders_from_template()
    │  ├─ for each placeholder:
    │  │   └─ agent.analyze_placeholder()
    │  │       ├─ generate_sql()
    │  │       ├─ validate_sql()
    │  │       └─ store_placeholder_metadata()
    │  │
    │  └─ events: {
    │      type: "placeholder_sql_generated",
    │      placeholder_name: "xxx",
    │      sql: "SELECT ...",
    │      confidence: 0.95
    │    }
    │
    ├─ Phase 3: ETL处理 (65-85%)
    │  │
    │  └─ for each placeholder with sql:
    │      ├─ replace_time_placeholders()
    │      │  └─ {{start_date}} → "2024-01-01"
    │      │
    │      ├─ execute_query(final_sql)
    │      │  ├─ create_connector(data_source)
    │      │  ├─ connector.execute_query()
    │      │  └─ result: DataFrame
    │      │
    │      ├─ validate_columns()
    │      │  └─ auto_fix_if_needed()
    │      │
    │      └─ extract_value()
    │          ├─ single_row_single_col → scalar
    │          ├─ single_row_multi_col → dict
    │          └─ multi_row → list[dict]
    │
    │  etl_result: {
    │      "placeholder_name": {
    │          "success": true,
    │          "value": 150000,  ← 实际数据值
    │          "metadata": {}
    │      }
    │  }
    │
    ├─ Phase 4: 构建占位符数据 (85-87%)
    │  │
    │  └─ placeholder_render_data = {
    │      "销售总额": 150000,
    │      "销售趋势": [
    │          {"date": "2024-01-01", "amount": 5000},
    │          ...
    │      ]
    │    }
    │
    ├─ Phase 5: 文档生成 (87-95%)
    │  │
    │  ├─ word_template_service.process_document_template(
    │  │      template_path="/path/template.docx",
    │  │      placeholder_data=placeholder_render_data,
    │  │      container=container,
    │  │      use_agent_optimization=True
    │  │   )
    │  │
    │  └─ return: {
    │       "success": true,
    │       "output_path": "/tmp/report_xxx.docx",
    │       "document_bytes": <binary>,
    │       "friendly_file_name": "report_20240101.docx"
    │     }
    │
    ├─ Phase 6: 存储上传 (92-95%)
    │  │
    │  └─ storage.upload_with_key(
    │       file_data=document_bytes,
    │       object_name="reports/{tenant}/{slug}/report.docx"
    │     )
    │     ├─ put_object(bucket, object_name, data)
    │     └─ return: {file_path, size, backend}
    │
    ├─ Phase 7: 数据保存 (95-97%)
    │  │
    │  ├─ task_execution.execution_result = {...}
    │  ├─ task_execution.execution_status = COMPLETED
    │  │
    │  └─ report_history = ReportHistory(
    │       task_id=task.id,
    │       file_path="reports/{tenant}/{slug}/...",
    │       file_size=524288,
    │       status="completed",
    │       processing_metadata={...}
    │     )
    │
    └─ Phase 8: 完成通知 (97-100%)
       ├─ notify_task_progress(status=COMPLETED)
       ├─ send_email_notification()
       └─ update_task_statistics()

Output:
{
    "status": "completed",
    "task_id": 1,
    "execution_id": "exec-uuid",
    "execution_time": 180,
    "result": {
        "success": true,
        "placeholders_success": 10,
        "report": {
            "storage_path": "reports/{tenant}/{slug}/report_20240101.docx",
            "backend": "minio",
            "size": 524288
        }
    }
}
```

### 2.2 文档优化数据流

```
Input: placeholder_render_data = {
    "销售总额": 150000,
    "同比增长": 12.5
}

Template Content:
"去年同期销售总额{{销售总额}}万元，同比{{同比增长}}%增长。"

┌──────────────────────────────────────────────┐
│ process_document_template()                  │
│ (WordTemplateService)                        │
└──────────────┬───────────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
Step 1: 文本替换  Step 2: Agent优化
   {{销售总额}}      原文:
   ↓                 "去年同期销售总额150000万元，"
   150000            "同比12.5%增长。"
                     │
                     ├─ 检查段落包含数据值?
                     │  YES: "150000" 在段落中
                     │
                     ├─ 构建优化请求:
                     │  {
                     │    paragraph_text: "去年同期...",
                     │    related_placeholders: {
                     │      "销售总额": 150000,
                     │      "同比增长": 12.5
                     │    },
                     │    requirements: [
                     │      "保持核心意思",
                     │      "更专业表达",
                     │      "根据数值调整语气"
                     │    ]
                     │  }
                     │
                     ├─ agent.generate_document()
                     │  │
                     │  └─ LLM调用 (Claude, GPT等)
                     │     └─ 返回:
                     │        {
                     │          "success": true,
                     │          "document_text":
                     │            "去年同期销售总额达150000万元，"
                     │            "环比增长12.5%，呈现稳健增长态势。"
                     │        }
                     │
                     ├─ 解析JSON响应
                     │  JSON格式化响应 → 提取文本
                     │  [尝试多个字段: optimized_paragraph, result, text, content]
                     │
                     ├─ 清理Markdown标记
                     │  移除 ``` 代码块标记
                     │
                     └─ 更新段落文本
                        p.runs[0].text = optimized_text
                        (保留原格式，仅更新内容)

Step 3: 图表处理
   {{图表：销售趋势}} → 从placeholder_data中查找
   └─ data = [
      {date: "2024-01-01", amount: 5000},
      {date: "2024-01-02", amount: 5200},
      ...
   ]
   
   ├─ ChartPlaceholderProcessor.process_chart_placeholder()
   │  ├─ detect_chart_type() → "line"
   │  ├─ transform_data()
   │  └─ generate_chart(data, chart_type)
   │      └─ agent.generate_chart()
   │         └─ 返回 chart_image_path
   │
   └─ insert_chart_in_document()
      └─ p.add_run().add_picture(chart_path, width=6inch)

Step 4: 文档保存
   doc.save(output_path)
   ├─ 所有优化内容已保存到Word
   ├─ 返回 BytesIO
   └─ 返回 {
      "success": true,
      "output_path": "/tmp/report_xxx.docx",
      "document_bytes": <optimized binary>,
      "friendly_file_name": "report_20240101.docx"
    }

Final Result:
最终Word文档包含:
✅ 被替换的占位符值 (150000, 12.5)
✅ 被Agent优化的段落文本 (更专业、更流畅)
✅ 生成的图表 (销售趋势线图)
```

---

## 三、关键方法签名和返回值

### 3.1 Task执行

```python
# 主任务入口
@celery_app.task(bind=True, base=DatabaseTask, 
                 name='tasks.infrastructure.execute_report_task')
def execute_report_task(
    self,
    db: Session,
    task_id: int,
    execution_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    执行报告生成任务
    
    Args:
        task_id: 任务ID
        execution_context: {trigger, schedule, triggered_at, ...}
    
    Returns:
        {
            "status": "completed" | "failed" | "cancelled",
            "task_id": 1,
            "execution_id": "uuid",
            "execution_time": 180,
            "result": {
                "success": bool,
                "events": [...],
                "etl_results": {...},
                "placeholders_processed": 10,
                "placeholders_success": 9,
                "placeholders_failed": ["failed_ph"],
                "report": {
                    "storage_path": "reports/...",
                    "backend": "minio",
                    "friendly_name": "report.docx",
                    "size": 524288
                }
            }
        }
    """
```

### 3.2 占位符分析

```python
async def _process_placeholders_individually():
    """
    单个循环处理占位符并批量持久化
    
    For each placeholder:
        ├─ placeholder_text: "销售总额"
        ├─ placeholder_type: "text" | "chart"
        ├─ agent.analyze()
        │  └─ return: {
        │       "success": true,
        │       "sql": "SELECT SUM(amount) FROM sales",
        │       "validated": true,
        │       "confidence": 0.95,
        │       "auto_fixed": false
        │     }
        └─ db.commit() (批量5条)
    
    Return: processed_count (int)
    """
```

### 3.3 文档处理

```python
async def process_document_template(
    self,
    template_path: str,
    placeholder_data: Dict[str, Any],
    output_path: str,
    container=None,
    use_agent_charts: bool = True,
    use_agent_optimization: bool = True,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    处理Word文档模板
    
    Args:
        template_path: "/path/to/template.docx"
        placeholder_data: {
            "销售总额": 150000,
            "销售趋势": [{"date": "...", "amount": ...}],
            ...
        }
        output_path: "/tmp/report_xxx.docx"
        use_agent_optimization: 是否使用Agent优化
        use_agent_charts: 是否使用Agent生成图表
    
    Returns:
        {
            "success": True,
            "output_path": "/tmp/report_xxx.docx",
            "document_bytes": <binary>,
            "friendly_file_name": "report_20240101.docx",
            "generation_mode": "word_template_service",
            "placeholders_processed": 10
        }
    """
```

### 3.4 优化内容处理

```python
async def _optimize_document_content_with_agent(
    self,
    doc,
    data: Dict[str, Any],
    container=None,
    user_id: Optional[str] = None
):
    """
    使用Agent优化文档内容
    
    For each paragraph:
        1. 检查是否包含已替换的数据值
        2. 如果包含，调用Agent优化
        3. Agent输入:
           - paragraph_context: "原始段落文本"
           - placeholder_data: [{key: value}, ...]
           - user_id: "user-uuid"
        4. Agent输出:
           - document_text: "优化后的段落" 或 JSON
        5. 解析JSON:
           - optimized_paragraph / result / text / content
        6. 更新paragraph: p.runs[0].text = optimized_text
    
    Side Effect:
        - 直接修改doc对象的段落文本
        - 记录优化统计 (optimized_count)
    """
```

### 3.5 存储上传

```python
def upload_with_key(
    self,
    file_data: BytesIO,
    object_name: str,
    content_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    按指定对象键上传文件
    
    Args:
        file_data: BytesIO缓冲区 (DOCX二进制)
        object_name: "reports/{tenant_id}/{slug}/report_20240101.docx"
        content_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    Returns (成功):
        {
            "file_path": "reports/{tenant_id}/{slug}/report_20240101.docx",
            "size": 524288,
            "backend": "minio",
            "uploaded_at": "2024-01-01T12:00:00"
        }
    
    Returns (失败):
        Exception: MinIOStorageError / FileStorageError
        
    Fallback:
        如果MinIO失败，自动回退本地存储:
        {
            "file_path": "...",
            "size": 524288,
            "backend": "local_fallback"
        }
    """
```

### 3.6 前端下载

```typescript
async downloadReport(id: string): Promise<void> {
    /*
    Request:
        GET /api/v1/reports/{id}/download
        
    Response Headers:
        Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
        Content-Disposition: attachment; filename="report_20240101.docx"
    
    Response Body:
        <binary DOCX data>
    
    Front-end Action:
        1. 创建 Blob(response.data)
        2. 创建 ObjectURL
        3. 创建临时<a>元素
        4. 设置 href 和 download
        5. 模拟点击下载
        6. 清理资源
    */
}
```

---

## 四、关键的数据转换点

### 4.1 SQL执行结果转换

```python
# Input: DorisQueryResult 对象
{
    data: DataFrame([
        {"date": "2024-01-01", "amount": 5000},
        {"date": "2024-01-02", "amount": 5200},
    ]),
    execution_time: 0.123
}

# Transform 1: DataFrame → Dict List
result_data = query_result.data.to_dict('records')
# → [{"date": "2024-01-01", "amount": 5000}, ...]

# Transform 2: Decimal → float
from app.utils.json_utils import convert_decimals
result_data = convert_decimals(result_data)
# → [{"date": "2024-01-01", "amount": 5000.0}, ...]

# Transform 3: 智能解包
if len(result_data) == 1 and len(result_data[0]) == 1:
    # 单行单列 → 标量值
    actual_value = list(result_data[0].values())[0]  # 5000
elif len(result_data) == 1:
    # 单行多列 → 字典
    actual_value = result_data[0]  # {"date": "2024-01-01", "amount": 5000}
else:
    # 多行 → 列表
    actual_value = result_data  # [...] 用于图表

# Output: placeholder_render_data[name] = actual_value
```

### 4.2 占位符值提取

```python
# Extract from various types
def _extract_value_from_result(value):
    
    # Case 1: None
    if value is None:
        return None
    
    # Case 2: 简单类型
    if isinstance(value, (str, int, float, bool)):
        return value
    
    # Case 3: DorisQueryResult
    if hasattr(value, 'data') and hasattr(value, 'execution_time'):
        return _extract_value_from_result(value.data)
    
    # Case 4: pandas.DataFrame
    if hasattr(value, 'iloc'):
        return value.iloc[0, 0]  # 取第一行第一列
    
    # Case 5: Dict
    if isinstance(value, dict):
        # 优先查找 data 字段
        if 'data' in value:
            return _extract_value_from_result(value['data'])
        # 查找常见的数值字段
        for key in ['count', 'total', 'sum', 'avg', 'value']:
            if key in value:
                return _extract_value_from_result(value[key])
        # 字典只有一个键值对
        if len(value) == 1:
            return next(iter(value.values()))
    
    # Case 6: List/Tuple
    if isinstance(value, (list, tuple)) and value:
        return _extract_value_from_result(value[0])
    
    # Case 7: 其他
    return str(value)
```

### 4.3 占位符替换链

```
替换链条:
{{销售总额}} (占位符)
    ↓
placeholder_render_data["销售总额"] (数据查询)
    ↓
150000 (ETL结果)
    ↓
"150000" (转换为字符串)
    ↓
p.runs[0].text = "去年销售总额150000万元..." (Word替换)
    ↓
Agent优化 (可选)
    ↓
p.runs[0].text = "去年销售总额达150000万元，呈稳定增长..." 
    ↓
doc.save() (保存)
    ↓
BytesIO (二进制)
    ↓
upload_with_key(file_data, object_name) (上传)
    ↓
file_path="reports/.../report.docx" (存储路径)
    ↓
ReportHistory.file_path (数据库保存)
    ↓
GET /reports/{id}/download (前端下载)
    ↓
最终Word文档 (用户)
```

---

## 五、关键错误处理流程

### 5.1 占位符分析失败

```python
try:
    # 1. Agent分析失败
    sql_result = await orchestration_service.analyze_placeholder()
except Exception as e:
    # 2. 切换到ERROR_RECOVERY阶段
    state_manager.set_stage(ExecutionStage.ERROR_RECOVERY)
    
    # 3. 记录错误上下文
    state_manager.add_context(
        key=f"sql_generation_error_{ph.placeholder_name}",
        item=ContextItem(
            type=ContextType.ERROR_INFO,
            content=f"占位符 {ph.placeholder_name} SQL生成失败: {error_msg}"
        )
    )
    
    # 4. 标记为失败
    failed_placeholders.append(ph.placeholder_name)
    
    # 5. 继续处理下一个占位符（不终止）
    continue
```

### 5.2 ETL容错

```python
# 允许有限失败继续生成
max_failed_allowed = settings.REPORT_MAX_FAILED_PLACEHOLDERS_FOR_DOC  # 默认0
tolerance_passed = (
    len(failed_placeholders) <= max_failed_allowed and 
    successful_placeholders_count > 0
)

if not tolerance_passed:
    # ETL全部失败 → 不生成文档
    should_generate_document = False
    report_generation_error = "ETL阶段存在失败..."
else:
    # ETL部分失败 → 继续生成，注入占位文本
    should_generate_document = True
    for failed_name in failed_placeholders:
        if placeholder_render_data.get(failed_name) in (None, ""):
            # 注入友好提示，避免空白
            placeholder_render_data[failed_name] = "【占位提示：数据暂不可用】"
```

### 5.3 优化容错

```python
try:
    optimized_text = await agent_adapter.generate_document(...)
except Exception as opt_error:
    logger.warning(f"段落优化异常: {opt_error}, 保持原文")
    # 优化失败不影响主流程 → 使用原文本
    # paragraph保持不变，继续执行下一段
    continue
```

### 5.4 存储容错

```python
try:
    # 1. 尝试MinIO上传
    result = minio_storage.upload_with_key(file_data, object_name)
except Exception as e:
    logger.error(f"MinIO存储失败: {e}")
    
    if self.backend_type == "minio" and self.fallback_service:
        # 2. MinIO失败 → 回退本地存储
        try:
            file_data.seek(0)
            result = self.fallback_service.upload_file(
                file_data, original_filename, file_type, content_type
            )
            result["backend"] = "local_fallback"
            logger.warning("MinIO存储失败，回退到本地存储")
        except Exception as fallback_error:
            # 3. 本地存储也失败 → 最终异常
            logger.error(f"回退存储也失败: {fallback_error}")
            raise fallback_error
    raise e
```

---

## 六、WebSocket实时进度通知

```python
# TaskProgressRecorder 负责发送进度通知

progress_recorder.start(msg)
    ├─ notify_task_start()
    └─ notify_task_progress(status=SCANNING, progress=0%)

progress_recorder.update(percentage, message, stage, ...)
    ├─ _append_event() (数据库)
    └─ notify_task_progress(
        status=pipeline_status,
        progress=percentage,
        details={stage, placeholder, ...}
    )

progress_recorder.complete(msg)
    ├─ _append_event(status="success")
    └─ notify_task_complete()

progress_recorder.fail(msg, error)
    ├─ _append_event(status="failed")
    └─ notify_task_error(error_details)

# WebSocket消息格式
{
    "task_id": "report_task_exec-uuid",
    "task_type": "REPORT_ASSEMBLY",
    "status": "SCANNING" | "ANALYZING" | "ASSEMBLING" | "COMPLETED" | "FAILED",
    "progress": 0.0-100.0,
    "message": "正在初始化...",
    "details": {
        "stage": "schema_initialization",
        "placeholder": "销售总额",
        "current": 3,
        "total": 10
    },
    "error": null | "错误信息"
}
```

---

## 七、完整代码调用栈示例

```
用户点击"生成报告" (前端)
    ↓
Task.execute() (API端点)
    ↓
celery.apply_async(execute_report_task, args=[task_id])
    ↓
execute_report_task(task_id, execution_context) (Celery Worker)
    ├─ 1. Schema初始化
    │  └─ create_schema_context_retriever().initialize()
    │
    ├─ 2. 占位符分析 (遍历)
    │  └─ for ph in placeholders_need_analysis:
    │      ├─ analyze_single_placeholder_task.delay()
    │      │  └─ PlaceholderOrchestrationService.analyze_placeholder_with_full_pipeline()
    │      │     └─ Agent.generate_sql()
    │      │
    │      └─ db.commit() (批量保存)
    │
    ├─ 3. ETL处理 (遍历)
    │  └─ for ph in placeholders:
    │      ├─ create_connector_from_config()
    │      ├─ connector.execute_query(final_sql)
    │      ├─ convert_decimals(result_data)
    │      └─ etl_results[name] = {success, value, ...}
    │
    ├─ 4. 文档生成
    │  └─ word_template_service.process_document_template(
    │      template_path=...,
    │      placeholder_data={name: value, ...},
    │      container=container,
    │      use_agent_optimization=True
    │    )
    │    ├─ _replace_text_in_document()
    │    │  └─ for p in doc.paragraphs:
    │    │      └─ p.runs[0].text = str(placeholder_render_data[key])
    │    │
    │    ├─ _optimize_document_content_with_agent()
    │    │  └─ for p in doc.paragraphs (if contains data):
    │    │      ├─ agent_adapter.generate_document(...)
    │    │      └─ p.runs[0].text = optimized_text
    │    │
    │    ├─ _replace_chart_placeholders_with_agent()
    │    │  └─ for p in doc.paragraphs (if {{chart:...}}):
    │    │      ├─ chart_processor.process_chart_placeholder()
    │    │      └─ p.add_run().add_picture()
    │    │
    │    └─ doc.save(output_path)
    │
    ├─ 5. 存储上传
    │  └─ storage.upload_with_key(
    │      file_data=document_bytes,
    │      object_name="reports/tenant_id/slug/report_xxx.docx"
    │    )
    │    ├─ MinIO: client.put_object()
    │    └─ return: {file_path, size, backend}
    │
    ├─ 6. 数据保存
    │  ├─ task_execution.execution_result = {...}
    │  ├─ report_history = ReportHistory(...)
    │  └─ db.commit()
    │
    └─ 7. 通知发送
       ├─ notify_task_progress(status=COMPLETED)
       ├─ send_email_notification()
       └─ return execution_result

用户在报告列表中看到"已完成" (前端)
    ↓
用户点击"下载"
    ↓
GET /api/v1/reports/{id}/download (API)
    ├─ 1. 查询 ReportHistory.file_path
    │
    ├─ 2. storage.download_file(file_path)
    │  └─ MinIO: client.get_object()
    │
    ├─ 3. return FileResponse(
    │      content=file_data,
    │      media_type="application/...",
    │      headers={Content-Disposition: ...}
    │    )
    │
    └─ 返回 DOCX 二进制

浏览器下载文档
    └─ 保存为 report_20240101.docx
```

