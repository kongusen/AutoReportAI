import csv
import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import crud, models
from app.api import deps
from app.services.enhanced_data_source_service import enhanced_data_source_service

router = APIRouter()


class ExportRequest(BaseModel):
    data_source_id: Optional[int] = None
    task_id: Optional[int] = None
    history_id: Optional[int] = None
    export_format: str = "csv"  # csv, json, excel, pdf
    filters: Optional[Dict[str, Any]] = None
    columns: Optional[List[str]] = None
    limit: Optional[int] = None


class BulkExportRequest(BaseModel):
    export_items: List[ExportRequest]
    export_format: str = "zip"
    include_metadata: bool = True


@router.post("/export-data")
async def export_data(
    *,
    db: Session = Depends(deps.get_db),
    export_request: ExportRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Export data from various sources in different formats.
    """
    try:
        # 获取数据
        if export_request.data_source_id:
            data = await export_from_data_source(
                export_request.data_source_id,
                export_request.filters,
                export_request.columns,
                export_request.limit,
            )
            filename_base = f"data_source_{export_request.data_source_id}"

        elif export_request.task_id:
            data = await export_from_task(db, export_request.task_id, current_user.id)
            filename_base = f"task_{export_request.task_id}"

        elif export_request.history_id:
            data = await export_from_history(
                db, export_request.history_id, current_user.id
            )
            filename_base = f"history_{export_request.history_id}"

        else:
            raise HTTPException(
                status_code=400,
                detail="Must specify data_source_id, task_id, or history_id",
            )

        # 根据格式导出
        if export_request.export_format.lower() == "csv":
            return export_as_csv(data, f"{filename_base}.csv")

        elif export_request.export_format.lower() == "json":
            return export_as_json(data, f"{filename_base}.json")

        elif export_request.export_format.lower() == "excel":
            return export_as_excel(data, f"{filename_base}.xlsx")

        elif export_request.export_format.lower() == "pdf":
            return export_as_pdf(data, f"{filename_base}.pdf")

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported export format: {export_request.export_format}",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/bulk-export")
async def bulk_export(
    *,
    db: Session = Depends(deps.get_db),
    bulk_request: BulkExportRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Export multiple data sources in a single archive.
    """
    try:
        import os
        import tempfile
        import zipfile

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "bulk_export.zip")

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:

                for i, export_item in enumerate(bulk_request.export_items):
                    try:
                        # 获取数据
                        if export_item.data_source_id:
                            data = await export_from_data_source(
                                export_item.data_source_id,
                                export_item.filters,
                                export_item.columns,
                                export_item.limit,
                            )
                            base_name = f"data_source_{export_item.data_source_id}"

                        elif export_item.task_id:
                            data = await export_from_task(
                                db, export_item.task_id, current_user.id
                            )
                            base_name = f"task_{export_item.task_id}"

                        elif export_item.history_id:
                            data = await export_from_history(
                                db, export_item.history_id, current_user.id
                            )
                            base_name = f"history_{export_item.history_id}"

                        else:
                            continue

                        # 生成文件内容
                        if export_item.export_format.lower() == "csv":
                            content = generate_csv_content(data)
                            filename = f"{base_name}.csv"

                        elif export_item.export_format.lower() == "json":
                            content = generate_json_content(data)
                            filename = f"{base_name}.json"

                        else:
                            content = generate_csv_content(data)  # 默认CSV
                            filename = f"{base_name}.csv"

                        # 添加到ZIP
                        zip_file.writestr(filename, content)

                    except Exception as e:
                        # 记录错误但继续处理其他项目
                        error_content = f"Export failed: {str(e)}"
                        zip_file.writestr(f"error_{i}.txt", error_content)

                # 添加元数据
                if bulk_request.include_metadata:
                    metadata = {
                        "export_timestamp": datetime.now().isoformat(),
                        "user_id": str(current_user.id),
                        "total_items": len(bulk_request.export_items),
                        "export_format": bulk_request.export_format,
                    }
                    zip_file.writestr("metadata.json", json.dumps(metadata, indent=2))

            # 读取ZIP文件内容
            with open(zip_path, "rb") as zip_file:
                zip_content = zip_file.read()

            # 返回ZIP文件
            return Response(
                content=zip_content,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename=bulk_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                },
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk export failed: {str(e)}")


