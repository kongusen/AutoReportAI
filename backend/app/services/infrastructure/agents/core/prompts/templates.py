"""
Prompt模板定义

从placeholder系统提取的高质量prompt模板，
结合ReAct机制的需求进行优化和扩展
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import json

from .context import (
    PromptContext, SQLAnalysisContext, ContextUpdateContext, 
    DataCompletionContext, ComplexityJudgeContext,
    ReActReasoningContext, ReActObservationContext, ReActReflectionContext,
    OrchestrationContext
)


class BasePromptTemplate(ABC):
    """基础prompt模板"""
    
    @abstractmethod
    def build(self, context: PromptContext) -> str:
        """构建prompt"""
        pass
    
    def _format_context_info(self, info: Any) -> str:
        """格式化上下文信息"""
        if isinstance(info, dict):
            return json.dumps(info, ensure_ascii=False, indent=2)
        elif isinstance(info, list):
            return '\n'.join([f"- {item}" for item in info])
        else:
            return str(info)


class AnalysisPromptTemplate(BasePromptTemplate):
    """分析任务prompt模板 - 来自placeholder系统的SQL分析"""
    
    def build(self, context: SQLAnalysisContext) -> str:
        """构建SQL分析prompt"""
        
        return f"""你是一个专业的数据分析师和SQL专家。请根据以下业务需求分析并生成优化的SQL查询。

业务命令：{context.business_command}

具体要求：{context.requirements}

目标：{context.target_objective}

上下文信息：{context.context_info}

数据源信息：{context.data_source_info or '暂无'}

请分析业务需求并生成相应的SQL查询，确保：
1. 查询语法正确
2. 性能优化
3. 满足业务要求
4. 包含必要的索引建议

请提供详细的分析过程和最终的SQL查询。

分析格式：
```
## 业务需求分析
[分析业务逻辑和数据需求]

## SQL查询设计
[解释查询思路和设计理念]

## 优化建议
[性能优化和索引建议]

## 最终SQL
```sql
[生成的SQL查询]
```
```"""


class UpdatePromptTemplate(BasePromptTemplate):
    """更新分析prompt模板 - 来自placeholder系统的上下文更新"""
    
    def build(self, context: ContextUpdateContext) -> str:
        """构建上下文更新分析prompt"""
        
        stored_info = "\n".join([f"- {p['name']}: {p['description']}" for p in context.stored_placeholders])
        
        return f"""你是一个智能的上下文分析师。请分析当前任务上下文的变化，判断是否需要更新已存储的占位符SQL。

当前任务上下文：{context.task_context}

当前任务信息：{context.current_task_info}

目标：{context.target_objective}

已存储的占位符：
{stored_info}

请分析：
1. 上下文变化对占位符的影响
2. 是否需要更新SQL查询
3. 更新的理由和建议
4. 置信度评估

分析格式：
```
## 上下文变化分析
[分析上下文的具体变化]

## 影响评估
[评估变化对现有占位符的影响]

## 更新决策
需要更新：是/否
理由：[详细说明]
置信度：[0-100]%

## 更新建议
[如果需要更新，提供具体的更新建议]
```

请提供详细的分析和明确的更新决策。"""


class CompletionPromptTemplate(BasePromptTemplate):
    """完成任务prompt模板 - 来自placeholder系统的数据完善"""
    
    def build(self, context: DataCompletionContext) -> str:
        """构建数据完成prompt"""
        
        data_summary = f"数据记录数：{len(context.etl_data)}"
        if context.etl_data:
            sample_data = str(context.etl_data[:3])  # 显示前3条数据
            data_summary += f"\n示例数据：{sample_data}"
        
        return f"""你是一个专业的报告撰写师和数据可视化专家。请基于以下ETL数据完善占位符内容。

占位符要求：{context.placeholder_requirements}

模板段落：{context.template_section}

ETL数据：
{data_summary}

图表生成：{'是' if context.chart_generation_needed else '否'}
目标图表类型：{context.target_chart_type or '无'}

请提供：
1. 基于数据的详细分析内容
2. 关键洞察和发现
3. 如果需要图表，请提供图表配置
4. 模板集成建议

