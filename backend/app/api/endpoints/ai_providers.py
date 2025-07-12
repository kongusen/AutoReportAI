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
