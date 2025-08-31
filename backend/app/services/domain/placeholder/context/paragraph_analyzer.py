"""
段落分析器
分析段落级别的上下文信息
"""
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from ..models import PlaceholderSpec, DocumentContext

logger = logging.getLogger(__name__)

@dataclass
class ParagraphContext:
    """段落上下文信息"""
    paragraph_index: int
    text_content: str
    sentence_count: int
    word_count: int
    placeholder_density: float
    topic_keywords: List[str]
    sentiment_score: float
    complexity_score: float
    business_terms: List[str]
    temporal_references: List[str]
    numerical_patterns: List[str]
    preceding_context: Optional[str] = None
    following_context: Optional[str] = None

class ParagraphAnalyzer:
    """段落分析器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.business_terms = self._load_business_terms()
        self.temporal_patterns = self._compile_temporal_patterns()
        self.numerical_patterns = self._compile_numerical_patterns()
        
    def _load_business_terms(self) -> Dict[str, List[str]]:
        """加载业务术语库"""
        return {
            "financial": ["收入", "支出", "利润", "成本", "预算", "投资", "回报", "营收", "毛利", "净利"],
            "sales": ["销售额", "客户", "订单", "转化率", "市场份额", "渠道", "业绩", "目标", "增长"],
            "operational": ["效率", "质量", "产能", "库存", "供应链", "流程", "优化", "监控"],
            "analytics": ["统计", "分析", "趋势", "对比", "预测", "指标", "维度", "度量", "KPI"],
            "temporal": ["年度", "月度", "季度", "日报", "周报", "实时", "历史", "当前", "未来"]
        }
    
    def _compile_temporal_patterns(self) -> List[re.Pattern]:
        """编译时间模式"""
        patterns = [
            r'\d{4}年\d{1,2}月',
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'第[一二三四]季度',
            r'上半年|下半年',
            r'本月|上月|下月',
            r'今年|去年|明年',
            r'最近\d+[天月年]',
            r'过去\d+[天月年]'
        ]
        return [re.compile(pattern) for pattern in patterns]
    
    def _compile_numerical_patterns(self) -> List[re.Pattern]:
        """编译数值模式"""
        patterns = [
            r'\d+(?:\.\d+)?%',
            r'\d+(?:,\d{3})*(?:\.\d+)?',
            r'[+-]?\d+(?:\.\d+)?[万千亿]',
            r'\$\d+(?:,\d{3})*(?:\.\d+)?',
            r'￥\d+(?:,\d{3})*(?:\.\d+)?'
        ]
        return [re.compile(pattern) for pattern in patterns]
    
    def analyze_paragraph(self, 
                         text: str, 
                         paragraph_index: int,
                         document_context: DocumentContext,
                         preceding_text: Optional[str] = None,
                         following_text: Optional[str] = None) -> ParagraphContext:
        """分析段落上下文"""
        try:
            # 基础文本统计
            sentences = self._split_sentences(text)
            word_count = len(text.replace(' ', ''))
            
            # 占位符密度分析
            placeholder_density = self._calculate_placeholder_density(text)
            
            # 主题关键词提取
            topic_keywords = self._extract_topic_keywords(text)
            
            # 情感分析
            sentiment_score = self._analyze_sentiment(text)
            
            # 复杂度分析
            complexity_score = self._calculate_complexity(text, sentences)
            
            # 业务术语识别
            business_terms = self._identify_business_terms(text)
            
            # 时间引用识别
            temporal_references = self._extract_temporal_references(text)
            
            # 数值模式识别
            numerical_patterns = self._extract_numerical_patterns(text)
            
            return ParagraphContext(
                paragraph_index=paragraph_index,
                text_content=text,
                sentence_count=len(sentences),
                word_count=word_count,
                placeholder_density=placeholder_density,
                topic_keywords=topic_keywords,
                sentiment_score=sentiment_score,
                complexity_score=complexity_score,
                business_terms=business_terms,
                temporal_references=temporal_references,
                numerical_patterns=numerical_patterns,
                preceding_context=preceding_text,
                following_context=following_text
            )
            
        except Exception as e:
            logger.error(f"段落分析失败: {e}")
            return self._create_fallback_context(text, paragraph_index)
    
    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        # 简单的中文句子分割
        sentences = re.split(r'[。！？；]', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_placeholder_density(self, text: str) -> float:
        """计算占位符密度"""
        placeholder_pattern = re.compile(r'\{\{[^}]+\}\}')
        placeholders = placeholder_pattern.findall(text)
        total_chars = len(text)
        placeholder_chars = sum(len(p) for p in placeholders)
        
        return placeholder_chars / total_chars if total_chars > 0 else 0.0
    
    def _extract_topic_keywords(self, text: str) -> List[str]:
        """提取主题关键词"""
        keywords = []
        
        # 基于业务术语提取
        for category, terms in self.business_terms.items():
            for term in terms:
                if term in text:
                    keywords.append(term)
        
        # 提取高频词汇
        words = re.findall(r'[\u4e00-\u9fff]+', text)
        word_freq = {}
        for word in words:
            if len(word) >= 2:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 按频率排序，取前5个
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        keywords.extend([word for word, freq in top_words if freq > 1])
        
        return list(set(keywords))
    
    def _analyze_sentiment(self, text: str) -> float:
        """分析情感倾向"""
        # 简单的情感词典方法
        positive_words = ["增长", "提升", "改善", "优秀", "成功", "高效", "良好", "优化"]
        negative_words = ["下降", "减少", "问题", "困难", "失败", "低效", "糟糕", "恶化"]
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        total_words = len(text.replace(' ', ''))
        if total_words == 0:
            return 0.0
        
        sentiment = (positive_count - negative_count) / total_words * 100
        return max(-1.0, min(1.0, sentiment))
    
    def _calculate_complexity(self, text: str, sentences: List[str]) -> float:
        """计算复杂度分数"""
        if not sentences:
            return 0.0
        
        # 基于句子长度和嵌套结构
        avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)
        
        # 嵌套占位符检测
        nested_placeholders = re.findall(r'\{\{[^}]*\{\{[^}]*\}\}[^}]*\}\}', text)
        nesting_score = len(nested_placeholders) * 0.3
        
        # 复杂标点符号
        complex_punctuation = len(re.findall(r'[（）【】《》""''：；,]', text))
        punctuation_score = complex_punctuation / len(text) if text else 0
        
        complexity = (avg_sentence_length / 50 + nesting_score + punctuation_score) / 3
        return min(1.0, complexity)
    
    def _identify_business_terms(self, text: str) -> List[str]:
        """识别业务术语"""
        identified_terms = []
        for category, terms in self.business_terms.items():
            for term in terms:
                if term in text:
                    identified_terms.append(term)
        return list(set(identified_terms))
    
    def _extract_temporal_references(self, text: str) -> List[str]:
        """提取时间引用"""
        temporal_refs = []
        for pattern in self.temporal_patterns:
            matches = pattern.findall(text)
            temporal_refs.extend(matches)
        return list(set(temporal_refs))
    
    def _extract_numerical_patterns(self, text: str) -> List[str]:
        """提取数值模式"""
        numerical_patterns = []
        for pattern in self.numerical_patterns:
            matches = pattern.findall(text)
            numerical_patterns.extend(matches)
        return list(set(numerical_patterns))
    
    def _create_fallback_context(self, text: str, paragraph_index: int) -> ParagraphContext:
        """创建回退上下文"""
        return ParagraphContext(
            paragraph_index=paragraph_index,
            text_content=text,
            sentence_count=1,
            word_count=len(text),
            placeholder_density=0.0,
            topic_keywords=[],
            sentiment_score=0.0,
            complexity_score=0.0,
            business_terms=[],
            temporal_references=[],
            numerical_patterns=[]
        )
    
    def calculate_contextual_weight(self, 
                                  paragraph_context: ParagraphContext,
                                  placeholder_spec: PlaceholderSpec) -> float:
        """计算上下文权重"""
        weight = 0.0
        
        # 关键词匹配权重
        keyword_matches = 0
        for keyword in paragraph_context.topic_keywords:
            if keyword in placeholder_spec.content:
                keyword_matches += 1
        if paragraph_context.topic_keywords:
            weight += (keyword_matches / len(paragraph_context.topic_keywords)) * 0.3
        
        # 业务术语相关性权重
        business_relevance = 0
        placeholder_type = getattr(placeholder_spec, 'statistical_type', '')
        if placeholder_type in ['统计', '统计图']:
            for term in paragraph_context.business_terms:
                if term in ["统计", "分析", "指标", "度量"]:
                    business_relevance += 0.1
        
        weight += min(business_relevance, 0.3)
        
        # 占位符密度权重
        weight += paragraph_context.placeholder_density * 0.2
        
        # 复杂度调节
        if paragraph_context.complexity_score > 0.7:
            weight += 0.1
        
        # 时间相关性权重
        if paragraph_context.temporal_references and '时间' in placeholder_spec.content:
            weight += 0.1
        
        return min(1.0, weight)