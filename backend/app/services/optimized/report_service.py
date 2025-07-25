"""
优化的报告生成服务
集成批处理、查询优化和异步处理
"""

import asyncio
import json
from typing import Dict, List, Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session

from app.crud.optimized.crud_report import crud_report
from app.crud.optimized.crud_template import crud_template
from app.crud.optimized.crud_data_source import crud_data_source
from app.crud.optimized.crud_task import crud_task
from app.models.optimized.report import Report, ReportStatus, ReportFormat
from app.models.optimized.template import Template
from app.models.optimized.task import Task, TaskType, TaskStatus
from app.schemas.report_history import ReportCreate, ReportUpdate
from app.services.optimized.base_service import BaseService, ValidationError, ServiceException
from app.services.intelligent_placeholder.batch_processor import BatchPlaceholderProcessor
from app.services.data_processing.query_optimizer import QueryOptimizer
from app.services.async_mcp_client import AsyncMCPClient


class ReportGenerationService(BaseService):
    """报告生成服务"""
    
    def __init__(self):
        super().__init__(crud_report, "Report")
        self.batch_processor = BatchPlaceholderProcessor()
        self.query_optimizer = QueryOptimizer()
        self.mcp_client = AsyncMCPClient()
    
    def _validate_create(self, obj_in: ReportCreate, user_id: Union[UUID, str] = None):
        """验证报告创建"""
        if not obj_in.title or len(obj_in.title.strip()) < 3:
            raise ValidationError("报告标题不能少于3个字符", "title")
        
        # 如果指定了模板，验证模板存在且可用
        if hasattr(obj_in, 'template_id') and obj_in.template_id:
            # 这里需要验证模板存在性，简化处理
            pass
    
    async def generate_report(
        self,
        db: Session,
        *,
        template_id: Union[UUID, str],
        data_source_id: Union[UUID, str] = None,
        user_id: Union[UUID, str],
        generation_config: Dict = None,
        format: ReportFormat = ReportFormat.HTML
    ) -> Report:
        """生成报告"""
        try:
            self._log_operation("generate_report", {
                "template_id": str(template_id),
                "data_source_id": str(data_source_id) if data_source_id else None,
                "user_id": str(user_id),
                "format": format.value
            })
            
            # 获取模板
            template = crud_template.get(db, id=template_id)
            if not template:
                raise ValidationError(f"模板 {template_id} 不存在", "template_id")
            
            # 获取数据源
            data_source = None
            if data_source_id:
                data_source = crud_data_source.get(db, id=data_source_id)
                if not data_source:
                    raise ValidationError(f"数据源 {data_source_id} 不存在", "data_source_id")
            
            # 创建任务
            task = await self._create_generation_task(
                db, template, data_source, user_id, generation_config
            )
            
            # 创建报告记录
            report_data = ReportCreate(
                title=f"{template.name} - {self._get_current_timestamp()}",
                description=f"基于模板 '{template.name}' 生成的报告",
                report_type=self._map_template_type_to_report_type(template.template_type),
                template_id=template.id,
                data_source_id=data_source.id if data_source else None,
                task_id=task.id,
                format=format,
                generation_config=generation_config or {}
            )
            
            report = crud_report.create_with_user(db, obj_in=report_data, user_id=user_id)
            
            # 开始生成
            crud_report.start_generation(db, report_id=report.id)
            crud_task.start_task(db, task_id=task.id)
            
            # 异步生成报告内容
            asyncio.create_task(self._generate_report_content(
                db, report, template, data_source, task, generation_config
            ))
            
            return report
            
        except Exception as e:
            self._handle_error("generate_report", e, {"template_id": str(template_id)})
    
    async def _create_generation_task(
        self,
        db: Session,
        template: Template,
        data_source,
        user_id: Union[UUID, str],
        generation_config: Dict = None
    ) -> Task:
        """创建生成任务"""
        from app.schemas.task import TaskCreate
        
        task_data = TaskCreate(
            name=f"生成报告: {template.name}",
            description=f"基于模板 '{template.name}' 生成报告",
            task_type=TaskType.REPORT_GENERATION,
            task_config={
                "template_id": str(template.id),
                "data_source_id": str(data_source.id) if data_source else None,
                "generation_config": generation_config or {}
            },
            estimated_duration=self._estimate_generation_time(template),
            total_steps=self._calculate_generation_steps(template)
        )
        
        return crud_task.create_with_user(db, obj_in=task_data, user_id=user_id)
    
    async def _generate_report_content(
        self,
        db: Session,
        report: Report,
        template: Template,
        data_source,
        task: Task,
        generation_config: Dict = None
    ):
        """异步生成报告内容"""
        try:
            # 更新任务进度
            crud_task.update_progress(
                db, task_id=task.id, progress=10, current_step="解析模板占位符"
            )
            
            # 1. 解析模板占位符
            placeholders = self._extract_placeholders(template.content)
            if not placeholders:
                content = template.content  # 无占位符，直接使用模板内容
            else:
                # 更新任务进度
                crud_task.update_progress(
                    db, task_id=task.id, progress=30, current_step="批量处理占位符"
                )
                
                # 2. 批量处理占位符
                processed_placeholders = await self.batch_processor.process_placeholders_batch(
                    placeholders, data_source, generation_config or {}
                )
                
                # 更新任务进度
                crud_task.update_progress(
                    db, task_id=task.id, progress=70, current_step="生成报告内容"
                )
                
                # 3. 替换占位符生成最终内容
                content = self._replace_placeholders(template.content, processed_placeholders)
            
            # 更新任务进度
            crud_task.update_progress(
                db, task_id=task.id, progress=90, current_step="保存报告结果"
            )
            
            # 4. 保存报告结果
            data_size = len(content.encode('utf-8'))
            record_count = len(placeholders) if placeholders else 0
            
            crud_report.complete_generation(
                db,
                report_id=report.id,
                content=content,
                data_size=data_size,
                record_count=record_count
            )
            
            # 完成任务
            crud_task.complete_task(
                db,
                task_id=task.id,
                success=True,
                result=f"报告生成成功，内容大小: {data_size} 字节"
            )
            
        except Exception as e:
            # 报告生成失败
            error_message = str(e)
            crud_report.fail_generation(
                db, report_id=report.id, error_message=error_message
            )
            crud_task.complete_task(
                db, task_id=task.id, success=False, error_message=error_message
            )
            
            self.logger.error(f"报告生成失败: {error_message}", extra={
                "report_id": str(report.id),
                "template_id": str(template.id)
            })
    
    def _extract_placeholders(self, content: str) -> List[Dict]:
        """提取占位符"""
        import re
        
        # 简化的占位符提取逻辑
        placeholder_pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(placeholder_pattern, content)
        
        placeholders = []
        for i, match in enumerate(matches):
            placeholders.append({
                "id": f"placeholder_{i}",
                "name": match.strip(),
                "type": "data_query",  # 简化处理
                "content": match.strip()
            })
        
        return placeholders
    
    def _replace_placeholders(self, content: str, processed_placeholders: Dict) -> str:
        """替换占位符"""
        result_content = content
        
        for placeholder_id, result in processed_placeholders.items():
            if isinstance(result, dict) and "processed_result" in result:
                # 简化的替换逻辑
                placeholder_name = result.get("original_name", "")
                if placeholder_name:
                    pattern = r'\{\{' + re.escape(placeholder_name) + r'\}\}'
                    replacement = str(result["processed_result"])
                    result_content = re.sub(pattern, replacement, result_content)
        
        return result_content
    
    def _estimate_generation_time(self, template: Template) -> int:
        """估算生成时间"""
        base_time = 30  # 基础30秒
        placeholder_count = template.placeholder_count or 0
        
        # 每个占位符增加10秒
        estimated_time = base_time + (placeholder_count * 10)
        
        return min(estimated_time, 600)  # 最多10分钟
    
    def _calculate_generation_steps(self, template: Template) -> int:
        """计算生成步骤数"""
        steps = 4  # 基础步骤：解析、处理、生成、保存
        placeholder_count = template.placeholder_count or 0
        
        # 复杂模板增加步骤
        if placeholder_count > 5:
            steps += 2
        
        return steps
    
    def _map_template_type_to_report_type(self, template_type):
        """映射模板类型到报告类型"""
        from app.models.optimized.report import ReportType
        from app.models.optimized.template import TemplateType
        
        mapping = {
            TemplateType.REPORT: ReportType.STANDARD,
            TemplateType.DASHBOARD: ReportType.DASHBOARD,
            TemplateType.CHART: ReportType.ANALYTICS,
        }
        
        return mapping.get(template_type, ReportType.STANDARD)
    
    def get_generation_status(
        self,
        db: Session,
        *,
        report_id: Union[UUID, str],
        user_id: Union[UUID, str] = None
    ) -> Dict[str, any]:
        """获取生成状态"""
        try:
            self._log_operation("get_generation_status", {"report_id": str(report_id)})
            
            report = self.get_by_id(db, id=report_id, user_id=user_id)
            
            status_data = {
                "report_id": str(report.id),
                "status": report.status.value,
                "progress": 0,
                "current_step": "准备中",
                "estimated_completion": None
            }
            
            # 如果有关联任务，获取任务状态
            if report.task_id:
                task = crud_task.get(db, id=report.task_id)
                if task:
                    status_data.update({
                        "progress": task.progress,
                        "current_step": task.current_step or "处理中",
                        "estimated_completion": task.estimated_duration
                    })
            
            return status_data
            
        except Exception as e:
            self._handle_error("get_generation_status", e, {"report_id": str(report_id)})
    
    def get_user_reports(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str],
        status: ReportStatus = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Report]:
        """获取用户报告"""
        try:
            self._log_operation("get_user_reports", {"user_id": str(user_id)})
            
            if status:
                return crud_report.get_by_status(db, status=status, user_id=user_id)
            else:
                return crud_report.get_by_user(db, user_id=user_id, skip=skip, limit=limit)
                
        except Exception as e:
            self._handle_error("get_user_reports", e, {"user_id": str(user_id)})
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


# 创建服务实例
report_service = ReportGenerationService()