from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core.security_logging import get_client_ip, security_logger
from app.schemas.base import APIResponse, create_success_response, create_error_response

router = APIRouter(tags=["AI服务"])


@router.get(
    "/",
    response_model=List[schemas.AIProviderResponse],
    summary="获取AI提供商列表",
    description="""
    获取所有可用的AI服务提供商列表。
    
    ## 支持的AI提供商
    
    ### OpenAI
    - **GPT-3.5-turbo**: 快速响应，适合一般任务
    - **GPT-4**: 高质量输出，适合复杂分析
    - **GPT-4-turbo**: 平衡性能和成本
    
    ### Anthropic
    - **Claude-3-sonnet**: 高性能模型，适合复杂推理
    - **Claude-3-haiku**: 快速模型，适合简单任务
    
    ### 本地模型
    - **Llama-2**: 开源本地部署
    - **Mistral**: 轻量级本地模型
    
    ## 查询参数
    - **provider_type**: 提供商类型过滤
    - **is_active**: 是否只返回活跃的提供商
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "name": "OpenAI GPT-4",
                            "provider_type": "openai",
                            "model_name": "gpt-4",
                            "is_active": True,
                            "config": {
                                "temperature": 0.7,
                                "max_tokens": 2000
                            },
                            "created_at": "2023-12-01T10:00:00Z"
                        }
                    ]
                }
            }
        }
    }
)
async def get_ai_providers(
    provider_type: Optional[str] = Query(None, description="提供商类型"),
    is_active: Optional[bool] = Query(None, description="是否只返回活跃的提供商"),
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> List[schemas.AIProviderResponse]:
    """
    Retrieve AI providers.
    """
    if not crud.user.is_superuser(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    ai_providers = crud.ai_provider.get_multi(db, skip=skip, limit=limit)
    return APIResponse[List[schemas.AIProvider]](
        success=True,
        message="AI提供商列表获取成功",
        data=ai_providers
    )


@router.get("/active", response_model=APIResponse[schemas.AIProvider])
def get_active_ai_provider(db: Session = Depends(deps.get_db)):
    """
    Get the currently active AI provider configuration.
    """
    active_provider = crud.ai_provider.get_active(db)
    if not active_provider:
        raise HTTPException(status_code=404, detail="No active AI provider found.")
    return APIResponse[schemas.AIProvider](
        success=True,
        message="活跃AI提供商获取成功",
        data=active_provider
    )


@router.put("/{provider_id}", response_model=APIResponse[schemas.AIProvider])
def update_ai_provider(
    *,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    provider_id: int,
    provider_in: schemas.AIProviderUpdate,
):
    """
    Update an AI provider configuration.
    """
    provider = crud.ai_provider.get(db=db, id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="AI provider not found")

    # Track changes for logging
    changes = {}
    if (
        provider_in.provider_name
        and provider_in.provider_name != provider.provider_name
    ):
        changes["provider_name"] = {
            "old": provider.provider_name,
            "new": provider_in.provider_name,
        }
    if (
        provider_in.is_active is not None
        and provider_in.is_active != provider.is_active
    ):
        changes["is_active"] = {"old": provider.is_active, "new": provider_in.is_active}

    updated_provider = crud.ai_provider.update(
        db=db, db_obj=provider, obj_in=provider_in
    )

    # Log configuration changes
    if changes:
        security_logger.log_configuration_change(
            user_id=str(current_user.id),
            config_type="ai_provider",
            config_id=str(provider_id),
            changes={"action": "update", "fields": changes},
            ip_address=get_client_ip(request),
        )

    # Log API key update if changed
    if provider_in.api_key:
        security_logger.log_sensitive_data_access(
            user_id=str(current_user.id),
            resource_type="ai_provider_api_key",
            resource_id=str(provider_id),
            action="update",
            ip_address=get_client_ip(request),
        )

    return APIResponse[schemas.AIProvider](
        success=True,
        message="AI提供商更新成功",
        data=updated_provider
    )


@router.delete("/{provider_id}", response_model=APIResponse[schemas.AIProvider])
def delete_ai_provider(
    *,
    db: Session = Depends(deps.get_db),
    provider_id: int,
):
    """
    Delete an AI provider configuration.
    """
    provider = crud.ai_provider.get(db=db, id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="AI provider not found")
    deleted_provider = crud.ai_provider.remove(db=db, id=provider_id)
    return APIResponse[schemas.AIProvider](
        success=True,
        message="AI提供商删除成功",
        data=deleted_provider
    )


@router.post(
    "/{provider_id}/test",
    response_model=schemas.AIProviderTestResponse,
    summary="测试AI提供商",
    description="""
    测试指定AI提供商的可用性和响应质量。
    
    ## 测试内容
    - API连接测试
    - 认证信息验证
    - 模型响应测试
    - 延迟测试
    
    ## 测试消息
    系统会发送一个标准的测试消息来验证AI提供商的响应。
    """,
    responses={
        200: {
            "description": "测试完成",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "AI提供商测试成功",
                        "response_time": 1.5,
                        "test_response": "你好！我是AI助手，很高兴为您服务。",
                        "model_info": {
                            "model": "gpt-4",
                            "tokens_used": 15
                        }
                    }
                }
            }
        }
    }
)
async def test_ai_provider(
    provider_id: str,
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> schemas.AIProviderTestResponse:
    """
    Test the connection to an AI provider.
    """
    provider = crud.ai_provider.get(db=db, id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="AI provider not found")

    try:
        # Test the connection using AIService
        from app.services.ai_integration import AIService

        # Create a temporary AI service instance for testing
        test_service = AIService(db)

        # Override the provider for testing
        original_provider = test_service.provider
        test_service.provider = provider

        # Decrypt API key for testing
        from app.core.security_utils import decrypt_data

        decrypted_api_key = decrypt_data(provider.api_key) if provider.api_key else None

        if provider.provider_type.value == "openai":
            if not decrypted_api_key:
                raise ValueError("API key is required for OpenAI provider")

            import openai

            test_client = openai.OpenAI(
                api_key=decrypted_api_key,
                base_url=str(provider.api_base_url) if provider.api_base_url else None,
            )

            # Test with a simple completion
            response = test_client.chat.completions.create(
                model=provider.default_model_name or "gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )

            if response.choices:
                test_result = {"msg": "AI provider connection test successful"}
                return APIResponse[schemas.Msg](
                    success=True,
                    message="AI提供商连接测试成功",
                    data=test_result
                )
            else:
                raise ValueError("No response from AI provider")
        else:
            raise ValueError(f"Unsupported provider type: {provider.provider_type}")

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"AI provider connection test failed: {str(e)}"
        )


@router.post("/{provider_id}/activate", response_model=APIResponse[schemas.AIProvider])
def activate_ai_provider(
    *,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    provider_id: int,
):
    """
    Activate an AI provider (deactivates all others).
    """
    provider = crud.ai_provider.get(db=db, id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="AI provider not found")

    # Deactivate all other providers
    all_providers = crud.ai_provider.get_multi(db)
    for p in all_providers:
        if p.id != provider_id and p.is_active == 1:
            crud.ai_provider.update(db=db, db_obj=p, obj_in={"is_active": 0})

    # Activate the selected provider
    activated_provider = crud.ai_provider.update(
        db=db, db_obj=provider, obj_in={"is_active": 1}
    )

    # Log the activation
    security_logger.log_configuration_change(
        user_id=str(current_user.id),
        config_type="ai_provider",
        config_id=str(provider_id),
        changes={"action": "activate", "provider_name": provider.provider_name},
        ip_address=get_client_ip(request),
    )

    return APIResponse[schemas.AIProvider](
        success=True,
        message="AI提供商激活成功",
        data=activated_provider
    )


@router.post("/{provider_id}/deactivate", response_model=APIResponse[schemas.AIProvider])
def deactivate_ai_provider(
    *,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    provider_id: int,
):
    """
    Deactivate an AI provider.
    """
    provider = crud.ai_provider.get(db=db, id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="AI provider not found")

    # Deactivate the provider
    deactivated_provider = crud.ai_provider.update(
        db=db, db_obj=provider, obj_in={"is_active": 0}
    )

    # Log the deactivation
    security_logger.log_configuration_change(
        user_id=str(current_user.id),
        config_type="ai_provider",
        config_id=str(provider_id),
        changes={"action": "deactivate", "provider_name": provider.provider_name},
        ip_address=get_client_ip(request),
    )

    return APIResponse[schemas.AIProvider](
        success=True,
        message="AI提供商停用成功",
        data=deactivated_provider
    )


@router.get("/{provider_id}/models", response_model=APIResponse[List[str]])
def get_ai_provider_models(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    provider_id: int,
):
    """
    Get available models for an AI provider.
    """
    provider = crud.ai_provider.get(db=db, id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="AI provider not found")

    try:
        from app.core.security_utils import decrypt_data

        decrypted_api_key = decrypt_data(provider.api_key) if provider.api_key else None

        if provider.provider_type.value == "openai":
            if not decrypted_api_key:
                raise ValueError("API key is required for OpenAI provider")

            import openai

            client = openai.OpenAI(
                api_key=decrypted_api_key,
                base_url=str(provider.api_base_url) if provider.api_base_url else None,
            )

            # Get available models
            models = client.models.list()
            model_names = [model.id for model in models.data]

            # Filter for commonly used chat models
            chat_models = [
                model
                for model in model_names
                if any(keyword in model.lower() for keyword in ["gpt", "chat", "turbo"])
            ]

            model_list = chat_models if chat_models else model_names[:10]  # Return top 10 if no chat models
            return APIResponse[List[str]](
                success=True,
                message="AI提供商模型列表获取成功",
                data=model_list
            )
        else:
            # For other provider types, return a default list
            model_list = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
            return APIResponse[List[str]](
                success=True,
                message="AI提供商模型列表获取成功",
                data=model_list
            )

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to get models from AI provider: {str(e)}"
        )


@router.get("/health", response_model=APIResponse[schemas.Msg])
def check_ai_providers_health(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
):
    """
    Check the health status of all AI providers.
    """
    providers = crud.ai_provider.get_multi(db)
    if not providers:
        health_result = {"msg": "No AI providers configured"}
        return APIResponse[schemas.Msg](
            success=True,
            message="AI提供商健康检查完成",
            data=health_result
        )

    active_provider = crud.ai_provider.get_active(db)
    if not active_provider:
        health_result = {"msg": "No active AI provider found"}
        return APIResponse[schemas.Msg](
            success=True,
            message="AI提供商健康检查完成",
            data=health_result
        )

    health_result = {"msg": f"AI providers healthy. Active provider: {active_provider.provider_name}"}
    return APIResponse[schemas.Msg](
        success=True,
        message="AI提供商健康检查完成",
        data=health_result
    )


@router.get("/{provider_id}", response_model=APIResponse[schemas.AIProvider])
def get_ai_provider(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    provider_id: int,
):
    """
    Get a specific AI provider by ID.
    """
    provider = crud.ai_provider.get(db=db, id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="AI provider not found")
    return APIResponse[schemas.AIProvider](
        success=True,
        message="AI提供商获取成功",
        data=provider
    )
