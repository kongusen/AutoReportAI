"""
阶段配置管理器

管理三阶段Agent的配置，包括工具集、提示词、质量阈值等
保留TT递归能力，通过Stage-Aware机制在不同阶段使用不同的工具集和提示词
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from ..types import ExecutionStage, ToolCategory

logger = logging.getLogger(__name__)


@dataclass
class StageConfig:
    """单个阶段的配置"""
    # 工具配置
    enabled_tools: List[str] = field(default_factory=list)
    tool_categories: List[ToolCategory] = field(default_factory=list)
    
    # 提示词配置
    system_prompt: str = ""
    execution_guidance: str = ""
    
    # 质量配置
    quality_threshold: float = 0.8
    max_iterations: int = 8
    
    # 阶段目标
    stage_goal: str = ""
    
    # 约束条件
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


class StageConfigManager:
    """阶段配置管理器"""
    
    def __init__(self):
        self.stage_configs: Dict[ExecutionStage, StageConfig] = {}
        self._initialize_default_configs()
        
        logger.info("🎯 [StageConfigManager] 初始化完成")
        logger.info(f"   已配置阶段: {list(self.stage_configs.keys())}")
    
    def _initialize_default_configs(self):
        """初始化默认阶段配置"""
        
        # SQL生成阶段配置
        self.stage_configs[ExecutionStage.SQL_GENERATION] = StageConfig(
            enabled_tools=[
                "schema_discovery",
                "schema_retrieval", 
                "schema_cache",
                "sql_generator",
                "sql_validator",
                "sql_column_checker",
                "sql_auto_fixer",
                "sql_executor",
            ],
            tool_categories=[
                ToolCategory.SCHEMA,
                ToolCategory.SQL,
            ],
            system_prompt=self._get_sql_stage_prompt(),
            execution_guidance=self._get_sql_execution_guidance(),
            quality_threshold=0.8,
            max_iterations=8,
            stage_goal="生成准确、高效的SQL查询",
            constraints={
                "output_format": "sql",
                "validation_required": True,
                "performance_check": True,
            },
            metadata={
                "priority": "high",
                "complexity": "medium",
                "requires_schema": True,
            }
        )
        
        # 图表生成阶段配置
        self.stage_configs[ExecutionStage.CHART_GENERATION] = StageConfig(
            enabled_tools=[
                "data_analyzer",
                "chart_type_selector",
                "chart_generator",
                "chart_validator",
                "data_sampler",
            ],
            tool_categories=[
                ToolCategory.DATA,
                ToolCategory.CHART,
            ],
            system_prompt=self._get_chart_stage_prompt(),
            execution_guidance=self._get_chart_execution_guidance(),
            quality_threshold=0.75,
            max_iterations=6,
            stage_goal="生成合适的数据可视化配置",
            constraints={
                "output_format": "chart_config",
                "data_analysis_required": True,
                "chart_type_validation": True,
            },
            metadata={
                "priority": "medium",
                "complexity": "medium",
                "requires_data": True,
            }
        )
        
        # 文档生成阶段配置
        self.stage_configs[ExecutionStage.COMPLETION] = StageConfig(
            enabled_tools=[
                "paragraph_analyzer",
                "text_generator",
                "style_checker",
                "consistency_validator",
            ],
            tool_categories=[
                ToolCategory.DATA,  # 用于分析数据
            ],
            system_prompt=self._get_document_stage_prompt(),
            execution_guidance=self._get_document_execution_guidance(),
            quality_threshold=0.85,
            max_iterations=5,
            stage_goal="生成流畅、准确的文档文本",
            constraints={
                "output_format": "text",
                "style_consistency": True,
                "data_accuracy": True,
            },
            metadata={
                "priority": "medium",
                "complexity": "low",
                "requires_context": True,
            }
        )
        
        # 初始化阶段配置（用于整体协调）
        self.stage_configs[ExecutionStage.INITIALIZATION] = StageConfig(
            enabled_tools=[
                "schema_discovery",
                "data_analyzer",
            ],
            tool_categories=[
                ToolCategory.SCHEMA,
                ToolCategory.DATA,
            ],
            system_prompt=self._get_initialization_prompt(),
            execution_guidance=self._get_initialization_guidance(),
            quality_threshold=0.7,
            max_iterations=3,
            stage_goal="初始化任务执行环境",
            constraints={
                "quick_setup": True,
                "minimal_tools": True,
            },
            metadata={
                "priority": "high",
                "complexity": "low",
                "setup_phase": True,
            }
        )
    
    def get_stage_config(self, stage: ExecutionStage) -> Optional[StageConfig]:
        """获取阶段配置"""
        config = self.stage_configs.get(stage)
        if config:
            logger.debug(f"📋 [StageConfigManager] 获取阶段配置: {stage.value}")
            logger.debug(f"   启用工具: {len(config.enabled_tools)} 个")
            logger.debug(f"   质量阈值: {config.quality_threshold}")
            logger.debug(f"   最大迭代: {config.max_iterations}")
        return config
    
    def get_enabled_tools_for_stage(self, stage: ExecutionStage) -> List[str]:
        """获取阶段启用的工具列表"""
        config = self.get_stage_config(stage)
        if config:
            return config.enabled_tools
        return []
    
    def get_system_prompt_for_stage(self, stage: ExecutionStage) -> str:
        """获取阶段的系统提示词"""
        config = self.get_stage_config(stage)
        if config:
            return config.system_prompt
        return ""
    
    def get_quality_threshold_for_stage(self, stage: ExecutionStage) -> float:
        """获取阶段的质量阈值"""
        config = self.get_stage_config(stage)
        if config:
            return config.quality_threshold
        return 0.8
    
    def get_max_iterations_for_stage(self, stage: ExecutionStage) -> int:
        """获取阶段的最大迭代次数"""
        config = self.get_stage_config(stage)
        if config:
            return config.max_iterations
        return 8
    
    def update_stage_config(self, stage: ExecutionStage, config: StageConfig):
        """更新阶段配置"""
        self.stage_configs[stage] = config
        logger.info(f"🔄 [StageConfigManager] 更新阶段配置: {stage.value}")
    
    def _get_sql_stage_prompt(self) -> str:
        """SQL阶段系统提示词"""
        return """你是一个Doris SQL生成专家，专门负责根据业务需求生成准确、高效的Doris SQL查询。

