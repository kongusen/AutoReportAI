from datetime import datetime, timedelta
from typing import Any, Dict

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import deps

router = APIRouter()

# --- Config Loading ---
# Load the placeholder-to-SQL mapping at startup
try:
    with open("app/placeholder_mapping.yaml", "r") as f:
        query_mapping = yaml.safe_load(f)
except FileNotFoundError:
    query_mapping = {}

try:
    with open("app/computation_mapping.yaml", "r") as f:
        computation_mapping = yaml.safe_load(f)
except FileNotFoundError:
    computation_mapping = {}


# --- Models ---
class DateConstraintRequest(BaseModel):
    report_type: str  # e.g., "daily", "weekly", "monthly"


class DateConstraintResponse(BaseModel):
    start_date: str
    end_date: str


class DataPlaceholderRequest(BaseModel):
    placeholder: str
    params: Dict[str, Any] = {}  # e.g., {"start_date": "...", "end_date": "..."}


class ComputationPlaceholderRequest(BaseModel):
    placeholder: str
    context: Dict[str, Any]


class PlaceholderResponse(BaseModel):
    placeholder: str
    value: Any


# --- Endpoints ---
@router.post("/resolve-date-constraint", response_model=DateConstraintResponse)
def resolve_date_constraint(request: DateConstraintRequest):
    """
    Resolves a report type into a concrete date range.
    """
    today = datetime.now()
    report_type = request.report_type.lower()

    if report_type == "daily":
        start_date = today - timedelta(days=1)
        end_date = today
    elif report_type == "weekly":
        start_of_week = today - timedelta(days=today.weekday())
        start_date = start_of_week - timedelta(days=7)
        end_date = start_of_week - timedelta(seconds=1)
    elif report_type == "monthly":
        first_day_of_current_month = today.replace(day=1)
        last_day_of_last_month = first_day_of_current_month - timedelta(days=1)
        first_day_of_last_month = last_day_of_last_month.replace(day=1)
        start_date = first_day_of_last_month
        end_date = last_day_of_last_month
    else:
        raise HTTPException(
            status_code=400, detail=f"Unsupported report type: {request.report_type}"
        )

    return DateConstraintResponse(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
    )


@router.post("/resolve-data-placeholder", response_model=PlaceholderResponse)
def resolve_data_placeholder(
    *, db: Session = Depends(deps.get_db), request: DataPlaceholderRequest
):
    """
    Resolves a data placeholder by executing a pre-defined SQL query from the mapping file.
    """
    placeholder = request.placeholder
    if placeholder not in query_mapping:
        raise HTTPException(
            status_code=404, detail=f"Placeholder '{placeholder}' not found in mapping."
        )

    query_info = query_mapping[placeholder]
    sql_query = text(query_info["query"])

    try:
        # Use the injected DB session to execute the query
        result = db.execute(sql_query, request.params)
        value = result.scalar_one_or_none()

        return PlaceholderResponse(placeholder=placeholder, value=value)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute query for '{placeholder}': {str(e)}",
        )


@router.post("/resolve-computation-placeholder", response_model=PlaceholderResponse)
def resolve_computation_placeholder(request: ComputationPlaceholderRequest):
    """
    Resolves a computational placeholder by evaluating a pre-defined Python expression.
    """
    placeholder = request.placeholder
    context = request.context

    if placeholder not in computation_mapping:
        raise HTTPException(
            status_code=404,
            detail=f"Computation placeholder '{placeholder}' not found in mapping.",
        )

    comp_info = computation_mapping[placeholder]
    dependencies = comp_info.get("dependencies", [])
    expression = comp_info.get("expression")

    if not all(dep in context for dep in dependencies):
        missing = [dep for dep in dependencies if dep not in context]
        raise HTTPException(
            status_code=400,
            detail=f"Missing dependencies for '{placeholder}': {missing}",
        )

    eval_context = {dep: context[dep] for dep in dependencies}

    try:
        # Note: Using eval can be risky if expressions are from untrusted sources.
        # Here, they come from our own controlled YAML file, making it safe.
        value = eval(expression, {"__builtins__": {}}, eval_context)
        return PlaceholderResponse(placeholder=placeholder, value=value)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to compute '{placeholder}': {str(e)}"
        )
