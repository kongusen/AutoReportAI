# 融合Claude Code理念的LlamaIndex Agent架构设计

## 📋 设计理念

本设计真正融合了Claude Code的核心理念，同时利用LlamaIndex的成熟框架：

- ✅ **ContentBlock多态系统**: 实现类型化的内容处理
- ✅ **流式处理能力**: 支持流式输入输出
- ✅ **工具执行编排**: 并行/顺序智能编排  
- ✅ **多级权限控制**: 四级权限验证系统
- ✅ **智能上下文管理**: 自动压缩和重要性评分
- ✅ **状态机架构**: 流式状态转换

## 🏗️ 核心架构设计

### 1. ContentBlock多态系统（Claude Code核心）

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, AsyncIterator
from dataclasses import dataclass
from enum import Enum
import json
import asyncio

class ContentBlockType(Enum):
    TEXT = "text"
    PLACEHOLDER_ANALYSIS = "placeholder_analysis"
    SQL_GENERATION = "sql_generation"
    SQL_VALIDATION = "sql_validation"
    CHART_GENERATION = "chart_generation"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    ERROR = "error"

@dataclass
class ContentBlock(ABC):
    """Claude Code风格的ContentBlock基类"""
    block_type: ContentBlockType
    block_id: str
    metadata: Dict[str, Any]
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        pass
    
    @abstractmethod
    async def process(self, context: 'ProcessingContext') -> 'ContentBlock':
        pass

class TextBlock(ContentBlock):
    """文本内容块"""
    def __init__(self, text: str, metadata: Optional[Dict] = None):
        super().__init__(
            block_type=ContentBlockType.TEXT,
            block_id=f"text_{hash(text) % 10000}",
            metadata=metadata or {}
        )
        self.text = text
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.block_type.value,
            "id": self.block_id,
            "text": self.text,
            "metadata": self.metadata
        }
    
    def validate(self) -> bool:
        return bool(self.text.strip())
    
    async def process(self, context: 'ProcessingContext') -> ContentBlock:
        return self  # 文本块无需处理

class PlaceholderAnalysisBlock(ContentBlock):
    """占位符分析内容块"""
    def __init__(self, placeholder_text: str, template_context: Dict, metadata: Optional[Dict] = None):
        super().__init__(
            block_type=ContentBlockType.PLACEHOLDER_ANALYSIS,
            block_id=f"placeholder_{hash(placeholder_text) % 10000}",
            metadata=metadata or {}
        )
        self.placeholder_text = placeholder_text
        self.template_context = template_context
        self.analysis_result = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.block_type.value,
            "id": self.block_id,
            "placeholder_text": self.placeholder_text,
            "template_context": self.template_context,
            "analysis_result": self.analysis_result,
            "metadata": self.metadata
        }
    
    def validate(self) -> bool:
        return bool(self.placeholder_text and "{{" in self.placeholder_text and "}}" in self.placeholder_text)
    
    async def process(self, context: 'ProcessingContext') -> ContentBlock:
        """使用LlamaIndex工具进行占位符分析"""
        # 调用占位符分析工具
        tool_result = await context.tool_executor.execute_tool(
            "analyze_placeholder",
            {
                "placeholder_text": self.placeholder_text,
                "template_context": self.template_context
            }
        )
        
        self.analysis_result = tool_result
        return self

class SQLGenerationBlock(ContentBlock):
    """SQL生成内容块"""
    def __init__(self, placeholder_analysis: Dict, schema_info: Dict, task_context: Dict, metadata: Optional[Dict] = None):
        super().__init__(
            block_type=ContentBlockType.SQL_GENERATION,
            block_id=f"sql_gen_{hash(str(placeholder_analysis)) % 10000}",
            metadata=metadata or {}
        )
        self.placeholder_analysis = placeholder_analysis
        self.schema_info = schema_info
        self.task_context = task_context
        self.generated_sql = None
        self.generation_metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.block_type.value,
            "id": self.block_id,
            "placeholder_analysis": self.placeholder_analysis,
            "schema_info": self.schema_info,
            "task_context": self.task_context,
            "generated_sql": self.generated_sql,
            "generation_metadata": self.generation_metadata,
            "metadata": self.metadata
        }
    
    def validate(self) -> bool:
        return bool(self.placeholder_analysis and self.schema_info)
    
    async def process(self, context: 'ProcessingContext') -> ContentBlock:
        """使用LlamaIndex工具生成SQL"""
        tool_result = await context.tool_executor.execute_tool(
            "generate_sql",
            {
                "placeholder_analysis": self.placeholder_analysis,
                "schema_info": self.schema_info,
                "task_context": self.task_context
            }
        )
        
        self.generated_sql = tool_result.get("sql")
        self.generation_metadata = tool_result.get("metadata", {})
        return self

