# AutoReportAI Prompts 目录深度分析报告

## 执行时间
2025-10-30

---

## 1. 目录结构分析

### 物理结构
```
/Users/shan/work/AutoReportAI/backend/app/services/infrastructure/agents/prompts/
├── __init__.py           (310 字节)
├── system.py             (18,854 字节)
├── stages.py             (16,821 字节)
├── templates.py          (19,218 字节)
└── __pycache__/          (编译缓存)
```

### 目录特点
- **4个核心Python模块** + 初始化文件
- **总代码量**: ~55KB (约2,100行有效代码)
- **组织清晰**: 按职责分离(系统级、阶段级、模板级)
- **完全模块化**: 支持独立导入和测试

---

## 2. 文件详细分析

### 2.1 `__init__.py` - 模块导出接口

**现状**:
- 长度: 14 行
- 全部为TODO注释
- 导出功能未实现

**内容**:
```python
"""Prompt 模板模块"""

# TODO: 实现导出
# from .system import SYSTEM_PROMPT, build_system_prompt
# from .stages import STAGE_PROMPTS, get_stage_prompt
# from .templates import PromptTemplate, build_prompt
```

**问题**:
- 模块公共接口未暴露
- 外部代码无法通过清晰的导入路径访问prompt功能
- 所有功能都是隐形导出状态

**优化方向**:
- 需要启用注释中的导出
- 添加`__all__`列表明确暴露的API

---

### 2.2 `system.py` - 系统级提示词管理

**代码规模**: 673 行

**核心职责**:
1. 定义Agent的基础系统提示
2. 构建阶段特定的系统提示
3. 根据复杂度生成差异化提示
4. 支持上下文感知的动态提示生成

**主要组件**:

#### A. SystemPromptBuilder 类 (18-596行)

**设计模式**: Builder + Manager 模式

**核心方法**:
```python
def __init__(self)
    - 初始化三个提示系统: 基础、阶段、复杂度

def build_system_prompt(stage, complexity, custom_instructions)
    - 组合多个提示部分
    - 支持可选的阶段和复杂度参数

def build_context_aware_prompt(context_info, stage, complexity)
    - 在标准提示基础上注入上下文信息
    - 返回充分上下文化的提示

def _build_base_prompt() -> str
    - 核心系统提示(~160行)
    - 定义Agent的角色、能力、工作原则

def _build_stage_prompts() -> Dict[ExecutionStage, str]
    - 8个执行阶段的专用提示
    - 每个阶段 5-35 行的指导内容

def _build_complexity_prompts() -> Dict[TaskComplexity, str]
    - 3个复杂度级别的策略指导
    - SIMPLE/MEDIUM/COMPLEX
```

**提示词组织特点**:

1. **基础提示** (位置: 26-161 行)
   - 总长: ~520 行
   - 包含模块: 角色定义、核心能力(4大块)、工作原则(4大块)、工具使用规范、输出格式、质量保证
   - **关键特征**: 强调"上下文优先原则"和"工具调用原则"

2. **阶段提示** (位置: 163-443 行)
   - INITIALIZATION: 任务理解、信息收集、规划制定
   - SCHEMA_DISCOVERY: 表结构探索、关系分析、上下文构建
   - SQL_GENERATION: 6步骤详细指导(分析Schema → 工具探索 → 设计逻辑 → 生成SQL → 验证 → 返回结果)
   - SQL_VALIDATION: 语法验证、逻辑验证、修复优化
   - DATA_EXTRACTION: 查询执行、数据采样、结果验证
   - ANALYSIS: 数据分析、业务洞察、结果总结
   - CHART_GENERATION: 图表选择、配置优化、交互设计
   - COMPLETION: 结果整合、质量检查、交付准备

3. **复杂度提示** (位置: 446-505 行)
   - SIMPLE (0.3): 直接简单查询、核心工具、快速响应
   - MEDIUM (0.5): 多表关联、工具链组合、详细分析
   - COMPLEX (0.8): 任务分解、高级SQL、多轮验证

