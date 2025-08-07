# 完善的AI数据分析-报告生成体系设计文档

## 1. 概述

本文档详细描述了一个基于Celery的完善AI数据分析-报告生成体系的设计方案。该系统旨在通过智能化的任务分解和并行处理，提高报告生成的效率和准确性。

## 2. 系统需求和目标

### 2.1 核心功能需求
1. **数据源管理**：
   - 支持多种数据源类型（SQL数据库、CSV文件、API接口、Apache Doris等）
   - 提供复杂查询配置和数据预处理能力

2. **智能模板解析**：
   - 自动识别模板中的占位符
   - 支持多种占位符类型（统计、图表、周期、区域等）

3. **AI驱动的数据分析**：
   - 利用LLM理解业务需求并生成相应的数据分析查询
   - 智能ETL规划和执行
   - 自动生成数据洞察和解释

4. **报告生成和导出**：
   - 支持Word、PDF等多种格式
   - 提供报告质量检查和优化建议

5. **任务调度和监控**：
   - 支持定时任务和手动触发
   - 提供任务状态跟踪和进度通知
   - 集成WebSocket实时通知

### 2.2 技术目标
1. **异步处理**：
   - 使用Celery实现后台任务处理
   - 支持大规模数据处理和长时间运行任务

2. **可扩展性**：
   - 模块化设计，便于添加新的数据源类型和分析功能
   - 支持水平扩展以处理高并发请求

3. **可观测性**：
   - 完整的日志记录和错误追踪
   - 性能监控和指标收集

4. **用户体验**：
   - 提供实时任务进度反馈
   - 友好的错误提示和改进建议

## 3. 系统架构设计

### 3.1 整体架构图

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│   API Layer     │    │  Business Logic  │    │   Data & AI Layer  │
│                 │    │                  │    │                    │
│  RESTful APIs   │───▶│  Task Manager    │───▶│  Data Sources      │
│  WebSockets     │    │  Report Engine   │    │  (SQL, CSV, API)   │
│                 │    │  AI Services     │    │                    │
└─────────────────┘    └──────────────────┘    └────────────────────┘
                              │                         │
                              ▼                         ▼
                     ┌──────────────────┐    ┌────────────────────┐
                     │  Async Workers   │    │  Storage Layer     │
                     │                  │    │                    │
                     │   Celery Tasks   │    │  PostgreSQL        │
                     │   (Report Gen)   │    │  Redis (Cache)     │
                     └──────────────────┘    │  File Storage      │
                              │              └────────────────────┘
                              ▼
                     ┌──────────────────┐
                     │  Notification    │
                     │                  │
                     │  WebSocket       │
                     │  Email           │
                     └──────────────────┘
```

### 3.2 核心组件设计

#### 3.2.1 任务管理器 (TaskManager)
负责协调整个报告生成流程：
- 接收用户请求并创建任务
- 调度Celery异步任务
- 跟踪任务状态和进度
- 处理任务失败和重试

#### 3.2.2 报告引擎 (ReportEngine)
核心报告生成组件：
- 模板解析和占位符识别
- 数据查询和ETL处理
- 报告内容生成和格式化
- 质量检查和优化

#### 3.2.3 AI服务层 (AIService)
提供智能化功能：
- 占位符需求分析
- ETL计划生成
- 数据洞察生成
- 模板优化建议

#### 3.2.4 异步工作器 (Celery Workers)
后台任务处理：
- 报告生成任务
- 数据处理任务
- AI推理任务
- 通知发送任务

### 3.3 数据流设计

#### 3.3.1 报告生成流程
1. 用户创建报告任务
2. TaskManager验证配置并创建任务记录
3. 调度Celery任务开始处理
4. Worker执行数据处理和AI分析
5. 生成报告并保存
6. 发送完成通知

#### 3.3.2 状态管理
- 任务状态：pending → processing → completed/failed
- 进度跟踪：通过Redis存储中间状态
- 实时通知：WebSocket推送状态更新

## 4. Celery任务实现方案

### 4.1 任务分解策略

#### 4.1.1 主任务流程
```
主报告生成任务 (report_generation_pipeline)
├── 模板解析任务 (template_parsing)
├── 占位符分析任务队列
│   ├── 占位符分析任务 1 (placeholder_analysis_1)
│   ├── 占位符分析任务 2 (placeholder_analysis_2)
│   └── 占位符分析任务 N (placeholder_analysis_n)
├── 数据处理任务队列
│   ├── 数据查询任务 1 (data_query_1)
│   ├── 数据查询任务 2 (data_query_2)
│   └── 数据查询任务 N (data_query_n)
├── 内容填充任务 (content_filling)
└── 报告生成任务 (report_generation)
```

#### 4.1.2 任务依赖关系
- 主任务协调所有子任务执行
- 占位符分析任务并行执行
- 数据查询任务依赖对应的占位符分析结果
- 内容填充任务等待所有数据查询完成
- 报告生成任务是最终步骤

### 4.2 具体任务实现

#### 4.2.1 主报告生成任务
```python
@celery_app.task(bind=True)
def report_generation_pipeline(self, task_id: int):
    """
    主报告生成任务 - 协调整个报告生成流程
    """
    # 1. 获取任务配置
    # 2. 解析模板获取占位符列表
    # 3. 创建子任务队列
    # 4. 监控任务进度并更新状态
    # 5. 汇总结果生成最终报告
