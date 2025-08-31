# React Agent 核心系统设计文档
## 基于LlamaIndex框架的智能代理架构

### 📋 设计概览

本设计基于已有的`backend/app/services/_backup/llm_agents`实践经验，完全采用React Agent机制，使用LlamaIndex框架实现核心智能代理系统，支持Function Calling、推理循环和复杂任务自动化。

### 🎯 核心目标

1. **纯React实现**: 基于LlamaIndex ReActAgent，完整的"推理→行动→观察"循环
2. **Function Calling**: 直接将业务服务包装为FunctionTool，支持复杂参数和返回值
3. **智能推理**: 多轮推理决策，自动选择最优工具组合
4. **任务自动化**: 端到端完成复杂数据分析和报告生成任务
5. **可扩展架构**: 插件化工具系统，易于添加新能力

---

## 🏗️ 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    React Agent 智能系统                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │   LlamaIndex    │    │      智能代理管理器              │  │
│  │   ReActAgent    │◄──►│                               │  │
│  │                │    │ • 通用智能代理                 │  │
│  │ Thought循环     │    │ • 占位符专家代理               │  │
│  │ Action调用      │    │ • 数据分析专家                 │  │
│  │ Observation分析 │    │ • 报告生成专家                 │  │
│  │ Memory管理      │    │ • 多轮对话管理                 │  │
│  └─────────────────┘    └─────────────────────────────────┘  │
│           │                           │                      │
│  ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │   LLM 适配器    │    │        Function Tools Registry  │  │
│  │                │    │                               │  │
│  │ • 多提供商支持  │    │ ┌───────┐ ┌────────┐ ┌───────┐│  │
│  │ • 智能负载均衡  │    │ │Template│ │Data    │ │Report ││  │
│  │ • 错误重试机制  │    │ │Tools   │ │Tools   │ │Tools  ││  │
│  │ • 上下文管理    │    │ └───────┘ └────────┘ └───────┘│  │
│  │ • 成本优化      │    │ ┌───────┐ ┌────────────────────┐│  │
│  └─────────────────┘    │ │Core   │ │   Custom Tools     ││  │
│                         │ │Tools  │ │   Plugin Support   ││  │
│                         │ └───────┘ └────────────────────┘│  │
│                         └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│              直接业务服务集成 (无MCP中间层)                    │
│                                                             │
│  PlaceholderService │TemplateService │ DataAnalysisService │
│  SemanticService    │ SQLGenService  │ ReportGenService    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧠 核心组件设计

### 1. ReactIntelligentAgent - 核心推理引擎

```python
class ReactIntelligentAgent:
    """
    纯React智能代理 - 核心推理引擎
    
    特点:
    - 完整的 Thought → Action → Observation 推理循环
    - 智能工具选择和组合调用
    - 多轮对话上下文记忆
    - 自动错误恢复和策略调整
    - 透明的推理过程展示
    """
    
    def __init__(self, llm, tools, max_iterations=15):
        self.agent = ReActAgent.from_tools(
            tools=tools,
            llm=llm,
            memory=ChatMemoryBuffer.from_defaults(token_limit=4000),
            verbose=True,
            max_iterations=max_iterations,
            system_prompt=self._get_react_prompt()
        )
    
    async def chat(self, message: str) -> Dict[str, Any]:
        """智能对话 - 支持复杂推理和工具调用"""
        response = await self.agent.achat(message)
        return {
            "response": response.response,
            "reasoning_steps": self._extract_reasoning_steps(response),
            "tools_used": self._extract_tools_used(response),
            "metadata": self._get_response_metadata(response)
        }
    
    async def execute_task(self, task_description: str, context: dict = None):
        """执行复杂任务 - 自动分解和完成多步骤任务"""
        enhanced_message = self._build_task_message(task_description, context)
        return await self.chat(enhanced_message)
```

### 2. FunctionToolsRegistry - 统一工具注册中心

