"""
LLM驱动的增强占位符分析器
使用真正的AI能力来理解占位符含义并生成SQL查询

这是上下文工程的核心组件，结合:
1. 用户选择的数据源信息
2. 实际的表结构和列信息  
3. 占位符的语义含义
4. LLM的推理能力
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from .integration.ai_service_enhanced import EnhancedAIService, AIRequest
from app.core.ai_service_factory import get_user_ai_service
from app.services.domain.placeholder.semantic_analyzer import SemanticAnalysisResult, PlaceholderSemanticType

logger = logging.getLogger(__name__)


@dataclass
class EnhancedSemanticAnalysisResult:
    """增强的语义分析结果"""
    
    primary_type: str
    sub_type: Optional[str] = None
    confidence: float = 0.0
    keywords: List[str] = None
    data_intent: str = ""
    sql_query: str = ""
    target_table: Optional[str] = None
    target_columns: List[str] = None
    explanation: str = ""
    suggestions: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.target_columns is None:
            self.target_columns = []
        if self.suggestions is None:
            self.suggestions = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DataSourceContext:
    """数据源上下文信息"""
    
    data_source_id: str
    data_source_name: str
    data_source_type: str
    tables: List[Dict[str, Any]]
    connection_info: Dict[str, Any]


class EnhancedPlaceholderAnalyzer:
    """LLM驱动的增强占位符分析器"""
    
    def __init__(self, db_session: Session = None, user_id: str = None):
        self.db_session = db_session
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
        
        # 获取用户专属的AI服务
        if user_id:
            self.ai_service = get_user_ai_service(user_id)
        else:
            self.ai_service = EnhancedAIService(db_session) if db_session else None
        
        if not self.ai_service:
            raise ValueError("无法初始化AI服务，请检查配置")
            
        logger.info(f"EnhancedPlaceholderAnalyzer initialized for user: {user_id}")
    
    async def analyze_placeholder(
        self,
        placeholder_text: str,
        data_source_context: DataSourceContext,
        template_context: Optional[Dict[str, Any]] = None
    ) -> EnhancedSemanticAnalysisResult:
        """
        使用LLM分析占位符并生成SQL查询
        这是核心的上下文工程方法
        """
        self.logger.info(f"开始LLM分析占位符: {placeholder_text}")
        
        try:
            # 构建丰富的上下文信息
            context_prompt = self._build_context_prompt(
                data_source_context, template_context or {}
            )
            
            # 构建系统提示词
            system_prompt = f"""
你是一个专业的数据分析专家，负责理解报告模板中的占位符含义，并基于实际数据源信息生成准确的SQL查询。

{context_prompt}

你的任务是:
1. 深度理解占位符的业务含义
2. 基于真实的表结构选择合适的表和字段
3. 生成能在指定数据源上执行的SQL查询
4. 提供清晰的解释和建议

请返回JSON格式的分析结果:
{{
    "primary_type": "temporal|statistical|dimensional|identifier|metric|filter",
    "sub_type": "具体的子类型如start_date, count, sum, region等",
    "confidence": 0.0-1.0的置信度,
    "keywords": ["提取的关键词列表"],
    "data_intent": "数据意图的详细描述",
    "sql_query": "完整的可执行SQL查询",
    "target_table": "主要目标表名",
    "target_columns": ["相关字段列表"],
    "explanation": "SQL查询的详细解释",
    "suggestions": ["优化建议列表"],
    "metadata": {{
        "analysis_approach": "分析方法",
        "table_selection_reason": "表选择原因",
        "column_mapping": {{"占位符概念": "实际字段名"}},
        "query_complexity": "simple|medium|complex"
    }}
}}

重要原则:
- 必须基于提供的真实表结构生成SQL
- SQL必须在{data_source_context.data_source_type}数据库中可执行
- 优先选择数据质量高、更新及时的表
- 生成的SQL要高效、准确、符合业务逻辑
- 如果占位符含义不明确，选择最合理的解释
"""
            
            # 构建用户提示词
            user_prompt = f"""
