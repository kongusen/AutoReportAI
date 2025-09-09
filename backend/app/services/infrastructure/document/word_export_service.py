"""
Word文档导出服务

负责将报告数据导出为Word文档，支持：
1. 模板解析和占位符替换
2. 图表插入和布局
3. 统一字体和格式设置
4. 文档结构化处理
5. 多种导出格式支持
"""

import logging
import os
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)


class DocumentFormat(Enum):
    """文档格式"""
    DOCX = "docx"
    PDF = "pdf"
    HTML = "html"


@dataclass
class DocumentConfig:
    """文档配置"""
    template_id: str
    output_format: DocumentFormat = DocumentFormat.DOCX
    font_name: str = "宋体"
    font_size: int = 12
    line_spacing: float = 1.5
    margins: Dict[str, float] = None
    header: Optional[str] = None
    footer: Optional[str] = None
    watermark: Optional[str] = None
    
    def __post_init__(self):
        if self.margins is None:
            self.margins = {"top": 2.54, "bottom": 2.54, "left": 3.17, "right": 3.17}  # cm


@dataclass
class DocumentExportResult:
    """文档导出结果"""
    success: bool
    document_path: Optional[str] = None
    file_size_bytes: int = 0
    page_count: int = 0
    export_time_seconds: float = 0.0
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WordExportService:
    """
    Word文档导出服务
    
    提供完整的Word文档生成功能：
    1. 解析模板文档
    2. 替换占位符内容
    3. 插入图表和图片
    4. 应用统一格式
    5. 导出为多种格式
    """
    
    def __init__(self, user_id: str):
        if not user_id:
            raise ValueError("user_id is required for WordExportService")
        self.user_id = user_id
        self.output_dir = f"/tmp/documents/{user_id}"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 确保导入必要的库
        self._ensure_document_dependencies()
    
    def _ensure_document_dependencies(self):
        """确保文档处理依赖库可用"""
        try:
            from docx import Document
            from docx.shared import Inches, Pt
            from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
            self.Document = Document
            self.Inches = Inches
            self.Pt = Pt
            self.WD_PARAGRAPH_ALIGNMENT = WD_PARAGRAPH_ALIGNMENT
            logger.info("Word文档处理依赖库加载成功")
        except ImportError as e:
            logger.warning(f"Word文档处理依赖库加载失败: {e}")
            self.Document = None
    
    async def export_report_document(
        self,
        template_id: str,
        placeholder_data: Dict[str, Any],
        etl_data: Dict[str, Any],
        chart_data: Dict[str, Any],
        config: Optional[DocumentConfig] = None
    ) -> DocumentExportResult:
        """
        导出报告文档
        
        Args:
            template_id: 模板ID
            placeholder_data: 占位符数据
            etl_data: ETL处理数据
            chart_data: 图表数据
            config: 文档配置
            
        Returns:
            文档导出结果
        """
        start_time = datetime.now()
        
        logger.info(f"开始导出报告文档: template_id={template_id}")
        
        if not self.Document:
            return DocumentExportResult(
                success=False,
                error="Word文档处理库不可用"
            )
        
        try:
            # 使用默认配置
            if config is None:
                config = DocumentConfig(template_id=template_id)
            
            # 1. 获取模板文档
            template_doc = await self._load_template_document(template_id)
            
            # 2. 处理占位符替换
            await self._replace_placeholders(template_doc, placeholder_data, etl_data)
            
            # 3. 插入图表
            await self._insert_charts(template_doc, chart_data)
            
            # 4. 应用文档格式
            self._apply_document_formatting(template_doc, config)
            
            # 5. 保存文档
            document_path = await self._save_document(template_doc, template_id, config.output_format)
            
            end_time = datetime.now()
            export_time = (end_time - start_time).total_seconds()
            
            # 获取文档信息
            file_size = os.path.getsize(document_path) if document_path and os.path.exists(document_path) else 0
            page_count = len(template_doc.element.body.xpath('.//w:p', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}))
            
            logger.info(f"文档导出完成: {document_path}, 大小: {file_size} bytes, 页数: {page_count}")
            
            return DocumentExportResult(
                success=True,
                document_path=document_path,
                file_size_bytes=file_size,
                page_count=max(page_count // 25, 1),  # 粗略估计页数
                export_time_seconds=export_time,
                metadata={
                    "template_id": template_id,
                    "output_format": config.output_format.value,
                    "font_name": config.font_name,
                    "export_timestamp": end_time.isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"文档导出失败: {e}")
            return DocumentExportResult(
                success=False,
                error=str(e)
            )
    
    async def _load_template_document(self, template_id: str):
        """加载模板文档"""
        try:
            from app.crud import template as crud_template
            from app.db.session import SessionLocal
            
            db = SessionLocal()
            try:
                template = crud_template.get(db, id=template_id)
                if not template:
                    raise ValueError(f"模板不存在: {template_id}")
                
                # 如果有模板文件路径，加载文档
                if hasattr(template, 'file_path') and template.file_path:
                    if os.path.exists(template.file_path):
                        return self.Document(template.file_path)
                
                # 否则创建新文档并使用模板内容
                doc = self.Document()
                
                # 添加标题
                title = doc.add_heading(template.name or '报告', 0)
                title.alignment = self.WD_PARAGRAPH_ALIGNMENT.CENTER
                
                # 添加模板内容
                if template.content:
                    # 按段落分割内容
                    paragraphs = template.content.split('\n')
                    for paragraph_text in paragraphs:
                        if paragraph_text.strip():
                            doc.add_paragraph(paragraph_text.strip())
                
                return doc
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"加载模板文档失败: {e}")
            # 返回空文档作为后备
            return self.Document()
    
    async def _replace_placeholders(
        self,
        doc,
        placeholder_data: Dict[str, Any],
        etl_data: Dict[str, Any]
    ):
        """替换文档中的占位符"""
        try:
            # 构建替换映射
            replacement_map = {}
            
            # 从占位符数据中提取替换值
            validation_results = placeholder_data.get('validation_results', [])
            for result in validation_results:
                placeholder_name = result.get('placeholder_name', '')
                if placeholder_name:
                    replacement_map[f"{{{{{placeholder_name}}}}}"] = self._get_placeholder_value(
                        result, etl_data
                    )
            
            # 替换文档中的占位符
            for paragraph in doc.paragraphs:
                for placeholder, value in replacement_map.items():
                    if placeholder in paragraph.text:
                        paragraph.text = paragraph.text.replace(placeholder, str(value))
            
            # 替换表格中的占位符
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for placeholder, value in replacement_map.items():
                            if placeholder in cell.text:
                                cell.text = cell.text.replace(placeholder, str(value))
            
            logger.debug(f"已替换 {len(replacement_map)} 个占位符")
            
        except Exception as e:
            logger.error(f"替换占位符失败: {e}")
    
    def _get_placeholder_value(
        self,
        placeholder_result: Dict[str, Any],
        etl_data: Dict[str, Any]
    ) -> str:
        """获取占位符的实际值"""
        try:
            placeholder_name = placeholder_result.get('placeholder_name', '')
            
            # 从ETL数据中查找对应的值
            for data_source_id, data_info in etl_data.items():
                transform_result = data_info.get('transform', {})
                if transform_result.get('success'):
                    data = transform_result.get('data', [])
                    if data:
                        # 简单的值提取逻辑
                        if isinstance(data, list) and data:
                            first_row = data[0]
                            if isinstance(first_row, dict):
                                # 查找匹配的字段
                                for key, value in first_row.items():
                                    if placeholder_name.lower() in key.lower():
                                        return str(value)
                                # 如果没有找到匹配字段，返回第一个数值字段
                                for key, value in first_row.items():
                                    if isinstance(value, (int, float)):
                                        return str(value)
            
            # 如果没有找到数据，返回占位符名称
            return f"[{placeholder_name}]"
            
        except Exception as e:
            logger.error(f"获取占位符值失败: {e}")
            return f"[{placeholder_name}]"
    
    async def _insert_charts(self, doc, chart_data: Dict[str, Any]):
        """在文档中插入图表"""
        try:
            chart_results = chart_data.get('data', [])
            
            for chart_result in chart_results:
                if chart_result.get('success') and chart_result.get('file_path'):
                    chart_path = chart_result['file_path']
                    
                    if os.path.exists(chart_path):
                        # 添加图表段落
                        chart_paragraph = doc.add_paragraph()
                        chart_paragraph.alignment = self.WD_PARAGRAPH_ALIGNMENT.CENTER
                        
                        # 插入图片
                        run = chart_paragraph.runs[0] if chart_paragraph.runs else chart_paragraph.add_run()
                        run.add_picture(chart_path, width=self.Inches(6))
                        
                        # 添加图表标题
                        if chart_result.get('metadata', {}).get('title'):
                            title_paragraph = doc.add_paragraph()
                            title_paragraph.alignment = self.WD_PARAGRAPH_ALIGNMENT.CENTER
                            title_run = title_paragraph.add_run(chart_result['metadata']['title'])
                            title_run.font.bold = True
                        
                        # 添加空行
                        doc.add_paragraph()
            
            logger.debug(f"已插入 {len([r for r in chart_results if r.get('success')])} 个图表")
            
        except Exception as e:
            logger.error(f"插入图表失败: {e}")
    
    def _apply_document_formatting(self, doc, config: DocumentConfig):
        """应用文档格式"""
        try:
            # 设置默认字体
            style = doc.styles['Normal']
            font = style.font
            font.name = config.font_name
            font.size = self.Pt(config.font_size)
            
            # 设置段落格式
            paragraph_format = style.paragraph_format
            paragraph_format.line_spacing = config.line_spacing
            
            # 应用到所有段落
            for paragraph in doc.paragraphs:
                paragraph.style = style
                for run in paragraph.runs:
                    run.font.name = config.font_name
                    run.font.size = self.Pt(config.font_size)
            
            # 设置页面边距
            sections = doc.sections
            for section in sections:
                section.top_margin = self.Inches(config.margins['top'] / 2.54)  # 转换cm到英寸
                section.bottom_margin = self.Inches(config.margins['bottom'] / 2.54)
                section.left_margin = self.Inches(config.margins['left'] / 2.54)
                section.right_margin = self.Inches(config.margins['right'] / 2.54)
            
            logger.debug("文档格式应用完成")
            
        except Exception as e:
            logger.error(f"应用文档格式失败: {e}")
    
    async def _save_document(
        self,
        doc,
        template_id: str,
        output_format: DocumentFormat
    ) -> str:
        """保存文档"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{template_id}_{timestamp}.{output_format.value}"
            file_path = os.path.join(self.output_dir, filename)
            
            if output_format == DocumentFormat.DOCX:
                doc.save(file_path)
            elif output_format == DocumentFormat.PDF:
                # 需要额外的PDF转换库
                docx_path = file_path.replace('.pdf', '.docx')
                doc.save(docx_path)
                file_path = await self._convert_to_pdf(docx_path, file_path)
            elif output_format == DocumentFormat.HTML:
                # 简单的HTML导出
                file_path = await self._convert_to_html(doc, file_path)
            
            logger.debug(f"文档已保存: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"保存文档失败: {e}")
            raise
    
    async def _convert_to_pdf(self, docx_path: str, pdf_path: str) -> str:
        """转换DOCX到PDF"""
        try:
            # 这里需要使用如python-docx2pdf或类似库
            # 暂时返回DOCX路径作为后备
            logger.warning("PDF转换功能未实现，返回DOCX格式")
            return docx_path
        except Exception as e:
            logger.error(f"PDF转换失败: {e}")
            return docx_path
    
    async def _convert_to_html(self, doc, html_path: str) -> str:
        """转换到HTML"""
        try:
            # 简单的HTML生成
            html_content = ["<!DOCTYPE html>", "<html><head><title>报告</title></head><body>"]
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    html_content.append(f"<p>{paragraph.text}</p>")
            
            html_content.extend(["</body></html>"])
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(html_content))
            
            return html_path
            
        except Exception as e:
            logger.error(f"HTML转换失败: {e}")
            raise
    
    def get_document_preview(self, document_path: str) -> Optional[Dict[str, Any]]:
        """获取文档预览信息"""
        try:
            if not os.path.exists(document_path):
                return None
            
            stat = os.stat(document_path)
            
            preview_info = {
                "file_path": document_path,
                "filename": os.path.basename(document_path),
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "format": os.path.splitext(document_path)[1][1:].upper()
            }
            
            # 如果是DOCX文件，获取更多信息
            if document_path.endswith('.docx') and self.Document:
                try:
                    doc = self.Document(document_path)
                    preview_info.update({
                        "paragraph_count": len(doc.paragraphs),
                        "table_count": len(doc.tables),
                        "has_images": any(
                            len(paragraph._element.xpath('.//pic:pic', 
                                namespaces={'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture'})) > 0
                            for paragraph in doc.paragraphs
                        )
                    })
                except Exception:
                    pass
            
            return preview_info
            
        except Exception as e:
            logger.error(f"获取文档预览失败: {e}")
            return None
    
    def list_exported_documents(self) -> List[Dict[str, Any]]:
        """列出已导出的文档"""
        try:
            documents = []
            for filename in os.listdir(self.output_dir):
                if filename.startswith('report_'):
                    file_path = os.path.join(self.output_dir, filename)
                    preview_info = self.get_document_preview(file_path)
                    if preview_info:
                        documents.append(preview_info)
            
            return sorted(documents, key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            logger.error(f"列出文档失败: {e}")
            return []
    
    def cleanup_old_documents(self, days_old: int = 30) -> int:
        """清理旧文档"""
        try:
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 3600)
            
            removed_count = 0
            for filename in os.listdir(self.output_dir):
                file_path = os.path.join(self.output_dir, filename)
                if os.path.isfile(file_path) and os.path.getctime(file_path) < cutoff_time:
                    os.remove(file_path)
                    removed_count += 1
            
            logger.info(f"清理了 {removed_count} 个旧文档文件")
            return removed_count
            
        except Exception as e:
            logger.error(f"清理文档文件失败: {e}")
            return 0
    
    async def batch_export_templates(
        self,
        template_ids: List[str],
        base_data: Dict[str, Any],
        config: Optional[DocumentConfig] = None
    ) -> List[DocumentExportResult]:
        """批量导出模板"""
        logger.info(f"开始批量导出 {len(template_ids)} 个模板")
        
        export_tasks = []
        for template_id in template_ids:
            task = self.export_report_document(
                template_id=template_id,
                placeholder_data=base_data.get('placeholder_data', {}),
                etl_data=base_data.get('etl_data', {}),
                chart_data=base_data.get('chart_data', {}),
                config=config
            )
            export_tasks.append(task)
        
        results = await asyncio.gather(*export_tasks, return_exceptions=True)
        
        export_results = []
        for template_id, result in zip(template_ids, results):
            if isinstance(result, Exception):
                export_results.append(DocumentExportResult(
                    success=False,
                    error=str(result)
                ))
            else:
                export_results.append(result)
        
        successful_exports = len([r for r in export_results if r.success])
        logger.info(f"批量导出完成: 成功={successful_exports}, 总计={len(export_results)}")
        
        return export_results


# 工厂函数
def create_word_export_service(user_id: str) -> WordExportService:
    """创建Word导出服务实例"""
    return WordExportService(user_id=user_id)