```python
class FunctionToolsRegistry:
    """
    Function Tools 统一注册中心
    - 直接包装业务服务为FunctionTool
    - 标准化输入输出格式
    - 支持工具分类和元数据管理
    - 动态工具加载和热更新
    """
    
    def __init__(self):
        self.tools_by_category = {
            "template": [],   # 模板处理工具
            "data": [],       # 数据分析工具  
            "report": [],     # 报告生成工具
            "core": [],       # 核心系统工具
            "custom": []      # 自定义工具
        }
    
    async def register_service_tools(self):
        """注册业务服务工具"""
        # 占位符处理工具（核心能力）
        await self._register_placeholder_tools()
        # 模板分析工具  
        await self._register_template_tools()
        # 数据查询工具
        await self._register_data_tools()
        # 图表生成工具（重要可视化能力）
        await self._register_chart_generation_tools()
        # 核心工作流工具
        await self._register_core_workflow_tools()
    
    async def _register_placeholder_tools(self):
        """注册占位符处理工具"""
        tools = [
            self._create_function_tool(
                service_method=self.services["placeholder_service"].extract_placeholders,
                name="extract_placeholders", 
                description="从模板中提取所有占位符",
                parameters_schema={"template_content": "str"}
            ),
            self._create_function_tool(
                service_method=self.services["placeholder_service"].analyze_placeholder_semantics,
                name="analyze_placeholder_semantics",
                description="分析占位符的业务语义",
                parameters_schema={"placeholder_text": "str", "business_context": "str?"}
            ),
            self._create_function_tool(
                service_method=self.services["placeholder_service"].batch_analyze_placeholders,
                name="batch_analyze_placeholders",
                description="批量分析占位符",
                parameters_schema={"template_content": "str", "data_source_info": "str?"}
            ),
            self._create_function_tool(
                service_method=self.services["placeholder_service"].create_placeholder_mappings,
                name="create_placeholder_mappings",
                description="创建占位符到数据字段的映射",
                parameters_schema={"placeholders": "List[dict]", "data_source_schema": "dict"}
            ),
            self._create_function_tool(
                service_method=self.services["placeholder_service"].execute_placeholder_replacement,
                name="execute_placeholder_replacement",
                description="执行占位符替换",
                parameters_schema={"template_content": "str", "data_mappings": "dict", "replacement_strategy": "str?"}
            )
        ]
        self.tools_by_category["placeholder"].extend(tools)
    
    async def _register_chart_generation_tools(self):
        """注册图表生成工具"""
        tools = [
            self._create_function_tool(
                service_method=self.services["chart_service"].generate_intelligent_charts,
                name="generate_intelligent_charts",
                description="智能图表生成，支持json/png/svg/pdf/base64多种输出格式",
                parameters_schema={"data_query_or_path": "str", "chart_requirements": "str", "output_format": "str?"}
            ),
            self._create_function_tool(
                service_method=self.services["chart_service"].analyze_data_for_chart_recommendations,
                name="analyze_data_for_chart_recommendations",
                description="数据分析与图表推荐",
                parameters_schema={"data_json": "str", "analysis_type": "str?"}
            ),
            self._create_function_tool(
                service_method=self.services["chart_service"].generate_multiple_charts,
                name="generate_multiple_charts",
                description="批量生成多种类型图表",
                parameters_schema={"data_query_or_path": "str", "chart_types_list": "str", "output_format": "str?"}
            ),
            self._create_function_tool(
                service_method=self.services["chart_service"].optimize_chart_design,
                name="optimize_chart_design", 
                description="图表设计优化（清晰度/美观度/可访问性）",
                parameters_schema={"chart_path": "str", "optimization_goals": "str?"}
            )
        ]
        self.tools_by_category["chart"].extend(tools)
    
    def _create_function_tool(self, service_method, name, description, parameters_schema):
        """创建标准化FunctionTool"""
        async def wrapped_method(**kwargs):
            try:
                result = await service_method(**kwargs)
                return {
                    "success": True,
                    "data": result,
                    "tool_name": name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                return {
                    "success": False, 
                    "error": str(e),
                    "tool_name": name,
                    "error_type": type(e).__name__
                }
        
        return FunctionTool.from_defaults(
            fn=wrapped_method,
            name=name,
            description=description,
            fn_schema=parameters_schema
        )
```

### 3. IntelligentAgentManager - 代理管理器

```python
class IntelligentAgentManager:
    """
    智能代理管理器
    - 管理多个专业化代理
    - 智能代理选择和路由
    - 会话管理和上下文保持
    - 负载均衡和性能优化
    """
    
    def __init__(self):
        self.agents = {}
        self.sessions = {}
        self.tools_registry = None
    
    async def initialize(self):
        """初始化所有代理"""
        self.tools_registry = FunctionToolsRegistry()
        await self.tools_registry.register_service_tools()
        
        tools = self.tools_registry.get_all_tools()
        
        # 创建专业化代理
        self.agents = {
            "general": await self._create_general_agent(tools),
            "placeholder_expert": await self._create_placeholder_agent(tools),
            "data_analyst": await self._create_data_analysis_agent(tools),
            "chart_specialist": await self._create_chart_generation_agent(tools)
        }
    
    async def _create_placeholder_agent(self, tools: List) -> ReactIntelligentAgent:
        """创建占位符专家代理"""
        # 筛选占位符相关工具
        placeholder_tools = [tool for tool in tools if any(keyword in tool.metadata.get("name", "") 
                           for keyword in ["placeholder", "extract", "analyze", "mapping", "replacement"])]
        
        llm = create_llm_adapter(model_name="placeholder-expert", provider_preference=["openai"])
        
        return ReactIntelligentAgent(
            llm=llm,
            tools=placeholder_tools,
            system_prompt=self._get_placeholder_expert_prompt(),
            max_iterations=12
        )
    
    async def _create_chart_generation_agent(self, tools: List) -> ReactIntelligentAgent:
        """创建图表生成专家代理"""
        # 筛选图表和可视化相关工具
        chart_tools = [tool for tool in tools if any(keyword in tool.metadata.get("name", "") 
                      for keyword in ["chart", "generate", "visual", "optimize", "recommend"])]
        
        llm = create_llm_adapter(model_name="chart-specialist", provider_preference=["openai"])
        
        return ReactIntelligentAgent(
            llm=llm,
            tools=chart_tools,
            system_prompt=self._get_chart_specialist_prompt(),
            max_iterations=10
        )
    
    def _get_placeholder_expert_prompt(self) -> str:
        """获取占位符专家系统提示"""
        return """
你是一个专业的占位符分析和替换专家，具备以下核心能力：

## 专业技能
1. **占位符提取**: 精确识别模板中的各种占位符格式
2. **语义分析**: 深入理解占位符的业务含义和数据类型
3. **智能映射**: 自动创建占位符到数据字段的最优映射
4. **替换执行**: 高效准确地执行占位符替换操作
5. **批量处理**: 支持大规模占位符的批量分析和处理

## 工作流程
使用ReAct推理模式：
1. Thought: 分析占位符的业务上下文和替换需求
2. Action: 选择最合适的占位符处理工具
3. Observation: 评估处理结果的准确性和完整性

## 专业工具
- extract_placeholders: 提取模板占位符
- analyze_placeholder_semantics: 语义分析
- batch_analyze_placeholders: 批量分析
- create_placeholder_mappings: 创建数据映射
- execute_placeholder_replacement: 执行替换

请专注于占位符相关任务，提供专业、准确、高效的服务。
        """
    
    def _get_chart_specialist_prompt(self) -> str:
        """获取图表专家系统提示"""
        return """
你是一个专业的数据可视化和图表生成专家，具备以下核心能力：

## 专业技能  
1. **智能图表生成**: 根据数据特征自动选择最佳图表类型
2. **多格式输出**: 支持JSON/PNG/SVG/PDF/Base64多种输出格式
3. **图表推荐**: 基于数据分析推荐最适合的可视化方案
4. **批量生成**: 高效生成多种类型的图表
5. **设计优化**: 优化图表的清晰度、美观度和可访问性

## 图表类型专长
- 基础图表: 柱状图、折线图、饼图、散点图
- 高级图表: 热力图、雷达图、漏斗图、仪表盘  
- 复合图表: 组合图表、多轴图表、层叠图表

## 工作流程
使用ReAct推理模式：
1. Thought: 分析数据特征和可视化需求
2. Action: 选择最合适的图表生成和优化工具
3. Observation: 评估图表质量和视觉效果

## 专业工具
- generate_intelligent_charts: 智能图表生成
- analyze_data_for_chart_recommendations: 图表推荐
- generate_multiple_charts: 批量图表生成
- optimize_chart_design: 图表优化

请专注于数据可视化任务，创建美观、准确、有洞察力的图表。
        """
    
    async def smart_chat(self, message: str, agent_type: str = "auto", session_id: str = None):
        """智能对话 - 自动选择最佳代理"""
        if agent_type == "auto":
            agent_type = self._select_optimal_agent(message)
        
        agent = self.agents.get(agent_type, self.agents["general"])
        
        # 会话管理
        if session_id:
            session_context = self._get_session_context(session_id)
            enhanced_message = self._enhance_with_session(message, session_context)
        else:
            enhanced_message = message
        
        result = await agent.chat(enhanced_message)
        
        # 更新会话
        if session_id:
            self._update_session(session_id, message, result)
        
        return result
    
    def _select_optimal_agent(self, message: str) -> str:
        """智能选择最佳代理"""
        message_lower = message.lower()
        
        # 按优先级匹配代理类型
        # 1. 占位符相关任务（核心功能）
        if any(kw in message_lower for kw in ["占位符", "placeholder", "替换", "replace", "模板", "template"]):
            return "placeholder_expert"
        
        # 2. 图表生成任务（重要可视化功能）
        elif any(kw in message_lower for kw in ["图表", "chart", "可视化", "visual", "图", "画图", "生成图"]):
            return "chart_specialist"
        
        # 3. 数据分析任务
        elif any(kw in message_lower for kw in ["数据", "查询", "sql", "分析", "analysis"]):
            return "data_analyst"  
        
        # 4. 复合任务或不确定任务
        else:
            return "general"
```