**核心设计特色**:
- **上下文感知**: `build_context_aware_prompt()` 支持数据源、表结构、业务上下文的动态注入
- **强制性指导**: 使用 `🔥` 、`❌`、`✅` 等视觉标记强调关键要求
- **错误指导**: SQL_GENERATION 阶段明确列出错误示例和正确示例
- **时间占位符强制**: 明确禁止硬编码日期，必须使用 `{{start_date}}`/`{{end_date}}`

#### B. 工厂函数 (599-656 行)

**导出的便利函数**:
- `create_system_prompt()`: 创建标准系统提示
- `create_context_aware_system_prompt()`: 创建上下文感知提示

**预定义提示常量**:
- `DEFAULT_SYSTEM_PROMPT`: 默认系统提示
- `SCHEMA_DISCOVERY_PROMPT`: Schema发现阶段提示
- `SQL_GENERATION_PROMPT`: SQL生成阶段提示
- `DATA_ANALYSIS_PROMPT`: 数据分析阶段提示
- `CHART_GENERATION_PROMPT`: 图表生成阶段提示

**问题**: 预定义常量使用硬编码的MEDIUM复杂度，缺乏灵活性

---

### 2.3 `stages.py` - 阶段提示管理

**代码规模**: 501 行

**核心职责**:
1. 管理各执行阶段的提示和转换
2. 支持阶段间转换的提示引导
3. 提供上下文和复杂度感知的阶段提示

**主要组件**:

#### A. StagePromptManager 类 (18-421 行)

**设计模式**: Manager + Template 模式

**核心结构**:
```python
def __init__(self)
    - 初始化阶段模板和阶段转换提示

def get_stage_prompt(stage, context, complexity)
    - 获取特定阶段的完整提示
    - 自动添加复杂度和上下文信息

def get_transition_prompt(from_stage, to_stage)
    - 获取从一个阶段到另一个阶段的转换提示
```

**数据结构**:

1. **阶段模板** (`_build_stage_templates()`)
   ```python
   {
       ExecutionStage.XXX: {
           "objective": "阶段目标",
           "key_tasks": ["任务1", "任务2", ...],
           "tools_to_use": ["工具1", "工具2", ...],
           "success_criteria": "成功标准",
           "next_stage": 下一阶段
       }
   }
   ```
   - 8个阶段，每个都有明确的目标、任务、工具、成功标准
   - 形成自然的工作流程链

2. **阶段转换提示** (`_build_transition_prompts()`)
   - 8个转换提示，包括:
   - `to_schema_discovery`: 进入Schema发现阶段的指导
   - `to_sql_generation`: 进入SQL生成阶段的指导
   - `to_data_extraction`: 进入数据提取阶段的指导
   - 等等...
   - 每个转换提示 10-15 行，提供步骤和关键点

#### B. 复杂度指导 (`_get_complexity_guidance()`)

**支持的组合**:
```python
(SQL_GENERATION, SIMPLE): "使用简单的单表查询，避免复杂的关联"
(SQL_GENERATION, MEDIUM): "可以使用多表关联，适当使用聚合函数"
(SQL_GENERATION, COMPLEX): "支持复杂查询，可以使用窗口函数、CTE等"

(SQL_VALIDATION, SIMPLE): "进行基本的语法和字段检查"
(SQL_VALIDATION, MEDIUM): "进行全面的验证，包括性能考虑"
(SQL_VALIDATION, COMPLEX): "进行深度验证，包括优化建议"

(ANALYSIS, SIMPLE): "提供基本的数据摘要和关键指标"
(ANALYSIS, MEDIUM): "进行详细分析，提供业务洞察"
(ANALYSIS, COMPLEX): "进行深度分析，提供多维度洞察和建议"
```

#### C. 提示生成逻辑 (`get_stage_prompt()`)

**输出组件**:
1. 阶段标题和目标
2. 关键任务列表 (编号形式)
3. 推荐工具列表
4. 成功标准
5. 复杂度特定指导 (如果提供)
6. 上下文信息 (如果提供)

**动态上下文注入**:
```python
def _build_context_guidance(context, stage):
    - 表数量和名称
    - 列数量
    - 时间窗口
    - 业务上下文信息
```

#### D. 预定义常量 (476-484 行)

