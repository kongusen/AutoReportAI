"""
文档组装工具

负责将数据和模板组装成最终的报告文档
"""

import logging
from typing import Dict, Any
from .base import Tool

logger = logging.getLogger(__name__)


class DocAssemblerTool(Tool):
    """文档组装工具"""

    def __init__(self, container=None, use_storage=False):
        super().__init__()
        self.name = "doc_assembler"
        self.description = "组装数据和模板生成最终报告文档"
        self.container = container
        self.use_storage = use_storage

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行文档组装，集成智能占位符处理器

        Args:
            input_data: 包含模板路径、上下文数据、ETL结果等信息

        Returns:
            文档组装结果
        """
        try:
            template_path = input_data.get("template_path")
            output_path = input_data.get("output_path")
            etl_results = input_data.get("etl_results", {})

            if not template_path or not output_path:
                raise ValueError("缺少必要的模板路径或输出路径")

            logger.info(f"开始文档组装: {template_path} -> {output_path}")

            # 第1步: 数据标准化组装
            assembled_data = await self._assemble_placeholder_data(etl_results)

            # 第2步: 使用智能处理器生成文本
            intelligent_texts = await self._process_with_intelligent_agent(
                assembled_data, template_path
            )

            # 第3步: 执行Word文档组装
            if self.use_storage:
                # 直接存储到MinIO模式
                storage_result = await self._assemble_and_store_document(
                    template_path, output_path, intelligent_texts, input_data
                )
                return {
                    "success": True,
                    "result": {
                        "storage_path": storage_result.get("storage_path"),
                        "backend": storage_result.get("backend"),
                        "placeholders_processed": len(intelligent_texts),
                        "output_path": storage_result.get("storage_path")
                    },
                    "output_path": storage_result.get("storage_path"),
                    "storage_info": storage_result,
                    "status": "completed"
                }
            else:
                # 传统本地文件模式
                document_path = await self._assemble_word_document(
                    template_path, output_path, intelligent_texts
                )
                return {
                    "success": True,
                    "result": {
                        "document_path": document_path,
                        "placeholders_processed": len(intelligent_texts),
                        "output_path": document_path
                    },
                    "output_path": document_path,
                    "status": "completed"
                }

        except Exception as e:
            logger.error(f"文档组装失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }

    async def _assemble_placeholder_data(self, etl_results: Dict[str, Any]) -> Dict[str, Any]:
        """数据标准化组装"""
        assembled_data = {}

        for placeholder_name, etl_result in etl_results.items():
            if etl_result.get("success", False):
                # 提取实际数据值
                raw_data = etl_result.get("data", [])
                if raw_data and len(raw_data) > 0:
                    # 简化：取第一行第一个值
                    first_row = raw_data[0]
                    data_value = list(first_row.values())[0] if first_row else None
                else:
                    data_value = None

                assembled_data[placeholder_name] = data_value
            else:
                assembled_data[placeholder_name] = None

        return assembled_data

    async def _process_with_intelligent_agent(self,
                                            assembled_data: Dict[str, Any],
                                            template_path: str) -> Dict[str, str]:
        """使用智能处理器生成文本"""

        try:
            # 导入并创建智能处理器
            from ..placeholder_intelligent_processor import PlaceholderIntelligentProcessor

            processor = PlaceholderIntelligentProcessor(self.container)

            # 提取模板上下文（如果需要）
            template_context = {}
            try:
                # 这里可以添加从Word文档提取上下文的逻辑
                # template_context = processor.extract_template_context(doc_content)
                pass
            except Exception as e:
                logger.warning(f"提取模板上下文失败: {e}")

            # 处理占位符数据
            intelligent_texts = await processor.process_placeholder_data(
                placeholder_data=assembled_data,
                template_context=template_context
            )

            logger.info(f"智能处理完成，生成了 {len(intelligent_texts)} 个智能文本")
            return intelligent_texts

        except Exception as e:
            logger.error(f"智能处理失败: {e}")
            # 降级到简单处理
            return {name: str(value) if value is not None else "暂无数据"
                   for name, value in assembled_data.items()}

    async def _assemble_word_document(self,
                                    template_path: str,
                                    output_path: str,
                                    intelligent_texts: Dict[str, str]) -> str:
        """执行Word文档组装"""

        try:
            # 导入Word模板服务
            from ...document.word_template_service import WordTemplateService
            from ...document.word_template_service import DOCX_AVAILABLE

            if not DOCX_AVAILABLE:
                raise RuntimeError("python-docx 未安装，无法处理Word文档")

            # 创建Word模板服务
            word_service = WordTemplateService()

            # 调用Word文档处理
            result = await word_service.process_template_with_data(
                template_path=template_path,
                output_path=output_path,
                placeholder_data=intelligent_texts
            )

            if result.get("success", False):
                return result.get("output_path", output_path)
            else:
                raise RuntimeError(f"Word文档处理失败: {result.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Word文档组装失败: {e}")
            # 降级方案：复制模板文件
            import shutil
            shutil.copy2(template_path, output_path)
            logger.warning(f"已复制原始模板到输出路径: {output_path}")
            return output_path

    async def _assemble_and_store_document(self,
                                         template_path: str,
                                         output_path: str,
                                         intelligent_texts: Dict[str, str],
                                         input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        组装Word文档并直接存储到MinIO

        Args:
            template_path: 模板文件路径
            output_path: 原始输出路径（用于生成存储键）
            intelligent_texts: 智能处理后的文本数据
            input_data: 输入数据，可能包含任务信息

        Returns:
            存储结果信息
        """
        import tempfile
        import os
        from io import BytesIO
        from datetime import datetime

        try:
            # 导入存储服务
            from ...storage.hybrid_storage_service import HybridStorageService

            # 创建存储服务
            storage = HybridStorageService()

            # 1. 先在内存中生成Word文档
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
                temp_path = tmp_file.name

            try:
                # 使用现有的Word文档组装逻辑
                document_path = await self._assemble_word_document(
                    template_path, temp_path, intelligent_texts
                )

                # 2. 读取生成的文档到内存
                with open(document_path, 'rb') as f:
                    document_bytes = f.read()

                # 3. 生成存储对象键
                storage_key = self._generate_storage_key(output_path, input_data)

                logger.info(f"开始上传文档到存储: {storage_key}")

                # 4. 上传到存储服务
                upload_result = storage.upload_with_key(
                    object_name=storage_key,
                    file_data=BytesIO(document_bytes),
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

                logger.info(f"✅ 文档已成功存储: {storage_key}")

                return {
                    "success": True,
                    "storage_path": upload_result.get("file_path", storage_key),
                    "backend": upload_result.get("backend", "unknown"),
                    "size": upload_result.get("size", len(document_bytes)),
                    "uploaded_at": upload_result.get("uploaded_at"),
                    "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "original_output_path": output_path
                }

            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"文档存储失败: {e}")

            # 降级方案：使用传统方式生成本地文件
            logger.warning("降级到本地文件生成模式")
            document_path = await self._assemble_word_document(
                template_path, output_path, intelligent_texts
            )

            return {
                "success": False,
                "error": str(e),
                "fallback_path": document_path,
                "storage_path": None,
                "backend": "local_fallback"
            }

    def _generate_storage_key(self, output_path: str, input_data: Dict[str, Any]) -> str:
        """
        生成MinIO存储对象键

        Args:
            output_path: 原始输出路径
            input_data: 输入数据

        Returns:
            存储对象键
        """
        from datetime import datetime
        import re
        import os

        # 获取任务信息（如果有）
        task_id = input_data.get("task_id", "unknown")
        task_name = input_data.get("task_name", f"task_{task_id}")
        tenant_id = input_data.get("tenant_id", "default")

        # 生成时间戳
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

        # 清理任务名称，生成URL安全的slug
        slug = re.sub(r'[^\w\-]+', '-', str(task_name)).strip('-')[:50]

        # 获取文件扩展名
        file_extension = os.path.splitext(output_path)[1] or '.docx'

        # 构建存储键: reports/{tenant_id}/{task_slug}/report_{timestamp}.docx
        storage_key = f"reports/{tenant_id}/{slug}/report_{timestamp}{file_extension}"

        logger.debug(f"生成存储键: {storage_key}")
        return storage_key


# 为了兼容性，也提供 DocumentAssemblerTool 别名
DocumentAssemblerTool = DocAssemblerTool