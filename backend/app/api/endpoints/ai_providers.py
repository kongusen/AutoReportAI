from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()

@router.post("/", response_model=schemas.AIProvider)
def create_ai_provider(
    *,
    db: Session = Depends(deps.get_db),
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
    return crud.ai_provider.create(db=db, obj_in=provider_in)

@router.get("/", response_model=List[schemas.AIProvider])
def read_ai_providers(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Retrieve all AI provider configurations.
    """
    return crud.ai_provider.get_multi(db, skip=skip, limit=limit)

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
    db: Session = Depends(deps.get_db),
    provider_id: int,
    provider_in: schemas.AIProviderUpdate,
):
    """
    Update an AI provider configuration.
    """
    provider = crud.ai_provider.get(db=db, id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="AI provider not found")
    return crud.ai_provider.update(db=db, db_obj=provider, obj_in=provider_in)

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