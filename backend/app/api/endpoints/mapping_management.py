from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.api import deps

router = APIRouter()


@router.post(
    "/templates/{template_id}/mappings", response_model=List[schemas.PlaceholderMapping]
)
def create_mappings_for_template(
    *,
    db: Session = Depends(deps.get_db),
    template_id: int,
    mappings_in: List[schemas.PlaceholderMappingCreate],
):
    """
    Create or update placeholder mappings for a specific template.
    (Note: This is a simplified version. A real implementation would handle updates more gracefully)
    """
    # Check if template exists
    template = crud.template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # For simplicity, we delete old mappings first.
    for old_mapping in template.mappings:
        crud.placeholder_mapping.remove(db=db, id=old_mapping.id)

    created_mappings = []
    for mapping_in in mappings_in:
        mapping = crud.placeholder_mapping.create(
            db=db, obj_in=mapping_in, template_id=template_id
        )
        created_mappings.append(mapping)

    return created_mappings


@router.get(
    "/templates/{template_id}/mappings", response_model=List[schemas.PlaceholderMapping]
)
def get_mappings_for_template(
    *,
    db: Session = Depends(deps.get_db),
    template_id: int,
):
    """
    Get all placeholder mappings for a specific template.
    """
    template = crud.template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template.mappings
