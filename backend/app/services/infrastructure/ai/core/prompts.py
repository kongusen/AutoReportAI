"""
提示词管理系统 - 集成到现有AI架构

"""

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
import json
import logging

logger = logging.getLogger(__name__)


class PromptComplexity(Enum):
    """提示词复杂度级别"""
    SIMPLE = "simple"      # 基础操作，简单指令
    MEDIUM = "medium"      # 标准操作，结构化指令  
    HIGH = "high"          # 复杂操作，详细约束和示例
    CRITICAL = "critical"  # 关键操作，最大安全防护


class PromptSafety(Enum):
    """安全级别"""
    LOW = "low"           # 只读操作
    MEDIUM = "medium"     # 标准写操作  
    HIGH = "high"         # 数据修改操作
    CRITICAL = "critical" # 系统级操作


@dataclass
class PromptTemplate:
    """提示词模板基类"""
    name: str
    complexity: PromptComplexity
    safety: PromptSafety
    version: str = "1.0"
    
    def render(self, context: Dict[str, Any]) -> str:
        """渲染提示词"""
        raise NotImplementedError


class SQLGenerationPrompts:
    """SQL生成提示词集合 - 优化版本"""
    
    @staticmethod
    def get_reasoning_prompt(
        placeholder_name: str,
        placeholder_analysis: str,
        available_tables: List[str],
        table_details: List[Dict[str, Any]],
        learned_insights: List[str] = None,
        iteration_history: List[Dict[str, Any]] = None,
        iteration: int = 0,
        complexity: PromptComplexity = PromptComplexity.HIGH
    ) -> str:
        """ReAct推理阶段提示词 - 渐进式披露设计"""
        
        learned_insights = learned_insights or []
        iteration_history = iteration_history or []
        
        # Layer 1: 强制性约束（最高优先级）
        safety_constraints = f"""
🚨【强制性约束 - 绝对不可违反】🚨
❌ NEVER 使用：complaints, users, orders, products, customers 等常见表名
❌ NEVER 编造任何表名，哪怕看起来很合理
✅ ALWAYS 从下面的真实表列表中选择：
{chr(10).join([f"  ✅ {table}" for table in available_tables])}

🔒【验证检查 - 必须通过】:
- selected_table 必须在上述真实表列表中存在
- relevant_fields 必须在选定表的字段列表中存在
- 如果找不到合适的表，选择最接近的表并说明原因
"""

        # Layer 2: 任务上下文
        task_context = f"""
【关键任务】: 为占位符 "{placeholder_name}" 从真实表中选择一个
【占位符分析】: {placeholder_analysis}
"""

        # Layer 3: 数据结构信息（条件复杂度）
        if complexity in [PromptComplexity.HIGH, PromptComplexity.CRITICAL]:
            data_info = f"""
📊【真实数据表结构】:
{SQLGenerationPrompts._build_detailed_tables_info(table_details)}
"""
        else:
            data_info = f"""
📋【可用表列表】: {', '.join(available_tables[:5])}{'...' if len(available_tables) > 5 else ''}
"""

        # Layer 4: 学习机制
        learning_section = ""
        if learned_insights:
            learning_section = f"""
💡【学习经验】:
{chr(10).join([f"   {i+1}. {insight}" for i, insight in enumerate(learned_insights[-5:])])}
"""

        # Layer 5: 迭代特定指导
        iteration_guidance = SQLGenerationPrompts._get_iteration_specific_guidance(
            iteration, iteration_history
        )

        # Layer 6: 输出格式约束
        output_format = """
📝【返回格式】严格按JSON格式，不允许任何偏差：
{
    "reasoning_process": "逐步分析过程：1.需求理解 2.表名匹配 3.字段分析 4.最终选择",
    "selected_table": "必须从真实表列表中选择，不允许编造",
    "table_business_purpose": "基于表名和字段推断的业务用途",
    "relevant_fields": ["严格从选定表的字段列表中选择"],
    "field_mappings": {
        "时间字段": "实际的时间字段名",
        "主要内容字段": "实际的内容字段名"
    },
    "query_strategy": "具体的查询策略",
    "confidence": 0.8,
    "table_validation": "确认选择的表在真实列表中: Yes/No",
    "alternatives": ["其他可能的真实表名"]
}
"""

        # 组装最终提示词
        return f"""{safety_constraints}

{task_context}

{data_info}

{learning_section}

🎯【分析步骤】:
1. 仔细阅读占位符"{placeholder_name}"的业务需求
2. 逐个检查上述真实表列表，寻找相关业务表
3. 基于表名和字段名推断业务用途（如：ods_complain = 投诉数据）
4. 选择最匹配的表和字段

{output_format}

🔥【第{iteration + 1}轮迭代特别提醒】:
{iteration_guidance}
"""

    @staticmethod
    def get_sql_generation_prompt(
        selected_table: str,
        relevant_fields: List[str],
        query_strategy: str,
        field_mappings: Dict[str, str],
        placeholder_name: str,
        placeholder_analysis: str,
        learned_insights: List[str] = None,
        complexity: PromptComplexity = PromptComplexity.MEDIUM
    ) -> str:
        """SQL生成阶段提示词 - 强制约束模式"""
        
        learned_insights = learned_insights or []
        
        # 绝对化规则约束
        absolute_constraints = f"""
🔒【强制SQL生成约束】🔒 你必须严格按照推理结果生成SQL，不允许任何偏差！

🚨【绝对禁止】:
❌ 不允许使用任何其他表名（如complaints, users等）
❌ 不允许使用未在字段列表中的字段名
❌ 不允许添加任何推理结果中没有的表或字段
❌ 不允许使用JOIN其他表
"""

        # 强制要求
        forced_requirements = f"""
🎯【推理结果 - 必须严格遵守】:
✅ 强制表名: {selected_table}
✅ 强制字段: {', '.join(relevant_fields)}
✅ 查询策略: {query_strategy}
✅ 字段映射: {field_mappings}
"""

        # 历史教训
        learning_section = ""
        if learned_insights:
            learning_section = f"""
💡【历史教训】:
{chr(10).join([f"   - {insight}" for insight in learned_insights[-3:]])}
"""

        # SQL生成规则
        generation_rules = f"""
📋【SQL生成规则】:
1. 表名: 只能是 `{selected_table}` - 一个字都不能错！
2. 字段: 只能从 [{', '.join(relevant_fields)}] 中选择
3. 时间字段: {field_mappings.get('时间字段', 'complain_time')} （如需要时间过滤）
4. 语法: 适合Doris数据库的标准SQL
5. 限制: 添加 LIMIT 10 用于测试

🔍【验证检查】:
- 确认表名完全匹配: {selected_table}
- 确认字段都在允许列表中
- 确认SQL语法正确
"""

        return f"""【占位符】: "{placeholder_name}"
【强制要求】: {placeholder_analysis}

{absolute_constraints}

{forced_requirements}

{learning_section}

{generation_rules}

直接返回SQL语句（不要markdown格式，不要解释）:
"""

    @staticmethod
    def get_reflection_prompt(
        reasoning_result: Dict[str, Any],
        sql: str,
        observation_result: Dict[str, Any],
        placeholder_name: str,
        iteration: int,
        complexity: PromptComplexity = PromptComplexity.HIGH
    ) -> str:
        """反思阶段提示词 - 结构化思维强制"""
        
        errors = observation_result.get("errors", [])
        validation_results = observation_result.get("validation_results", [])
        
        return f"""
作为数据库专家，请分析第{iteration + 1}轮SQL生成失败的原因并提出改进建议。

【推理结果】:
{json.dumps(reasoning_result, ensure_ascii=False, indent=2)}

【生成的SQL】:
{sql}

【观察到的错误】:
{errors}

【验证结果详情】:
{validation_results}

【占位符】: {placeholder_name}

🔥【强制分析框架】请严格按照以下JSON格式返回，不允许偏差：

{{
    "failure_analysis": "详细的失败原因分析",
    "root_cause": "根本原因（如表选择错误、字段映射错误、SQL语法错误等）",
    "insights": [
        "经验教训1：具体描述避免什么",
        "经验教训2：具体描述应该做什么"
    ],
    "next_iteration_strategy": "下一轮迭代的改进策略",
    "alternative_approaches": [
        "备选方案1：具体的表或字段建议",
        "备选方案2：具体的查询策略建议"
    ],
    "confidence_adjustment": "置信度评估和调整建议"
}}

🚨【分析要求】:
1. 错误根因必须具体，不能模糊
2. 经验教训必须可执行，避免抽象建议
3. 改进策略必须针对具体的技术问题
4. 备选方案必须基于实际可用的表和字段
"""

    @staticmethod  
    def _build_detailed_tables_info(table_details: List[Dict[str, Any]]) -> str:
        """构建详细表结构信息"""
        if not table_details:
            return "❌ 警告: 未找到表结构信息"
        
        info_parts = []
        for i, table_detail in enumerate(table_details, 1):
            table_name = table_detail.get('name')
            columns_count = table_detail.get('columns_count', 0)
            estimated_rows = table_detail.get('estimated_rows', 0)
            
            # 关键字段智能提取
            all_columns = table_detail.get('all_columns', [])
            key_columns = [col for col in all_columns[:10]]
            
            table_info = f"""
{i}. 表名: {table_name}
   📈 统计: {columns_count}个字段, 约{estimated_rows}行数据
   🔍 关键字段: {', '.join(key_columns)}{'...' if len(all_columns) > 10 else ''}
   💡 推荐用途: 根据字段名推断业务用途
"""
            info_parts.append(table_info)
        
        return "".join(info_parts)
    
    @staticmethod
    def _get_iteration_specific_guidance(
        iteration: int, 
        iteration_history: List[Dict[str, Any]]
    ) -> str:
        """迭代特定指导"""
        
        if iteration == 0:
            return "这是第一次尝试，请仔细分析表结构，选择最合适的表。"
        
        guidance_parts = [f"这是第{iteration + 1}次尝试！"]
        
        if iteration_history:
            last_attempt = iteration_history[-1]
            last_errors = last_attempt.get('observation', {}).get('errors', [])
            
            if last_errors:
                error_patterns = []
                for error in last_errors[:2]:
                    if "表不存在" in error or "Unknown table" in error:
                        error_patterns.append("❌ 上次使用了不存在的表名，这次必须从真实表列表中选择！")
                    elif "字段不存在" in error or "Unknown column" in error:
                        error_patterns.append("❌ 上次使用了不存在的字段，这次必须从真实字段列表中选择！")
                    elif "语法错误" in error or "syntax" in error.lower():
                        error_patterns.append("❌ 上次SQL语法有误，这次注意SQL格式！")
                
                if error_patterns:
                    guidance_parts.extend([
                        "\n🔥【上次失败教训】:",
                        *error_patterns,
                        "🎯 这次必须避免相同错误，严格按照真实表结构来！"
                    ])
        
        return "\n".join(guidance_parts)


