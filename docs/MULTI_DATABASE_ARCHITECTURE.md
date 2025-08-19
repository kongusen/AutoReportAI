# 多库多表架构设计

## 📊 架构概述

针对企业级数据环境中一个数据源包含多个数据库，每个数据库又包含多张表的复杂场景，我们设计了一个层次化的数据组织架构。

## 🏗️ 数据层次结构

```
DataSource (数据源)
├── Database (数据库)
│   ├── Table (表)
│   │   ├── Column (字段)
│   │   └── Index (索引)
│   └── View (视图)
└── CrossDatabaseRelation (跨库关系)
```

## 📋 核心模型设计

### 1. 扩展DataSource模型

当前DataSource模型需要扩展以支持多数据库：

```python
class DataSource(Base):
    # 现有字段...
    
    # 移除单一数据库配置
    # doris_database = Column(String, nullable=True)  # 删除此字段
    
    # 添加多数据库支持
    default_database = Column(String, nullable=True)  # 默认数据库
    database_discovery_enabled = Column(Boolean, default=True)  # 启用数据库发现
    
    # 关系
    databases = relationship("Database", back_populates="data_source", cascade="all, delete-orphan")
```

### 2. Database模型（已在table_schema.py中定义）

每个数据源可以包含多个数据库：

```python
class Database(Base):
    __tablename__ = "databases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    
    # 数据源关联
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False)
    
    # 统计信息
    table_count = Column(Integer, default=0)
    total_size_mb = Column(BigInteger, default=0)
    
    # 业务分类
    business_domain = Column(String, nullable=True)  # 业务域：finance, hr, sales等
    data_sensitivity = Column(String, nullable=True)  # 敏感度级别
```

### 3. Agent访问机制设计

#### 3.1 分层访问策略

```python
class DatabaseAccessStrategy:
    """数据库访问策略"""
    
    def __init__(self, data_source_id: str):
        self.data_source_id = data_source_id
        self.access_cache = {}  # 访问缓存
        
    async def discover_databases(self) -> List[Database]:
        """发现数据源中的所有数据库"""
        pass
        
    async def get_database_by_domain(self, domain: str) -> Optional[Database]:
        """根据业务域获取数据库"""
        pass
        
    async def get_table_by_semantic(self, semantic: str) -> List[Table]:
        """根据语义搜索表"""
        pass
```

#### 3.2 智能路由机制

```python
class DatabaseRouter:
    """数据库查询路由器"""
    
    async def route_query(self, query_intent: str, context: Dict) -> QueryPlan:
        """
        根据查询意图智能路由到合适的数据库和表
        
        Args:
            query_intent: 查询意图，如 "用户订单统计"
            context: 上下文信息
            
        Returns:
            包含数据库、表和查询计划的对象
        """
        
        # 1. 意图解析
        parsed_intent = await self.parse_intent(query_intent)
        
        # 2. 表发现
        candidate_tables = await self.discover_relevant_tables(parsed_intent)
        
        # 3. 关系推理
        table_relations = await self.infer_table_relations(candidate_tables)
        
        # 4. 查询计划生成
        return await self.generate_query_plan(candidate_tables, table_relations)
```

## 🔄 数据发现与同步机制

### 1. 元数据发现服务

```python
class MetadataDiscoveryService:
    """元数据发现服务"""
    
    async def discover_databases(self, data_source: DataSource) -> List[Database]:
        """发现数据源中的所有数据库"""
        
    async def discover_tables(self, database: Database) -> List[Table]:
        """发现数据库中的所有表"""
        
    async def discover_columns(self, table: Table) -> List[TableColumn]:
        """发现表中的所有字段"""
        
    async def infer_relations(self, tables: List[Table]) -> List[TableRelation]:
        """推理表间关系"""
```

### 2. 增量同步机制

```python
class MetadataSyncService:
    """元数据同步服务"""
    
    async def sync_metadata(self, data_source_id: str, mode: str = "incremental"):
        """同步元数据"""
        
        if mode == "full":
            await self.full_sync(data_source_id)
        else:
            await self.incremental_sync(data_source_id)
    
    async def detect_schema_changes(self, database: Database) -> List[SchemaChange]:
        """检测数据库结构变化"""
        pass
```

## 🤖 Agent智能访问机制

### 1. 语义理解层

```python
class SemanticUnderstanding:
    """语义理解组件"""
    
    async def understand_query(self, natural_query: str) -> QueryContext:
        """理解自然语言查询"""
        
        # 1. 实体识别
        entities = await self.extract_entities(natural_query)
        
        # 2. 意图分类
        intent = await self.classify_intent(natural_query)
        
        # 3. 表映射
        relevant_tables = await self.map_to_tables(entities, intent)
        
        return QueryContext(entities=entities, intent=intent, tables=relevant_tables)
```

