# 基于 Agent 的表结构分析使用示例

## 概述

本文档展示了如何使用基于 AI Agent 的表结构分析功能，包括表关系分析、业务语义识别和数据质量评估。

## 基本使用

### 1. 初始化服务

```python
from sqlalchemy.orm import Session
from app.services.schema_management import SchemaAnalysisService

# 创建数据库会话
db_session = Session()

# 创建表结构分析服务
schema_analysis_service = SchemaAnalysisService(db_session)
```

### 2. 表关系分析

```python
# 分析表之间的关系
result = await schema_analysis_service.analyze_table_relationships(data_source_id)

if result["success"]:
    print(f"发现 {result['relationships_count']} 个表关系")
    
    # 显示关系详情
    for rel in result["relationships"]:
        print(f"关系: {rel['source_column']} -> {rel['target_column']}")
        print(f"类型: {rel['type']}")
        print(f"置信度: {rel['confidence']}")
        print(f"描述: {rel['description']}")
    
    # 显示 AI 洞察
    for insight in result["agent_insights"]:
        print(f"AI 洞察: {insight}")
else:
    print(f"分析失败: {result['error']}")
```

### 3. 业务语义分析

```python
# 分析业务语义
result = await schema_analysis_service.analyze_business_semantics(data_source_id)

if result["success"]:
    analysis = result["analysis"]
    
    # 显示业务分类
    print("业务分类:")
    for category, tables in analysis["business_categories"].items():
        print(f"  {category}: {len(tables)} 个表")
    
    # 显示语义模式
    print("语义模式:")
    for pattern, details in analysis["semantic_patterns"].items():
        print(f"  {pattern}: {details}")
    
    # 显示领域洞察
    print("领域洞察:")
    for insight in analysis["domain_insights"]:
        print(f"  - {insight}")
else:
    print(f"分析失败: {result['error']}")
```

### 4. 数据质量分析

```python
# 分析数据质量
result = await schema_analysis_service.analyze_data_quality(data_source_id)

if result["success"]:
    analysis = result["analysis"]
    
    print(f"总体质量评分: {analysis['overall_score']:.1f}/100")
    
    # 显示表质量详情
    print("表质量详情:")
    for table_quality in analysis["table_quality"]:
        print(f"  表: {table_quality['table_name']}")
        print(f"    评分: {table_quality['score']:.1f}/100")
        print(f"    因素: {', '.join(table_quality['factors'])}")
        
        # 显示 AI 洞察
        if 'ai_insights' in table_quality:
            for insight in table_quality['ai_insights']:
                print(f"    AI 洞察: {insight}")
    
    # 显示建议
    print("改进建议:")
    for recommendation in analysis["recommendations"]:
        print(f"  - {recommendation}")
    
    # 显示最佳实践
    if "best_practices" in analysis:
        print("最佳实践:")
        for practice in analysis["best_practices"]:
            print(f"  - {practice}")
else:
    print(f"分析失败: {result['error']}")
```

## 高级使用

### 1. 直接使用 SchemaAnalysisAgent

```python
from app.services.agents import SchemaAnalysisAgent

# 创建专门的表结构分析 Agent
agent = SchemaAnalysisAgent(db_session)

# 准备表结构数据
schema_data = {
    "tables": [
        {
            "table_name": "users",
            "business_category": "用户管理",
            "estimated_row_count": 10000,
            "columns": [
                {
                    "column_name": "user_id",
                    "data_type": "int",
                    "is_primary_key": True,
                    "is_nullable": False,
                    "business_name": "用户ID",
                    "semantic_category": "ID标识"
                },
                {
                    "column_name": "username",
                    "data_type": "varchar",
                    "is_primary_key": False,
                    "is_nullable": False,
                    "business_name": "用户名",
                    "semantic_category": "名称"
                }
            ]
        }
    ],
    "total_tables": 1,
    "analysis_context": "表关系分析"
}

# 构建分析提示
analysis_prompt = """
请分析以下数据库表结构，识别表之间的潜在关系：

数据库包含 1 个表：

表名: users
业务分类: 用户管理
预估行数: 10000
列信息:
  - user_id (int) [主键] [业务名: 用户ID] [语义: ID标识]
  - username (varchar) [业务名: 用户名] [语义: 名称]

请分析并返回以下信息：
1. 表之间的外键关系（基于命名约定和业务逻辑）
2. 业务实体关系（如用户-订单、产品-库存等）
3. 数据流向关系（如日志表、配置表等）
4. 关系置信度和建议
5. 潜在的数据模型优化建议

请以JSON格式返回分析结果。
"""

# 执行分析
result = await agent.analyze_schema_relationships(schema_data, analysis_prompt)

print("关系分析结果:")
for rel in result["relationships"]:
    print(f"  {rel}")

print("AI 洞察:")
for insight in result["insights"]:
    print(f"  - {insight}")
```

