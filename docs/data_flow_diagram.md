# AutoReportAI 数据流转图

## 系统数据流转总览

```mermaid
graph TD
    %% 数据输入源
    subgraph "数据输入源 (Data Sources)"
        UI[用户输入<br/>模板/配置/需求]
        EXT_DB[(外部数据库<br/>Doris/MySQL/PostgreSQL)]
        FILES[文件上传<br/>CSV/Excel/JSON]
        API_DATA[API数据源<br/>RESTful APIs]
    end
    
    %% 数据接收层
    subgraph "数据接收层 (Data Reception Layer)"
        API_GATEWAY[API网关<br/>FastAPI Router]
        FILE_HANDLER[文件处理器<br/>FileHandler]
        WS_MANAGER[WebSocket管理器<br/>实时数据流]
    end
    
    %% 数据预处理
    subgraph "数据预处理层 (Data Preprocessing)"
        VALIDATOR[数据验证器<br/>DataValidator]
        NORMALIZER[数据标准化器<br/>DataNormalizer]
        PARSER[数据解析器<br/>DataParser]
        SANITIZER[数据清洗器<br/>DataSanitizer]
    end
    
    %% 智能处理层
    subgraph "智能处理层 (Intelligent Processing)"
        REACT_AGENT[React智能代理<br/>ReactAgent]
        LLM_SELECTOR[LLM智能选择器<br/>用户个性化模型选择]
        CONTEXT_ENGINE[上下文分析引擎<br/>ContextAnalysisEngine]
        PLACEHOLDER_AI[占位符智能分析<br/>PlaceholderAI]
    end
    
    %% 业务处理层
    subgraph "业务处理层 (Business Processing)"
        TEMPLATE_SERVICE[模板服务<br/>TemplateService]
        PLACEHOLDER_SERVICE[占位符服务<br/>PlaceholderService]
        DATA_ANALYSIS[数据分析服务<br/>DataAnalysisService]
        SCHEMA_SERVICE[Schema服务<br/>SchemaService]
    end
    
    %% 数据存储层
    subgraph "数据存储层 (Data Storage)"
        MAIN_DB[(PostgreSQL<br/>主数据库)]
        CACHE_DB[(Redis<br/>缓存数据库)]
        FILE_STORAGE[(MinIO<br/>文件存储)]
        VECTOR_DB[(向量数据库<br/>embeddings)]
    end
    
    %% 数据输出层
    subgraph "数据输出层 (Data Output)"
        REPORT_GEN[报告生成器<br/>ReportGenerator]
        WORD_GEN[Word生成器<br/>WordGenerator]
        CHART_GEN[图表生成器<br/>ChartGenerator]
        API_RESPONSE[API响应<br/>JSON/XML]
    end
    
    %% 数据消费端
    subgraph "数据消费端 (Data Consumers)"
        WEB_UI[Web界面<br/>用户展示]
        DOWNLOAD[文件下载<br/>报告文档]
        EXTERNAL_API[外部API<br/>第三方集成]
        NOTIFICATION[通知推送<br/>邮件/WebSocket]
    end
    
    %% 数据流连接
    UI --> API_GATEWAY
    EXT_DB --> API_GATEWAY
    FILES --> FILE_HANDLER
    API_DATA --> API_GATEWAY
    
    API_GATEWAY --> VALIDATOR
    FILE_HANDLER --> VALIDATOR
    WS_MANAGER --> VALIDATOR
    
    VALIDATOR --> NORMALIZER
    NORMALIZER --> PARSER
    PARSER --> SANITIZER
    
    SANITIZER --> REACT_AGENT
    REACT_AGENT --> LLM_SELECTOR
    REACT_AGENT --> CONTEXT_ENGINE
    REACT_AGENT --> PLACEHOLDER_AI
    
    CONTEXT_ENGINE --> TEMPLATE_SERVICE
    PLACEHOLDER_AI --> PLACEHOLDER_SERVICE
    LLM_SELECTOR --> DATA_ANALYSIS
    
    TEMPLATE_SERVICE --> MAIN_DB
    PLACEHOLDER_SERVICE --> MAIN_DB
    DATA_ANALYSIS --> SCHEMA_SERVICE
    
    %% 缓存流
    TEMPLATE_SERVICE -.-> CACHE_DB
    PLACEHOLDER_SERVICE -.-> CACHE_DB
    DATA_ANALYSIS -.-> CACHE_DB
    
    %% 文件存储流
    FILE_HANDLER --> FILE_STORAGE
    REPORT_GEN --> FILE_STORAGE
    
    %% 向量存储流
    CONTEXT_ENGINE -.-> VECTOR_DB
    PLACEHOLDER_AI -.-> VECTOR_DB
    
    %% 输出流
    MAIN_DB --> REPORT_GEN
    CACHE_DB --> REPORT_GEN
    FILE_STORAGE --> REPORT_GEN
    
    REPORT_GEN --> WORD_GEN
    REPORT_GEN --> CHART_GEN
    REPORT_GEN --> API_RESPONSE
    
    WORD_GEN --> WEB_UI
    CHART_GEN --> WEB_UI
    API_RESPONSE --> WEB_UI
    
    WORD_GEN --> DOWNLOAD
    CHART_GEN --> DOWNLOAD
    
    API_RESPONSE --> EXTERNAL_API
    WS_MANAGER --> NOTIFICATION
    
    %% 样式定义
    classDef inputLayer fill:#e3f2fd
    classDef receptionLayer fill:#f1f8e9
    classDef preprocessLayer fill:#fff3e0
    classDef intelligentLayer fill:#fce4ec
    classDef businessLayer fill:#f3e5f5
    classDef storageLayer fill:#e8eaf6
    classDef outputLayer fill:#e0f2f1
    classDef consumerLayer fill:#fafafa
    
    class UI,EXT_DB,FILES,API_DATA inputLayer
    class API_GATEWAY,FILE_HANDLER,WS_MANAGER receptionLayer
    class VALIDATOR,NORMALIZER,PARSER,SANITIZER preprocessLayer
    class REACT_AGENT,LLM_SELECTOR,CONTEXT_ENGINE,PLACEHOLDER_AI intelligentLayer
    class TEMPLATE_SERVICE,PLACEHOLDER_SERVICE,DATA_ANALYSIS,SCHEMA_SERVICE businessLayer
    class MAIN_DB,CACHE_DB,FILE_STORAGE,VECTOR_DB storageLayer
    class REPORT_GEN,WORD_GEN,CHART_GEN,API_RESPONSE outputLayer
    class WEB_UI,DOWNLOAD,EXTERNAL_API,NOTIFICATION consumerLayer
```