# 你的核心任务
根据占位符中的业务需求，生成符合Doris数据库语法规范的SQL查询。

# 🔥 关键要求
- **必须使用Doris兼容的SQL语法**
- **必须包含时间占位符 {{start_date}} 和 {{end_date}}**
- **禁止硬编码任何日期值**
- **所有时间相关查询必须使用时间过滤条件**

# TT递归执行流程
你将使用TT递归机制自动迭代优化，直到达到质量阈值：

1. **Thought**: 分析业务需求，理解数据关系和时间要求
2. **Tool**: 使用schema工具了解表结构和字段信息
3. **Thought**: 设计查询逻辑和SQL结构，确定时间过滤条件
4. **Tool**: 使用sql_generator生成初始Doris SQL
5. **Thought**: 评估SQL的语法和逻辑正确性，检查时间占位符使用
6. **Tool**: 使用sql_validator验证Doris语法和字段存在性
7. **Thought**: 如果有问题，分析具体原因
8. **Tool**: 使用sql_auto_fixer修复发现的问题
9. **Thought**: 再次验证，确保SQL质量和时间占位符正确性
10. **Tool**: 使用sql_executor进行干运行测试（如果可能）
11. **Thought**: 评估最终质量，决定是否继续迭代

# 质量标准
- **语法正确性**: 100% - SQL必须符合Doris语法规范
- **字段存在性**: 100% - 所有字段必须在目标表中存在
- **时间占位符**: 100% - 必须使用 {{start_date}} 和 {{end_date}}
- **逻辑正确性**: 90%+ - 查询逻辑必须符合业务需求
- **性能优化**: 80%+ - 查询应该尽可能高效

# Doris SQL示例
```sql
-- ✅ 正确示例
SELECT COUNT(*) AS total_count
FROM sales_table 
WHERE sale_date >= '{{start_date}}' 
  AND sale_date <= '{{end_date}}'

-- ❌ 错误示例（硬编码日期）
SELECT COUNT(*) FROM sales_table 
WHERE sale_date >= '2024-01-01' AND sale_date <= '2024-01-31'
```

# 重要原则
1. **优先使用工具**: 始终先使用schema工具获取准确的表结构信息
2. **时间占位符优先**: 所有时间相关查询必须使用 {{start_date}} 和 {{end_date}}
3. **迭代优化**: 使用TT递归机制持续改进，直到达到质量阈值
4. **错误处理**: 遇到问题时，使用相应的修复工具
5. **验证优先**: 每次生成SQL后都要进行验证
6. **性能考虑**: 在保证正确性的前提下，优化查询性能

持续使用TT递归迭代，直到Doris SQL达到最优状态！"""
    
    def _get_chart_stage_prompt(self) -> str:
        """图表阶段系统提示词"""
        return """你是一个数据可视化专家，专门负责根据数据特征选择并生成最合适的图表配置。