```

#### 4.2.2 模板解析任务
```python
@celery_app.task
def template_parsing(template_id: str):
    """
    模板解析任务 - 提取所有占位符
    """
    # 1. 加载模板内容
    # 2. 使用PlaceholderProcessor解析占位符
    # 3. 返回占位符列表和元数据
```

#### 4.2.3 占位符分析任务
```python
@celery_app.task
def placeholder_analysis(placeholder_data: dict, data_source_id: str):
    """
    占位符分析任务 - 单个占位符的AI分析
    """
    # 1. 接收占位符数据和数据源信息
    # 2. 调用EnhancedAIService分析占位符需求
    # 3. 生成ETL指令
    # 4. 返回分析结果和执行计划
```

#### 4.2.4 数据查询任务
```python
@celery_app.task
def data_query(etl_instruction: dict, data_source_id: str):
    """
    数据查询任务 - 执行单个ETL指令
    """
    # 1. 接收ETL指令和数据源信息
    # 2. 调用IntelligentETLExecutor执行查询
    # 3. 返回查询结果
```

#### 4.2.5 报告生成任务
```python
@celery_app.task
def report_generation(template_content: str, filled_data: dict, output_config: dict):
    """
    报告生成任务 - 最终生成报告文件
    """
    # 1. 接收填充后的数据和模板
    # 2. 使用ReportCompositionService生成内容
    # 3. 调用WordGeneratorService生成文件
    # 4. 保存报告并返回路径
```

### 4.3 任务状态管理

#### 4.3.1 状态定义
```python
class TaskStatus:
    PENDING = "pending"      # 任务已创建，等待执行
    ANALYZING = "analyzing"  # 正在分析占位符
    QUERYING = "querying"    # 正在执行数据查询
    PROCESSING = "processing" # 正在处理数据
    GENERATING = "generating" # 正在生成报告
    COMPLETED = "completed"  # 任务完成
    FAILED = "failed"        # 任务失败
```

#### 4.3.2 进度跟踪
- 使用Redis存储任务进度信息
- 每个子任务完成时更新主任务进度
- 通过WebSocket实时推送进度给用户

### 4.4 错误处理和重试机制

#### 4.4.1 错误分类
- 占位符解析错误
- AI分析错误
- 数据查询错误
- 报告生成错误

#### 4.4.2 重试策略
- 占位符分析失败：重试3次，使用不同的AI模型
- 数据查询失败：重试2次，检查数据源连接
- 报告生成失败：重试1次，检查模板格式

### 4.5 性能优化

#### 4.5.1 并行处理
- 同类型占位符分析任务并行执行
- 独立的数据查询任务并行执行
- 使用Celery的group和chord特性

#### 4.5.2 缓存机制
- 缓存占位符分析结果
- 缓存常用查询结果
- 缓存模板解析结果

## 5. 监控和通知机制

### 5.1 任务状态跟踪

#### 5.1.1 状态存储
使用Redis存储任务实时状态信息：

```python
# 任务状态键结构
task_status_key = f"report_task:{task_id}:status"
task_progress_key = f"report_task:{task_id}:progress"
task_results_key = f"report_task:{task_id}:results"