## 详细数据流转说明

### 1. 数据输入阶段 (Data Input Stage)

```mermaid
sequenceDiagram
    participant U as 用户
    participant API as API网关
    participant V as 数据验证器
    participant N as 标准化器
    participant DB as 主数据库
    
    U->>API: 提交模板/数据请求
    API->>V: 验证数据格式
    V->>V: 数据完整性检查
    V->>N: 数据标准化
    N->>N: 格式统一化处理
    N->>DB: 存储验证后的数据
    DB-->>API: 返回处理结果
    API-->>U: 响应处理状态
```

### 2. 智能处理阶段 (Intelligent Processing Stage)

```mermaid
sequenceDiagram
    participant API as API网关
    participant RA as ReactAgent
    participant LLM as LLM选择器
    participant CE as 上下文引擎
    participant PA as 占位符AI
    participant Cache as 缓存系统
    
    API->>RA: 提交处理任务
    RA->>LLM: 请求最佳模型
    LLM->>LLM: 基于用户偏好选择
    LLM-->>RA: 返回选定模型
    RA->>CE: 构建处理上下文
    CE->>Cache: 检查上下文缓存
    Cache-->>CE: 返回缓存结果
    RA->>PA: 智能分析占位符
    PA->>PA: 语义理解+SQL生成
    PA-->>RA: 返回分析结果
    RA-->>API: 返回处理结果
```

### 3. 业务处理阶段 (Business Processing Stage)

```mermaid
sequenceDiagram
    participant RA as ReactAgent
    participant TS as 模板服务
    participant PS as 占位符服务
    participant AS as 数据分析服务
    participant SS as Schema服务
    participant DB as 主数据库
    participant Redis as 缓存
    
    RA->>TS: 处理模板请求
    TS->>PS: 分析模板占位符
    PS->>SS: 获取Schema信息
    SS->>DB: 查询表结构
    DB-->>SS: 返回Schema
    SS-->>PS: 返回分析结果
    PS->>AS: 执行数据分析
    AS->>DB: 执行查询
    DB-->>AS: 返回数据结果
    AS->>Redis: 缓存分析结果
    AS-->>PS: 返回处理结果
    PS-->>TS: 返回占位符数据
    TS-->>RA: 返回完整模板
```