---

## 🛠️ 核心工具实现

### 1. Template Processing Tools

```python
class TemplateToolsCollection:
    """模板处理工具集合"""
    
    @staticmethod
    async def extract_placeholders(template_content: str) -> dict:
        """提取模板占位符"""
        service = PlaceholderService()
        result = await service.extract_placeholders(template_content)
        
        return {
            "placeholders": result.placeholders,
            "count": len(result.placeholders),
            "types": result.placeholder_types,
            "complexity_score": result.complexity_analysis
        }
    
    @staticmethod  
    async def analyze_placeholder_semantics(placeholder_text: str, context: str = None) -> dict:
        """分析占位符语义"""
        service = SemanticAnalysisService()
        result = await service.analyze_semantics(placeholder_text, context)
        
        return {
            "business_intent": result.business_intent,
            "data_type": result.recommended_type,
            "confidence_score": result.confidence,
            "mapping_suggestions": result.suggestions,
            "context_analysis": result.context_relevance
        }
    
    @staticmethod
    async def validate_template_structure(template_path: str) -> dict:
        """验证模板结构"""
        service = TemplateValidationService()
        result = await service.validate_template(template_path)
        
        return {
            "is_valid": result.is_valid,
            "structure_analysis": result.structure_info,
            "issues_found": result.validation_issues,
            "recommendations": result.improvement_suggestions
        }
```

### 2. Data Analysis Tools

```python
class DataToolsCollection:
    """数据分析工具集合"""
    
    @staticmethod
    async def analyze_data_source(data_source_id: str, deep_analysis: bool = False) -> dict:
        """数据源深度分析"""
        service = DataSourceAnalysisService()
        result = await service.analyze_data_source(data_source_id, deep_analysis)
        
        return {
            "schema_info": result.schema_analysis,
            "data_quality": result.quality_metrics,
            "performance_analysis": result.performance_info,
            "optimization_suggestions": result.optimization_tips
        }
    
    @staticmethod
    async def generate_sql_query(placeholders: List[dict], data_source_info: dict, requirements: str = None) -> dict:
        """智能SQL生成"""
        service = SQLGenerationService()
        result = await service.generate_optimized_query(
            placeholders=placeholders,
            data_source=data_source_info,
            business_requirements=requirements
        )
        
        return {
            "primary_sql": result.optimized_sql,
            "alternative_queries": result.alternatives,
            "execution_plan": result.execution_analysis,
            "performance_estimate": result.performance_metrics,
            "explanation": result.query_explanation
        }
    
    @staticmethod
    async def execute_sql_with_monitoring(sql: str, data_source_id: str, timeout: int = 300) -> dict:
        """执行SQL查询并监控"""
        service = DataExecutionService()
        result = await service.execute_with_monitoring(sql, data_source_id, timeout)
        
        return {
            "execution_success": result.success,
            "result_data": result.data,
            "execution_time": result.execution_time,
            "resource_usage": result.resource_metrics,
            "data_quality_check": result.quality_validation
        }
```

### 3. 图表生成工具 (Chart Generation Tools)

