"""
Report Generation Domain Service

报告生成领域服务，包含纯业务逻辑
"""

import logging
import re
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """报告格式"""
    HTML = "html"
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    MARKDOWN = "markdown"
    JSON = "json"


class ReportStatus(Enum):
    """报告状态"""
    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentType(Enum):
    """内容类型"""
    TEXT = "text"
    TABLE = "table"
    CHART = "chart"
    IMAGE = "image"
    LIST = "list"
    SECTION = "section"


@dataclass
class ReportMetadata:
    """报告元数据"""
    title: str
    description: str = ""
    author: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0"
    tags: Set[str] = field(default_factory=set)
    language: str = "zh-CN"
    template_id: Optional[str] = None
    data_sources: List[str] = field(default_factory=list)


@dataclass
class ContentBlock:
    """内容块"""
    block_id: str
    content_type: ContentType
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    order: int = 0
    is_required: bool = True
    
    def render_as_text(self) -> str:
        """渲染为文本"""
        if self.content_type == ContentType.TEXT:
            return str(self.content)
        elif self.content_type == ContentType.TABLE:
            return self._render_table_as_text()
        elif self.content_type == ContentType.LIST:
            return self._render_list_as_text()
        elif self.content_type == ContentType.SECTION:
            return f"## {self.content.get('title', '')}\n{self.content.get('body', '')}"
        else:
            return f"[{self.content_type.value.upper()} CONTENT]"
    
    def _render_table_as_text(self) -> str:
        """渲染表格为文本"""
        if not isinstance(self.content, dict) or 'data' not in self.content:
            return "[TABLE]"
        
        data = self.content['data']
        if not data:
            return "[EMPTY TABLE]"
        
        # 简化的表格文本渲染
        headers = list(data[0].keys()) if data else []
        rows = []
        
        # 表头
        if headers:
            rows.append(" | ".join(headers))
            rows.append(" | ".join(["-" * len(h) for h in headers]))
        
        # 数据行
        for row in data[:10]:  # 最多显示10行
            row_data = [str(row.get(h, "")) for h in headers]
            rows.append(" | ".join(row_data))
        
        if len(data) > 10:
            rows.append(f"... ({len(data) - 10} more rows)")
        
        return "\n".join(rows)
    
    def _render_list_as_text(self) -> str:
        """渲染列表为文本"""
        if not isinstance(self.content, dict) or 'items' not in self.content:
            return "[LIST]"
        
        items = self.content['items']
        list_type = self.content.get('type', 'unordered')
        
        rendered_items = []
        for i, item in enumerate(items):
            if list_type == 'ordered':
                rendered_items.append(f"{i+1}. {item}")
            else:
                rendered_items.append(f"• {item}")
        
        return "\n".join(rendered_items)


@dataclass
class ReportSection:
    """报告段落"""
    section_id: str
    title: str
    content_blocks: List[ContentBlock] = field(default_factory=list)
    subsections: List['ReportSection'] = field(default_factory=list)
    order: int = 0
    is_optional: bool = False
    conditions: List[str] = field(default_factory=list)
    
    def add_content_block(self, block: ContentBlock):
        """添加内容块"""
        self.content_blocks.append(block)
        self.content_blocks.sort(key=lambda b: b.order)
    
    def get_total_content_length(self) -> int:
        """获取总内容长度"""
        total_length = 0
        
        for block in self.content_blocks:
            if block.content_type == ContentType.TEXT:
                total_length += len(str(block.content))
            elif block.content_type == ContentType.TABLE:
                if isinstance(block.content, dict) and 'data' in block.content:
                    total_length += len(block.content['data']) * 50  # 估算
        
        for subsection in self.subsections:
            total_length += subsection.get_total_content_length()
        
        return total_length


