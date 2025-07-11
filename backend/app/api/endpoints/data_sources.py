from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.api import deps

router = APIRouter()

@router.post("/", response_model=schemas.DataSource)
def create_data_source(
    *,
    db: Session = Depends(deps.get_db),
    source_in: schemas.DataSourceCreate,
):
    """
    Create a new data source.
    """
    return crud.data_source.create(db=db, obj_in=source_in)

@router.get("/", response_model=List[schemas.DataSource])
def read_data_sources(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Retrieve data sources.
    """
    return crud.data_source.get_multi(db, skip=skip, limit=limit)

@router.get("/{source_id}", response_model=schemas.DataSource)
def read_data_source(
    *,
    db: Session = Depends(deps.get_db),
    source_id: int,
):
    """
    Get data source by ID.
    """
    source = crud.data_source.get(db=db, id=source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")
    return source

@router.put("/{source_id}", response_model=schemas.DataSource)
def update_data_source(
    *,
    db: Session = Depends(deps.get_db),
    source_id: int,
    source_in: schemas.DataSourceUpdate,
):
    """
    Update a data source.
    """
    source = crud.data_source.get(db=db, id=source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")
    source = crud.data_source.update(db=db, db_obj=source, obj_in=source_in)
    return source

@router.delete("/{source_id}", response_model=schemas.DataSource)
def delete_data_source(
    *,
    db: Session = Depends(deps.get_db),
    source_id: int,
):
    """
    Delete a data source.
    """
    source = crud.data_source.get(db=db, id=source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")
    crud.data_source.remove(db=db, id=source_id)
    return source 