class ReportGenerationPrompts:
    """报告生成提示词集合"""
    
    @staticmethod
    def get_content_generation_prompt(
        report_type: str,
        data_summary: Dict[str, Any],
        business_context: str,
        complexity: PromptComplexity = PromptComplexity.MEDIUM
    ) -> str:
        """报告内容生成提示词"""
        
        base_constraints = """
🎯【报告生成约束】:
✅ ALWAYS 使用数据驱动的分析
✅ ALWAYS 提供具体的数字和趋势
❌ NEVER 编造数据或统计
❌ NEVER 使用模糊的表述如"大约"、"可能"
"""

        if complexity == PromptComplexity.SIMPLE:
            content_requirements = """
📋【内容要求 - 简化版】:
1. 数据摘要（3-5个关键指标）
2. 主要发现（2-3个要点）
3. 简单建议（1-2个行动项）
"""
        elif complexity == PromptComplexity.HIGH:
            content_requirements = """
📋【内容要求 - 完整版】:
1. 执行摘要（关键发现和建议）
2. 数据分析（详细指标和趋势）
3. 深度洞察（原因分析和影响评估）
4. 行动建议（具体可执行的措施）
5. 风险评估（潜在问题和缓解策略）
6. 附录（详细数据和方法说明）
"""
        else:
            content_requirements = """
📋【内容要求 - 标准版】:
1. 概要（关键指标概述）
2. 分析（数据趋势和模式）
3. 洞察（业务影响分析）
4. 建议（改进措施）
"""

        return f"""{base_constraints}

【报告类型】: {report_type}
【业务背景】: {business_context}

【数据基础】:
{json.dumps(data_summary, ensure_ascii=False, indent=2)}

{content_requirements}

🔍【质量标准】:
- 每个结论必须有数据支撑
- 趋势分析必须包含时间对比
- 建议必须具体可执行
- 语言专业且易理解

📝【输出格式】:
使用Markdown格式，包含适当的标题层级和列表结构。
"""


