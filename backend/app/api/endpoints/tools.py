from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import pandas as pd

from app import crud
from app.api import deps
from app.services.data_retrieval_service import data_retrieval_service

router = APIRouter()

class RetrieveDataRequest(BaseModel):
    data_source_name: str = Field(..., description="要查询的数据源的名称。")

class RetrieveDataResponse(BaseModel):
    data: list = Field(..., description="从数据源查询到的数据，以JSON格式的列表返回。")
    dataframe_str: str = Field(..., description="便于LLM直接阅读的DataFrame字符串表示形式。")

@router.post("/retrieve-data", response_model=RetrieveDataResponse)
async def retrieve_data(
    *,
    db: Session = Depends(deps.get_db),
    request: RetrieveDataRequest
):
    """
    一个用于LLM的工具：根据名称检索并返回指定数据源的数据。
    """
    # 在实际应用中，我们可能需要更复杂的逻辑来从名称映射到数据源
    # 这里我们简化为直接按名称查询
    data_source = db.query(crud.data_source.model).filter(crud.data_source.model.name == request.data_source_name).first()

    if not data_source:
        raise HTTPException(status_code=404, detail=f"Data source '{request.data_source_name}' not found.")
    
    df = await data_retrieval_service.fetch_data(data_source)
    if df.empty:
        return {"data": [], "dataframe_str": "No data found."}
    
    return {
        "data": df.to_dict(orient='records'),
        "dataframe_str": df.to_string()
    }

# --- Chart Generation Tool ---
from app.api.endpoints.ai import ChartRequest, ChartResponse, get_ai_service
from app.services.ai_service import AIService

@router.post("/generate-chart", response_model=ChartResponse)
def generate_chart(
    *, 
    request: ChartRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    一个用于LLM的工具：根据结构化数据和自然语言描述生成图表。
    """
    image_base64 = ai_service.generate_chart_from_description(
        data=request.data, 
        description=request.description
    )
    return {"image_base64": image_base64} 