# 你的核心任务
根据ETL数据特征，选择并生成最能表达数据含义的图表配置。

# TT递归执行流程
你将使用TT递归机制自动迭代优化图表配置：

1. **Thought**: 分析数据特征（分布、趋势、关系、类型）
2. **Tool**: 使用data_analyzer深入分析数据特征
3. **Thought**: 根据数据特征确定最适合的图表类型
4. **Tool**: 使用chart_type_selector选择最佳图表类型
5. **Thought**: 设计图表元素映射和数据映射
6. **Tool**: 使用chart_generator生成图表配置
7. **Thought**: 评估图表配置的合理性和可读性
8. **Tool**: 使用chart_validator验证配置正确性
9. **Thought**: 如果需要优化，分析改进点
10. **Tool**: 重新生成优化后的配置
11. **Thought**: 最终评估，确保达到质量标准

# 质量标准
- **图表类型适配度**: 90%+ - 图表类型必须适合数据特征
- **数据映射正确性**: 100% - 数据到图表元素的映射必须准确
- **可读性**: 85%+ - 图表应该清晰易读
- **美观度**: 80%+ - 图表应该美观专业

# 图表类型选择原则
1. **时间序列数据**: 优先选择折线图、面积图
2. **分类数据**: 优先选择柱状图、条形图
3. **比例数据**: 优先选择饼图、环形图
4. **关系数据**: 优先选择散点图、气泡图
5. **分布数据**: 优先选择直方图、箱线图

# 重要原则
1. **数据驱动**: 根据数据特征选择图表类型
2. **迭代优化**: 使用TT递归持续改进配置
3. **验证配置**: 确保图表配置的语法和逻辑正确
4. **用户体验**: 考虑图表的可读性和美观性
5. **性能考虑**: 避免过于复杂的图表配置

持续迭代，选择最能表达数据的可视化方式！"""
    
    def _get_document_stage_prompt(self) -> str:
        """文档阶段系统提示词"""
        return """你是一个专业文档写作专家，专门负责基于数据生成流畅、准确、专业的文档段落。

# 你的核心任务
基于数据结果和段落上下文，生成符合文档风格的高质量文本。

# TT递归执行流程
你将使用TT递归机制自动迭代优化文档内容：

1. **Thought**: 理解段落上下文和数据含义
2. **Tool**: 使用paragraph_analyzer分析段落结构和风格要求
3. **Thought**: 设计表达方式和语言风格
4. **Tool**: 使用text_generator生成初始文本
5. **Thought**: 评估文本质量和表达效果
6. **Tool**: 使用style_checker检查语言风格和一致性
7. **Thought**: 识别需要改进的地方
8. **Tool**: 使用consistency_validator检查整体一致性
9. **Thought**: 如果需要，重新生成优化后的文本
10. **Tool**: 最终验证，确保达到质量标准

# 质量标准
- **数据准确性**: 100% - 文本中的数据必须准确无误
- **语言流畅性**: 90%+ - 文本应该流畅自然
- **风格一致性**: 85%+ - 与文档整体风格保持一致
- **专业度**: 85%+ - 文本应该专业、正式

# 写作原则
1. **数据驱动**: 基于实际数据生成文本，避免虚构
2. **风格一致**: 保持与文档整体风格的一致性
3. **逻辑清晰**: 文本逻辑应该清晰，层次分明
4. **语言规范**: 使用规范的语言表达
5. **专业表达**: 使用专业、正式的商务语言

# 重要原则
1. **准确性优先**: 确保所有数据引用准确
2. **迭代优化**: 使用TT递归持续改进文本质量
3. **风格检查**: 定期检查语言风格和一致性
4. **上下文感知**: 考虑段落在整个文档中的位置
5. **用户友好**: 生成易于理解的文本

持续优化，生成高质量的专业文档！"""
    
    def _get_initialization_prompt(self) -> str:
        """初始化阶段系统提示词"""
        return """你是一个任务初始化专家，负责为后续的SQL生成、图表生成、文档生成等任务做好准备工作。

# 你的核心任务
快速了解任务环境，为后续阶段执行做好基础准备。

# 执行流程
1. **Thought**: 分析任务需求和复杂度
2. **Tool**: 使用schema_discovery了解数据源结构
3. **Thought**: 评估数据可用性和任务可行性
4. **Tool**: 使用data_analyzer进行初步数据分析
5. **Thought**: 总结发现，为后续阶段提供指导

# 目标
- 快速了解数据源结构
- 评估任务复杂度
- 为后续阶段提供基础信息
- 确保任务环境准备就绪

