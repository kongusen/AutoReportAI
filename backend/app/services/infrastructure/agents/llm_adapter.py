"""
LLM 适配器

将容器的 LLM 服务适配为 Loom 的 BaseLLM 接口
基于现有的 Container 和 RealLLMServiceAdapter 实现
"""

from __future__ import annotations

import json
import logging
import asyncio
import contextvars
import tiktoken
from typing import Any, Dict, List, Optional, Callable

from loom.interfaces.llm import BaseLLM

from .types import LLMConfig, ExecutionStage

logger = logging.getLogger(__name__)

# 上下文变量
_CURRENT_USER_ID = contextvars.ContextVar("loom_agent_user_id", default="")
_CURRENT_STAGE = contextvars.ContextVar("loom_agent_stage", default="agent_runtime")
_CURRENT_OUTPUT_KIND = contextvars.ContextVar("loom_agent_output_kind", default="text")


class ContainerLLMAdapter(BaseLLM):
    """Container LLM 适配器

    将容器的 LLM 服务桥接到 Loom 的 BaseLLM 接口
    基于现有的 RealLLMServiceAdapter 实现
    """

    def __init__(
        self,
        service: Any,
        logger: Optional[logging.Logger] = None, 
        default_user_id: str = "system",
        tool_call_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> None:
        """初始化适配器

        Args:
            service: 容器的 LLM 服务 (RealLLMServiceAdapter)
            logger: 日志器
            default_user_id: 默认用户 ID
            tool_call_callback: 工具调用回调函数
        """
        if not hasattr(service, "ask"):
            raise ValueError("Container LLM service must expose an async 'ask' method.")

        self._service = service
        self._logger = logger or logging.getLogger(self.__class__.__name__)
        self._default_user_id = default_user_id
        self._model_name = getattr(service, "default_model", "container-llm")
        self._tool_call_callback = tool_call_callback
        
        # 初始化 tiktoken tokenizer
        try:
            # 使用 GPT-4 的 tokenizer (cl100k_base)
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            self._logger.warning(f"⚠️ 无法初始化 tiktoken，将使用简单估算: {e}")
            self._tokenizer = None

    @property
    def model_name(self) -> str:
        """模型名称"""
        return self._model_name

    @property
    def supports_tools(self) -> bool:
        """🔥 关键修复：标记此LLM支持工具调用

        这会让Loom的AgentExecutor调用generate_with_tools()而不是generate()
        从而注入工具调用指令，使LLM能够正确调用工具
        """
        return True

    def count_tokens(self, text: str) -> int:
        """精确计算 token 数量"""
        if self._tokenizer:
            try:
                return len(self._tokenizer.encode(text))
            except Exception as e:
                self._logger.warning(f"⚠️ tiktoken 计算失败，使用估算: {e}")
                return self._estimate_tokens(text)
        else:
            return self._estimate_tokens(text)
    
    def _estimate_tokens(self, text: str) -> int:
        """估算 token 数量（备用方法）"""
        # 简单估算：中文字符按 1.5 个 token 计算，英文按 0.25 个 token 计算
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.25)
    
    def count_tokens_in_messages(self, messages: List[Dict]) -> int:
        """计算消息列表的总 token 数"""
        total_tokens = 0
        for message in messages:
            content = message.get('content', '')
            if isinstance(content, str):
                total_tokens += self.count_tokens(content)
            elif isinstance(content, list):
                # 处理结构化内容
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        total_tokens += self.count_tokens(item['text'])
        return total_tokens

    async def generate_response(self, messages: List[Dict], **kwargs) -> str:
        """兼容性方法：使用 generate() 实现 generate_response 接口"""
        self._logger.debug(f"🧠 [ContainerLLMAdapter] generate_response called with {len(messages)} messages")
        try:
            result = await self.generate(messages)
            # 确保返回字符串
            if isinstance(result, str):
                return result
            elif isinstance(result, dict):
                return result.get("content", str(result))
            else:
                return str(result)
        except Exception as e:
            self._logger.error(f"❌ [ContainerLLMAdapter] generate_response failed: {e}")
            raise
    async def generate(self, messages: List[Dict]) -> str:
        """
        生成 LLM 响应
        
        🔥 关键改进：合并所有 messages（包括 Loom 注入的 system messages）
        这样可以确保 ContextRetriever 注入的 schema context 被传递给 LLM
        """
        # 🔥 合并所有 messages 为一个完整的 prompt
        prompt = self._compose_full_prompt(messages)
        user_id = self._extract_user_id(messages)

        self._logger.info(f"🧠 [ContainerLLMAdapter] Composed prompt length: {len(prompt)} chars")
        self._logger.debug(f"   Message count: {len(messages)}, user_id: {user_id}")

        try:
            response = await self._service.ask(
                user_id=user_id,
                prompt=prompt,
                response_format={"type": "json_object"},
                llm_policy={
                    "stage": _CURRENT_STAGE.get("agent_runtime"),
                    "output_kind": _CURRENT_OUTPUT_KIND.get("text"),
                },
            )

            # ✅ 添加响应验证
            if not response:
                self._logger.error("❌ 容器LLM服务返回空响应")
                raise ValueError("LLM returned empty response")

            if isinstance(response, str) and not response.strip():
                self._logger.error("❌ 响应为空字符串")
                raise ValueError("LLM returned empty string")

        except Exception as exc:  # pragma: no cover - container side errors
            self._logger.error("❌ 容器LLM服务失败: %s", exc)
            raise

        if isinstance(response, dict):
            for key in ("response", "result", "text", "sql", "content"):
                if response.get(key):
                    self._logger.debug(
                        "🧠 [ContainerLLMAdapter] user=%s key=%s preview=%s",
                        user_id,
                        key,
                        str(response[key])[:80],
                    )
                    return response[key]
            return str(response)
        
        self._logger.debug(
            "🧠 [ContainerLLMAdapter] user=%s raw_response=%s", user_id, str(response)[:80]
        )
        return str(response)

    async def generate_with_tools(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        """
        生成带工具调用的响应
        
        🔥 关键功能：
        1. 将工具描述注入到 system message 中
        2. 指示 LLM 以 JSON 格式返回响应（包含 tool_calls）
        3. 解析 LLM 响应，提取工具调用
        
        返回格式：
        {
            "content": "...",       # LLM 的文本响应
            "tool_calls": [         # 工具调用数组（可选）
                {
                    "id": "unique_id",
                    "type": "function",
                    "function": {
                        "name": "tool_name",
                        "arguments": "{...}"  # JSON 字符串
                    }
                }
            ]
        }
        """
        import uuid

        # 🔥 Step 1: 构建工具描述
        tools_desc = self._format_tools_description(tools)
        
        # 📊 监控 Token 使用
        tools_tokens = self.count_tokens(tools_desc)
        self._logger.info(f"📊 工具描述 tokens: {tools_tokens}")

        # 🔥 Step 2: 添加工具调用指令到 system message
        tool_system_msg = f"""
# SQL生成Agent - 智能执行模式

**核心任务**: 根据用户需求生成准确的SQL查询

**执行流程**:
1. **分析需求**: 理解用户要查询什么数据
2. **获取表结构**: 使用schema工具了解数据库结构
3. **生成SQL**: 基于表结构生成SQL查询
4. **验证SQL**: 确保SQL语法正确和逻辑合理

**可用工具**:
{tools_desc}

## 响应格式

**调用工具**:
```json
{{
  "reasoning": "需要了解ods_refund表结构",
  "action": "tool_call", 
  "tool_calls": [{{"name": "schema_discovery", "arguments": {{"tables": ["ods_refund"], "discovery_type": "columns"}}}}]
}}
```

**生成SQL**:
```json
{{
  "reasoning": "已了解表结构，生成SQL",
  "action": "finish",
  "content": "SELECT COUNT(*) FROM ods_refund WHERE status = '退货成功'"
}}
```

**关键原则**:
- ✅ **优先使用schema_retrieval**: 直接获取特定表结构，不要使用schema_discovery
- ✅ **避免重复调用**: 不要重复调用相同工具
- ✅ **生成有效SQL**: 确保SQL语法正确，字段存在
- ❌ **不要使用schema_discovery**: 会返回所有表信息，浪费资源
- ❌ **不要无限循环**: 最多2次工具调用，然后必须生成SQL
- ❌ **不要空响应**: 必须返回有效的SQL查询

**示例**:
用户: "统计退货成功的退货单数量"
1. 分析需求：需要统计退货单数量，条件是状态为"退货成功"
2. 调用schema_retrieval获取ods_refund表结构: `{{"name": "schema_retrieval", "arguments": {{"table_names": ["ods_refund"]}}}}`
3. 基于ods_refund表生成SQL: "SELECT COUNT(*) FROM ods_refund WHERE status = '退货成功'"
4. 完成任务

**重要**: 优先使用schema_retrieval工具获取特定表结构，避免使用schema_discovery获取所有表信息！
"""

        # 🔥 Step 3: 注入工具调用指令
        enhanced_messages = [{"role": "system", "content": tool_system_msg}] + messages

        # 🔥 Step 4: 调用 LLM
        prompt = self._compose_full_prompt(enhanced_messages)
        user_id = self._extract_user_id(enhanced_messages)

        # 计算 token 数量
        input_tokens = self.count_tokens(prompt)
        self._logger.info(f"🔧 [ContainerLLMAdapter] Calling LLM with {len(tools)} tools available")
        self._logger.info(f"📊 [ContainerLLMAdapter] Input tokens: {input_tokens}")
        
        # 📝 [DEBUG] 添加详细调试日志
        self._logger.info(f"📝 [DEBUG] 发送给 LLM 的 prompt 长度: {len(prompt)} 字符")
        self._logger.info(f"📝 [DEBUG] 工具数量: {len(tools)}")
        self._logger.info(f"📝 [DEBUG] Prompt 前500字符:\n{prompt[:500]}")

        try:
            response = await self._service.ask(
                user_id=user_id,
                prompt=prompt,
                response_format={"type": "json_object"},
                llm_policy={
                    "stage": _CURRENT_STAGE.get("agent_runtime"),
                    "output_kind": _CURRENT_OUTPUT_KIND.get("text"),
                },
            )

            # ✅ 添加响应验证
            if not response:
                self._logger.error("❌ 容器LLM服务返回空响应")
                raise ValueError("LLM returned empty response")

            if isinstance(response, str) and not response.strip():
                self._logger.error("❌ 响应为空字符串")
                raise ValueError("LLM returned empty string")

        except Exception as exc:
            self._logger.error("❌ 容器LLM服务失败: %s", exc)
            raise

        # 🔥 Step 5: 解析响应
        result = self._parse_tool_response(response)

        # 📝 [DEBUG] 添加响应解析调试日志
        self._logger.info(f"📝 [DEBUG] LLM 原始响应: {str(response)[:500]}")
        self._logger.info(f"📝 [DEBUG] tool_calls 数量: {len(result.get('tool_calls', []))}")

        # 记录解析结果
        if isinstance(result, dict):
            output_content = result.get('content', '')
            tool_calls = result.get('tool_calls', [])

            # 计算输出 tokens
            if isinstance(output_content, str):
                output_tokens = self.count_tokens(output_content)
                self._logger.info(f"📊 [ContainerLLMAdapter] Output tokens: {output_tokens}")

            # 记录工具调用情况
            if tool_calls:
                self._logger.info(f"✅ [ContainerLLMAdapter] 成功解析 {len(tool_calls)} 个工具调用")
                for i, tc in enumerate(tool_calls):
                    self._logger.info(f"   工具 {i+1}: {tc.get('name')} (id: {tc.get('id')})")
            else:
                self._logger.info(f"✅ [ContainerLLMAdapter] LLM 返回最终答案（无工具调用）")

        return result

    def _format_tools_description(self, tools: List[Dict]) -> str:
        """
        格式化工具描述
        
        Loom 的工具格式：
        {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "...",
                "parameters": {...}
            }
        }
        """
        lines = []
        for tool in tools:
            # 🔥 处理 Loom 的工具格式
            if "function" in tool:
                func_spec = tool["function"]
                name = func_spec.get("name", "unknown")
                desc = func_spec.get("description", "")
                params = func_spec.get("parameters", {})
            else:
                # 兼容其他格式
                name = tool.get("name", "unknown")
                desc = tool.get("description", "")
                params = tool.get("parameters", {})

            # 提取参数信息
            params_desc = []
            if isinstance(params, dict):
                properties = params.get("properties", {})
                required = params.get("required", [])

                for param_name, param_info in properties.items():
                    param_type = param_info.get("type", "any")
                    param_desc = param_info.get("description", "")
                    is_required = param_name in required
                    req_marker = "必需" if is_required else "可选"
                    params_desc.append(f"  - {param_name} ({param_type}, {req_marker}): {param_desc}")

            tool_block = f"### {name}\n{desc}\n"
            if params_desc:
                tool_block += "参数：\n" + "\n".join(params_desc)

            lines.append(tool_block)

        return "\n\n".join(lines)

    def _parse_tool_response(self, response: Any) -> Dict:
        """
        解析 LLM 响应，提取工具调用
        
        期望的 response 格式：
        {
            "reasoning": "...",
            "action": "tool_call" | "finish",
            "tool_calls": [...],  # 如果 action == "tool_call"
            "content": "..."      # 如果 action == "finish"
        }
        """
        import uuid

        # 处理不同的响应格式
        if isinstance(response, str):
            try:
                parsed = json.loads(response)
            except json.JSONDecodeError:
                # 如果不是 JSON，当作普通文本响应
                self._logger.warning("⚠️ LLM response is not JSON, treating as text")
                return {"content": response, "tool_calls": []}
        elif isinstance(response, dict):
            # 尝试从 dict 中提取响应
            parsed = None
            for key in ("response", "result", "text", "content"):
                if key in response and response[key]:
                    try:
                        parsed = json.loads(response[key]) if isinstance(response[key], str) else response[key]
                        break
                    except (json.JSONDecodeError, TypeError):
                        continue

            if parsed is None:
                # 如果找不到明确的响应字段，尝试直接使用 response
                parsed = response
        else:
            self._logger.warning(f"⚠️ Unexpected response type: {type(response)}")
            return {"content": str(response), "tool_calls": []}

        if not isinstance(parsed, dict):
            self._logger.warning("⚠️ Parsed response is not a dict")
            return {"content": str(parsed), "tool_calls": []}

        # 检查 action 字段
        action = parsed.get("action", "finish")

        # 🔧 调试日志：记录解析的 action
        self._logger.info(f"📝 [DEBUG] 解析后的 action: {action}")

        if action == "tool_call":
            # 提取工具调用
            raw_tool_calls = parsed.get("tool_calls", [])
            tool_calls = []

            for tc in raw_tool_calls:
                if not isinstance(tc, dict):
                    continue

                tool_name = tc.get("name")
                tool_args = tc.get("arguments", {})

                if not tool_name:
                    self._logger.warning("⚠️ Tool call missing name, skipping")
                    continue

                # 🔥 转换为 Loom 期望的格式（扁平结构）
                tool_calls.append({
                    "id": str(uuid.uuid4()),  # 生成唯一 ID
                    "name": tool_name,
                    "arguments": tool_args if isinstance(tool_args, dict) else {}
                })

            self._logger.info(f"🔧 [ContainerLLMAdapter] Extracted {len(tool_calls)} tool calls")

            # 触发工具调用回调
            if self._tool_call_callback:
                for tool_call in tool_calls:
                    try:
                        self._tool_call_callback(tool_call["name"], tool_call["arguments"])
                    except Exception as e:
                        self._logger.warning(f"⚠️ Tool call callback failed: {e}")

            # 返回结果
            return {
                "content": parsed.get("reasoning", ""),  # 使用 reasoning 作为 content
                "tool_calls": tool_calls
            }
        else:
            # action == "finish" 或其他
            content = parsed.get("content") or parsed.get("sql") or parsed.get("result") or ""

            self._logger.info("✅ [ContainerLLMAdapter] LLM returned final answer (no tool calls)")

            return {
                "content": content,
                "tool_calls": []
            }

    async def stream(self, messages: List[Dict]):
        """流式生成响应"""
        text = await self.generate(messages)
        for ch in text:
            await asyncio.sleep(0)
            yield ch

    async def chat_completion(self, messages: List[Dict], **kwargs) -> str:
        """
        兼容性方法：使用 generate() 实现 chat_completion 接口
        某些组件（如 quality_scorer）可能需要这个方法

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            LLM 响应文本
        """
        self._logger.debug(f"🧠 [ContainerLLMAdapter] chat_completion called with {len(messages)} messages")
        try:
            result = await self.generate(messages)
            # 确保返回字符串
            if isinstance(result, str):
                return result
            elif isinstance(result, dict):
                return result.get("content", str(result))
            else:
                return str(result)
        except Exception as e:
            self._logger.error(f"❌ [ContainerLLMAdapter] chat_completion failed: {e}")
            raise

    def _compose_full_prompt(self, messages: List[Dict], max_tokens: int = 12000) -> str:
        """
        合并所有 messages 为一个完整的 prompt，并进行智能 token 管理
        
        🔥 关键功能：
        1. 确保 Loom 注入的 system messages（schema context）被包含
        2. 使用滑动窗口机制，避免递归过程中的 token 累积爆炸
        3. 保留最重要的信息（system + 最新的对话）
        
        Token 预算分配：
        - System messages: 最多 4000 tokens（schema context）
        - Recent conversation: 最多 8000 tokens（最近的对话历史）
        - Total: 最多 12000 tokens
        
        支持的 message 类型：
        - system: 系统指令（包括 ContextRetriever 注入的 schema）
        - user: 用户输入
        - assistant: 助手响应
        - tool: 工具执行结果
        """
        # 粗略估算：4 chars ≈ 1 token
        CHARS_PER_TOKEN = 4
        max_chars = max_tokens * CHARS_PER_TOKEN

        sections = []

        # 1. 收集所有 system messages（包括 schema context）
        # System messages 优先级最高，必须保留
        system_messages = [
            m.get("content", "")
            for m in messages
            if m.get("role") == "system" and m.get("content")
        ]

        system_content = ""
        if system_messages:
            # 🔥 Schema context 会在这里被包含！
            system_content = "\n\n".join(system_messages)
            system_chars = len(system_content)
            system_tokens = system_chars // CHARS_PER_TOKEN

            self._logger.debug(f"📋 [ContainerLLMAdapter] System messages count: {len(system_messages)}, chars: {system_chars}, est. tokens: {system_tokens}")

            # 如果 system content 超过预算，裁剪（但这不应该发生，因为 ContextAssembler 已经控制了）
            if system_chars > (max_chars // 3):  # System 最多占 1/3
                self._logger.warning(f"⚠️ [ContainerLLMAdapter] System content too large ({system_tokens} tokens), truncating")
                system_content = system_content[:max_chars // 3]

            sections.append("# SYSTEM INSTRUCTIONS\n\n" + system_content)

        # 2. 收集对话历史（user, assistant, tool）
        # 使用滑动窗口：只保留最近的 N 条消息
        conversation_messages = []
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")

            if role == "user":
                conversation_messages.append(f"# USER\n{content}")
            elif role == "assistant":
                conversation_messages.append(f"# ASSISTANT\n{content}")
            elif role == "tool":
                tool_name = m.get("name", "unknown")
                conversation_messages.append(f"# TOOL RESULT ({tool_name})\n{content}")

        # 🔥 滑动窗口机制：从最新的消息开始，逐步添加，直到达到 token 限制
        conversation_chars_budget = max_chars - len(system_content) - 200  # 保留 200 chars 作为分隔符
        conversation = []
        current_chars = 0

        # 从最新的消息开始（reverse）
        for msg in reversed(conversation_messages):
            msg_chars = len(msg)
            if current_chars + msg_chars <= conversation_chars_budget:
                conversation.insert(0, msg)  # 插入到开头，保持时间顺序
                current_chars += msg_chars
            else:
                # 超过预算，停止添加
                self._logger.warning(
                    f"⚠️ [ContainerLLMAdapter] Conversation truncated: "
                    f"kept {len(conversation)}/{len(conversation_messages)} messages, "
                    f"{current_chars} chars, est. {current_chars // CHARS_PER_TOKEN} tokens"
                )
                break

        if conversation:
            sections.append("\n\n".join(conversation))

        # 3. 合并所有部分
        separator = "\n\n" + "=" * 80 + "\n\n"
        full_prompt = separator.join(sections)

        # 最终检查
        final_chars = len(full_prompt)
        final_tokens = final_chars // CHARS_PER_TOKEN

        self._logger.info(
            f"🧠 [ContainerLLMAdapter] Prompt composed: {final_chars} chars, "
            f"est. {final_tokens} tokens (budget: {max_tokens})"
        )
        if final_tokens > max_tokens:
            self._logger.error(
                f"❌ [ContainerLLMAdapter] Prompt exceeds token budget! "
                f"{final_tokens} > {max_tokens}"
            )

        return full_prompt

    def _extract_user_id(self, messages: List[Dict]) -> str:
        """从消息中提取用户 ID"""
        # 🔥 优先从context variable获取
        ctx_user = _CURRENT_USER_ID.get()
        if ctx_user:
            return ctx_user
        
        # 🔥 从消息metadata中获取
        for m in reversed(messages):
            metadata = m.get("metadata") or {}
            if isinstance(metadata, dict) and metadata.get("user_id"):
                return metadata["user_id"]
        
        # 🔥 如果没有找到用户ID，抛出异常而不是使用system
        raise ValueError("无法提取用户ID，请确保在请求中提供有效的用户ID")


# 🔥 LLM适配器缓存管理器
class LLMAdapterCache:
    """LLM适配器缓存管理器，避免重复创建适配器"""
    
    def __init__(self):
        self._cache: Dict[str, ContainerLLMAdapter] = {}
    
    def _generate_cache_key(self, container_id: str) -> str:
        """生成缓存键"""
        return f"llm_adapter:{container_id}"
    
    def get_adapter(self, container_id: str) -> Optional[ContainerLLMAdapter]:
        """获取缓存的适配器实例"""
        cache_key = self._generate_cache_key(container_id)
        return self._cache.get(cache_key)
    
    def set_adapter(self, container_id: str, adapter: ContainerLLMAdapter):
        """缓存适配器实例"""
        cache_key = self._generate_cache_key(container_id)
        self._cache[cache_key] = adapter
        logger.debug(f"🔧 [LLMAdapterCache] 缓存适配器: {container_id}")
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.info("🧹 [LLMAdapterCache] 清空适配器缓存")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "cached_adapters": len(self._cache),
            "memory_usage": f"{len(self._cache)} adapters"
        }


# 全局LLM适配器缓存实例
_llm_adapter_cache = LLMAdapterCache()


def create_llm_adapter(container: Any) -> ContainerLLMAdapter:
    """创建 LLM 适配器（带缓存）

    Args:
        container: 依赖容器

    Returns:
        LLM 适配器实例
    """
    # 🔥 使用缓存机制
    container_id = str(id(container))
    cached_adapter = _llm_adapter_cache.get_adapter(container_id)
    
    if cached_adapter:
        logger.info(f"♻️ [LLMAdapter] 使用缓存适配器: {container_id}")
        return cached_adapter
    
    # 创建新的适配器
    logger.info(f"🔧 [LLMAdapter] 创建新适配器: {container_id}")
    
    # 从 container 获取 LLM 服务
    llm_service = container.llm
    
    adapter = ContainerLLMAdapter(
        service=llm_service,
        default_user_id=None  # 🔥 不设置默认值，让_extract_user_id方法处理
    )
    
    # 缓存适配器
    _llm_adapter_cache.set_adapter(container_id, adapter)
    
    # 记录缓存统计
    cache_stats = _llm_adapter_cache.get_cache_stats()
    logger.info(f"📦 [LLMAdapter] 适配器创建完成，缓存统计: {cache_stats}")
    
    return adapter


def create_llm_adapter_from_config(config: LLMConfig, container: Any) -> ContainerLLMAdapter:
    """从配置创建 LLM 适配器
    
    Args:
        config: LLM 配置
        container: 依赖容器
        
    Returns:
        LLM 适配器实例
    """
    adapter = create_llm_adapter(container)
    
    # 应用配置
    if config.temperature is not None:
        # 注意：ContainerLLMAdapter 不直接支持 temperature 配置
        # 这需要通过 LLM 策略传递
        pass
    
    return adapter


# 别名函数
def get_llm_adapter(container: Any) -> ContainerLLMAdapter:
    """get_llm_adapter 别名函数，向后兼容"""
    return create_llm_adapter(container)


# 导出
__all__ = [
    "ContainerLLMAdapter",
    "create_llm_adapter",
    "get_llm_adapter",  # 添加别名
    "create_llm_adapter_from_config",
]