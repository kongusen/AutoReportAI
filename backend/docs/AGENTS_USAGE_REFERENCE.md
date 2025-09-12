# Agents 系统使用参考文档

## 概述

本文档详细介绍了 `backend/app/services/infrastructure/agents` 系统的使用方法，包括数据结构、API接口和最佳实践。

## 目录
- [快速开始](#快速开始)
- [核心数据结构](#核心数据结构)
- [Context 上下文系统](#context-上下文系统)
- [Tools 工具系统](#tools-工具系统)
- [模板填充系统](#模板填充系统)
- [Domain 层集成](#domain-层集成)
- [错误处理和恢复](#错误处理和恢复)
- [最佳实践](#最佳实践)
- [示例代码](#示例代码)

---

## 快速开始

### 基础导入

```python
from app.services.infrastructure.agents import (
    # 核心函数
    execute_agent_task,
    get_agent_coordinator,
    get_context_builder,
    
    # 上下文构建
    AgentContextBuilder,
    ContextType,
    PlaceholderType,
    PlaceholderInfo,
    TemplateInfo,
    TaskInfo,
    DatabaseSchemaInfo,
    
    # 便捷函数
    create_simple_context,
    create_data_analysis_context,
    create_template_filling_context
)
```

### 最简单的使用方式

```python
# 执行一个简单的任务
result = await execute_agent_task(
    task_name="数据分析",
    task_description="分析销售数据趋势",
    context_data={
        "placeholders": {
            "data_source": "sales_2024",
            "time_range": "Q1",
            "metrics": ["revenue", "growth_rate"]
        }
    }
)

print(f"任务状态: {result['success']}")
print(f"使用的Agent: {result['target_agent']}")
```

---

## 核心数据结构

### 1. AgentMessage - 消息传递核心

```python
@dataclass
class AgentMessage:
    # 必需字段
    message_id: str                    # 唯一消息ID
    message_type: MessageType          # 消息类型
    from_agent: str                   # 发送方Agent
    to_agent: str                     # 接收方Agent
    payload: Any                      # 消息载荷
    
    # 可选字段
    priority: MessagePriority = MessagePriority.NORMAL
    is_streaming: bool = False
    progress: Optional[float] = None   # 0.0-1.0
    confidence: Optional[float] = None
    metadata: MessageMetadata = field(default_factory=MessageMetadata)
```

**MessageType 枚举值**:
- `TASK_REQUEST` - 任务请求
- `PROGRESS_UPDATE` - 进度更新
- `RESULT_RESPONSE` - 结果响应
- `STREAM_START/CHUNK/END` - 流式传输
- `ERROR_NOTIFICATION` - 错误通知

**MessagePriority 级别**:
- `LOW` - 低优先级
- `NORMAL` - 普通优先级
- `HIGH` - 高优先级
- `URGENT` - 紧急
- `CRITICAL` - 关键

### 2. ToolExecutionContext - 工具执行上下文

```python
@dataclass
class ToolExecutionContext:
    # 基本信息
    request_id: str                   # 请求ID
    user_id: Optional[str]           # 用户ID
    session_id: str                  # 会话ID
    
    # 执行环境
    working_directory: str = "."
    timeout_seconds: int = 30
    environment_variables: Dict[str, str] = field(default_factory=dict)
    
    # 权限控制
    permissions: List[ToolPermission] = field(default_factory=list)
    allowed_paths: List[str] = field(default_factory=list)
    
    # 共享状态
    shared_data: Dict[str, Any] = field(default_factory=dict)
    progress_callback: Optional[Callable] = None
```

### 3. ToolResult - 工具执行结果

```python
@dataclass
class ToolResult:
    # 核心结果
    success: bool                     # 执行是否成功
    data: Any = None                 # 结果数据
    error: Optional[str] = None      # 错误信息
    
    # 元数据
    tool_name: str = ""
    execution_time_ms: float = 0
    content_type: str = "text"
    
    # 流式支持
    is_partial: bool = False
    sequence_number: int = 0
    
    # 质量度量
    confidence: Optional[float] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
```

---

## Context 上下文系统

### 1. AgentContext - 主要上下文结构

```python
@dataclass
class AgentContext:
    # 标识信息
    context_id: str                              # 上下文唯一ID
    context_type: ContextType                    # 上下文类型
    
    # 核心数据
    task_info: TaskInfo                         # 任务信息
    placeholders: List[PlaceholderInfo]         # 占位符列表
    templates: List[TemplateInfo]               # 模板列表
    database_schemas: List[DatabaseSchemaInfo]  # 数据库模式信息
    
    # 处理结果
    resolved_placeholders: Dict[str, Any]       # 已解析的占位符
    processed_templates: Dict[str, str]         # 已处理的模板
    query_context: Dict[str, Any]               # 查询上下文
    
    # 执行配置
    execution_options: Dict[str, Any]           # 执行选项
    tool_preferences: Dict[str, Any]            # 工具偏好设置
```

### 2. ContextType - 上下文类型

```python
class ContextType(Enum):
    DATA_ANALYSIS = "data_analysis"             # 数据分析
    REPORT_GENERATION = "report_generation"     # 报告生成
    SQL_GENERATION = "sql_generation"           # SQL生成
    BUSINESS_INTELLIGENCE = "business_intelligence"  # 商业智能
    TEMPLATE_PROCESSING = "template_processing" # 模板处理
    TEMPLATE_FILLING = "template_filling"       # 模板填充 ★新增★
```

### 3. 占位符信息结构

```python
@dataclass
class PlaceholderInfo:
    # 基本信息
    name: str                          # 占位符名称
    type: PlaceholderType             # 占位符类型
    value: Any = None                 # 占位符值
    description: str = ""             # 描述信息
    
    # 验证规则
    required: bool = True             # 是否必需
    default_value: Any = None         # 默认值
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**PlaceholderType 类型**:
- `TABLE_NAME` - 表名
- `COLUMN_NAME` - 列名
- `TEMPLATE_VARIABLE` - 模板变量
- `FILL_MODE` - 填充模式 ★新增★
- `TEMPLATE_TYPE` - 模板类型 ★新增★
- `DATE_RANGE` - 日期范围
- `METRIC_NAME` - 指标名称

### 4. 使用 AgentContextBuilder

```python
# 创建上下文构建器
builder = AgentContextBuilder()

# 创建任务信息
task_info = TaskInfo(
    task_id="task_001",
    task_name="季度报告生成",
    task_type="template_fill",
    description="生成Q1季度业绩报告"
)

# 创建占位符
placeholders = [
    PlaceholderInfo(
        name="company_name",
        type=PlaceholderType.TEMPLATE_VARIABLE,
        value="科技有限公司",
        description="公司名称"
    ),
    PlaceholderInfo(
        name="revenue",
        type=PlaceholderType.TEMPLATE_VARIABLE,
        value=1250.8,
        description="季度收入（万元）"
    ),
    PlaceholderInfo(
        name="fill_mode",
        type=PlaceholderType.FILL_MODE,
        value="smart",
        description="智能填充模式"
    )
]

# 创建模板信息
templates = [
    TemplateInfo(
        template_id="quarterly_report",
        name="季度报告模板",
        template_type="word",
        content="""
# {company_name} 季度报告

## 财务概况
本季度营业收入达到 {revenue} 万元，同比增长显著。

## 业务分析
{business_analysis}

## 展望
{future_outlook}
        """,
        variables=["company_name", "revenue", "business_analysis", "future_outlook"]
    )
]

# 构建完整上下文
context = builder.build_context(
    task_info=task_info,
    placeholders=placeholders,
    templates=templates,
    context_type=ContextType.TEMPLATE_FILLING  # 可选，会自动推断
)

print(f"上下文类型: {context.context_type}")
print(f"推荐工具: {context.tool_preferences['preferred_tools']}")
```

---

## Tools 工具系统

### 1. AgentTool 基础接口

```python
class AgentTool(ABC):
    def __init__(self, definition: ToolDefinition):
        self.definition = definition
        self.name = definition.name
    
    @abstractmethod
    async def validate_input(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        """验证输入数据"""
        pass
    
    @abstractmethod
    async def check_permissions(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> bool:
        """检查权限"""
        pass
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """执行工具逻辑"""
        pass
```

### 2. StreamingAgentTool - 流式工具

```python
class StreamingAgentTool(AgentTool):
    async def stream_progress(self, progress_data: Dict[str, Any], context: ToolExecutionContext) -> ToolResult:
        """发送进度更新"""
        return ToolResult(
            success=True,
            data=progress_data,
            is_partial=True,
            content_type="progress"
        )
    
    async def stream_final_result(self, result_data: Dict[str, Any], context: ToolExecutionContext) -> ToolResult:
        """发送最终结果"""
        return ToolResult(
            success=True,
            data=result_data,
            is_partial=False,
            content_type="result"
        )
```

### 3. 工具权限系统

```python
class ToolPermission(Enum):
    READ_ONLY = "read_only"           # 只读权限
    READ_WRITE = "read_write"         # 读写权限
    FILE_SYSTEM = "file_system"       # 文件系统访问
    NETWORK = "network"               # 网络访问
    DATABASE = "database"             # 数据库访问
    SYSTEM = "system"                 # 系统级操作
    ADMIN = "admin"                   # 管理员权限
```

---

## 模板填充系统

### 1. TemplateFillTool 输入结构

```python
class TemplateFillInput(BaseModel):
    # 核心参数
    template_content: str = Field(..., min_length=1, description="模板内容")
    placeholders: Dict[str, Any] = Field(..., description="占位符数据字典")
    
    # 格式控制
    template_type: str = Field(default="word", description="模板类型：word, html, markdown, text")
    fill_mode: str = Field(default="smart", description="填充模式：smart, exact, descriptive, enhanced")
    
    # 处理选项
    add_descriptions: bool = Field(default=True, description="是否添加简短描述")
    preserve_formatting: bool = Field(default=True, description="是否保持格式")
    
    # Domain 集成选项
    generate_word_document: bool = Field(default=True, description="是否生成Word文档")
    document_title: str = Field(default="模板填充报告", description="Word文档标题")
    enable_quality_check: bool = Field(default=True, description="是否启用质量检查")
```

### 2. 支持的占位符模式

```python
# TemplateFillTool 支持多种占位符格式
placeholder_patterns = {
    'curly_braces': r'\{([^}]+)\}',        # {placeholder}
    'double_braces': r'\{\{([^}]+)\}\}',   # {{placeholder}}
    'angle_brackets': r'<([^>]+)>',        # <placeholder>
    'square_brackets': r'\[([^\]]+)\]',    # [placeholder]
    'percent_style': r'%([^%]+)%',         # %placeholder%
    'dollar_style': r'\$\{([^}]+)\}'       # ${placeholder}
}
```

### 3. 填充模式说明

- **exact**: 精确替换，直接使用原始值
- **smart**: 智能格式化（数字千分位、日期格式化等）
- **descriptive**: 包含数据类型和描述信息
- **enhanced**: 智能格式化 + 描述信息

### 4. 使用示例

```python
from app.services.infrastructure.agents.tools.data.report_tool import TemplateFillTool

# 创建工具实例
tool = TemplateFillTool()

# 准备输入数据
input_data = {
    'template_content': '''
# {company_name} 业绩报告

## 核心指标
- 营业收入：{revenue} 万元
- 利润率：{profit_margin}%
- 客户数量：{customer_count} 个

## 分析总结
{analysis_summary}
    ''',
    'placeholders': {
        'company_name': '智能科技有限公司',
        'revenue': 2580.5,
        'profit_margin': 15.3,
        'customer_count': 1250,
        'analysis_summary': '本季度业绩表现优异，各项指标均超预期。'
    },
    'template_type': 'word',
    'fill_mode': 'smart',
    'add_descriptions': True,
    'generate_word_document': True,
    'document_title': '季度业绩报告',
    'enable_quality_check': True
}

# 创建执行上下文
context = ToolExecutionContext(
    request_id="req_001",
    user_id="user_123",
    session_id="session_456"
)

# 执行模板填充
async for result in tool.execute(input_data, context):
    if result.is_partial:
        print(f"进度: {result.data.get('progress', 0)}%")
        print(f"状态: {result.data.get('message', '')}")
    else:
        print("填充完成!")
        print(f"成功: {result.data['success']}")
        if result.data.get('word_document'):
            word_doc = result.data['word_document']
            print(f"Word文档路径: {word_doc.get('word_document_path', 'N/A')}")
```

---

## Domain 层集成

### 1. 模板填充与Word生成集成

```python
from app.services.infrastructure.agents.tools.data.template_domain_integration import process_template_to_word

# 直接使用便捷函数
template_fill_result = {
    'success': True,
    'filled_content': '已填充的模板内容...',
    'domain_data': {
        'template_analysis': {...},
        'placeholder_data': {...},
        'word_generation_params': {...}
    },
    'metadata': {...}
}

# 处理为Word文档
word_result = await process_template_to_word(
    template_fill_result=template_fill_result,
    title="业绩报告",
    enable_quality_check=True
)

if word_result['success']:
    print(f"Word文档生成成功: {word_result['word_document_path']}")
    print(f"质量检查分数: {word_result['quality_check']['overall_score']}")
else:
    print(f"生成失败: {word_result['error']}")
```

### 2. Domain 集成的输出结构

```python
integration_result = {
    'success': bool,                              # 是否成功
    'word_document_path': str,                    # Word文档路径
    'template_analysis': {                        # 模板分析结果
        'total_placeholders': int,
        'filled_placeholders': int,
        'complexity_score': int
    },
    'quality_check': {                           # 质量检查结果
        'overall_score': float,                  # 总体质量分数
        'metrics': {
            'completeness_score': float,
            'consistency_score': float,
            'readability_score': float
        },
        'issues': List[str],                     # 发现的问题
        'recommendations': List[str]             # 改进建议
    },
    'generation_metadata': {                     # 生成元数据
        'template_type': str,
        'fill_mode': str,
        'generation_time': str,
        'integration_version': str
    },
    'placeholder_summary': {                     # 占位符摘要
        'total_placeholders': int,
        'filled_successfully': int,
        'descriptions_generated': int
    }
}
```

---

## 错误处理和恢复

### 1. 错误类型

```python
class ErrorType(Enum):
    NETWORK_ERROR = "network_error"             # 网络错误
    DATABASE_ERROR = "database_error"           # 数据库错误
    MEMORY_ERROR = "memory_error"               # 内存错误
    TIMEOUT_ERROR = "timeout_error"             # 超时错误
    VALIDATION_ERROR = "validation_error"       # 验证错误
    PERMISSION_ERROR = "permission_error"       # 权限错误
    PROCESSING_ERROR = "processing_error"       # 处理错误
```

### 2. 错误恢复策略

```python
from app.services.infrastructure.agents.prompts.error_recovery_prompts import (
    get_error_recovery_prompt,
    create_recovery_strategy
)

# 创建恢复策略
recovery_strategy = create_recovery_strategy(
    error_type=ErrorType.MEMORY_ERROR,
    severity="high",
    auto_retry=True
)

# 获取恢复提示
recovery_prompt = get_error_recovery_prompt(ErrorType.MEMORY_ERROR)
```

### 3. 异常处理最佳实践

```python
async def safe_agent_execution():
    try:
        result = await execute_agent_task(
            task_name="数据处理",
            task_description="处理大数据集",
            context_data={...}
        )
        return result
        
    except ValidationError as e:
        # 验证错误 - 检查输入数据
        logger.error(f"输入验证失败: {e}")
        return {"success": False, "error": "input_validation_failed", "details": str(e)}
        
    except TimeoutError as e:
        # 超时错误 - 可能需要分批处理
        logger.warning(f"任务超时: {e}")
        return await execute_agent_task_with_batching(...)
        
    except MemoryError as e:
        # 内存错误 - 启用内存优化模式
        logger.warning(f"内存不足: {e}")
        return await execute_agent_task_memory_optimized(...)
        
    except Exception as e:
        # 通用错误处理
        logger.error(f"未知错误: {e}")
        return {"success": False, "error": "unknown_error", "details": str(e)}
```

---

## 最佳实践

### 1. 上下文构建最佳实践

```python
# ✅ 好的做法
def create_comprehensive_context():
    """创建完整的上下文"""
    return AgentContextBuilder().build_context(
        task_info=TaskInfo(
            task_id=f"task_{uuid.uuid4()}",
            task_name="明确的任务名称",
            task_type="template_fill",
            description="详细的任务描述，包含目标和期望结果"
        ),
        placeholders=[
            PlaceholderInfo(
                name="data_field",
                type=PlaceholderType.TEMPLATE_VARIABLE,
                value="actual_value",
                description="清晰的字段描述",
                required=True,
                validation_rules={"min_length": 1}
            )
        ],
        templates=[
            TemplateInfo(
                template_id="unique_template_id",
                name="模板显示名称",
                template_type="word",
                content="包含占位符的模板内容",
                variables=["列出所有变量"]
            )
        ]
    )

# ❌ 避免的做法
def create_minimal_context():
    """过于简单的上下文"""
    return create_simple_context(
        task_name="任务",  # 过于简单
        task_description="做某事",  # 描述不清晰
        placeholders_dict={"x": "y"}  # 缺少类型信息
    )
```

### 2. 错误处理最佳实践

```python
# ✅ 好的做法
async def robust_template_processing():
    """健壮的模板处理"""
    try:
        # 预验证
        if not validate_template_syntax(template_content):
            raise ValidationError("模板语法错误")
        
        # 执行处理
        result = await execute_agent_task(...)
        
        # 后验证
        if result.get('success') and result.get('word_document'):
            quality_score = result['word_document']['quality_check']['overall_score']
            if quality_score < 0.7:
                logger.warning(f"生成质量较低: {quality_score}")
        
        return result
        
    except ValidationError as e:
        return handle_validation_error(e)
    except Exception as e:
        return handle_generic_error(e)
```

### 3. 性能优化最佳实践

```python
# ✅ 批量处理
async def process_multiple_templates():
    """批量处理多个模板"""
    tasks = []
    for template_data in template_list:
        task = execute_agent_task(
            task_name=f"处理模板_{template_data['id']}",
            task_description="模板填充",
            context_data=template_data
        )
        tasks.append(task)
    
    # 并发执行
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return process_batch_results(results)

# ✅ 缓存利用
def get_cached_context(cache_key: str):
    """利用缓存减少重复计算"""
    if cache_key in context_cache:
        return context_cache[cache_key]
    
    context = build_context(...)
    context_cache[cache_key] = context
    return context
```

---

## 示例代码

### 示例1: 完整的模板填充流程

```python
import asyncio
from app.services.infrastructure.agents import *

async def complete_template_filling_example():
    """完整的模板填充示例"""
    
    # 1. 准备模板内容
    template_content = """
# {company_name} 财务报告

## 核心财务指标
- 营业收入：{revenue} 万元
- 净利润：{net_profit} 万元  
- 毛利率：{gross_margin}%
- 净利率：{net_margin}%

## 业务分析
{business_analysis}

## 风险评估
{risk_assessment}

## 未来展望
{future_outlook}

---
报告生成时间：{report_date}
数据来源：{data_source}
"""

    # 2. 准备占位符数据
    placeholder_data = {
        'company_name': '创新科技股份有限公司',
        'revenue': 5280.7,
        'net_profit': 658.5,
        'gross_margin': 32.5,
        'net_margin': 12.5,
        'business_analysis': '本期公司主营业务稳步增长，新产品市场反应良好...',
        'risk_assessment': '主要风险包括市场竞争加剧、原材料价格波动...',
        'future_outlook': '预计下季度将继续保持稳健增长态势...',
        'report_date': '2024-03-31',
        'data_source': '财务管理系统'
    }
    
    # 3. 使用便捷函数执行任务
    try:
        result = await execute_agent_task(
            task_name="财务报告生成",
            task_description="基于模板生成季度财务报告，包含关键指标分析和业务展望",
            context_data={
                "templates": [{
                    "id": "financial_report",
                    "name": "财务报告模板",
                    "type": "word",
                    "content": template_content
                }],
                "placeholders": placeholder_data
            },
            target_agent="report_generation_agent"
        )
        
        # 4. 处理结果
        if result['success']:
            print("✅ 报告生成成功!")
            print(f"使用的Agent: {result['target_agent']}")
            
            # 获取生成的文档信息
            if 'word_document' in result['result']:
                word_info = result['result']['word_document']
                if word_info.get('success'):
                    print(f"📄 Word文档路径: {word_info['word_document_path']}")
                    print(f"📊 质量评分: {word_info['quality_check']['overall_score']:.1f}/10")
                else:
                    print(f"⚠️ Word生成失败: {word_info.get('error')}")
            
            return result
        else:
            print(f"❌ 任务执行失败: {result.get('error', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"💥 执行过程中出现异常: {e}")
        return None

# 运行示例
if __name__ == "__main__":
    result = asyncio.run(complete_template_filling_example())
```

### 示例2: 自定义工具开发

```python
from app.services.infrastructure.agents.tools.core.base import StreamingAgentTool, ToolDefinition, create_tool_definition

class CustomDataProcessorTool(StreamingAgentTool):
    """自定义数据处理工具示例"""
    
    def __init__(self):
        definition = create_tool_definition(
            name="custom_data_processor",
            description="自定义数据处理工具，支持多种数据格式转换",
            category=ToolCategory.DATA,
            priority=ToolPriority.HIGH,
            permissions=[ToolPermission.READ_WRITE],
            supports_streaming=True,
            typical_execution_time_ms=5000
        )
        super().__init__(definition)
    
    async def validate_input(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        """验证输入数据"""
        required_fields = ['input_data', 'output_format']
        for field in required_fields:
            if field not in input_data:
                raise ValidationError(f"缺少必需字段: {field}")
        
        return input_data
    
    async def check_permissions(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> bool:
        """检查权限"""
        return ToolPermission.READ_WRITE in context.permissions
    
    async def execute(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """执行数据处理"""
        
        # 阶段1: 初始化
        yield await self.stream_progress({
            'status': 'initializing',
            'message': '初始化数据处理器...',
            'progress': 0
        }, context)
        
        # 阶段2: 数据验证
        yield await self.stream_progress({
            'status': 'validating',
            'message': '验证输入数据...',
            'progress': 20
        }, context)
        
        # 模拟验证过程
        await asyncio.sleep(1)
        
        # 阶段3: 数据转换
        yield await self.stream_progress({
            'status': 'processing',
            'message': '执行数据转换...',
            'progress': 50
        }, context)
        
        # 执行实际处理逻辑
        processed_data = self._process_data(
            input_data['input_data'],
            input_data['output_format']
        )
        
        # 阶段4: 质量检查
        yield await self.stream_progress({
            'status': 'quality_check',
            'message': '执行质量检查...',
            'progress': 80
        }, context)
        
        quality_score = self._calculate_quality_score(processed_data)
        
        # 最终结果
        result_data = {
            'success': True,
            'processed_data': processed_data,
            'quality_score': quality_score,
            'processing_metadata': {
                'input_size': len(str(input_data['input_data'])),
                'output_size': len(str(processed_data)),
                'processing_time': context.execution_metrics.get('duration', 0)
            }
        }
        
        yield await self.stream_final_result(result_data, context)
    
    def _process_data(self, data: Any, output_format: str) -> Any:
        """实际的数据处理逻辑"""
        # 这里实现具体的数据处理逻辑
        return {"processed": data, "format": output_format}
    
    def _calculate_quality_score(self, data: Any) -> float:
        """计算数据质量分数"""
        # 这里实现质量评估逻辑
        return 0.85

# 注册自定义工具
from app.services.infrastructure.agents.tools.core.registry import get_tool_registry

registry = get_tool_registry()
registry.register_tool(CustomDataProcessorTool())
```

### 示例3: 复杂上下文构建

```python
async def advanced_context_example():
    """高级上下文构建示例"""
    
    builder = AgentContextBuilder()
    
    # 创建复杂的任务信息
    task_info = TaskInfo(
        task_id="complex_analysis_001",
        task_name="多维度业务分析报告",
        task_type="comprehensive_analysis",
        description="基于多个数据源生成包含财务、运营、市场分析的综合报告",
        priority=MessagePriority.HIGH,
        requirements=[
            "整合财务数据和运营数据",
            "生成可视化图表",
            "包含趋势预测分析",
            "输出Word和PDF格式"
        ],
        success_criteria=[
            "数据完整性检查通过",
            "报告质量分数>8.0",
            "所有图表正常显示",
            "文档格式规范"
        ],
        estimated_duration=300  # 5分钟
    )
    
    # 创建多类型占位符
    placeholders = [
        # 基本信息占位符
        PlaceholderInfo(
            name="company_info",
            type=PlaceholderType.TEMPLATE_VARIABLE,
            value={
                "name": "创新科技有限公司",
                "industry": "软件开发",
                "established": "2018-05-15",
                "employees": 256
            },
            description="公司基本信息",
            validation_rules={"required_keys": ["name", "industry"]}
        ),
        
        # 财务数据占位符
        PlaceholderInfo(
            name="financial_metrics",
            type=PlaceholderType.METRIC_NAME,
            value={
                "revenue": 12580.5,
                "profit": 2156.3,
                "growth_rate": 15.8,
                "margin": 17.1
            },
            description="核心财务指标",
            metadata={"currency": "CNY", "unit": "万元"}
        ),
        
        # 日期范围占位符
        PlaceholderInfo(
            name="report_period",
            type=PlaceholderType.DATE_RANGE,
            value={
                "start_date": "2024-01-01",
                "end_date": "2024-03-31",
                "period_name": "2024年第一季度"
            },
            description="报告期间"
        ),
        
        # 填充模式控制
        PlaceholderInfo(
            name="fill_mode",
            type=PlaceholderType.FILL_MODE,
            value="enhanced",
            description="使用增强模式填充，包含描述和格式化"
        )
    ]
    
    # 创建多个模板
    templates = [
        # 主报告模板
        TemplateInfo(
            template_id="main_report",
            name="综合业务分析报告",
            template_type="word",
            content=load_template_content("comprehensive_report.docx"),
            variables=["company_info", "financial_metrics", "report_period"],
            sections=["executive_summary", "financial_analysis", "operational_review"],
            format_options={
                "page_orientation": "portrait",
                "font_family": "Microsoft YaHei",
                "include_toc": True
            }
        ),
        
        # 图表模板
        TemplateInfo(
            template_id="charts_template",
            name="数据可视化模板",
            template_type="html",
            content=load_template_content("charts.html"),
            variables=["chart_data", "chart_config"],
            metadata={"chart_library": "echarts", "responsive": True}
        )
    ]
    
    # 创建数据库模式信息
    database_schemas = [
        DatabaseSchemaInfo(
            table_name="financial_records",
            columns=[
                {"name": "record_id", "type": "INTEGER", "primary_key": True},
                {"name": "revenue", "type": "DECIMAL(15,2)", "nullable": False},
                {"name": "record_date", "type": "DATE", "nullable": False}
            ],
            relationships=[
                {"type": "foreign_key", "target_table": "companies", "columns": ["company_id"]}
            ],
            statistics={"row_count": 15420, "avg_row_length": 128},
            sample_data=[
                {"record_id": 1, "revenue": 125.50, "record_date": "2024-01-01"},
                {"record_id": 2, "revenue": 158.30, "record_date": "2024-01-02"}
            ]
        )
    ]
    
    # 构建完整上下文
    context = builder.build_context(
        task_info=task_info,
        placeholders=placeholders,
        templates=templates,
        database_schemas=database_schemas
    )
    
    # 验证上下文质量
    print(f"上下文类型: {context.context_type}")
    print(f"占位符解析率: {len(context.resolved_placeholders)}/{len(placeholders)}")
    print(f"推荐工具: {context.tool_preferences['preferred_tools']}")
    print(f"执行选项: {list(context.execution_options.keys())}")
    
    return context

def load_template_content(template_file: str) -> str:
    """加载模板内容的辅助函数"""
    # 这里应该实现实际的模板加载逻辑
    template_mapping = {
        "comprehensive_report.docx": """
# {company_info.name} 综合业务分析报告

## 报告期间
{report_period.period_name}

## 执行摘要
本报告期间，{company_info.name} 实现营业收入 {financial_metrics.revenue} 万元...

## 财务分析
### 核心指标
- 营业收入：{financial_metrics.revenue} 万元
- 净利润：{financial_metrics.profit} 万元
- 增长率：{financial_metrics.growth_rate}%
        """,
        "charts.html": """
<div id="revenue-chart" style="width: 100%; height: 400px;"></div>
<script>
    // ECharts 配置
    var chartData = {chart_data};
    var chartConfig = {chart_config};
</script>
        """
    }
    
    return template_mapping.get(template_file, f"模板内容 - {template_file}")

# 运行高级示例
if __name__ == "__main__":
    context = asyncio.run(advanced_context_example())
    print(f"复杂上下文构建完成，ID: {context.context_id}")
```

---

## 总结

本文档详细介绍了 Agents 系统的核心概念、数据结构和使用方法。通过这些示例和最佳实践，您可以：

1. **理解数据结构**：掌握各组件的输入输出格式
2. **构建智能上下文**：创建适合任务的执行环境
3. **使用模板填充**：实现复杂的文档生成需求
4. **开发自定义工具**：扩展系统功能
5. **处理错误和异常**：构建健壮的应用

Agents 系统提供了强大而灵活的基础设施，支持构建复杂的AI驱动应用。通过合理使用这些功能，您可以实现高效、可靠的智能化业务处理流程。