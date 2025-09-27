"""
Business Context Coordinator (Domain)

Coordinates the three high-level contexts needed for placeholder processing:
- Template context (id, content, business domain)
- Data source schema context (tables, columns)
- Task/time context (execution time, schedule)

This service intentionally returns structured, non-prompt context that can be
consumed by Domain services and Infra adapters (which build prompts and agent
inputs).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class TemplateContextRef:
    template_id: str
    content: str
    business_domain: str = "general"


@dataclass
class DataSourceSchemaRef:
    data_source_id: str
    tables: List[str] = field(default_factory=list)
    columns: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class TaskContextRef:
    execution_time: datetime
    timezone: str = "Asia/Shanghai"
    schedule: Dict[str, Any] = field(default_factory=lambda: {"frequency": "daily"})
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportContext:
    template: TemplateContextRef
    schema: DataSourceSchemaRef
    task: TaskContextRef
    stage: str  # template_analysis | task_processing | report_assembly


class BusinessContextCoordinator:
    """Builds ReportContext from IDs and raw inputs.

    Note: Data fetching (template content, schema) is intentionally mocked here
    and should be delegated to application/infrastructure in production.
    """

    async def build(
        self,
        template_id: str,
        data_source_id: str,
        task_info: Dict[str, Any],
        stage: str,
        template_content_loader: Optional[callable] = None,
        schema_loader: Optional[callable] = None,
    ) -> ReportContext:
        # Load template content
        if template_content_loader:
            content, biz_domain = await template_content_loader(template_id)
        else:
            content, biz_domain = ("", "general")

        # Load schema
        if schema_loader:
            tables, columns = await schema_loader(data_source_id)
        else:
            tables, columns = ([], {})

        # Build task context
        task = TaskContextRef(
            execution_time=task_info.get("execution_time", datetime.now()),
            timezone=task_info.get("timezone", "Asia/Shanghai"),
            schedule=task_info.get("schedule", {"frequency": "daily"}),
            parameters=task_info.get("parameters", {}),
        )

        return ReportContext(
            template=TemplateContextRef(template_id=template_id, content=content, business_domain=biz_domain),
            schema=DataSourceSchemaRef(data_source_id=data_source_id, tables=tables, columns=columns),
            task=task,
            stage=stage,
        )

