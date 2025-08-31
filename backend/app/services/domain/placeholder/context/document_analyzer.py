"""
文档分析器
分析整个文档的结构、主题和全局上下文
"""
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import Counter
from ..models import PlaceholderSpec, DocumentContext

logger = logging.getLogger(__name__)

@dataclass
class DocumentStructure:
    """文档结构信息"""
    total_sections: int
    max_depth: int
    section_hierarchy: Dict[int, List[str]]
    toc_structure: List[Dict[str, Any]]
    document_flow: List[str]
    structural_patterns: List[str]

@dataclass
class DocumentMetrics:
    """文档度量信息"""
    total_word_count: int
    total_placeholder_count: int
    placeholder_distribution: Dict[str, int]
    section_balance_score: float
    content_density_variance: float
    readability_score: float
    coherence_score: float

@dataclass
class DocumentTheme:
    """文档主题信息"""
    primary_theme: str
    secondary_themes: List[str]
    business_focus_areas: List[str]
    document_purpose: str
    target_audience: str
    reporting_scope: str

@dataclass
class GlobalDocumentContext:
    """全局文档上下文"""
    structure: DocumentStructure
    metrics: DocumentMetrics
    theme: DocumentTheme
    global_concepts: List[str]
    cross_section_relationships: Dict[str, List[str]]
    data_dependencies: Dict[str, List[str]]
    narrative_arc: List[str]

