"""
阶段 Prompt

定义各个执行阶段的特定提示和指导
支持阶段感知的 Prompt 生成
"""

from __future__ import annotations

import logging
from typing import Dict, List, Any, Optional

from ..types import ExecutionStage, TaskComplexity, ContextInfo

logger = logging.getLogger(__name__)


class StagePromptManager:
    """阶段提示管理器"""
    
    def __init__(self):
        self._stage_templates = self._build_stage_templates()
        self._transition_prompts = self._build_transition_prompts()
    
    def _build_stage_templates(self) -> Dict[ExecutionStage, Dict[str, str]]:
        """构建阶段模板"""
        return {
            ExecutionStage.INITIALIZATION: {
                "objective": "理解业务需求，制定执行计划",
                "key_tasks": [
                    "分析占位符中的业务需求",
                    "识别关键业务指标和维度",
                    "确定数据范围和时间窗口",
                    "制定查询执行计划"
                ],
                "tools_to_use": ["schema_discovery", "schema_retrieval"],
                "success_criteria": "明确理解业务需求，制定可行的执行计划",
                "next_stage": ExecutionStage.SCHEMA_DISCOVERY
            },
            
            ExecutionStage.SCHEMA_DISCOVERY: {
                "objective": "探索数据源结构，理解表关系",
                "key_tasks": [
                    "发现相关的数据表",
                    "获取表的详细结构信息",
                    "理解表之间的关系和约束",
                    "构建数据上下文"
                ],
                "tools_to_use": ["schema_discovery", "schema_retrieval", "schema_cache"],
                "success_criteria": "获得完整的数据结构信息，理解表关系",
                "next_stage": ExecutionStage.SQL_GENERATION
            },
            
            ExecutionStage.SQL_GENERATION: {
                "objective": "基于数据结构生成准确的SQL查询",
                "key_tasks": [
                    "设计查询逻辑和表关联",
                    "生成符合语法的SQL查询",
                    "添加适当的过滤和聚合条件",
                    "优化查询性能"
                ],
                "tools_to_use": ["sql_generator", "sql_validator"],
                "success_criteria": "生成语法正确、逻辑合理的SQL查询",
                "next_stage": ExecutionStage.SQL_VALIDATION
            },
            
            ExecutionStage.SQL_VALIDATION: {
                "objective": "验证SQL的正确性和合理性",
                "key_tasks": [
                    "检查SQL语法正确性",
                    "验证表名和字段名",
                    "检查数据类型和约束",
                    "修复发现的问题"
                ],
                "tools_to_use": ["sql_validator", "sql_column_checker", "sql_auto_fixer"],
                "success_criteria": "SQL查询通过所有验证检查",
                "next_stage": ExecutionStage.DATA_EXTRACTION
            },
            
            ExecutionStage.DATA_EXTRACTION: {
                "objective": "执行查询并获取数据结果",
                "key_tasks": [
                    "执行验证通过的SQL查询",
                    "监控执行状态和性能",
                    "获取查询结果数据",
                    "验证数据质量和完整性"
                ],
                "tools_to_use": ["sql_executor", "data_sampler"],
                "success_criteria": "成功获取准确的数据结果",
                "next_stage": ExecutionStage.ANALYSIS
            },
            
            ExecutionStage.ANALYSIS: {
                "objective": "分析数据并提供业务洞察",
                "key_tasks": [
                    "分析查询结果数据",
                    "计算关键指标和统计信息",
                    "识别数据趋势和模式",
                    "提供业务洞察和建议"
                ],
                "tools_to_use": ["data_analyzer"],
                "success_criteria": "提供有价值的业务分析和洞察",
                "next_stage": ExecutionStage.CHART_GENERATION
            },
            
            ExecutionStage.CHART_GENERATION: {
                "objective": "生成数据可视化图表",
                "key_tasks": [
                    "选择合适的图表类型",
                    "配置图表样式和参数",
                    "优化图表展示效果",
                    "确保数据可视化准确性"
                ],
                "tools_to_use": ["chart_generator", "chart_analyzer"],
                "success_criteria": "生成准确美观的数据图表",
                "next_stage": ExecutionStage.COMPLETION
            },
            
            ExecutionStage.COMPLETION: {
                "objective": "整合结果，完成最终交付",
                "key_tasks": [
                    "整合所有执行结果",
                    "进行最终质量检查",
                    "格式化输出结果",
                    "提供完整的分析报告"
                ],
                "tools_to_use": [],
                "success_criteria": "提供完整准确的分析结果",
                "next_stage": None
            }
        }
    
    def _build_transition_prompts(self) -> Dict[str, str]:
        """构建阶段转换提示"""
        return {
            "to_schema_discovery": """
## 进入 Schema 发现阶段

现在开始探索数据源结构。请：

1. **使用 schema_discovery 工具**发现与业务需求相关的表
2. **使用 schema_retrieval 工具**获取表的详细结构信息
3. **理解表之间的关系**和约束条件
4. **构建数据上下文**为后续查询做准备

重点关注：
- 表名和字段名的业务含义
- 数据类型和约束条件
- 主键和外键关系
- 索引和性能考虑
""",
            
            "to_sql_generation": """
## 进入 SQL 生成阶段

基于已获得的数据结构信息，现在开始生成SQL查询。请：

1. **设计查询逻辑**选择合适的表和字段
2. **使用 sql_generator 工具**生成SQL查询
3. **考虑查询性能**和优化策略
4. **添加必要的注释**说明查询目的

重点关注：
- 表关联的正确性
- 过滤条件的合理性
- 聚合和分组的准确性
- 查询性能的优化
""",
            
            "to_sql_validation": """
## 进入 SQL 验证阶段

生成的SQL需要经过验证确保正确性。请：

1. **使用 sql_validator 工具**检查语法正确性
2. **使用 sql_column_checker 工具**验证字段存在性
3. **检查数据类型**和约束条件
4. **使用 sql_auto_fixer 工具**修复发现的问题

重点关注：
- SQL语法的标准性
- 表名和字段名的准确性
- 数据类型的一致性
- 查询逻辑的合理性
""",
            
            "to_data_extraction": """
## 进入数据提取阶段

验证通过的SQL现在可以执行。请：

1. **使用 sql_executor 工具**执行SQL查询
2. **监控执行状态**和性能指标
3. **获取查询结果**数据
4. **使用 data_sampler 工具**进行数据采样验证

重点关注：
- 查询执行的稳定性
- 数据结果的准确性
- 数据量和性能表现
- 异常情况的处理
""",
            
            "to_analysis": """
## 进入数据分析阶段

获得数据结果后，现在进行深入分析。请：

1. **使用 data_analyzer 工具**分析数据特征
2. **计算关键指标**和统计信息
3. **识别数据趋势**和模式
4. **提供业务洞察**和建议

重点关注：
- 数据的业务含义
- 关键指标的准确性
- 趋势和模式的识别
- 业务价值的挖掘
""",
            
            "to_chart_generation": """
## 进入图表生成阶段

基于分析结果，现在生成数据可视化。请：

1. **使用 chart_generator 工具**选择合适的图表类型
2. **配置图表样式**和参数
3. **使用 chart_analyzer 工具**优化展示效果
4. **确保数据可视化**的准确性

重点关注：
- 图表类型的合适性
- 数据展示的准确性
- 视觉效果的美观性
- 交互功能的实用性
""",
            
            "to_completion": """
## 进入完成阶段

所有分析工作即将完成。请：

1. **整合所有结果**形成完整报告
2. **进行最终质量检查**
3. **格式化输出结果**
4. **提供清晰的总结**和建议

重点关注：
- 结果的完整性和准确性
- 输出的清晰性和可读性
- 建议的实用性和可操作性
- 用户体验的友好性
"""
        }
    
    def get_stage_prompt(
        self,
        stage: ExecutionStage,
        context: Optional[ContextInfo] = None,
        complexity: Optional[TaskComplexity] = None
    ) -> str:
        """
        获取阶段提示
        
        Args:
            stage: 执行阶段
            context: 上下文信息
            complexity: 任务复杂度
            
        Returns:
            阶段提示字符串
        """
        if stage not in self._stage_templates:
            logger.warning(f"⚠️ 未知的执行阶段: {stage}")
            return ""
        
        template = self._stage_templates[stage]
        
        # 构建基础提示
        prompt_parts = [
            f"# {stage.value.replace('_', ' ').title()} 阶段",
            "",
            f"## 目标\n{template['objective']}",
            "",
            "## 关键任务"
        ]
        
        # 添加关键任务
        for i, task in enumerate(template['key_tasks'], 1):
            prompt_parts.append(f"{i}. {task}")
        
        # 添加工具使用指导
        if template['tools_to_use']:
            prompt_parts.extend([
                "",
                "## 推荐工具",
                ", ".join(template['tools_to_use'])
            ])
        
        # 添加成功标准
        prompt_parts.extend([
            "",
            "## 成功标准",
            template['success_criteria']
        ])
        
        # 添加复杂度特定指导
        if complexity:
            complexity_guidance = self._get_complexity_guidance(stage, complexity)
            if complexity_guidance:
                prompt_parts.extend([
                    "",
                    "## 复杂度指导",
                    complexity_guidance
                ])
        
        # 添加上下文特定信息
        if context:
            context_info = self._build_context_guidance(context, stage)
            if context_info:
                prompt_parts.extend([
                    "",
                    "## 上下文信息",
                    context_info
                ])
        
        return "\n".join(prompt_parts)
    
    def get_transition_prompt(
        self,
        from_stage: ExecutionStage,
        to_stage: ExecutionStage
    ) -> str:
        """
        获取阶段转换提示
        
        Args:
            from_stage: 源阶段
            to_stage: 目标阶段
            
        Returns:
            转换提示字符串
        """
        transition_key = f"to_{to_stage.value}"
        
        if transition_key in self._transition_prompts:
            return self._transition_prompts[transition_key]
        
        # 默认转换提示
        return f"""
## 阶段转换

从 {from_stage.value} 阶段转换到 {to_stage.value} 阶段。

请根据当前阶段的完成情况，开始执行下一阶段的任务。
确保前一阶段的目标已经达成，然后按照下一阶段的要求继续执行。
"""
    
    def _get_complexity_guidance(
        self,
        stage: ExecutionStage,
        complexity: TaskComplexity
    ) -> str:
        """获取复杂度特定指导"""
        guidance_map = {
            (ExecutionStage.SQL_GENERATION, TaskComplexity.SIMPLE): "使用简单的单表查询，避免复杂的关联",
            (ExecutionStage.SQL_GENERATION, TaskComplexity.MEDIUM): "可以使用多表关联，适当使用聚合函数",
            (ExecutionStage.SQL_GENERATION, TaskComplexity.COMPLEX): "支持复杂查询，可以使用窗口函数、CTE等高级功能",
            
            (ExecutionStage.SQL_VALIDATION, TaskComplexity.SIMPLE): "进行基本的语法和字段检查",
            (ExecutionStage.SQL_VALIDATION, TaskComplexity.MEDIUM): "进行全面的验证，包括性能考虑",
            (ExecutionStage.SQL_VALIDATION, TaskComplexity.COMPLEX): "进行深度验证，包括优化建议",
            
            (ExecutionStage.ANALYSIS, TaskComplexity.SIMPLE): "提供基本的数据摘要和关键指标",
            (ExecutionStage.ANALYSIS, TaskComplexity.MEDIUM): "进行详细分析，提供业务洞察",
            (ExecutionStage.ANALYSIS, TaskComplexity.COMPLEX): "进行深度分析，提供多维度洞察和建议",
        }
        
        return guidance_map.get((stage, complexity), "")
    
    def _build_context_guidance(self, context: ContextInfo, stage: ExecutionStage) -> str:
        """构建上下文指导"""
        guidance_parts = []
        
        # 表信息
        if context.tables:
            guidance_parts.append(f"可用表数量: {len(context.tables)}")
            if len(context.tables) <= 5:
                table_names = [table.get('name', 'Unknown') for table in context.tables]
                guidance_parts.append(f"表名: {', '.join(table_names)}")
        
        # 列信息
        if context.columns:
            guidance_parts.append(f"相关列数量: {len(context.columns)}")
        
        # 时间窗口
        if context.time_window:
            guidance_parts.append(f"时间窗口: {context.time_window}")
        
        # 业务上下文
        if context.business_context:
            guidance_parts.append("业务上下文:")
            for key, value in context.business_context.items():
                guidance_parts.append(f"  - {key}: {value}")
        
        return "\n".join(guidance_parts) if guidance_parts else ""
    
    def get_stage_summary(self, stage: ExecutionStage) -> Dict[str, Any]:
        """获取阶段摘要"""
        if stage not in self._stage_templates:
            return {}
        
        template = self._stage_templates[stage]
        return {
            "stage": stage.value,
            "objective": template["objective"],
            "key_tasks": template["key_tasks"],
            "tools": template["tools_to_use"],
            "success_criteria": template["success_criteria"],
            "next_stage": template["next_stage"].value if template["next_stage"] else None
        }