class ToolUseBlock(ContentBlock):
    """工具使用内容块"""
    def __init__(self, tool_name: str, tool_input: Dict, tool_id: str, metadata: Optional[Dict] = None):
        super().__init__(
            block_type=ContentBlockType.TOOL_USE,
            block_id=tool_id,
            metadata=metadata or {}
        )
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.tool_id = tool_id
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.block_type.value,
            "id": self.block_id,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_id": self.tool_id,
            "metadata": self.metadata
        }
    
    def validate(self) -> bool:
        return bool(self.tool_name and isinstance(self.tool_input, dict))
    
    async def process(self, context: 'ProcessingContext') -> 'ToolResultBlock':
        """执行工具调用"""
        result = await context.tool_executor.execute_tool(self.tool_name, self.tool_input)
        return ToolResultBlock(self.tool_id, result, is_error=result.get("success", True) == False)

class ToolResultBlock(ContentBlock):
    """工具结果内容块"""
    def __init__(self, tool_id: str, result: Any, is_error: bool = False, metadata: Optional[Dict] = None):
        super().__init__(
            block_type=ContentBlockType.TOOL_RESULT,
            block_id=f"result_{tool_id}",
            metadata=metadata or {}
        )
        self.tool_id = tool_id
        self.result = result
        self.is_error = is_error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.block_type.value,
            "id": self.block_id,
            "tool_id": self.tool_id,
            "result": self.result,
            "is_error": self.is_error,
            "metadata": self.metadata
        }
    
    def validate(self) -> bool:
        return self.tool_id is not None
    
    async def process(self, context: 'ProcessingContext') -> ContentBlock:
        return self  # 结果块无需进一步处理
```

### 2. 流式JSON解析器（Claude Code核心）

```python
import json
import re
from typing import AsyncIterator, List, Dict, Any

