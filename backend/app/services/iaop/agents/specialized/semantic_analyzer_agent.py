from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from ..base import BaseAgent
from ...context.execution_context import EnhancedExecutionContext
# 使用LLM客户端替代AI服务工厂
from app.services.llm.client import LLMServerClient, LLMRequest, LLMMessage

logger = logging.getLogger(__name__)


class PlaceholderSemanticAnalyzerAgent(BaseAgent):
    """占位符语义分析Agent - 使用LLM深度理解占位符业务含义"""
    
    def __init__(self, name: str = "semantic_analyzer", capabilities: List[str] = None):
        super().__init__(name, capabilities or ["semantic_analysis", "intent_extraction", "context_understanding"])
        self.ai_service = None
        
    async def validate_preconditions(self, context: EnhancedExecutionContext) -> bool:
        """验证执行前置条件"""
        required_fields = ['placeholder_text', 'data_source_context']
        for field in required_fields:
            if not context.request.get(field):
                logger.warning(f"缺少必要字段: {field}")
                return False
        return True
        
    async def execute(self, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """执行语义分析"""
        try:
            # 初始化LLM客户端
            if not self.ai_service:
                self.ai_service = LLMServerClient()
            
            placeholder_text = context.request.get('placeholder_text', '')
            data_source_context = context.request.get('data_source_context', {})
            template_context = context.request.get('template_context', {})
            
            # 构建语义分析的系统提示词
            system_prompt = self._build_semantic_analysis_prompt(data_source_context, template_context)
            
            # 构建用户查询
            user_prompt = f"""
请深度分析以下占位符的业务含义:

占位符文本: "{placeholder_text}"

请分析:
1. 这个占位符在业务报告中的具体作用
2. 需要什么类型的数据来填充
3. 业务逻辑和计算逻辑
4. 相关的业务概念和维度

返回JSON格式结果:
{{
    "primary_intent": "主要业务意图",
    "data_type": "temporal|statistical|dimensional|identifier|metric|filter",
    "sub_category": "具体子类别",
    "business_concept": "对应的业务概念",
    "calculation_logic": "计算逻辑描述",
    "required_dimensions": ["需要的维度列表"],
    "keywords": ["关键词列表"],
    "confidence": 0.0-1.0,
    "context_dependencies": ["依赖的上下文信息"]
}}
"""
            
            # 创建LLM请求
            request = LLMRequest(
                messages=[
                    LLMMessage(role="system", content=system_prompt),
                    LLMMessage(role="user", content=user_prompt)
                ],
                max_tokens=1500,
                temperature=0.1
            )
            
            # 调用LLM分析
            response = await self.ai_service.chat_completion(request)
            
            # 解析响应
            semantic_result = self._parse_semantic_response(response.content, placeholder_text)
            
            logger.info(f"语义分析完成: {placeholder_text}, 置信度: {semantic_result.get('confidence', 0)}")
            
            return {
                'agent': self.name,
                'type': 'semantic_analysis',
                'success': True,
                'data': semantic_result,
                'metadata': {
                    'analysis_timestamp': datetime.now().isoformat(),
                    'placeholder_text': placeholder_text,
                    'analysis_method': 'llm_semantic'
                }
            }
            
        except Exception as e:
            logger.error(f"语义分析失败: {e}")
            # 返回基础回退结果
            return self._generate_fallback_semantic_result(context, str(e))
    
    def _build_semantic_analysis_prompt(self, data_source_context: Dict, template_context: Dict) -> str:
        """构建语义分析的系统提示词"""
        
        prompt_parts = [
            "你是一个专业的数据智能分析专家，专门负责理解报告模板中占位符的业务含义。",
            "\n数据源上下文:"
        ]
        
        # 添加数据源信息
        if data_source_context:
            ds_name = data_source_context.get('data_source_name', '未知')
            ds_type = data_source_context.get('data_source_type', '未知')
            prompt_parts.append(f"- 数据源: {ds_name} ({ds_type})")
            
            tables = data_source_context.get('tables', [])
            if tables:
                prompt_parts.append("- 可用表结构:")
                for table in tables[:3]:  # 限制表数量
                    table_name = table.get('table_name', '')
                    business_category = table.get('business_category', '未分类')
                    prompt_parts.append(f"  * {table_name} - {business_category}")
        
        # 添加模板上下文
        if template_context:
            prompt_parts.append("\n模板上下文:")
            for key, value in template_context.items():
                if key in ['template_title', 'template_type', 'business_domain']:
                    prompt_parts.append(f"- {key}: {value}")
        
        prompt_parts.extend([
            "\n你的任务是深度理解占位符的业务含义，提取其核心意图和数据需求。",
            "重点关注:",
            "1. 业务场景和用途",
            "2. 数据计算逻辑", 
            "3. 业务维度和指标",
            "4. 时间和空间范围"
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_semantic_response(self, response_content: str, placeholder_text: str) -> Dict[str, Any]:
        """解析LLM的语义分析响应"""
        try:
            # 尝试解析JSON
            semantic_data = json.loads(response_content)
            
            # 验证和补充必要字段
            result = {
                'primary_intent': semantic_data.get('primary_intent', f'分析{placeholder_text}'),
                'data_type': semantic_data.get('data_type', 'unknown'),
                'sub_category': semantic_data.get('sub_category', 'general'),
                'business_concept': semantic_data.get('business_concept', placeholder_text),
                'calculation_logic': semantic_data.get('calculation_logic', '自动推断'),
                'required_dimensions': semantic_data.get('required_dimensions', []),
                'keywords': semantic_data.get('keywords', [placeholder_text]),
                'confidence': float(semantic_data.get('confidence', 0.7)),
                'context_dependencies': semantic_data.get('context_dependencies', [])
            }
            
            # 添加分析元数据
            result['analysis_source'] = 'llm_semantic_analysis'
            result['placeholder_text'] = placeholder_text
            
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"LLM响应解析失败: {e}")
            
            # 基于规则的回退分析
            return self._rule_based_semantic_analysis(placeholder_text)
    
    def _rule_based_semantic_analysis(self, placeholder_text: str) -> Dict[str, Any]:
        """基于规则的回退语义分析"""
        text_lower = placeholder_text.lower()
        
        # 时间类型识别
        if any(keyword in text_lower for keyword in ['年', '月', '日', '时间', '周期', '开始', '结束', 'date', 'time']):
            return {
                'primary_intent': '时间信息获取',
                'data_type': 'temporal',
                'sub_category': 'time_period',
                'business_concept': '时间维度',
                'calculation_logic': '时间计算或格式化',
                'required_dimensions': ['时间'],
                'keywords': [keyword for keyword in ['年', '月', '日', '时间', '周期'] if keyword in text_lower],
                'confidence': 0.8,
                'context_dependencies': [],
                'analysis_source': 'rule_based_fallback'
            }
        
        # 统计类型识别
        elif any(keyword in text_lower for keyword in ['统计', '总数', '件数', '占比', '百分比', '同比', 'count', 'sum', 'avg']):
            return {
                'primary_intent': '统计指标计算',
                'data_type': 'statistical',
                'sub_category': 'aggregation',
                'business_concept': '业务指标',
                'calculation_logic': '聚合计算',
                'required_dimensions': ['统计对象'],
                'keywords': [keyword for keyword in ['统计', '总数', '件数', '占比'] if keyword in text_lower],
                'confidence': 0.75,
                'context_dependencies': ['时间范围'],
                'analysis_source': 'rule_based_fallback'
            }
        
        # 图表类型识别
        elif any(keyword in text_lower for keyword in ['图表', '折线图', '饼图', '柱状图', 'chart']):
            return {
                'primary_intent': '数据可视化',
                'data_type': 'visualization',
                'sub_category': 'chart_data',
                'business_concept': '图表展示',
                'calculation_logic': '数据聚合和格式化',
                'required_dimensions': ['分组维度', '数值维度'],
                'keywords': [keyword for keyword in ['图表', '折线图', '饼图'] if keyword in text_lower],
                'confidence': 0.8,
                'context_dependencies': ['图表类型', '数据范围'],
                'analysis_source': 'rule_based_fallback'
            }
        
        # 维度类型识别
        elif any(keyword in text_lower for keyword in ['区域', '地区', '类型', '来源', '分类']):
            return {
                'primary_intent': '维度信息获取',
                'data_type': 'dimensional',
                'sub_category': 'category_info',
                'business_concept': '分类维度',
                'calculation_logic': '维度值提取',
                'required_dimensions': ['分类字段'],
                'keywords': [keyword for keyword in ['区域', '地区', '类型', '来源'] if keyword in text_lower],
                'confidence': 0.7,
                'context_dependencies': ['维度范围'],
                'analysis_source': 'rule_based_fallback'
            }
        
        # 默认处理
        else:
            return {
                'primary_intent': f'获取{placeholder_text}相关信息',
                'data_type': 'general',
                'sub_category': 'unknown',
                'business_concept': placeholder_text,
                'calculation_logic': '待确定',
                'required_dimensions': [],
                'keywords': [placeholder_text],
                'confidence': 0.5,
                'context_dependencies': [],
                'analysis_source': 'rule_based_default'
            }
    
    def _generate_fallback_semantic_result(self, context: EnhancedExecutionContext, error_msg: str) -> Dict[str, Any]:
        """生成回退语义分析结果"""
        placeholder_text = context.request.get('placeholder_text', '未知占位符')
        
        return {
            'agent': self.name,
            'type': 'semantic_analysis',
            'success': False,
            'data': {
                'primary_intent': f'分析{placeholder_text}',
                'data_type': 'unknown',
                'sub_category': 'error',
                'business_concept': placeholder_text,
                'calculation_logic': '分析失败',
                'required_dimensions': [],
                'keywords': [placeholder_text],
                'confidence': 0.1,
                'context_dependencies': [],
                'analysis_source': 'error_fallback'
            },
            'error': error_msg,
            'metadata': {
                'analysis_timestamp': datetime.now().isoformat(),
                'placeholder_text': placeholder_text,
                'analysis_method': 'error_fallback'
            }
        }


