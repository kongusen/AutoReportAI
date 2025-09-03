"""
模板处理器服务

负责智能处理和优化模板内容
"""

import logging
import re
from typing import Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PlaceholderInfo:
    """占位符信息"""
    text: str
    type: str
    requires_data: bool
    position: int


@dataclass
class TemplateProcessingResult:
    """模板处理结果"""
    processed_content: str
    placeholders_found: List[PlaceholderInfo]
    placeholder_count: int
    processing_score: float
    optimization_applied: bool
    warnings: List[str]


class TemplateProcessorService:
    """模板处理器服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 占位符匹配模式 (按优先级排序，避免重复匹配)
        self.placeholder_patterns = {
            'double_brace': r'\{\{([^}]+)\}\}',  # {{占位符}}
            'dollar_brace': r'\$\{([^}]+)\}',   # ${占位符}
            'percent': r'%([^%]+)%',            # %占位符%
            # 注释掉单括号避免与双括号冲突
            # 'single_brace': r'\{([^}]+)\}',     # {占位符}
        }
        
        # 优化规则
        self.optimization_rules = [
            'remove_duplicate_spaces',
            'normalize_line_breaks', 
            'optimize_placeholder_spacing',
            'validate_placeholder_syntax'
        ]
    
    async def process_template(
        self, 
        template_content: str, 
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        处理模板内容
        
        Args:
            template_content: 模板内容
            context: 上下文信息
            
        Returns:
            处理结果字典
        """
        try:
            self.logger.info(f"开始处理模板，长度: {len(template_content)}")
            
            # 1. 检测占位符
            placeholders = await self._detect_placeholders(template_content)
            
            # 2. 应用优化规则
            processed_content, optimization_applied = await self._apply_optimizations(
                template_content, context
            )
            
            # 3. 验证处理结果
            warnings = await self._validate_template(processed_content, placeholders)
            
            # 4. 计算处理分数
            processing_score = self._calculate_processing_score(
                template_content, processed_content, placeholders
            )
            
            result = {
                "processed_content": processed_content,
                "placeholders_found": [
                    {
                        "text": ph.text,
                        "type": ph.type,
                        "requires_data": ph.requires_data,
                        "position": ph.position
                    } for ph in placeholders
                ],
                "placeholder_count": len(placeholders),
                "processing_score": processing_score,
                "optimization_applied": optimization_applied,
                "warnings": warnings,
                "metadata": {
                    "original_length": len(template_content),
                    "processed_length": len(processed_content),
                    "context_used": bool(context),
                    "processing_time": "calculated"
                }
            }
            
            self.logger.info(f"模板处理完成: 发现{len(placeholders)}个占位符，分数: {processing_score}")
            return result
            
        except Exception as e:
            self.logger.error(f"模板处理失败: {e}")
            raise ValueError(f"模板处理失败: {str(e)}")
    
    async def _detect_placeholders(self, content: str) -> List[PlaceholderInfo]:
        """检测模板中的占位符"""
        placeholders = []
        
        for pattern_name, pattern in self.placeholder_patterns.items():
            matches = list(re.finditer(pattern, content))
            
            for match in matches:
                placeholder_text = match.group(1).strip()
                
                # 分析占位符类型
                placeholder_type = self._classify_placeholder(placeholder_text)
                
                placeholder_info = PlaceholderInfo(
                    text=placeholder_text,
                    type=placeholder_type,
                    requires_data=self._requires_data_lookup(placeholder_text),
                    position=match.start()
                )
                
                placeholders.append(placeholder_info)
        
        # 按位置排序
        placeholders.sort(key=lambda x: x.position)
        return placeholders
    
    def _classify_placeholder(self, placeholder_text: str) -> str:
        """分类占位符类型"""
        text_lower = placeholder_text.lower()
        
        # 统计类型关键词
        if any(keyword in text_lower for keyword in ['统计', '总计', '求和', 'sum', 'count']):
            return 'statistical'
        elif any(keyword in text_lower for keyword in ['趋势', '变化', '增长', 'trend']):
            return 'trend'
        elif any(keyword in text_lower for keyword in ['图表', '图', 'chart', 'graph']):
            return 'chart'
        elif any(keyword in text_lower for keyword in ['列表', '明细', 'list', 'detail']):
            return 'list'
        elif any(keyword in text_lower for keyword in ['时间', '日期', 'time', 'date']):
            return 'temporal'
        else:
            return 'dynamic'
    
    def _requires_data_lookup(self, placeholder_text: str) -> bool:
        """判断占位符是否需要数据查询"""
        # 简单的静态文本不需要数据查询
        static_keywords = ['公司名称', '报告标题', '当前日期', '页码']
        return not any(keyword in placeholder_text for keyword in static_keywords)
    
    async def _apply_optimizations(
        self, 
        content: str, 
        context: Dict[str, Any] = None
    ) -> tuple[str, bool]:
        """应用优化规则"""
        optimized_content = content
        optimization_applied = False
        
        # 1. 移除多余空格
        original_content = optimized_content
        optimized_content = re.sub(r'\s+', ' ', optimized_content)
        if optimized_content != original_content:
            optimization_applied = True
        
        # 2. 规范化换行符
        optimized_content = optimized_content.replace('\r\n', '\n').replace('\r', '\n')
        
        # 3. 优化占位符周围的空格
        optimized_content = re.sub(r'\s*\{\{\s*', '{{', optimized_content)
        optimized_content = re.sub(r'\s*\}\}\s*', '}}', optimized_content)
        
        # 4. 基于上下文的优化
        if context:
            # 如果有数据源信息，可以优化占位符
            if 'data_sources' in context:
                optimization_applied = True
                # 这里可以添加基于数据源的优化逻辑
        
        return optimized_content, optimization_applied
    
    async def _validate_template(
        self, 
        content: str, 
        placeholders: List[PlaceholderInfo]
    ) -> List[str]:
        """验证模板内容"""
        warnings = []
        
        # 1. 检查未闭合的占位符
        open_braces = content.count('{{')
        close_braces = content.count('}}')
        if open_braces != close_braces:
            warnings.append(f"占位符括号不匹配: {{ 数量({open_braces}) != }} 数量({close_braces})")
        
        # 2. 检查空占位符
        empty_placeholders = [ph for ph in placeholders if not ph.text.strip()]
        if empty_placeholders:
            warnings.append(f"发现{len(empty_placeholders)}个空占位符")
        
        # 3. 检查重复占位符
        placeholder_texts = [ph.text for ph in placeholders]
        duplicates = set([x for x in placeholder_texts if placeholder_texts.count(x) > 1])
        if duplicates:
            warnings.append(f"发现重复占位符: {list(duplicates)}")
        
        # 4. 检查模板长度
        if len(content) > 50000:  # 50KB
            warnings.append("模板内容过长，可能影响处理性能")
        
        return warnings
    
    def _calculate_processing_score(
        self, 
        original: str, 
        processed: str, 
        placeholders: List[PlaceholderInfo]
    ) -> float:
        """计算处理质量分数"""
        score = 1.0
        
        # 基于占位符质量调整分数
        if placeholders:
            valid_placeholders = [ph for ph in placeholders if ph.text.strip()]
            placeholder_quality = len(valid_placeholders) / len(placeholders)
            score *= placeholder_quality
        
        # 基于内容优化程度调整分数
        if len(processed) < len(original):
            compression_ratio = len(processed) / len(original)
            if compression_ratio > 0.9:  # 轻微优化
                score *= 1.05
            elif compression_ratio > 0.8:  # 中等优化
                score *= 1.1
        
        # 确保分数在合理范围内
        return min(max(score, 0.0), 1.0)


# 全局实例
template_processor_service = TemplateProcessorService()