def get_stage_prompt(
    stage: ExecutionStage,
    context: Optional[ContextInfo] = None,
    complexity: Optional[TaskComplexity] = None
) -> str:
    """
    获取阶段提示
    
    Args:
        stage: 执行阶段
        context: 上下文信息
        complexity: 任务复杂度
        
    Returns:
        阶段提示字符串
    """
    manager = StagePromptManager()
    return manager.get_stage_prompt(stage, context, complexity)


def get_transition_prompt(
    from_stage: ExecutionStage,
    to_stage: ExecutionStage
) -> str:
    """
    获取阶段转换提示
    
    Args:
        from_stage: 源阶段
        to_stage: 目标阶段
        
    Returns:
        转换提示字符串
    """
    manager = StagePromptManager()
    return manager.get_transition_prompt(from_stage, to_stage)


def get_stage_summary(stage: ExecutionStage) -> Dict[str, Any]:
    """
    获取阶段摘要
    
    Args:
        stage: 执行阶段
        
    Returns:
        阶段摘要字典
    """
    manager = StagePromptManager()
    return manager.get_stage_summary(stage)


# 预定义的阶段提示
INITIALIZATION_PROMPT = get_stage_prompt(ExecutionStage.INITIALIZATION)
SCHEMA_DISCOVERY_PROMPT = get_stage_prompt(ExecutionStage.SCHEMA_DISCOVERY)
SQL_GENERATION_PROMPT = get_stage_prompt(ExecutionStage.SQL_GENERATION)
SQL_VALIDATION_PROMPT = get_stage_prompt(ExecutionStage.SQL_VALIDATION)
DATA_EXTRACTION_PROMPT = get_stage_prompt(ExecutionStage.DATA_EXTRACTION)
ANALYSIS_PROMPT = get_stage_prompt(ExecutionStage.ANALYSIS)
CHART_GENERATION_PROMPT = get_stage_prompt(ExecutionStage.CHART_GENERATION)
COMPLETION_PROMPT = get_stage_prompt(ExecutionStage.COMPLETION)


# 导出
__all__ = [
    "StagePromptManager",
    "get_stage_prompt",
    "get_transition_prompt",
    "get_stage_summary",
    "INITIALIZATION_PROMPT",
    "SCHEMA_DISCOVERY_PROMPT",
    "SQL_GENERATION_PROMPT",
    "SQL_VALIDATION_PROMPT",
    "DATA_EXTRACTION_PROMPT",
    "ANALYSIS_PROMPT",
    "CHART_GENERATION_PROMPT",
    "COMPLETION_PROMPT",
]