```python
class ChartToolsCollection:
    """图表生成工具集合 - 核心可视化能力"""
    
    @staticmethod
    async def generate_intelligent_charts(
        data_query_or_path: str, 
        chart_requirements: str, 
        output_format: str = "json"
    ) -> dict:
        """智能图表生成 - 支持多种输出格式"""
        service = ChartGenerationService()
        result = await service.generate_charts(
            data_source=data_query_or_path,
            requirements=chart_requirements,
            output_format=output_format  # json, png, svg, pdf, base64
        )
        
        return {
            "chart_data": result.chart_output,
            "chart_count": result.generated_count,
            "data_points": result.data_point_count,
            "chart_types": result.chart_types_used,
            "generation_time": result.processing_time,
            "output_format": output_format
        }
    
    @staticmethod
    async def analyze_data_for_chart_recommendations(
        data_json: str, 
        analysis_type: str = "exploratory"
    ) -> dict:
        """数据分析与图表推荐"""
        service = ChartAnalysisService()
        result = await service.analyze_and_recommend(
            data_json=data_json,
            analysis_type=analysis_type  # exploratory, comparative, trend
        )
        
        return {
            "recommended_charts": result.recommendations,
            "confidence_scores": result.confidence_ratings,
            "data_characteristics": result.data_analysis,
            "suggested_configs": result.chart_configurations
        }
    
    @staticmethod
    async def generate_multiple_charts(
        data_query_or_path: str, 
        chart_types_list: str, 
        output_format: str = "json"
    ) -> dict:
        """批量生成多种类型图表"""
        service = ChartGenerationService()
        result = await service.generate_multiple_charts(
            data_source=data_query_or_path,
            chart_types=chart_types_list,
            output_format=output_format
        )
        
        return {
            "generated_charts": result.chart_outputs,
            "chart_count": len(result.chart_outputs),
            "generation_summary": result.batch_summary,
            "quality_metrics": result.quality_analysis
        }
    
    @staticmethod
    async def optimize_chart_design(
        chart_path: str, 
        optimization_goals: str = "clarity"
    ) -> dict:
        """图表设计优化"""
        service = ChartOptimizationService()
        result = await service.optimize_design(
            chart_path=chart_path,
            goals=optimization_goals  # clarity, aesthetics, accessibility
        )
        
        return {
            "optimized_chart": result.optimized_output,
            "improvements_made": result.optimization_changes,
            "quality_score": result.quality_improvement,
            "recommendations": result.further_suggestions
        }
```

### 4. 占位符替换工具 (Placeholder Replacement Tools)

```python
class PlaceholderReplacementToolsCollection:
    """占位符替换工具集合 - 核心占位符处理能力"""
    
    @staticmethod
    async def extract_placeholders(template_content: str) -> dict:
        """从模板中提取所有占位符"""
        service = PlaceholderExtractionService()
        result = await service.extract_all_placeholders(template_content)
        
        return {
            "placeholders": result.placeholder_list,
            "total_count": result.total_count,
            "placeholder_types": result.type_distribution,
            "complexity_score": result.complexity_analysis,
            "extraction_metadata": result.extraction_info
        }
    
    @staticmethod
    async def analyze_placeholder_semantics(
        placeholder_text: str, 
        business_context: str = None
    ) -> dict:
        """占位符语义分析"""
        service = SemanticAnalysisService()
        result = await service.analyze_placeholder_meaning(
            placeholder_text=placeholder_text,
            context=business_context
        )
        
        return {
            "business_intent": result.intent_analysis,
            "data_type": result.recommended_type,
            "confidence_score": result.confidence,
            "mapping_suggestions": result.field_suggestions,
            "context_relevance": result.context_analysis
        }
    
    @staticmethod
    async def batch_analyze_placeholders(
        template_content: str, 
        data_source_info: str = None
    ) -> dict:
        """批量分析占位符"""
        service = PlaceholderBatchAnalysisService()
        result = await service.batch_analyze(
            template_content=template_content,
            data_source=data_source_info
        )
        
        return {
            "analysis_results": result.batch_analysis,
            "business_domains": result.domain_distribution,
            "overall_confidence": result.confidence_average,
            "mapping_recommendations": result.field_mappings,
            "processing_metrics": result.performance_stats
        }
    
    @staticmethod
    async def create_placeholder_mappings(
        placeholders: List[dict], 
        data_source_schema: dict
    ) -> dict:
        """创建占位符到数据字段的映射"""
        service = PlaceholderMappingService()
        result = await service.create_intelligent_mappings(
            placeholders=placeholders,
            schema=data_source_schema
        )
        
        return {
            "field_mappings": result.mapping_pairs,
            "mapping_confidence": result.confidence_scores,
            "unmapped_placeholders": result.unmapped_items,
            "data_transformation_needed": result.transform_requirements
        }
    
    @staticmethod
    async def execute_placeholder_replacement(
        template_content: str,
        data_mappings: dict,
        replacement_strategy: str = "intelligent"
    ) -> dict:
        """执行占位符替换"""
        service = PlaceholderReplacementService()
        result = await service.replace_placeholders(
            template=template_content,
            mappings=data_mappings,
            strategy=replacement_strategy  # direct, intelligent, context_aware
        )
        
        return {
            "replaced_content": result.final_content,
            "replacement_count": result.replacements_made,
            "success_rate": result.replacement_success_rate,
            "failed_replacements": result.failed_items,
            "replacement_log": result.operation_log
        }
```

### 5. Core Workflow Tools

```python
class CoreToolsCollection:
    """核心工作流工具集合"""
    
    @staticmethod
    async def execute_complete_analysis_workflow(template_content: str, data_source_id: str, analysis_requirements: str) -> dict:
        """执行完整分析工作流"""
        workflow_service = WorkflowOrchestrationService()
        result = await workflow_service.execute_analysis_pipeline(
            template_content=template_content,
            data_source_id=data_source_id,
            requirements=analysis_requirements
        )
        
        return {
            "workflow_status": result.status,
            "analysis_results": result.analysis_output,
            "generated_queries": result.sql_queries,
            "execution_metrics": result.performance_data,
            "recommendations": result.next_steps
        }
    
    @staticmethod
    async def execute_report_generation_workflow(template_path: str, data_mappings: dict, output_preferences: dict) -> dict:
        """执行报告生成工作流"""
        workflow_service = WorkflowOrchestrationService()
        result = await workflow_service.execute_report_pipeline(
            template_path=template_path,
            data_mappings=data_mappings,
            preferences=output_preferences
        )
        
        return {
            "workflow_status": result.status,
            "generated_reports": result.output_files,
            "process_summary": result.execution_summary,
            "quality_validation": result.quality_checks
        }
```