保持简洁高效，为后续阶段打好基础！"""
    
    def _get_sql_execution_guidance(self) -> str:
        """SQL阶段执行指导"""
        return """# SQL生成阶段执行指导

## 执行步骤
1. **需求分析**: 仔细理解占位符中的业务需求
2. **Schema探索**: 使用schema工具了解相关表结构
3. **SQL设计**: 基于表结构设计查询逻辑
4. **SQL生成**: 使用sql_generator生成初始SQL
5. **质量验证**: 使用sql_validator验证SQL质量
6. **问题修复**: 如有问题，使用sql_auto_fixer修复
7. **性能测试**: 使用sql_executor进行干运行测试
8. **迭代优化**: 重复验证和修复，直到达到质量阈值

## 质量检查点
- SQL语法正确性
- 字段存在性验证
- 查询逻辑合理性
- 性能优化程度

## 常见问题处理
- 字段名错误 → 使用sql_column_checker检查
- 语法错误 → 使用sql_auto_fixer修复
- 性能问题 → 优化查询结构"""
    
    def _get_chart_execution_guidance(self) -> str:
        """图表阶段执行指导"""
        return """# 图表生成阶段执行指导

## 执行步骤
1. **数据分析**: 使用data_analyzer分析数据特征
2. **类型选择**: 使用chart_type_selector选择合适图表
3. **配置生成**: 使用chart_generator生成图表配置
4. **配置验证**: 使用chart_validator验证配置正确性
5. **优化改进**: 根据验证结果优化配置
6. **最终验证**: 确保配置达到质量标准

## 质量检查点
- 图表类型适配度
- 数据映射正确性
- 配置语法正确性
- 视觉效果合理性

## 图表类型选择指南
- 时间序列 → 折线图、面积图
- 分类对比 → 柱状图、条形图
- 比例展示 → 饼图、环形图
- 关系分析 → 散点图、气泡图"""
    
    def _get_document_execution_guidance(self) -> str:
        """文档阶段执行指导"""
        return """# 文档生成阶段执行指导

## 执行步骤
1. **上下文分析**: 使用paragraph_analyzer分析段落结构
2. **文本生成**: 使用text_generator生成初始文本
3. **风格检查**: 使用style_checker检查语言风格
4. **一致性验证**: 使用consistency_validator检查一致性
5. **优化改进**: 根据检查结果优化文本
6. **最终验证**: 确保文本达到质量标准

## 质量检查点
- 数据引用准确性
- 语言流畅性
- 风格一致性
- 专业表达程度

## 写作要点
- 基于真实数据生成文本
- 保持专业商务风格
- 确保逻辑清晰
- 避免重复和冗余"""
    
    def _get_initialization_guidance(self) -> str:
        """初始化阶段执行指导"""
        return """# 初始化阶段执行指导

## 执行步骤
1. **任务分析**: 理解任务需求和复杂度
2. **环境探索**: 使用schema_discovery了解数据源
3. **数据评估**: 使用data_analyzer评估数据可用性
4. **准备总结**: 为后续阶段提供基础信息

## 目标
- 快速了解数据源结构
- 评估任务可行性
- 为后续阶段做准备
- 确保环境就绪

## 输出
- 数据源结构概览
- 任务复杂度评估
- 后续阶段建议"""
    
    def get_all_stages(self) -> List[ExecutionStage]:
        """获取所有已配置的阶段"""
        return list(self.stage_configs.keys())
    
    def get_stage_metadata(self, stage: ExecutionStage) -> Dict[str, Any]:
        """获取阶段元数据"""
        config = self.get_stage_config(stage)
        if config:
            return config.metadata
        return {}
    
    def is_stage_configured(self, stage: ExecutionStage) -> bool:
        """检查阶段是否已配置"""
        return stage in self.stage_configs
    
    def get_stage_constraints(self, stage: ExecutionStage) -> Dict[str, Any]:
        """获取阶段约束条件"""
        config = self.get_stage_config(stage)
        if config:
            return config.constraints
        return {}


# 全局实例
_stage_config_manager: Optional[StageConfigManager] = None


def get_stage_config_manager() -> StageConfigManager:
    """获取全局阶段配置管理器实例"""
    global _stage_config_manager
    if _stage_config_manager is None:
        _stage_config_manager = StageConfigManager()
    return _stage_config_manager


def create_custom_stage_config_manager() -> StageConfigManager:
    """创建自定义阶段配置管理器"""
    return StageConfigManager()


# 导出
__all__ = [
    "StageConfig",
    "StageConfigManager", 
    "get_stage_config_manager",
    "create_custom_stage_config_manager",
]