```python
INITIALIZATION_PROMPT
SCHEMA_DISCOVERY_PROMPT
SQL_GENERATION_PROMPT
SQL_VALIDATION_PROMPT
DATA_EXTRACTION_PROMPT
ANALYSIS_PROMPT
CHART_GENERATION_PROMPT
COMPLETION_PROMPT
```

**特点**: 全部使用默认参数创建，不支持动态复杂度调整

---

### 2.4 `templates.py` - 提示词模板和格式化

**代码规模**: 704 行

**核心职责**:
1. 定义可重用的提示词模板
2. 支持动态模板格式化和变量替换
3. 格式化各种上下文信息(Schema、业务、数据、错误等)
4. 支持自定义模板创建

**主要组件**:

#### A. PromptTemplate 类 (19-49 行)

**设计**: 基于Python标准库 `string.Template`

```python
class PromptTemplate:
    def __init__(self, template: str, variables: Dict = None):
        self.template = template
        self.variables = variables or {}
        self._template = Template(template)  # 使用 string.Template

    def format(self, **kwargs) -> str:
        # 合并默认变量和传入变量
        # 使用 safe_substitute() 忽略缺失的变量
```

**特点**:
- 使用 `${variable}` 语法
- 支持默认变量值
- 安全替换(缺失变量不会报错)

#### B. PromptTemplateManager 类 (52-420 行)

**管理9个内置模板**:

1. **basic_request** (62-83)
   - 任务请求的基础模板
   - 变量: placeholder, data_source_id, user_id, complexity, max_iterations, context_section

2. **schema_discovery** (86-111)
   - Schema发现任务的模板
   - 包含发现策略和重点关注

3. **sql_generation** (114-223)
   - SQL生成任务的模板
   - **最复杂**: ~110行
   - 包含:
     - Doris数据库规范说明
     - 时间占位符强制要求 (🔥 重点强调)
     - SQL质量检查清单
     - 示例(正确和错误)
   
4. **sql_validation** (226-251)
   - SQL验证任务的模板
   - 包含验证步骤和修复要求

5. **data_analysis** (254-281)
   - 数据分析任务的模板
   - 包含分析要求和分析维度

6. **chart_generation** (284-311)
   - 图表生成任务的模板
   - 包含图表要求和类型建议

7. **error_handling** (314-341)
   - 错误处理的模板
   - 包含错误信息、类型、处理策略

8. **result_summary** (344-371)
   - 结果总结的模板
   - 包含执行统计、发现和建议

**方法**:
```python
def get_template(template_name: str) -> Optional[PromptTemplate]
    - 获取指定模板

def format_template(template_name: str, **kwargs) -> str
    - 格式化模板并返回字符串

def create_custom_template(name, template, variables) -> PromptTemplate
    - 创建自定义模板（动态注册）
```

#### C. ContextFormatter 类 (423-516 行)

**职责**: 格式化各种类型的上下文信息为可读的文本

**核心方法**:
```python
@staticmethod
def format_schema_context(context: ContextInfo) -> str
    - 格式化表结构信息
    - 输出: Markdown格式的表和列信息

@staticmethod
def format_business_context(context: ContextInfo) -> str
    - 格式化业务上下文
    - 输出: 关键值对列表

@staticmethod
def format_data_results(data: Any) -> str
    - 格式化查询结果数据
    - 输出: Markdown表格(前5行)

@staticmethod
def format_tool_calls(tool_calls: List[Dict]) -> str
    - 格式化工具调用历史
    - 输出: 编号列表(包含成功/失败状态)
```

#### D. 便利函数 (519-692 行)

**阶段提示格式化**:
```python
def format_request_prompt(request, context) -> str
    - 格式化请求提示
    - 使用 basic_request 模板

def format_stage_prompt(stage, request, context, additional_data) -> str
    - 格式化阶段提示
    - 根据阶段选择对应模板(schema_discovery/sql_generation等)
```

**错误和结果格式化**:
```python
def format_error_prompt(error_message, current_stage, ...) -> str
def format_result_summary(success, main_results, execution_time, ...) -> str
```

---

## 3. 现有提示词的组织方式分析

### 3.1 硬编码 vs 模板化

**现状**:
- **硬编码**: ~70% (system.py 和 stages.py 中的字符串)
- **模板化**: ~30% (templates.py 中的可参数化模板)