class ReportEntity:
    """报告实体"""
    
    def __init__(self, report_id: str, metadata: ReportMetadata):
        self.id = report_id
        self.metadata = metadata
        self.status = ReportStatus.DRAFT
        
        # 报告结构
        self.sections: List[ReportSection] = []
        self.toc_enabled = True
        self.page_numbering = True
        
        # 生成配置
        self.target_formats: Set[ReportFormat] = {ReportFormat.HTML}
        self.generation_config: Dict[str, Any] = {}
        
        # 数据和上下文
        self.placeholder_values: Dict[str, Any] = {}
        self.generation_context: Dict[str, Any] = {}
        
        # 审计信息
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.generation_started_at: Optional[datetime] = None
        self.generation_completed_at: Optional[datetime] = None
        
        # 生成结果
        self.generated_content: Dict[ReportFormat, str] = {}
        self.generation_errors: List[str] = []
        self.generation_warnings: List[str] = []
    
    def add_section(self, section: ReportSection):
        """添加段落"""
        self.sections.append(section)
        self.sections.sort(key=lambda s: s.order)
        self.updated_at = datetime.now()
    
    def remove_section(self, section_id: str) -> bool:
        """移除段落"""
        initial_count = len(self.sections)
        self.sections = [s for s in self.sections if s.section_id != section_id]
        
        if len(self.sections) < initial_count:
            self.updated_at = datetime.now()
            return True
        return False
    
    def set_placeholder_value(self, placeholder_name: str, value: Any):
        """设置占位符值"""
        self.placeholder_values[placeholder_name] = value
        self.updated_at = datetime.now()
    
    def set_placeholder_values(self, values: Dict[str, Any]):
        """批量设置占位符值"""
        self.placeholder_values.update(values)
        self.updated_at = datetime.now()
    
    def start_generation(self):
        """开始生成"""
        self.status = ReportStatus.GENERATING
        self.generation_started_at = datetime.now()
        self.generated_content.clear()
        self.generation_errors.clear()
        self.generation_warnings.clear()
    
    def complete_generation(self, generated_content: Dict[ReportFormat, str]):
        """完成生成"""
        self.status = ReportStatus.COMPLETED
        self.generation_completed_at = datetime.now()
        self.generated_content = generated_content
    
    def fail_generation(self, errors: List[str]):
        """生成失败"""
        self.status = ReportStatus.FAILED
        self.generation_completed_at = datetime.now()
        self.generation_errors = errors
    
    def get_generation_duration(self) -> Optional[float]:
        """获取生成时长（秒）"""
        if self.generation_started_at and self.generation_completed_at:
            return (self.generation_completed_at - self.generation_started_at).total_seconds()
        return None
    
    def validate_structure(self) -> Dict[str, Any]:
        """验证报告结构"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 检查是否有段落
        if not self.sections:
            validation_result['valid'] = False
            validation_result['errors'].append("Report must have at least one section")
        
        # 检查段落结构
        for section in self.sections:
            if not section.title.strip():
                validation_result['warnings'].append(f"Section {section.section_id} has empty title")
            
            if not section.content_blocks:
                validation_result['warnings'].append(f"Section {section.section_id} has no content blocks")
        
        # 检查必需的占位符
        required_placeholders = self.extract_required_placeholders()
        missing_placeholders = [
            ph for ph in required_placeholders 
            if ph not in self.placeholder_values
        ]
        
        if missing_placeholders:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Missing required placeholders: {missing_placeholders}")
        
        return validation_result
    
    def extract_required_placeholders(self) -> Set[str]:
        """提取必需的占位符"""
        placeholders = set()
        
        for section in self.sections:
            for block in section.content_blocks:
                if block.is_required:
                    placeholders.update(self._extract_placeholders_from_content(block.content))
        
        return placeholders
    
    def _extract_placeholders_from_content(self, content: Any) -> Set[str]:
        """从内容中提取占位符"""
        placeholders = set()
        
        if isinstance(content, str):
            # 提取 {{placeholder}} 格式的占位符
            matches = re.findall(r'\{\{\s*([^{}]+?)\s*\}\}', content)
            placeholders.update(matches)
        elif isinstance(content, dict):
            for value in content.values():
                placeholders.update(self._extract_placeholders_from_content(value))
        elif isinstance(content, list):
            for item in content:
                placeholders.update(self._extract_placeholders_from_content(item))
        
        return placeholders
    
    def get_content_statistics(self) -> Dict[str, Any]:
        """获取内容统计"""
        stats = {
            'total_sections': len(self.sections),
            'total_content_blocks': 0,
            'content_by_type': {},
            'estimated_word_count': 0,
            'estimated_page_count': 0
        }
        
        for section in self.sections:
            stats['total_content_blocks'] += len(section.content_blocks)
            
            for block in section.content_blocks:
                content_type = block.content_type.value
                stats['content_by_type'][content_type] = stats['content_by_type'].get(content_type, 0) + 1
                
                # 估算字数
                if block.content_type == ContentType.TEXT:
                    text_content = str(block.content)
                    stats['estimated_word_count'] += len(text_content.split())
                elif block.content_type == ContentType.TABLE:
                    stats['estimated_word_count'] += 100  # 表格估算
        
        # 估算页数（每页约500字）
        stats['estimated_page_count'] = max(1, stats['estimated_word_count'] // 500)
        
        return stats


class ReportGenerationDomainService:
    """报告生成领域服务"""
    
    def __init__(self):
        self.content_processors = {
            ContentType.TEXT: self._process_text_content,
            ContentType.TABLE: self._process_table_content,
            ContentType.LIST: self._process_list_content,
            ContentType.SECTION: self._process_section_content
        }
    
    def create_report(self, report_id: str, metadata: ReportMetadata) -> ReportEntity:
        """创建报告"""
        report = ReportEntity(report_id, metadata)
        
        logger.info(f"Created report: {metadata.title}")
        return report
    
    def populate_report_from_template(self, report: ReportEntity, 
                                    template_structure: Dict[str, Any]) -> ReportEntity:
        """从模板结构填充报告"""
        # 清空现有段落
        report.sections.clear()
        
        # 解析模板段落
        for section_data in template_structure.get('sections', []):
            section = self._create_section_from_template(section_data)
            report.add_section(section)
        
        # 设置配置
        if 'config' in template_structure:
            config = template_structure['config']
            report.toc_enabled = config.get('toc_enabled', True)
            report.page_numbering = config.get('page_numbering', True)
            report.generation_config.update(config.get('generation', {}))
        
        logger.info(f"Populated report {report.id} from template with {len(report.sections)} sections")
        return report
    
    def process_placeholder_substitution(self, report: ReportEntity) -> Dict[str, Any]:
        """处理占位符替换"""
        substitution_result = {
            'success': True,
            'substituted_count': 0,
            'errors': [],
            'warnings': []
        }
        
        for section in report.sections:
            for block in section.content_blocks:
                try:
                    processed_content = self._substitute_placeholders_in_content(
                        block.content, report.placeholder_values
                    )
                    
                    if processed_content != block.content:
                        block.content = processed_content
                        substitution_result['substituted_count'] += 1
                        
                except Exception as e:
                    error_msg = f"Failed to substitute placeholders in block {block.block_id}: {e}"
                    substitution_result['errors'].append(error_msg)
                    logger.error(error_msg)
        
        if substitution_result['errors']:
            substitution_result['success'] = False
        
        return substitution_result
    
    def validate_report_content(self, report: ReportEntity) -> Dict[str, Any]:
        """验证报告内容"""
        validation_result = report.validate_structure()
        
        # 内容级别验证
        for section in report.sections:
            # 验证段落条件
            if section.conditions:
                condition_met = self._evaluate_section_conditions(
                    section.conditions, report.generation_context
                )
                if not condition_met:
                    validation_result['warnings'].append(
                        f"Section {section.section_id} conditions not met"
                    )
            
            # 验证内容块
            for block in section.content_blocks:
                block_validation = self._validate_content_block(block)
                validation_result['warnings'].extend(block_validation.get('warnings', []))
                validation_result['errors'].extend(block_validation.get('errors', []))
        
        return validation_result
    
    def generate_table_of_contents(self, report: ReportEntity) -> Dict[str, Any]:
        """生成目录"""
        if not report.toc_enabled:
            return {'enabled': False, 'toc': []}
        
        toc = []
        
        for i, section in enumerate(report.sections):
            toc_entry = {
                'level': 1,
                'title': section.title,
                'section_id': section.section_id,
                'page_number': i + 1,  # 简化的页码计算
                'subsections': []
            }
            
            for j, subsection in enumerate(section.subsections):
                sub_entry = {
                    'level': 2,
                    'title': subsection.title,
                    'section_id': subsection.section_id,
                    'page_number': i + 1
                }
                toc_entry['subsections'].append(sub_entry)
            
            toc.append(toc_entry)
        
        return {
            'enabled': True,
            'toc': toc,
            'total_sections': len(toc)
        }
    
    def calculate_report_metrics(self, report: ReportEntity) -> Dict[str, Any]:
        """计算报告指标"""
        content_stats = report.get_content_statistics()
        
        metrics = {
            'structure_metrics': content_stats,
            'complexity_score': self._calculate_complexity_score(report),
            'completeness_ratio': self._calculate_completeness_ratio(report),
            'placeholder_coverage': self._calculate_placeholder_coverage(report),
            'generation_metrics': {
                'duration': report.get_generation_duration(),
                'status': report.status.value,
                'errors_count': len(report.generation_errors),
                'warnings_count': len(report.generation_warnings)
            }
        }
        
        return metrics
    
    def _create_section_from_template(self, section_data: Dict[str, Any]) -> ReportSection:
        """从模板数据创建段落"""
        section = ReportSection(
            section_id=section_data.get('id', f"section_{datetime.now().timestamp()}"),
            title=section_data.get('title', ''),
            order=section_data.get('order', 0),
            is_optional=section_data.get('optional', False),
            conditions=section_data.get('conditions', [])
        )
        
        # 创建内容块
        for block_data in section_data.get('content_blocks', []):
            block = ContentBlock(
                block_id=block_data.get('id', f"block_{datetime.now().timestamp()}"),
                content_type=ContentType(block_data.get('type', 'text')),
                content=block_data.get('content', ''),
                metadata=block_data.get('metadata', {}),
                order=block_data.get('order', 0),
                is_required=block_data.get('required', True)
            )
            section.add_content_block(block)
        
        return section
    
    def _substitute_placeholders_in_content(self, content: Any, 
                                          placeholder_values: Dict[str, Any]) -> Any:
        """在内容中替换占位符"""
        if isinstance(content, str):
            # 替换 {{placeholder}} 格式的占位符
            def replace_placeholder(match):
                placeholder_name = match.group(1).strip()
                return str(placeholder_values.get(placeholder_name, f"{{{{ {placeholder_name} }}}}"))
            
            return re.sub(r'\{\{\s*([^{}]+?)\s*\}\}', replace_placeholder, content)
        
        elif isinstance(content, dict):
            return {
                key: self._substitute_placeholders_in_content(value, placeholder_values)
                for key, value in content.items()
            }
        
        elif isinstance(content, list):
            return [
                self._substitute_placeholders_in_content(item, placeholder_values)
                for item in content
            ]
        
        else:
            return content
    
    def _evaluate_section_conditions(self, conditions: List[str], 
                                   context: Dict[str, Any]) -> bool:
        """评估段落条件"""
        # 简化的条件评估
        for condition in conditions:
            # 这里可以实现更复杂的条件评估逻辑
            if condition.startswith('has_'):
                variable_name = condition[4:]
                if variable_name not in context:
                    return False
            elif condition.startswith('not_empty_'):
                variable_name = condition[10:]
                if not context.get(variable_name):
                    return False
        
        return True
    
    def _validate_content_block(self, block: ContentBlock) -> Dict[str, Any]:
        """验证内容块"""
        validation = {'errors': [], 'warnings': []}
        
        if block.content_type in self.content_processors:
            processor = self.content_processors[block.content_type]
            processor_result = processor(block)
            validation['warnings'].extend(processor_result.get('warnings', []))
            validation['errors'].extend(processor_result.get('errors', []))
        
        return validation
    
    def _process_text_content(self, block: ContentBlock) -> Dict[str, Any]:
        """处理文本内容"""
        result = {'warnings': [], 'errors': []}
        
        if not isinstance(block.content, str):
            result['errors'].append(f"Text block {block.block_id} content is not a string")
        elif len(block.content.strip()) == 0:
            result['warnings'].append(f"Text block {block.block_id} is empty")
        
        return result
    
    def _process_table_content(self, block: ContentBlock) -> Dict[str, Any]:
        """处理表格内容"""
        result = {'warnings': [], 'errors': []}
        
        if not isinstance(block.content, dict):
            result['errors'].append(f"Table block {block.block_id} content is not a dict")
        elif 'data' not in block.content:
            result['errors'].append(f"Table block {block.block_id} missing 'data' field")
        elif not isinstance(block.content['data'], list):
            result['errors'].append(f"Table block {block.block_id} 'data' is not a list")
        elif len(block.content['data']) == 0:
            result['warnings'].append(f"Table block {block.block_id} has no data rows")
        
        return result
    
    def _process_list_content(self, block: ContentBlock) -> Dict[str, Any]:
        """处理列表内容"""
        result = {'warnings': [], 'errors': []}
        
        if not isinstance(block.content, dict):
            result['errors'].append(f"List block {block.block_id} content is not a dict")
        elif 'items' not in block.content:
            result['errors'].append(f"List block {block.block_id} missing 'items' field")
        elif not isinstance(block.content['items'], list):
            result['errors'].append(f"List block {block.block_id} 'items' is not a list")
        elif len(block.content['items']) == 0:
            result['warnings'].append(f"List block {block.block_id} has no items")
        
        return result
    
    def _process_section_content(self, block: ContentBlock) -> Dict[str, Any]:
        """处理段落内容"""
        result = {'warnings': [], 'errors': []}
        
        if not isinstance(block.content, dict):
            result['errors'].append(f"Section block {block.block_id} content is not a dict")
        elif 'title' not in block.content:
            result['warnings'].append(f"Section block {block.block_id} missing title")
        
        return result
    
    def _calculate_complexity_score(self, report: ReportEntity) -> float:
        """计算复杂度分数"""
        score = 0.0
        
        # 基于段落数量
        score += len(report.sections) * 0.5
        
        # 基于内容块数量和类型
        for section in report.sections:
            for block in section.content_blocks:
                if block.content_type == ContentType.TEXT:
                    score += 0.1
                elif block.content_type == ContentType.TABLE:
                    score += 0.5
                elif block.content_type == ContentType.CHART:
                    score += 0.3
        
        # 基于占位符数量
        placeholders = report.extract_required_placeholders()
        score += len(placeholders) * 0.1
        
        return round(score, 2)
    
    def _calculate_completeness_ratio(self, report: ReportEntity) -> float:
        """计算完整性比率"""
        total_blocks = 0
        complete_blocks = 0
        
        for section in report.sections:
            for block in section.content_blocks:
                total_blocks += 1
                
                # 检查内容是否完整
                if block.content_type == ContentType.TEXT:
                    if isinstance(block.content, str) and len(block.content.strip()) > 0:
                        complete_blocks += 1
                elif block.content_type == ContentType.TABLE:
                    if (isinstance(block.content, dict) and 
                        'data' in block.content and 
                        len(block.content['data']) > 0):
                        complete_blocks += 1
                else:
                    if block.content:
                        complete_blocks += 1
        
        return complete_blocks / total_blocks if total_blocks > 0 else 1.0
    
    def _calculate_placeholder_coverage(self, report: ReportEntity) -> float:
        """计算占位符覆盖率"""
        required_placeholders = report.extract_required_placeholders()
        if not required_placeholders:
            return 1.0
        
        covered_placeholders = sum(
            1 for ph in required_placeholders 
            if ph in report.placeholder_values and report.placeholder_values[ph] is not None
        )
        
        return covered_placeholders / len(required_placeholders)