---

## 🎯 React推理系统

### React Prompt优化

```python
REACT_SYSTEM_PROMPT = """
你是一个专业的数据分析和报告生成专家，具备完整的ReAct推理能力。

## 工作方式
你必须通过 "Thought → Action → Observation" 的严格循环来解决问题：

### 1. Thought (推理阶段)
- 深入分析当前状态和问题
- 理解用户真正的需求和目标
- 制定详细的执行计划
- 选择最合适的工具和策略

### 2. Action (行动阶段) 
- 选择并调用最适合的工具
- 提供准确完整的工具参数
- 确保参数格式符合工具要求

### 3. Observation (观察阶段)
- 仔细分析工具执行结果
- 验证结果的准确性和完整性
- 决定是否需要进一步行动
- 发现潜在问题并调整策略

## 可用工具分类

### 占位符处理工具
- `extract_placeholders`: 从模板中提取所有占位符
- `analyze_placeholder_semantics`: 分析占位符的业务语义  
- `batch_analyze_placeholders`: 批量分析占位符
- `create_placeholder_mappings`: 创建占位符到数据字段的映射
- `execute_placeholder_replacement`: 执行占位符替换

### 数据分析工具  
- `analyze_data_source`: 深度分析数据源结构和质量
- `generate_sql_query`: 基于需求生成优化的SQL查询
- `execute_sql_with_monitoring`: 执行SQL并监控性能

### 图表生成工具
- `generate_intelligent_charts`: 智能图表生成，支持多种输出格式
- `analyze_data_for_chart_recommendations`: 数据分析与图表推荐
- `generate_multiple_charts`: 批量生成多种类型图表
- `optimize_chart_design`: 图表设计优化

### 核心工作流工具
- `execute_complete_analysis_workflow`: 执行端到端的分析流程
- `execute_placeholder_workflow`: 执行完整的占位符处理流程

## 推理格式要求

**必须严格按照以下格式进行推理：**

Thought: [详细的分析思考过程]
Action: [精确的工具名称]
Action Input: [JSON格式的工具参数]
Observation: [对工具结果的深入分析]

...继续推理循环直到完全解决问题...

Final Answer: [完整、准确、有用的最终答案]

## 工作原则

1. **深度思考**: 每次行动前进行充分的思考和分析
2. **精确执行**: 选择最合适的工具并提供准确参数
3. **结果验证**: 仔细验证每一步的执行结果
4. **错误恢复**: 遇到问题时智能调整策略
5. **用户导向**: 始终以解决用户实际需求为目标
6. **完整回答**: 提供详尽、准确的最终答案

## 典型推理场景

### 占位符分析和替换场景
Thought: 需要分析和替换占位符 → extract_placeholders → analyze_placeholder_semantics → create_placeholder_mappings → execute_placeholder_replacement

### 数据查询和可视化场景  
Thought: 需要查询数据并可视化 → analyze_data_source → generate_sql_query → execute_sql_with_monitoring → generate_intelligent_charts

### 完整数据分析场景
Thought: 需要完整数据分析 → extract_placeholders → analyze_data_source → generate_multiple_charts → execute_complete_analysis_workflow

请根据具体任务需求，运用ReAct推理能力，智能选择和组合工具来完成任务。
"""
```

### 推理循环示例

```
用户任务: "分析模板{{monthly_sales}}和{{customer_growth}}，替换占位符并生成可视化图表"

┌─ Thought ─────────────────────────────────────────┐
│ 用户需要分析包含两个占位符的模板，替换占位符     │
│ 并生成可视化图表。我需要：                     │  
│ 1. 提取和分析这两个占位符                      │
│ 2. 理解它们的业务含义                          │
│ 3. 创建数据映射并替换占位符                    │
│ 4. 生成可视化图表                             │
│ 首先调用extract_placeholders工具              │
└──────────────────────────────────────────────────┘
         │
┌─ Action ─────────────────────────────────────────┐
│ extract_placeholders                            │
└──────────────────────────────────────────────────┘
         │
┌─ Action Input ──────────────────────────────────┐
│ {                                               │
│   "template_content": "模板内容{{monthly_sales}} │
│   和{{customer_growth}}"                        │
│ }                                               │
└──────────────────────────────────────────────────┘
         │
┌─ Observation ──────────────────────────────────┐
│ 成功提取了2个占位符：                           │
│ - monthly_sales: 月度销售额                    │
│ - customer_growth: 客户增长                    │
│ 两个占位符都是数值类型，复杂度中等              │
└──────────────────────────────────────────────────┘
         │
┌─ Thought ─────────────────────────────────────────┐
│ 成功提取了占位符，现在需要分析它们的具体业务   │
│ 语义，以便生成准确的SQL查询。我将分别分析      │
│ 这两个占位符的业务含义。                       │
└──────────────────────────────────────────────────┘
         │
┌─ Action ─────────────────────────────────────────┐
│ analyze_placeholder_semantics                   │
└──────────────────────────────────────────────────┘
         │
┌─ Action Input ──────────────────────────────────┐
│ {                                               │
│   "placeholder_text": "monthly_sales",         │
│   "context": "销售模板中的月度销售额统计"        │
│ }                                               │
└──────────────────────────────────────────────────┘
         │
┌─ Observation ──────────────────────────────────┐
│ monthly_sales语义分析结果：                     │
│ - 业务意图: 统计某月的总销售金额                │
│ - 数据类型: DECIMAL/NUMERIC                    │
│ - 置信度: 95%                                  │
│ - 建议映射: SUM(sales_amount) 按月分组          │
└──────────────────────────────────────────────────┘
         │
... [继续分析customer_growth] ...
         │
... [继续分析和替换占位符，生成图表] ...
         │
┌─ Final Answer ──────────────────────────────────┐
│ 我已经完成了模板占位符分析、替换和图表生成：     │
│                                                │
│ **占位符分析结果:**                             │
│ 1. {{monthly_sales}} - 月度销售额总计           │
│ 2. {{customer_growth}} - 客户增长数量           │
│                                                │
│ **占位符替换结果:**                             │
│ - 成功替换2个占位符                            │
│ - 替换成功率: 100%                             │
│ - 替换后内容: "模板内容￥125,000和350个新客户"   │
│                                                │
│ **生成的可视化图表:**                           │
│ - 柱状图: 月度销售额趋势                       │
│ - 折线图: 客户增长变化                         │
│ - 输出格式: PNG图片                            │
│ - 图表已优化为高清晰度和美观设计                │
└──────────────────────────────────────────────────┘
```