**硬编码部分**:
- system.py: 基础系统提示、阶段提示、复杂度提示都是硬编码字符串
- stages.py: 阶段目标、任务列表、转换提示都是硬编码字符串

**模板化部分**:
- templates.py: 9个预定义模板使用 `${variable}` 语法
- 支持动态注入内容

### 3.2 提示词的分层结构

```
系统级提示 (system.py)
├── 基础系统提示 (不变)
├── 阶段级提示 (随阶段变化)
└── 复杂度级提示 (随复杂度变化)

阶段级提示 (stages.py)
├── 阶段目标和任务
├── 工具推荐
├── 成功标准
└── 阶段转换指导

模板级提示 (templates.py)
├── 预定义模板 (9个)
└── 自定义模板 (动态注册)

上下文注入
├── Schema上下文 (表、列、关系)
├── 业务上下文 (业务规则、维度)
└── 数据上下文 (样本数据、结果)
```

### 3.3 提示词的特点

**强制性标记**:
- 🔥: 最重要的要求
- ⚠️: 警告
- ✅/❌: 正确/错误示例
- 🟢/🟡/🔴: 优先级指示

**显式约束**:
- 时间占位符强制使用
- Doris语法强制符合
- 表名必须来自上下文
- 错误自纠正机制

**结构化指导**:
- 分步骤的执行指导
- 示例代码块
- 检查清单
- 成功标准定义

---

## 4. 与 AdaptivePromptGenerator 的集成分析

### 4.1 AdaptivePromptGenerator 概览

**位置**: `/Users/shan/work/AutoReportAI/backend/app/services/infrastructure/agents/runtime.py:928-1200+`

**核心功能**:
```python
class AdaptivePromptGenerator:
    """自适应提示词生成器"""
    
    def generate_next_prompt(last_error, last_result) -> str
        - 基于当前状态和错误历史生成下一步提示
    
    def generate_initial_prompt(task_description) -> str
        - 生成初始提示
    
    def _generate_goal_section(progress) -> str
        - 生成目标和进度部分
    
    def _generate_error_guidance(error) -> str
        - 生成错误指导
    
    def _generate_progress_feedback(result) -> str
        - 生成进度反馈
    
    def _generate_action_guidance(action_plan) -> str
        - 生成行动指导
    
    def _generate_dynamic_constraints() -> str
        - 生成动态约束
```

### 4.2 当前集成状况

**问题**: 
- AdaptivePromptGenerator 与 prompts 模块**完全隔离**
- runtime.py 不导入任何 prompts 模块的内容
- AdaptivePromptGenerator 内部自行生成所有提示内容

**验证**:
```bash
$ grep -n "from.*prompts import\|import.*prompts" runtime.py
(无结果 - 完全没有导入)
```

### 4.3 潜在的集成点

#### A. 系统提示集成

**当前状态** (AdaptivePromptGenerator):
```python
def __init__(self, goal, tracker, base_system_prompt=None):
    self.goal = goal
    self.tracker = tracker
    self.base_system_prompt = base_system_prompt or ""

def generate_next_prompt(self):
    if self.base_system_prompt:
        prompt_parts.append(self.base_system_prompt)
```

**集成机会**:
```python
# 改进方案
from .prompts.system import SystemPromptBuilder
from .prompts.stages import StagePromptManager

class AdaptivePromptGenerator:
    def __init__(self, goal, tracker, stage=None, complexity=None):
        self.goal = goal
        self.tracker = tracker
        self.stage = stage
        self.complexity = complexity
        
        # 使用系统提示构建器
        self._system_prompt_builder = SystemPromptBuilder()
        self._stage_prompt_manager = StagePromptManager()
        
        # 获取基础系统提示
        self.base_system_prompt = self._system_prompt_builder.build_system_prompt(
            stage=stage,
            complexity=complexity
        )
```

#### B. 阶段感知的提示生成

**当前缺陷**:
- AdaptivePromptGenerator 不知道当前执行阶段
- 无法生成阶段特定的提示