# 状态信息结构
{
    "task_id": task_id,
    "status": "analyzing",
    "progress": 25,  # 0-100
    "current_step": "placeholder_analysis_1",
    "total_steps": 10,
    "completed_steps": 2,
    "started_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:05:00Z",
    "placeholder_results": {
        "placeholder_1": {"status": "completed", "result": "..."},
        "placeholder_2": {"status": "processing", "progress": 50}
    }
}
```

#### 5.1.2 进度更新机制
```python
def update_task_progress(task_id: int, status: str, progress: int, 
                        current_step: str = None, step_details: dict = None):
    """
    更新任务进度
    """
    status_data = {
        "status": status,
        "progress": progress,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    if current_step:
        status_data["current_step"] = current_step
        
    # 更新Redis
    redis_client.hset(f"report_task:{task_id}:status", mapping=status_data)
    
    # 推送WebSocket通知
    if step_details:
        await websocket_manager.send_task_notification(
            task_id=task_id,
            user_id=get_task_owner(task_id),
            status=status,
            message=f"任务进度: {progress}%",
            data=step_details
        )
```

### 5.2 实时通知系统

#### 5.2.1 WebSocket通知
```python
class TaskNotificationService:
    async def send_progress_update(self, task_id: int, progress_data: dict):
        """
        发送任务进度更新通知
        """
        user_id = get_task_owner(task_id)
        notification = NotificationMessage(
            type="info",
            title=f"报告任务 #{task_id}",
            message=f"处理进度: {progress_data['progress']}%",
            data={
                "task_id": task_id,
                "progress": progress_data["progress"],
                "status": progress_data["status"],
                "current_step": progress_data.get("current_step")
            },
            user_id=user_id
        )
        await websocket_manager.send_personal_message(notification, user_id)
    
    async def send_completion_notification(self, task_id: int, report_path: str):
        """
        发送任务完成通知
        """
        user_id = get_task_owner(task_id)
        notification = NotificationMessage(
            type="success",
            title="报告生成完成",
            message=f"报告任务 #{task_id} 已完成，可以下载查看。",
            data={
                "task_id": task_id,
                "report_path": report_path,
                "download_url": f"/api/reports/{task_id}/download"
            },
            user_id=user_id
        )
        await websocket_manager.send_personal_message(notification, user_id)
```

#### 5.2.2 邮件通知
```python
class EmailNotificationService:
    def send_task_completion_email(self, user_email: str, task_name: str, 
                                 report_path: str, download_url: str):
        """
        发送任务完成邮件
        """
        subject = f"报告 '{task_name}' 生成完成"
        body = f"""
        <p>您好！</p>
        <p>您请求的报告 '{task_name}' 已经生成完成。</p>
        <p><a href="{download_url}">点击这里下载报告</a></p>
        <p>文件路径: {report_path}</p>
        <p>感谢使用我们的服务！</p>
        """
        email_service.send_email(to_emails=[user_email], subject=subject, body=body)
```

### 5.3 日志和监控

#### 5.3.1 任务日志记录
```python
import logging
from app.core.logging_config import get_performance_logger

perf_logger = get_performance_logger()

@celery_app.task
def placeholder_analysis(placeholder_data: dict, data_source_id: str):
    """
    占位符分析任务 - 单个占位符的AI分析
    """
    task_id = placeholder_data.get('task_id')
    placeholder_name = placeholder_data.get('name')
    
    start_time = time.time()
    perf_logger.info(f"开始分析占位符: {placeholder_name}, 任务ID: {task_id}")
    
    try:
        # 执行分析逻辑
        result = enhanced_ai_service.analyze_placeholder(placeholder_data, data_source_id)
        
        duration = time.time() - start_time
        perf_logger.info(f"占位符分析完成: {placeholder_name}, 耗时: {duration:.2f}秒, 任务ID: {task_id}")
        
        return result
    except Exception as e:
        perf_logger.error(f"占位符分析失败: {placeholder_name}, 错误: {str(e)}, 任务ID: {task_id}")
        raise
```

#### 5.3.2 性能监控指标
```python
class TaskMetrics:
    def __init__(self):
        self.metrics = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "avg_processing_time": 0,
            "placeholder_analysis_time": {},
            "data_query_time": {},
            "report_generation_time": 0
        }
    
    def record_task_completion(self, task_id: int, duration: float, status: str):
        """
        记录任务完成情况
        """
        self.metrics["total_tasks"] += 1
        if status == "completed":
            self.metrics["completed_tasks"] += 1
        else:
            self.metrics["failed_tasks"] += 1
            
        # 更新平均处理时间
        current_avg = self.metrics["avg_processing_time"]
        total_completed = self.metrics["completed_tasks"]
        self.metrics["avg_processing_time"] = (current_avg * (total_completed - 1) + duration) / total_completed
