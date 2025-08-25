# 占位符SQL构建Agent集成指南

## 架构概述

新的占位符SQL构建Agent是一个独立的、基于上下文工程设计的智能分析系统，专门负责：

1. **语义分析**：深度理解占位符的业务含义
2. **智能SQL生成**：基于表结构和语义分析生成准确的SQL查询
3. **上下文感知**：充分利用数据库表结构信息和业务上下文
4. **任务集成**：支持任务板块和模版占位符分析板块的调用

## 核心组件

### 1. 占位符语义分析器 (`semantic_analyzer.py`)
- 专门识别占位符的语义类型（时间、统计、维度等）
- 支持中英文混合分析
- 针对时间相关占位符有特殊处理逻辑

### 2. 智能SQL生成器 (`intelligent_sql_generator.py`)
- 基于语义分析结果生成准确的SQL
- 充分利用存储的表结构信息
- 支持参数化查询和动态条件构建

### 3. 占位符SQL构建Agent (`placeholder_sql_agent.py`)
- 独立的Agent，基于上下文工程设计
- 支持批量分析和单个分析
- 自动存储分析结果到数据库

### 4. 门面服务 (`placeholder_analysis_facade.py`)
- 为不同调用场景提供统一接口
- 支持模版页面和任务执行两种调用模式

## 调用场景

### 场景1：模版页面主动分析

**使用时机**：上传模版后在占位符页面主动调用分析

```python
# API调用
POST /api/v1/placeholder-analysis/templates/{template_id}/placeholders/analyze
{
    "force_reanalyze": false
}

# 直接使用门面服务
from app.services.ai.facades.placeholder_analysis_facade import create_placeholder_analysis_facade

facade = create_placeholder_analysis_facade(db_session)
result = await facade.analyze_template_placeholders(
    template_id="template-123",
    user_id="user-456",
    force_reanalyze=False
)
```

**返回结果**：
```json
{
    "success": true,
    "message": "成功分析 8/10 个占位符",
    "total_count": 10,
    "analyzed_count": 8,
    "failed_count": 2,
    "results": [...],
    "summary": {
        "semantic_types": {"temporal": 3, "statistical": 4, "dimensional": 1},
        "confidence_distribution": {"high": 6, "medium": 2, "low": 0}
    }
}
```

### 场景2：任务执行时检查SQL

**使用时机**：在任务中判断有没有存储的SQL，没有则调用分析，有则直接ETL

```python
# API调用
GET /api/v1/placeholder-analysis/placeholders/{placeholder_id}/sql?task_id=task-123

# 直接使用门面服务
result = await facade.ensure_placeholder_sql_for_task(
    placeholder_id="placeholder-789",
    user_id="user-456", 
    task_id="task-123"
)
```

**业务逻辑**：
1. 首先检查是否已有存储的SQL
2. 如果有，直接返回用于ETL
3. 如果没有，自动调用分析生成SQL
4. 生成后存储到数据库供下次使用

**返回结果**：
```json
{
    "success": true,
    "source": "stored",  // "stored" | "generated"
    "sql": "SELECT COUNT(*) AS total_count FROM ods_guide WHERE region = {region}",
    "confidence": 0.9,
    "target_table": "ods_guide"
}
```

## 分析能力示例

### 时间相关占位符
```
输入："周期:统计开始日期"
分析结果：
- 语义类型：temporal
- 子类型：start_date  
- 生成SQL：SELECT MIN(dt) as start_date FROM target_table
- 置信度：0.9
```

### 统计相关占位符
```
输入："用户去重总数"
分析结果：
- 语义类型：statistical
- 子类型：count
- 生成SQL：SELECT COUNT(DISTINCT user_id) AS distinct_count FROM target_table
- 置信度：0.85
```

### 维度相关占位符
```
输入："地区分布"
分析结果：
- 语义类型：dimensional
- 子类型：region
- 生成SQL：SELECT DISTINCT region_name FROM target_table ORDER BY region_name
- 置信度：0.8
```

## API端点总览