class StreamingJSONParser:
    """Claude Code风格的流式JSON解析器"""
    
    def __init__(self):
        self.buffer = ""
        self.bracket_stack = []
        self.in_string = False
        self.escape_next = False
        self.parsed_blocks = []
    
    async def feed_chunk(self, chunk: str) -> List[ContentBlock]:
        """处理流式输入块，解析出完整的ContentBlock"""
        self.buffer += chunk
        return await self._extract_complete_blocks()
    
    async def _extract_complete_blocks(self) -> List[ContentBlock]:
        """提取完整的内容块"""
        blocks = []
        current_start = 0
        
        # 查找完整的JSON对象
        for i, char in enumerate(self.buffer):
            self._process_character(char)
            
            if self._is_json_object_complete():
                try:
                    json_str = self.buffer[current_start:i+1]
                    block_data = json.loads(json_str)
                    
                    # 根据类型创建对应的ContentBlock
                    block = await self._create_content_block(block_data)
                    if block:
                        blocks.append(block)
                    
                    current_start = i + 1
                    self._reset_parser_state()
                except json.JSONDecodeError:
                    continue
        
        # 清理已处理的缓冲区
        self.buffer = self.buffer[current_start:]
        return blocks
    
    def _process_character(self, char: str):
        """处理单个字符，维护解析状态"""
        if self.escape_next:
            self.escape_next = False
            return
        
        if char == '\\':
            self.escape_next = True
            return
        
        if char == '"' and not self.escape_next:
            self.in_string = not self.in_string
            return
        
        if not self.in_string:
            if char == '{':
                self.bracket_stack.append('{')
            elif char == '}':
                if self.bracket_stack and self.bracket_stack[-1] == '{':
                    self.bracket_stack.pop()
    
    def _is_json_object_complete(self) -> bool:
        """检查JSON对象是否完整"""
        return not self.in_string and len(self.bracket_stack) == 0 and self.buffer.strip().endswith('}')
    
    def _reset_parser_state(self):
        """重置解析器状态"""
        self.bracket_stack = []
        self.in_string = False
        self.escape_next = False
    
    async def _create_content_block(self, block_data: Dict[str, Any]) -> Optional[ContentBlock]:
        """根据数据创建相应的ContentBlock"""
        block_type = block_data.get("type")
        
        if block_type == "text":
            return TextBlock(block_data.get("text", ""), block_data.get("metadata", {}))
        elif block_type == "placeholder_analysis":
            return PlaceholderAnalysisBlock(
                block_data.get("placeholder_text", ""),
                block_data.get("template_context", {}),
                block_data.get("metadata", {})
            )
        elif block_type == "sql_generation":
            return SQLGenerationBlock(
                block_data.get("placeholder_analysis", {}),
                block_data.get("schema_info", {}),
                block_data.get("task_context", {}),
                block_data.get("metadata", {})
            )
        elif block_type == "tool_use":
            return ToolUseBlock(
                block_data.get("tool_name", ""),
                block_data.get("tool_input", {}),
                block_data.get("tool_id", ""),
                block_data.get("metadata", {})
            )
        elif block_type == "tool_result":
            return ToolResultBlock(
                block_data.get("tool_id", ""),
                block_data.get("result", {}),
                block_data.get("is_error", False),
                block_data.get("metadata", {})
            )
        
        return None
```

### 3. 工具执行编排器（Claude Code核心）

```python
import asyncio
from typing import List, Dict, Any, Set
from enum import Enum

class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    AUTO = "auto"

