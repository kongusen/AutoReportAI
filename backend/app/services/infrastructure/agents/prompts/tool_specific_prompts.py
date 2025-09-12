"""
工具特定提示词系统
==================

为每个智能体工具定制的详细使用指令和模式
"""

class ToolSpecificPrompts:
    """工具特定的详细使用提示词"""
    
    # === 数据工具提示词 ===
    
    SQL_GENERATOR_PROMPT = """
# SQLGeneratorTool 使用指南

## 关键使用模式

### 最佳实践：任务描述
```python
# 优秀示例：详细且上下文丰富
{
    "task_description": "查找2024年第三季度所有活跃客户的订单数据，包括订单金额、产品类别和客户地理位置信息，用于分析区域销售趋势",
    "table_names": ["customers", "orders", "products", "regions"],
    "sql_type": "SELECT",
    "database_type": "postgresql",
    "optimization_level": "advanced"
}

# 避免的示例：过于简单
{
    "task_description": "查询订单"  # 太模糊，缺少关键信息
}
```

### 复杂查询构建策略
```python
# 对于复杂分析需求，分步构建
async def build_complex_analytical_query(analysis_requirements):
    # 步骤1：基础数据查询
    base_query = await sql_generator_tool.execute({
        "task_description": f"获取{analysis_requirements['time_period']}的基础销售数据",
        "table_names": analysis_requirements["core_tables"],
        "sql_type": "SELECT",
        "optimization_level": "standard"
    })
    
    # 步骤2：添加分析维度
    enhanced_query = await sql_generator_tool.execute({
        "task_description": f"在基础查询基础上添加{analysis_requirements['dimensions']}维度分析",
        "context": f"基础查询: {base_query['sql_query']}",
        "sql_type": "SELECT", 
        "optimization_level": "advanced"
    })
    
    return enhanced_query
```

### 错误恢复模式
```python
# 自动优化级别降级
try:
    query = await sql_generator_tool.execute({
        "task_description": task,
        "optimization_level": "advanced"
    })
except GenerationError as e:
    # 降级到标准优化
    query = await sql_generator_tool.execute({
        "task_description": task + f" (简化版本，修复错误: {e})",
        "optimization_level": "standard"
    })
```
"""

    SQL_EXECUTOR_PROMPT = """
# SQLExecutorTool 安全执行指南

## 安全执行协议

### 强制安全检查
```python
# 始终从dry_run开始
async def safe_sql_execution(sql_query: str, execute_mode: str):
    # 阶段1：语法和安全验证
    dry_run_result = await sql_executor_tool.execute({
        "sql_query": sql_query,
        "database_connection": connection_string,
        "execute_mode": execute_mode,
        "dry_run": True  # 强制验证
    })
    
    if not dry_run_result["success"]:
        # 使用SQL生成器修复错误
        corrected_query = await sql_generator_tool.execute({
            "task_description": f"修复以下SQL错误: {dry_run_result['validation_result']['error']}",
            "context": f"原始查询: {sql_query}",
            "optimization_level": "basic"
        })
        sql_query = corrected_query["sql_query"]
    
    # 阶段2：实际执行
    result = await sql_executor_tool.execute({
        "sql_query": sql_query,
        "database_connection": connection_string, 
        "execute_mode": execute_mode,
        "limit_rows": 5000,  # 安全限制
        "timeout_seconds": 60
    })
    
    return result
```

### 性能优化模式
```python
# 大数据集处理策略
async def handle_large_dataset_query(query_spec):
    # 首先估算结果集大小
    count_query = await sql_generator_tool.execute({
        "task_description": f"计算以下查询的结果行数: {query_spec['description']}",
        "sql_type": "SELECT",
        "optimization_level": "basic"
    })
    
    row_estimate = await sql_executor_tool.execute({
        "sql_query": count_query["sql_query"].replace("SELECT *", "SELECT COUNT(*)"),
        "execute_mode": "read_only",
        "limit_rows": 1
    })
    
    estimated_rows = row_estimate["rows"][0]["count"]
    
    if estimated_rows > 10000:
        # 分批处理大结果集
        batch_size = 5000
        all_results = []
        
        for offset in range(0, estimated_rows, batch_size):
            batch_query = query_spec["sql_query"] + f" LIMIT {batch_size} OFFSET {offset}"
            batch_result = await sql_executor_tool.execute({
                "sql_query": batch_query,
                "execute_mode": "read_only"
            })
            all_results.extend(batch_result["rows"])
        
        return {"rows": all_results, "batched": True}
```
"""

    DATA_ANALYSIS_PROMPT = """
# DataAnalysisTool 统计分析指南

## 分析类型选择决策树

### 数据探索阶段
```python
# 始终从描述性统计开始
initial_analysis = await data_analysis_tool.execute({
    "operation": "descriptive_analysis",
    "data": dataset,
    "include_distribution": True,
    "include_outliers": True,
    "confidence_level": 0.95
})

# 基于初始结果确定下一步分析
if initial_analysis["outliers_detected"]:
    # 深入异常值分析
    outlier_analysis = await data_analysis_tool.execute({
        "operation": "outlier_analysis", 
        "data": dataset,
        "method": "isolation_forest",
        "contamination": 0.1
    })
```

### 假设检验工作流
```python
# 结构化假设检验方法
async def structured_hypothesis_testing(dataset, hypothesis):
    # 步骤1：正态性检验
    normality_test = await data_analysis_tool.execute({
        "operation": "normality_test",
        "data": dataset,
        "test_method": "shapiro_wilk"
    })
    
    # 步骤2：基于正态性选择适当测试
    if normality_test["is_normal"]:
        statistical_test = "t_test" if hypothesis["type"] == "mean_comparison" else "pearson_correlation"
    else:
        statistical_test = "mann_whitney" if hypothesis["type"] == "mean_comparison" else "spearman_correlation"
    
    # 步骤3：执行适当的统计检验
    test_result = await data_analysis_tool.execute({
        "operation": "hypothesis_testing",
        "data": dataset,
        "test_type": statistical_test,
        "hypothesis": hypothesis,
        "alpha": 0.05
    })
    
    return test_result
```

### 高级分析组合
```python
# 全面的数据分析管道
async def comprehensive_data_analysis_pipeline(dataset, analysis_objectives):
    analysis_results = {}
    
    # 1. 基础统计
    analysis_results["descriptive"] = await data_analysis_tool.execute({
        "operation": "descriptive_analysis",
        "data": dataset,
        "include_all": True
    })
    
    # 2. 相关性分析
    if len(dataset.columns) > 2:
        analysis_results["correlation"] = await data_analysis_tool.execute({
            "operation": "correlation_analysis",
            "data": dataset,
            "method": "all_methods",  # pearson, spearman, kendall
            "visualize": True
        })
    
    # 3. 时间序列分析（如果有时间列）
    if "date" in dataset.columns or "timestamp" in dataset.columns:
        analysis_results["time_series"] = await data_analysis_tool.execute({
            "operation": "time_series_analysis",
            "data": dataset,
            "forecast_periods": 12,
            "seasonality": "auto_detect"
        })
    
    # 4. 聚类分析（如果数据适合）
    if analysis_objectives.get("clustering", False):
        analysis_results["clustering"] = await data_analysis_tool.execute({
            "operation": "clustering_analysis",
            "data": dataset,
            "algorithm": "kmeans",
            "optimal_clusters": "elbow_method"
        })
    
    return analysis_results
```
"""

    REPORT_GENERATOR_PROMPT = """
# ReportGeneratorTool 报告生成指南

## 报告类型和模板选择

### 执行摘要报告
```python
# 高管级别的简洁报告
executive_report = await report_generator_tool.execute({
    "report_type": "executive",
    "data_sources": analysis_results,
    "key_metrics": top_kpis,
    "output_format": "html",
    "template_style": "executive_modern",
    "sections": [
        "executive_summary",    # 1-2段落概述
        "key_findings",        # 3-5个关键发现
        "recommendations",     # 具体行动项
        "risk_assessment"      # 风险和缓解措施
    ],
    "page_limit": 3,
    "include_appendix": False
})
```

### 技术详细报告
```python
# 面向技术团队的详细报告
technical_report = await report_generator_tool.execute({
    "report_type": "detailed",
    "data_sources": all_analysis_results,
    "methodology": analysis_methodology,
    "output_format": "pdf",
    "template_style": "technical_detailed",
    "sections": [
        "methodology",         # 分析方法说明
        "data_quality_assessment",  # 数据质量报告
        "statistical_analysis",     # 详细统计结果
        "visualizations",           # 图表和可视化
        "technical_appendix",       # 技术附录
        "code_documentation"        # 分析代码文档
    ],
    "include_code": True,
    "include_raw_data": True
})
```

### 动态报告配置
```python
# 基于数据特征动态调整报告结构
async def adaptive_report_generation(analysis_data, audience_profile):
    # 分析数据特征
    data_characteristics = {
        "has_time_series": "time_series" in analysis_data,
        "has_categorical": any("categorical" in str(col) for col in analysis_data.keys()),
        "has_correlations": "correlation" in analysis_data,
        "complexity_level": len(analysis_data)
    }
    
    # 基于受众调整报告配置
    if audience_profile["level"] == "executive":
        config = {
            "report_type": "executive",
            "focus": "business_impact",
            "detail_level": "high_level",
            "visualizations": "dashboard_style"
        }
    elif audience_profile["level"] == "analyst":
        config = {
            "report_type": "analytical", 
            "focus": "statistical_insights",
            "detail_level": "detailed",
            "visualizations": "comprehensive"
        }
    else:  # technical
        config = {
            "report_type": "technical",
            "focus": "methodology_and_results", 
            "detail_level": "exhaustive",
            "visualizations": "publication_ready"
        }
    
    # 动态添加相关部分
    sections = ["executive_summary"]
    
    if data_characteristics["has_time_series"]:
        sections.extend(["trend_analysis", "forecasting"])
    
    if data_characteristics["has_correlations"]:
        sections.append("relationship_analysis")
    
    if data_characteristics["complexity_level"] > 5:
        sections.append("detailed_methodology")
    
    config["sections"] = sections
    
    # 生成定制报告
    report = await report_generator_tool.execute(config)
    return report
```
"""

    # === 系统工具提示词 ===
    
    FILE_OPERATION_PROMPT = """
# FileOperationTool 安全文件管理指南

## 安全文件操作协议

### 路径验证和安全检查
```python
# 强制安全路径验证
def validate_file_path_safety(file_path: str) -> bool:
    # 绝对禁止的路径模式
    forbidden_patterns = [
        r'\.\./',           # 路径遍历
        r'/etc/',           # 系统配置
        r'/sys/',           # 系统文件
        r'/proc/',          # 进程文件
        r'~/',              # 用户主目录
        r'/var/log/',       # 系统日志
    ]
    
    for pattern in forbidden_patterns:
        if re.search(pattern, file_path, re.IGNORECASE):
            raise SecurityError(f"禁止的路径模式: {pattern} in {file_path}")
    
    return True

# 安全文件操作包装器
async def secure_file_operation(operation: str, **kwargs):
    file_path = kwargs.get('file_path')
    validate_file_path_safety(file_path)
    
    # 为重要操作自动备份
    if operation in ['write', 'delete', 'move'] and Path(file_path).exists():
        backup_result = await file_tool.execute({
            "operation": "copy",
            "file_path": file_path,
            "target_path": f"{file_path}.backup_{int(time.time())}"
        })
        kwargs['backup_created'] = backup_result
    
    # 执行操作
    result = await file_tool.execute({
        "operation": operation,
        **kwargs
    })
    
    return result
```

### 大文件处理策略
```python
# 智能大文件处理
async def intelligent_large_file_handling(file_path: str, operation: str):
    # 检查文件大小
    file_info = await file_tool.execute({
        "operation": "info",
        "file_path": file_path
    })
    
    size_mb = file_info["file_info"]["size_bytes"] / (1024 * 1024)
    
    if size_mb > 100:  # 100MB以上的大文件
        if operation == "read":
            # 流式读取大文件
            chunk_size = 10 * 1024 * 1024  # 10MB chunks
            chunks = []
            
            # 分块读取（这里是概念性示例）
            for offset in range(0, file_info["file_info"]["size_bytes"], chunk_size):
                chunk = await file_tool.execute({
                    "operation": "read",
                    "file_path": file_path,
                    "offset": offset,
                    "limit_bytes": chunk_size
                })
                chunks.append(chunk["content"])
            
            return {"content": "".join(chunks), "chunked": True}
        
        elif operation in ["copy", "move"]:
            # 大文件操作需要特殊处理
            return await file_tool.execute({
                "operation": operation,
                "file_path": file_path,
                "large_file_mode": True,
                "progress_callback": True
            })
    
    else:
        # 正常文件大小，标准处理
        return await file_tool.execute({
            "operation": operation,
            "file_path": file_path
        })
```
"""

    BASH_EXECUTOR_PROMPT = """
# BashExecutorTool 安全命令执行指南

## 命令安全分类体系

### 安全命令清单（safe_mode=True）
```python
SAFE_COMMANDS = {
    # 信息收集
    "information": ["ls", "pwd", "whoami", "date", "uptime", "df", "free", "ps"],
    
    # 文件查看
    "file_viewing": ["cat", "head", "tail", "less", "more", "wc", "file"],
    
    # 搜索和查找
    "search": ["find", "grep", "rg", "locate", "which", "type"],
    
    # 版本信息
    "version_check": ["python --version", "node --version", "npm --version", "git --version"],
    
    # Git只读操作
    "git_readonly": ["git status", "git log", "git diff", "git show", "git branch"]
}

# 危险命令清单（需要approval）
DANGEROUS_COMMANDS = {
    # 文件系统修改
    "file_modification": ["rm", "rmdir", "mv", "cp", "touch", "mkdir", "chmod", "chown"],
    
    # 包管理
    "package_management": ["npm install", "pip install", "apt-get", "yum", "brew"],
    
    # 构建和测试
    "build_test": ["npm run", "make", "cmake", "pytest", "jest", "mvn"],
    
    # 网络操作
    "network": ["curl", "wget", "ssh", "scp", "ping", "nc"]
}
```

### 命令执行决策逻辑
```python
async def intelligent_command_execution(command: str, context: str):
    # 阶段1：命令分类
    command_category = classify_command_safety(command)
    
    # 阶段2：上下文感知决策
    execution_strategy = await reasoning_tool.execute({
        "operation": "logical_analysis",
        "statements": [
            f"命令'{command}'在上下文'{context}'中是安全的",
            f"命令'{command}'需要文件系统写权限",
            f"命令'{command}'需要网络访问权限"
        ],
        "analysis_type": "implications"
    })
    
    # 阶段3：渐进式权限提升
    if command_category == "safe":
        # 直接以安全模式执行
        result = await bash_tool.execute({
            "command": command,
            "safe_mode": True,
            "timeout_seconds": 30
        })
    
    elif command_category == "potentially_safe":
        # 首先尝试安全模式
        try:
            result = await bash_tool.execute({
                "command": command,
                "safe_mode": True,
                "timeout_seconds": 60
            })
        except PermissionError:
            # 权限错误 - 升级到完整权限
            result = await bash_tool.execute({
                "command": command,
                "safe_mode": False,
                "capture_output": True
            })
    
    else:  # dangerous
        # 需要明确审批
        result = await bash_tool.execute({
            "command": command,
            "safe_mode": False,
            "capture_output": True,
            "environment_vars": {"AUDIT_COMMAND": "true"}
        })
    
    return result
```

### 系统监控集成
```python
# 命令执行与系统监控结合
async def monitored_command_execution(command: str):
    # 执行前系统状态
    pre_state = await bash_tool.execute({
        "operation": "system_info",
        "info_type": "system"
    })
    
    # 执行命令
    start_time = time.time()
    result = await bash_tool.execute({
        "command": command,
        "safe_mode": False,
        "capture_output": True
    })
    execution_time = time.time() - start_time
    
    # 执行后系统状态
    post_state = await bash_tool.execute({
        "operation": "system_info", 
        "info_type": "system"
    })
    
    # 分析系统影响
    system_impact = await data_analysis_tool.execute({
        "operation": "comparison_analysis",
        "data": {"pre": pre_state, "post": post_state},
        "analysis_type": "change_detection"
    })
    
    return {
        "command_result": result,
        "execution_time": execution_time,
        "system_impact": system_impact
    }
```
"""

    SEARCH_TOOL_PROMPT = """
# SearchTool 内容发现指南

## 高级搜索策略

### 多层次搜索方法
```python
async def comprehensive_content_discovery(search_objectives: Dict[str, Any]):
    search_results = {}
    
    # 层次1：文件结构探索
    file_structure = await search_tool.execute({
        "operation": "file_search",
        "pattern": "*",
        "search_path": search_objectives["base_path"],
        "recursive": True,
        "max_depth": 3,
        "group_by": "type"
    })
    
    # 层次2：内容模式搜索
    for pattern in search_objectives["content_patterns"]:
        content_matches = await search_tool.execute({
            "operation": "content_search",
            "pattern": pattern["regex"],
            "search_path": search_objectives["base_path"],
            "file_types": pattern["file_types"],
            "context_lines": 2,
            "regex_mode": True
        })
        search_results[pattern["name"]] = content_matches
    
    # 层次3：高级过滤和分析
    filtered_results = await search_tool.execute({
        "operation": "advanced_search",
        "search_path": search_objectives["base_path"],
        "criteria": {
            "size": {"operator": ">", "value": "1MB"},
            "modified": {"operator": ">", "days_ago": 7},
            "type": ".log"
        },
        "sort_by": "modified",
        "sort_order": "desc"
    })
    
    return {
        "file_structure": file_structure,
        "content_matches": search_results,
        "filtered_results": filtered_results
    }
```

### 智能搜索优化
```python
# 自适应搜索策略
async def adaptive_search_optimization(initial_query: str, search_path: str):
    # 初始搜索
    initial_results = await search_tool.execute({
        "operation": "content_search",
        "pattern": initial_query,
        "search_path": search_path,
        "max_results": 100
    })
    
    # 结果分析
    if len(initial_results["files_with_matches"]) == 0:
        # 无结果 - 扩展搜索
        expanded_search = await search_tool.execute({
            "operation": "content_search",
            "pattern": f".*{initial_query}.*",  # 添加通配符
            "search_path": search_path,
            "regex_mode": True,
            "case_sensitive": False
        })
        return expanded_search
    
    elif len(initial_results["files_with_matches"]) > 50:
        # 结果太多 - 精化搜索
        refined_search = await search_tool.execute({
            "operation": "content_search",
            "pattern": initial_query,
            "search_path": search_path,
            "file_types": [".py", ".js", ".ts"],  # 限制文件类型
            "whole_words": True,  # 完整单词匹配
            "max_results": 25
        })
        return refined_search
    
    else:
        # 结果合适 - 返回原始结果
        return initial_results
```

### 代码库特定搜索模式
```python
# 针对代码库的专门搜索
CODE_SEARCH_PATTERNS = {
    "security_issues": {
        "pattern": r"(password|secret|key|token|auth).*=.*['\"][\w\-\.]+['\"]",
        "description": "搜索硬编码的敏感信息",
        "file_types": [".py", ".js", ".ts", ".java", ".cpp"]
    },
    
    "code_smells": {
        "pattern": r"(TODO|FIXME|HACK|XXX|BUG)",
        "description": "搜索代码质量标记",
        "context_lines": 3
    },
    
    "performance_issues": {
        "pattern": r"(for.*for.*for|while.*while|\\.append\\(.*for)",
        "description": "搜索潜在性能问题",
        "regex_mode": True
    },
    
    "database_queries": {
        "pattern": r"(SELECT|INSERT|UPDATE|DELETE).*FROM",
        "description": "搜索SQL查询",
        "case_sensitive": False
    }
}

async def specialized_code_analysis(codebase_path: str):
    analysis_results = {}
    
    for category, pattern_config in CODE_SEARCH_PATTERNS.items():
        results = await search_tool.execute({
            "operation": "content_search",
            "search_path": codebase_path,
            **pattern_config
        })
        
        # 添加严重性评估
        severity_analysis = await reasoning_tool.execute({
            "operation": "reasoning",
            "problem_statement": f"评估{category}搜索结果的严重性和优先级",
            "evidence": [{"matches": results}],
            "reasoning_type": "analytical_reasoning"
        })
        
        analysis_results[category] = {
            "search_results": results,
            "severity_assessment": severity_analysis
        }
    
    return analysis_results
```
"""

    # === AI工具提示词 ===
    
    REASONING_TOOL_PROMPT = """
# ReasoningTool 高级推理指南

## 推理类型选择指南

### Chain-of-Thought（思维链）推理
```python
# 适用场景：需要逐步逻辑推演的问题
chain_of_thought_example = {
    "problem_statement": "为什么我们的数据库查询性能在上个月下降了40%？",
    "reasoning_type": "chain_of_thought",
    "context": "系统部署历史、查询日志、服务器指标",
    "constraints": ["不能影响生产环境", "必须在24小时内找到原因"],
    "complexity_level": "high"
}

# 期望输出：逐步推理过程
# 1. 理解 -> 2. 分解 -> 3. 分析 -> 4. 综合 -> 5. 结论
```

### 逻辑分析推理
```python
# 适用场景：验证逻辑关系和一致性
logical_analysis_example = {
    "operation": "logical_analysis",
    "statements": [
        "所有活跃用户都会收到营销邮件",
        "用户A没有收到营销邮件",
        "用户A的账户状态显示为活跃"
    ],
    "analysis_type": "contradictions",
    "formal_logic": False
}

# 期望输出：逻辑矛盾检测和建议
```

### 问题解决推理
```python
# 适用场景：复杂系统性问题的解决
problem_solving_example = {
    "operation": "problem_solving",
    "problem_description": "客户流失率在第三季度增加了25%，需要识别原因并制定挽回策略",
    "known_information": [
        "产品价格在7月份上涨了15%",
        "竞争对手推出了新的促销活动",  
        "客服响应时间增加了30%"
    ],
    "unknowns": [
        "不同客户群体的具体流失模式",
        "价格敏感度分析",
        "竞争对手策略的具体影响"
    ],
    "solution_criteria": [
        "可在90天内实施",
        "预算限制在50万以内",
        "必须有可衡量的ROI"
    ]
}
```

## 高级推理组合模式

### 多层推理验证
```python
async def multi_layer_reasoning_validation(complex_problem):
    # 层次1：初始分析
    initial_analysis = await reasoning_tool.execute({
        "operation": "reasoning",
        "problem_statement": complex_problem["description"],
        "reasoning_type": "chain_of_thought",
        "complexity_level": "medium"
    })
    
    # 层次2：逻辑验证
    logic_validation = await reasoning_tool.execute({
        "operation": "logical_analysis",
        "statements": initial_analysis["reasoning_steps"],
        "analysis_type": "validity"
    })
    
    # 层次3：解决方案生成
    if logic_validation["overall_assessment"]["logical_soundness"] == "valid":
        solution = await reasoning_tool.execute({
            "operation": "problem_solving",
            "problem_description": complex_problem["description"],
            "known_information": initial_analysis["synthesis"]["key_findings"],
            "solution_criteria": complex_problem.get("success_criteria", [])
        })
        
        return {
            "analysis": initial_analysis,
            "validation": logic_validation,
            "solution": solution,
            "confidence": min(
                initial_analysis["quality_assessment"]["quality_score"],
                logic_validation["overall_assessment"]["quality_score"]
            )
        }
    else:
        # 逻辑验证失败 - 重新分析
        revised_analysis = await reasoning_tool.execute({
            "operation": "reasoning",
            "problem_statement": complex_problem["description"] + f" (修正逻辑错误: {logic_validation['issues']})",
            "reasoning_type": "chain_of_thought",
            "complexity_level": "high"
        })
        
        return {"revised_analysis": revised_analysis, "original_issues": logic_validation}
```

### 领域专家推理
```python
# 不同领域的专门推理策略
DOMAIN_REASONING_STRATEGIES = {
    "software_engineering": {
        "problem_patterns": ["架构决策", "性能优化", "代码质量"],
        "reasoning_type": "problem_solving",
        "evidence_types": ["代码指标", "性能数据", "用户反馈"],
        "solution_criteria": ["可维护性", "性能", "安全性"]
    },
    
    "business_analytics": {
        "problem_patterns": ["市场趋势", "客户行为", "收入优化"],
        "reasoning_type": "causal_reasoning", 
        "evidence_types": ["历史数据", "市场研究", "竞争分析"],
        "solution_criteria": ["ROI", "市场份额", "客户满意度"]
    },
    
    "data_science": {
        "problem_patterns": ["模型选择", "特征工程", "结果解释"],
        "reasoning_type": "analytical_reasoning",
        "evidence_types": ["统计测试", "模型指标", "数据质量"],
        "solution_criteria": ["预测准确性", "模型解释性", "计算效率"]
    }
}

async def domain_specific_reasoning(problem, domain):
    strategy = DOMAIN_REASONING_STRATEGIES.get(domain, DOMAIN_REASONING_STRATEGIES["business_analytics"])
    
    # 应用领域特定策略
    reasoning_result = await reasoning_tool.execute({
        "operation": "reasoning",
        "problem_statement": problem["description"],
        "reasoning_type": strategy["reasoning_type"],
        "domain": domain,
        "evidence": problem.get("evidence", []),
        "goals": strategy["solution_criteria"]
    })
    
    return reasoning_result
```
"""

def get_tool_specific_prompt(tool_name: str) -> str:
    """获取特定工具的详细使用提示词"""
    
    prompt_map = {
        "sql_generator": ToolSpecificPrompts.SQL_GENERATOR_PROMPT,
        "sql_executor": ToolSpecificPrompts.SQL_EXECUTOR_PROMPT, 
        "data_analysis": ToolSpecificPrompts.DATA_ANALYSIS_PROMPT,
        "report_generator": ToolSpecificPrompts.REPORT_GENERATOR_PROMPT,
        "file_operation": ToolSpecificPrompts.FILE_OPERATION_PROMPT,
        "bash_executor": ToolSpecificPrompts.BASH_EXECUTOR_PROMPT,
        "search_tool": ToolSpecificPrompts.SEARCH_TOOL_PROMPT,
        "reasoning_tool": ToolSpecificPrompts.REASONING_TOOL_PROMPT
    }
    
    return prompt_map.get(tool_name, "工具特定提示词未找到。")