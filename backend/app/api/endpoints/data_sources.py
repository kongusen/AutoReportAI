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
    # Check if data source with this name already exists
    existing_source = crud.data_source.get_by_name(db, name=source_in.name)
    if existing_source:
        raise HTTPException(
            status_code=400,
            detail="A data source with this name already exists.",
        )
    
    return crud.data_source.create(db=db, obj_in=source_in)


@router.get("/", response_model=List[schemas.DataSource])
def read_data_sources(
    db: Session = Depends(deps.get_db), skip: int = 0, limit: int = 100
):
    """
    Retrieve data sources.
    """
    sources = crud.data_source.get_multi(db, skip=skip, limit=limit)
    return sources


@router.get("/{source_id}", response_model=schemas.DataSource)
def get_data_source(
    *,
    db: Session = Depends(deps.get_db),
    source_id: int,
):
    """
    Get a specific data source by ID.
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
    
    # Check if updating name conflicts with existing
    if source_in.name and source_in.name != source.name:
        existing_source = crud.data_source.get_by_name(db, name=source_in.name)
        if existing_source:
            raise HTTPException(
                status_code=400,
                detail="A data source with this name already exists.",
            )
    
    return crud.data_source.update(db=db, db_obj=source, obj_in=source_in)


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
    return crud.data_source.remove(db=db, id=source_id)


@router.post("/{source_id}/test", response_model=schemas.Msg)
async def test_data_source_connection(
    *,
    db: Session = Depends(deps.get_db),
    source_id: int,
):
    """
    Test the connection to a data source.
    """
    source = crud.data_source.get(db=db, id=source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    try:
        from app.services.data_retrieval_service import DataRetrievalService
        
        # Create service instance
        data_service = DataRetrievalService()
        
        # Test connection based on source type
        if source.source_type.value == "sql":
            if not source.connection_string:
                raise ValueError("SQL data source requires connection string")
            
            # Validate connection string
            from app.core.security_utils import validate_connection_string
            validate_connection_string(source.connection_string)
            
            # Test connection
            from sqlalchemy import create_engine, text
            engine = create_engine(source.connection_string)
            with engine.connect() as conn:
                # Simple test query
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            return {"msg": "SQL data source connection test successful"}
            
        elif source.source_type.value == "csv":
            if not source.file_path:
                raise ValueError("CSV data source requires file path")
            
            # Test file access
            import os
            if not os.path.exists(source.file_path):
                raise ValueError(f"CSV file not found: {source.file_path}")
            
            # Test file reading
            import pandas as pd
            df = pd.read_csv(source.file_path, nrows=1)  # Read just first row
            
            return {"msg": f"CSV data source connection test successful. Found {len(df.columns)} columns"}
            
        elif source.source_type.value == "api":
            if not source.api_url:
                raise ValueError("API data source requires URL")
            
            # Test API connection
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=source.api_method or "GET",
                    url=source.api_url,
                    headers=source.api_headers,
                    json=source.api_body,
                    timeout=10.0,
                )
                response.raise_for_status()
            
            return {"msg": "API data source connection test successful"}
        else:
            raise ValueError(f"Unsupported data source type: {source.source_type}")
            
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Data source connection test failed: {str(e)}"
        )


@router.get("/{source_id}/preview", response_model=dict)
async def preview_data_source(
    *,
    db: Session = Depends(deps.get_db),
    source_id: int,
    limit: int = 10,
):
    """
    Preview data from a data source.
    """
    source = crud.data_source.get(db=db, id=source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    try:
        from app.services.data_retrieval_service import DataRetrievalService
        
        # Create service instance
        data_service = DataRetrievalService()
        
        # Get preview data based on source type
        if source.source_type.value == "sql":
            if not source.connection_string:
                raise ValueError("SQL data source requires connection string")
            
            # Validate connection string
            from app.core.security_utils import validate_connection_string
            validate_connection_string(source.connection_string)
            
            # Get preview data
            from sqlalchemy import create_engine, text
            engine = create_engine(source.connection_string)
            
            # Use the defined query if available, otherwise show tables
            if source.db_query:
                query = f"SELECT * FROM ({source.db_query}) subquery LIMIT {limit}"
            else:
                # Try to get table names
                query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' LIMIT 10"
            
            import pandas as pd
            df = pd.read_sql(query, engine)
            
            return {
                "columns": df.columns.tolist(),
                "data": df.to_dict(orient="records"),
                "row_count": len(df)
            }
            
        elif source.source_type.value == "csv":
            if not source.file_path:
                raise ValueError("CSV data source requires file path")
            
            # Get preview data
            import pandas as pd
            df = pd.read_csv(source.file_path, nrows=limit)
            
            return {
                "columns": df.columns.tolist(),
                "data": df.to_dict(orient="records"),
                "row_count": len(df)
            }
            
        elif source.source_type.value == "api":
            if not source.api_url:
                raise ValueError("API data source requires URL")
            
            # Get preview data
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=source.api_method or "GET",
                    url=source.api_url,
                    headers=source.api_headers,
                    json=source.api_body,
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
            
            # Handle different API response formats
            if isinstance(data, list):
                preview_data = data[:limit]
                columns = list(preview_data[0].keys()) if preview_data else []
            elif isinstance(data, dict):
                # If it's a dict, try to find the data array
                if "data" in data:
                    preview_data = data["data"][:limit]
                    columns = list(preview_data[0].keys()) if preview_data else []
                else:
                    preview_data = [data]
                    columns = list(data.keys())
            else:
                preview_data = [{"value": data}]
                columns = ["value"]
            
            return {
                "columns": columns,
                "data": preview_data,
                "row_count": len(preview_data)
            }
        else:
            raise ValueError(f"Unsupported data source type: {source.source_type}")
            
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Data source preview failed: {str(e)}"
        )
