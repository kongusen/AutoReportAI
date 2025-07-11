from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any

router = APIRouter()

class DataRequirement(BaseModel):
    placeholders: List[str]
    charts: List[str]
    tables: List[str]

class FetchedData(BaseModel):
    data: Dict[str, Any]

@router.post("/fetch", response_model=FetchedData)
def fetch_data(requirements: DataRequirement):
    """
    Corresponds to "组织数据溯源" and "数据分析".
    
    This MCP interface receives data requirements (placeholders, charts, tables)
    and returns the fetched and processed data. It would interact with
    a database, run SQL queries, and perform calculations.
    
    (This is a mock implementation)
    """
    # In a real implementation, this service would connect to a business DB.
    # It would map requirements like "total_sales" to specific SQL queries,
    # execute them, and perform any necessary analysis or calculations.
    
    mock_data = {
        "project_name": "云南旅游项目",
        "report_date": "2023-10-27",
        "total_sales": 1500000,
        "sales_by_region_chart": {
            "type": "bar",
            "data": {"昆明": 500000, "大理": 400000, "丽江": 600000}
        },
        "detailed_sales_data_table": [
            {"region": "昆明", "sales": 500000, "growth": "5%"},
            {"region": "大理", "sales": 400000, "growth": "3%"},
            {"region": "丽江", "sales": 600000, "growth": "8%"}
        ]
    }
    
    # Filter the data to return only what was requested
    response_data = {}
    for key in requirements.placeholders:
        if key in mock_data:
            response_data[key] = mock_data[key]
    for key in requirements.charts:
        if key in mock_data:
            response_data[key] = mock_data[key]
    for key in requirements.tables:
        if key in mock_data:
            response_data[key] = mock_data[key]
            
    return {"data": response_data}
