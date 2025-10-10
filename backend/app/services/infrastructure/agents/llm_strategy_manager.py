"""
LLM策略管理器
实现基于PTOF阶段和复杂度的智能模型选择策略矩阵
"""

from typing import Dict, Any, Optional, List
import logging
from enum import Enum

from .production_config_provider import production_config_provider


class ComplexityLevel(str, Enum):
    """复杂度级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PTOFStage(str, Enum):
    """PTOF执行阶段"""
    PLAN = "plan"           # 计划生成
    TOOL = "tool"           # 工具执行
    OBSERVE = "observe"     # 观察总结
    FINALIZE = "finalize"   # 最终决策


class ToolType(str, Enum):
    """工具类型"""
    SQL_DRAFT = "sql.draft"
    SQL_VALIDATE = "sql.validate"
    SQL_POLICY = "sql.policy"
    SQL_EXECUTE = "sql.execute"
    SQL_REFINE = "sql.refine"
    DATA_QUALITY = "data.quality"
    CHART_SPEC = "chart.spec"
    WORD_CHART_GENERATOR = "word_chart_generator"
    TIME_WINDOW = "time.window"
    SCHEMA_LIST_COLUMNS = "schema.list_columns"


class LLMStrategyManager:
    """LLM策略管理器"""

    def __init__(self):
        """初始化策略管理器"""
        self.logger = logging.getLogger(self.__class__.__name__)

        # 请求级缓存（避免同一请求中重复查询数据库）
        self._user_config_cache: Dict[str, Dict[str, Any]] = {}
        self._user_policy_cache: Dict[str, Dict[str, Any]] = {}

        # 默认策略矩阵
        self.default_strategy_matrix = {
            # 计划阶段：使用THINK模型确保可靠的JSON输出
            PTOFStage.PLAN: {
                ComplexityLevel.LOW: "think",
                ComplexityLevel.MEDIUM: "think",
                ComplexityLevel.HIGH: "think"
            },

            # 最终决策阶段：使用THINK模型确保可靠的JSON输出
            PTOFStage.FINALIZE: {
                ComplexityLevel.LOW: "think",
                ComplexityLevel.MEDIUM: "think",
                ComplexityLevel.HIGH: "think"
            },

            # 工具执行阶段：根据工具类型和复杂度选择
            PTOFStage.TOOL: {
                ComplexityLevel.LOW: "default",
                ComplexityLevel.MEDIUM: "default",
                ComplexityLevel.HIGH: "think"
            }
        }

        # 工具特定策略
        self.tool_strategy_matrix = {
            # SQL生成工具：复杂查询使用THINK
            ToolType.SQL_DRAFT: {
                ComplexityLevel.LOW: "default",
                ComplexityLevel.MEDIUM: "default",
                ComplexityLevel.HIGH: "think"  # ranking/compare/复杂SQL
            },

            # 图表配置：复杂图表使用THINK
            ToolType.CHART_SPEC: {
                ComplexityLevel.LOW: "default",
                ComplexityLevel.MEDIUM: "default",
                ComplexityLevel.HIGH: "think"  # 复杂图表配置
            },

            # 验证工具：使用DEFAULT即可
            ToolType.SQL_VALIDATE: {
                ComplexityLevel.LOW: "default",
                ComplexityLevel.MEDIUM: "default",
                ComplexityLevel.HIGH: "default"
            },

            # 策略检查：使用DEFAULT即可
            ToolType.SQL_POLICY: {
                ComplexityLevel.LOW: "default",
                ComplexityLevel.MEDIUM: "default",
                ComplexityLevel.HIGH: "default"
            },

            # 数据质量检查：使用DEFAULT即可
            ToolType.DATA_QUALITY: {
                ComplexityLevel.LOW: "default",
                ComplexityLevel.MEDIUM: "default",
                ComplexityLevel.HIGH: "default"
            },

            # SQL细化：复杂场景使用THINK
            ToolType.SQL_REFINE: {
                ComplexityLevel.LOW: "default",
                ComplexityLevel.MEDIUM: "think",  # 细化通常需要更好的推理
                ComplexityLevel.HIGH: "think"
            }
        }

    def clear_cache(self):
        """
        清除请求级缓存

        应在每次新的报告生成请求开始时调用，确保不同请求之间不会复用缓存
        """
        self._user_config_cache.clear()
        self._user_policy_cache.clear()
        self.logger.debug("已清除LLM策略管理器的请求级缓存")

    def _get_cached_user_config(self, user_id: str) -> Dict[str, Any]:
        """
        带缓存的用户配置获取

        Args:
            user_id: 用户ID

        Returns:
            用户配置字典
        """
        if user_id not in self._user_config_cache:
            self.logger.debug(f"缓存未命中，从数据库获取用户配置: user_id={user_id}")
            self._user_config_cache[user_id] = production_config_provider.get_user_config(user_id)
        else:
            self.logger.debug(f"缓存命中，使用已缓存的用户配置: user_id={user_id}")

        return self._user_config_cache[user_id]

    def _get_cached_user_policy(self, user_id: str, stage: str, complexity: str) -> Dict[str, Any]:
        """
        带缓存的用户LLM策略获取

        Args:
            user_id: 用户ID
            stage: 阶段
            complexity: 复杂度

        Returns:
            用户LLM策略字典
        """
        cache_key = f"{user_id}:{stage}:{complexity}"

        if cache_key not in self._user_policy_cache:
            self.logger.debug(f"缓存未命中，从数据库获取LLM策略: {cache_key}")
            self._user_policy_cache[cache_key] = production_config_provider.get_llm_policy_config(
                user_id, stage, complexity
            )
        else:
            self.logger.debug(f"缓存命中，使用已缓存的LLM策略: {cache_key}")

        return self._user_policy_cache[cache_key]

    def get_recommended_model_type(
        self,
        stage: str,
        complexity: str = "medium",
        tool_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        获取推荐的模型类型

        Args:
            stage: PTOF阶段 (plan/tool/finalize)
            complexity: 复杂度级别 (low/medium/high)
            tool_name: 工具名称（如果是tool阶段）
            context: 上下文信息（用于动态调整复杂度）
            user_id: 用户ID（用于获取用户偏好）

        Returns:
            推荐的模型类型 ("default" 或 "think")
        """
        try:
            # 标准化输入
            stage_enum = self._parse_stage(stage)
            complexity_enum = self._parse_complexity(complexity)

            # 动态调整复杂度
            adjusted_complexity = self._adjust_complexity_by_context(
                complexity_enum, context, tool_name
            )

            # 获取策略推荐
            recommended_type = self._get_strategy_recommendation(
                stage_enum, adjusted_complexity, tool_name
            )

            # 应用用户偏好覆盖
            if user_id:
                recommended_type = self._apply_user_preference_override(
                    user_id, stage, tool_name, recommended_type
                )

            self.logger.info(
                f"模型类型推荐: stage={stage}, tool={tool_name}, "
                f"complexity={complexity}→{adjusted_complexity.value}, "
                f"recommended={recommended_type}"
            )

            return recommended_type

        except Exception as e:
            self.logger.error(f"模型类型推荐失败: {e}")
            # 默认返回think，确保可靠性
            return "think"

    def _parse_stage(self, stage: str) -> PTOFStage:
        """解析PTOF阶段"""
        try:
            return PTOFStage(stage.lower())
        except ValueError:
            return PTOFStage.TOOL  # 默认为工具阶段

    def _parse_complexity(self, complexity: str) -> ComplexityLevel:
        """解析复杂度级别"""
        try:
            return ComplexityLevel(complexity.lower())
        except ValueError:
            return ComplexityLevel.MEDIUM  # 默认中等复杂度

    def _adjust_complexity_by_context(
        self,
        base_complexity: ComplexityLevel,
        context: Optional[Dict[str, Any]],
        tool_name: Optional[str]
    ) -> ComplexityLevel:
        """
        根据上下文动态调整复杂度

        Args:
            base_complexity: 基础复杂度
            context: 上下文信息
            tool_name: 工具名称

        Returns:
            调整后的复杂度
        """
        if not context:
            return base_complexity

        # 提取关键指标
        semantic_type = context.get("semantic_type", "")
        top_n = context.get("top_n")
        tables_count = len(context.get("tables", []))
        columns_count = sum(len(cols) for cols in context.get("columns", {}).values())
        output_kind = context.get("output_kind", "")

        complexity_score = base_complexity.value

        # 语义类型复杂度提升
        if semantic_type in ["ranking", "compare", "chart"]:
            complexity_score = "high"

        # Top N查询复杂度提升
        if top_n and top_n > 10:
            complexity_score = "high"

        # 多表联查复杂度提升
        if tables_count > 3:
            complexity_score = "high"
        elif tables_count > 1:
            complexity_score = max(complexity_score, "medium")

        # 大量字段复杂度提升
        if columns_count > 50:
            complexity_score = "high"
        elif columns_count > 20:
            complexity_score = max(complexity_score, "medium")

        # 图表输出复杂度提升
        if output_kind == "chart":
            complexity_score = max(complexity_score, "high")

        # 特定工具的复杂度调整
        if tool_name == "sql.draft":
            # SQL生成工具的特殊处理
            if semantic_type in ["ranking", "compare"] or output_kind == "chart":
                complexity_score = "high"

        return ComplexityLevel(complexity_score)

    def _get_strategy_recommendation(
        self,
        stage: PTOFStage,
        complexity: ComplexityLevel,
        tool_name: Optional[str]
    ) -> str:
        """
        根据策略矩阵获取推荐

        Args:
            stage: PTOF阶段
            complexity: 复杂度级别
            tool_name: 工具名称

        Returns:
            推荐的模型类型
        """
        # 如果是工具阶段且有具体工具名，优先使用工具特定策略
        if stage == PTOFStage.TOOL and tool_name:
            try:
                tool_enum = ToolType(tool_name)
                if tool_enum in self.tool_strategy_matrix:
                    return self.tool_strategy_matrix[tool_enum][complexity]
            except (ValueError, KeyError):
                pass

        # 使用通用策略矩阵
        return self.default_strategy_matrix.get(stage, {}).get(
            complexity, "think"  # 默认使用think确保可靠性
        )

    def _apply_user_preference_override(
        self,
        user_id: str,
        stage: str,
        tool_name: Optional[str],
        default_recommendation: str
    ) -> str:
        """
        应用用户偏好覆盖

        Args:
            user_id: 用户ID
            stage: 阶段
            tool_name: 工具名称
            default_recommendation: 默认推荐

        Returns:
            最终推荐（考虑用户偏好）
        """
        try:
            # 使用缓存获取用户配置，避免重复DB查询
            user_config = self._get_cached_user_config(user_id)
            model_preferences = user_config.get("model_preferences", {})

            # 检查工具特定偏好
            if tool_name and tool_name in model_preferences:
                preference = model_preferences[tool_name]
                if preference in ["default", "think"]:
                    return preference

            # 检查阶段特定偏好
            if stage in model_preferences:
                preference = model_preferences[stage]
                if preference in ["default", "think"]:
                    return preference

            # 检查全局偏好
            if "global_model_type" in model_preferences:
                preference = model_preferences["global_model_type"]
                if preference in ["default", "think"]:
                    return preference

        except Exception as e:
            self.logger.warning(f"应用用户偏好失败 (user_id: {user_id}): {e}")

        return default_recommendation

    def build_llm_policy(
        self,
        user_id: str,
        stage: str,
        complexity: str = "medium",
        tool_name: Optional[str] = None,
        output_kind: str = "sql",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        构建完整的LLM策略配置

        Args:
            user_id: 用户ID
            stage: PTOF阶段
            complexity: 基础复杂度
            tool_name: 工具名称
            output_kind: 输出类型
            context: 上下文信息

        Returns:
            LLM策略配置字典
        """
        # 获取推荐模型类型
        recommended_model_type = self.get_recommended_model_type(
            stage=stage,
            complexity=complexity,
            tool_name=tool_name,
            context=context,
            user_id=user_id
        )

        # 获取用户配置（使用缓存）
        try:
            user_llm_policy = self._get_cached_user_policy(user_id, stage, complexity)
        except Exception as e:
            self.logger.warning(f"获取用户LLM策略失败: {e}")
            user_llm_policy = {}

        # 构建完整策略
        llm_policy = {
            "user_id": user_id,
            "stage": stage,
            "step": tool_name,
            "complexity": complexity,
            "output_kind": output_kind,
            "preferred_model_type": recommended_model_type,
            **user_llm_policy
        }

        return llm_policy


# 创建全局实例
llm_strategy_manager = LLMStrategyManager()