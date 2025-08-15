# 表结构管理系统

## 概述

表结构管理系统是 AutoReportAI 的核心组件之一，负责发现、存储、分析和查询数据源的表结构信息。该系统提供了完整的表结构元数据管理功能，支持智能数据分析和查询优化。

## 系统架构

### 核心模块

1. **SchemaDiscoveryService** - 表结构发现服务
   - 负责从数据源发现表结构信息
   - 支持多种数据源类型（目前支持 Doris）
   - 自动存储表结构和列信息到数据库

2. **SchemaAnalysisService** - 表结构分析服务
   - 分析表之间的关系和依赖
   - 识别业务语义和数据质量
   - 生成优化建议

3. **SchemaQueryService** - 表结构查询服务
   - 提供表结构信息的查询接口
   - 支持搜索和过滤功能
   - 生成统计信息

4. **SchemaMetadataService** - 表结构元数据服务
   - 管理业务语义信息
   - 支持元数据的导入导出
   - 批量更新功能

### 工具类

1. **TypeNormalizer** - 数据类型标准化工具
   - 将不同数据库的数据类型标准化
   - 提供类型分类和判断功能

2. **RelationshipAnalyzer** - 表关系分析工具
   - 分析表之间的关联关系
   - 检测循环依赖
   - 生成优化建议

## 数据模型

### TableSchema（表结构）
- 存储表的基本信息和元数据
- 包含业务分类、数据质量评分等
- 关联到数据源和列信息

### ColumnSchema（列结构）
- 存储列的详细信息和约束
- 包含数据类型、业务语义等
- 支持数据质量统计

### TableRelationship（表关系）
- 存储表之间的关联关系
- 包含关系类型和置信度
- 支持业务描述

## 使用流程

### 1. 表结构发现

```python
from app.services.schema_management import SchemaDiscoveryService

# 创建服务实例
discovery_service = SchemaDiscoveryService(db_session)

# 发现并存储表结构
result = await discovery_service.discover_and_store_schemas(data_source_id)
```

### 2. 表结构分析

```python
from app.services.schema_management import SchemaAnalysisService

# 创建服务实例
analysis_service = SchemaAnalysisService(db_session)

# 分析表关系
relationships = await analysis_service.analyze_table_relationships(data_source_id)

# 分析业务语义
semantics = await analysis_service.analyze_business_semantics(data_source_id)

# 分析数据质量
quality = await analysis_service.analyze_data_quality(data_source_id)
```

### 3. 智能数据分析

```python
from app.services.data_processing import SchemaAwareAnalysisService

# 创建服务实例
schema_aware_service = SchemaAwareAnalysisService(db_session)

# 基于表结构进行智能分析
analysis = await schema_aware_service.analyze_data_source_with_schema(data_source_id)

# 生成查询建议
suggestions = await schema_aware_service.get_optimized_query_suggestions(
    data_source_id, "分析用户订单数据"
)
```

## 功能特性

### 1. 自动表结构发现
- 支持多种数据源类型
- 自动识别表关系和约束
- 智能数据类型标准化

### 2. 业务语义分析
- 基于命名约定的业务分类
- 自动识别字段语义
- 支持自定义业务标签

### 3. 数据质量评估
- 完整性、准确性评分
- 数据模式识别
- 质量改进建议

### 4. 智能查询优化
- 基于表结构的查询建议
- 自动生成统计查询
- 性能优化提示

### 5. 元数据管理
- 支持元数据导入导出
- 批量更新功能
- 版本控制支持

## 扩展性

### 支持新的数据源类型
1. 在 `connectors` 目录下添加新的连接器
2. 实现 `get_all_tables()` 和 `get_table_schema()` 方法
3. 在 `SchemaDiscoveryService` 中添加对应的处理逻辑

### 自定义分析规则
1. 扩展 `SchemaAnalysisService` 的分析方法
2. 添加新的业务语义识别规则
3. 自定义数据质量评估标准

### 集成其他系统
1. 通过 API 接口暴露服务
2. 支持事件驱动的架构
3. 提供 Webhook 回调机制

## 最佳实践

### 1. 定期更新表结构
- 建议定期刷新表结构信息
- 监控表结构变化
- 及时更新业务语义信息

### 2. 合理设置业务分类
- 使用统一的业务分类标准
- 避免过于细粒度的分类
- 定期清理无效分类

### 3. 优化查询性能
- 合理使用索引
- 避免复杂的表关联
- 定期分析查询性能

### 4. 数据质量监控
- 设置数据质量阈值
- 定期生成质量报告
- 及时处理质量问题

## 故障排除

### 常见问题

1. **表结构发现失败**
   - 检查数据源连接配置
   - 确认用户权限
   - 查看错误日志

2. **关系分析不准确**
   - 检查外键约束
   - 验证命名规范
   - 手动调整关系

3. **查询建议不相关**
   - 更新业务语义信息
   - 优化关键词匹配
   - 调整相关性算法

### 调试方法

1. 启用详细日志记录
2. 使用数据库查询工具检查元数据
3. 运行单元测试验证功能

## 未来规划

1. **支持更多数据源类型**
   - MySQL, PostgreSQL, Oracle
   - 云数据库服务
   - 大数据平台

2. **增强分析能力**
   - 机器学习辅助分析
   - 自动优化建议
   - 智能数据治理

3. **改进用户体验**
   - 可视化表结构图
   - 交互式查询构建器
   - 实时监控面板
