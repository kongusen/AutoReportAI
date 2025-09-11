"""
增强提示系统 - 基于Claude Code的心理学导向提示工程
简化原有复杂的提示词，使用更有效的行为塑造技巧
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
import logging

from .prompts import PromptComplexity

logger = logging.getLogger(__name__)


class PsychologicalPromptBuilder:
    """
    心理学导向的提示构建器 - 基于Claude Code理念
    
    核心原理：
    1. 使用XML标签强制结构化思考
    2. 负面引导比正面指令更有效
    3. 明确的非行动指令
    4. 虚构奖惩机制增强约束力
    """
    
    @staticmethod
    def build_task_orchestration_prompt(
        goal: str,
        available_tools: List[str],
        conversation_history: List[Dict[str, Any]] = None,
        iteration: int = 0,
        context_info: str = ""
    ) -> str:
        """
        构建任务编排提示 - 使用XML标签强制思考
        
        Args:
            goal: 任务目标
            available_tools: 可用工具列表
            conversation_history: 对话历史
            iteration: 当前迭代轮次
            context_info: 上下文信息
            
        Returns:
            优化后的提示词
        """
        
        # 强制性行为约束 - 使用心理学技巧
        behavioral_constraints = PsychologicalPromptBuilder._build_behavioral_constraints(
            conversation_history, iteration
        )
        
        # 使用XML标签强制结构化思考
        structured_thinking = f"""
<task_analysis>
任务目标: {goal}
当前是第{iteration + 1}轮分析

必须回答的问题：
1. 这个任务的核心问题是什么？
2. 需要什么具体的数据或信息？
3. 预期的输出格式是什么？
</task_analysis>

<context_evaluation>
{context_info if context_info else "无特定上下文"}

基于上下文分析：
- 有哪些关键信息可以利用？
- 缺少什么必要信息？
- 需要什么额外的数据支持？
</context_evaluation>

<tool_selection>
可用工具：
{chr(10).join([f"- {tool}" for tool in available_tools])}

工具评估（必须完成）：
- 哪个工具最符合任务需求？
- 为什么选择这个工具？
- 需要哪些具体参数？
- 预期会得到什么结果？
</tool_selection>"""
        
        # 心理学强化约束
        psychological_reinforcement = """
**⚠️ 关键要求 ⚠️**：
- 你**必须**严格按照上述XML结构分析，**绝对不允许**跳过任何部分
- 每个分析步骤都**必须**给出具体答案，不能含糊其辞
- 工具选择**必须**有明确理由，不能随意选择
- **违反任何要求都将导致任务失败！**

💰 **奖励机制**：完整按照要求分析将获得额外积分
🚫 **惩罚机制**：跳过分析步骤将扣除积分并重新开始"""
        
        return f"""{behavioral_constraints}

{structured_thinking}

{psychological_reinforcement}

请以JSON格式返回最终决策：
{{"tool": "工具名", "params": {{"参数": "值"}}, "confidence": 0.8, "reasoning": "详细理由"}}"""
    
    @staticmethod
    def build_sql_analysis_prompt(
        placeholder_name: str,
        template_context: str,
        available_tables: List[str],
        error_history: List[str] = None
    ) -> str:
        """
        构建SQL分析提示 - 简化但更有效
        
        Args:
            placeholder_name: 占位符名称
            template_context: 模板上下文
            available_tables: 可用表列表
            error_history: 错误历史
            
        Returns:
            优化后的提示词
        """
        
        # 错误学习约束
        error_constraints = ""
        if error_history:
            error_constraints = f"""
🚨 **重要警告** - 以下错误**绝对不能**重复：
{chr(10).join([f"❌ {error}" for error in error_history[-3:]])}
重复这些错误将导致严重后果！
"""
        
        # 强制性表名约束 - 使用更直接的心理学技巧
        table_constraints = f"""
**🔒 绝对规则 🔒**：
- **只能**使用以下真实表名：{', '.join(available_tables[:5])}{'...' if len(available_tables) > 5 else ''}
- **绝不允许**编造表名，哪怕看起来很合理
- **绝不允许**使用 users, orders, products 等常见名称
- 违反此规则将立即终止任务！"""
        
        return f"""{error_constraints}

分析占位符：**{placeholder_name}**
出现在：{template_context[:200]}...

{table_constraints}

<business_analysis>
基于占位符名称和上下文，这个占位符需要什么业务数据？
- 数据类型：数值/文本/日期？
- 统计方式：总数/平均值/最大值？
- 时间范围：是否需要特定时间段？
</business_analysis>

<table_matching>
从真实表列表中选择最合适的表：
{chr(10).join([f"- {table}" for table in available_tables])}

选择标准：
- 表名是否与业务需求相关？
- 可能包含什么样的数据字段？
- 为什么这个表最合适？
</table_matching>

**非常重要**：你**必须**完成上述所有分析步骤！

返回JSON格式：
{{"selected_table": "表名", "business_reason": "业务理由", "expected_fields": ["字段1", "字段2"], "confidence": 0.8}}"""
    
    @staticmethod
    def build_error_recovery_prompt(
        original_goal: str,
        failed_attempts: List[Dict[str, Any]],
        available_alternatives: List[str]
    ) -> str:
        """
        构建错误恢复提示 - 基于失败学习
        
        Args:
            original_goal: 原始目标
            failed_attempts: 失败尝试列表
            available_alternatives: 可用替代方案
            
        Returns:
            错误恢复提示词
        """
        
        failure_analysis = f"""