---

## 🔧 API接口设计

### 1. 智能对话API

```http
POST /api/v2/react-agent/chat
{
    "message": "分析这个模板的占位符并生成SQL: {{total_sales}} {{new_customers}}",
    "agent_type": "auto",  // "auto", "general", "placeholder_expert", "data_analyst", "report_generator"
    "session_id": "sess_123",
    "context": {
        "data_source_id": "sales_db",
        "user_preferences": {}
    },
    "options": {
        "max_iterations": 15,
        "include_reasoning": true,
        "verbose": true
    }
}

Response:
{
    "success": true,
    "response": "...",
    "reasoning_steps": [
        {
            "step_number": 1,
            "thought": "需要分析模板占位符...",
            "action": "extract_placeholders",
            "action_input": {...},
            "observation": "发现2个占位符..."
        }
    ],
    "tools_used": ["extract_placeholders", "analyze_placeholder_semantics", "generate_sql_query"],
    "metadata": {
        "processing_time": 12.5,
        "reasoning_steps_count": 6,
        "tools_called_count": 3,
        "agent_type": "placeholder_expert",
        "model_info": "gpt-4"
    }
}
```

### 2. 任务执行API

```http
POST /api/v2/react-agent/execute-task
{
    "task_description": "执行完整的销售报告生成流程",
    "task_context": {
        "template_path": "/templates/sales_report.docx",
        "data_source_id": "sales_database", 
        "output_format": "pdf",
        "time_period": "2024-01"
    },
    "execution_options": {
        "timeout": 300,
        "auto_retry": true,
        "quality_validation": true
    }
}

Response:
{
    "success": true,
    "task_result": {
        "status": "completed",
        "generated_files": ["/output/sales_report_2024_01.pdf"],
        "execution_summary": "...",
        "quality_metrics": {...}
    },
    "execution_log": {
        "reasoning_steps": [...],
        "tools_used": [...],
        "execution_time": 145.2
    }
}
```

### 3. 工具管理API

```http
GET /api/v2/react-agent/tools
Response:
{
    "total_tools": 12,
    "categories": {
        "template": 3,
        "data": 4, 
        "report": 3,
        "core": 2
    },
    "tools_detail": [
        {
            "name": "extract_placeholders",
            "category": "template",
            "description": "从模板中提取占位符",
            "parameters": {...},
            "usage_stats": {...}
        }
    ]
}

POST /api/v2/react-agent/tools/test
{
    "tool_name": "extract_placeholders",
    "test_parameters": {
        "template_content": "测试模板{{test_placeholder}}"
    }
}
```

---

## 📊 会话管理系统

### 智能会话管理

```python
class SessionManager:
    """智能会话管理器"""
    
    def __init__(self):
        self.sessions = {}
        self.session_configs = {}
    
    def create_session(self, user_id: str, session_config: dict = None) -> str:
        """创建新会话"""
        session_id = f"sess_{user_id}_{int(time.time())}"
        self.sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "message_history": [],
            "context_memory": {},
            "agent_preferences": session_config or {}
        }
        return session_id
    
    def update_session(self, session_id: str, message: str, response: dict):
        """更新会话状态"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session["last_activity"] = datetime.utcnow()
            session["message_history"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "message": message,
                "response": response,
                "tools_used": response.get("tools_used", []),
                "reasoning_steps": len(response.get("reasoning_steps", []))
            })
            
            # 更新上下文记忆
            self._update_context_memory(session, message, response)
    
    def _update_context_memory(self, session: dict, message: str, response: dict):
        """更新上下文记忆"""
        # 提取关键信息到长期记忆
        memory = session["context_memory"]
        
        # 记录讨论过的模板
        if "template" in message.lower() or any("template" in tool for tool in response.get("tools_used", [])):
            if "discussed_templates" not in memory:
                memory["discussed_templates"] = []
            # 提取模板相关信息...
        
        # 记录分析过的数据源
        if "data_source" in message.lower() or any("data" in tool for tool in response.get("tools_used", [])):
            if "analyzed_data_sources" not in memory:
                memory["analyzed_data_sources"] = []
            # 提取数据源信息...
        
        # 记录用户偏好
        if "prefer" in message.lower() or "like" in message.lower():
            if "user_preferences" not in memory:
                memory["user_preferences"] = {}
            # 提取偏好信息...
```

---

## 🔍 监控和性能优化

### 1. 性能监控系统