### 4. 数据输出阶段 (Data Output Stage)

```mermaid
sequenceDiagram
    participant TS as 模板服务
    participant RG as 报告生成器
    participant WG as Word生成器
    participant CG as 图表生成器
    participant FS as 文件存储
    participant UI as Web界面
    participant WS as WebSocket
    
    TS->>RG: 提交报告生成任务
    RG->>WG: 生成Word文档
    RG->>CG: 生成数据图表
    WG->>FS: 保存Word文件
    CG->>FS: 保存图表文件
    FS-->>WG: 确认保存
    FS-->>CG: 确认保存
    WG-->>RG: 返回文件路径
    CG-->>RG: 返回图表路径
    RG->>WS: 推送完成通知
    RG-->>UI: 返回生成结果
    WS-->>UI: 实时状态更新
```

## 关键数据流转节点

### 1. 用户个性化数据流

```mermaid
graph LR
    subgraph "用户个性化流程"
        USER[用户请求] --> AUTH[身份认证]
        AUTH --> PROFILE[用户配置加载]
        PROFILE --> LLM_PREF[LLM偏好选择]
        LLM_PREF --> CONTEXT[个性化上下文]
        CONTEXT --> PROCESSING[个性化处理]
        PROCESSING --> RESULT[个性化结果]
    end
    
    classDef userFlow fill:#e1f5fe
    class USER,AUTH,PROFILE,LLM_PREF,CONTEXT,PROCESSING,RESULT userFlow
```

### 2. 缓存数据流

```mermaid
graph TB
    subgraph "多层缓存架构"
        REQUEST[请求] --> L1[L1: 内存缓存<br/>热点数据]
        L1 --> L2[L2: Redis缓存<br/>共享数据]
        L2 --> L3[L3: 数据库<br/>持久化数据]
        
        L1 -.->|缓存未命中| L2
        L2 -.->|缓存未命中| L3
        L3 -.->|数据回填| L2
        L2 -.->|数据回填| L1
    end
    
    classDef cacheFlow fill:#f3e5f5
    class REQUEST,L1,L2,L3 cacheFlow
```

### 3. 实时数据流

```mermaid
graph LR
    subgraph "实时数据处理"
        WS_IN[WebSocket输入] --> STREAM[数据流处理]
        STREAM --> BUFFER[缓冲队列]
        BUFFER --> BATCH[批处理]
        BATCH --> UPDATE[实时更新]
        UPDATE --> WS_OUT[WebSocket推送]
    end
    
    classDef realtimeFlow fill:#e8f5e8
    class WS_IN,STREAM,BUFFER,BATCH,UPDATE,WS_OUT realtimeFlow
```

## 数据一致性保证

### 1. 事务管理
- **ACID事务**: 关键业务操作使用数据库事务
- **分布式事务**: 跨服务操作使用补偿模式
- **最终一致性**: 缓存更新采用最终一致性

### 2. 数据同步
- **主从同步**: PostgreSQL主从复制
- **缓存同步**: Redis与数据库的延迟同步
- **文件同步**: MinIO分布式存储同步

### 3. 错误恢复
- **重试机制**: 网络错误自动重试
- **降级策略**: 服务不可用时的降级处理
- **数据修复**: 定期数据一致性检查和修复

## 性能优化策略

### 1. 数据预加载
- **预热缓存**: 系统启动时预加载热点数据
- **预测缓存**: 基于用户行为预测数据需求
- **批量加载**: 批量加载相关数据减少IO

### 2. 并发处理
- **异步处理**: 非阻塞的异步数据处理
- **并行计算**: 多核并行处理大数据集
- **流水线**: 数据处理流水线优化

### 3. 智能优化
- **AI预测**: 使用AI预测数据访问模式
- **动态调整**: 根据负载动态调整缓存策略
- **自动优化**: 自动SQL查询优化和索引建议

这个数据流转图展现了AutoReportAI系统中数据的完整生命周期，从输入、处理、存储到输出的全链路数据流转过程，体现了智能化、个性化和高性能的数据处理架构。