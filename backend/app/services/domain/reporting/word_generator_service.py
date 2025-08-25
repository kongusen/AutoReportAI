import base64
import io
import logging
import re
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, Optional

import docx
from docx.shared import Inches

from app.services.infrastructure.storage.file_storage_service import file_storage_service

logger = logging.getLogger(__name__)


class WordGeneratorService:
    # Regex to find <img ...> tags with base64 data
    IMG_REGEX = re.compile(r'<img src="data:image/png;base64,([^"]+)">')

    def generate_report_from_template(
        self,
        template_content: str,
        placeholder_values: Dict[str, Any],
        title: str = "自动生成报告",
        format: str = "docx"
    ) -> str:
        """
        基于模板生成报告文件
        
        Args:
            template_content: 模板内容 (hex编码的二进制数据或文本)
            placeholder_values: 占位符值字典
            title: 报告标题
            format: 文件格式 (docx)
            
        Returns:
            存储后的文件路径
        """
        try:
            # 1. 处理模板内容
            if self._is_binary_template(template_content):
                # 处理二进制模板 (hex编码)
                return self._generate_from_binary_template(
                    template_content, placeholder_values, title
                )
            else:
                # 处理文本模板
                return self._generate_from_text_template(
                    template_content, placeholder_values, title
                )
                
        except Exception as e:
            logger.error(f"基于模板的报告生成失败: {str(e)}")
            # 降级到普通生成
            processed_content = self._replace_placeholders_in_text(
                template_content, placeholder_values
            )
            return self.generate_report(processed_content, title, format)

    def _is_binary_template(self, content: str) -> bool:
        """判断是否为二进制模板内容"""
        if not content:
            return False
        # 检查是否为hex编码
        content_clean = content.replace(' ', '').replace('\n', '')
        return len(content_clean) > 100 and all(c in '0123456789ABCDEFabcdef' for c in content_clean)

    def _generate_from_binary_template(
        self,
        template_content: str,
        placeholder_values: Dict[str, Any],
        title: str
    ) -> str:
        """从二进制模板生成报告"""
        try:
            # 解析hex编码的二进制数据
            binary_data = bytes.fromhex(template_content.replace(' ', '').replace('\n', ''))
            
            # 加载为Word文档
            template_buffer = BytesIO(binary_data)
            doc = docx.Document(template_buffer)
            
            # 替换占位符
            self._replace_placeholders_in_doc(doc, placeholder_values)
            
            # 保存到内存
            doc_buffer = BytesIO()
            doc.save(doc_buffer)
            doc_buffer.seek(0)
            
            # 生成文件名并上传 (保持DOCX格式)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{title}_{timestamp}.docx"
            
            file_info = file_storage_service.upload_file(
                file_data=doc_buffer,
                original_filename=filename,
                file_type="report",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
            logger.info(f"基于二进制模板的报告生成成功: {file_info['file_path']}")
            return file_info['file_path']
            
        except Exception as e:
            logger.warning(f"二进制模板处理失败，降级到文本处理: {e}")
            raise

    def _generate_from_text_template(
        self,
        template_content: str,
        placeholder_values: Dict[str, Any],
        title: str
    ) -> str:
        """从文本模板生成报告"""
        # 替换占位符
        processed_content = self._replace_placeholders_in_text(template_content, placeholder_values)
        
        # 使用普通生成方法
        return self.generate_report(processed_content, title)

    def _replace_placeholders_in_doc(self, doc, placeholder_values: Dict[str, Any]):
        """在Word文档中替换占位符"""
        logger.error("🔥🔥🔥 CLAUDE修复的占位符替换代码正在运行! 🔥🔥🔥")
        logger.info(f"开始占位符替换 - 输入 {len(placeholder_values)} 个占位符")
        
        # 处理占位符值，提取实际值
        processed_values = {}
        logger.info("处理占位符值详情:")
        for key, value_info in placeholder_values.items():
            logger.info(f"处理占位符: {key}, 原始值: {value_info}")
            
            if isinstance(value_info, dict) and "value" in value_info:
                extracted_value = self._extract_value_from_result(value_info["value"])
                processed_values[key] = str(extracted_value) if extracted_value is not None else ""
            else:
                extracted_value = self._extract_value_from_result(value_info)
                processed_values[key] = str(extracted_value) if extracted_value is not None else ""
            
            logger.info(f"提取后的值: {key} = '{processed_values[key]}'")
            
            # 如果值为空或者是 "None"，为常见占位符提供默认值
            if not processed_values[key] or processed_values[key] in ["None", "null", ""]:
                default_value = self._get_default_placeholder_value(key)
                if default_value:
                    processed_values[key] = default_value
                    logger.warning(f"⚠️  使用默认值: {key} = {default_value}")
                else:
                    logger.error(f"❌ 占位符无法处理: {key} (无默认值)")
        
        # 显示处理后的占位符值（仅显示前5个）
        logger.info(f"处理后的占位符值（显示前5个）:")
        count = 0
        for key, value in processed_values.items():
            if count >= 5:
                break
            logger.info(f"  {key} = '{value}' (长度: {len(value)})")
            count += 1
        
        # 替换段落中的占位符
        replacements_made = 0
        for paragraph in doc.paragraphs:
            original_text = paragraph.text
            if original_text.strip() and "{{" in original_text:  # 只处理包含占位符的非空段落
                logger.debug(f"检查段落文本: {original_text}")
                paragraph_changed = False
                for key, value in processed_values.items():
                    # 支持多种占位符格式，包括中文冒号分隔符
                    patterns = [
                        f"{{{{{key}}}}}",    # {{key}}
                        f"{{{key}}}",        # {key}
                    ]
                        
                    for pattern in patterns:
                        if pattern in paragraph.text:
                            paragraph.text = paragraph.text.replace(pattern, value)
                            replacements_made += 1
                            logger.info(f"段落替换成功: {pattern} -> {value}")
                            paragraph_changed = True
                            break  # 找到一个匹配就跳出，避免重复替换
                
                if paragraph_changed:
                    logger.debug(f"段落替换后: {paragraph.text}")
        
        logger.info(f"段落中完成 {replacements_made} 个占位符替换")
        
        # 替换表格中的占位符
        table_replacements = 0
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip() and "{{" in cell.text:  # 只处理包含占位符的非空单元格
                        logger.debug(f"检查表格单元格文本: {cell.text}")
                        cell_changed = False
                        for key, value in processed_values.items():
                            # 支持多种占位符格式，包括中文冒号分隔符
                            patterns = [
                                f"{{{{{key}}}}}",    # {{key}}
                                f"{{{key}}}",        # {key}
                            ]
                                
                            for pattern in patterns:
                                if pattern in cell.text:
                                    cell.text = cell.text.replace(pattern, value)
                                    table_replacements += 1
                                    logger.info(f"表格替换成功: {pattern} -> {value}")
                                    cell_changed = True
                                    break  # 找到一个匹配就跳出，避免重复替换
                        
                        if cell_changed:
                            logger.debug(f"表格单元格替换后: {cell.text}")
        
        logger.info(f"表格中完成 {table_replacements} 个占位符替换")
        total_replacements = replacements_made + table_replacements
        logger.info(f"总共完成 {total_replacements} 个占位符替换")

    def _get_default_placeholder_value(self, key: str) -> str:
        """为常见占位符提供默认值"""
        from datetime import datetime
        current_time = datetime.now()
        
        # 时间相关占位符
        if "报告年份" in key:
            return str(current_time.year)
        elif "统计开始日期" in key:
            return f"{current_time.year}-{current_time.month:02d}-01"
        elif "统计结束日期" in key:
            next_month = current_time.month + 1 if current_time.month < 12 else 1
            next_year = current_time.year if current_time.month < 12 else current_time.year + 1
            return f"{next_year}-{next_month:02d}-01"
        elif "地区名称" in key:
            return "云南省"  # 默认地区
        
        # 数量相关占位符
        elif "投诉件数" in key or "件数" in key:
            return "0"
        elif "占比" in key or "百分比" in key:
            return "0.0"
        elif "时长" in key:
            return "0"
        
        return None

    def _extract_value_from_result(self, value: Any) -> Any:
        """从查询结果中提取实际数值"""
        try:
            # 如果是None或简单类型，直接返回
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            
            # 如果是DorisQueryResult对象或类似结构
            if hasattr(value, 'data') and hasattr(value, 'execution_time'):
                return self._extract_value_from_result(value.data)
            
            # 如果是pandas DataFrame
            if hasattr(value, 'iloc') and hasattr(value, '__len__'):
                try:
                    if len(value) > 0 and hasattr(value, 'empty') and not value.empty:
                        return value.iloc[0, 0]
                    return 0
                except Exception:
                    # 如果DataFrame访问失败，尝试其他方法
                    pass
            
            # 如果是包含data字段的字典
            if isinstance(value, dict):
                # 首先检查是否有嵌套的data结构
                if 'data' in value:
                    nested_result = self._extract_value_from_result(value['data'])
                    if nested_result != value['data']:  # 避免无限递归
                        return nested_result
                
                # 尝试从常见字段中获取数值
                for key in ['count', 'total', 'sum', 'avg', 'value', 'result', 'amount']:
                    if key in value:
                        extracted = self._extract_value_from_result(value[key])
                        if extracted != value[key]:  # 避免无限递归
                            return extracted
                
                # 如果字典只有一个键值对，返回值
                if len(value) == 1:
                    return next(iter(value.values()))
                    
                # 如果没有找到特定字段，返回第一个非None值
                for v in value.values():
                    if v is not None and not isinstance(v, dict):
                        return self._extract_value_from_result(v)
                
            # 如果是列表或元组
            if isinstance(value, (list, tuple)) and value:
                first_item = value[0]
                if isinstance(first_item, dict):
                    # 如果第一个元素是字典，尝试获取其值
                    return self._extract_value_from_result(first_item)
                else:
                    # 如果是简单值，直接返回
                    return first_item
                
            # 如果是其他对象类型，尝试转换为字符串
            if hasattr(value, '__str__') and not str(value).startswith('<'):
                return str(value)
                
            # 最后返回"无数据"而不是对象引用
            return "无数据"
            
        except Exception as e:
            logger.warning(f"提取查询结果数值失败: {e}, 值类型: {type(value)}")
            # 发生异常时返回"无数据"而不是原值
            return "无数据"

    def _replace_placeholders_in_text(self, content: str, placeholder_values: Dict[str, Any]) -> str:
        """在文本中替换占位符"""
        processed_content = content
        
        # 处理占位符值，提取实际值
        for key, value_info in placeholder_values.items():
            if isinstance(value_info, dict) and "value" in value_info:
                extracted_value = self._extract_value_from_result(value_info["value"])
                value = str(extracted_value)
            else:
                extracted_value = self._extract_value_from_result(value_info)
                value = str(extracted_value)
                
            # 支持多种占位符格式
            patterns = [
                f"{{{{{key}}}}}",  # {{key}}
                f"{{{key}}}",      # {key}
            ]
            for pattern in patterns:
                processed_content = processed_content.replace(pattern, value)
        return processed_content

    def _get_file_format_info(self, format_type: str) -> Dict[str, str]:
        """获取文件格式信息"""
        format_map = {
            'docx': {
                'extension': '.docx',
                'content_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            },
            'xlsx': {
                'extension': '.xlsx', 
                'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            },
            'txt': {
                'extension': '.txt',
                'content_type': 'text/plain'
            },
            'html': {
                'extension': '.html',
                'content_type': 'text/html'
            }
        }
        return format_map.get(format_type, format_map['docx'])

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
            
            # 获取格式信息并生成文件名
            format_info = self._get_file_format_info(format)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{title}_{timestamp}{format_info['extension']}"
            
            # 上传到存储服务
            file_info = file_storage_service.upload_file(
                file_data=doc_buffer,
                original_filename=filename,
                file_type="report",
                content_type=format_info['content_type']
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