**🔍 失败分析** - 必须从错误中学习：
原始目标：{original_goal}

失败的尝试：
{chr(10).join([f"❌ {attempt.get('tool', '未知')}: {attempt.get('error', '失败')}" for attempt in failed_attempts[-3:]])}

**⚠️ 关键教训**：上述方法已经验证失败，**绝对不能**再次尝试！"""
        
        return f"""{failure_analysis}

<failure_root_cause>
分析失败的根本原因：
- 是工具选择错误？
- 是参数设置不当？
- 是理解需求有偏差？
- 是数据源问题？
</failure_root_cause>

<alternative_strategy>
可用的替代方案：
{chr(10).join([f"- {alt}" for alt in available_alternatives])}

制定新策略：
- 如何避免之前的错误？
- 选择哪个替代方案？
- 需要调整什么参数？
- 成功的关键是什么？
</alternative_strategy>

**🔥 成功要求**：
- **必须**选择与之前完全不同的方法
- **必须**基于失败教训调整策略
- **必须**有明确的成功判断标准

返回新的执行计划：
{{"strategy": "新策略", "tool": "工具", "params": {{}}, "success_criteria": "成功标准"}}"""
    
    @staticmethod
    def _build_behavioral_constraints(
        conversation_history: List[Dict[str, Any]] = None,
        iteration: int = 0
    ) -> str:
        """构建行为约束 - 基于历史和迭代"""
        
        constraints = []
        
        # 基本约束
        constraints.append("**🎯 基本要求**：严格按照指定格式分析，不允许跳过步骤")
        
        # 迭代相关约束
        if iteration > 0:
            constraints.append(f"**🔄 迭代约束**：这是第{iteration + 1}轮，必须比前一轮更准确")
        
        # 历史错误约束
        if conversation_history:
            failed_attempts = [h for h in conversation_history if not h.get("success", True)]
            if failed_attempts:
                recent_failures = [f["tool"] for f in failed_attempts[-2:] if "tool" in f]
                if recent_failures:
                    constraints.append(f"**❌ 历史约束**：以下工具已失败，不要重复使用：{', '.join(recent_failures)}")
        
        return chr(10).join(constraints) + chr(10)


class SimplifiedPromptManager:
    """
    简化的提示词管理器 - 替换复杂的原始系统
    
    核心改进：
    1. 减少提示词长度，降低成本
    2. 使用心理学技巧提高效果
    3. 动态适应错误历史
    4. 更直接的约束表达
    """
    
    def __init__(self):
        self.builder = PsychologicalPromptBuilder()
        self.usage_stats = {"total_prompts": 0, "avg_length": 0}
    
    def get_orchestration_prompt(
        self,
        goal: str,
        available_tools: List[str],
        context: Dict[str, Any] = None
    ) -> str:
        """获取编排提示词"""
        
        conversation_history = context.get("conversation_history", []) if context else []
        iteration = context.get("iteration", 0) if context else 0
        context_info = context.get("context_info", "") if context else ""
        
        prompt = self.builder.build_task_orchestration_prompt(
            goal, available_tools, conversation_history, iteration, context_info
        )
        
        self._update_stats(prompt)
        return prompt
    
    def get_sql_analysis_prompt(
        self,
        placeholder_name: str,
        template_context: str,
        available_tables: List[str],
        error_history: List[str] = None
    ) -> str:
        """获取SQL分析提示词"""
        
        prompt = self.builder.build_sql_analysis_prompt(
            placeholder_name, template_context, available_tables, error_history
        )
        
        self._update_stats(prompt)
        return prompt
    
    def get_error_recovery_prompt(
        self,
        original_goal: str,
        failed_attempts: List[Dict[str, Any]],
        available_alternatives: List[str]
    ) -> str:
        """获取错误恢复提示词"""
        
        prompt = self.builder.build_error_recovery_prompt(
            original_goal, failed_attempts, available_alternatives
        )
        
        self._update_stats(prompt)
        return prompt
    
    def _update_stats(self, prompt: str):
        """更新使用统计"""
        self.usage_stats["total_prompts"] += 1
        current_avg = self.usage_stats["avg_length"]
        current_count = self.usage_stats["total_prompts"]
        
        # 计算新的平均长度
        new_avg = (current_avg * (current_count - 1) + len(prompt)) / current_count
        self.usage_stats["avg_length"] = int(new_avg)
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """获取使用统计"""
        return self.usage_stats.copy()


# 全局实例
_simplified_prompt_manager: Optional[SimplifiedPromptManager] = None


def get_simplified_prompt_manager() -> SimplifiedPromptManager:
    """获取简化提示词管理器实例"""
    global _simplified_prompt_manager
    if _simplified_prompt_manager is None:
        _simplified_prompt_manager = SimplifiedPromptManager()
    return _simplified_prompt_manager


# 便捷导出
__all__ = [
    "PsychologicalPromptBuilder",
    "SimplifiedPromptManager",
    "get_simplified_prompt_manager"
]