async def export_from_data_source(
    data_source_id: int,
    filters: Optional[Dict[str, Any]] = None,
    columns: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """从数据源导出数据"""
    query_params = {}

    if limit:
        query_params["limit"] = limit
        query_params["nrows"] = limit

    # 获取数据
    df = await enhanced_data_source_service.fetch_data(
        str(data_source_id), query_params
    )

    # 应用过滤器
    if filters:
        for column, filter_value in filters.items():
            if column in df.columns:
                if isinstance(filter_value, dict):
                    # 支持复杂过滤器 {"operator": ">=", "value": 100}
                    operator = filter_value.get("operator", "==")
                    value = filter_value.get("value")

                    if operator == ">=":
                        df = df[df[column] >= value]
                    elif operator == "<=":
                        df = df[df[column] <= value]
                    elif operator == ">":
                        df = df[df[column] > value]
                    elif operator == "<":
                        df = df[df[column] < value]
                    elif operator == "!=":
                        df = df[df[column] != value]
                    elif operator == "contains":
                        df = df[
                            df[column].astype(str).str.contains(str(value), na=False)
                        ]
                    else:  # ==
                        df = df[df[column] == value]
                else:
                    # 简单过滤器
                    df = df[df[column] == filter_value]

    # 选择列
    if columns:
        available_columns = [col for col in columns if col in df.columns]
        if available_columns:
            df = df[available_columns]

    return df


async def export_from_task(db: Session, task_id: int, user_id: str) -> pd.DataFrame:
    """从任务导出数据"""
    task = crud.task.get(db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 检查权限
    if str(task.owner_id) != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # 获取任务相关的数据源数据
    return await export_from_data_source(task.data_source_id)


async def export_from_history(
    db: Session, history_id: int, user_id: str
) -> pd.DataFrame:
    """从历史记录导出数据"""
    history = crud.report_history.get(db, id=history_id)
    if not history:
        raise HTTPException(status_code=404, detail="History record not found")

    # 检查权限 - 需要通过task检查
    task = crud.task.get(db, id=history.task_id)
    if not task or str(task.owner_id) != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # 从历史记录的数据源导出
    return await export_from_data_source(task.data_source_id)


def export_as_csv(data: pd.DataFrame, filename: str) -> StreamingResponse:
    """导出为CSV格式"""
    output = io.StringIO()
    data.to_csv(output, index=False)
    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def export_as_json(data: pd.DataFrame, filename: str) -> StreamingResponse:
    """导出为JSON格式"""
    json_data = data.to_json(orient="records", indent=2)

    return StreamingResponse(
        io.BytesIO(json_data.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def export_as_excel(data: pd.DataFrame, filename: str) -> StreamingResponse:
    """导出为Excel格式"""
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        data.to_excel(writer, sheet_name="Data", index=False)

        # 添加元数据工作表
        metadata_df = pd.DataFrame(
            {
                "Property": ["Export Date", "Row Count", "Column Count"],
                "Value": [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    len(data),
                    len(data.columns),
                ],
            }
        )
        metadata_df.to_excel(writer, sheet_name="Metadata", index=False)

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def export_as_pdf(data: pd.DataFrame, filename: str) -> StreamingResponse:
    """导出为PDF格式"""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        elements = []

        # 添加标题
        styles = getSampleStyleSheet()
        title = Paragraph("Data Export Report", styles["Title"])
        elements.append(title)

        # 限制显示的行数和列数（PDF空间有限）
        max_rows = 50
        max_cols = 10

        display_data = data.head(max_rows)
        if len(data.columns) > max_cols:
            display_data = display_data.iloc[:, :max_cols]

        # 准备表格数据
        table_data = [display_data.columns.tolist()]
        for _, row in display_data.iterrows():
            table_data.append([str(val)[:20] for val in row.tolist()])  # 限制单元格长度

        # 创建表格
        table = Table(table_data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("FONTSIZE", (0, 1), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        elements.append(table)

        # 添加统计信息
        if len(data) > max_rows or len(data.columns) > max_cols:
            note = Paragraph(
                f"Note: Showing {len(display_data)} of {len(data)} rows and {len(display_data.columns)} of {len(data.columns)} columns",
                styles["Normal"],
            )
            elements.append(note)

        doc.build(elements)
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="PDF export requires reportlab package. Please install it.",
        )


def generate_csv_content(data: pd.DataFrame) -> str:
    """生成CSV内容"""
    output = io.StringIO()
    data.to_csv(output, index=False)
    return output.getvalue()


def generate_json_content(data: pd.DataFrame) -> str:
    """生成JSON内容"""
    return data.to_json(orient="records", indent=2)


@router.get("/export-formats")
def get_supported_export_formats(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """获取支持的导出格式"""
    return {
        "formats": [
            {
                "name": "CSV",
                "value": "csv",
                "description": "Comma-separated values format",
                "mime_type": "text/csv",
            },
            {
                "name": "JSON",
                "value": "json",
                "description": "JavaScript Object Notation format",
                "mime_type": "application/json",
            },
            {
                "name": "Excel",
                "value": "excel",
                "description": "Microsoft Excel format",
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
            {
                "name": "PDF",
                "value": "pdf",
                "description": "Portable Document Format",
                "mime_type": "application/pdf",
            },
        ],
        "bulk_formats": [
            {
                "name": "ZIP Archive",
                "value": "zip",
                "description": "Multiple files in ZIP archive",
                "mime_type": "application/zip",
            }
        ],
    }
