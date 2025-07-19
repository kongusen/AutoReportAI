from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.mcp_analytics_tools import MCPAnalyticsAPI

router = APIRouter()


class AnalyticsRequest(BaseModel):
    data: Dict[str, List[Any]] = Field(..., description="分析数据")
    operation: str = Field(..., description="分析操作类型")
    date_column: Optional[str] = Field(None, description="日期列名")
    value_columns: Optional[List[str]] = Field(None, description="数值列名")
    group_columns: Optional[List[str]] = Field(None, description="分组列名")
    parameters: Optional[Dict[str, Any]] = Field(None, description="分析参数")


class BatchAnalyticsRequest(BaseModel):
    data: Dict[str, List[Any]] = Field(..., description="分析数据")
    operations: List[str] = Field(..., description="分析操作类型列表")
    date_column: Optional[str] = Field(None, description="日期列名")
    value_columns: Optional[List[str]] = Field(None, description="数值列名")
    group_columns: Optional[List[str]] = Field(None, description="分组列名")
    parameters: Optional[Dict[str, Any]] = Field(None, description="分析参数")


class AnalyticsResponse(BaseModel):
    operation: str
    status: str
    result: Dict[str, Any]
    metadata: Dict[str, Any]


@router.post("/analyze", response_model=AnalyticsResponse)
async def analyze_data(request: AnalyticsRequest):
    """执行单种统计分析"""
    api = MCPAnalyticsAPI()

    try:
        result = await api.analyze_data(
            data=request.data,
            operation=request.operation,
            date_column=request.date_column,
            value_columns=request.value_columns,
            group_columns=request.group_columns,
            parameters=request.parameters,
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze/batch")
async def batch_analyze_data(request: BatchAnalyticsRequest):
    """批量执行多种统计分析"""
    api = MCPAnalyticsAPI()

    try:
        result = await api.batch_analyze(
            data=request.data,
            operations=request.operations,
            date_column=request.date_column,
            value_columns=request.value_columns,
            group_columns=request.group_columns,
            parameters=request.parameters,
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/operations")
def list_analytics_operations():
    """列出所有支持的统计分析操作"""
    from app.services.mcp_analytics_tools import AnalyticsOperationType

    operations = [
        {
            "operation": AnalyticsOperationType.PERIOD_COMPARISON,
            "name": "环比分析",
            "description": "计算相邻时间段的数值变化",
        },
        {
            "operation": AnalyticsOperationType.YEAR_OVER_YEAR,
            "name": "同比分析",
            "description": "计算与去年同期相比的变化",
        },
        {
            "operation": AnalyticsOperationType.SUMMARY_STATISTICS,
            "name": "汇总统计",
            "description": "计算基本的统计指标（计数、求和、均值、标准差等）",
        },
        {
            "operation": AnalyticsOperationType.GROWTH_RATE,
            "name": "增长率",
            "description": "计算时间序列的增长率",
        },
        {
            "operation": AnalyticsOperationType.PROPORTION,
            "name": "比例分析",
            "description": "计算各部分占总体的比例",
        },
        {
            "operation": AnalyticsOperationType.TREND_ANALYSIS,
            "name": "趋势分析",
            "description": "分析数据的线性趋势",
        },
        {
            "operation": AnalyticsOperationType.MOVING_AVERAGE,
            "name": "移动平均",
            "description": "计算移动平均值和平滑数据",
        },
        {
            "operation": AnalyticsOperationType.PERCENTILE,
            "name": "百分位数",
            "description": "计算数据的百分位数分布",
        },
    ]

    return {"operations": operations}


@router.post("/analyze/sample")
async def get_sample_analysis():
    """获取示例分析数据"""
    from datetime import datetime, timedelta

    import pandas as pd

    # 生成示例数据
    dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
    np.random.seed(42)

    sample_data = {
        "date": [d.strftime("%Y-%m-%d") for d in dates],
        "sales": [100 + i * 0.5 + np.random.normal(0, 10) for i in range(len(dates))],
        "orders": [50 + i * 0.2 + np.random.normal(0, 5) for i in range(len(dates))],
        "category": ["A"] * (len(dates) // 2) + ["B"] * (len(dates) // 2),
    }

    return {
        "sample_data": sample_data,
        "description": "示例销售数据，包含日期、销售额、订单数和类别",
    }
