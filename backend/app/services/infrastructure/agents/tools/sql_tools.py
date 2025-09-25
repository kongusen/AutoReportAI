"""
SQL相关工具集合

提供SQL生成、验证、执行、策略检查等功能
适配backup系统的数据源和LLM服务
"""

import logging
from typing import Dict, Any
from ..auth_context import auth_manager
from ..config_context import config_manager
from ..llm_strategy_manager import llm_strategy_manager
from ..data_source_security_service import data_source_security_service

from .base import Tool


class SQLDraftTool(Tool):
    """SQL生成工具"""

    def __init__(self, container):
        super().__init__()
        self.name = "sql.draft"
        self.description = "根据描述和schema生成SQL查询"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成SQL查询"""
        try:
            placeholder = input_data.get("placeholder", {})
            # 支持从上下文直接读取schema
            schema = input_data.get("schema") or {
                "tables": input_data.get("tables", []),
                "columns": input_data.get("columns", {}),
            }
            description = placeholder.get("description", input_data.get("user_prompt", ""))

            # 语义与可选参数
            semantic_type = (input_data.get("semantic_type") or "").lower() or None
            top_n = input_data.get("top_n")
            window = input_data.get("window") or {}

            # 构建SQL生成提示词（类型感知）
            prompt = self._build_sql_prompt(description, schema, semantic_type=semantic_type, top_n=top_n, window=window)

            # 从input_data获取用户ID，优先使用认证上下文
            user_id = input_data.get("user_id") or auth_manager.get_current_user_id() or "system"

            # 调用LLM服务
            llm_service = getattr(self.container, 'llm_service', None) or getattr(self.container, 'llm', None)
            if not llm_service:
                return {"success": False, "error": "LLM service not available"}

            # 使用策略管理器构建智能LLM策略
            base_complexity = "high" if (semantic_type or '').lower() in ("ranking", "compare", "chart") else "medium"

            llm_policy = llm_strategy_manager.build_llm_policy(
                user_id=user_id,
                stage="tool",
                complexity=base_complexity,
                tool_name="sql.draft",
                output_kind=input_data.get('output_kind', 'sql'),
                context={
                    "semantic_type": semantic_type,
                    "top_n": top_n,
                    "tables": schema.get("tables", []),
                    "columns": schema.get("columns", {}),
                    "window": window,
                    "output_kind": input_data.get('output_kind', 'sql')
                }
            )
            result = await self._call_llm(llm_service, prompt, llm_policy=llm_policy, user_id=user_id)

            # 清理SQL格式（移除markdown代码块）
            cleaned_sql = self._clean_sql_response(result)

            return {
                "success": True,
                "sql": cleaned_sql,
                "description": description
            }

        except Exception as e:
            self._logger.error(f"SQL生成失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _build_sql_prompt(self, description: str, schema: Dict[str, Any], *, semantic_type: str = None, top_n: int = None, window: Dict[str, Any] = None) -> str:
        """构建SQL生成提示词"""
        tables = schema.get("tables", [])
        columns = schema.get("columns", {})

        schema_info = []
        for table in tables:
            table_columns = columns.get(table, [])
            if table_columns:
                schema_info.append(f"表 {table}: {', '.join(table_columns)}")

        schema_str = "\n".join(schema_info) if schema_info else "无具体表结构信息"

        guidance = []
        # 类型指导
        if semantic_type == "ranking":
            if top_n:
                guidance.append(f"按度量降序排序并取前{top_n}（可用 ORDER BY + LIMIT {top_n}，或窗口函数 RANK()）")
            else:
                guidance.append("按度量降序排序并取前N（可用 ORDER BY + LIMIT N，或窗口函数 RANK()）")
            guidance.append("选择清晰的分组维度与度量字段（SUM/COUNT/AVG等）")
        elif semantic_type == "compare":
            guidance.append("输出基准值、对比值、差值(diff)与百分比变化(pct_change)列")
            guidance.append("两个时间范围/组的过滤条件与口径保持一致")
        elif semantic_type == "period":
            guidance.append("使用合适的时间粒度（日/周/月/季度）分组，字段命名清晰")

        # 时间指令（可选）
        time_hint = ""
        try:
            tc = (window or {}).get("task_schedule", {})
            cron = tc.get("cron_expression")
            tz = tc.get("timezone")
            if cron or tz:
                time_hint = f"调度: {cron or ''} {f'({tz})' if tz else ''}".strip()
        except Exception:
            pass

        guidance_lines = "\n".join([f"- {g}" for g in guidance]) if guidance else ""

        return f"""
