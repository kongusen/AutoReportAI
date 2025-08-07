import base64
import io
import logging
import re
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, Optional

import docx
from docx.shared import Inches

from app.services.storage.file_storage_service import file_storage_service

logger = logging.getLogger(__name__)


class WordGeneratorService:
    # Regex to find <img ...> tags with base64 data
    IMG_REGEX = re.compile(r'<img src="data:image/png;base64,([^"]+)">')

    def generate_report(
        self,
        content: str,
        title: str = "自动生成报告",
        format: str = "docx"
    ) -> str:
        """
        生成报告文件并存储到MinIO或本地
        
        Args:
            content: 报告内容
            title: 报告标题  
            format: 文件格式 (docx)
            
        Returns:
            存储后的文件路径
        """
        try:
            # 创建Word文档
            doc = docx.Document()
            
            # 添加标题
            doc.add_heading(title, 0)
            
            # 添加生成时间
            doc.add_paragraph(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            doc.add_paragraph("")  # 空行
            
            # 处理内容
            self._process_content(doc, content)
            
            # 将文档保存到内存
            doc_buffer = BytesIO()
            doc.save(doc_buffer)
            doc_buffer.seek(0)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{title}_{timestamp}.docx"
            
            # 上传到存储服务
            file_info = file_storage_service.upload_file(
                file_data=doc_buffer,
                original_filename=filename,
                file_type="report",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
            logger.info(f"报告生成成功: {file_info['file_path']}")
            return file_info['file_path']
            
        except Exception as e:
            logger.error(f"报告生成失败: {str(e)}")
            raise

    def generate_report_from_content(self, composed_content: str, output_path: str):
        """
        Generates a .docx report from a string containing the fully composed content.
        This content can include text and special <img> tags for base64 images.
        
        保留原有方法以保持向后兼容
        """
        doc = docx.Document()

        # Split the content into paragraphs based on newlines
        paragraphs = composed_content.split("\n")

        for para_text in paragraphs:
            self._process_paragraph(doc, para_text)

        doc.save(output_path)

    def _process_content(self, doc, content: str):
        """处理报告内容，支持文本和图像"""
        # 分段处理
        paragraphs = content.split("\n")
        
        for para_text in paragraphs:
            self._process_paragraph(doc, para_text)

    def _process_paragraph(self, doc, para_text: str):
        """
        Processes a single paragraph of text, adding text and images to the document.
        """
        # Find all image tags in the paragraph
        img_matches = list(self.IMG_REGEX.finditer(para_text))

        if not img_matches:
            # If no images, add the whole paragraph as text
            doc.add_paragraph(para_text)
            return

        current_pos = 0
        for match in img_matches:
            # Add text before the image
            start, end = match.span()
            if start > current_pos:
                doc.add_paragraph(para_text[current_pos:start])

            # Add the image
            base64_data = match.group(1)
            try:
                image_stream = io.BytesIO(base64.b64decode(base64_data))
                doc.add_picture(image_stream, width=Inches(6.0))
            except Exception as e:
                print(f"Error decoding or adding picture: {e}")
                # Add a placeholder text on error
                doc.add_paragraph(f"[Image could not be loaded: {e}]")

            current_pos = end

        # Add any remaining text after the last image
        if current_pos < len(para_text):
            doc.add_paragraph(para_text[current_pos:])


word_generator_service = WordGeneratorService()