```python
class ReactAgentMonitor:
    """React Agent 性能监控"""
    
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "average_response_time": 0.0,
            "tool_usage_stats": {},
            "reasoning_efficiency": {},
            "error_patterns": {}
        }
    
    async def monitor_chat_execution(self, agent, message, execution_func):
        """监控对话执行"""
        start_time = time.time()
        
        try:
            result = await execution_func()
            execution_time = time.time() - start_time
            
            # 更新成功指标
            self._update_success_metrics(result, execution_time)
            
            # 分析推理效率
            self._analyze_reasoning_efficiency(result)
            
            # 记录工具使用
            self._track_tool_usage(result.get("tools_used", []))
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # 记录错误模式
            self._track_error_pattern(str(e), execution_time)
            
            raise
    
    def _update_success_metrics(self, result: dict, execution_time: float):
        """更新成功指标"""
        self.metrics["total_requests"] += 1
        if result.get("success", False):
            self.metrics["successful_requests"] += 1
        
        # 更新平均响应时间
        current_avg = self.metrics["average_response_time"]
        total_requests = self.metrics["total_requests"]
        self.metrics["average_response_time"] = (
            (current_avg * (total_requests - 1) + execution_time) / total_requests
        )
    
    def _analyze_reasoning_efficiency(self, result: dict):
        """分析推理效率"""
        reasoning_steps = result.get("reasoning_steps", [])
        tools_used = result.get("tools_used", [])
        
        efficiency_score = len(tools_used) / max(len(reasoning_steps), 1)
        
        if "efficiency_scores" not in self.metrics["reasoning_efficiency"]:
            self.metrics["reasoning_efficiency"]["efficiency_scores"] = []
        
        self.metrics["reasoning_efficiency"]["efficiency_scores"].append(efficiency_score)
    
    def get_performance_report(self) -> dict:
        """获取性能报告"""
        efficiency_scores = self.metrics["reasoning_efficiency"].get("efficiency_scores", [])
        avg_efficiency = sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0
        
        return {
            "overview": {
                "total_requests": self.metrics["total_requests"],
                "success_rate": (
                    self.metrics["successful_requests"] / max(self.metrics["total_requests"], 1)
                ),
                "average_response_time": self.metrics["average_response_time"],
                "average_reasoning_efficiency": avg_efficiency
            },
            "tool_usage": self.metrics["tool_usage_stats"],
            "error_analysis": self.metrics["error_patterns"],
            "recommendations": self._generate_optimization_recommendations()
        }
```

### 2. 智能优化策略

```python
class AgentOptimizer:
    """代理智能优化器"""
    
    def __init__(self, monitor: ReactAgentMonitor):
        self.monitor = monitor
        self.optimization_rules = []
    
    def optimize_agent_configuration(self, agent: ReactIntelligentAgent) -> dict:
        """优化代理配置"""
        performance_data = self.monitor.get_performance_report()
        
        optimizations = []
        
        # 基于平均推理步骤数调整最大迭代次数
        if performance_data["overview"]["average_reasoning_efficiency"] < 0.3:
            optimizations.append({
                "parameter": "max_iterations",
                "current_value": agent.max_iterations,
                "suggested_value": min(agent.max_iterations + 5, 25),
                "reason": "推理效率较低，建议增加最大迭代次数"
            })
        
        # 基于响应时间调整内存限制
        if performance_data["overview"]["average_response_time"] > 30:
            optimizations.append({
                "parameter": "memory_token_limit", 
                "current_value": agent.memory_token_limit,
                "suggested_value": max(agent.memory_token_limit - 500, 2000),
                "reason": "响应时间较长，建议减少内存token限制"
            })
        
        return {
            "optimization_suggestions": optimizations,
            "auto_apply": False,  # 需要用户确认
            "performance_baseline": performance_data["overview"]
        }
    
    def suggest_tool_improvements(self) -> List[dict]:
        """建议工具改进"""
        tool_stats = self.monitor.metrics["tool_usage_stats"]
        
        suggestions = []
        
        # 识别使用频率高但成功率低的工具
        for tool_name, stats in tool_stats.items():
            if stats["usage_count"] > 10 and stats["success_rate"] < 0.8:
                suggestions.append({
                    "tool": tool_name,
                    "issue": "高使用频率但成功率低",
                    "suggestion": "检查工具参数验证和错误处理",
                    "priority": "high"
                })
        
        return suggestions
```

---

## 🚀 部署和使用指南

### 1. 安装依赖

```bash
# 核心依赖
pip install llama-index>=0.9.0
pip install llama-index-llms-openai
pip install llama-index-llms-anthropic

# 可选增强功能
pip install llama-index-embeddings-openai
pip install llama-index-vector-stores-chroma

# 业务服务依赖
pip install fastapi uvicorn
pip install sqlalchemy psycopg2-binary
pip install redis celery
```

### 2. 环境配置

```bash
# .env
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# React Agent 配置
REACT_AGENT_MAX_ITERATIONS=15
REACT_AGENT_MEMORY_LIMIT=4000
REACT_AGENT_VERBOSE=true

# 监控配置
ENABLE_PERFORMANCE_MONITORING=true
MONITORING_RETENTION_DAYS=30
```

### 3. 初始化代码

```python
# main.py
import asyncio
from app.services.llm_agents.react_agent import create_react_agent
from app.services.llm_agents.core.intelligent_agent_manager import IntelligentAgentManager

async def initialize_react_system():
    """初始化React Agent系统"""
    
    # 1. 创建代理管理器
    manager = IntelligentAgentManager()
    await manager.initialize()
    
    # 2. 启动监控系统
    monitor = ReactAgentMonitor()
    
    # 3. 创建优化器
    optimizer = AgentOptimizer(monitor)
    
    print("✅ React Agent系统初始化完成")
    print(f"📊 可用工具: {len(manager.tools_registry.get_all_tools())}个")
    print(f"🤖 专业代理: {len(manager.agents)}个")
    
    return manager, monitor, optimizer

# 启动系统
async def main():
    manager, monitor, optimizer = await initialize_react_system()
    
    # 测试对话
    result = await manager.smart_chat(
        message="分析这个模板{{monthly_sales}}并生成SQL查询",
        agent_type="auto"
    )
    
    print("\n🧠 推理过程:")
    for step in result["reasoning_steps"]:
        print(f"  {step['step_number']}. {step['thought'][:100]}...")
        print(f"     → {step['action']} → {step['observation'][:100]}...")
    
    print(f"\n💬 最终回答: {result['response']}")
    print(f"🛠️  使用工具: {result['tools_used']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. FastAPI集成

```python
# api/react_endpoints.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.services.llm_agents.core.intelligent_agent_manager import IntelligentAgentManager