根据以下需求生成SQL查询语句:

需求描述: {description}

可用数据结构:
{schema_str}

{('时间上下文: ' + time_hint) if time_hint else ''}

类型指导:
{guidance_lines}

要求:
1. 生成标准的SELECT语句（命名清晰，必要时添加别名）
2. 使用适当的WHERE/LIMIT（大表优先限制时间或返回行数）
3. 考虑数据类型和字段关系
4. 只返回SQL语句，不要包含解释文字
"""

    async def _call_llm(self, llm_service, prompt: str, llm_policy: Dict[str, Any] = None, user_id: str = "system") -> str:
        """调用LLM生成SQL"""
        try:
            if hasattr(llm_service, 'ask'):
                result = await llm_service.ask(user_id=user_id, prompt=prompt, llm_policy=llm_policy)
                return result.get("response", "") if isinstance(result, dict) else str(result)
            elif hasattr(llm_service, 'generate_response'):
                result = await llm_service.generate_response(prompt=prompt, user_id=user_id)
                return result.get("response", "") if isinstance(result, dict) else str(result)
            elif callable(llm_service):
                return await llm_service(prompt)
            else:
                raise ValueError("Unsupported LLM service interface")
        except Exception as e:
            self._logger.error(f"LLM调用失败: {str(e)}")
            return ""

    def _clean_sql_response(self, response: str) -> str:
        """清理LLM响应中的SQL代码，移除markdown格式"""
        if not response:
            return ""

        # 移除markdown代码块标记
        lines = response.strip().split('\n')
        cleaned_lines = []

        in_code_block = False
        for line in lines:
            line_stripped = line.strip()
            # 跳过代码块开始标记
            if line_stripped.startswith('```'):
                in_code_block = not in_code_block
                continue
            # 如果在代码块内或者看起来像SQL，保留这行
            if in_code_block or line_stripped.upper().startswith(('SELECT', 'WITH', 'INSERT', 'UPDATE', 'DELETE')):
                cleaned_lines.append(line)

        result = '\n'.join(cleaned_lines).strip()

        # 如果清理后没有内容，返回原始响应
        if not result:
            return response.strip()

        return result


class SQLValidateTool(Tool):
    """SQL验证工具"""

    def __init__(self, container):
        super().__init__()
        self.name = "sql.validate"
        self.description = "验证SQL语句的正确性"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

        # Compare强校验配置（支持环境变量配置）
        import os
        self.compare_strict_validation = os.getenv('AGENT_COMPARE_STRICT_VALIDATION', 'true').lower() in ('true', '1', 'yes')
        self.compare_enforce_column_names = os.getenv('AGENT_COMPARE_ENFORCE_COLUMN_NAMES', 'false').lower() in ('true', '1', 'yes')
        self.required_compare_columns = ["baseline", "compare", "diff", "pct_change"]  # 必需列名
        self.required_compare_concepts = ["baseline", "compare", "difference", "percentage"]  # 必需概念

        # SQL安全策略配置
        self.enable_table_scan_protection = os.getenv('AGENT_ENABLE_TABLE_SCAN_PROTECTION', 'true').lower() in ('true', '1', 'yes')
        self.max_table_scan_size = int(os.getenv('AGENT_MAX_TABLE_SCAN_SIZE', '10000'))  # 允许无WHERE条件的最大表行数
        self.scan_whitelist_tables = set(os.getenv('AGENT_SCAN_WHITELIST_TABLES', 'metadata,config,lookup').split(','))
        self.scan_exempt_patterns = ['LIMIT', 'TOP', 'ROWNUM', 'SAMPLE']  # 豁免模式

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证SQL语句"""
        try:
            sql = input_data.get("current_sql") or input_data.get("sql", "")
            if not sql:
                return {"success": False, "error": "SQL语句为空"}

            # 基础语法验证
            validation_result = self._validate_sql_syntax(sql)

            # 语义类型特定验证
            semantic_type = (input_data.get("semantic_type") or "").lower() or None
            top_n = input_data.get("top_n")
            issues_extra = []
            warnings_extra = []

            # Compare强校验
            if semantic_type == "compare":
                compare_validation = self._validate_compare_sql(sql, input_data)
                if not compare_validation["valid"]:
                    issues_extra.extend(compare_validation["issues"])
                warnings_extra.extend(compare_validation.get("warnings", []))

            # Ranking验证
            elif semantic_type == "ranking" and top_n:
                ranking_validation = self._validate_ranking_sql(sql, top_n)
                if not ranking_validation["valid"]:
                    issues_extra.extend(ranking_validation["issues"])
                warnings_extra.extend(ranking_validation.get("warnings", []))

            # Chart验证
            elif semantic_type == "chart":
                chart_validation = self._validate_chart_sql(sql, input_data)
                warnings_extra.extend(chart_validation.get("warnings", []))

            # SQL安全策略验证（表扫描保护）
            if self.enable_table_scan_protection:
                security_validation = self._validate_table_scan_security(sql, input_data)
                if not security_validation["valid"]:
                    issues_extra.extend(security_validation["issues"])
                warnings_extra.extend(security_validation.get("warnings", []))

            # 合并验证结果
            if issues_extra:
                validation_result["issues"] = (validation_result.get("issues") or []) + issues_extra
                validation_result["valid"] = False

            if warnings_extra:
                validation_result["warnings"] = (validation_result.get("warnings", [])) + warnings_extra

            return {
                "success": validation_result["valid"],
                "sql": sql,
                "issues": validation_result.get("issues", []),
                "warnings": validation_result.get("warnings", []),
                "error": validation_result.get("error") if not validation_result["valid"] else None
            }

        except Exception as e:
            self._logger.error(f"SQL验证失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _validate_sql_syntax(self, sql: str) -> Dict[str, Any]:
        """基础SQL语法验证"""
        sql_upper = sql.upper().strip()
        issues = []

        # 检查基本SQL结构
        if not sql_upper.startswith("SELECT"):
            issues.append("SQL必须以SELECT开头")

        if "FROM" not in sql_upper:
            issues.append("SQL必须包含FROM子句")

        # 检查危险操作
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER"]
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                issues.append(f"SQL包含危险关键词: {keyword}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "error": "; ".join(issues) if issues else None
        }

    def _validate_compare_sql(self, sql: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compare查询强校验"""
        issues = []
        warnings = []
        valid = True

        if not self.compare_strict_validation:
            self._logger.info("Compare强校验已禁用，跳过验证")
            return {"valid": True, "issues": [], "warnings": []}

        sql_upper = sql.upper()
        self._logger.info(f"🔍 [CompareValidation] 开始Compare强校验，enforce_column_names={self.compare_enforce_column_names}")

        # 1. 强制检查必需列名（如果启用）
        if self.compare_enforce_column_names:
            missing_columns = []
            for required_col in self.required_compare_columns:
                if required_col.upper() not in sql_upper:
                    missing_columns.append(required_col)

            if missing_columns:
                issues.append(f"Compare查询必须包含以下列名: {', '.join(missing_columns)}")
                valid = False
                self._logger.warning(f"⚠️ [CompareValidation] 缺少必需列名: {missing_columns}")

        # 2. 必须包含基准期和对比期的概念（更严格）
        baseline_keywords = ["BASELINE", "BASE", "PREVIOUS", "LAST", "PRIOR", "BEFORE", "OLD"]
        compare_keywords = ["COMPARE", "CURRENT", "NEW", "NOW", "AFTER", "RECENT"]

        has_baseline = any(keyword in sql_upper for keyword in baseline_keywords)
        has_compare = any(keyword in sql_upper for keyword in compare_keywords)

        if not has_baseline:
            issues.append(f"Compare查询必须包含基准期概念 (关键词: {', '.join(baseline_keywords[:3])}...)")
            valid = False

        if not has_compare:
            issues.append(f"Compare查询必须包含对比期概念 (关键词: {', '.join(compare_keywords[:3])}...)")
            valid = False

        # 3. 强制要求包含差值计算（更精确检查）
        diff_patterns = ["DIFF", "DIFFERENCE", "CHANGE", "DELTA", "MINUS", "SUBTRACT", "VARIANCE"]
        has_diff = any(pattern in sql_upper for pattern in diff_patterns)
        has_arithmetic_diff = " - " in sql or "(-" in sql  # 算术差值

        if not (has_diff or has_arithmetic_diff):
            issues.append("Compare查询必须包含差值计算 (使用 DIFF/CHANGE 列名或算术运算 '-')")
            valid = False

        # 4. 强制要求包含百分比变化（更精确检查）
        pct_patterns = ["PCT", "PERCENT", "PERCENTAGE", "RATE", "RATIO", "GROWTH"]
        has_pct = any(pattern in sql_upper for pattern in pct_patterns)
        has_pct_formula = "*100" in sql.replace(" ", "") or "/100" in sql.replace(" ", "")  # 百分比公式

        if not (has_pct or has_pct_formula):
            issues.append("Compare查询必须包含百分比变化 (使用 PCT_CHANGE/PERCENTAGE 列名或百分比计算)")
            valid = False

        # 5. 检查是否有时间维度（升级为强制要求）
        time_keywords = ["DATE", "TIME", "YEAR", "MONTH", "DAY", "PERIOD", "WEEK", "QUARTER"]
        has_time_dimension = any(keyword in sql_upper for keyword in time_keywords)

        if not has_time_dimension:
            issues.append("Compare查询必须包含时间维度以明确对比期间")
            valid = False

        # 6. 检查是否有适当的分组和排序
        has_group_by = "GROUP BY" in sql_upper
        has_order_by = "ORDER BY" in sql_upper

        if not has_group_by:
            warnings.append("Compare查询建议使用 GROUP BY 进行适当分组")

        if not has_order_by:
            warnings.append("Compare查询建议使用 ORDER BY 按变化幅度排序")

        # 7. 检查潜在的数据质量问题
        if "WHERE" not in sql_upper:
            warnings.append("Compare查询建议添加 WHERE 条件限制数据范围，避免全表扫描")

        result = {
            "valid": valid,
            "issues": issues,
            "warnings": warnings
        }

        if valid:
            self._logger.info("✅ [CompareValidation] Compare查询通过强校验")
        else:
            self._logger.warning(f"🚨 [CompareValidation] Compare查询未通过强校验，发现 {len(issues)} 个问题")

        return result

    def _validate_ranking_sql(self, sql: str, top_n: int) -> Dict[str, Any]:
        """排名查询验证"""
        issues = []
        warnings = []
        valid = True

        sql_upper = sql.upper()

        # 检查是否有排序和限制
        has_order_by = "ORDER BY" in sql_upper
        has_limit = "LIMIT" in sql_upper or f"LIMIT {top_n}" in sql_upper
        has_rank_function = any(func in sql_upper for func in [
            "RANK()", "DENSE_RANK()", "ROW_NUMBER()", "NTILE("
        ])

        if not has_order_by and not has_rank_function:
            issues.append("排名查询必须包含 ORDER BY 子句或窗口排名函数")
            valid = False

        if not has_limit and not has_rank_function:
            warnings.append(f"排名查询建议使用 LIMIT {top_n} 或窗口函数限制结果数量")

        return {
            "valid": valid,
            "issues": issues,
            "warnings": warnings
        }

    def _validate_chart_sql(self, sql: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """图表查询验证"""
        warnings = []

        chart_type = input_data.get("chart_type", "").lower()
        sql_upper = sql.upper()

        # 根据图表类型给出建议
        if chart_type == "pie":
            if "GROUP BY" not in sql_upper:
                warnings.append("饼图建议使用 GROUP BY 对类别进行分组")
        elif chart_type == "line":
            has_time = any(keyword in sql_upper for keyword in [
                "DATE", "TIME", "YEAR", "MONTH", "DAY"
            ])
            if not has_time:
                warnings.append("折线图建议包含时间维度数据")
        elif chart_type == "bar":
            if "ORDER BY" not in sql_upper:
                warnings.append("柱状图建议使用 ORDER BY 对结果排序")

        return {
            "valid": True,
            "warnings": warnings
        }

    def _validate_table_scan_security(self, sql: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """SQL表扫描安全验证 - 防止无WHERE条件的大表扫描"""
        issues = []
        warnings = []
        valid = True

        if not self.enable_table_scan_protection:
            self._logger.info("表扫描保护已禁用，跳过验证")
            return {"valid": True, "issues": [], "warnings": []}

        sql_upper = sql.upper()
        self._logger.info(f"🔐 [TableScanSecurity] 开始表扫描安全验证")

        # 检查是否有WHERE条件
        has_where = "WHERE" in sql_upper
        has_limit = any(pattern in sql_upper for pattern in self.scan_exempt_patterns)

        if not has_where and not has_limit:
            # 提取表名进行白名单检查
            tables = self._extract_table_names(sql)
            blocked_tables = []
            whitelisted_tables = []

            for table in tables:
                table_clean = table.lower().strip()
                if table_clean in self.scan_whitelist_tables:
                    whitelisted_tables.append(table)
                else:
                    blocked_tables.append(table)

            if blocked_tables:
                self._logger.warning(f"🚨 [TableScanSecurity] 检测到大表扫描风险: {blocked_tables}")

                # 尝试获取表大小信息（如果可用）
                table_size_info = self._get_table_size_info(blocked_tables, input_data)
                large_tables = []

                for table, size_info in table_size_info.items():
                    estimated_size = size_info.get("estimated_rows", 0)
                    if estimated_size > self.max_table_scan_size:
                        large_tables.append(f"{table}(~{estimated_size}行)")

                if large_tables:
                    issues.append(
                        f"禁止无WHERE条件扫描大表: {', '.join(large_tables)}。"
                        f"请添加WHERE条件限制数据范围，或使用LIMIT限制返回行数"
                    )
                    valid = False
                else:
                    warnings.append(
                        f"检测到无WHERE条件的表扫描: {', '.join(blocked_tables)}。"
                        f"建议添加WHERE条件或LIMIT子句以提升性能"
                    )

            if whitelisted_tables:
                self._logger.info(f"✅ [TableScanSecurity] 白名单表允许扫描: {whitelisted_tables}")

        # 检查JOIN操作的安全性
        if "JOIN" in sql_upper and not has_where:
            warnings.append("多表JOIN操作建议使用WHERE条件限制结果集大小")

        # 检查聚合操作
        has_aggregation = any(func in sql_upper for func in ["COUNT", "SUM", "AVG", "MAX", "MIN", "GROUP BY"])
        if has_aggregation and not has_where and not has_limit:
            warnings.append("聚合查询建议添加WHERE条件或时间范围限制")

        result = {
            "valid": valid,
            "issues": issues,
            "warnings": warnings
        }

        if valid:
            self._logger.info("✅ [TableScanSecurity] SQL表扫描安全验证通过")
        else:
            self._logger.warning(f"🚨 [TableScanSecurity] SQL存在安全风险，发现 {len(issues)} 个问题")

        return result

    def _extract_table_names(self, sql: str) -> list:
        """从SQL中提取表名"""
        import re

        # 简化的表名提取（可以根据需要改进）
        sql_clean = re.sub(r'--.*', '', sql)  # 移除注释
        sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)  # 移除多行注释

        # 查找FROM和JOIN后的表名
        tables = set()

        # FROM子句
        from_pattern = r'\bFROM\s+(\w+)'
        for match in re.finditer(from_pattern, sql_clean, re.IGNORECASE):
            tables.add(match.group(1))

        # JOIN子句
        join_pattern = r'\bJOIN\s+(\w+)'
        for match in re.finditer(join_pattern, sql_clean, re.IGNORECASE):
            tables.add(match.group(1))

        return list(tables)

    def _get_table_size_info(self, tables: list, input_data: Dict[str, Any]) -> Dict[str, Dict]:
        """获取表大小信息（如果可用）"""
        # 简化实现，实际可以从数据源或元数据服务获取
        size_info = {}

        # 默认表大小估算（实际应该从数据库统计信息获取）
        default_estimates = {
            "users": {"estimated_rows": 50000},
            "orders": {"estimated_rows": 100000},
            "transactions": {"estimated_rows": 500000},
            "logs": {"estimated_rows": 1000000},
            "events": {"estimated_rows": 2000000},
        }

        for table in tables:
            table_lower = table.lower()
            if table_lower in default_estimates:
                size_info[table] = default_estimates[table_lower]
            else:
                # 保守估计
                size_info[table] = {"estimated_rows": self.max_table_scan_size + 1}

        return size_info


class SQLExecuteTool(Tool):
    """SQL执行工具"""

    def __init__(self, container):
        super().__init__()
        self.name = "sql.execute"
        self.description = "执行SQL查询获取数据"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行SQL查询"""
        try:
            sql = input_data.get("current_sql") or input_data.get("sql", "")
            if not sql:
                return {"success": False, "error": "SQL语句为空"}

            # 获取用户ID和数据源ID
            user_id = input_data.get("user_id") or auth_manager.get_current_user_id() or "system"
            data_source_config = input_data.get("data_source", {})
            data_source_id = data_source_config.get("id")

            # 数据源权限验证
            if user_id != "system" and data_source_id:
                self._logger.info(f"验证用户 {user_id} 对数据源 {data_source_id} 的访问权限")

                access_validation = data_source_security_service.validate_data_source_access(
                    user_id=user_id,
                    data_source_id=data_source_id
                )

                if not access_validation.get("allowed"):
                    self._logger.warning(f"数据源访问被拒绝: {access_validation}")
                    return {
                        "success": False,
                        "error": f"数据源访问权限验证失败: {access_validation.get('reason', '未知错误')}",
                        "error_code": access_validation.get("error_code", "ACCESS_DENIED")
                    }

                self._logger.info("数据源权限验证通过")

            # 获取数据源服务
            data_source_service = getattr(self.container, 'data_source_service', None) or getattr(self.container, 'data_source', None)
            if not data_source_service:
                return {"success": False, "error": "Data source service not available"}

            # 执行SQL (这里需要根据backup系统的实际接口调整)
            result = await self._execute_sql(data_source_service, sql, input_data)

            return {
                "success": True,
                "sql": sql,
                "rows": result.get("rows", []),
                "columns": result.get("columns", []),
                "row_count": len(result.get("rows", []))
            }

        except Exception as e:
            self._logger.error(f"SQL执行失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _execute_sql(self, data_source_service, sql: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行SQL查询"""
        try:
            # 构建数据源配置
            data_source_config = context.get("data_source", {}) or {}

            # 若 data_source 中仅有 id/type/database 等简要信息，尝试通过 user_data_source_service 获取完整连接配置
            container = getattr(self, 'container', None)
            user_id = context.get("user_id")
            ds_id = data_source_config.get("id")
            resolved_cfg = None

            if container and hasattr(container, 'user_data_source_service') and user_id and ds_id:
                try:
                    uds = await container.user_data_source_service.get_user_data_source(user_id=user_id, data_source_id=ds_id)
                    if uds and getattr(uds, 'connection_config', None):
                        resolved_cfg = uds.connection_config
                except Exception:
                    resolved_cfg = None

            final_cfg = resolved_cfg or data_source_config

            # 兼容类型映射（mysql/postgres → sql）
            t = (final_cfg.get("source_type") or final_cfg.get("type") or "").lower()
            if t in ("mysql", "postgres", "postgresql", "mariadb"):
                final_cfg["source_type"] = "sql"

            # 尝试不同的执行方法
            if hasattr(data_source_service, 'execute_query'):
                result = await data_source_service.execute_query(sql, final_cfg)
            elif hasattr(data_source_service, 'run_query'):
                result = await data_source_service.run_query(final_cfg, sql)
            elif callable(data_source_service):
                result = await data_source_service(sql, final_cfg)
            else:
                raise ValueError("Unsupported data source service interface")

            return {
                "rows": result.get("rows", result.get("data", [])),
                "columns": result.get("columns", result.get("column_names", []))
            }

        except Exception as e:
            self._logger.error(f"SQL执行异常: {str(e)}")
            return {"rows": [], "columns": []}


class SQLRefineTool(Tool):
    """SQL优化工具"""

    def __init__(self, container):
        super().__init__()
        self.name = "sql.refine"
        self.description = "基于问题反馈优化SQL语句"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """优化SQL语句"""
        try:
            sql = input_data.get("current_sql") or input_data.get("sql", "")
            issues = input_data.get("issues", [])

            if not sql:
                return {"success": False, "error": "SQL语句为空"}

            # 构建优化提示词
            prompt = self._build_refine_prompt(sql, issues)

            # 调用LLM优化
            llm_service = getattr(self.container, 'llm_service', None) or getattr(self.container, 'llm', None)
            if not llm_service:
                return {"success": False, "error": "LLM service not available"}

            # 从input_data获取用户ID，优先使用认证上下文
            user_id = input_data.get("user_id") or auth_manager.get_current_user_id() or "system"
            refined_sql = await self._call_llm(llm_service, prompt, user_id=user_id)

            return {
                "success": True,
                "sql": refined_sql,
                "original_sql": sql,
                "issues_addressed": issues
            }

        except Exception as e:
            self._logger.error(f"SQL优化失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _build_refine_prompt(self, sql: str, issues: list) -> str:
        """构建SQL优化提示词"""
        issues_str = "\n".join([f"- {issue}" for issue in issues])

        return f"""
请优化以下SQL语句，解决发现的问题:

原始SQL:
{sql}

发现的问题:
{issues_str}

要求:
1. 保持原有查询逻辑
2. 修复所有问题
3. 优化性能
4. 只返回优化后的SQL语句
"""

    async def _call_llm(self, llm_service, prompt: str, user_id: str = "system") -> str:
        """调用LLM优化SQL"""
        try:
            if hasattr(llm_service, 'ask'):
                result = await llm_service.ask(user_id=user_id, prompt=prompt)
                return result.get("response", "") if isinstance(result, dict) else str(result)
            elif hasattr(llm_service, 'generate_response'):
                result = await llm_service.generate_response(prompt=prompt, user_id=user_id)
                return result.get("response", "") if isinstance(result, dict) else str(result)
            elif callable(llm_service):
                return await llm_service(prompt)
            else:
                raise ValueError("Unsupported LLM service interface")
        except Exception as e:
            self._logger.error(f"LLM调用失败: {str(e)}")
            return ""


class SQLPolicyTool(Tool):
    """SQL策略检查工具"""

    def __init__(self, container):
        super().__init__()
        self.name = "sql.policy"
        self.description = "执行SQL策略检查并添加LIMIT"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行SQL策略检查"""
        try:
            sql = input_data.get("current_sql") or input_data.get("sql", "")
            if not sql:
                return {"success": False, "error": "SQL语句为空"}

            # 获取用户信息
            user_id = input_data.get("user_id") or auth_manager.get_current_user_id() or "system"
            data_source_config = input_data.get("data_source", {})
            data_source_id = data_source_config.get("id")

            # 确定用户是否为超级用户
            is_superuser = False
            if user_id != "system":
                auth_context = auth_manager.get_current_auth_context()
                is_superuser = auth_context.is_superuser if auth_context else False

            # 使用DataSourceSecurityService进行SQL安全策略检查
            security_result = data_source_security_service.apply_sql_security_policy(
                sql=sql,
                user_id=user_id,
                data_source_id=data_source_id,
                is_superuser=is_superuser
            )

            if not security_result.get("allowed"):
                self._logger.warning(f"SQL策略检查失败: {security_result}")
                return {
                    "success": False,
                    "error": f"SQL安全策略检查失败: {'; '.join(security_result.get('issues', []))}",
                    "issues": security_result.get("issues", [])
                }

            # 使用经过安全策略处理的SQL
            processed_sql = security_result.get("modified_sql", sql)

            return {
                "success": True,
                "sql": processed_sql,
                "original_sql": sql,
                "policies_applied": security_result.get("modifications", []),
                "warnings": security_result.get("warnings", []),
                "issues": security_result.get("issues", [])
            }

        except Exception as e:
            self._logger.error(f"SQL策略检查失败: {str(e)}")
            return {"success": False, "error": str(e)}