**集成机会**:
```python
def generate_stage_aware_prompt(self, current_stage, context):
    """生成阶段感知的自适应提示"""
    # 获取阶段基础提示
    stage_prompt = self._stage_prompt_manager.get_stage_prompt(
        stage=current_stage,
        context=context,
        complexity=self.tracker.task_complexity
    )
    
    # 结合自适应部分
    adaptive_part = self._generate_adaptive_section()
    
    return f"{stage_prompt}\n\n{adaptive_part}"
```

#### C. 错误处理和修复建议

**当前** (AdaptivePromptGenerator):
```python
def _generate_error_guidance(self, error):
    error_type = type(error).__name__
    error_msg = str(error)
    
    suggestions = self._get_error_fix_suggestions(error_type, error_msg)
    
    return f"""# ⚠️ 上一步执行失败
    
**错误类型**: {error_type}
**错误信息**: {error_msg}
...
"""
```

**缺陷**: 
- 建议内容是硬编码的
- 不能利用 templates.py 中的 error_handling 模板

**集成机会**:
```python
from .prompts.templates import PromptTemplateManager

class AdaptivePromptGenerator:
    def __init__(self, ...):
        self._template_manager = PromptTemplateManager()
    
    def _generate_error_guidance(self, error):
        # 使用模板
        return self._template_manager.format_template(
            "error_handling",
            error_message=str(error),
            error_type=type(error).__name__,
            current_stage=self.current_stage.value,
            iteration_count=self.tracker.iteration_count,
            tool_call_count=self.tracker.tool_call_count,
            suggested_actions=self._get_error_fix_suggestions(...)
        )
```

#### D. 上下文感知的提示

**当前缺陷**:
- AdaptivePromptGenerator 不支持上下文注入
- 无法利用 ContextFormatter 的功能

**集成机会**:
```python
from .prompts.templates import ContextFormatter

def _build_context_aware_section(self, context_info):
    """构建上下文感知部分"""
    if context_info.tables:
        schema_section = ContextFormatter.format_schema_context(context_info)
    if context_info.business_context:
        business_section = ContextFormatter.format_business_context(context_info)
    
    return f"{schema_section}\n\n{business_section}"
```

---

## 5. 需要改进的地方

### 5.1 架构级别的改进

#### 问题 1: 模块导出不完整 🔴

**现状**:
```python
# __init__.py 全部为注释，功能未导出
```

**影响**:
- 外部代码无法清晰导入prompt功能
- 无法形成统一的公共API

**改进建议**:
```python
# __init__.py 应该导出核心功能
from .system import (
    SystemPromptBuilder,
    create_system_prompt,
    create_context_aware_system_prompt,
    DEFAULT_SYSTEM_PROMPT,
    SCHEMA_DISCOVERY_PROMPT,
    SQL_GENERATION_PROMPT,
    DATA_ANALYSIS_PROMPT,
    CHART_GENERATION_PROMPT,
)

from .stages import (
    StagePromptManager,
    get_stage_prompt,
    get_transition_prompt,
    get_stage_summary,
    INITIALIZATION_PROMPT,
    SCHEMA_DISCOVERY_PROMPT,
    SQL_GENERATION_PROMPT,
    # ... 其他预定义常量
)

from .templates import (
    PromptTemplate,
    PromptTemplateManager,
    ContextFormatter,
    format_request_prompt,
    format_stage_prompt,
    format_error_prompt,
    format_result_summary,
)

__all__ = [
    # system 模块
    "SystemPromptBuilder",
    "create_system_prompt",
    "create_context_aware_system_prompt",
    
    # stages 模块
    "StagePromptManager",
    "get_stage_prompt",
    "get_transition_prompt",
    
    # templates 模块
    "PromptTemplate",
    "PromptTemplateManager",
    "ContextFormatter",
    
    # 便利函数
    "format_request_prompt",
    "format_stage_prompt",
    "format_error_prompt",
    "format_result_summary",
]
```

#### 问题 2: AdaptivePromptGenerator 与 prompts 模块隔离 🔴

**现状**:
- runtime.py 中的 AdaptivePromptGenerator 不使用 prompts 模块
- 导致代码重复和维护困难

**影响**:
- 提示词逻辑分散在两个地方
- 修改提示词需要同时更新两个模块
- 无法利用 templates 模块的模板功能