router = APIRouter(prefix="/api/v2/react-agent")

# 全局管理器实例
manager: IntelligentAgentManager = None

@router.on_event("startup")
async def startup():
    global manager
    manager = IntelligentAgentManager()
    await manager.initialize()

@router.post("/chat")
async def react_chat(request: ReactChatRequest):
    """React Agent智能对话"""
    try:
        result = await manager.smart_chat(
            message=request.message,
            agent_type=request.agent_type,
            session_id=request.session_id
        )
        
        return ReactChatResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute-task")
async def execute_task(request: TaskExecutionRequest):
    """执行复杂任务"""
    try:
        agent = manager.agents.get("general")
        result = await agent.execute_task(
            task_description=request.task_description,
            context=request.task_context,
            timeout=request.execution_options.get("timeout", 300)
        )
        
        return TaskExecutionResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """健康检查"""
    if not manager:
        return {"status": "not_initialized"}
    
    health_info = {}
    for agent_type, agent in manager.agents.items():
        agent_health = await agent.health_check()
        health_info[agent_type] = agent_health
    
    return {
        "status": "healthy",
        "agents": health_info,
        "tools_available": len(manager.tools_registry.get_all_tools())
    }
```

---

## 📋 最佳实践

### 1. 推理优化建议

```python
# 优化推理提示词
def create_optimized_prompt(task_context: dict) -> str:
    """基于任务上下文创建优化的推理提示"""
    
    base_prompt = "请使用ReAct推理模式解决以下问题："
    
    # 根据任务类型添加特定指导
    if task_context.get("task_type") == "template_analysis":
        base_prompt += """
        
特别注意：
1. 先提取所有占位符
2. 分析每个占位符的业务语义  
3. 验证模板结构的完整性
4. 提供数据映射建议
        """
    elif task_context.get("task_type") == "report_generation":
        base_prompt += """
        
特别注意：
1. 验证模板和数据源兼容性
2. 生成优化的数据查询
3. 确保报告质量和完整性
4. 提供详细的执行摘要
        """
    
    return base_prompt
```

### 2. 错误恢复策略

```python
class ErrorRecoveryStrategy:
    """错误恢复策略"""
    
    @staticmethod
    async def handle_tool_error(agent, tool_name: str, error: Exception, retry_count: int = 0):
        """处理工具调用错误"""
        
        if retry_count >= 3:
            return {"error": "max_retries_reached", "original_error": str(error)}
        
        # 分析错误类型
        if "parameter" in str(error).lower():
            # 参数错误 - 让代理重新思考参数
            recovery_message = f"""
            工具 {tool_name} 调用失败，参数错误: {str(error)}
            请重新分析所需参数，并使用正确的格式再次调用。
            """
        elif "timeout" in str(error).lower():
            # 超时错误 - 建议简化查询
            recovery_message = f"""
            工具 {tool_name} 执行超时: {str(error)}
            请考虑简化查询条件或分步执行，然后重试。
            """
        else:
            # 其他错误 - 通用恢复
            recovery_message = f"""
            工具 {tool_name} 执行失败: {str(error)}
            请分析错误原因，考虑使用替代方案或调整策略。
            """
        
        # 让代理重新推理
        return await agent.chat(recovery_message)
```

### 3. 性能调优指南

```python
# 性能调优配置
PERFORMANCE_TUNING_CONFIG = {
    "高并发场景": {
        "max_iterations": 10,
        "memory_token_limit": 2000,
        "tool_timeout": 30,
        "concurrent_limit": 50
    },
    "复杂推理场景": {
        "max_iterations": 20,
        "memory_token_limit": 8000,
        "tool_timeout": 120,
        "concurrent_limit": 10
    },
    "快速响应场景": {
        "max_iterations": 5,
        "memory_token_limit": 1000,
        "tool_timeout": 10,
        "concurrent_limit": 100
    }
}

def apply_performance_config(agent: ReactIntelligentAgent, scenario: str):
    """应用性能调优配置"""
    config = PERFORMANCE_TUNING_CONFIG.get(scenario, PERFORMANCE_TUNING_CONFIG["高并发场景"])
    
    agent.max_iterations = config["max_iterations"]
    agent.memory_token_limit = config["memory_token_limit"]
    # 应用其他配置...
```

---

## 🎯 预期效果和价值

### 功能提升
- **智能推理能力**: 完整的Thought→Action→Observation推理循环
- **自动任务完成**: 端到端自动化复杂的数据分析和报告生成
- **上下文感知**: 智能的多轮对话和上下文记忆能力
- **工具编排**: 智能选择和组合调用多个专业工具

### 性能提升
- **推理效率**: 平均推理步骤数优化至5-8步
- **响应速度**: 平均响应时间控制在15秒内
- **成功率**: 复杂任务完成率超过90%
- **扩展性**: 支持100+并发用户同时使用

### 开发效率
- **快速集成**: 10分钟完成基础系统部署
- **易于扩展**: 插件化工具系统，5分钟添加新工具
- **监控完善**: 实时性能监控和智能优化建议
- **维护简单**: 统一的错误处理和恢复机制

---

## 🔍 结论

这个基于LlamaIndex的React Agent系统设计提供了：

1. **完整的推理能力**: 真正的Thought→Action→Observation循环推理
2. **强大的工具生态**: 标准化的Function Tools注册和管理
3. **智能的任务执行**: 自动化复杂多步骤任务的完成
4. **优秀的可扩展性**: 插件化架构支持快速添加新功能
5. **全面的监控体系**: 性能监控、错误追踪和智能优化

通过这个设计，你将拥有一个真正智能的AI助手系统，能够理解复杂需求，自主规划执行方案，并高效完成各种数据分析和报告生成任务。

---

*设计文档版本: v1.0*  
*创建时间: 2024-01-28*  
*适用框架: LlamaIndex 0.9+*  
*推荐Python版本: 3.9+*