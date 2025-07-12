import os
import shutil
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import crud, schemas
from app.api import deps
from app.services.template_parser_service import template_parser

router = APIRouter()

TEMPLATES_DIR = "templates"


@router.post("", response_model=schemas.Template)
def create_template(
    *,
    db: Session = Depends(deps.get_db),
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(None),
):
    """
    Upload a new .docx template, parse it, and save it to the database.
    """
    os.makedirs(TEMPLATES_DIR, exist_ok=True)

    file_path = os.path.join(TEMPLATES_DIR, file.filename)
    if os.path.exists(file_path):
        raise HTTPException(
            status_code=400, detail=f"Template file '{file.filename}' already exists."
        )

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    try:
        parsed_structure = template_parser.parse(file_path)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=422, detail=f"Failed to parse template: {e}")

    template_in = schemas.TemplateCreate(name=name, description=description)
    template = crud.template.create(
        db=db,
        obj_in=template_in,
        file_path=file_path,
        parsed_structure=parsed_structure,
    )
    return template


@router.get("", response_model=List[schemas.Template])
def list_templates(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    List all available templates.
    """
    templates = crud.template.get_multi(db, skip=skip, limit=limit)
    return templates


@router.get("/{template_id}", response_model=schemas.Template)
def get_template(
    *,
    db: Session = Depends(deps.get_db),
    template_id: int,
):
    """
    Get a single template by ID.
    """
    template = crud.template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.delete("/{template_id}", response_model=schemas.Template)
def delete_template(
    *,
    db: Session = Depends(deps.get_db),
    template_id: int,
):
    """
    Delete a template from the filesystem and the database.
    """
    template = crud.template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if os.path.exists(template.file_path):
        os.remove(template.file_path)

    deleted_template = crud.template.remove(db=db, id=template_id)
    return deleted_template