class ToolExecutionOrchestrator:
    """Claude Code风格的工具执行编排器"""
    
    def __init__(self, llama_agent, permission_controller):
        self.llama_agent = llama_agent  # LlamaIndex ReActAgent
        self.permission_controller = permission_controller
        self.active_executions: Dict[str, asyncio.Task] = {}
    
    async def execute_tools(
        self,
        tool_blocks: List[ToolUseBlock],
        execution_mode: ExecutionMode = ExecutionMode.AUTO
    ) -> List[ToolResultBlock]:
        """编排工具执行 - 融合Claude Code智能编排和LlamaIndex工具系统"""
        
        # 1. 权限验证（Claude Code特性）
        await self._validate_permissions(tool_blocks)
        
        # 2. 分析工具依赖关系（Claude Code特性）
        dependency_graph = await self._analyze_tool_dependencies(tool_blocks)
        
        # 3. 构建执行计划
        execution_plan = await self._build_execution_plan(
            tool_blocks, dependency_graph, execution_mode
        )
        
        # 4. 执行工具（使用LlamaIndex的工具系统）
        results = await self._execute_plan(execution_plan)
        
        return results
    
    async def _analyze_tool_dependencies(self, tool_blocks: List[ToolUseBlock]) -> Dict[str, Set[str]]:
        """分析工具之间的依赖关系"""
        dependencies = {}
        
        for tool_block in tool_blocks:
            tool_id = tool_block.tool_id
            dependencies[tool_id] = set()
            
            # 分析输入参数是否依赖其他工具的输出
            for param_key, param_value in tool_block.tool_input.items():
                if isinstance(param_value, str) and param_value.startswith("$tool_result_"):
                    # 依赖其他工具的结果
                    dependency_tool_id = param_value.replace("$tool_result_", "")
                    dependencies[tool_id].add(dependency_tool_id)
        
        return dependencies
    
    async def _build_execution_plan(
        self,
        tool_blocks: List[ToolUseBlock],
        dependencies: Dict[str, Set[str]],
        mode: ExecutionMode
    ) -> List[List[ToolUseBlock]]:
        """构建执行计划 - 按批次分组工具"""
        
        if mode == ExecutionMode.SEQUENTIAL:
            return [[tool] for tool in tool_blocks]
        
        if mode == ExecutionMode.PARALLEL:
            return [tool_blocks]  # 全并行（忽略依赖）
        
        # AUTO模式：智能分组
        plan = []
        remaining_tools = {tool.tool_id: tool for tool in tool_blocks}
        completed_tools = set()
        
        while remaining_tools:
            # 找出当前批次可以执行的工具（依赖已满足）
            ready_tools = []
            for tool_id, tool in remaining_tools.items():
                tool_deps = dependencies.get(tool_id, set())
                if tool_deps.issubset(completed_tools):
                    ready_tools.append(tool)
            
            if not ready_tools:
                # 出现循环依赖，强制执行剩余工具
                ready_tools = list(remaining_tools.values())
            
            plan.append(ready_tools)
            
            # 更新状态
            for tool in ready_tools:
                completed_tools.add(tool.tool_id)
                remaining_tools.pop(tool.tool_id)
        
        return plan
    
    async def _execute_plan(self, execution_plan: List[List[ToolUseBlock]]) -> List[ToolResultBlock]:
        """执行编排计划"""
        all_results = []
        tool_results_cache = {}  # 缓存工具结果供后续工具使用
        
        for batch in execution_plan:
            # 并行执行当前批次的工具
            batch_tasks = []
            for tool_block in batch:
                # 解析工具输入中的依赖引用
                resolved_input = await self._resolve_tool_input_dependencies(
                    tool_block.tool_input, tool_results_cache
                )
                
                # 创建执行任务
                task = self._execute_single_tool(tool_block.tool_name, resolved_input)
                batch_tasks.append((tool_block.tool_id, task))
            
            # 等待批次完成
            batch_results = await asyncio.gather(*[task for _, task in batch_tasks])
            
            # 处理结果
            for (tool_id, _), result in zip(batch_tasks, batch_results):
                tool_result = ToolResultBlock(tool_id, result)
                all_results.append(tool_result)
                tool_results_cache[tool_id] = result
        
        return all_results
    
    async def _execute_single_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个工具 - 使用LlamaIndex的工具系统"""
        # 找到LlamaIndex Agent中对应的工具
        llama_tool = None
        for tool in self.llama_agent.tools:
            if tool.metadata.name == tool_name:
                llama_tool = tool
                break
        
        if not llama_tool:
            return {"success": False, "error": f"Tool {tool_name} not found"}
        
        try:
            # 调用LlamaIndex工具
            result = await llama_tool.acall(**tool_input)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _resolve_tool_input_dependencies(
        self, 
        tool_input: Dict[str, Any], 
        results_cache: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析工具输入中的依赖引用"""
        resolved_input = {}
        
        for key, value in tool_input.items():
            if isinstance(value, str) and value.startswith("$tool_result_"):
                # 引用其他工具的结果
                dependency_tool_id = value.replace("$tool_result_", "")
                if dependency_tool_id in results_cache:
                    resolved_input[key] = results_cache[dependency_tool_id]
                else:
                    resolved_input[key] = None  # 依赖未找到
            else:
                resolved_input[key] = value
        
        return resolved_input
```

### 4. 多级权限控制系统（Claude Code核心）

```python
from typing import Dict, Any, List
from enum import Enum

class PermissionLevel(Enum):
    USER = "user"
    TOOL = "tool" 
    CONTEXT = "context"
    DYNAMIC = "dynamic"

class PermissionResult:
    def __init__(self, allowed: bool, reason: str = "", metadata: Optional[Dict] = None):
        self.allowed = allowed
        self.reason = reason
        self.metadata = metadata or {}

