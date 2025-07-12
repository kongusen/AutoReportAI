from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core.security_logging import get_client_ip, security_logger

router = APIRouter()


@router.post("/", response_model=schemas.AIProvider)
def create_ai_provider(
    *,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    provider_in: schemas.AIProviderCreate,
):
    """
    Create a new AI provider configuration.
    """
    provider = crud.ai_provider.get_by_provider_name(db, name=provider_in.provider_name)
    if provider:
        raise HTTPException(
            status_code=400,
            detail="An AI provider with this name already exists.",
        )

    created_provider = crud.ai_provider.create(db=db, obj_in=provider_in)

    # Log sensitive configuration change
    security_logger.log_configuration_change(
        user_id=str(current_user.id),
        config_type="ai_provider",
        config_id=str(created_provider.id),
        changes={"action": "create", "provider_name": provider_in.provider_name},
        ip_address=get_client_ip(request),
    )

    # Log sensitive data access (API key creation)
    if provider_in.api_key:
        security_logger.log_sensitive_data_access(
            user_id=str(current_user.id),
            resource_type="ai_provider_api_key",
            resource_id=str(created_provider.id),
            action="create",
            ip_address=get_client_ip(request),
        )

    return created_provider


@router.get("/", response_model=List[schemas.AIProvider])
def read_ai_providers(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_superuser),
):
    """
    Retrieve AI providers.
    """
    if not crud.user.is_superuser(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    ai_providers = crud.ai_provider.get_multi(db, skip=skip, limit=limit)
    return ai_providers


@router.get("/active", response_model=schemas.AIProvider)
def get_active_ai_provider(db: Session = Depends(deps.get_db)):
    """
    Get the currently active AI provider configuration.
    """
    active_provider = crud.ai_provider.get_active(db)
    if not active_provider:
        raise HTTPException(status_code=404, detail="No active AI provider found.")
    return active_provider


@router.put("/{provider_id}", response_model=schemas.AIProvider)
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

    return updated_provider


@router.delete("/{provider_id}", response_model=schemas.AIProvider)
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
    return crud.ai_provider.remove(db=db, id=provider_id)


@router.post("/{provider_id}/test", response_model=schemas.Msg)
def test_ai_provider_connection(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    provider_id: int,
):
    """
    Test the connection to an AI provider.
    """
    provider = crud.ai_provider.get(db=db, id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="AI provider not found")

    try:
        # Test the connection using AIService
        from app.services.ai_service import AIService
        
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
                max_tokens=5
            )
            
            if response.choices:
                return {"msg": "AI provider connection test successful"}
            else:
                raise ValueError("No response from AI provider")
        else:
            raise ValueError(f"Unsupported provider type: {provider.provider_type}")
            
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"AI provider connection test failed: {str(e)}"
        )


@router.post("/{provider_id}/activate", response_model=schemas.AIProvider)
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
            crud.ai_provider.update(
                db=db, db_obj=p, obj_in={"is_active": 0}
            )

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

    return activated_provider


@router.post("/{provider_id}/deactivate", response_model=schemas.AIProvider)
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

    return deactivated_provider


@router.get("/{provider_id}/models", response_model=List[str])
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
                model for model in model_names 
                if any(keyword in model.lower() for keyword in ['gpt', 'chat', 'turbo'])
            ]
            
            return chat_models if chat_models else model_names[:10]  # Return top 10 if no chat models
        else:
            # For other provider types, return a default list
            return ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
            
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get models from AI provider: {str(e)}"
        )


@router.get("/health", response_model=schemas.Msg)
def check_ai_providers_health(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
):
    """
    Check the health status of all AI providers.
    """
    providers = crud.ai_provider.get_multi(db)
    if not providers:
        return {"msg": "No AI providers configured"}
    
    active_provider = crud.ai_provider.get_active(db)
    if not active_provider:
        return {"msg": "No active AI provider found"}
    
    return {"msg": f"AI providers healthy. Active provider: {active_provider.provider_name}"}


@router.get("/{provider_id}", response_model=schemas.AIProvider)
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
    return provider