### 2. 查询规划器

```python
class QueryPlanner:
    """查询规划器"""
    
    async def plan_query(self, context: QueryContext) -> ExecutionPlan:
        """制定查询执行计划"""
        
        # 1. 表选择
        selected_tables = await self.select_tables(context.tables)
        
        # 2. JOIN策略
        join_strategy = await self.plan_joins(selected_tables)
        
        # 3. 查询优化
        optimized_plan = await self.optimize_query(selected_tables, join_strategy)
        
        return ExecutionPlan(
            tables=selected_tables,
            joins=join_strategy,
            execution_order=optimized_plan
        )
```

### 3. 执行引擎

```python
class CrossDatabaseExecutor:
    """跨数据库执行引擎"""
    
    async def execute_plan(self, plan: ExecutionPlan) -> QueryResult:
        """执行查询计划"""
        
        results = []
        
        # 按数据库分组执行
        for database_id, table_group in self.group_by_database(plan.tables):
            db_result = await self.execute_database_query(database_id, table_group)
            results.append(db_result)
        
        # 跨库数据合并
        if len(results) > 1:
            return await self.merge_cross_database_results(results)
        else:
            return results[0]
```

## 📊 使用示例

### 场景1：Agent查询用户订单信息

```python
# Agent接收到查询：
user_query = "查询最近30天VIP用户的订单统计"

# 1. 语义理解
context = await semantic_understanding.understand_query(user_query)
# 识别实体: ["VIP用户", "订单", "最近30天"]
# 识别意图: "统计查询"
# 相关表: ["user_database.users", "order_database.orders"]

# 2. 查询规划
plan = await query_planner.plan_query(context)
# 选择表: users (user_database), orders (order_database)
# JOIN策略: users.id = orders.user_id
# 过滤条件: users.level = 'VIP' AND orders.created_at >= NOW() - INTERVAL 30 DAY

# 3. 执行查询
result = await executor.execute_plan(plan)
```

### 场景2：跨库关联分析

```python
# Agent需要关联多个数据库的数据
query = "分析人力资源数据库中的员工绩效与销售数据库中的业绩关联"

# 涉及数据库:
# - hr_database.employees
# - hr_database.performance_reviews  
# - sales_database.sales_records

# 跨库JOIN策略:
# 1. 先在各自数据库内完成聚合
# 2. 通过employee_id进行跨库关联
# 3. 在应用层完成最终结果合并
```

## 🔧 配置管理

### 1. 数据源配置

```yaml
# datasource_config.yaml
data_sources:
  company_data:
    type: doris
    connection:
      hosts: ["192.168.61.30"]
      port: 9030
      username: root
      password: encrypted_password
    databases:
      - name: user_db
        display_name: "用户数据库"
        business_domain: "user_management"
        tables:
          - users
          - user_profiles
          - user_sessions
      - name: order_db
        display_name: "订单数据库"
        business_domain: "transaction"
        tables:
          - orders
          - order_items
          - payments
```

### 2. Agent配置

```python
agent_config = {
    "database_access": {
        "max_concurrent_connections": 10,
        "query_timeout": 30,
        "enable_cross_database_joins": True,
        "cache_metadata": True,
        "cache_ttl": 3600
    },
    "semantic_understanding": {
        "enable_entity_recognition": True,
        "enable_intent_classification": True,
        "confidence_threshold": 0.8
    }
}
```

## 📈 性能优化策略

### 1. 元数据缓存
- Redis缓存热点表结构
- 本地缓存表关系
- 智能预加载相关表信息

### 2. 查询优化
- 谓词下推到各数据库
- 结果集大小预估
- 自适应JOIN策略选择

### 3. 并发控制
- 数据库连接池管理
- 查询负载均衡
- 慢查询监控和优化

## 🔒 安全与权限

### 1. 数据权限控制
```python
class DatabasePermissionManager:
    async def check_table_access(self, user_id: str, table_id: str) -> bool:
        """检查用户对表的访问权限"""
        
    async def get_accessible_databases(self, user_id: str) -> List[Database]:
        """获取用户可访问的数据库列表"""
```

### 2. 敏感数据保护
- 字段级别的敏感度标记
- 查询结果脱敏
- 审计日志记录

这个架构设计为Agent提供了强大的多库多表访问能力，支持智能查询路由、跨库关联分析，同时保证了性能和安全性。