内容格式：
```
## 数据分析
[基于ETL数据的深度分析]

## 关键洞察
[数据中的重要发现和趋势]

## 占位符内容
[可直接用于模板的内容]

## 图表配置
[如果需要图表，提供详细配置]
{{"x轴": "字段名", "y轴": "字段名", "图表类型": "类型"}}

## 集成建议
[模板使用建议]
```

内容应该专业、准确、有洞察力。"""


class ComplexityJudgeTemplate(BasePromptTemplate):
    """复杂度判断prompt模板 - 来自placeholder系统的编排复杂度判断"""
    
    def build(self, context: ComplexityJudgeContext) -> str:
        """构建复杂度判断prompt"""
        
        orchestration_json = json.dumps(
            context.orchestration_context.to_dict(), 
            ensure_ascii=False, 
            indent=2
        )
        
        return f"""你是一个智能的编排复杂度评估专家。请分析以下编排上下文，判断当前步骤需要的模型复杂度。

编排上下文（JSON格式）：
```json
{orchestration_json}
```

请基于以下维度评估复杂度：

1. **编排阶段复杂度**：
   - 初始步骤 vs 中间步骤 vs 最终步骤
   - 依赖链条的长度和复杂性

2. **上下文累积复杂度**：
   - 前序步骤的结果复杂性
   - 需要综合考虑的信息量
   - 状态变化的影响程度

3. **交互复杂度**：
   - 与其他步骤的关联程度
   - 错误传播的可能性
   - 后续步骤的依赖程度

4. **决策复杂度**：
   - 当前步骤的决策影响范围
   - 不确定性程度
   - 需要的推理深度

复杂度级别：
- **low**: 简单独立操作，上下文清晰，影响范围小
- **medium**: 中等关联操作，需要考虑部分上下文
- **high**: 高关联操作，需要深度理解上下文，影响后续步骤
- **complex**: 关键决策点，需要综合分析所有上下文，深度推理

请只返回：low、medium、high、complex

不要解释，只返回一个单词。"""


class ReActPromptTemplate(BasePromptTemplate):
    """ReAct通用prompt模板基类"""
    
    def _format_previous_steps(self, steps: List[Dict[str, Any]]) -> str:
        """格式化前序步骤"""
        if not steps:
            return "无前序步骤"
        
        formatted_steps = []
        for i, step in enumerate(steps, 1):
            step_info = f"步骤{i}:"
            if step.get("reasoning"):
                step_info += f"\n  推理: {step['reasoning']}"
            if step.get("action_results"):
                step_info += f"\n  行动结果: {step['action_results']}"
            if step.get("observation"):
                step_info += f"\n  观察: {step['observation']}"
            if step.get("reflection"):
                step_info += f"\n  反思: {step['reflection']}"
            formatted_steps.append(step_info)
        
        return "\n\n".join(formatted_steps)
    
    def _format_success_criteria(self, criteria: Dict[str, Any]) -> str:
        """格式化成功标准"""
        if not criteria:
            return "无明确标准"
        
        formatted_criteria = []
        for key, value in criteria.items():
            formatted_criteria.append(f"- {key}: {value}")
        
        return "\n".join(formatted_criteria)


class ReActReasoningTemplate(ReActPromptTemplate):
    """ReAct推理阶段prompt模板"""
    
    def build(self, context: ReActReasoningContext) -> str:
        """构建ReAct推理prompt"""
        
        previous_steps = self._format_previous_steps(context.previous_steps)
        success_criteria = self._format_success_criteria(context.success_criteria)
        
        return f"""你是一个智能的任务分析师，正在进行ReAct推理。请分析当前情况并制定行动计划。

## 任务目标
{context.objective}

## 当前状态
- 尝试次数: {context.current_attempt}/{context.max_attempts}
- 前序步骤:
{previous_steps}

## 成功标准
{success_criteria}

## 失败模式
{', '.join(context.failure_patterns) if context.failure_patterns else '无已知失败模式'}

请基于以上信息进行推理分析：

1. **当前状态分析**: 分析已有的步骤和结果
2. **问题识别**: 识别前序步骤中的问题或不足
3. **策略制定**: 制定本次尝试的具体策略
4. **行动计划**: 详细的执行计划

