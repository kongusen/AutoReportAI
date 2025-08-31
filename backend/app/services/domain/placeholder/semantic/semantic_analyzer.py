"""
语义分析器

深度分析占位符的语义内容和业务含义
"""

import logging
import re
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass
from ..models import StatisticalType, DocumentContext

logger = logging.getLogger(__name__)


@dataclass
class SemanticEntity:
    """语义实体"""
    text: str
    entity_type: str
    confidence: float
    position: Tuple[int, int]  # 在文本中的位置


@dataclass
class SemanticRelation:
    """语义关系"""
    subject: str
    predicate: str
    object: str
    confidence: float


class SemanticAnalyzer:
    """语义分析器"""
    
    def __init__(self):
        # 实体识别规则
        self.entity_patterns = {
            'time_period': {
                'patterns': [
                    r'(\d{4}年\d{1,2}月)',
                    r'(\d{4}-\d{2})',
                    r'(本月|上月|去年|今年)',
                    r'(一月|二月|三月|四月|五月|六月|七月|八月|九月|十月|十一月|十二月)',
                    r'(第[一二三四]季度)',
                    r'(上半年|下半年)'
                ],
                'type': 'TIME_PERIOD'
            },
            'metrics': {
                'patterns': [
                    r'(\w*销售额\w*)',
                    r'(\w*营收\w*)', 
                    r'(\w*利润\w*)',
                    r'(\w*成本\w*)',
                    r'(\w*数量\w*)',
                    r'(\w*业绩\w*)',
                    r'(\w*收入\w*)'
                ],
                'type': 'METRIC'
            },
            'organization': {
                'patterns': [
                    r'(\w*部门)',
                    r'(\w*分公司)',
                    r'(\w*区域?)',
                    r'(华东|华南|华北|华中|西南|西北)区?',
                    r'(\w*团队)',
                    r'(\w*事业部)'
                ],
                'type': 'ORGANIZATION'
            },
            'product': {
                'patterns': [
                    r'(\w*产品\w*)',
                    r'(\w*服务\w*)',
                    r'(\w*系列)',
                    r'(\w*品类)',
                    r'(\w*型号)'
                ],
                'type': 'PRODUCT'
            },
            'person': {
                'patterns': [
                    r'(\w*销售员\w*)',
                    r'(\w*员工\w*)',
                    r'(\w*客户\w*)',
                    r'(\w*经理\w*)',
                    r'(\w*总监\w*)'
                ],
                'type': 'PERSON'
            }
        }
        
        # 语义关系模板
        self.relation_templates = {
            'aggregation': {
                'patterns': [
                    r'(\w+)的?总(\w+)',
                    r'所有(\w+)的(\w+)',
                    r'全部(\w+)'
                ],
                'relation_type': 'AGGREGATION'
            },
            'comparison': {
                'patterns': [
                    r'(\w+)比(\w+)',
                    r'(\w+)与(\w+)对比',
                    r'(\w+)相比(\w+)'
                ],
                'relation_type': 'COMPARISON'
            },
            'ranking': {
                'patterns': [
                    r'(\w+)排名',
                    r'最好的(\w+)',
                    r'前\d*名(\w+)',
                    r'(\w+)第\d+'
                ],
                'relation_type': 'RANKING'
            }
        }
        
        # 业务语义词典
        self.business_semantics = {
            'sales_metrics': {
                'terms': ['销售额', '营收', '收入', '业绩', '成交额', '订单金额'],
                'dimension': 'FINANCIAL',
                'aggregation_method': 'SUM'
            },
            'count_metrics': {
                'terms': ['数量', '个数', '笔数', '件数', '人数'],
                'dimension': 'QUANTITY',
                'aggregation_method': 'COUNT'
            },
            'average_metrics': {
                'terms': ['平均', '均值', '平均值', '单价'],
                'dimension': 'AVERAGE',
                'aggregation_method': 'AVG'
            },
            'rate_metrics': {
                'terms': ['率', '比例', '百分比', '占比', '份额'],
                'dimension': 'PERCENTAGE',
                'aggregation_method': 'RATIO'
            }
        }
    
    async def analyze_semantics(
        self,
        placeholder_text: str,
        context: Optional[DocumentContext] = None,
        intent_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行语义分析"""
        try:
            # 提取描述文本
            description = self._extract_description(placeholder_text)
            
            # 实体识别
            entities = await self._extract_entities(description, context)
            
            # 关系抽取  
            relations = await self._extract_relations(description, entities)
            
            # 业务语义理解
            business_semantics = await self._analyze_business_semantics(
                description, entities, intent_info
            )
            
            # 数据维度分析
            data_dimensions = await self._analyze_data_dimensions(
                description, entities, context
            )
            
            # 综合语义理解
            semantic_understanding = await self._synthesize_semantics(
                entities, relations, business_semantics, data_dimensions
            )
            
            return {
                'entities': [self._entity_to_dict(e) for e in entities],
                'relations': [self._relation_to_dict(r) for r in relations],
                'business_semantics': business_semantics,
                'data_dimensions': data_dimensions,
                'semantic_understanding': semantic_understanding,
                'confidence': self._calculate_semantic_confidence(
                    entities, relations, business_semantics
                ),
                'suggested_type': semantic_understanding.get('recommended_stat_type'),
                'business_domain': semantic_understanding.get('business_domain'),
                'time_dimension': semantic_understanding.get('time_dimension'),
                'data_granularity': semantic_understanding.get('data_granularity')
            }
            
        except Exception as e:
            logger.error(f"语义分析失败: {placeholder_text}, 错误: {e}")
            return self._get_default_analysis()
    
    def _extract_description(self, placeholder_text: str) -> str:
        """提取占位符描述"""
        text = placeholder_text.strip()
        if text.startswith('{{') and text.endswith('}}'):
            text = text[2:-2]
        
        if '：' in text:
            parts = text.split('：', 1)
            if len(parts) > 1:
                return parts[1].split('|')[0].strip()
        
        return text
    
    async def _extract_entities(
        self,
        description: str,
        context: Optional[DocumentContext] = None
    ) -> List[SemanticEntity]:
        """实体识别"""
        entities = []
        
        # 基于规则的实体识别
        for entity_category, config in self.entity_patterns.items():
            for pattern in config['patterns']:
                matches = re.finditer(pattern, description)
                for match in matches:
                    entity = SemanticEntity(
                        text=match.group(1) if match.groups() else match.group(0),
                        entity_type=config['type'],
                        confidence=0.8,  # 基于规则的置信度
                        position=(match.start(), match.end())
                    )
                    entities.append(entity)
        
        # 上下文增强的实体识别
        if context:
            context_entities = await self._extract_context_entities(
                context, description
            )
            entities.extend(context_entities)
        
        # 去重和合并相似实体
        entities = self._merge_similar_entities(entities)
        
        return entities
    
    async def _extract_context_entities(
        self,
        context: DocumentContext,
        description: str
    ) -> List[SemanticEntity]:
        """从上下文中提取实体"""
        context_entities = []
        
        # 从段落内容中提取相关实体
        context_text = context.paragraph_content + " " + context.section_title
        
        # 寻找在描述中提到的但可能在上下文中有更多信息的实体
        for entity_category, config in self.entity_patterns.items():
            for pattern in config['patterns']:
                matches = re.finditer(pattern, context_text)
                for match in matches:
                    entity_text = match.group(1) if match.groups() else match.group(0)
                    
                    # 检查这个实体是否与描述相关
                    if self._is_entity_relevant_to_description(entity_text, description):
                        entity = SemanticEntity(
                            text=entity_text,
                            entity_type=config['type'],
                            confidence=0.6,  # 上下文实体置信度较低
                            position=(match.start(), match.end())
                        )
                        context_entities.append(entity)
        
        return context_entities
    
    def _is_entity_relevant_to_description(self, entity_text: str, description: str) -> bool:
        """判断实体是否与描述相关"""
        # 简单的相关性判断
        entity_words = set(entity_text)
        description_words = set(description)
        
        # 如果有共同字符，认为相关
        return bool(entity_words.intersection(description_words))
    
    def _merge_similar_entities(self, entities: List[SemanticEntity]) -> List[SemanticEntity]:
        """合并相似的实体"""
        merged_entities = []
        processed = set()
        
        for i, entity in enumerate(entities):
            if i in processed:
                continue
                
            similar_entities = [entity]
            processed.add(i)
            
            # 查找相似实体
            for j, other_entity in enumerate(entities[i+1:], i+1):
                if j in processed:
                    continue
                    
                if self._entities_similar(entity, other_entity):
                    similar_entities.append(other_entity)
                    processed.add(j)
            
            # 合并相似实体
            merged_entity = self._merge_entities(similar_entities)
            merged_entities.append(merged_entity)
        
        return merged_entities
    
    def _entities_similar(self, entity1: SemanticEntity, entity2: SemanticEntity) -> bool:
        """判断两个实体是否相似"""
        # 类型相同且文本相似
        if entity1.entity_type != entity2.entity_type:
            return False
        
        # 文本相似度检查（简单版本）
        text1_chars = set(entity1.text)
        text2_chars = set(entity2.text)
        
        if not text1_chars or not text2_chars:
            return False
        
        intersection = text1_chars.intersection(text2_chars)
        union = text1_chars.union(text2_chars)
        
        similarity = len(intersection) / len(union) if union else 0
        return similarity > 0.7
    
    def _merge_entities(self, entities: List[SemanticEntity]) -> SemanticEntity:
        """合并多个实体"""
        if len(entities) == 1:
            return entities[0]
        
        # 选择置信度最高的实体作为基础
        base_entity = max(entities, key=lambda e: e.confidence)
        
        # 计算合并后的置信度
        avg_confidence = sum(e.confidence for e in entities) / len(entities)
        
        return SemanticEntity(
            text=base_entity.text,
            entity_type=base_entity.entity_type,
            confidence=min(avg_confidence * 1.1, 1.0),  # 合并提升置信度
            position=base_entity.position
        )
    
    async def _extract_relations(
        self,
        description: str,
        entities: List[SemanticEntity]
    ) -> List[SemanticRelation]:
        """关系抽取"""
        relations = []
        
        # 基于模板的关系抽取
        for relation_category, config in self.relation_templates.items():
            for pattern in config['patterns']:
                matches = re.finditer(pattern, description)
                for match in matches:
                    groups = match.groups()
                    if len(groups) >= 2:
                        relation = SemanticRelation(
                            subject=groups[0],
                            predicate=config['relation_type'],
                            object=groups[1] if len(groups) > 1 else "",
                            confidence=0.7
                        )
                        relations.append(relation)
        
        # 基于实体的关系推断
        entity_relations = await self._infer_entity_relations(entities, description)
        relations.extend(entity_relations)
        
        return relations
    
    async def _infer_entity_relations(
        self,
        entities: List[SemanticEntity],
        description: str
    ) -> List[SemanticRelation]:
        """基于实体推断关系"""
        relations = []
        
        # 简单的关系推断规则
        metrics = [e for e in entities if e.entity_type == 'METRIC']
        organizations = [e for e in entities if e.entity_type == 'ORGANIZATION']
        time_periods = [e for e in entities if e.entity_type == 'TIME_PERIOD']
        
        # 指标-组织关系
        for metric in metrics:
            for org in organizations:
                relation = SemanticRelation(
                    subject=org.text,
                    predicate='HAS_METRIC',
                    object=metric.text,
                    confidence=0.6
                )
                relations.append(relation)
        
        # 指标-时间关系
        for metric in metrics:
            for time_period in time_periods:
                relation = SemanticRelation(
                    subject=metric.text,
                    predicate='IN_TIME_PERIOD',
                    object=time_period.text,
                    confidence=0.6
                )
                relations.append(relation)
        
        return relations
    
    async def _analyze_business_semantics(
        self,
        description: str,
        entities: List[SemanticEntity],
        intent_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """业务语义分析"""
        business_semantics = {}
        
        # 识别业务语义类别
        for category, config in self.business_semantics.items():
            for term in config['terms']:
                if term in description:
                    business_semantics[category] = {
                        'dimension': config['dimension'],
                        'aggregation_method': config['aggregation_method'],
                        'confidence': 0.8,
                        'matched_term': term
                    }
                    break
        
        # 结合意图信息增强理解
        if intent_info and 'business_domain' in intent_info:
            business_semantics['domain_context'] = intent_info['business_domain']
        
        return business_semantics
    
    async def _analyze_data_dimensions(
        self,
        description: str,
        entities: List[SemanticEntity],
        context: Optional[DocumentContext] = None
    ) -> Dict[str, Any]:
        """数据维度分析"""
        dimensions = {
            'time_dimension': None,
            'spatial_dimension': None,
            'organizational_dimension': None,
            'product_dimension': None,
            'granularity': 'medium'
        }
        
        # 时间维度
        time_entities = [e for e in entities if e.entity_type == 'TIME_PERIOD']
        if time_entities:
            dimensions['time_dimension'] = time_entities[0].text
            
            # 推断时间粒度
            if any(term in time_entities[0].text for term in ['日', '天']):
                dimensions['granularity'] = 'daily'
            elif any(term in time_entities[0].text for term in ['月', '季度']):
                dimensions['granularity'] = 'monthly'
            elif any(term in time_entities[0].text for term in ['年']):
                dimensions['granularity'] = 'yearly'
        
        # 组织维度
        org_entities = [e for e in entities if e.entity_type == 'ORGANIZATION']
        if org_entities:
            dimensions['organizational_dimension'] = org_entities[0].text
        
        # 产品维度
        product_entities = [e for e in entities if e.entity_type == 'PRODUCT']
        if product_entities:
            dimensions['product_dimension'] = product_entities[0].text
        
        return dimensions
    
    async def _synthesize_semantics(
        self,
        entities: List[SemanticEntity],
        relations: List[SemanticRelation],
        business_semantics: Dict[str, Any],
        data_dimensions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """综合语义理解"""
        understanding = {}
        
        # 推荐统计类型
        if any('aggregation' in bs for bs in business_semantics.keys()):
            understanding['recommended_stat_type'] = StatisticalType.STATISTICS
        elif any(r.predicate == 'RANKING' for r in relations):
            understanding['recommended_stat_type'] = StatisticalType.LIST
        elif data_dimensions.get('time_dimension'):
            understanding['recommended_stat_type'] = StatisticalType.TREND
        else:
            understanding['recommended_stat_type'] = StatisticalType.STATISTICS
        
        # 业务领域
        domain_indicators = [e.text for e in entities if e.entity_type in ['METRIC', 'ORGANIZATION']]
        if any('销售' in indicator for indicator in domain_indicators):
            understanding['business_domain'] = 'sales'
        elif any('财务' in indicator for indicator in domain_indicators):
            understanding['business_domain'] = 'finance'
        else:
            understanding['business_domain'] = 'general'
        
        # 时间维度和粒度
        understanding['time_dimension'] = data_dimensions.get('time_dimension')
        understanding['data_granularity'] = data_dimensions.get('granularity')
        
        return understanding
    
    def _calculate_semantic_confidence(
        self,
        entities: List[SemanticEntity],
        relations: List[SemanticRelation], 
        business_semantics: Dict[str, Any]
    ) -> float:
        """计算语义分析置信度"""
        # 实体识别质量
        entity_confidence = sum(e.confidence for e in entities) / len(entities) if entities else 0
        
        # 关系抽取质量
        relation_confidence = sum(r.confidence for r in relations) / len(relations) if relations else 0
        
        # 业务语义理解质量
        semantic_confidence = sum(
            bs.get('confidence', 0) for bs in business_semantics.values()
        ) / len(business_semantics) if business_semantics else 0
        
        # 综合置信度
        weights = [0.4, 0.3, 0.3]
        scores = [entity_confidence, relation_confidence, semantic_confidence]
        
        return sum(w * s for w, s in zip(weights, scores))
    
    def _entity_to_dict(self, entity: SemanticEntity) -> Dict[str, Any]:
        """将实体转换为字典"""
        return {
            'text': entity.text,
            'type': entity.entity_type,
            'confidence': entity.confidence,
            'position': entity.position
        }
    
    def _relation_to_dict(self, relation: SemanticRelation) -> Dict[str, Any]:
        """将关系转换为字典"""
        return {
            'subject': relation.subject,
            'predicate': relation.predicate,
            'object': relation.object,
            'confidence': relation.confidence
        }
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """获取默认分析结果"""
        return {
            'entities': [],
            'relations': [],
            'business_semantics': {},
            'data_dimensions': {'granularity': 'medium'},
            'semantic_understanding': {
                'recommended_stat_type': StatisticalType.STATISTICS,
                'business_domain': 'general'
            },
            'confidence': 0.3,
            'suggested_type': StatisticalType.STATISTICS,
            'business_domain': 'general',
            'time_dimension': None,
            'data_granularity': 'medium'
        }