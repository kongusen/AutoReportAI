"""
章节分析器
分析章节级别的上下文信息和结构
"""
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from ..models import PlaceholderSpec, DocumentContext

logger = logging.getLogger(__name__)

@dataclass
class SectionStructure:
    """章节结构信息"""
    section_index: int
    title: str
    level: int  # 标题级别 (1-6)
    paragraph_count: int
    subsection_count: int
    total_word_count: int
    placeholder_count: int
    section_type: str  # 章节类型：introduction, analysis, conclusion等
    business_domain: List[str]  # 业务领域
    data_requirements: List[str]  # 数据需求
    reporting_elements: List[str]  # 报告元素

@dataclass
class SectionContext:
    """章节上下文信息"""
    structure: SectionStructure
    semantic_theme: str
    information_density: float
    analytical_complexity: float
    narrative_flow_score: float
    cross_references: List[str]
    dependent_sections: List[int]
    key_concepts: List[str]
    data_flow_patterns: List[str]

class SectionAnalyzer:
    """章节分析器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.section_types = self._define_section_types()
        self.business_domains = self._define_business_domains()
        self.reporting_elements = self._define_reporting_elements()
        
    def _define_section_types(self) -> Dict[str, Dict[str, Any]]:
        """定义章节类型特征"""
        return {
            "executive_summary": {
                "keywords": ["摘要", "总结", "概要", "执行", "核心", "要点"],
                "characteristics": {"high_density": True, "data_heavy": True}
            },
            "introduction": {
                "keywords": ["介绍", "概述", "背景", "前言", "引言"],
                "characteristics": {"contextual": True, "foundational": True}
            },
            "methodology": {
                "keywords": ["方法", "流程", "步骤", "程序", "标准"],
                "characteristics": {"procedural": True, "technical": True}
            },
            "analysis": {
                "keywords": ["分析", "研究", "评估", "调查", "检查", "统计"],
                "characteristics": {"analytical": True, "data_intensive": True}
            },
            "results": {
                "keywords": ["结果", "发现", "数据", "统计", "指标", "表现"],
                "characteristics": {"data_presentation": True, "factual": True}
            },
            "discussion": {
                "keywords": ["讨论", "解释", "说明", "阐述", "解读"],
                "characteristics": {"interpretive": True, "contextual": True}
            },
            "conclusion": {
                "keywords": ["结论", "总结", "结果", "结束", "小结"],
                "characteristics": {"summarizing": True, "decisive": True}
            },
            "recommendations": {
                "keywords": ["建议", "推荐", "提议", "方案", "策略"],
                "characteristics": {"actionable": True, "forward_looking": True}
            }
        }
    
    def _define_business_domains(self) -> Dict[str, List[str]]:
        """定义业务领域关键词"""
        return {
            "finance": ["财务", "金融", "资金", "预算", "成本", "收益", "投资", "利润"],
            "sales": ["销售", "营销", "客户", "市场", "渠道", "业绩", "转化"],
            "operations": ["运营", "生产", "供应链", "库存", "效率", "质量", "流程"],
            "hr": ["人力资源", "员工", "招聘", "培训", "绩效", "薪酬"],
            "it": ["信息技术", "系统", "软件", "硬件", "网络", "数据库", "安全"],
            "strategy": ["战略", "规划", "目标", "发展", "增长", "竞争", "市场定位"]
        }
    
    def _define_reporting_elements(self) -> Dict[str, List[str]]:
        """定义报告元素类型"""
        return {
            "charts": ["图表", "柱状图", "折线图", "饼图", "散点图", "热力图"],
            "tables": ["表格", "数据表", "统计表", "明细表", "汇总表"],
            "kpis": ["KPI", "指标", "度量", "关键绩效", "核心指标"],
            "trends": ["趋势", "变化", "发展", "走势", "演变"],
            "comparisons": ["对比", "比较", "差异", "变化", "增减"],
            "forecasts": ["预测", "预计", "估算", "预期", "展望"]
        }
    
    def analyze_section(self, 
                       title: str,
                       content: str,
                       section_index: int,
                       document_context: DocumentContext,
                       preceding_sections: List[str] = None,
                       following_sections: List[str] = None) -> SectionContext:
        """分析章节上下文"""
        try:
            # 分析章节结构
            structure = self._analyze_section_structure(
                title, content, section_index
            )
            
            # 分析语义主题
            semantic_theme = self._analyze_semantic_theme(title, content)
            
            # 计算信息密度
            information_density = self._calculate_information_density(content)
            
            # 分析分析复杂度
            analytical_complexity = self._analyze_analytical_complexity(content)
            
            # 评估叙述流畅度
            narrative_flow_score = self._evaluate_narrative_flow(content)
            
            # 识别交叉引用
            cross_references = self._identify_cross_references(content)
            
            # 分析依赖关系
            dependent_sections = self._analyze_section_dependencies(
                content, preceding_sections, following_sections
            )
            
            # 提取关键概念
            key_concepts = self._extract_key_concepts(content)
            
            # 分析数据流模式
            data_flow_patterns = self._analyze_data_flow_patterns(content)
            
            return SectionContext(
                structure=structure,
                semantic_theme=semantic_theme,
                information_density=information_density,
                analytical_complexity=analytical_complexity,
                narrative_flow_score=narrative_flow_score,
                cross_references=cross_references,
                dependent_sections=dependent_sections,
                key_concepts=key_concepts,
                data_flow_patterns=data_flow_patterns
            )
            
        except Exception as e:
            logger.error(f"章节分析失败: {e}")
            return self._create_fallback_section_context(title, content, section_index)
    
    def _analyze_section_structure(self, 
                                  title: str, 
                                  content: str, 
                                  section_index: int) -> SectionStructure:
        """分析章节结构"""
        # 检测标题级别
        level = self._detect_heading_level(title)
        
        # 统计段落数量
        paragraphs = content.split('\n\n')
        paragraph_count = len([p for p in paragraphs if p.strip()])
        
        # 统计子章节
        subsection_count = len(re.findall(r'^#+\s', content, re.MULTILINE))
        
        # 字数统计
        total_word_count = len(content.replace(' ', ''))
        
        # 占位符统计
        placeholder_count = len(re.findall(r'\{\{[^}]+\}\}', content))
        
        # 识别章节类型
        section_type = self._classify_section_type(title, content)
        
        # 识别业务领域
        business_domain = self._identify_business_domain(content)
        
        # 识别数据需求
        data_requirements = self._identify_data_requirements(content)
        
        # 识别报告元素
        reporting_elements = self._identify_reporting_elements(content)
        
        return SectionStructure(
            section_index=section_index,
            title=title,
            level=level,
            paragraph_count=paragraph_count,
            subsection_count=subsection_count,
            total_word_count=total_word_count,
            placeholder_count=placeholder_count,
            section_type=section_type,
            business_domain=business_domain,
            data_requirements=data_requirements,
            reporting_elements=reporting_elements
        )
    
    def _detect_heading_level(self, title: str) -> int:
        """检测标题级别"""
        # 检查Markdown格式
        if title.startswith('#'):
            return len(title) - len(title.lstrip('#'))
        
        # 基于标题内容推断级别
        if any(keyword in title for keyword in ["第", "章", "部分"]):
            return 1
        elif any(keyword in title for keyword in ["节", "小节", "子"]):
            return 2
        else:
            return 3
    
    def _classify_section_type(self, title: str, content: str) -> str:
        """分类章节类型"""
        combined_text = (title + " " + content).lower()
        
        best_match = "general"
        best_score = 0
        
        for section_type, definition in self.section_types.items():
            score = 0
            for keyword in definition["keywords"]:
                if keyword in combined_text:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_match = section_type
        
        return best_match
    
    def _identify_business_domain(self, content: str) -> List[str]:
        """识别业务领域"""
        identified_domains = []
        
        for domain, keywords in self.business_domains.items():
            domain_score = sum(1 for keyword in keywords if keyword in content)
            if domain_score >= 2:  # 至少匹配2个关键词
                identified_domains.append(domain)
        
        return identified_domains
    
    def _identify_data_requirements(self, content: str) -> List[str]:
        """识别数据需求"""
        requirements = []
        
        # 数据源需求
        if re.search(r'数据库|表格|数据源', content):
            requirements.append("database_access")
        
        # 实时数据需求
        if re.search(r'实时|即时|当前', content):
            requirements.append("real_time_data")
        
        # 历史数据需求
        if re.search(r'历史|过去|趋势', content):
            requirements.append("historical_data")
        
        # 聚合数据需求
        if re.search(r'统计|汇总|聚合|合计', content):
            requirements.append("aggregated_data")
        
        return requirements
    
    def _identify_reporting_elements(self, content: str) -> List[str]:
        """识别报告元素"""
        elements = []
        
        for element_type, keywords in self.reporting_elements.items():
            if any(keyword in content for keyword in keywords):
                elements.append(element_type)
        
        return elements
    
    def _analyze_semantic_theme(self, title: str, content: str) -> str:
        """分析语义主题"""
        # 基于关键词频率分析主题
        combined_text = title + " " + content
        
        # 主题关键词
        themes = {
            "performance": ["绩效", "表现", "业绩", "成果", "效果"],
            "growth": ["增长", "发展", "提升", "改善", "进步"],
            "analysis": ["分析", "研究", "调查", "评估", "检查"],
            "planning": ["计划", "规划", "策略", "目标", "方案"],
            "comparison": ["对比", "比较", "差异", "变化", "区别"],
            "trend": ["趋势", "走势", "变化", "发展", "演变"]
        }
        
        theme_scores = {}
        for theme, keywords in themes.items():
            score = sum(combined_text.count(keyword) for keyword in keywords)
            if score > 0:
                theme_scores[theme] = score
        
        if theme_scores:
            return max(theme_scores, key=theme_scores.get)
        return "general"
    
    def _calculate_information_density(self, content: str) -> float:
        """计算信息密度"""
        total_chars = len(content)
        if total_chars == 0:
            return 0.0
        
        # 数值信息密度
        numbers = len(re.findall(r'\d+', content))
        
        # 占位符密度
        placeholders = len(re.findall(r'\{\{[^}]+\}\}', content))
        
        # 专业术语密度
        professional_terms = 0
        for domain_keywords in self.business_domains.values():
            professional_terms += sum(1 for keyword in domain_keywords if keyword in content)
        
        density = (numbers + placeholders * 2 + professional_terms) / total_chars * 100
        return min(1.0, density)
    
    def _analyze_analytical_complexity(self, content: str) -> float:
        """分析分析复杂度"""
        complexity_indicators = [
            ("统计", 0.3),
            ("分析", 0.2),
            ("对比", 0.2),
            ("趋势", 0.2),
            ("预测", 0.4),
            ("关联", 0.3),
            ("相关性", 0.4)
        ]
        
        total_complexity = 0.0
        for indicator, weight in complexity_indicators:
            count = content.count(indicator)
            total_complexity += count * weight
        
        # 归一化
        content_length = len(content)
        if content_length > 0:
            normalized_complexity = total_complexity / content_length * 100
            return min(1.0, normalized_complexity)
        
        return 0.0
    
    def _evaluate_narrative_flow(self, content: str) -> float:
        """评估叙述流畅度"""
        # 连接词使用情况
        connectors = ["因此", "所以", "然而", "但是", "另外", "此外", "同时", "接着"]
        connector_count = sum(content.count(conn) for conn in connectors)
        
        # 段落结构
        paragraphs = content.split('\n\n')
        avg_paragraph_length = sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0
        
        # 逻辑结构词
        logic_words = ["首先", "其次", "最后", "总之", "综上"]
        logic_count = sum(content.count(word) for word in logic_words)
        
        # 计算流畅度分数
        flow_score = (
            (connector_count / len(content) * 1000 if content else 0) * 0.4 +
            (1 - abs(avg_paragraph_length - 100) / 200) * 0.4 +  # 理想段落长度100字符
            (logic_count / len(paragraphs) if paragraphs else 0) * 0.2
        )
        
        return min(1.0, max(0.0, flow_score))
    
    def _identify_cross_references(self, content: str) -> List[str]:
        """识别交叉引用"""
        references = []
        
        # 章节引用
        section_refs = re.findall(r'第[一二三四五六七八九十\d]+[章节部分]', content)
        references.extend(section_refs)
        
        # 表格图表引用
        table_refs = re.findall(r'[表图]\s*\d+', content)
        references.extend(table_refs)
        
        # 附录引用
        appendix_refs = re.findall(r'附录[A-Z\d]+', content)
        references.extend(appendix_refs)
        
        return list(set(references))
    
    def _analyze_section_dependencies(self, 
                                    content: str, 
                                    preceding_sections: List[str] = None,
                                    following_sections: List[str] = None) -> List[int]:
        """分析章节依赖关系"""
        dependencies = []
        
        if preceding_sections:
            for i, section in enumerate(preceding_sections):
                # 检查是否引用了前面的章节内容
                if any(keyword in content for keyword in ["如前所述", "上述", "前面提到"]):
                    dependencies.append(i)
        
        return dependencies
    
    def _extract_key_concepts(self, content: str) -> List[str]:
        """提取关键概念"""
        concepts = []
        
        # 专业术语
        for domain_keywords in self.business_domains.values():
            concepts.extend([kw for kw in domain_keywords if kw in content])
        
        # 高频词汇
        words = re.findall(r'[\u4e00-\u9fff]{2,}', content)
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 取频率最高的概念
        high_freq_words = [word for word, freq in word_freq.items() if freq >= 3]
        concepts.extend(high_freq_words[:10])
        
        return list(set(concepts))
    
    def _analyze_data_flow_patterns(self, content: str) -> List[str]:
        """分析数据流模式"""
        patterns = []
        
        if re.search(r'输入|导入|读取', content):
            patterns.append("data_input")
        
        if re.search(r'处理|转换|计算', content):
            patterns.append("data_processing")
        
        if re.search(r'输出|导出|生成', content):
            patterns.append("data_output")
        
        if re.search(r'聚合|汇总|合并', content):
            patterns.append("data_aggregation")
        
        if re.search(r'筛选|过滤|查询', content):
            patterns.append("data_filtering")
        
        return patterns
    
    def _create_fallback_section_context(self, 
                                       title: str, 
                                       content: str, 
                                       section_index: int) -> SectionContext:
        """创建回退章节上下文"""
        structure = SectionStructure(
            section_index=section_index,
            title=title,
            level=1,
            paragraph_count=1,
            subsection_count=0,
            total_word_count=len(content),
            placeholder_count=0,
            section_type="general",
            business_domain=[],
            data_requirements=[],
            reporting_elements=[]
        )
        
        return SectionContext(
            structure=structure,
            semantic_theme="general",
            information_density=0.0,
            analytical_complexity=0.0,
            narrative_flow_score=0.5,
            cross_references=[],
            dependent_sections=[],
            key_concepts=[],
            data_flow_patterns=[]
        )
    
    def calculate_section_relevance(self, 
                                  section_context: SectionContext,
                                  placeholder_spec: PlaceholderSpec) -> float:
        """计算章节相关性权重"""
        weight = 0.0
        
        # 业务领域匹配
        placeholder_content = placeholder_spec.content.lower()
        domain_matches = 0
        for domain in section_context.structure.business_domain:
            if domain in placeholder_content:
                domain_matches += 1
        
        if section_context.structure.business_domain:
            weight += (domain_matches / len(section_context.structure.business_domain)) * 0.25
        
        # 章节类型相关性
        section_type = section_context.structure.section_type
        placeholder_type = getattr(placeholder_spec, 'statistical_type', '')
        
        type_relevance_map = {
            "analysis": ["统计", "分析", "对比"],
            "results": ["统计", "列表", "统计图"],
            "conclusion": ["统计", "对比"],
            "recommendations": ["预测", "趋势"]
        }
        
        if section_type in type_relevance_map:
            if placeholder_type in type_relevance_map[section_type]:
                weight += 0.2
        
        # 信息密度权重
        weight += section_context.information_density * 0.15
        
        # 分析复杂度权重
        weight += section_context.analytical_complexity * 0.15
        
        # 关键概念匹配
        concept_matches = 0
        for concept in section_context.key_concepts:
            if concept in placeholder_spec.content:
                concept_matches += 1
        
        if section_context.key_concepts:
            weight += (concept_matches / len(section_context.key_concepts)) * 0.25
        
        return min(1.0, weight)