```

### 5.4 错误处理和告警

#### 5.4.1 错误分类和处理
```python
class TaskErrorHandler:
    def handle_task_error(self, task_id: int, error: Exception, task_type: str):
        """
        处理任务错误
        """
        error_info = {
            "task_id": task_id,
            "task_type": task_type,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 记录错误日志
        logger.error(f"任务执行失败: {error_info}")
        
        # 更新任务状态
        update_task_status(task_id, "failed", error_info=error_info)
        
        # 发送错误通知
        user_id = get_task_owner(task_id)
        notification_service.notify_task_failed(
            task_id=task_id,
            user_id=user_id,
            error_message=str(error)
        )
        
        # 根据错误类型决定是否重试
        if self.should_retry(error, task_type):
            self.schedule_retry(task_id, task_type)
```

#### 5.4.2 告警机制
```python
class AlertManager:
    def check_task_failure_rate(self):
        """
        检查任务失败率并发送告警
        """
        failure_rate = self.calculate_failure_rate()
        if failure_rate > 0.1:  # 失败率超过10%
            self.send_alert(
                level="warning",
                title="报告生成任务失败率过高",
                message=f"最近一小时任务失败率达到 {failure_rate:.2%}"
            )
    
    def send_alert(self, level: str, title: str, message: str):
        """
        发送系统告警
        """
        # 记录告警日志
        logger.warning(f"系统告警 [{level}]: {title} - {message}")
        
        # 发送WebSocket系统通知
        websocket_manager.send_system_notification(
            title=title,
            message=message,
            notification_type=level
        )
        
        # 发送邮件告警给管理员
        if level in ["warning", "error"]:
            email_service.send_alert_to_admins(title, message)
```

### 5.5 任务重试机制

#### 5.5.1 重试策略
```python
@celery_app.task(bind=True, autoretry_for=(Exception,), 
                retry_kwargs={'max_retries': 3}, retry_backoff=True)
def robust_placeholder_analysis(self, placeholder_data: dict, data_source_id: str):
    """
    带重试机制的占位符分析任务
    """
    try:
        # 更新任务状态为重试中
        if self.request.retries > 0:
            update_task_status(
                placeholder_data['task_id'], 
                'retrying', 
                retry_count=self.request.retries
            )
        
        # 执行分析
        result = enhanced_ai_service.analyze_placeholder(placeholder_data, data_source_id)
        return result
        
    except Exception as e:
        # 记录重试信息
        logger.warning(f"占位符分析任务重试 {self.request.retries}/3: {str(e)}")
        raise  # 重新抛出异常触发重试
```

## 6. 技术实现建议

### 6.1 Celery配置优化
```python
# celery_config.py
from kombu import Queue

# 任务队列配置
task_routes = {
    'report_generation_pipeline': {'queue': 'report_tasks'},
    'template_parsing': {'queue': 'parsing_tasks'},
    'placeholder_analysis': {'queue': 'analysis_tasks'},
    'data_query': {'queue': 'query_tasks'},
    'report_generation': {'queue': 'generation_tasks'},
}

# 队列声明
task_queues = (
    Queue('report_tasks', routing_key='report_tasks'),
    Queue('parsing_tasks', routing_key='parsing_tasks'),
    Queue('analysis_tasks', routing_key='analysis_tasks'),
    Queue('query_tasks', routing_key='query_tasks'),
    Queue('generation_tasks', routing_key='generation_tasks'),
)

# 其他配置
worker_prefetch_multiplier = 1
task_acks_late = True
```

### 6.2 Redis存储优化
```python
# 使用Redis的Hash结构存储任务状态
# 使用Redis的Sorted Set存储任务队列
# 设置合理的过期时间避免内存泄漏
```

### 6.3 监控集成
```python
# 集成Prometheus监控
# 使用Celery的事件系统
# 配置日志收集和分析
```

## 7. 部署建议

### 7.1 服务部署架构
```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│   Web Server    │    │  Celery Workers  │    │   Redis/Database   │
│                 │    │                  │    │                    │
│  FastAPI App    │    │  Report Workers  │    │  Redis Cluster     │
│  (Gunicorn)     │    │  Analysis Workers│    │  PostgreSQL        │
│                 │    │  Query Workers   │    │                    │
└─────────────────┘    └──────────────────┘    └────────────────────┘
        │                       │                         │
        └───────────────────────┼─────────────────────────┘
                                ▼
                     ┌──────────────────┐
                     │  Load Balancer   │
                     └──────────────────┘
```

### 7.2 扩展性考虑
- 根据任务类型动态扩展不同类型的Worker
- 使用Kubernetes进行容器化部署
- 配置自动扩缩容策略

这个设计文档提供了一个完整的AI数据分析-报告生成体系的实现方案，能够满足您对精细化任务处理和实时监控的需求。