请分析以下占位符并生成相应的SQL查询:

占位符文本: "{placeholder_text}"

请仔细分析占位符的含义，考虑:
1. 字面意思和业务含义
2. 在报告模板中的作用
3. 需要什么样的数据来填充这个占位符
4. 基于提供的表结构，应该查询哪些表和字段

请生成准确、可执行的SQL查询，并提供详细的分析说明。
"""
            
            # 创建AI请求
            request = AIRequest(
                model=self.ai_service.provider.default_model_name or "gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.1  # 低温度确保一致性
            )
            
            # 调用LLM
            response = await self.ai_service.chat_completion(request)
            
            # 解析响应
            try:
                analysis_data = json.loads(response.content)
                
                # 验证和补充必要字段
                analysis_data = self._validate_and_enhance_response(
                    analysis_data, placeholder_text, data_source_context
                )
                
                result = EnhancedSemanticAnalysisResult(**analysis_data)
                
                self.logger.info(f"LLM分析完成: {placeholder_text}, 置信度: {result.confidence}")
                return result
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"LLM响应JSON解析失败: {e}")
                # 生成回退结果
                return self._generate_fallback_result(placeholder_text, data_source_context)
                
        except Exception as e:
            self.logger.error(f"LLM占位符分析失败: {e}")
            return self._generate_fallback_result(placeholder_text, data_source_context)
    
    def _build_context_prompt(
        self, 
        data_source_context: DataSourceContext, 
        template_context: Dict[str, Any]
    ) -> str:
        """构建丰富的上下文提示词"""
        
        context_parts = [
            f"数据源信息:",
            f"- 数据源ID: {data_source_context.data_source_id}",
            f"- 数据源名称: {data_source_context.data_source_name}",
            f"- 数据库类型: {data_source_context.data_source_type}",
            f"- 连接信息: {data_source_context.connection_info}",
            "",
            "可用表结构:"
        ]
        
        # 添加表结构信息
        for i, table in enumerate(data_source_context.tables):
            table_name = table.get('table_name', f'table_{i}')
            business_category = table.get('business_category', '未分类')
            data_quality_score = table.get('data_quality_score', 0.0)
            estimated_rows = table.get('estimated_row_count', 0)
            
            context_parts.append(f"表 {table_name}:")
            context_parts.append(f"  - 业务类别: {business_category}")
            context_parts.append(f"  - 数据质量评分: {data_quality_score}")
            context_parts.append(f"  - 估计行数: {estimated_rows}")
            
            # 添加列信息
            columns = table.get('columns', [])
            if columns:
                context_parts.append("  - 字段信息:")
                for col in columns[:10]:  # 最多显示10个字段
                    col_name = col.get('name', '')
                    col_type = col.get('type', '')
                    business_name = col.get('business_name', '')
                    business_desc = col.get('business_description', '')
                    
                    col_info = f"    {col_name} ({col_type})"
                    if business_name:
                        col_info += f" - 业务名称: {business_name}"
                    if business_desc:
                        col_info += f" - 说明: {business_desc}"
                    
                    context_parts.append(col_info)
                
                if len(columns) > 10:
                    context_parts.append(f"    ... 还有 {len(columns) - 10} 个字段")
            
            context_parts.append("")
        
        # 添加模板上下文
        if template_context:
            context_parts.append("模板上下文:")
            for key, value in template_context.items():
                context_parts.append(f"- {key}: {value}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _validate_and_enhance_response(
        self, 
        analysis_data: Dict[str, Any], 
        placeholder_text: str,
        data_source_context: DataSourceContext
    ) -> Dict[str, Any]:
        """验证和增强LLM响应"""
        
        # 确保必要字段存在
        if 'primary_type' not in analysis_data:
            analysis_data['primary_type'] = 'unknown'
        
        if 'confidence' not in analysis_data:
            analysis_data['confidence'] = 0.5
            
        if 'sql_query' not in analysis_data or not analysis_data['sql_query']:
            # 生成基于占位符内容的智能SQL查询
            analysis_data['sql_query'], analysis_data['target_table'] = self._generate_intelligent_fallback_sql(
                placeholder_text, data_source_context
            )
        
        if 'data_intent' not in analysis_data:
            analysis_data['data_intent'] = f"获取与'{placeholder_text}'相关的数据"
        
        if 'explanation' not in analysis_data:
            analysis_data['explanation'] = f"基于占位符'{placeholder_text}'生成的查询"
        
        # 添加分析时间戳
        if 'metadata' not in analysis_data:
            analysis_data['metadata'] = {}
        
        analysis_data['metadata']['analysis_timestamp'] = datetime.now().isoformat()
        analysis_data['metadata']['analyzer_type'] = 'llm_enhanced'
        analysis_data['metadata']['data_source_id'] = data_source_context.data_source_id
        
        return analysis_data
    
    def _generate_intelligent_fallback_sql(
        self, 
        placeholder_text: str, 
        data_source_context: DataSourceContext
    ) -> Tuple[str, Optional[str]]:
        """基于占位符内容生成智能的回退SQL查询"""
        
        # 选择最佳表
        target_table = self._select_best_table_for_placeholder(placeholder_text, data_source_context)
        
        if not target_table:
            return "SELECT 1", None
        
        # 基于占位符内容类型生成不同的SQL
        placeholder_lower = placeholder_text.lower()
        
        # 图表类型占位符
        if any(keyword in placeholder_lower for keyword in ['图表', 'chart', '折线图', '饼图', '柱状图', 'bar', 'pie', 'line']):
            return self._generate_chart_sql(placeholder_text, target_table, data_source_context)
        
        # 时间相关占位符  
        if any(keyword in placeholder_lower for keyword in ['年', '月', '日', '时间', '周期', '开始', '结束', 'date', 'time']):
            return self._generate_temporal_sql(placeholder_text, target_table, data_source_context)
        
        # 统计相关占位符
        if any(keyword in placeholder_lower for keyword in ['统计', '总数', '件数', '占比', '百分比', '同比', '变化', 'count', 'sum', 'avg', 'total']):
            return self._generate_statistical_sql(placeholder_text, target_table, data_source_context)
        
        # 区域相关占位符
        if any(keyword in placeholder_lower for keyword in ['区域', '地区', '地名', '城市', '省份', 'region', 'area', 'city']):
            return self._generate_dimensional_sql(placeholder_text, target_table, data_source_context)
        
        # 默认计数查询
        return f"SELECT COUNT(*) as total_count FROM {target_table}", target_table
    
    def _select_best_table_for_placeholder(
        self, 
        placeholder_text: str, 
        data_source_context: DataSourceContext
    ) -> Optional[str]:
        """为占位符选择最佳表"""
        
        if not data_source_context.tables:
            return None
        
        # 根据占位符内容选择相关的表
        placeholder_lower = placeholder_text.lower()
        
        # 寻找业务相关的表
        for table in data_source_context.tables:
            table_name = table.get('table_name', '').lower()
            business_category = (table.get('business_category') or '').lower()
            
            # 投诉相关
            if any(keyword in placeholder_lower for keyword in ['投诉', 'complain']) and 'complain' in table_name:
                return table.get('table_name')
            
            # 通过业务类别匹配
            if business_category and any(keyword in placeholder_lower for keyword in business_category.split()):
                return table.get('table_name')
        
        # 默认选择第一个表或数据质量最高的表
        best_table = data_source_context.tables[0]
        best_score = best_table.get('data_quality_score', 0.0) or 0.0
        
        for table in data_source_context.tables[1:]:
            score = table.get('data_quality_score', 0.0) or 0.0
            if score > best_score:
                best_score = score
                best_table = table
        
        return best_table.get('table_name')
    
    def _generate_chart_sql(
        self, 
        placeholder_text: str, 
        target_table: str, 
        data_source_context: DataSourceContext
    ) -> Tuple[str, str]:
        """生成图表专用的SQL查询"""
        
        # 寻找时间列和分组列
        time_columns, category_columns = self._find_relevant_columns(target_table, data_source_context)
        
        if '趋势' in placeholder_text or 'trend' in placeholder_text.lower():
            # 趋势图 - 按时间分组
            if time_columns:
                time_col = time_columns[0]
                sql = f"""SELECT 
                    DATE_FORMAT({time_col}, '%Y-%m') as time_period,
                    COUNT(*) as count_value
                FROM {target_table} 
                GROUP BY DATE_FORMAT({time_col}, '%Y-%m')
                ORDER BY time_period"""
                return sql, target_table
        
        elif '来源' in placeholder_text or 'source' in placeholder_text.lower():
            # 来源分布 - 按来源分组
            if category_columns:
                cat_col = category_columns[0]
                sql = f"""SELECT 
                    {cat_col} as category,
                    COUNT(*) as count_value
                FROM {target_table} 
                GROUP BY {cat_col}
                ORDER BY count_value DESC
                LIMIT 10"""
                return sql, target_table
        
        elif '类型' in placeholder_text or 'type' in placeholder_text.lower():
            # 类型分布 - 按类型分组
            if category_columns:
                cat_col = category_columns[0] 
                sql = f"""SELECT 
                    {cat_col} as category,
                    COUNT(*) as count_value
                FROM {target_table} 
                GROUP BY {cat_col}
                ORDER BY count_value DESC"""
                return sql, target_table
        
        # 默认图表查询 - 生成图表格式数据
        return self._generate_default_chart_data(placeholder_text, target_table), target_table
    
    def _generate_default_chart_data(self, placeholder_text: str, target_table: str) -> str:
        """生成默认图表数据的特殊格式"""
        
        if '趋势' in placeholder_text or '折线图' in placeholder_text:
            # 趋势图表数据
            return f"""
            <chart type="line" title="{placeholder_text}">
            SELECT 
                DATE_FORMAT(创建时间, '%Y-%m') as x_axis,
                COUNT(*) as y_axis
            FROM {target_table}
            WHERE 创建时间 >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(创建时间, '%Y-%m')
            ORDER BY x_axis
            </chart>
            """
        elif '饼图' in placeholder_text or '来源' in placeholder_text:
            # 饼图数据
            return f"""
            <chart type="pie" title="{placeholder_text}">
            SELECT 
                来源类型 as label,
                COUNT(*) as value
            FROM {target_table}
            GROUP BY 来源类型
            ORDER BY value DESC
            LIMIT 8
            </chart>
            """
        elif '柱状图' in placeholder_text or '类型' in placeholder_text:
            # 柱状图数据
            return f"""
            <chart type="bar" title="{placeholder_text}">
            SELECT 
                投诉类型 as category,
                COUNT(*) as value
            FROM {target_table}
            GROUP BY 投诉类型
            ORDER BY value DESC
            LIMIT 10
            </chart>
            """
        else:
            # 通用图表
            return f"""
            <chart type="default" title="{placeholder_text}">
            SELECT 
                '总计' as label,
                COUNT(*) as value
            FROM {target_table}
            </chart>
            """
    
    def _generate_temporal_sql(
        self, 
        placeholder_text: str, 
        target_table: str, 
        data_source_context: DataSourceContext
    ) -> Tuple[str, str]:
        """生成时间相关的SQL查询"""
        
        time_columns, _ = self._find_relevant_columns(target_table, data_source_context)
        
        if '报告年份' in placeholder_text:
            return "SELECT YEAR(NOW()) as report_year", target_table
        elif '开始日期' in placeholder_text or '统计开始' in placeholder_text:
            return "SELECT DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 MONTH), '%Y-%m-01') as start_date", target_table
        elif '结束日期' in placeholder_text or '统计结束' in placeholder_text:
            return "SELECT DATE_FORMAT(LAST_DAY(DATE_SUB(NOW(), INTERVAL 1 MONTH)), '%Y-%m-%d') as end_date", target_table
        
        # 默认时间查询
        if time_columns:
            time_col = time_columns[0]
            return f"SELECT DATE_FORMAT(MAX({time_col}), '%Y-%m-%d') as latest_date FROM {target_table}", target_table
        
        return "SELECT DATE_FORMAT(NOW(), '%Y-%m-%d') as current_date", target_table
    
    def _generate_statistical_sql(
        self, 
        placeholder_text: str, 
        target_table: str, 
        data_source_context: DataSourceContext
    ) -> Tuple[str, str]:
        """生成统计相关的SQL查询"""
        
        placeholder_lower = placeholder_text.lower()
        
        # 根据占位符内容生成特定的统计查询
        if '总投诉件数' in placeholder_text or '投诉件数' in placeholder_text:
            # 添加时间筛选条件
            sql = f"""SELECT COUNT(*) as total_count 
                    FROM {target_table}
                    WHERE DATE_FORMAT(创建时间, '%Y-%m') = DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 MONTH), '%Y-%m')"""
        elif '占比' in placeholder_text and ('热线' in placeholder_text or 'app' in placeholder_text.lower()):
            # 来源占比统计
            sql = f"""SELECT 
                    COUNT(*) as count_value,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {target_table}), 2) as percentage
                    FROM {target_table}
                    WHERE 来源类型 LIKE '%热线%' OR 来源类型 LIKE '%APP%'"""
        elif '同比' in placeholder_text:
            # 同比变化统计
            sql = f"""SELECT 
                    COUNT(*) as current_count,
                    (SELECT COUNT(*) FROM {target_table} 
                     WHERE DATE_FORMAT(创建时间, '%Y-%m') = DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 13 MONTH), '%Y-%m')) as last_year_count
                    FROM {target_table}
                    WHERE DATE_FORMAT(创建时间, '%Y-%m') = DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 MONTH), '%Y-%m')"""
        elif '去重' in placeholder_text:
            # 去重统计
            if '身份证' in placeholder_text:
                sql = f"SELECT COUNT(DISTINCT 身份证号) as unique_count FROM {target_table}"
            elif '手机' in placeholder_text:
                sql = f"SELECT COUNT(DISTINCT 手机号) as unique_count FROM {target_table}"  
            else:
                sql = f"SELECT COUNT(DISTINCT 投诉人) as unique_count FROM {target_table}"
        else:
            # 默认统计查询
            sql = f"SELECT COUNT(*) as total_count FROM {target_table}"
        
        return sql, target_table
    
    def _generate_dimensional_sql(
        self, 
        placeholder_text: str, 
        target_table: str, 
        data_source_context: DataSourceContext
    ) -> Tuple[str, str]:
        """生成维度相关的SQL查询"""
        
        if '地区名称' in placeholder_text or '区域' in placeholder_text:
            # 默认地区信息
            return "SELECT '云南省' as region_name", target_table
        
        # 默认维度查询
        return f"SELECT '未知' as dimension_value", target_table
    
    def _find_relevant_columns(
        self, 
        target_table: str, 
        data_source_context: DataSourceContext
    ) -> Tuple[List[str], List[str]]:
        """查找相关的时间列和分类列"""
        
        time_columns = []
        category_columns = []
        
        for table in data_source_context.tables:
            if table.get('table_name') == target_table:
                columns = table.get('columns', [])
                
                for col in columns:
                    col_name = col.get('name', '').lower()
                    col_type = (col.get('type') or '').lower()
                    
                    # 时间列识别
                    if (any(keyword in col_name for keyword in ['time', 'date', '时间', '日期', '创建', '更新']) or
                        any(keyword in col_type for keyword in ['datetime', 'timestamp', 'date'])):
                        time_columns.append(col.get('name'))
                    
                    # 分类列识别
                    elif (any(keyword in col_name for keyword in ['type', 'category', '类型', '来源', '分类']) or
                          col_type in ['varchar', 'text', 'string']):
                        category_columns.append(col.get('name'))
                
                break
        
        return time_columns[:3], category_columns[:3]  # 限制返回数量
    
    def _generate_fallback_result(
        self, 
        placeholder_text: str, 
        data_source_context: DataSourceContext
    ) -> EnhancedSemanticAnalysisResult:
        """生成回退结果"""
        
        # 使用智能SQL生成
        sql_query, target_table = self._generate_intelligent_fallback_sql(placeholder_text, data_source_context)
        
        return EnhancedSemanticAnalysisResult(
            primary_type="unknown",
            sub_type="fallback",
            confidence=0.3,
            keywords=[placeholder_text],
            data_intent=f"获取与'{placeholder_text}'相关的数据（回退模式）",
            sql_query=sql_query,
            target_table=target_table,
            target_columns=[],
            explanation="由于LLM分析失败，使用回退模式生成的基本查询",
            suggestions=["建议检查AI服务配置", "尝试重新分析"],
            metadata={
                'fallback_reason': 'llm_analysis_failed',
                'analysis_timestamp': datetime.now().isoformat(),
                'analyzer_type': 'fallback'
            }
        )
    
    async def batch_analyze_placeholders(
        self,
        placeholder_requests: List[Tuple[str, DataSourceContext]],
        template_context: Optional[Dict[str, Any]] = None
    ) -> List[EnhancedSemanticAnalysisResult]:
        """批量分析占位符"""
        
        results = []
        
        for placeholder_text, data_source_context in placeholder_requests:
            try:
                result = await self.analyze_placeholder(
                    placeholder_text, data_source_context, template_context
                )
                results.append(result)
            except Exception as e:
                self.logger.error(f"批量分析中单个占位符失败: {placeholder_text}, 错误: {e}")
                fallback_result = self._generate_fallback_result(placeholder_text, data_source_context)
                results.append(fallback_result)
        
        return results
    
    async def validate_generated_sql(
        self, 
        sql_query: str, 
        data_source_context: DataSourceContext
    ) -> Dict[str, Any]:
        """验证生成的SQL查询"""
        
        try:
            # 构建验证提示词
            validation_prompt = f"""
