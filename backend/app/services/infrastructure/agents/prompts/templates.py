"""
Prompt 模板

定义各种 Prompt 模板和格式化函数
支持动态模板生成和上下文注入
"""

from __future__ import annotations

import logging
from typing import Dict, List, Any, Optional, Union
from string import Template

from ..types import ExecutionStage, TaskComplexity, ContextInfo, AgentRequest

logger = logging.getLogger(__name__)


class PromptTemplate:
    """Prompt 模板类"""
    
    def __init__(self, template: str, variables: Optional[Dict[str, Any]] = None):
        """
        Args:
            template: 模板字符串
            variables: 默认变量值
        """
        self.template = template
        self.variables = variables or {}
        self._template = Template(template)
    
    def format(self, **kwargs) -> str:
        """
        格式化模板
        
        Args:
            **kwargs: 模板变量
            
        Returns:
            格式化后的字符串
        """
        # 合并默认变量和传入变量
        all_variables = {**self.variables, **kwargs}
        
        try:
            return self._template.safe_substitute(**all_variables)
        except Exception as e:
            logger.error(f"❌ 模板格式化失败: {e}")
            return self.template


class PromptTemplateManager:
    """Prompt 模板管理器"""
    
    def __init__(self):
        self._templates = self._build_templates()
    
    def _build_templates(self) -> Dict[str, PromptTemplate]:
        """构建模板字典"""
        return {
            # 基础模板
            "basic_request": PromptTemplate(
                template="""
# 任务请求

## 业务需求
${placeholder}

## 数据源信息
- 数据源ID: ${data_source_id}
- 用户ID: ${user_id}

## 任务配置
- 复杂度: ${complexity}
- 最大迭代次数: ${max_iterations}

${context_section}
""",
                variables={
                    "complexity": "medium",
                    "max_iterations": "10"
                }
            ),
            
            # Schema 发现模板
            "schema_discovery": PromptTemplate(
                template="""
# Schema 发现任务

## 目标
探索数据源结构，发现与业务需求相关的表。

## 业务需求
${placeholder}

## 发现策略
1. 使用 schema_discovery 工具发现相关表
2. 使用 schema_retrieval 工具获取详细结构
3. 理解表之间的关系和约束
4. 构建数据上下文

## 重点关注
- 表名和字段名的业务含义
- 数据类型和约束条件
- 主键和外键关系
- 索引和性能考虑

${schema_context}
""",
                variables={}
            ),
            
            # SQL 生成模板
            "sql_generation": PromptTemplate(
                template="""
# SQL 生成任务

## 目标
基于数据结构生成准确的Doris SQL查询。

## 业务需求
${placeholder}

## 可用数据结构
${schema_info}

## 🎯 Doris 数据库规范（必须遵守）

### 1. Doris 语法特性
- 使用标准 SQL 语法，兼容 MySQL
- 支持 OLAP 分析查询
- 支持列式存储和向量化执行
- 支持多种数据类型：TINYINT, SMALLINT, INT, BIGINT, LARGEINT, FLOAT, DOUBLE, DECIMAL, DATE, DATETIME, CHAR, VARCHAR, STRING, BOOLEAN, JSON

### 2. Doris 查询优化
- 优先使用分区字段进行过滤
- 合理使用聚合函数：SUM, COUNT, AVG, MAX, MIN, GROUP_CONCAT
- 支持窗口函数：ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD
- 支持子查询和 CTE (WITH 子句)

### 3. Doris 性能建议
- 避免 SELECT *，明确指定需要的字段
- 使用 LIMIT 限制结果集大小
- 合理使用 WHERE 条件进行数据过滤
- 利用 Doris 的列式存储特性

## ⚠️ 时间占位符要求（强制遵守）

### 🔥 核心要求
**所有基于时间周期的查询必须使用时间占位符，禁止硬编码日期！**

### 必需的时间占位符
- **{{start_date}}**: 数据开始时间（YYYY-MM-DD格式）
- **{{end_date}}**: 数据结束时间（YYYY-MM-DD格式）

### 可选的时间占位符
- **{{execution_date}}**: 执行时间（YYYY-MM-DD格式）
- **{{current_date}}**: 当前日期（YYYY-MM-DD格式）

### Doris 时间过滤示例
```sql
-- ✅ 正确：使用时间占位符（使用 <TABLE_NAME> 和 <DATE_COLUMN> 占位符，实际使用时替换为上下文中的真实表名和列名）
SELECT COUNT(*) as total_count
FROM <TABLE_NAME> 
WHERE <DATE_COLUMN> >= '{{start_date}}' 
  AND <DATE_COLUMN> <= '{{end_date}}'

-- ✅ 正确：单日期过滤
SELECT SUM(amount) as total_amount
FROM <TABLE_NAME> 
WHERE <DATE_COLUMN> = '{{start_date}}'

-- ✅ 正确：使用 BETWEEN
SELECT * FROM <TABLE_NAME> 
WHERE <DATE_COLUMN> BETWEEN '{{start_date}}' AND '{{end_date}}'

-- ❌ 错误：硬编码日期
SELECT COUNT(*) FROM <TABLE_NAME> 
WHERE <DATE_COLUMN> >= '2024-01-01' AND <DATE_COLUMN> <= '2024-01-31'

-- ❌ 错误：缺少时间过滤
SELECT COUNT(*) FROM <TABLE_NAME>
```

### Doris 数据类型处理
```sql
-- 日期类型字段
WHERE date_column >= '{{start_date}}'

-- 日期时间类型字段  
WHERE datetime_column >= '{{start_date}} 00:00:00'
  AND datetime_column <= '{{end_date}} 23:59:59'

-- 字符串类型日期字段
WHERE date_string >= '{{start_date}}'
  AND date_string <= '{{end_date}}'
```

## 生成要求
1. **必须使用Doris兼容的SQL语法**
2. **必须包含时间占位符 {{start_date}} 和 {{end_date}}**
3. **使用正确的表名和字段名**
4. **考虑Doris查询性能优化**
5. **添加适当的注释说明**
6. **禁止硬编码任何日期值**

## 查询类型
${query_type}

## 质量检查清单
- [ ] SQL语法符合Doris规范
- [ ] 包含必需的时间占位符 {{start_date}} 和 {{end_date}}
- [ ] 没有硬编码的日期值
- [ ] 使用了正确的表名和字段名
- [ ] 查询逻辑符合业务需求
- [ ] 考虑了性能优化

${additional_requirements}
""",
                variables={
                    "query_type": "Doris SELECT查询"
                }
            ),
            
            # SQL 验证模板
            "sql_validation": PromptTemplate(
                template="""
# SQL 验证任务

## 目标
验证SQL的正确性和合理性。

## 待验证的SQL
```sql
${sql_query}
```

## 验证步骤
1. 语法检查：确保SQL语法正确
2. 字段检查：验证表名和字段名存在
3. 类型检查：确认数据类型匹配
4. 逻辑检查：验证查询逻辑合理

## 数据结构参考
${schema_info}

## 修复要求
如果发现问题，请使用 sql_auto_fixer 工具进行修复。
""",
                variables={}
            ),
            
            # 数据分析模板
            "data_analysis": PromptTemplate(
                template="""
# 数据分析任务

## 目标
分析查询结果数据，提供业务洞察。

## 业务需求
${placeholder}

## 数据结果
${data_results}

## 分析要求
1. 计算关键指标和统计信息
2. 识别数据趋势和模式
3. 提供业务洞察和建议
4. 识别异常和潜在问题

## 分析维度
${analysis_dimensions}

${business_context}
""",
                variables={
                    "analysis_dimensions": "时间趋势、分类统计、关键指标"
                }
            ),
            
            # 图表生成模板
            "chart_generation": PromptTemplate(
                template="""
# 图表生成任务

## 目标
生成数据可视化图表。

## 业务需求
${placeholder}

## 数据信息
${data_summary}

## 图表要求
1. 选择合适的图表类型
2. 配置颜色、标签和样式
3. 确保数据可视化准确性
4. 优化图表展示效果

## 图表类型建议
${chart_type_suggestions}

${visualization_preferences}
""",
                variables={
                    "chart_type_suggestions": "根据数据特点选择合适的图表类型"
                }
            ),
            
            # 错误处理模板
            "error_handling": PromptTemplate(
                template="""
# 错误处理

## 错误信息
${error_message}

## 错误类型
${error_type}

## 当前状态
- 执行阶段: ${current_stage}
- 迭代次数: ${iteration_count}
- 工具调用次数: ${tool_call_count}

## 处理策略
1. 分析错误原因
2. 尝试替代方案
3. 使用降级策略
4. 提供用户友好的错误信息

## 建议操作
${suggested_actions}
""",
                variables={
                    "error_type": "执行错误"
                }
            ),
            
            # 结果总结模板
            "result_summary": PromptTemplate(
                template="""
# 执行结果总结

## 任务完成情况
${completion_status}

## 主要结果
${main_results}

## 执行统计
- 总执行时间: ${execution_time}ms
- 迭代次数: ${iterations_used}
- 工具调用次数: ${tool_calls_count}
- 质量评分: ${quality_score}

## 关键发现
${key_findings}

## 建议和后续行动
${recommendations}

${metadata_info}
""",
                variables={
                    "completion_status": "已完成"
                }
            ),

            # SQL 纠错分析模板
            "sql_error_analysis": PromptTemplate(
                template="""
# SQL 纠错专家任务

你是一个SQL纠错专家。请分析以下SQL查询的错误，并提供修复后的SQL。

## 原始SQL
```sql
${current_sql}
```

## 验证错误信息
${error_message}

## 采样数据信息
${sample_info}

## 占位符需求
${placeholder_text}

## Doris 数据库约束
- 使用标准 SQL 语法，兼容 MySQL
- 支持 OLAP 分析查询
- 时间字段必须使用占位符：{{start_date}}、{{end_date}}
- 支持聚合函数：SUM, COUNT, AVG, MAX, MIN, GROUP_CONCAT
- 支持窗口函数：ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD

## 任务要求
1. **错误分析**：分析错误原因（语法、语义、表/列不存在等）
2. **数据结构理解**：根据采样数据了解实际的表结构和列名
3. **SQL修复**：生成修复后的SQL，确保：
   - 语法正确（符合Doris规范）
   - 表名和列名存在（参考采样数据）
   - 符合占位符需求
   - 能够成功执行

## 输出格式（仅返回JSON）
```json
{
    "error_analysis": "详细的错误分析...",
    "fix_strategy": "修复策略说明...",
    "fixed_sql": "修复后的完整SQL语句",
    "changes_made": ["修改1：描述", "修改2：描述", ...]
}
```

**重要提示**：
- 请严格按照JSON格式输出
- fixed_sql字段必须包含完整可执行的SQL
- 确保修复后的SQL能通过验证
""",
                variables={}
            )
        }
    
    def get_template(self, template_name: str) -> Optional[PromptTemplate]:
        """获取模板"""
        return self._templates.get(template_name)
    
    def format_template(
        self,
        template_name: str,
        **kwargs
    ) -> str:
        """
        格式化模板
        
        Args:
            template_name: 模板名称
            **kwargs: 模板变量
            
        Returns:
            格式化后的字符串
        """
        template = self.get_template(template_name)
        if not template:
            logger.warning(f"⚠️ 未找到模板: {template_name}")
            return ""
        
        return template.format(**kwargs)
    
    def create_custom_template(
        self,
        name: str,
        template: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> PromptTemplate:
        """
        创建自定义模板
        
        Args:
            name: 模板名称
            template: 模板字符串
            variables: 默认变量
            
        Returns:
            创建的模板
        """
        custom_template = PromptTemplate(template, variables)
        self._templates[name] = custom_template
        logger.info(f"✅ 创建自定义模板: {name}")
        return custom_template


class ContextFormatter:
    """上下文格式化器"""
    
    @staticmethod
    def format_schema_context(context: ContextInfo) -> str:
        """格式化 Schema 上下文"""
        if not context.tables:
            return "暂无表结构信息"
        
        sections = ["## 表结构信息"]
        
        for table in context.tables:
            table_name = table.get('name', 'Unknown')
            table_desc = table.get('description', '')
            
            sections.append(f"### {table_name}")
            if table_desc:
                sections.append(f"**说明**: {table_desc}")
            
            # 添加列信息
            columns = table.get('columns', [])
            if columns:
                sections.append("**列信息**:")
                for col in columns:
                    col_name = col.get('name', '')
                    col_type = col.get('type', '')
                    col_desc = col.get('description', '')
                    
                    col_line = f"- {col_name} ({col_type})"
                    if col_desc:
                        col_line += f": {col_desc}"
                    sections.append(col_line)
            
            sections.append("")  # 空行分隔
        
        return "\n".join(sections)
    
    @staticmethod
    def format_business_context(context: ContextInfo) -> str:
        """格式化业务上下文"""
        if not context.business_context:
            return ""
        
        sections = ["## 业务上下文"]
        for key, value in context.business_context.items():
            sections.append(f"- **{key}**: {value}")
        
        return "\n".join(sections)
    
    @staticmethod
    def format_data_results(data: Any) -> str:
        """格式化数据结果"""
        if isinstance(data, dict):
            if 'rows' in data:
                rows = data['rows']
                if rows:
                    # 显示前几行数据
                    preview_rows = rows[:5]
                    sections = [f"## 数据结果 (共 {len(rows)} 行，显示前 {len(preview_rows)} 行)"]
                    
                    # 添加表头
                    if preview_rows and isinstance(preview_rows[0], dict):
                        headers = list(preview_rows[0].keys())
                        sections.append("| " + " | ".join(headers) + " |")
                        sections.append("| " + " | ".join(["---"] * len(headers)) + " |")
                        
                        # 添加数据行
                        for row in preview_rows:
                            values = [str(row.get(h, '')) for h in headers]
                            sections.append("| " + " | ".join(values) + " |")
                    
                    return "\n".join(sections)
        
        return f"## 数据结果\n{str(data)[:500]}..."
    
    @staticmethod
    def format_tool_calls(tool_calls: List[Dict[str, Any]]) -> str:
        """格式化工具调用历史"""
        if not tool_calls:
            return "## 工具调用历史\n无工具调用记录"
        
        sections = ["## 工具调用历史"]
        for i, call in enumerate(tool_calls, 1):
            tool_name = call.get('tool_name', 'Unknown')
            success = call.get('success', False)
            execution_time = call.get('execution_time_ms', 0)
            
            status = "✅ 成功" if success else "❌ 失败"
            sections.append(f"{i}. **{tool_name}** - {status} ({execution_time}ms)")
            
            if not success and call.get('error'):
                sections.append(f"   错误: {call['error']}")
        
        return "\n".join(sections)


def format_request_prompt(
    request: AgentRequest,
    context: Optional[ContextInfo] = None
) -> str:
    """
    格式化请求 Prompt
    
    Args:
        request: Agent 请求
        context: 上下文信息
        
    Returns:
        格式化后的 Prompt
    """
    manager = PromptTemplateManager()
    formatter = ContextFormatter()
    
    # 构建上下文部分
    context_section = ""
    if context:
        if context.tables:
            context_section += formatter.format_schema_context(context)
        if context.business_context:
            context_section += "\n\n" + formatter.format_business_context(context)
    
    return manager.format_template(
        "basic_request",
        placeholder=request.placeholder,
        data_source_id=request.data_source_id,
        user_id=request.user_id,
        complexity=request.complexity.value,
        max_iterations=request.max_iterations,
        context_section=context_section
    )


def format_stage_prompt(
    stage: ExecutionStage,
    request: AgentRequest,
    context: Optional[ContextInfo] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    格式化阶段 Prompt
    
    Args:
        stage: 执行阶段
        request: Agent 请求
        context: 上下文信息
        additional_data: 额外数据
        
    Returns:
        格式化后的 Prompt
    """
    manager = PromptTemplateManager()
    formatter = ContextFormatter()
    
    # 根据阶段选择模板
    template_map = {
        ExecutionStage.SCHEMA_DISCOVERY: "schema_discovery",
        ExecutionStage.SQL_GENERATION: "sql_generation",
        ExecutionStage.SQL_VALIDATION: "sql_validation",
        ExecutionStage.ANALYSIS: "data_analysis",
        ExecutionStage.CHART_GENERATION: "chart_generation",
    }
    
    template_name = template_map.get(stage)
    if not template_name:
        return format_request_prompt(request, context)
    
    # 准备模板变量
    variables = {
        "placeholder": request.placeholder,
        "data_source_id": request.data_source_id,
        "user_id": request.user_id,
    }
    
    # 添加上下文信息
    if context:
        if context.tables:
            variables["schema_info"] = formatter.format_schema_context(context)
        if context.business_context:
            variables["business_context"] = formatter.format_business_context(context)
    
    # 添加额外数据
    if additional_data:
        variables.update(additional_data)
    
    return manager.format_template(template_name, **variables)


def format_error_prompt(
    error_message: str,
    current_stage: ExecutionStage,
    iteration_count: int,
    tool_call_count: int,
    suggested_actions: Optional[List[str]] = None
) -> str:
    """
    格式化错误处理 Prompt
    
    Args:
        error_message: 错误信息
        current_stage: 当前阶段
        iteration_count: 迭代次数
        tool_call_count: 工具调用次数
        suggested_actions: 建议操作
        
    Returns:
        格式化后的 Prompt
    """
    manager = PromptTemplateManager()
    
    actions_text = ""
    if suggested_actions:
        actions_text = "\n".join([f"- {action}" for action in suggested_actions])
    
    return manager.format_template(
        "error_handling",
        error_message=error_message,
        current_stage=current_stage.value,
        iteration_count=iteration_count,
        tool_call_count=tool_call_count,
        suggested_actions=actions_text
    )


def format_result_summary(
    success: bool,
    main_results: str,
    execution_time: int,
    iterations_used: int,
    tool_calls_count: int,
    quality_score: float,
    key_findings: Optional[List[str]] = None,
    recommendations: Optional[List[str]] = None
) -> str:
    """
    格式化结果总结
    
    Args:
        success: 是否成功
        main_results: 主要结果
        execution_time: 执行时间
        iterations_used: 迭代次数
        tool_calls_count: 工具调用次数
        quality_score: 质量评分
        key_findings: 关键发现
        recommendations: 建议
        
    Returns:
        格式化后的总结
    """
    manager = PromptTemplateManager()
    
    findings_text = ""
    if key_findings:
        findings_text = "\n".join([f"- {finding}" for finding in key_findings])
    
    recommendations_text = ""
    if recommendations:
        recommendations_text = "\n".join([f"- {rec}" for rec in recommendations])
    
    return manager.format_template(
        "result_summary",
        completion_status="✅ 成功完成" if success else "❌ 执行失败",
        main_results=main_results,
        execution_time=execution_time,
        iterations_used=iterations_used,
        tool_calls_count=tool_calls_count,
        quality_score=f"{quality_score:.2f}",
        key_findings=findings_text,
        recommendations=recommendations_text
    )


# 导出
__all__ = [
    "PromptTemplate",
    "PromptTemplateManager",
    "ContextFormatter",
    "format_request_prompt",
    "format_stage_prompt",
    "format_error_prompt",
    "format_result_summary",
]