**改进建议**:
```python
# runtime.py 应该集成 prompts 模块
from .prompts import (
    SystemPromptBuilder,
    StagePromptManager,
    PromptTemplateManager,
    ContextFormatter,
)

class AdaptivePromptGenerator:
    """改进版本：集成 prompts 模块"""
    
    def __init__(self, goal, tracker, stage=None, complexity=None):
        self.goal = goal
        self.tracker = tracker
        self.stage = stage
        self.complexity = complexity
        
        # 使用 prompts 模块的组件
        self._system_builder = SystemPromptBuilder()
        self._stage_manager = StagePromptManager()
        self._template_manager = PromptTemplateManager()
        self._context_formatter = ContextFormatter()
    
    def generate_system_prompt(self):
        """生成系统提示"""
        return self._system_builder.build_system_prompt(
            stage=self.stage,
            complexity=self.complexity
        )
    
    def generate_stage_prompt(self, context=None):
        """生成阶段提示"""
        return self._stage_manager.get_stage_prompt(
            stage=self.stage,
            context=context,
            complexity=self.complexity
        )
    
    def generate_error_prompt(self, error, iteration_count, tool_call_count):
        """生成错误处理提示"""
        return self._template_manager.format_template(
            "error_handling",
            error_message=str(error),
            error_type=type(error).__name__,
            current_stage=self.stage.value,
            iteration_count=iteration_count,
            tool_call_count=tool_call_count,
            suggested_actions=self._get_error_suggestions(error)
        )
```

#### 问题 3: 提示词的适应性不足 🟡

**现状**:
- 预定义常量硬编码为 MEDIUM 复杂度
- 不同复杂度任务无法自动使用对应的提示词

**影响**:
- SIMPLE/COMPLEX 任务的提示词没有充分优化
- 需要手动创建定制提示词

**改进建议**:
```python
# stages.py 应该支持动态预定义常量生成
# 或提供便利函数

def get_stage_prompt_for_complexity(stage, complexity):
    """获取特定复杂度的阶段提示"""
    manager = StagePromptManager()
    return manager.get_stage_prompt(stage, complexity=complexity)

# 或使用工厂函数
SIMPLE_PROMPTS = {
    stage: get_stage_prompt(stage, complexity=TaskComplexity.SIMPLE)
    for stage in ExecutionStage
}

COMPLEX_PROMPTS = {
    stage: get_stage_prompt(stage, complexity=TaskComplexity.COMPLEX)
    for stage in ExecutionStage
}
```

### 5.2 功能级别的改进

#### 问题 4: 缺乏动态提示词生成机制 🟡

**现状**:
- 所有提示词都是预定义的静态字符串
- 无法根据执行历史、错误模式等动态调整

**影响**:
- 无法从失败中学习
- 无法优化迭代策略
- 每次生成相同的提示

**改进建议**:
```python
class DynamicPromptOptimizer:
    """动态提示词优化器"""
    
    def __init__(self):
        self._system_builder = SystemPromptBuilder()
        self._error_patterns = {}  # 错误模式学习
        self._success_patterns = {}  # 成功模式学习
    
    def optimize_for_failure_pattern(self, error_type, error_count):
        """根据错误模式优化提示词"""
        if error_count > 3:
            # 错误过多，考虑改变策略
            return self._build_recovery_prompt()
        
        if error_type == "table_not_found":
            # 表不存在错误，强调上下文使用
            return self._build_context_awareness_prompt()
    
    def optimize_for_success_path(self, successful_steps):
        """根据成功路径优化提示词"""
        # 记录成功的执行路径，用于后续优化
        pass
```

#### 问题 5: 缺乏提示词版本管理 🟡

**现状**:
- 提示词没有版本号
- 无法回滚到之前的版本
- 难以追踪提示词变化的影响

**改进建议**:
```python
@dataclass
class PromptVersion:
    """提示词版本"""
    version: str  # e.g., "1.0.0", "1.1.0"
    name: str
    content: str
    created_at: datetime
    changelog: str
    metadata: Dict[str, Any]

class PromptVersionManager:
    """提示词版本管理器"""
    
    def create_version(self, name, content, changelog):
        """创建新版本"""
        version = PromptVersion(...)
        self._versions[name] = version
        self._version_history[name].append(version)
    
    def get_version(self, name, version_str=None):
        """获取特定版本"""
        if version_str is None:
            return self._versions[name]  # 最新版本
        return self._version_history[name][version_str]
    
    def rollback(self, name, version_str):
        """回滚到某个版本"""
        pass
```

