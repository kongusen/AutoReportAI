"""
模型执行器 - 基于用户配置的模型调用
与简化选择器配合使用，执行实际的模型调用
集成统一消息管道功能，支持流式处理和异步响应
"""

import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.llm_server import LLMServer, LLMModel
from app.crud.crud_llm_server import crud_llm_server
from app.crud.crud_llm_model import crud_llm_model
from .types import TaskRequirement, ModelSelection

logger = logging.getLogger(__name__)

# 导入统一消息管道组件
try:
    from ..agents.core.message_processor import (
        UnifiedMessage, UnifiedMessageType, MessageStage, StreamingContext,
        MessagePipelineProcessor, create_unified_message, create_streaming_message
    )
    UNIFIED_PIPELINE_AVAILABLE = True
except ImportError:
    logger.warning("Unified message pipeline not available, running in compatibility mode")
    UNIFIED_PIPELINE_AVAILABLE = False


class ModelExecutor:
    """
    模型执行器 - 集成统一消息管道
    
    功能扩展：
    1. 支持统一消息格式处理
    2. 流式响应和增量更新
    3. 与TT控制循环集成
    4. 背压管理和错误恢复
    """
    
    def __init__(self, enable_streaming: bool = True):
        # 移除对simple_model_selector的依赖，直接使用数据库
        self.enable_streaming = enable_streaming
        self.streaming_contexts: Dict[str, StreamingContext] = {}
        
        logger.info(f"模型执行器初始化完成 (统一管道: {UNIFIED_PIPELINE_AVAILABLE}, 流式处理: {enable_streaming})")
    
    # ========================================
    # 统一消息管道接口
    # ========================================
    
    async def process_llm_message(
        self,
        message,
        context: Dict[str, Any] = None
    ):
        """
        处理LLM消息 - 统一消息管道接口
        参考Claude Code的流式LLM处理模式
        """
        if not UNIFIED_PIPELINE_AVAILABLE:
            logger.error("Unified pipeline not available")
            return
        
        try:
            # 提取LLM请求参数
            user_id = message.metadata.headers.get("user_id", "anonymous")
            prompt = str(message.content.get("prompt", message.content))
            task_requirement = self._extract_task_requirement(message, context)
            
            # 创建流式响应
            if self.enable_streaming and message.stream_id:
                async for response in self._execute_streaming_llm(
                    user_id=user_id,
                    prompt=prompt,
                    task_requirement=task_requirement,
                    stream_id=message.stream_id,
                    correlation_id=message.metadata.correlation_id,
                    context=context
                ):
                    yield response
            else:
                # 非流式处理
                result = await self.execute_with_auto_selection(
                    user_id=user_id,
                    prompt=prompt,
                    task_requirement=task_requirement,
                    **(context or {})
                )
                
                response = create_unified_message(
                    UnifiedMessageType.LLM_RESPONSE,
                    content=result,
                    user_id=user_id,
                    correlation_id=message.metadata.correlation_id
                )
                response.stage = MessageStage.OUTPUT
                yield response
                
        except Exception as e:
            logger.error(f"LLM message processing error: {e}")
            
            error_response = create_unified_message(
                UnifiedMessageType.ERROR_MESSAGE,
                content={"error": str(e), "stage": "llm_execution"},
                user_id=message.metadata.headers.get("user_id"),
                correlation_id=message.metadata.correlation_id
            )
            error_response.stage = MessageStage.OUTPUT
            yield error_response
    
    async def _execute_streaming_llm(
        self,
        user_id: str,
        prompt: str,
        task_requirement: TaskRequirement,
        stream_id: str,
        correlation_id: str,
        context: Dict[str, Any] = None
    ):
        """执行流式LLM调用"""
        
        # 创建流式上下文
        if stream_id not in self.streaming_contexts:
            self.streaming_contexts[stream_id] = StreamingContext(stream_id=stream_id)
        
        streaming_ctx = self.streaming_contexts[stream_id]
        
        try:
            # 发送开始信号
            yield create_streaming_message(
                UnifiedMessageType.LLM_STREAM_DELTA,
                content={"action": "stream_start", "model_selection": "in_progress"},
                stream_id=stream_id,
                correlation_id=correlation_id
            )

            # 选择模型 - 使用数据库驱动的选择
            from .pure_database_manager import select_model_for_user
            db = SessionLocal()

            try:
                selection_dict = await select_model_for_user(
                    user_id=user_id,
                    task_type=task_requirement.task_type,
                    complexity=task_requirement.complexity_level
                )

                # 转换为 ModelSelection 格式
                selection = ModelSelection(
                    model_id=1,  # 临时ID
                    model_name=selection_dict["model"],
                    model_type="reasoning" if "claude" in selection_dict["model"] else "general",
                    server_id=1,  # 临时ID
                    server_name=selection_dict["provider"],
                    provider_type=selection_dict["provider"],
                    reasoning=selection_dict["reasoning"]
                )

                if not selection:
                    raise Exception("未找到可用的模型")

                # 发送模型选择结果
                yield create_streaming_message(
                    UnifiedMessageType.LLM_STREAM_DELTA,
                    content={
                        "action": "model_selected",
                        "model": selection.model_name,
                        "reasoning": selection.reasoning
                    },
                    stream_id=stream_id,
                    correlation_id=correlation_id
                )

                # 模拟流式执行（实际应该调用真实的流式API）
                await self._simulate_streaming_execution(
                    selection=selection,
                    prompt=prompt,
                    stream_id=stream_id,
                    correlation_id=correlation_id,
                    streaming_ctx=streaming_ctx
                )

            finally:
                db.close()

            # 发送完成信号
            yield create_streaming_message(
                UnifiedMessageType.COMPLETION,
                content={
                    "final_result": streaming_ctx.buffer,
                    "total_chunks": streaming_ctx.total_chunks,
                    "total_bytes": streaming_ctx.total_bytes
                },
                stream_id=stream_id,
                correlation_id=correlation_id
            )
            
        except Exception as e:
            logger.error(f"Streaming LLM execution error: {e}")
            
            yield create_streaming_message(
                UnifiedMessageType.ERROR_MESSAGE,
                content={"error": str(e), "stage": "streaming_llm"},
                stream_id=stream_id,
                correlation_id=correlation_id
            )
        
        finally:
            # 清理流式上下文
            if stream_id in self.streaming_contexts:
                streaming_ctx.is_complete = True
    
    async def _simulate_streaming_execution(
        self,
        selection: ModelSelection,
        prompt: str,
        stream_id: str,
        correlation_id: str,
        streaming_ctx
    ):
        """模拟流式执行（实际应该调用真实的API）"""
        
        # 模拟响应内容
        response_chunks = [
            "正在分析您的请求...",
            f"使用模型 {selection.model_name} 处理...",
            "生成中...",
            f"基于提示: {prompt[:50]}...",
            "处理完成！"
        ]
        
        for i, chunk in enumerate(response_chunks):
            # 模拟处理延迟
            await asyncio.sleep(0.5)
            
            # 更新流式上下文
            streaming_ctx.buffer += chunk + " "
            streaming_ctx.total_chunks += 1
            streaming_ctx.total_bytes += len(chunk)
            
            # 发送增量
            delta_message = create_streaming_message(
                UnifiedMessageType.LLM_STREAM_DELTA,
                content={
                    "delta": chunk,
                    "chunk_index": i,
                    "is_final": i == len(response_chunks) - 1
                },
                stream_id=stream_id,
                is_delta=True,
                correlation_id=correlation_id
            )
            delta_message.stage = MessageStage.PROCESSING
            
            # 注意：这里应该yield，但在辅助方法中我们通过其他方式返回
            # 实际实现中应该通过队列或其他机制传递
    
    def _extract_task_requirement(
        self, 
        message, 
        context: Dict[str, Any] = None
    ) -> TaskRequirement:
        """从统一消息中提取任务需求"""
        
        # 从消息内容中提取或使用默认值
        content = message.content if isinstance(message.content, dict) else {}
        
        return TaskRequirement(
            task_type=content.get("task_type", "general"),
            complexity_level=content.get("complexity", "medium"),
            requires_reasoning=content.get("requires_reasoning", False),
            requires_tool_use=content.get("requires_tool_use", False),
            max_tokens=content.get("max_tokens", 4000),
            temperature=content.get("temperature", 0.7)
        )
    
    def cleanup_streaming_context(self, stream_id: str):
        """清理流式上下文"""
        if stream_id in self.streaming_contexts:
            del self.streaming_contexts[stream_id]
            logger.debug(f"Cleaned up LLM streaming context: {stream_id}")
    
    def get_streaming_metrics(self) -> Dict[str, Any]:
        """获取流式处理统计"""
        return {
            "active_streams": len(self.streaming_contexts),
            "total_contexts": sum(
                ctx.total_chunks for ctx in self.streaming_contexts.values()
            ),
            "total_bytes": sum(
                ctx.total_bytes for ctx in self.streaming_contexts.values()
            )
        }
    
    # ========================================
    # 原有接口保持兼容
    # ========================================
    
    async def execute_with_auto_selection(
        self,
        user_id: str,
        prompt: str,
        task_requirement: TaskRequirement,
        db: Optional[Session] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """基于任务需求自动选择并执行模型"""
        
        if db is None:
            db = SessionLocal()
            should_close_db = True
        else:
            should_close_db = False
        
        try:
            # 1. 选择最适合的模型 - 使用数据库驱动的选择
            from .pure_database_manager import select_model_for_user

            selection_dict = await select_model_for_user(
                user_id=user_id,
                task_type=task_requirement.task_type,
                complexity=task_requirement.complexity_level
            )

            # 转换为 ModelSelection 格式 - 使用真实的数据库ID
            selection = ModelSelection(
                model_id=selection_dict.get("model_id", 1),  # 使用真实model_id
                model_name=selection_dict["model"],
                model_type="reasoning" if "claude" in selection_dict["model"] else "general",
                server_id=selection_dict.get("server_id", 1),  # 使用真实server_id
                server_name=selection_dict["provider"],
                provider_type=selection_dict["provider"],
                reasoning=selection_dict["reasoning"]
            )
            
            if not selection:
                return {
                    "success": False,
                    "error": "未找到可用的模型",
                    "user_id": user_id
                }
            
            logger.info(f"为用户 {user_id} 选择模型: {selection.model_name} (理由: {selection.reasoning})")
            
            # 2. 执行模型调用 - 使用正确的执行路径（真实API）
            result = await self._execute_model(
                selection=selection,
                prompt=prompt,
                db=db,
                **kwargs
            )
            
            # 3. 添加选择信息到结果
            result.update({
                "selected_model": {
                    "model_id": selection.model_id,
                    "model_name": selection.model_name,
                    "model_type": selection.model_type,
                    "server_name": selection.server_name,
                    "reasoning": selection.reasoning
                }
            })
            
            return result
            
        except Exception as e:
            logger.error(f"执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_id": user_id
            }
        finally:
            if should_close_db:
                db.close()
    
    async def execute_with_specific_model(
        self,
        model_id: int,
        prompt: str,
        db: Optional[Session] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """使用指定模型执行"""
        
        if db is None:
            db = SessionLocal()
            should_close_db = True
        else:
            should_close_db = False
        
        try:
            # 获取模型和服务器信息
            model = crud_llm_model.get(db, id=model_id)
            if not model:
                return {
                    "success": False,
                    "error": f"模型 {model_id} 不存在"
                }
            
            server = crud_llm_server.get(db, id=model.server_id)
            if not server:
                return {
                    "success": False,
                    "error": f"服务器 {model.server_id} 不存在"
                }
            
            # 检查状态
            if not model.is_active or not model.is_healthy:
                return {
                    "success": False,
                    "error": f"模型 {model.name} 不可用"
                }
            
            if not server.is_active or not server.is_healthy:
                return {
                    "success": False,
                    "error": f"服务器 {server.name} 不可用"
                }
            
            # 构建选择对象
            selection = ModelSelection(
                model_id=model.id,
                model_name=model.name,
                model_type=model.model_type,
                server_id=server.id,
                server_name=server.name,
                provider_type=server.provider_type,
                reasoning="用户指定模型"
            )
            
            # 执行调用
            result = await self._execute_model(
                selection=selection,
                prompt=prompt,
                db=db,
                **kwargs
            )
            
            return result
            
        except Exception as e:
            logger.error(f"指定模型执行失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if should_close_db:
                db.close()
    
    async def _execute_model_direct(
        self,
        model_name: str,
        provider: str,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """直接执行模型调用，不依赖数据库查询"""

        try:
            # 根据提供商类型调用不同的实现
            if provider == "anthropic":
                return await self._call_anthropic_direct(model_name, prompt, **kwargs)
            elif provider == "openai":
                return await self._call_openai_direct(model_name, prompt, **kwargs)
            else:
                # 默认尝试OpenAI兼容格式
                return await self._call_openai_direct(model_name, prompt, **kwargs)

        except Exception as e:
            logger.error(f"直接模型调用失败: {e}")

            return {
                "success": False,
                "error": f"模型调用失败: {str(e)}",
                "model_name": model_name
            }

    async def _execute_model(
        self,
        selection: ModelSelection,
        prompt: str,
        db: Session,
        **kwargs
    ) -> Dict[str, Any]:
        """执行具体的模型调用"""
        
        try:
            # 获取模型和服务器详细信息
            model = crud_llm_model.get(db, id=selection.model_id)
            server = crud_llm_server.get(db, id=selection.server_id)
            
            # 根据服务器类型调用不同的实现
            if server.provider_type == "openai":
                return await self._call_openai_compatible(server, model, prompt, **kwargs)
            elif server.provider_type == "anthropic":
                return await self._call_anthropic_compatible(server, model, prompt, **kwargs)
            elif server.provider_type == "custom":
                return await self._call_custom_api(server, model, prompt, **kwargs)
            else:
                # 默认尝试OpenAI兼容格式
                return await self._call_openai_compatible(server, model, prompt, **kwargs)
                
        except Exception as e:
            logger.error(f"模型调用失败: {e}")
            
            # 如果有备选模型，尝试备选
            if selection.fallback_model_id:
                logger.info(f"尝试备选模型: {selection.fallback_model_id}")
                try:
                    fallback_result = await self.execute_with_specific_model(
                        model_id=selection.fallback_model_id,
                        prompt=prompt,
                        db=db,
                        **kwargs
                    )
                    if fallback_result.get("success"):
                        fallback_result["used_fallback"] = True
                        return fallback_result
                except Exception as fallback_e:
                    logger.error(f"备选模型也失败: {fallback_e}")
            
            return {
                "success": False,
                "error": f"模型调用失败: {str(e)}",
                "model_name": selection.model_name
            }
    
    async def _call_openai_compatible(
        self,
        server: LLMServer,
        model: LLMModel,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """调用OpenAI兼容API"""
        
        # 实际的HTTP API调用
        import httpx
        import time
        
        start_time = time.time()
        headers = {
            "Authorization": f"Bearer {server.api_key}",
            "Content-Type": "application/json"
        }
        
        # Default JSON mode for structured outputs unless explicitly overridden
        response_format = kwargs.get("response_format")
        if not response_format:
            response_format = {"type": "json_object"}

        # Build messages, adding a JSON-only system instruction if in JSON mode
        messages = []
        if isinstance(response_format, dict) and response_format.get("type") in {"json_object", "json_schema"}:
            messages.append({
                "role": "system",
                "content": (
                    "You are a strict JSON generator. Respond with one single JSON object only, "
                    "no explanations, no markdown, no code fences."
                )
            })
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model.name,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.2),
            "top_p": kwargs.get("top_p", 1.0),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
            "presence_penalty": kwargs.get("presence_penalty", 0.0)
        }

        # Attach response_format (for JSON mode)
        if response_format:
            payload["response_format"] = response_format
            logger.info(f"Using response_format: {response_format}")
        
        try:
            logger.info(f"调用API: {server.base_url}/chat/completions, 模型: {model.name}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{server.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                
                logger.info(f"API响应状态码: {response.status_code}")
                response_time = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        logger.info(f"API调用成功，响应时间: {response_time}ms")
                        
                        # 检查响应结构
                        if "choices" not in data or not data["choices"]:
                            raise Exception(f"API响应格式错误: 缺少choices字段或为空")
                        
                        if "message" not in data["choices"][0]:
                            raise Exception(f"API响应格式错误: 缺少message字段")
                        
                        content = data["choices"][0]["message"]["content"]
                        logger.info(f"API返回内容长度: {len(content) if content else 0}")

                        # Try to parse JSON if JSON mode enabled
                        parsed_json = None
                        try:
                            if isinstance(response_format, dict) and response_format.get("type") in {"json_object", "json_schema"} and content:
                                import json as _json
                                parsed_json = _json.loads(content)
                        except Exception:
                            parsed_json = None

                        result_payload = {
                            "success": True,
                            "result": content,
                            "model": model.name,
                            "provider": "openai_compatible",
                            "tokens_used": data.get("usage", {}).get("total_tokens", 0),
                            "response_time_ms": response_time
                        }
                        if parsed_json is not None:
                            result_payload["result_json"] = parsed_json

                        return result_payload
                    except Exception as parse_e:
                        response_text = response.text
                        logger.error(f"解析API响应失败: {parse_e}, 原始响应: {response_text[:500]}")
                        raise Exception(f"解析API响应失败: {parse_e}")
                else:
                    error_text = response.text
                    logger.error(f"API调用失败，状态码: {response.status_code}, 错误信息: {error_text[:500]}")
                    raise Exception(f"API调用失败 (状态码: {response.status_code}): {error_text}")
                        
        except httpx.RequestError as e:
            logger.error(f"网络连接错误: {e}")
            raise Exception(f"网络连接错误: {e}")
        except Exception as e:
            logger.error(f"OpenAI兼容API调用失败: {str(e)}")
            raise
    
    async def _call_anthropic_compatible(
        self,
        server: LLMServer,
        model: LLMModel,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """调用Anthropic兼容API"""
        
        # 实际的Anthropic API调用
        import httpx
        import time
        
        start_time = time.time()
        headers = {
            "x-api-key": server.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": model.name,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "messages": [{"role": "user", "content": prompt}]
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{server.base_url}/messages",
                    json=payload,
                    headers=headers
                )
                
                response_time = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "success": True,
                        "result": data["content"][0]["text"],
                        "model": model.name,
                        "provider": "anthropic_compatible", 
                        "tokens_used": data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
                        "response_time_ms": response_time
                    }
                else:
                    error_text = response.text
                    raise Exception(f"Anthropic API调用失败 (状态码: {response.status_code}): {error_text}")
                        
        except Exception as e:
            logger.error(f"Anthropic兼容API调用失败: {e}")
            raise
    
    async def _call_openai_direct(
        self,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """直接调用OpenAI兼容API（模拟调用，返回假数据）"""

        import time
        import asyncio

        # 模拟处理延迟
        await asyncio.sleep(0.1)

        start_time = time.time()
        response_time = int((time.time() - start_time) * 1000)

        # 不再返回硬编码的SQL，而是提示需要真实LLM服务
        logger.warning("使用模拟OpenAI调用，无法生成真实SQL，需要配置真实LLM服务")

        return {
            "success": False,
            "error": "mock_llm_service",
            "message": "Using mock LLM service, please configure real LLM server for SQL generation",
            "model": model_name,
            "provider": "openai_mock",
            "tokens_used": 0,
            "response_time_ms": response_time
        }

    async def _call_anthropic_direct(
        self,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """直接调用Anthropic兼容API（模拟调用，返回假数据）"""

        import time
        import asyncio

        # 模拟处理延迟
        await asyncio.sleep(0.2)

        start_time = time.time()
        response_time = int((time.time() - start_time) * 1000)

        # 不再返回硬编码的SQL，而是提示需要真实LLM服务
        logger.warning("使用模拟Anthropic调用，无法生成真实SQL，需要配置真实LLM服务")

        return {
            "success": False,
            "error": "mock_llm_service",
            "message": "Using mock LLM service, please configure real LLM server for SQL generation",
            "model": model_name,
            "provider": "anthropic_mock",
            "tokens_used": 0,
            "response_time_ms": response_time
        }

    async def _call_custom_api(
        self,
        server: LLMServer,
        model: LLMModel,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """调用自定义API"""

        # 实际的自定义API调用
        import httpx
        import time

        start_time = time.time()
        headers = {
            "Authorization": f"Bearer {server.api_key}",
            "Content-Type": "application/json"
        }

        # 根据服务器配置构建请求
        payload = {
            "prompt": prompt,
            "model": model.name,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7)
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{server.base_url}/generate",
                    json=payload,
                    headers=headers
                )

                response_time = int((time.time() - start_time) * 1000)

                if response.status_code == 200:
                    data = response.json()

                    return {
                        "success": True,
                        "result": data.get("text", data.get("response", "")),
                        "model": model.name,
                        "provider": "custom",
                        "tokens_used": data.get("tokens_used", len(prompt) // 4),
                        "response_time_ms": response_time
                    }
                else:
                    error_text = response.text
                    raise Exception(f"自定义API调用失败 (状态码: {response.status_code}): {error_text}")

        except Exception as e:
            logger.error(f"自定义API调用失败: {e}")
            raise


# 全局实例
_model_executor: Optional[ModelExecutor] = None


def get_model_executor() -> ModelExecutor:
    """获取模型执行器实例"""
    global _model_executor
    if _model_executor is None:
        _model_executor = ModelExecutor()
    return _model_executor
