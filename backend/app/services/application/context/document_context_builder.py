"""
文档上下文构建器
从文档内容、模板信息和用户需求构建标准的DocumentContext对象
"""
import logging
import re
from typing import Optional, Dict, Any, List, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import hashlib

from app.services.domain.placeholder.models import DocumentContext

logger = logging.getLogger(__name__)

class DocumentType(Enum):
    """文档类型枚举"""
    FINANCIAL_REPORT = "financial_report"
    SALES_REPORT = "sales_report"
    OPERATIONAL_REPORT = "operational_report"
    MARKETING_REPORT = "marketing_report"
    EXECUTIVE_SUMMARY = "executive_summary"
    DASHBOARD = "dashboard"
    KPI_REPORT = "kpi_report"
    ANALYSIS_REPORT = "analysis_report"
    COMPLIANCE_REPORT = "compliance_report"
    PROJECT_REPORT = "project_report"
    CUSTOM_REPORT = "custom_report"

class DocumentFormat(Enum):
    """文档格式枚举"""
    HTML = "html"
    MARKDOWN = "markdown"
    DOCX = "docx"
    PDF = "pdf"
    PLAIN_TEXT = "plain_text"
    JSON = "json"
    XML = "xml"

class ContentComplexity(Enum):
    """内容复杂度枚举"""
    SIMPLE = "simple"      # 简单报告，基础数据展示
    MODERATE = "moderate"  # 中等复杂度，有分析和图表
    COMPLEX = "complex"    # 复杂报告，多层次分析
    ADVANCED = "advanced"  # 高级报告，深度分析和洞察

@dataclass
class TemplateInfo:
    """模板信息"""
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    template_version: Optional[str] = None
    template_category: Optional[str] = None
    placeholder_count: int = 0
    structure_elements: List[str] = None
    
    def __post_init__(self):
        if self.structure_elements is None:
            self.structure_elements = []

@dataclass
class DocumentStructure:
    """文档结构信息"""
    total_sections: int = 0
    heading_levels: List[int] = None
    paragraph_count: int = 0
    placeholder_count: int = 0
    table_count: int = 0
    chart_count: int = 0
    image_count: int = 0
    
    def __post_init__(self):
        if self.heading_levels is None:
            self.heading_levels = []

@dataclass
class ContentAnalysis:
    """内容分析结果"""
    word_count: int = 0
    sentence_count: int = 0
    avg_sentence_length: float = 0.0
    readability_score: float = 0.0
    technical_term_count: int = 0
    business_term_count: int = 0
    time_references: List[str] = None
    key_topics: List[str] = None
    
    def __post_init__(self):
        if self.time_references is None:
            self.time_references = []
        if self.key_topics is None:
            self.key_topics = []