推理格式：
```
## 状态分析
[分析当前情况和前序步骤]

## 问题识别
[识别需要解决的问题]

## 策略制定
[本次尝试的具体策略]

## 行动计划
工具调用序列:
1. 工具名: [工具名称]
   输入: [具体输入参数]
   预期: [预期结果]

[如有多个工具调用，继续列出]
```

请提供详细的推理过程和明确的行动计划。"""


class ReActObservationTemplate(ReActPromptTemplate):
    """ReAct观察阶段prompt模板"""
    
    def build(self, context: ReActObservationContext) -> str:
        """构建ReAct观察prompt"""
        
        success_criteria = self._format_success_criteria(context.success_criteria)
        
        # 格式化工具结果
        tool_results_info = []
        for result in context.tool_results:
            result_info = f"工具: {result.get('tool_name', 'unknown')}"
            if result.get('success'):
                result_info += f"\n成功: 是\n结果: {result.get('result', 'N/A')}"
            else:
                result_info += f"\n成功: 否\n错误: {result.get('error', 'N/A')}"
            tool_results_info.append(result_info)
        
        tool_results_text = "\n\n".join(tool_results_info) if tool_results_info else "无工具执行结果"
        
        return f"""你是一个专业的结果评估师，正在进行ReAct观察分析。请评估执行结果的质量。

## 任务目标
{context.objective}

## 成功标准
{success_criteria}

## 执行结果
{tool_results_text}

请对执行结果进行质量评估：

1. **结果正确性**: 结果是否符合预期
2. **完整性检查**: 是否满足所有成功标准
3. **质量评分**: 0.0-1.0的质量分数
4. **问题识别**: 发现的具体问题
5. **改进建议**: 如果质量不佳，提供改进建议

观察格式：
```
## 正确性评估
[评估结果的正确性]

## 完整性检查
成功标准符合情况：
- 标准1: ✅/❌ [具体说明]
- 标准2: ✅/❌ [具体说明]
[继续列出所有标准]

## 质量评分
分数: [0.0-1.0]
理由: [评分理由]

## 问题识别
[发现的具体问题，如果有]

## 改进建议
[改进建议，如果需要]
```

请提供客观、详细的观察分析。"""


class ReActReflectionTemplate(ReActPromptTemplate):
    """ReAct反思阶段prompt模板"""
    
    def build(self, context: ReActReflectionContext) -> str:
        """构建ReAct反思prompt"""
        
        success_criteria = self._format_success_criteria(context.success_criteria)
        
        # 格式化观察结果
        observation_info = []
        for obs in context.observation_results:
            obs_info = f"观察项: {obs.get('item', 'unknown')}"
            obs_info += f"\n质量分数: {obs.get('quality_score', 0.0)}"
            obs_info += f"\n符合标准: {'是' if obs.get('meets_criteria', False) else '否'}"
            if obs.get('issues'):
                obs_info += f"\n发现问题: {', '.join(obs['issues'])}"
            if obs.get('suggestions'):
                obs_info += f"\n改进建议: {', '.join(obs['suggestions'])}"
            observation_info.append(obs_info)
        
        observation_text = "\n\n".join(observation_info) if observation_info else "无观察结果"
        
        return f"""你是一个智能的决策分析师，正在进行ReAct反思。请基于观察结果决定下一步行动。

## 任务目标
{context.objective}

## 当前状态
- 尝试次数: {context.current_attempt}/{context.max_attempts}
- 整体质量: {context.overall_quality:.2f}
- 符合标准: {'是' if context.meets_criteria else '否'}

## 成功标准
{success_criteria}

## 观察结果
{observation_text}

请进行深度反思并做出决策：

1. **执行评估**: 评估本次尝试的整体表现
2. **问题分析**: 深入分析发现的问题
3. **决策制定**: 决定下一步行动（继续/成功/失败）
4. **改进策略**: 如果需要继续，提供改进策略

反思格式：
```
## 执行评估
[评估本次尝试的整体表现]

## 问题分析
[深入分析核心问题]

## 决策制定
决策: [CONTINUE/SUCCESS/FAILURE]
理由: [决策理由]
置信度: [0-100]%

## 改进策略
[如果决策是CONTINUE，提供详细的改进策略]
```

请提供深思熟虑的反思分析和明确的决策。"""