#### 问题 6: 上下文注入的灵活性不足 🟡

**现状**:
- `_build_context_section()` 在系统提示中硬编码
- 上下文信息格式化逻辑分散

**影响**:
- 不同场景需要不同的上下文格式
- 无法复用格式化逻辑

**改进建议**:
```python
class ContextFormattingStrategy:
    """上下文格式化策略"""
    
    def format_for_schema_discovery(self, context):
        """Schema发现场景的格式化"""
        pass
    
    def format_for_sql_generation(self, context):
        """SQL生成场景的格式化"""
        pass
    
    def format_for_analysis(self, context):
        """数据分析场景的格式化"""
        pass

# 在 PromptTemplateManager 中使用
class PromptTemplateManager:
    def __init__(self):
        self._templates = {}
        self._context_strategies = {
            "schema_discovery": ContextFormattingStrategy().format_for_schema_discovery,
            "sql_generation": ContextFormattingStrategy().format_for_sql_generation,
            "analysis": ContextFormattingStrategy().format_for_analysis,
        }
```

### 5.3 代码质量改进

#### 问题 7: 代码重复度高 🟡

**现状**:
```python
# system.py 中定义了基础系统提示
# stages.py 中又单独定义了阶段目标和任务
# templates.py 中又有相似的模板内容
```

**影响**:
- 修改逻辑需要同时更新多个地方
- 难以保持一致性

**改进建议**:
```python
# 创建统一的提示内容库
class PromptContentLibrary:
    """提示内容库"""
    
    STAGE_OBJECTIVES = {
        ExecutionStage.SQL_GENERATION: "基于数据结构生成准确的SQL查询",
        # ...
    }
    
    KEY_TASKS = {
        ExecutionStage.SQL_GENERATION: [
            "设计查询逻辑和表关联",
            "生成符合语法的SQL查询",
            # ...
        ]
    }
    
    TOOL_RECOMMENDATIONS = {
        ExecutionStage.SQL_GENERATION: ["sql_generator", "sql_validator"],
        # ...
    }
```

#### 问题 8: 缺乏单元测试 🟡

**现状**:
- 没有看到专门的测试文件
- 提示词生成逻辑没有测试覆盖

**改进建议**:
```python
# tests/test_prompts.py
class TestSystemPromptBuilder:
    def test_base_prompt_contains_required_elements(self):
        builder = SystemPromptBuilder()
        prompt = builder._build_base_prompt()
        assert "角色定义" in prompt
        assert "核心能力" in prompt
    
    def test_stage_prompts_completeness(self):
        builder = SystemPromptBuilder()
        prompts = builder._build_stage_prompts()
        assert len(prompts) == 8  # 8个执行阶段
    
    def test_context_aware_prompt_includes_schema(self):
        builder = SystemPromptBuilder()
        context = ContextInfo(tables=[{"name": "test_table"}])
        prompt = builder.build_context_aware_prompt(context, stage=None, complexity=None)
        assert "test_table" in prompt

class TestPromptTemplateManager:
    def test_template_variable_substitution(self):
        manager = PromptTemplateManager()
        result = manager.format_template(
            "basic_request",
            placeholder="test placeholder",
            data_source_id=1,
            user_id="user1",
            complexity="medium",
            max_iterations=10,
            context_section=""
        )
        assert "test placeholder" in result
        assert "user1" in result
```

#### 问题 9: 文档不完整 🟡

**现状**:
- 没有看到详细的使用文档
- API文档需要从代码推断

**改进建议**:
```
prompts/
├── README.md                 # 使用文档
├── ARCHITECTURE.md           # 架构说明
├── API_REFERENCE.md          # API参考
├── EXAMPLES.md               # 使用示例
└── TROUBLESHOOTING.md        # 故障排除
```

### 5.4 性能级别的改进

#### 问题 10: 每次调用都重新生成提示 🟢

**现状**:
```python
# 每次调用 get_stage_prompt() 都重新格式化
manager = StagePromptManager()  # 每次创建新实例
return manager.get_stage_prompt(...)
```