### 2. 获取分析摘要

```python
# 获取表结构分析摘要
summary = await agent.get_analysis_summary(schema_data)

print(f"数据库概览:")
print(f"  表数量: {summary['table_count']}")
print(f"  总列数: {summary['total_columns']}")

print(f"分析摘要:")
print(summary['summary'])
```

### 3. 批量分析多个数据源

```python
async def analyze_multiple_data_sources(data_source_ids: List[str]):
    """批量分析多个数据源"""
    
    results = {}
    
    for data_source_id in data_source_ids:
        print(f"分析数据源: {data_source_id}")
        
        # 表关系分析
        relationship_result = await schema_analysis_service.analyze_table_relationships(data_source_id)
        
        # 业务语义分析
        semantic_result = await schema_analysis_service.analyze_business_semantics(data_source_id)
        
        # 数据质量分析
        quality_result = await schema_analysis_service.analyze_data_quality(data_source_id)
        
        results[data_source_id] = {
            "relationships": relationship_result,
            "semantics": semantic_result,
            "quality": quality_result
        }
    
    return results

# 使用示例
data_source_ids = ["ds_001", "ds_002", "ds_003"]
results = await analyze_multiple_data_sources(data_source_ids)

# 生成汇总报告
for data_source_id, result in results.items():
    print(f"\n数据源 {data_source_id} 分析结果:")
    
    if result["relationships"]["success"]:
        print(f"  发现 {result['relationships']['relationships_count']} 个表关系")
    
    if result["semantics"]["success"]:
        print(f"  业务语义分析完成")
    
    if result["quality"]["success"]:
        quality_score = result["quality"]["analysis"]["overall_score"]
        print(f"  数据质量评分: {quality_score:.1f}/100")
```

## 错误处理

### 1. AI 服务异常处理

```python
try:
    result = await schema_analysis_service.analyze_table_relationships(data_source_id)
    
    if not result["success"]:
        # 检查是否是 AI 服务问题
        if "AI分析失败" in result["error"]:
            print("AI 服务不可用，使用传统规则分析")
            # 可以在这里调用传统分析方法
        else:
            print(f"分析失败: {result['error']}")
    
except Exception as e:
    print(f"服务异常: {e}")
    # 记录日志或发送告警
```

### 2. 数据解析异常处理

```python
# 检查 AI 响应格式
if "agent_insights" in result:
    for insight in result["agent_insights"]:
        if "解析失败" in insight:
            print("AI 响应解析失败，使用备用解析方法")
            # 可以在这里实现备用的解析逻辑
```

## 性能优化

### 1. 异步并发分析

```python
import asyncio

async def concurrent_analysis(data_source_id: str):
    """并发执行多种分析"""
    
    # 并发执行三种分析
    tasks = [
        schema_analysis_service.analyze_table_relationships(data_source_id),
        schema_analysis_service.analyze_business_semantics(data_source_id),
        schema_analysis_service.analyze_data_quality(data_source_id)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return {
        "relationships": results[0] if not isinstance(results[0], Exception) else {"success": False, "error": str(results[0])},
        "semantics": results[1] if not isinstance(results[1], Exception) else {"success": False, "error": str(results[1])},
        "quality": results[2] if not isinstance(results[2], Exception) else {"success": False, "error": str(results[2])}
    }
```

