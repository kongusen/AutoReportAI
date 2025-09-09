"""
模型执行器 - 基于用户配置的模型调用
与简化选择器配合使用，执行实际的模型调用
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.llm_server import LLMServer, LLMModel
from app.crud.crud_llm_server import crud_llm_server
from app.crud.crud_llm_model import crud_llm_model
from app.services.infrastructure.ai.llm.simple_model_selector import (
    get_simple_model_selector,
    TaskRequirement,
    ModelSelection
)

logger = logging.getLogger(__name__)


class ModelExecutor:
    """模型执行器"""
    
    def __init__(self):
        self.selector = get_simple_model_selector()
        logger.info("模型执行器初始化完成")
    
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
            # 1. 选择最适合的模型
            selection = self.selector.select_model_for_user(
                user_id=user_id,
                task_requirement=task_requirement,
                db=db
            )
            
            if not selection:
                return {
                    "success": False,
                    "error": "未找到可用的模型",
                    "user_id": user_id
                }
            
            logger.info(f"为用户 {user_id} 选择模型: {selection.model_name} (理由: {selection.reasoning})")
            
            # 2. 执行模型调用
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
                    "model_type": selection.model_type.value,
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
        
        payload = {
            "model": model.name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7)
        }
        
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
                        
                        return {
                            "success": True,
                            "result": content,
                            "model": model.name,
                            "provider": "openai_compatible",
                            "tokens_used": data.get("usage", {}).get("total_tokens", 0),
                            "response_time_ms": response_time
                        }
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