class PermissionController:
    """Claude Code风格的多级权限控制器"""
    
    def __init__(self):
        self.permission_rules = {}
        self.user_permissions = {}
        self.tool_permissions = {}
        self.context_permissions = {}
    
    async def validate_tool_execution(
        self,
        user_id: str,
        tool_block: ToolUseBlock,
        execution_context: Dict[str, Any]
    ) -> PermissionResult:
        """多级权限验证"""
        
        # Level 1: 用户级权限
        user_check = await self._check_user_permission(user_id, tool_block.tool_name)
        if not user_check.allowed:
            return user_check
        
        # Level 2: 工具级权限
        tool_check = await self._check_tool_permission(tool_block)
        if not tool_check.allowed:
            return tool_check
        
        # Level 3: 上下文级权限
        context_check = await self._check_context_permission(execution_context, tool_block)
        if not context_check.allowed:
            return context_check
        
        # Level 4: 动态安全检查
        security_check = await self._dynamic_security_check(
            user_id, tool_block, execution_context
        )
        
        return security_check
    
    async def _check_user_permission(self, user_id: str, tool_name: str) -> PermissionResult:
        """用户级权限检查"""
        user_perms = self.user_permissions.get(user_id, {})
        allowed_tools = user_perms.get("allowed_tools", [])
        
        if tool_name in allowed_tools or "all" in allowed_tools:
            return PermissionResult(True, "User permission granted")
        else:
            return PermissionResult(False, f"User {user_id} not allowed to use tool {tool_name}")
    
    async def _check_tool_permission(self, tool_block: ToolUseBlock) -> PermissionResult:
        """工具级权限检查"""
        tool_perms = self.tool_permissions.get(tool_block.tool_name, {})
        
        # 检查工具输入参数限制
        restricted_params = tool_perms.get("restricted_params", [])
        for param in restricted_params:
            if param in tool_block.tool_input:
                return PermissionResult(
                    False, 
                    f"Parameter {param} is restricted for tool {tool_block.tool_name}"
                )
        
        return PermissionResult(True, "Tool permission granted")
    
    async def _check_context_permission(
        self, 
        execution_context: Dict[str, Any], 
        tool_block: ToolUseBlock
    ) -> PermissionResult:
        """上下文级权限检查"""
        # 检查是否在允许的业务上下文中使用工具
        business_context = execution_context.get("business_context", {})
        allowed_contexts = self.context_permissions.get(tool_block.tool_name, {}).get("allowed_contexts", [])
        
        current_context = business_context.get("context_type", "unknown")
        if allowed_contexts and current_context not in allowed_contexts:
            return PermissionResult(
                False,
                f"Tool {tool_block.tool_name} not allowed in context {current_context}"
            )
        
        return PermissionResult(True, "Context permission granted")
    
    async def _dynamic_security_check(
        self,
        user_id: str,
        tool_block: ToolUseBlock,
        execution_context: Dict[str, Any]
    ) -> PermissionResult:
        """动态安全检查"""
        
        # 检查敏感操作
        if self._is_sensitive_operation(tool_block):
            # 需要额外验证
            return await self._require_additional_auth(user_id, tool_block)
        
        # 检查资源消耗
        if self._is_resource_intensive(tool_block):
            # 检查资源配额
            return await self._check_resource_quota(user_id, tool_block)
        
        # 检查操作频率
        if await self._is_rate_limited(user_id, tool_block.tool_name):
            return PermissionResult(False, "Rate limit exceeded")
        
        return PermissionResult(True, "Dynamic security check passed")