class PromptManager:
    """提示词管理器 - 与AI基础设施集成"""
    
    def __init__(self):
        self.templates = {
            'sql_generation': SQLGenerationPrompts,
            'report_generation': ReportGenerationPrompts,
        }
        
        # 复杂度自适应规则
        self.complexity_rules = {
            'high_stakes': PromptComplexity.CRITICAL,
            'data_modification': PromptComplexity.HIGH,
            'standard_query': PromptComplexity.MEDIUM,
            'simple_read': PromptComplexity.SIMPLE
        }
        
        self.logger = logger
    
    def get_prompt(
        self, 
        category: str, 
        prompt_type: str, 
        context: Dict[str, Any],
        complexity: Optional[PromptComplexity] = None
    ) -> str:
        """获取优化后的提示词"""
        
        try:
            if category not in self.templates:
                raise ValueError(f"Unknown prompt category: {category}")
            
            template_class = self.templates[category]
            
            # 自动复杂度评估
            if complexity is None:
                complexity = self._assess_complexity(context)
            
            # 动态方法调用
            method_name = f"get_{prompt_type}_prompt"
            if not hasattr(template_class, method_name):
                raise ValueError(f"Unknown prompt type: {prompt_type}")
            
            method = getattr(template_class, method_name)
            
            # 注入复杂度参数
            if 'complexity' in method.__code__.co_varnames:
                context['complexity'] = complexity
            
            prompt = method(**context)
            
            # 记录提示词使用情况
            self._log_prompt_usage(category, prompt_type, complexity, len(prompt))
            
            return prompt
            
        except Exception as e:
            self.logger.error(f"提示词生成失败: {category}.{prompt_type} - {e}")
            raise
    
    def _assess_complexity(self, context: Dict[str, Any]) -> PromptComplexity:
        """自动评估提示词复杂度"""
        
        # 关键操作检查
        if context.get('is_critical_operation', False):
            return PromptComplexity.CRITICAL
        
        # 错误历史检查
        error_history = context.get('error_history', [])
        iteration_history = context.get('iteration_history', [])
        
        if len(error_history) >= 3 or len(iteration_history) >= 3:
            return PromptComplexity.HIGH
        
        if len(error_history) >= 1 or len(iteration_history) >= 1:
            return PromptComplexity.HIGH
        
        # 数据复杂度检查
        if context.get('data_size', 0) > 1000:
            return PromptComplexity.HIGH
        
        # 表数量检查
        available_tables = context.get('available_tables', [])
        if len(available_tables) > 20:
            return PromptComplexity.HIGH
        
        return PromptComplexity.MEDIUM
    
    def _log_prompt_usage(self, category: str, prompt_type: str, complexity: PromptComplexity, length: int):
        """记录提示词使用情况"""
        self.logger.info(
            f"提示词使用: {category}.{prompt_type} | 复杂度: {complexity.value} | 长度: {length}"
        )


# 全局实例
prompt_manager = PromptManager()


def get_prompt_manager() -> PromptManager:
    """获取全局提示词管理器实例"""
    return prompt_manager


# 便捷函数
def get_sql_reasoning_prompt(**kwargs) -> str:
    """获取SQL推理提示词"""
    return prompt_manager.get_prompt('sql_generation', 'reasoning', kwargs)

def get_sql_generation_prompt(**kwargs) -> str:
    """获取SQL生成提示词"""
    return prompt_manager.get_prompt('sql_generation', 'sql_generation', kwargs)

def get_sql_reflection_prompt(**kwargs) -> str:
    """获取SQL反思提示词"""
    return prompt_manager.get_prompt('sql_generation', 'reflection', kwargs)

def get_report_content_prompt(**kwargs) -> str:
    """获取报告内容生成提示词"""
    return prompt_manager.get_prompt('report_generation', 'content_generation', kwargs)