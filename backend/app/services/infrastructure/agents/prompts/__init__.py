"""
智能体提示词系统
================

基于Claude Code模式的全面智能体指令和提示词管理系统
"""

from .core_instructions import AgentCoreInstructions, get_complete_instructions
from .specialized_instructions import (
    DataAnalysisAgentInstructions,
    SystemAdministrationAgentInstructions, 
    DevelopmentAgentInstructions,
    BusinessIntelligenceAgentInstructions,
    get_specialized_instructions
)
from .tool_specific_prompts import ToolSpecificPrompts, get_tool_specific_prompt
from .error_recovery_prompts import ErrorRecoveryPrompts, ErrorType, get_error_recovery_prompt, get_complete_error_recovery_instructions

class PromptManager:
    """智能体提示词管理器"""
    
    def __init__(self):
        self.core_instructions = AgentCoreInstructions()
        self.specialized_instructions = {
            "data_analysis": DataAnalysisAgentInstructions(),
            "system_administration": SystemAdministrationAgentInstructions(),
            "development": DevelopmentAgentInstructions(), 
            "business_intelligence": BusinessIntelligenceAgentInstructions()
        }
        self.tool_prompts = ToolSpecificPrompts()
        self.error_recovery = ErrorRecoveryPrompts()
    
    def get_agent_instructions(self, agent_type: str = "general", tools: list = None) -> str:
        """
        获取特定智能体类型的完整指令
        
        Args:
            agent_type: 智能体类型 (general, data_analysis, system_administration, development, business_intelligence)
            tools: 可用工具列表
            
        Returns:
            完整的智能体指令字符串
        """
        instructions = [
            "# 智能体操作指令",
            "",
            get_complete_instructions()
        ]
        
        # 添加专业化指令
        if agent_type != "general":
            specialized = get_specialized_instructions(agent_type)
            if specialized:
                instructions.extend([
                    "",
                    f"# {agent_type.title()} 专业化指令",
                    "",
                    specialized
                ])
        
        # 添加工具特定指令
        if tools:
            instructions.extend([
                "",
                "# 工具特定使用指令",
                ""
            ])
            
            for tool_name in tools:
                tool_prompt = get_tool_specific_prompt(tool_name)
                if "未找到" not in tool_prompt:
                    instructions.extend([
                        f"## {tool_name.title()} 工具指令",
                        "",
                        tool_prompt,
                        ""
                    ])
        
        # 添加错误恢复指令
        instructions.extend([
            "",
            "# 错误恢复指令", 
            "",
            get_complete_error_recovery_instructions(ErrorType.PROCESSING_ERROR)
        ])
        
        return "\n".join(instructions)
    
    def get_tool_usage_prompt(self, tool_name: str) -> str:
        """获取特定工具的使用提示词"""
        return get_tool_specific_prompt(tool_name)
    
    def get_error_handling_prompt(self, error_type: str) -> str:
        """获取特定错误类型的处理提示词"""
        return get_error_recovery_prompt(error_type)
    
    def get_workflow_prompt(self, workflow_type: str) -> str:
        """获取特定工作流类型的提示词"""
        workflow_prompts = {
            "data_pipeline": """
# 数据管道工作流提示词

遵循六阶段数据管道模式：
1. **验证阶段** - 并行验证数据源连接和权限
2. **发现阶段** - 并行执行数据发现和模式分析  
3. **提取阶段** - 顺序执行数据提取和清洗
4. **转换阶段** - 应用业务逻辑和数据转换
5. **分析阶段** - 执行统计分析和洞察生成
6. **交付阶段** - 生成报告和可视化输出

每个阶段都必须：
- 使用TodoWrite跟踪进度
- 流式传输状态更新
- 实施错误恢复机制
- 记录详细的执行日志
""",

            "system_maintenance": """
# 系统维护工作流提示词

遵循安全优先的系统维护模式：
1. **评估阶段** - 系统健康检查和风险评估
2. **备份阶段** - 关键数据和配置备份
3. **维护阶段** - 执行维护操作（安全模式优先）
4. **验证阶段** - 验证维护结果和系统稳定性
5. **监控阶段** - 持续监控系统状态
6. **报告阶段** - 生成维护报告和建议

安全要求：
- 所有命令先尝试safe_mode=True
- 权限错误自动升级到safe_mode=False
- 维护前强制创建备份
- 失败时自动回滚机制
""",

            "code_analysis": """
# 代码分析工作流提示词

遵循全面的代码质量分析模式：
1. **发现阶段** - 并行文件扫描和结构分析
2. **静态分析阶段** - 代码质量、安全性、性能问题检测
3. **动态分析阶段** - 执行测试和性能评估（如果可用）
4. **推理阶段** - 使用ReasoningTool分析架构质量
5. **建议阶段** - 生成改进建议和优先级
6. **报告阶段** - 生成技术报告和行动计划

分析重点：
- 安全漏洞和代码注入风险
- 性能瓶颈和优化机会
- 代码可维护性和可读性
- 架构设计和最佳实践遵循
"""
        }
        
        return workflow_prompts.get(workflow_type, "通用工作流：遵循六阶段执行模式。")
    
    def get_context_aware_prompt(self, context: dict) -> str:
        """根据上下文生成动态提示词"""
        
        prompt_parts = ["# 上下文感知智能体指令"]
        
        # 基于用户角色调整
        if context.get("user_role") == "executive":
            prompt_parts.append("""
## 高管用户适配
- 优先生成执行摘要和关键洞察
- 使用商业语言而非技术术语
- 重点关注业务影响和ROI
- 提供明确的行动建议
""")
        elif context.get("user_role") == "analyst":
            prompt_parts.append("""
## 分析师用户适配  
- 提供详细的方法论说明
- 包含统计显著性检验
- 展示数据来源和质量评估
- 提供可重复的分析步骤
""")
        elif context.get("user_role") == "developer":
            prompt_parts.append("""
## 开发者用户适配
- 包含技术实现细节
- 提供代码示例和最佳实践
- 重点关注性能和可维护性
- 包含测试和部署考虑
""")
        
        # 基于时间压力调整
        if context.get("urgency") == "high":
            prompt_parts.append("""
## 高优先级任务适配
- 优先最关键的发现和建议
- 使用并行执行最大化效率
- 简化非必要的详细分析
- 提供快速决策支持
""")
        
        # 基于数据敏感性调整
        if context.get("data_sensitivity") == "high":
            prompt_parts.append("""
## 高敏感数据适配
- 强制执行最严格的安全检查
- 所有操作必须记录审计日志
- 限制数据访问和导出
- 使用假名化和数据脱敏
""")
        
        # 基于可用资源调整
        if context.get("resource_constraints"):
            constraints = context["resource_constraints"]
            if constraints.get("memory_limited"):
                prompt_parts.append("""
## 内存限制适配
- 启用流式处理和分批操作
- 限制并发操作数量
- 优先使用内存高效算法
- 自动清理临时数据
""")
            
            if constraints.get("time_limited"):
                prompt_parts.append("""
## 时间限制适配
- 使用采样而非全量分析
- 优先核心指标和关键发现
- 使用缓存加速重复操作
- 提供进度估算和中期结果
""")
        
        return "\n".join(prompt_parts)

# 全局提示词管理器实例
prompt_manager = PromptManager()

__all__ = [
    "AgentCoreInstructions",
    "DataAnalysisAgentInstructions", 
    "SystemAdministrationAgentInstructions",
    "DevelopmentAgentInstructions",
    "BusinessIntelligenceAgentInstructions",
    "ToolSpecificPrompts",
    "ErrorRecoveryPrompts",
    "ErrorType",
    "PromptManager",
    "prompt_manager",
    "get_complete_instructions",
    "get_specialized_instructions", 
    "get_tool_specific_prompt",
    "get_error_recovery_prompt",
    "get_complete_error_recovery_instructions"
]