class DocumentAnalyzer:
    """文档分析器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.document_types = self._define_document_types()
        self.narrative_patterns = self._define_narrative_patterns()
        
    def _define_document_types(self) -> Dict[str, Dict[str, Any]]:
        """定义文档类型特征"""
        return {
            "annual_report": {
                "structure": ["摘要", "业务概述", "财务分析", "风险评估", "展望"],
                "focus": ["财务", "业绩", "战略"],
                "audience": "stakeholders"
            },
            "monthly_report": {
                "structure": ["概要", "关键指标", "运营分析", "问题与建议"],
                "focus": ["运营", "指标", "趋势"],
                "audience": "management"
            },
            "project_report": {
                "structure": ["项目概述", "进度报告", "风险分析", "下步计划"],
                "focus": ["项目", "进度", "风险"],
                "audience": "project_team"
            },
            "analysis_report": {
                "structure": ["问题定义", "数据分析", "发现洞察", "建议措施"],
                "focus": ["数据", "分析", "洞察"],
                "audience": "analysts"
            },
            "dashboard_report": {
                "structure": ["核心指标", "趋势分析", "异常监控", "行动建议"],
                "focus": ["指标", "监控", "实时"],
                "audience": "operators"
            }
        }
    
    def _define_narrative_patterns(self) -> Dict[str, List[str]]:
        """定义叙述模式"""
        return {
            "problem_solution": ["问题识别", "原因分析", "解决方案", "实施计划"],
            "temporal_analysis": ["历史回顾", "现状分析", "趋势预测", "未来规划"],
            "comparative_study": ["基线建立", "对比分析", "差异识别", "改进建议"],
            "performance_review": ["目标设定", "执行过程", "结果评估", "持续改进"],
            "strategic_planning": ["环境分析", "战略制定", "资源配置", "执行监控"]
        }
    
    def analyze_document(self, 
                        sections: List[Dict[str, str]], 
                        document_context: DocumentContext) -> GlobalDocumentContext:
        """分析整个文档的全局上下文"""
        try:
            # 分析文档结构
            structure = self._analyze_document_structure(sections)
            
            # 计算文档度量
            metrics = self._calculate_document_metrics(sections)
            
            # 分析文档主题
            theme = self._analyze_document_theme(sections, document_context)
            
            # 提取全局概念
            global_concepts = self._extract_global_concepts(sections)
            
            # 分析跨章节关系
            cross_section_relationships = self._analyze_cross_section_relationships(sections)
            
            # 分析数据依赖
            data_dependencies = self._analyze_data_dependencies(sections)
            
            # 构建叙述弧线
            narrative_arc = self._build_narrative_arc(sections, structure)
            
            return GlobalDocumentContext(
                structure=structure,
                metrics=metrics,
                theme=theme,
                global_concepts=global_concepts,
                cross_section_relationships=cross_section_relationships,
                data_dependencies=data_dependencies,
                narrative_arc=narrative_arc
            )
            
        except Exception as e:
            logger.error(f"文档分析失败: {e}")
            return self._create_fallback_document_context(sections)
    
    def _analyze_document_structure(self, sections: List[Dict[str, str]]) -> DocumentStructure:
        """分析文档结构"""
        total_sections = len(sections)
        
        # 分析标题层级
        hierarchy = {}
        max_depth = 0
        toc_structure = []
        
        for i, section in enumerate(sections):
            title = section.get("title", "")
            level = self._determine_title_level(title)
            max_depth = max(max_depth, level)
            
            if level not in hierarchy:
                hierarchy[level] = []
            hierarchy[level].append(title)
            
            toc_structure.append({
                "index": i,
                "title": title,
                "level": level,
                "word_count": len(section.get("content", ""))
            })
        
        # 分析文档流程
        document_flow = [section.get("title", f"Section {i}") for i, section in enumerate(sections)]
        
        # 识别结构模式
        structural_patterns = self._identify_structural_patterns(sections)
        
        return DocumentStructure(
            total_sections=total_sections,
            max_depth=max_depth,
            section_hierarchy=hierarchy,
            toc_structure=toc_structure,
            document_flow=document_flow,
            structural_patterns=structural_patterns
        )
    
    def _calculate_document_metrics(self, sections: List[Dict[str, str]]) -> DocumentMetrics:
        """计算文档度量"""
        total_word_count = 0
        total_placeholder_count = 0
        placeholder_types = Counter()
        section_lengths = []
        
        for section in sections:
            content = section.get("content", "")
            words = len(content)
            total_word_count += words
            section_lengths.append(words)
            
            # 统计占位符
            placeholders = re.findall(r'\{\{([^}]+)\}\}', content)
            total_placeholder_count += len(placeholders)
            
            # 分类占位符类型
            for placeholder in placeholders:
                placeholder_type = self._classify_placeholder_type(placeholder)
                placeholder_types[placeholder_type] += 1
        
        # 计算章节平衡分数
        if section_lengths:
            avg_length = sum(section_lengths) / len(section_lengths)
            variance = sum((length - avg_length) ** 2 for length in section_lengths) / len(section_lengths)
            balance_score = max(0, 1 - (variance ** 0.5) / avg_length) if avg_length > 0 else 0
        else:
            balance_score = 0
        
        # 计算内容密度方差
        content_densities = []
        for section in sections:
            content = section.get("content", "")
            density = len(re.findall(r'[\u4e00-\u9fff]', content)) / len(content) if content else 0
            content_densities.append(density)
        
        density_variance = sum((d - sum(content_densities) / len(content_densities)) ** 2 
                             for d in content_densities) / len(content_densities) if content_densities else 0
        
        # 计算可读性分数
        readability_score = self._calculate_readability_score(sections)
        
        # 计算连贯性分数
        coherence_score = self._calculate_coherence_score(sections)
        
        return DocumentMetrics(
            total_word_count=total_word_count,
            total_placeholder_count=total_placeholder_count,
            placeholder_distribution=dict(placeholder_types),
            section_balance_score=balance_score,
            content_density_variance=density_variance,
            readability_score=readability_score,
            coherence_score=coherence_score
        )
    
    def _analyze_document_theme(self, 
                               sections: List[Dict[str, str]], 
                               document_context: DocumentContext) -> DocumentTheme:
        """分析文档主题"""
        all_content = " ".join([section.get("content", "") for section in sections])
        all_titles = " ".join([section.get("title", "") for section in sections])
        combined_text = all_titles + " " + all_content
        
        # 识别主要主题
        primary_theme = self._identify_primary_theme(combined_text)
        
        # 识别次要主题
        secondary_themes = self._identify_secondary_themes(combined_text)
        
        # 识别业务焦点领域
        business_focus_areas = self._identify_business_focus_areas(combined_text)
        
        # 确定文档目的
        document_purpose = self._determine_document_purpose(sections)
        
        # 识别目标受众
        target_audience = self._identify_target_audience(combined_text, document_purpose)
        
        # 确定报告范围
        reporting_scope = self._determine_reporting_scope(combined_text)
        
        return DocumentTheme(
            primary_theme=primary_theme,
            secondary_themes=secondary_themes,
            business_focus_areas=business_focus_areas,
            document_purpose=document_purpose,
            target_audience=target_audience,
            reporting_scope=reporting_scope
        )
    
    def _determine_title_level(self, title: str) -> int:
        """确定标题级别"""
        if title.startswith('#'):
            return len(title) - len(title.lstrip('#'))
        
        # 基于内容判断
        if any(keyword in title for keyword in ["第", "章", "部分"]):
            return 1
        elif any(keyword in title for keyword in ["节", "小节"]):
            return 2
        elif any(keyword in title for keyword in ["项", "条"]):
            return 3
        else:
            return 2  # 默认级别
    
    def _identify_structural_patterns(self, sections: List[Dict[str, str]]) -> List[str]:
        """识别结构模式"""
        patterns = []
        titles = [section.get("title", "").lower() for section in sections]
        
        # 检查标准报告结构
        for doc_type, definition in self.document_types.items():
            structure_keywords = definition["structure"]
            matches = sum(1 for keyword in structure_keywords 
                         if any(keyword.lower() in title for title in titles))
            
            if matches >= len(structure_keywords) * 0.6:  # 60%匹配度
                patterns.append(doc_type)
        
        # 检查叙述模式
        for narrative_type, stages in self.narrative_patterns.items():
            stage_matches = sum(1 for stage in stages
                              if any(stage.lower() in title for title in titles))
            
            if stage_matches >= len(stages) * 0.5:  # 50%匹配度
                patterns.append(narrative_type)
        
        return patterns if patterns else ["custom_structure"]
    
    def _classify_placeholder_type(self, placeholder: str) -> str:
        """分类占位符类型"""
        if ":" in placeholder or "：" in placeholder:
            return "parameterized"
        elif "|" in placeholder:
            return "composite"
        elif any(op in placeholder for op in ["==", "!=", ">", "<"]):
            return "conditional"
        else:
            return "basic"
    
    def _calculate_readability_score(self, sections: List[Dict[str, str]]) -> float:
        """计算可读性分数"""
        total_score = 0
        total_sections = len(sections)
        
        if total_sections == 0:
            return 0.0
        
        for section in sections:
            content = section.get("content", "")
            if not content:
                continue
            
            # 句子平均长度
            sentences = re.split(r'[。！？]', content)
            sentences = [s.strip() for s in sentences if s.strip()]
            avg_sentence_length = sum(len(s) for s in sentences) / len(sentences) if sentences else 0
            
            # 复杂词汇比例
            words = re.findall(r'[\u4e00-\u9fff]+', content)
            complex_words = [w for w in words if len(w) > 4]
            complex_ratio = len(complex_words) / len(words) if words else 0
            
            # 标点符号多样性
            punctuation = re.findall(r'[，。；：！？""''（）【】]', content)
            punct_diversity = len(set(punctuation)) / 10 if punctuation else 0
            
            # 综合可读性分数
            readability = (
                min(1.0, (50 - avg_sentence_length) / 50) * 0.4 +  # 理想句长50字符
                (1 - min(1.0, complex_ratio)) * 0.4 +
                min(1.0, punct_diversity) * 0.2
            )
            
            total_score += readability
        
        return total_score / total_sections
    
    def _calculate_coherence_score(self, sections: List[Dict[str, str]]) -> float:
        """计算连贯性分数"""
        if len(sections) < 2:
            return 1.0
        
        coherence_scores = []
        
        for i in range(len(sections) - 1):
            current_content = sections[i].get("content", "")
            next_content = sections[i + 1].get("content", "")
            
            # 词汇重叠度
            current_words = set(re.findall(r'[\u4e00-\u9fff]+', current_content))
            next_words = set(re.findall(r'[\u4e00-\u9fff]+', next_content))
            
            if current_words and next_words:
                overlap = len(current_words & next_words) / len(current_words | next_words)
                coherence_scores.append(overlap)
        
        return sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0
    
    def _identify_primary_theme(self, text: str) -> str:
        """识别主要主题"""
        theme_keywords = {
            "financial": ["财务", "资金", "收入", "利润", "成本", "预算", "投资"],
            "operational": ["运营", "生产", "效率", "质量", "流程", "管理"],
            "strategic": ["战略", "规划", "发展", "目标", "增长", "竞争"],
            "analytical": ["分析", "数据", "统计", "趋势", "预测", "洞察"],
            "performance": ["绩效", "表现", "业绩", "成果", "KPI", "指标"]
        }
        
        theme_scores = {}
        for theme, keywords in theme_keywords.items():
            score = sum(text.count(keyword) for keyword in keywords)
            if score > 0:
                theme_scores[theme] = score
        
        if theme_scores:
            return max(theme_scores, key=theme_scores.get)
        return "general"
    
    def _identify_secondary_themes(self, text: str) -> List[str]:
        """识别次要主题"""
        theme_keywords = {
            "technology": ["技术", "系统", "软件", "数据库", "网络"],
            "market": ["市场", "客户", "竞争", "份额", "渠道"],
            "risk": ["风险", "合规", "安全", "控制", "审计"],
            "innovation": ["创新", "研发", "产品", "服务", "改进"],
            "sustainability": ["可持续", "环保", "社会责任", "ESG"]
        }
        
        secondary_themes = []
        for theme, keywords in theme_keywords.items():
            score = sum(text.count(keyword) for keyword in keywords)
            if score >= 2:  # 至少出现2次相关词汇
                secondary_themes.append(theme)
        
        return secondary_themes
    
    def _identify_business_focus_areas(self, text: str) -> List[str]:
        """识别业务焦点领域"""
        focus_areas = {
            "sales": ["销售", "营收", "客户获取", "市场拓展"],
            "customer_service": ["客户服务", "满意度", "体验", "支持"],
            "product_development": ["产品开发", "研发", "创新", "设计"],
            "supply_chain": ["供应链", "采购", "物流", "库存"],
            "human_resources": ["人力资源", "员工", "培训", "招聘"],
            "finance": ["财务管理", "成本控制", "资金", "预算"]
        }
        
        identified_areas = []
        for area, keywords in focus_areas.items():
            if any(keyword in text for keyword in keywords):
                identified_areas.append(area)
        
        return identified_areas
    
    def _determine_document_purpose(self, sections: List[Dict[str, str]]) -> str:
        """确定文档目的"""
        all_titles = " ".join([section.get("title", "") for section in sections]).lower()
        
        purpose_indicators = {
            "monitoring": ["监控", "跟踪", "观察", "检查"],
            "analysis": ["分析", "研究", "评估", "调查"],
            "reporting": ["报告", "汇报", "总结", "回顾"],
            "planning": ["计划", "规划", "策略", "方案"],
            "evaluation": ["评价", "考核", "审查", "检讨"]
        }
        
        for purpose, indicators in purpose_indicators.items():
            if any(indicator in all_titles for indicator in indicators):
                return purpose
        
        return "general_reporting"
    
    def _identify_target_audience(self, text: str, purpose: str) -> str:
        """识别目标受众"""
        audience_indicators = {
            "executives": ["高管", "领导", "决策", "战略"],
            "managers": ["管理", "主管", "负责人", "团队"],
            "analysts": ["分析师", "数据", "统计", "研究"],
            "stakeholders": ["股东", "投资者", "利益相关者"],
            "operators": ["操作", "执行", "实施", "运营"]
        }
        
        # 基于目的推断受众
        purpose_to_audience = {
            "monitoring": "operators",
            "analysis": "analysts", 
            "reporting": "managers",
            "planning": "executives",
            "evaluation": "stakeholders"
        }
        
        # 首先基于目的推断
        if purpose in purpose_to_audience:
            default_audience = purpose_to_audience[purpose]
        else:
            default_audience = "general"
        
        # 基于内容关键词确认
        for audience, indicators in audience_indicators.items():
            if any(indicator in text for indicator in indicators):
                return audience
        
        return default_audience
    
    def _determine_reporting_scope(self, text: str) -> str:
        """确定报告范围"""
        scope_indicators = {
            "enterprise": ["公司", "企业", "集团", "全集团"],
            "department": ["部门", "事业部", "分部"],
            "project": ["项目", "工程", "计划"],
            "product": ["产品", "服务", "业务线"],
            "regional": ["地区", "区域", "分公司", "子公司"]
        }
        
        for scope, indicators in scope_indicators.items():
            if any(indicator in text for indicator in indicators):
                return scope
        
        return "general"
    
    def _extract_global_concepts(self, sections: List[Dict[str, str]]) -> List[str]:
        """提取全局概念"""
        all_content = " ".join([section.get("content", "") for section in sections])
        
        # 提取高频专业术语
        words = re.findall(r'[\u4e00-\u9fff]{2,}', all_content)
        word_freq = Counter(words)
        
        # 过滤常用词
        common_words = {"我们", "公司", "业务", "工作", "情况", "方面", "进行", "实现", "通过", "主要"}
        professional_terms = [word for word, freq in word_freq.most_common(20) 
                             if freq >= 3 and word not in common_words]
        
        return professional_terms[:10]
    
    def _analyze_cross_section_relationships(self, sections: List[Dict[str, str]]) -> Dict[str, List[str]]:
        """分析跨章节关系"""
        relationships = {}
        
        for i, section in enumerate(sections):
            section_title = section.get("title", f"Section {i}")
            content = section.get("content", "")
            related_sections = []
            
            # 查找明确的引用
            references = re.findall(r'第[一二三四五六七八九十\d]+[章节部分]', content)
            related_sections.extend(references)
            
            # 查找概念重叠
            current_concepts = set(re.findall(r'[\u4e00-\u9fff]{3,}', content))
            
            for j, other_section in enumerate(sections):
                if i != j:
                    other_content = other_section.get("content", "")
                    other_concepts = set(re.findall(r'[\u4e00-\u9fff]{3,}', other_content))
                    
                    # 计算概念重叠度
                    if current_concepts and other_concepts:
                        overlap = len(current_concepts & other_concepts) / len(current_concepts)
                        if overlap > 0.3:  # 30%重叠度
                            other_title = other_section.get("title", f"Section {j}")
                            related_sections.append(other_title)
            
            if related_sections:
                relationships[section_title] = list(set(related_sections))
        
        return relationships
    
    def _analyze_data_dependencies(self, sections: List[Dict[str, str]]) -> Dict[str, List[str]]:
        """分析数据依赖关系"""
        dependencies = {}
        
        for section in sections:
            title = section.get("title", "")
            content = section.get("content", "")
            section_deps = []
            
            # 识别数据源需求
            if re.search(r'数据库|表格|数据源', content):
                section_deps.append("database")
            
            if re.search(r'API|接口|服务', content):
                section_deps.append("api")
            
            if re.search(r'文件|导入|Excel', content):
                section_deps.append("file_import")
            
            # 识别计算依赖
            if re.search(r'计算|统计|聚合', content):
                section_deps.append("computation")
            
            if re.search(r'前面|上述|之前', content):
                section_deps.append("previous_sections")
            
            if section_deps:
                dependencies[title] = section_deps
        
        return dependencies
    
    def _build_narrative_arc(self, 
                           sections: List[Dict[str, str]], 
                           structure: DocumentStructure) -> List[str]:
        """构建叙述弧线"""
        arc = []
        
        # 基于结构模式确定叙述弧线
        if "problem_solution" in structure.structural_patterns:
            arc = ["问题阐述", "原因分析", "解决探索", "方案实施", "效果评估"]
        elif "temporal_analysis" in structure.structural_patterns:
            arc = ["历史背景", "现状分析", "趋势识别", "未来预测"]
        elif "performance_review" in structure.structural_patterns:
            arc = ["目标回顾", "执行跟踪", "成果展示", "差距分析", "改进计划"]
        else:
            # 基于实际章节内容构建
            for section in sections:
                title = section.get("title", "")
                if any(keyword in title for keyword in ["概述", "介绍", "背景"]):
                    arc.append("背景介绍")
                elif any(keyword in title for keyword in ["分析", "研究", "调查"]):
                    arc.append("深入分析")
                elif any(keyword in title for keyword in ["结果", "发现", "数据"]):
                    arc.append("结果展示")
                elif any(keyword in title for keyword in ["结论", "总结", "建议"]):
                    arc.append("结论总结")
        
        return arc if arc else ["信息展示", "数据分析", "洞察总结"]
    
    def _create_fallback_document_context(self, sections: List[Dict[str, str]]) -> GlobalDocumentContext:
        """创建回退文档上下文"""
        structure = DocumentStructure(
            total_sections=len(sections),
            max_depth=1,
            section_hierarchy={1: [f"Section {i}" for i in range(len(sections))]},
            toc_structure=[],
            document_flow=[f"Section {i}" for i in range(len(sections))],
            structural_patterns=["custom_structure"]
        )
        
        metrics = DocumentMetrics(
            total_word_count=sum(len(s.get("content", "")) for s in sections),
            total_placeholder_count=0,
            placeholder_distribution={},
            section_balance_score=0.5,
            content_density_variance=0.0,
            readability_score=0.5,
            coherence_score=0.5
        )
        
        theme = DocumentTheme(
            primary_theme="general",
            secondary_themes=[],
            business_focus_areas=[],
            document_purpose="general_reporting",
            target_audience="general",
            reporting_scope="general"
        )
        
        return GlobalDocumentContext(
            structure=structure,
            metrics=metrics,
            theme=theme,
            global_concepts=[],
            cross_section_relationships={},
            data_dependencies={},
            narrative_arc=["信息展示"]
        )
    
    def calculate_document_level_weight(self, 
                                      document_context: GlobalDocumentContext,
                                      placeholder_spec: PlaceholderSpec) -> float:
        """计算文档级别权重"""
        weight = 0.0
        
        # 主题相关性权重
        placeholder_content = placeholder_spec.content.lower()
        if document_context.theme.primary_theme in placeholder_content:
            weight += 0.3
        
        # 业务领域匹配权重
        focus_matches = sum(1 for area in document_context.theme.business_focus_areas
                           if area in placeholder_content)
        if document_context.theme.business_focus_areas:
            weight += (focus_matches / len(document_context.theme.business_focus_areas)) * 0.2
        
        # 全局概念匹配权重
        concept_matches = sum(1 for concept in document_context.global_concepts
                             if concept in placeholder_spec.content)
        if document_context.global_concepts:
            weight += (concept_matches / len(document_context.global_concepts)) * 0.2
        
        # 文档目的相关性
        placeholder_type = getattr(placeholder_spec, 'statistical_type', '')
        purpose = document_context.theme.document_purpose
        
        purpose_type_map = {
            "monitoring": ["统计", "列表", "统计图"],
            "analysis": ["分析", "对比", "趋势"],
            "planning": ["预测", "趋势"],
            "evaluation": ["统计", "对比"]
        }
        
        if purpose in purpose_type_map and placeholder_type in purpose_type_map[purpose]:
            weight += 0.2
        
        # 结构复杂度调节
        if document_context.structure.max_depth > 3:
            weight += 0.05
        
        # 连贯性加成
        weight += document_context.metrics.coherence_score * 0.05
        
        return min(1.0, weight)