import os
# No longer need requests here!
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict
from sqlalchemy.orm import Session
import pandas as pd
from pathlib import Path

from app import crud, schemas
from app.api import deps
from app.services.ai_service import ai_service
from app.services.word_generator_service import word_generator_service
from app.services.computation_service import computation_service
from app.services.mcp_client import mcp_client  # Import our new client
from app.services.email_service import email_service

router = APIRouter()
REPORTS_DIR = "generated_reports"

class ReportGenerationRequest(BaseModel):
    template_id: int
    report_name: str
    recipients: List[str] = []

class ReportGenerationResponse(BaseModel):
    status: str
    message: str
    report_path: str = None

def send_email_notification(recipients: List[str], report_name: str, file_path: str):
    """Background task to send an email notification with the report."""
    subject = f"自动化报告已生成: {report_name}"
    body = f"您好，\n\n附件中是您订阅的最新报告 '{report_name}'。\n\n此邮件由AutoReportAI系统自动发出，请勿回复。"
    email_service.send_email(
        recipients=recipients,
        subject=subject,
        body=body,
        attachment_path=Path(file_path),
    )

def _get_data_from_source(sql_query: str) -> pd.DataFrame:
    """ Mock function to simulate fetching data and returning a pandas DataFrame. """
    print(f"Executing SQL: {sql_query}")
    if "region" in sql_query.lower():
        data = [
            {"region": "昆明", "sales": 520000, "units_sold": 120},
            {"region": "大理", "sales": 410000, "units_sold": 95},
            {"region": "丽江", "sales": 630000, "units_sold": 150},
            {"region": "西双版纳", "sales": 350000, "units_sold": 80},
            {"region": "香格里拉", "sales": 280000, "units_sold": 65},
        ]
        return pd.DataFrame(data)
    elif "total_sales" in sql_query.lower():
        return pd.DataFrame([{"total": 2190000}])
    return pd.DataFrame()

# The messy _call_ai_chart_service function is now gone.


@router.post("/generate", response_model=ReportGenerationResponse)
def generate_report(
    *,
    db: Session = Depends(deps.get_db),
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Orchestrates the end-to-end report generation process.
    """
    # 1. Fetch Template and Mappings
    template = crud.template.get(db=db, id=request.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # 2. Fetch data for all 'query' type placeholders, returning DataFrames
    final_data = {}
    data_context = {} # This will hold DataFrames for computation
    query_mappings = [m for m in template.mappings if m.placeholder_type == "query" or m.placeholder_type in ["chart", "table"]]
    
    for mapping in query_mappings:
        df = _get_data_from_source(mapping.source_logic)
        if not df.empty:
            data_context[mapping.placeholder_name] = df
            
            if mapping.placeholder_type == "query":
                # For scalar queries, extract the first value from the DataFrame
                final_data[mapping.placeholder_name] = df.iloc[0, 0]
            else: # Chart or Table
                # For charts/tables, we'll later need the data as a list of dicts for JSON serialization
                final_data[mapping.placeholder_name] = df.to_dict(orient='records')

    # 3. Process 'computed' type placeholders using DataFrames
    computed_mappings = [m for m in template.mappings if m.placeholder_type == "computed"]
    for mapping in computed_mappings:
        try:
            # The computation function receives the context of all DataFrames
            computed_result = computation_service.execute(mapping.source_logic, data_context)
            
            # The result could be a scalar value or a new DataFrame
            if isinstance(computed_result, pd.DataFrame):
                # If the function returns a new DataFrame, we might use it to update an existing table
                # or create a new one. For simplicity, let's assume it replaces a placeholder.
                data_context[mapping.placeholder_name] = computed_result
                final_data[mapping.placeholder_name] = computed_result.to_dict(orient='records')
            else:
                # If it's a scalar value, just add it to the final data
                final_data[mapping.placeholder_name] = computed_result

        except ValueError as e:
            print(f"Skipping computed field '{mapping.placeholder_name}' due to error: {e}")
            final_data[mapping.placeholder_name] = "[计算错误]"

    # 4. Call AI Service for charts VIA FastMCP CLIENT
    chart_mappings = [m for m in template.mappings if m.placeholder_type == "chart"]
    for mapping in chart_mappings:
        chart_data = final_data.get(mapping.placeholder_name)
        if chart_data:
            # Clean, abstract, and robust call using our client
            response = mcp_client.post(
                service_name="ai_service",
                endpoint="/generate-chart",
                payload={"description": mapping.description, "data": chart_data}
            )
            
            if response:
                final_data[mapping.placeholder_name] = response.get("image_base64", "")
            else:
                final_data[mapping.placeholder_name] = "[AI图表生成失败]"

    # 5. Call AI Service for text summary (if requested)
    # We can check if a specific placeholder like 'ai_summary' exists.
    # For now, let's assume if any text placeholder exists, we might want a summary.
    # A better approach would be a specific mapping type 'ai_text'.
    if any(p.type == 'scalar' for p in template.parsed_structure.get('placeholders', [])):
        # Let's assume a special placeholder name 'ai_summary' triggers this
        if 'ai_summary' in [p.get('name') for p in template.parsed_structure.get('placeholders', [])]:
             summary_text = ai_service.generate_text_summary(final_data)
             final_data["ai_summary"] = summary_text
    
    # 6. Generate Word Document
    os.makedirs(REPORTS_DIR, exist_ok=True)
    output_path = os.path.join(REPORTS_DIR, f"{request.report_name}.docx")
    
    word_generator_service.generate_report(
        template_path=template.file_path,
        output_path=output_path,
        data=final_data
    )

    # 7. Send Email in Background
    if request.recipients:
        background_tasks.add_task(send_email_notification, request.recipients, request.report_name, output_path)

    return {
        "status": "success",
        "message": "Report generation process started.",
        "report_path": output_path
    }