请验证以下SQL查询的正确性:

SQL: {sql_query}
数据库类型: {data_source_context.data_source_type}
可用表: {[table['table_name'] for table in data_source_context.tables]}

请检查:
1. 语法是否正确
2. 表名和字段名是否存在
3. 查询逻辑是否合理
4. 是否符合{data_source_context.data_source_type}语法规范

返回JSON格式结果:
{{
    "is_valid": true/false,
    "issues": ["问题列表"],
    "suggestions": ["改进建议"],
    "corrected_sql": "修正后的SQL（如果需要）"
}}
"""
            
            request = AIRequest(
                model=self.ai_service.provider.default_model_name or "gpt-3.5-turbo",
                messages=[{"role": "user", "content": validation_prompt}],
                max_tokens=800,
                temperature=0.1
            )
            
            response = await self.ai_service.chat_completion(request)
            
            try:
                return json.loads(response.content)
            except json.JSONDecodeError:
                return {
                    "is_valid": True,
                    "issues": [],
                    "suggestions": [],
                    "corrected_sql": sql_query
                }
                
        except Exception as e:
            self.logger.error(f"SQL验证失败: {e}")
            return {
                "is_valid": False,
                "issues": [f"验证过程出错: {str(e)}"],
                "suggestions": ["建议人工检查SQL"],
                "corrected_sql": sql_query
            }


def create_enhanced_placeholder_analyzer(
    db_session: Session = None, 
    user_id: str = None
) -> EnhancedPlaceholderAnalyzer:
    """创建增强占位符分析器的工厂函数"""
    return EnhancedPlaceholderAnalyzer(db_session, user_id)