**影响**:
- 不必要的计算和内存分配
- 在高频调用时可能影响性能

**改进建议**:
```python
class CachedPromptManager:
    """缓存的提示管理器"""
    
    def __init__(self):
        self._cache = {}
        self._managers = {
            'system': SystemPromptBuilder(),
            'stages': StagePromptManager(),
            'templates': PromptTemplateManager(),
        }
    
    def get_cached_prompt(self, stage, complexity):
        """获取缓存的提示"""
        cache_key = f"{stage.value}_{complexity.name}"
        if cache_key not in self._cache:
            self._cache[cache_key] = self._managers['stages'].get_stage_prompt(
                stage, complexity=complexity
            )
        return self._cache[cache_key]
```

---

## 6. 集成与使用现状

### 6.1 当前使用情况

**被引用的文件**:
- `runtime.py`: 未直接导入，但应该导入
- `stage_aware_adapter.py`: 可能需要使用
- `context_retriever.py`: 可能需要上下文格式化

**未被利用的功能**:
- `ContextFormatter` 的格式化功能
- 模板管理器的模板化能力
- 版本控制和优化机制

### 6.2 使用示例

**最佳使用模式** (应该但目前没有):
```python
# runtime.py 中的改进
from prompts import (
    SystemPromptBuilder,
    StagePromptManager,
    PromptTemplateManager,
    ContextFormatter,
    TaskComplexity,
    ExecutionStage,
)

class AgentRuntime:
    def __init__(self, config):
        self._system_builder = SystemPromptBuilder()
        self._stage_manager = StagePromptManager()
        self._template_manager = PromptTemplateManager()
        self._context_formatter = ContextFormatter()
    
    def prepare_execution_context(self, request, context):
        """准备执行上下文"""
        # 1. 获取系统提示
        system_prompt = self._system_builder.build_system_prompt(
            stage=request.stage,
            complexity=request.complexity
        )
        
        # 2. 获取阶段提示
        stage_prompt = self._stage_manager.get_stage_prompt(
            stage=request.stage,
            context=context,
            complexity=request.complexity
        )
        
        # 3. 格式化上下文
        formatted_context = self._format_context(context, request.stage)
        
        # 4. 组合所有部分
        full_prompt = f"{system_prompt}\n\n{stage_prompt}\n\n{formatted_context}"
        
        return full_prompt
    
    def _format_context(self, context, stage):
        """格式化上下文"""
        if stage == ExecutionStage.SQL_GENERATION:
            return self._context_formatter.format_schema_context(context)
        elif stage == ExecutionStage.ANALYSIS:
            return self._context_formatter.format_business_context(context)
```

---

## 7. 优先级总结

### 🔴 高优先级 (必须做)
1. **完成 `__init__.py` 导出** - 让模块API清晰可用
2. **集成 prompts 模块到 runtime.py** - 避免代码重复
3. **完成 AdaptivePromptGenerator 与 prompts 的集成** - 统一提示生成逻辑

### 🟡 中优先级 (应该做)
4. **增加动态提示词优化机制** - 从失败中学习
5. **完善上下文格式化策略** - 支持多场景
6. **添加单元测试** - 保证质量
7. **完善文档** - 提高可维护性

### 🟢 低优先级 (可以做)
8. **提示词版本管理** - 追踪变化
9. **性能优化(缓存)** - 提升响应速度
10. **消除代码重复** - 重构内容库

---

## 8. 总结

### 优势
✅ 提示词组织清晰，分层合理
✅ 支持上下文感知的动态生成
✅ 包含详细的执行指导和错误处理
✅ 代码易于理解和扩展
✅ 预定义常量提供便利使用

### 劣势
❌ 模块导出不完整，API不清晰
❌ 与 AdaptivePromptGenerator 隔离，代码重复
❌ 缺乏版本管理和动态优化
❌ 缺少单元测试
❌ 文档不完善

### 建议行动
1. 立即完成 `__init__.py` 导出
2. 集成 prompts 模块到 runtime.py 的 AdaptivePromptGenerator
3. 添加基本测试
4. 完善文档和使用示例
5. 根据实际使用情况迭代改进