### 2. 缓存分析结果

```python
from functools import lru_cache
import hashlib
import json

class CachedSchemaAnalysisService(SchemaAnalysisService):
    """带缓存功能的表结构分析服务"""
    
    def __init__(self, db_session: Session):
        super().__init__(db_session)
        self.cache = {}
    
    def _get_cache_key(self, data_source_id: str, analysis_type: str) -> str:
        """生成缓存键"""
        # 可以基于表结构的哈希值生成缓存键
        table_schemas = self.db_session.query(TableSchema).filter(
            TableSchema.data_source_id == data_source_id
        ).all()
        
        # 简化的缓存键生成
        cache_data = {
            "data_source_id": data_source_id,
            "analysis_type": analysis_type,
            "table_count": len(table_schemas),
            "last_updated": max([ts.updated_at for ts in table_schemas]) if table_schemas else None
        }
        
        return hashlib.md5(json.dumps(cache_data, default=str).encode()).hexdigest()
    
    async def analyze_table_relationships(self, data_source_id: str) -> Dict[str, Any]:
        """带缓存的表关系分析"""
        
        cache_key = self._get_cache_key(data_source_id, "relationships")
        
        # 检查缓存
        if cache_key in self.cache:
            print("使用缓存的分析结果")
            return self.cache[cache_key]
        
        # 执行分析
        result = await super().analyze_table_relationships(data_source_id)
        
        # 缓存结果
        if result["success"]:
            self.cache[cache_key] = result
        
        return result
```

## 监控和日志

### 1. 性能监控

```python
import time
from app.core.monitoring import PerformanceMonitor

class MonitoredSchemaAnalysisService(SchemaAnalysisService):
    """带性能监控的表结构分析服务"""
    
    def __init__(self, db_session: Session):
        super().__init__(db_session)
        self.monitor = PerformanceMonitor()
    
    async def analyze_table_relationships(self, data_source_id: str) -> Dict[str, Any]:
        """带性能监控的表关系分析"""
        
        start_time = time.time()
        
        try:
            result = await super().analyze_table_relationships(data_source_id)
            
            # 记录性能指标
            execution_time = time.time() - start_time
            self.monitor.record_metric(
                "schema_analysis.relationships.execution_time",
                execution_time,
                tags={"data_source_id": data_source_id, "success": result["success"]}
            )
            
            return result
            
        except Exception as e:
            # 记录错误指标
            execution_time = time.time() - start_time
            self.monitor.record_metric(
                "schema_analysis.relationships.error_count",
                1,
                tags={"data_source_id": data_source_id, "error_type": type(e).__name__}
            )
            raise
```

### 2. 详细日志记录

```python
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 在分析过程中记录详细日志
async def analyze_with_logging(data_source_id: str):
    logger.info(f"开始分析数据源: {data_source_id}")
    
    # 记录分析步骤
    logger.info("步骤 1: 获取表结构信息")
    table_schemas = schema_analysis_service.db_session.query(TableSchema).filter(
        TableSchema.data_source_id == data_source_id
    ).all()
    logger.info(f"获取到 {len(table_schemas)} 个表")
    
    # 记录 AI 分析
    logger.info("步骤 2: 执行 AI Agent 分析")
    result = await schema_analysis_service.analyze_table_relationships(data_source_id)
    
    if result["success"]:
        logger.info(f"分析成功，发现 {result['relationships_count']} 个关系")
        for insight in result.get("agent_insights", []):
            logger.info(f"AI 洞察: {insight}")
    else:
        logger.error(f"分析失败: {result['error']}")
    
    return result
```

## 最佳实践

1. **错误处理**: 始终检查分析结果的 `success` 字段
2. **性能优化**: 对于大型数据库，考虑分批分析或使用缓存
3. **监控**: 记录分析性能和错误率
4. **日志**: 记录详细的分析过程，便于调试
5. **备用方案**: 当 AI 服务不可用时，使用传统规则分析
6. **数据验证**: 验证 AI 分析结果的合理性
7. **定期更新**: 定期刷新表结构信息和分析结果
