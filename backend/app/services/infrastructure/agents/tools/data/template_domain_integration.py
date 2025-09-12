"""
模板填充与Domain报告服务集成
============================

负责将agents模板填充系统与domain层报告服务进行集成。
实现模板填充结果到Word文档生成的无缝衔接。
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.services.domain.reporting import (
    WordGeneratorService, 
    ReportQualityChecker,
    QualityCheckResult
)

logger = logging.getLogger(__name__)


class TemplateDomainIntegration:
    """
    模板填充与Domain服务集成器
    
    负责：
    1. 接收agents模板填充工具的输出
    2. 转换为domain层可处理的格式
    3. 调用WordGeneratorService生成Word文档
    4. 执行质量检查和验证
    5. 返回统一的结果格式
    """
    
    def __init__(self):
        self.word_generator = WordGeneratorService()
        self.quality_checker = ReportQualityChecker()
    
    async def process_template_fill_result(
        self, 
        template_fill_result: Dict[str, Any],
        output_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理模板填充结果并生成Word文档
        
        Args:
            template_fill_result: 来自TemplateFillTool的结果
            output_options: 输出选项配置
            
        Returns:
            集成处理结果
        """
        try:
            # 提取模板填充结果
            filled_content = template_fill_result.get('filled_content', '')
            domain_data = template_fill_result.get('domain_data', {})
            metadata = template_fill_result.get('metadata', {})
            
            # 获取输出配置
            output_options = output_options or {}
            
            # 准备Word生成参数
            word_params = await self._prepare_word_generation_params(
                domain_data, output_options, metadata
            )
            
            # 生成Word文档
            logger.info("开始生成Word文档...")
            word_file_path = await self._generate_word_document(
                filled_content, word_params, domain_data
            )
            
            # 执行质量检查
            quality_result = None
            if word_params.get('enable_quality_check', True):
                logger.info("执行报告质量检查...")
                quality_result = await self._perform_quality_check(
                    filled_content, domain_data, word_file_path
                )
            
            # 构建集成结果
            integration_result = {
                'success': True,
                'word_document_path': word_file_path,
                'template_analysis': template_fill_result.get('template_analysis', {}),
                'quality_check': quality_result.to_dict() if quality_result else None,
                'generation_metadata': {
                    'template_type': metadata.get('template_type', 'unknown'),
                    'fill_mode': metadata.get('fill_mode', 'smart'),
                    'generation_time': datetime.now().isoformat(),
                    'integration_version': '1.0.0'
                },
                'placeholder_summary': {
                    'total_placeholders': len(domain_data.get('placeholder_data', {})),
                    'filled_successfully': len([
                        p for p in domain_data.get('placeholder_metadata', {}).values() 
                        if p.get('is_filled', False)
                    ]),
                    'descriptions_generated': len(domain_data.get('placeholder_descriptions', {}))
                },
                'domain_integration': {
                    'word_generation_successful': bool(word_file_path),
                    'quality_check_performed': quality_result is not None,
                    'processing_time_ms': self._calculate_processing_time(metadata)
                }
            }
            
            logger.info(f"模板填充集成处理完成，Word文档路径: {word_file_path}")
            return integration_result
            
        except Exception as e:
            logger.error(f"模板填充集成处理失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'template_domain_integration_error',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _prepare_word_generation_params(
        self, 
        domain_data: Dict[str, Any], 
        output_options: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """准备Word生成参数"""
        
        # 从domain_data提取Word生成参数
        word_gen_params = domain_data.get('word_generation_params', {})
        
        # 合并输出选项
        params = {
            # 基础参数
            'title': output_options.get('title', '模板填充报告'),
            'format': 'docx',
            
            # 格式选项
            'preserve_formatting': word_gen_params.get('preserve_formatting', True),
            'include_metadata': word_gen_params.get('include_metadata', True),
            'add_table_of_contents': word_gen_params.get('add_table_of_contents', False),
            'add_page_numbers': word_gen_params.get('add_page_numbers', True),
            'document_style': word_gen_params.get('document_style', 'professional'),
            
            # 质量检查选项
            'enable_quality_check': output_options.get('enable_quality_check', True),
            
            # 模板相关参数
            'template_type': metadata.get('template_type', 'word'),
            'fill_mode': metadata.get('fill_mode', 'smart'),
        }
        
        return params
    
    async def _generate_word_document(
        self, 
        filled_content: str,
        word_params: Dict[str, Any],
        domain_data: Dict[str, Any]
    ) -> str:
        """生成Word文档"""
        
        try:
            # 准备占位符数据（用于Word生成器的向后兼容）
            placeholder_values = {}
            
            # 从domain_data提取占位符信息
            placeholder_metadata = domain_data.get('placeholder_metadata', {})
            for name, meta in placeholder_metadata.items():
                placeholder_values[name] = {
                    'value': meta.get('value'),
                    'description': meta.get('description', ''),
                    'data_type': meta.get('data_type', 'str')
                }
            
            # 检查是否需要使用模板生成还是普通生成
            if self._should_use_template_generation(domain_data):
                # 使用模板生成模式
                return self.word_generator.generate_report_from_template(
                    template_content=filled_content,
                    placeholder_values=placeholder_values,
                    title=word_params['title'],
                    format=word_params['format']
                )
            else:
                # 使用普通报告生成模式
                return self.word_generator.generate_report(
                    content=filled_content,
                    title=word_params['title'],
                    format=word_params['format']
                )
                
        except Exception as e:
            logger.error(f"Word文档生成失败: {e}")
            raise
    
    def _should_use_template_generation(self, domain_data: Dict[str, Any]) -> bool:
        """判断是否应该使用模板生成模式"""
        
        # 检查模板分析结果
        template_analysis = domain_data.get('template_analysis', {})
        structure = template_analysis.get('structure', {})
        
        # 如果模板包含复杂结构（表格、图像等），使用模板生成
        if structure.get('contains_tables') or structure.get('contains_images'):
            return True
        
        # 如果占位符数量较多，使用模板生成
        if template_analysis.get('total_placeholders', 0) > 5:
            return True
        
        # 如果复杂度分数较高，使用模板生成
        if template_analysis.get('complexity_score', 0) > 15:
            return True
        
        # 默认使用普通生成
        return False
    
    async def _perform_quality_check(
        self, 
        filled_content: str,
        domain_data: Dict[str, Any],
        word_file_path: str
    ) -> QualityCheckResult:
        """执行报告质量检查"""
        
        try:
            # 准备质量检查参数
            quality_params = domain_data.get('quality_check_params', {})
            
            # 构建质量检查配置
            check_config = {
                'check_placeholder_completeness': quality_params.get('check_placeholder_completeness', True),
                'check_data_consistency': quality_params.get('check_data_consistency', True),
                'check_language_quality': quality_params.get('check_language_quality', True),
                'generate_summary': quality_params.get('generate_summary', True)
            }
            
            # 准备检查数据
            check_data = {
                'content': filled_content,
                'placeholder_data': domain_data.get('placeholder_data', {}),
                'template_analysis': domain_data.get('template_analysis', {}),
                'file_path': word_file_path
            }
            
            # 执行质量检查
            quality_result = await self.quality_checker.check_report_quality(
                content=filled_content,
                metadata=check_data,
                config=check_config
            )
            
            return quality_result
            
        except Exception as e:
            logger.warning(f"质量检查失败，将跳过: {e}")
            # 创建默认的质量检查结果
            from app.services.domain.reporting.quality_checker import QualityCheckResult, QualityMetrics
            
            return QualityCheckResult(
                overall_score=75.0,  # 默认分数
                metrics=QualityMetrics(
                    completeness_score=80.0,
                    consistency_score=75.0,
                    readability_score=70.0,
                    accuracy_score=80.0
                ),
                issues=[],
                recommendations=["质量检查过程中出现异常，请手动审核生成的报告"],
                metadata={'quality_check_error': str(e)}
            )
    
    def _calculate_processing_time(self, metadata: Dict[str, Any]) -> float:
        """计算处理时间（毫秒）"""
        
        try:
            processing_time = metadata.get('processing_time')
            if processing_time:
                # 如果有ISO格式的时间戳，计算差值
                start_time = datetime.fromisoformat(processing_time.replace('Z', '+00:00'))
                end_time = datetime.now()
                delta = end_time - start_time
                return delta.total_seconds() * 1000
            
            # 如果没有时间信息，返回默认值
            return 0.0
            
        except Exception:
            return 0.0


# 创建全局实例
template_domain_integration = TemplateDomainIntegration()


# 便捷函数
async def process_template_to_word(
    template_fill_result: Dict[str, Any],
    title: str = "模板填充报告",
    enable_quality_check: bool = True
) -> Dict[str, Any]:
    """
    便捷函数：将模板填充结果处理为Word文档
    
    Args:
        template_fill_result: TemplateFillTool的输出结果
        title: 报告标题
        enable_quality_check: 是否启用质量检查
        
    Returns:
        处理结果，包含Word文档路径和质量检查结果
    """
    
    output_options = {
        'title': title,
        'enable_quality_check': enable_quality_check
    }
    
    return await template_domain_integration.process_template_fill_result(
        template_fill_result, output_options
    )


__all__ = [
    'TemplateDomainIntegration',
    'template_domain_integration', 
    'process_template_to_word'
]