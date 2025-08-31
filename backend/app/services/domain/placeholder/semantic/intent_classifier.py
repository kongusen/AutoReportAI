"""
意图分类器

识别占位符表达的业务意图和统计需求
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from ..models import StatisticalType, DocumentContext

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """意图类型枚举"""
    DATA_AGGREGATION = "data_aggregation"        # 数据聚合
    TREND_ANALYSIS = "trend_analysis"            # 趋势分析
    RANKING_ANALYSIS = "ranking_analysis"        # 排名分析
    COMPARISON_ANALYSIS = "comparison_analysis"   # 对比分析
    EXTREME_VALUE = "extreme_value"              # 极值分析
    FORECASTING = "forecasting"                  # 预测分析
    VISUALIZATION = "visualization"              # 可视化需求
    CONDITIONAL_ANALYSIS = "conditional_analysis" # 条件分析


class BusinessDomain(Enum):
    """业务领域枚举"""
    SALES = "sales"           # 销售
    FINANCE = "finance"       # 财务
    MARKETING = "marketing"   # 营销
    OPERATIONS = "operations" # 运营
    HR = "human_resources"    # 人力资源
    GENERAL = "general"       # 通用


class IntentClassifier:
    """意图分类器"""
    
    def __init__(self):
        # 意图识别规则
        self.intent_patterns = {
            IntentType.DATA_AGGREGATION: {
                'keywords': [
                    '总和', '总计', '合计', '汇总', '统计', '计算', '求和',
                    '平均', '平均值', '均值', '数量', '个数', '计数'
                ],
                'patterns': [
                    r'总\w*[额值量]',
                    r'平均\w*',
                    r'\w*统计',
                    r'\w*数量'
                ],
                'statistical_type': StatisticalType.STATISTICS
            },
            
            IntentType.TREND_ANALYSIS: {
                'keywords': [
                    '趋势', '变化', '增长', '下降', '上升', '波动', '发展',
                    '同比', '环比', '增长率', '变化率', '走势'
                ],
                'patterns': [
                    r'\w*增长\w*',
                    r'\w*趋势',
                    r'\w*变化',
                    r'(同比|环比)\w*'
                ],
                'statistical_type': StatisticalType.TREND
            },
            
            IntentType.RANKING_ANALYSIS: {
                'keywords': [
                    '排名', '排行', '第一', '第二', '最好', '最差', '前几',
                    'TOP', 'top', '名次', '排序', '前十', '前五'
                ],
                'patterns': [
                    r'(前|后)\d*[名个位]',
                    r'TOP\s*\d*',
                    r'\w*排[名行]',
                    r'第\d+',
                    r'最[好差高低大小]'
                ],
                'statistical_type': StatisticalType.LIST
            },
            
            IntentType.COMPARISON_ANALYSIS: {
                'keywords': [
                    '对比', '比较', '差异', '差别', '相比', '比率', '比例',
                    '占比', '份额', '百分比', '相对', '绝对'
                ],
                'patterns': [
                    r'\w*对比\w*',
                    r'\w*比较\w*',
                    r'\w*占\w*比例',
                    r'\w*份额',
                    r'\w*比率'
                ],
                'statistical_type': StatisticalType.COMPARISON
            },
            
            IntentType.EXTREME_VALUE: {
                'keywords': [
                    '最大', '最小', '最高', '最低', '极值', '极大', '极小',
                    '峰值', '谷值', '异常', '突出', '特殊'
                ],
                'patterns': [
                    r'最[大小高低多少]',
                    r'极[大小高低值]',
                    r'\w*峰值',
                    r'\w*异常\w*'
                ],
                'statistical_type': StatisticalType.EXTREME
            },
            
            IntentType.FORECASTING: {
                'keywords': [
                    '预测', '预估', '预期', '预判', '趋势预测', '未来',
                    '预计', '展望', '预见', '估算'
                ],
                'patterns': [
                    r'预[测估期计判]',
                    r'未来\w*',
                    r'\w*预测\w*',
                    r'\w*展望\w*'
                ],
                'statistical_type': StatisticalType.FORECAST
            },
            
            IntentType.VISUALIZATION: {
                'keywords': [
                    '图表', '图形', '柱状图', '折线图', '饼图', '散点图',
                    '条形图', '面积图', '可视化', '展示'
                ],
                'patterns': [
                    r'\w*图[表形]?',
                    r'\w*可视化',
                    r'图形\w*展示'
                ],
                'statistical_type': StatisticalType.CHART
            },
            
            IntentType.CONDITIONAL_ANALYSIS: {
                'keywords': [
                    '如果', '当', '满足', '条件', '筛选', '过滤',
                    '符合', '达到', '超过', '低于', '等于'
                ],
                'patterns': [
                    r'如果\w*',
                    r'当\w*时',
                    r'满足\w*条件',
                    r'\w*筛选\w*',
                    r'(超过|低于|等于)\w*'
                ],
                'statistical_type': StatisticalType.STATISTICS
            }
        }
        
        # 业务领域识别规则
        self.domain_patterns = {
            BusinessDomain.SALES: {
                'keywords': [
                    '销售', '营收', '收入', '业绩', '成交', '订单', '客户',
                    '合同', '回款', '提成', '目标', '完成率'
                ]
            },
            BusinessDomain.FINANCE: {
                'keywords': [
                    '财务', '利润', '成本', '费用', '预算', '现金流',
                    '资产', '负债', '净利润', '毛利率', '投资回报'
                ]
            },
            BusinessDomain.MARKETING: {
                'keywords': [
                    '营销', '推广', '活动', '转化', '点击', '曝光',
                    '获客', '留存', '用户', '流量', '渠道'
                ]
            },
            BusinessDomain.OPERATIONS: {
                'keywords': [
                    '运营', '生产', '库存', '供应链', '物流', '配送',
                    '效率', '质量', '产能', '良品率', '周转率'
                ]
            },
            BusinessDomain.HR: {
                'keywords': [
                    '人力资源', '员工', '人员', '薪资', '绩效', '考勤',
                    '招聘', '培训', '离职率', '满意度', '团队'
                ]
            }
        }
    
    async def classify_intent(
        self,
        placeholder_text: str,
        context: Optional[DocumentContext] = None
    ) -> Dict[str, Any]:
        """分类占位符意图"""
        try:
            # 提取文本内容进行分析
            description = self._extract_description(placeholder_text)
            
            # 意图分类
            intent_scores = await self._calculate_intent_scores(description)
            primary_intent, primary_score = max(intent_scores.items(), key=lambda x: x[1])
            
            # 业务领域识别
            domain_scores = await self._calculate_domain_scores(description, context)
            primary_domain, domain_score = max(domain_scores.items(), key=lambda x: x[1])
            
            # 置信度计算
            confidence = self._calculate_confidence(primary_score, domain_score)
            
            # 推断统计类型
            suggested_stat_type = self.intent_patterns[primary_intent]['statistical_type']
            
            return {
                'intent_type': primary_intent.value,
                'confidence': confidence,
                'business_domain': primary_domain.value,
                'domain_confidence': domain_score,
                'statistical_type': suggested_stat_type,
                'all_intent_scores': {k.value: v for k, v in intent_scores.items()},
                'all_domain_scores': {k.value: v for k, v in domain_scores.items()},
                'reasoning': self._generate_reasoning(
                    primary_intent, primary_score, primary_domain, domain_score
                )
            }
            
        except Exception as e:
            logger.error(f"意图分类失败: {placeholder_text}, 错误: {e}")
            return self._get_default_classification()
    
    def _extract_description(self, placeholder_text: str) -> str:
        """从占位符中提取描述文本"""
        # 移除占位符语法标记
        text = placeholder_text.strip()
        if text.startswith('{{') and text.endswith('}}'):
            text = text[2:-2]
        
        # 提取冒号后的描述部分
        if '：' in text:
            parts = text.split('：', 1)
            if len(parts) > 1:
                description = parts[1].split('|')[0]  # 移除参数部分
                return description.strip()
        
        return text
    
    async def _calculate_intent_scores(self, description: str) -> Dict[IntentType, float]:
        """计算各种意图的匹配分数"""
        scores = {}
        
        for intent_type, rules in self.intent_patterns.items():
            score = 0.0
            
            # 关键词匹配
            for keyword in rules['keywords']:
                if keyword in description:
                    score += 1.0
            
            # 模式匹配
            for pattern in rules['patterns']:
                if re.search(pattern, description):
                    score += 1.5  # 模式匹配权重更高
            
            # 归一化分数
            max_possible = len(rules['keywords']) + len(rules['patterns']) * 1.5
            scores[intent_type] = score / max_possible if max_possible > 0 else 0.0
        
        return scores
    
    async def _calculate_domain_scores(
        self,
        description: str,
        context: Optional[DocumentContext] = None
    ) -> Dict[BusinessDomain, float]:
        """计算业务领域匹配分数"""
        scores = {}
        
        for domain, rules in self.domain_patterns.items():
            score = 0.0
            
            # 描述文本中的关键词匹配
            for keyword in rules['keywords']:
                if keyword in description:
                    score += 1.0
            
            # 上下文信息加权
            if context:
                context_text = f"{context.paragraph_content} {context.section_title}"
                for keyword in rules['keywords']:
                    if keyword in context_text:
                        score += 0.5  # 上下文匹配权重较低
            
            # 归一化分数
            max_possible = len(rules['keywords'])
            if context:
                max_possible += len(rules['keywords']) * 0.5
            
            scores[domain] = score / max_possible if max_possible > 0 else 0.0
        
        # 如果没有明确的领域匹配，给通用领域一个基础分数
        if all(score < 0.1 for score in scores.values()):
            scores[BusinessDomain.GENERAL] = 0.5
        
        return scores
    
    def _calculate_confidence(self, intent_score: float, domain_score: float) -> float:
        """计算分类置信度"""
        # 综合意图和领域分数
        base_confidence = (intent_score * 0.7 + domain_score * 0.3)
        
        # 应用置信度调整
        if base_confidence > 0.8:
            return min(base_confidence * 1.1, 1.0)
        elif base_confidence < 0.3:
            return max(base_confidence * 0.8, 0.1)
        else:
            return base_confidence
    
    def _generate_reasoning(
        self,
        intent: IntentType,
        intent_score: float,
        domain: BusinessDomain,
        domain_score: float
    ) -> str:
        """生成分类推理说明"""
        reasoning_parts = []
        
        # 意图推理
        if intent_score > 0.7:
            reasoning_parts.append(f"强匹配{intent.value}意图(分数:{intent_score:.2f})")
        elif intent_score > 0.4:
            reasoning_parts.append(f"中等匹配{intent.value}意图(分数:{intent_score:.2f})")
        else:
            reasoning_parts.append(f"弱匹配{intent.value}意图(分数:{intent_score:.2f})")
        
        # 领域推理
        if domain_score > 0.6:
            reasoning_parts.append(f"明确识别为{domain.value}领域")
        elif domain_score > 0.3:
            reasoning_parts.append(f"可能属于{domain.value}领域")
        else:
            reasoning_parts.append("领域不明确")
        
        return "；".join(reasoning_parts)
    
    def _get_default_classification(self) -> Dict[str, Any]:
        """获取默认分类结果"""
        return {
            'intent_type': IntentType.DATA_AGGREGATION.value,
            'confidence': 0.3,
            'business_domain': BusinessDomain.GENERAL.value,
            'domain_confidence': 0.2,
            'statistical_type': StatisticalType.STATISTICS,
            'all_intent_scores': {},
            'all_domain_scores': {},
            'reasoning': "分类失败，使用默认设置"
        }
    
    def get_intent_suggestions(self, partial_description: str) -> List[Dict[str, Any]]:
        """基于部分描述获取意图建议"""
        suggestions = []
        
        # 计算各意图的部分匹配分数
        for intent_type, rules in self.intent_patterns.items():
            score = 0
            matched_keywords = []
            
            for keyword in rules['keywords']:
                if keyword in partial_description:
                    score += 1
                    matched_keywords.append(keyword)
            
            if score > 0:
                suggestions.append({
                    'intent_type': intent_type.value,
                    'statistical_type': rules['statistical_type'].value,
                    'matched_keywords': matched_keywords,
                    'confidence': min(score / len(rules['keywords']), 1.0),
                    'suggestion': f"基于关键词 {', '.join(matched_keywords)}，建议使用{rules['statistical_type'].value}类型"
                })
        
        # 按置信度排序
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:3]  # 返回前3个建议
    
    def explain_classification(self, classification_result: Dict[str, Any]) -> str:
        """解释分类结果"""
        intent = classification_result['intent_type']
        confidence = classification_result['confidence']
        domain = classification_result['business_domain']
        reasoning = classification_result['reasoning']
        
        explanation = f"""
意图分类结果:
- 识别意图: {intent}
- 业务领域: {domain}  
- 置信度: {confidence:.2f}
- 推理过程: {reasoning}

建议统计类型: {classification_result['statistical_type'].value}
"""
        
        return explanation.strip()