### 模版相关
- `POST /api/v1/placeholder-analysis/templates/{template_id}/placeholders/analyze` - 分析模版占位符
- `GET /api/v1/placeholder-analysis/templates/{template_id}/placeholders/status` - 获取模版占位符状态

### 任务相关  
- `POST /api/v1/placeholder-analysis/tasks/placeholders/check` - 批量检查任务占位符
- `GET /api/v1/placeholder-analysis/placeholders/{placeholder_id}/sql` - 获取占位符SQL

### 单个操作
- `POST /api/v1/placeholder-analysis/placeholders/{placeholder_id}/analyze` - 分析单个占位符
- `GET /api/v1/placeholder-analysis/placeholders/{placeholder_id}/status` - 获取占位符状态

### 批量操作
- `POST /api/v1/placeholder-analysis/placeholders/batch-analyze` - 批量分析占位符

### 系统状态
- `GET /api/v1/placeholder-analysis/system/placeholder-analysis/stats` - 获取系统统计信息

## 集成步骤

### 1. 注册路由
在 `app/api/api.py` 中添加：

```python
from app.api.endpoints import placeholder_analysis

api_router.include_router(
    placeholder_analysis.router, 
    prefix="/placeholder-analysis", 
    tags=["placeholder-analysis"]
)
```

### 2. 前端集成

#### 模版页面
```javascript
// 分析模版占位符
const analyzeTemplatePlaceholders = async (templateId, forceReanalyze = false) => {
  const response = await fetch(`/api/v1/placeholder-analysis/templates/${templateId}/placeholders/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force_reanalyze: forceReanalyze })
  });
  return await response.json();
};

// 获取占位符状态
const getPlaceholderStatus = async (templateId) => {
  const response = await fetch(`/api/v1/placeholder-analysis/templates/${templateId}/placeholders/status`);
  return await response.json();
};
```

#### 任务执行页面
```javascript
// 检查任务占位符SQL
const checkTaskPlaceholders = async (placeholderIds, taskId) => {
  const response = await fetch('/api/v1/placeholder-analysis/tasks/placeholders/check', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ placeholder_ids: placeholderIds, task_id: taskId })
  });
  return await response.json();
};

// 获取占位符SQL用于ETL
const getPlaceholderSql = async (placeholderId, taskId) => {
  const response = await fetch(`/api/v1/placeholder-analysis/placeholders/${placeholderId}/sql?task_id=${taskId}`);
  return await response.json();
};
```

### 3. 任务流程集成

```python
# 在任务执行前检查占位符SQL
async def prepare_task_placeholders(task_id: str, placeholder_ids: List[str], user_id: str):
    facade = create_placeholder_analysis_facade(db)
    
    result = await facade.batch_ensure_placeholders_sql_for_task(
        placeholder_ids=placeholder_ids,
        user_id=user_id,
        task_id=task_id
    )
    
    if not result['all_ready']:
        # 有占位符还没有SQL，需要提示用户先分析
        need_analysis = [r for r in result['results'] if r.get('needs_analysis')]
        raise Exception(f"有 {len(need_analysis)} 个占位符需要先进行分析")
    
    # 所有占位符都已准备就绪，可以开始ETL
    return result
```

## 性能特点

1. **智能缓存**：分析结果自动存储到数据库，避免重复分析
2. **批量处理**：支持批量分析多个占位符，提高效率
3. **增量分析**：只分析变更的占位符，节省计算资源
4. **上下文复用**：充分利用已有的表结构信息，减少数据库查询

## 故障处理

1. **分析失败**：系统会自动回退到基础SQL模板
2. **数据源缺失**：会提示用户检查数据源配置
3. **表结构缺失**：会建议用户先进行表结构扫描

## 监控指标

- 占位符分析成功率
- 平均分析时间
- SQL生成置信度分布
- 语义类型分布统计

## 扩展能力

系统设计支持：
- 新增语义类型识别
- 自定义SQL模板
- 多语言占位符支持
- AI模型集成增强

通过这个新的Agent系统，占位符分析的准确率和用户体验都将得到显著提升，特别是对于时间相关占位符的处理将更加准确和智能。