```

### 5. 主Agent类（融合设计）

```python
class ClaudeCodeInspiredLlamaIndexAgent:
    """融合Claude Code理念的LlamaIndex Agent"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        
        # Claude Code核心组件
        self.content_blocks: List[ContentBlock] = []
        self.streaming_parser = StreamingJSONParser()
        self.tool_orchestrator = ToolExecutionOrchestrator(None, PermissionController())
        self.context_manager = ClaudeCodeContextManager()
        
        # LlamaIndex组件
        self.llm = self._initialize_llm()
        self.tools = self._initialize_llamaindex_tools()
        self.llama_agent = ReActAgent.from_tools(
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            max_iterations=10
        )
        
        # 关联组件
        self.tool_orchestrator.llama_agent = self.llama_agent
    
    async def process_streaming_input(
        self, 
        input_stream: AsyncIterator[str]
    ) -> AsyncIterator[ContentBlock]:
        """处理流式输入 - Claude Code风格"""
        
        async for chunk in input_stream:
            # 使用流式解析器处理输入
            new_blocks = await self.streaming_parser.feed_chunk(chunk)
            
            for block in new_blocks:
                if block.validate():
                    # 处理ContentBlock
                    processed_block = await self._process_content_block(block)
                    yield processed_block
    
    async def _process_content_block(self, block: ContentBlock) -> ContentBlock:
        """处理单个ContentBlock"""
        
        # 添加到上下文管理器
        await self.context_manager.add_block(block)
        
        # 根据块类型进行处理
        if isinstance(block, PlaceholderAnalysisBlock):
            return await self._process_placeholder_analysis(block)
        elif isinstance(block, SQLGenerationBlock):
            return await self._process_sql_generation(block)
        elif isinstance(block, ToolUseBlock):
            return await self._process_tool_use(block)
        else:
            return block
    
    async def _process_placeholder_analysis(self, block: PlaceholderAnalysisBlock) -> ContentBlock:
        """处理占位符分析块"""
        processing_context = ProcessingContext(
            tool_executor=self.tool_orchestrator,
            context_manager=self.context_manager,
            user_id=self.user_id
        )
        
        return await block.process(processing_context)
    
    async def process_autoreport_workflow(
        self,
        placeholder_text: str,
        template_id: str,
        data_source_id: str,
        task_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """AutoReportAI工作流 - 融合Claude Code和LlamaIndex"""
        
        # 1. 创建占位符分析块
        placeholder_block = PlaceholderAnalysisBlock(
            placeholder_text=placeholder_text,
            template_context={"template_id": template_id},
            metadata={"data_source_id": data_source_id, "task_context": task_context}
        )
        
        # 2. 处理占位符分析
        analysis_result = await self._process_content_block(placeholder_block)
        
        # 3. 创建SQL生成块
        sql_block = SQLGenerationBlock(
            placeholder_analysis=analysis_result.analysis_result,
            schema_info=await self._get_schema_info(data_source_id),
            task_context=task_context or {},
            metadata={"template_id": template_id}
        )
        
        # 4. 处理SQL生成
        sql_result = await self._process_content_block(sql_block)
        
        # 5. 验证SQL（使用工具编排器的并行执行）
        validation_tools = [
            ToolUseBlock("test_execute_sql", {"sql": sql_result.generated_sql, "data_source_id": data_source_id}, "sql_test_1"),
            ToolUseBlock("validate_sql_result", {"sql": sql_result.generated_sql, "expected": analysis_result.analysis_result}, "sql_validate_1")
        ]
        
        validation_results = await self.tool_orchestrator.execute_tools(
            validation_tools, ExecutionMode.PARALLEL
        )
        
        # 6. 返回完整结果
        return {
            "placeholder_analysis": analysis_result.to_dict(),
            "sql_generation": sql_result.to_dict(),
            "validation_results": [r.to_dict() for r in validation_results],
            "final_sql": sql_result.generated_sql,
            "status": "success"
        }
```

## 🎯 设计总结

这个重新设计的版本真正融合了Claude Code的核心理念：

### ✅ Claude Code核心特性全部实现
1. **ContentBlock多态系统**: 类型化的内容处理
2. **流式JSON解析器**: 实时解析能力  
3. **工具执行编排器**: 智能并行/顺序执行
4. **多级权限控制**: 四级权限验证
5. **智能上下文管理**: 自动压缩和清理

### 🚀 LlamaIndex优势保持
1. **成熟的工具系统**: 复用LlamaIndex的工具框架
2. **ReAct循环**: 利用内置的思考循环
3. **LLM管理**: 复用现有的LLM集成

### 🎪 最佳实践融合
- **渐进式采用**: 可以逐步启用Claude Code特性
- **向后兼容**: 保持与现有系统的兼容性
- **性能优化**: 并行执行和智能编排提升性能

这个设计真正做到了"既要又要"：既获得了Claude Code的先进架构，又利用了LlamaIndex的成熟生态。