class DocumentContextBuilder:
    """文档上下文构建器"""
    
    def __init__(self):
        self._document_patterns = self._initialize_document_patterns()
        self._complexity_indicators = self._initialize_complexity_indicators()
        self._business_terms = self._initialize_business_terms()
        self._technical_terms = self._initialize_technical_terms()
    
    def _initialize_document_patterns(self) -> Dict[DocumentType, Dict[str, Any]]:
        """初始化文档模式"""
        return {
            DocumentType.FINANCIAL_REPORT: {
                "keywords": ["财务", "收入", "支出", "利润", "资产", "负债", "现金流"],
                "typical_sections": ["财务概览", "收入分析", "成本分析", "利润分析", "资产负债"],
                "complexity_baseline": 0.7,
                "expected_placeholders": ["统计", "趋势", "对比", "统计图"]
            },
            DocumentType.SALES_REPORT: {
                "keywords": ["销售", "客户", "订单", "业绩", "目标", "渠道", "转化"],
                "typical_sections": ["销售概览", "业绩分析", "客户分析", "渠道分析", "目标达成"],
                "complexity_baseline": 0.6,
                "expected_placeholders": ["统计", "对比", "列表", "统计图"]
            },
            DocumentType.OPERATIONAL_REPORT: {
                "keywords": ["运营", "效率", "质量", "生产", "流程", "成本", "绩效"],
                "typical_sections": ["运营概览", "效率分析", "质量控制", "成本分析", "改进建议"],
                "complexity_baseline": 0.6,
                "expected_placeholders": ["统计", "趋势", "极值", "统计图"]
            },
            DocumentType.EXECUTIVE_SUMMARY: {
                "keywords": ["摘要", "总结", "概览", "关键", "核心", "重点", "洞察"],
                "typical_sections": ["核心要点", "关键指标", "主要发现", "建议措施"],
                "complexity_baseline": 0.8,
                "expected_placeholders": ["统计", "极值", "对比"]
            },
            DocumentType.DASHBOARD: {
                "keywords": ["仪表盘", "监控", "实时", "指标", "KPI", "状态", "概览"],
                "typical_sections": ["关键指标", "趋势图表", "状态监控", "异常预警"],
                "complexity_baseline": 0.5,
                "expected_placeholders": ["统计", "统计图", "趋势", "极值"]
            }
        }
    
    def _initialize_complexity_indicators(self) -> Dict[str, float]:
        """初始化复杂度指标权重"""
        return {
            "nested_placeholders": 0.3,
            "conditional_logic": 0.25,
            "multiple_data_sources": 0.2,
            "advanced_calculations": 0.25,
            "cross_references": 0.15,
            "dynamic_content": 0.1
        }
    
    def _initialize_business_terms(self) -> Dict[str, List[str]]:
        """初始化业务术语库"""
        return {
            "finance": ["ROI", "EBITDA", "现金流", "资产负债率", "毛利率", "净利率"],
            "sales": ["转化率", "客单价", "留存率", "获客成本", "生命周期价值"],
            "operations": ["产能利用率", "良品率", "周转率", "效率指标", "SLA"],
            "marketing": ["点击率", "展示量", "转化漏斗", "品牌知名度", "用户画像"],
            "hr": ["离职率", "满意度", "绩效评估", "培训完成率", "招聘成本"]
        }
    
    def _initialize_technical_terms(self) -> List[str]:
        """初始化技术术语库"""
        return [
            "API", "数据库", "算法", "机器学习", "人工智能", "大数据",
            "云计算", "微服务", "容器化", "DevOps", "自动化", "集成",
            "架构", "框架", "中间件", "负载均衡", "缓存", "队列"
        ]
    
    def build_from_template(self, 
                           template_content: str,
                           template_info: Optional[TemplateInfo] = None,
                           document_type: Optional[DocumentType] = None,
                           custom_metadata: Optional[Dict[str, Any]] = None) -> DocumentContext:
        """
        从模板内容构建文档上下文
        
        Args:
            template_content: 模板内容
            template_info: 模板信息
            document_type: 文档类型
            custom_metadata: 自定义元数据
        """
        try:
            # 分析文档结构
            structure = self._analyze_document_structure(template_content)
            
            # 分析内容
            content_analysis = self._analyze_content(template_content)
            
            # 推断文档类型
            if not document_type:
                document_type = self._infer_document_type(template_content, content_analysis)
            
            # 推断文档格式
            document_format = self._infer_document_format(template_content)
            
            # 计算复杂度
            complexity = self._calculate_complexity(
                template_content, structure, content_analysis, document_type
            )
            
            # 推断语言
            language = self._detect_language(template_content)
            
            # 构建元数据
            metadata = self._build_template_metadata(
                template_info, structure, content_analysis, custom_metadata
            )
            
            return DocumentContext(
                document_type=document_type.value,
                domain=self._infer_domain_from_type(document_type),
                language=language,
                structure_complexity=complexity,
                format_type=document_format.value,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"文档上下文构建失败: {e}")
            return self._create_default_document_context()
    
    def build_from_content_analysis(self,
                                   content: str,
                                   user_intent: Optional[Dict[str, Any]] = None,
                                   document_specs: Optional[Dict[str, Any]] = None) -> DocumentContext:
        """
        从内容分析构建文档上下文
        
        Args:
            content: 文档内容
            user_intent: 用户意图
            document_specs: 文档规格要求
        """
        try:
            # 深度内容分析
            content_analysis = self._deep_content_analysis(content)
            
            # 结构分析
            structure = self._analyze_document_structure(content)
            
            # 基于用户意图调整
            if user_intent:
                document_type = self._determine_type_from_intent(user_intent, content_analysis)
                complexity_adjustment = user_intent.get("complexity_preference", 0.0)
            else:
                document_type = self._infer_document_type(content, content_analysis)
                complexity_adjustment = 0.0
            
            # 计算调整后的复杂度
            base_complexity = self._calculate_complexity(content, structure, content_analysis, document_type)
            final_complexity = min(1.0, max(0.0, base_complexity + complexity_adjustment))
            
            # 应用文档规格
            if document_specs:
                metadata = self._apply_document_specs(document_specs, content_analysis)
                if "document_type" in document_specs:
                    try:
                        document_type = DocumentType(document_specs["document_type"])
                    except ValueError:
                        pass
            else:
                metadata = {}
            
            # 构建上下文
            return DocumentContext(
                document_type=document_type.value,
                domain=self._infer_domain_from_content(content, content_analysis),
                language=self._detect_language(content),
                structure_complexity=final_complexity,
                format_type=self._infer_document_format(content).value,
                metadata={
                    **metadata,
                    "content_analysis": {
                        "word_count": content_analysis.word_count,
                        "technical_density": content_analysis.technical_term_count / max(content_analysis.word_count, 1),
                        "business_density": content_analysis.business_term_count / max(content_analysis.word_count, 1),
                        "key_topics": content_analysis.key_topics[:5]
                    },
                    "structure_info": {
                        "sections": structure.total_sections,
                        "placeholders": structure.placeholder_count,
                        "charts": structure.chart_count
                    },
                    "user_intent": user_intent or {},
                    "created_at": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"基于内容分析的文档上下文构建失败: {e}")
            return self._create_default_document_context()
    
    def build_for_dashboard(self,
                           dashboard_config: Dict[str, Any],
                           widget_specs: List[Dict[str, Any]],
                           data_sources: List[str]) -> DocumentContext:
        """
        为仪表盘构建专门的文档上下文
        
        Args:
            dashboard_config: 仪表盘配置
            widget_specs: 组件规格列表
            data_sources: 数据源列表
        """
        try:
            # 分析仪表盘复杂度
            complexity = self._calculate_dashboard_complexity(widget_specs, data_sources)
            
            # 推断主要业务域
            domain = self._infer_domain_from_widgets(widget_specs)
            
            # 构建仪表盘特定元数据
            metadata = {
                "dashboard_config": dashboard_config,
                "widget_count": len(widget_specs),
                "data_source_count": len(data_sources),
                "widget_types": list(set(w.get("type", "unknown") for w in widget_specs)),
                "refresh_frequency": dashboard_config.get("refresh_frequency", "5min"),
                "real_time_widgets": len([w for w in widget_specs if w.get("real_time", False)]),
                "interactive_widgets": len([w for w in widget_specs if w.get("interactive", False)]),
                "data_sources": data_sources,
                "created_at": datetime.now().isoformat()
            }
            
            return DocumentContext(
                document_type=DocumentType.DASHBOARD.value,
                domain=domain,
                language="chinese",  # 默认中文
                structure_complexity=complexity,
                format_type=DocumentFormat.HTML.value,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"仪表盘文档上下文构建失败: {e}")
            return self._create_default_document_context()
    
    def _analyze_document_structure(self, content: str) -> DocumentStructure:
        """分析文档结构"""
        structure = DocumentStructure()
        
        # 统计标题层级
        heading_pattern = re.compile(r'^#{1,6}\s+', re.MULTILINE)
        headings = heading_pattern.findall(content)
        structure.heading_levels = [len(h.strip()) for h in headings]
        structure.total_sections = len(headings)
        
        # 统计段落
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        structure.paragraph_count = len(paragraphs)
        
        # 统计占位符
        placeholder_pattern = re.compile(r'\{\{[^}]+\}\}')
        placeholders = placeholder_pattern.findall(content)
        structure.placeholder_count = len(placeholders)
        
        # 统计表格
        table_patterns = [
            r'\|.*\|',  # Markdown表格
            r'<table[^>]*>.*?</table>',  # HTML表格
            r'表格[:：]\s*\{\{[^}]+\}\}'  # 中文表格占位符
        ]
        structure.table_count = sum(
            len(re.findall(pattern, content, re.IGNORECASE | re.DOTALL))
            for pattern in table_patterns
        )
        
        # 统计图表
        chart_patterns = [
            r'\{\{统计图[^}]*\}\}',
            r'图表[:：]\s*\{\{[^}]+\}\}',
            r'<canvas[^>]*>',
            r'<svg[^>]*>'
        ]
        structure.chart_count = sum(
            len(re.findall(pattern, content, re.IGNORECASE))
            for pattern in chart_patterns
        )
        
        # 统计图片
        image_patterns = [
            r'!\[[^\]]*\]\([^)]+\)',  # Markdown图片
            r'<img[^>]*>',  # HTML图片
            r'图片[:：]\s*\{\{[^}]+\}\}'  # 中文图片占位符
        ]
        structure.image_count = sum(
            len(re.findall(pattern, content, re.IGNORECASE))
            for pattern in image_patterns
        )
        
        return structure
    
    def _analyze_content(self, content: str) -> ContentAnalysis:
        """分析内容特征"""
        analysis = ContentAnalysis()
        
        # 基础统计
        words = re.findall(r'[\w\u4e00-\u9fff]+', content)
        analysis.word_count = len(words)
        
        sentences = re.split(r'[。！？.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        analysis.sentence_count = len(sentences)
        
        if analysis.sentence_count > 0:
            analysis.avg_sentence_length = analysis.word_count / analysis.sentence_count
        
        # 技术术语统计
        technical_count = 0
        for term in self._technical_terms:
            technical_count += content.count(term)
        analysis.technical_term_count = technical_count
        
        # 业务术语统计
        business_count = 0
        for category_terms in self._business_terms.values():
            for term in category_terms:
                business_count += content.count(term)
        analysis.business_term_count = business_count
        
        # 时间引用
        time_patterns = [
            r'\d{4}年\d{1,2}月',
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'第[一二三四]季度',
            r'本月|上月|下月',
            r'今年|去年|明年'
        ]
        time_refs = []
        for pattern in time_patterns:
            time_refs.extend(re.findall(pattern, content))
        analysis.time_references = list(set(time_refs))
        
        # 关键主题提取（简化版）
        analysis.key_topics = self._extract_key_topics(content, words)
        
        # 可读性评分（简化版）
        analysis.readability_score = self._calculate_readability(content, analysis)
        
        return analysis
    
    def _deep_content_analysis(self, content: str) -> ContentAnalysis:
        """深度内容分析"""
        # 基础分析
        analysis = self._analyze_content(content)
        
        # 扩展分析
        # 1. 语义密度分析
        semantic_density = self._calculate_semantic_density(content)
        
        # 2. 结构复杂度分析
        structural_complexity = self._analyze_structural_complexity(content)
        
        # 3. 信息层次分析
        information_hierarchy = self._analyze_information_hierarchy(content)
        
        # 更新分析结果
        analysis.readability_score = (
            analysis.readability_score * 0.4 +
            semantic_density * 0.3 +
            structural_complexity * 0.3
        )
        
        return analysis
    
    def _infer_document_type(self, content: str, analysis: ContentAnalysis) -> DocumentType:
        """推断文档类型"""
        content_lower = content.lower()
        
        # 基于关键词匹配
        type_scores = {}
        for doc_type, patterns in self._document_patterns.items():
            score = 0
            keywords = patterns["keywords"]
            for keyword in keywords:
                score += content_lower.count(keyword)
            
            # 归一化分数
            if len(keywords) > 0:
                type_scores[doc_type] = score / len(keywords)
        
        # 基于结构特征调整
        if analysis.business_term_count > analysis.technical_term_count:
            # 偏向业务报告
            if DocumentType.SALES_REPORT in type_scores:
                type_scores[DocumentType.SALES_REPORT] *= 1.2
            if DocumentType.FINANCIAL_REPORT in type_scores:
                type_scores[DocumentType.FINANCIAL_REPORT] *= 1.2
        
        if len(analysis.time_references) > 3:
            # 有很多时间引用，可能是定期报告
            for report_type in [DocumentType.FINANCIAL_REPORT, DocumentType.SALES_REPORT, 
                               DocumentType.OPERATIONAL_REPORT]:
                if report_type in type_scores:
                    type_scores[report_type] *= 1.1
        
        # 返回得分最高的类型
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            if type_scores[best_type] > 0:
                return best_type
        
        return DocumentType.CUSTOM_REPORT
    
    def _infer_document_format(self, content: str) -> DocumentFormat:
        """推断文档格式"""
        if re.search(r'<[^>]+>', content):
            return DocumentFormat.HTML
        elif re.search(r'#{1,6}\s+', content):
            return DocumentFormat.MARKDOWN
        elif content.startswith('<?xml'):
            return DocumentFormat.XML
        else:
            return DocumentFormat.PLAIN_TEXT
    
    def _calculate_complexity(self, 
                            content: str, 
                            structure: DocumentStructure,
                            analysis: ContentAnalysis,
                            doc_type: DocumentType) -> float:
        """计算文档复杂度"""
        complexity_score = 0.0
        
        # 基础复杂度（基于文档类型）
        base_complexity = self._document_patterns.get(doc_type, {}).get("complexity_baseline", 0.5)
        complexity_score += base_complexity * 0.3
        
        # 结构复杂度
        structure_score = 0.0
        if structure.total_sections > 5:
            structure_score += 0.2
        if len(structure.heading_levels) > 0 and max(structure.heading_levels) > 3:
            structure_score += 0.1
        if structure.placeholder_count > 10:
            structure_score += 0.2
        if structure.chart_count > 3:
            structure_score += 0.1
        
        complexity_score += structure_score * 0.3
        
        # 内容复杂度
        content_score = 0.0
        if analysis.technical_term_count > 5:
            content_score += 0.2
        if analysis.avg_sentence_length > 30:
            content_score += 0.1
        if len(analysis.time_references) > 5:
            content_score += 0.1
        
        complexity_score += content_score * 0.2
        
        # 占位符复杂度
        placeholder_complexity = self._analyze_placeholder_complexity(content)
        complexity_score += placeholder_complexity * 0.2
        
        return min(1.0, max(0.0, complexity_score))
    
    def _analyze_placeholder_complexity(self, content: str) -> float:
        """分析占位符复杂度"""
        complexity = 0.0
        
        # 检测各种复杂度指标
        indicators = self._complexity_indicators
        
        # 嵌套占位符
        nested_pattern = r'\{\{[^}]*\{\{[^}]*\}\}[^}]*\}\}'
        nested_count = len(re.findall(nested_pattern, content))
        complexity += (nested_count / 10) * indicators["nested_placeholders"]
        
        # 条件逻辑
        conditional_patterns = [r'\{\{[^}]*条件[^}]*\}\}', r'\{\{[^}]*if[^}]*\}\}']
        conditional_count = sum(len(re.findall(pattern, content, re.IGNORECASE)) 
                               for pattern in conditional_patterns)
        complexity += (conditional_count / 5) * indicators["conditional_logic"]
        
        # 参数化占位符
        param_pattern = r'\{\{[^}]*\|[^}]*\}\}'
        param_count = len(re.findall(param_pattern, content))
        complexity += (param_count / 15) * indicators["advanced_calculations"]
        
        return min(1.0, complexity)
    
    def _detect_language(self, content: str) -> str:
        """检测文档语言"""
        # 简单的语言检测
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_chars = len(re.findall(r'[a-zA-Z]', content))
        
        if chinese_chars > english_chars:
            return "chinese"
        elif english_chars > chinese_chars:
            return "english"
        else:
            return "mixed"
    
    def _infer_domain_from_type(self, doc_type: DocumentType) -> str:
        """从文档类型推断业务领域"""
        type_to_domain = {
            DocumentType.FINANCIAL_REPORT: "finance",
            DocumentType.SALES_REPORT: "sales",
            DocumentType.OPERATIONAL_REPORT: "operations",
            DocumentType.MARKETING_REPORT: "marketing",
            DocumentType.EXECUTIVE_SUMMARY: "strategy",
            DocumentType.DASHBOARD: "analytics",
            DocumentType.KPI_REPORT: "performance",
            DocumentType.ANALYSIS_REPORT: "analytics",
            DocumentType.COMPLIANCE_REPORT: "compliance",
            DocumentType.PROJECT_REPORT: "project_management"
        }
        
        return type_to_domain.get(doc_type, "general")
    
    def _infer_domain_from_content(self, content: str, analysis: ContentAnalysis) -> str:
        """从内容推断业务领域"""
        content_lower = content.lower()
        
        domain_scores = {}
        for domain, terms in self._business_terms.items():
            score = sum(content_lower.count(term.lower()) for term in terms)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        
        return "general"
    
    def _extract_key_topics(self, content: str, words: List[str]) -> List[str]:
        """提取关键主题（简化版）"""
        # 词频统计
        word_freq = {}
        for word in words:
            if len(word) >= 2 and word.isalnum():
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 过滤常用词
        common_words = {"的", "了", "在", "是", "有", "和", "与", "或", "不", "这", "那", "我们", "公司", "业务"}
        filtered_freq = {word: freq for word, freq in word_freq.items() 
                        if word not in common_words and freq >= 2}
        
        # 返回频率最高的前10个词
        sorted_words = sorted(filtered_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10]]
    
    def _calculate_readability(self, content: str, analysis: ContentAnalysis) -> float:
        """计算可读性分数（简化版）"""
        if analysis.sentence_count == 0:
            return 0.5
        
        # 基于平均句子长度的简单评分
        avg_length = analysis.avg_sentence_length
        
        if avg_length < 10:
            return 0.9  # 非常易读
        elif avg_length < 20:
            return 0.7  # 易读
        elif avg_length < 30:
            return 0.5  # 中等
        elif avg_length < 40:
            return 0.3  # 较难
        else:
            return 0.1  # 很难读
    
    def _calculate_semantic_density(self, content: str) -> float:
        """计算语义密度"""
        # 简化的语义密度计算
        total_chars = len(content)
        if total_chars == 0:
            return 0.0
        
        # 计算信息承载字符比例
        info_chars = len(re.findall(r'[\u4e00-\u9fff\w]', content))
        semantic_density = info_chars / total_chars
        
        return min(1.0, semantic_density)
    
    def _analyze_structural_complexity(self, content: str) -> float:
        """分析结构复杂度"""
        complexity = 0.0
        
        # 列表结构
        list_count = len(re.findall(r'^\s*[-*+]\s+', content, re.MULTILINE))
        complexity += min(0.3, list_count / 10)
        
        # 编号结构
        number_count = len(re.findall(r'^\s*\d+[.)]\s+', content, re.MULTILINE))
        complexity += min(0.2, number_count / 10)
        
        # 引用结构
        quote_count = len(re.findall(r'^\s*>\s+', content, re.MULTILINE))
        complexity += min(0.1, quote_count / 5)
        
        return min(1.0, complexity)
    
    def _analyze_information_hierarchy(self, content: str) -> float:
        """分析信息层次"""
        # 检测标题层次的深度和分布
        headings = re.findall(r'^(#{1,6})\s+', content, re.MULTILINE)
        if not headings:
            return 0.0
        
        heading_levels = [len(h) for h in headings]
        max_depth = max(heading_levels)
        level_variety = len(set(heading_levels))
        
        hierarchy_score = (max_depth / 6) * 0.5 + (level_variety / 6) * 0.5
        return min(1.0, hierarchy_score)
    
    def _build_template_metadata(self, 
                                template_info: Optional[TemplateInfo],
                                structure: DocumentStructure,
                                analysis: ContentAnalysis,
                                custom_metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """构建模板元数据"""
        metadata = {
            "builder_version": "1.0",
            "created_at": datetime.now().isoformat(),
            "structure_analysis": {
                "sections": structure.total_sections,
                "paragraphs": structure.paragraph_count,
                "placeholders": structure.placeholder_count,
                "charts": structure.chart_count,
                "tables": structure.table_count
            },
            "content_analysis": {
                "word_count": analysis.word_count,
                "readability": analysis.readability_score,
                "key_topics": analysis.key_topics[:5],
                "time_references": len(analysis.time_references)
            }
        }
        
        if template_info:
            metadata["template_info"] = {
                "template_id": template_info.template_id,
                "template_name": template_info.template_name,
                "template_version": template_info.template_version,
                "template_category": template_info.template_category
            }
        
        if custom_metadata:
            metadata["custom"] = custom_metadata
        
        return metadata
    
    def _create_default_document_context(self) -> DocumentContext:
        """创建默认文档上下文"""
        return DocumentContext(
            document_type=DocumentType.CUSTOM_REPORT.value,
            domain="general",
            language="chinese",
            structure_complexity=0.5,
            format_type=DocumentFormat.PLAIN_TEXT.value,
            metadata={
                "default_context": True,
                "created_at": datetime.now().isoformat()
            }
        )