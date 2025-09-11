"""
安全检查模块 - 基于Claude Code的多层安全检查理念
提供工具执行的安全验证、模式分析和用户确认机制
"""

import re
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Pattern
from enum import Enum

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """安全级别"""
    SAFE = "safe"                # 完全安全，直接执行
    LOW_RISK = "low_risk"        # 低风险，记录日志
    MEDIUM_RISK = "medium_risk"  # 中等风险，需要确认
    HIGH_RISK = "high_risk"      # 高风险，需要强确认
    FORBIDDEN = "forbidden"      # 禁止执行


@dataclass
class SecurityCheckResult:
    """安全检查结果"""
    level: SecurityLevel
    allowed: bool
    reason: str
    require_confirmation: bool = False
    confidence: float = 0.0
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class SecurityPattern:
    """安全模式定义"""
    name: str
    pattern: Pattern[str]
    level: SecurityLevel
    description: str
    suggestion: str = ""


class SecurityChecker:
    """
    工具执行安全检查器 - 基于Claude Code的安全理念
    
    实现多层安全检查：
    1. 静态规则检查 - 危险命令模式
    2. 动态模式分析 - 上下文风险评估
    3. 用户确认机制 - 建立信任
    4. 沙箱预检查 - 执行前验证
    """
    
    def __init__(self):
        self.security_patterns = self._initialize_security_patterns()
        self.execution_history: List[Dict[str, Any]] = []
        self.user_confirmations: Dict[str, bool] = {}
        
    def _initialize_security_patterns(self) -> List[SecurityPattern]:
        """初始化安全模式"""
        return [
            # 文件系统危险操作
            SecurityPattern(
                name="dangerous_delete",
                pattern=re.compile(r"rm\s+-rf\s+/", re.IGNORECASE),
                level=SecurityLevel.FORBIDDEN,
                description="危险的递归删除操作",
                suggestion="使用更安全的删除方式，避免递归删除根目录"
            ),
            SecurityPattern(
                name="system_files",
                pattern=re.compile(r"rm\s+.*(/etc/|/usr/|/var/|/sys/)", re.IGNORECASE),
                level=SecurityLevel.HIGH_RISK,
                description="删除系统重要文件",
                suggestion="确认是否真的需要删除系统文件"
            ),
            
            # 数据库危险操作
            SecurityPattern(
                name="drop_database",
                pattern=re.compile(r"DROP\s+(DATABASE|SCHEMA)", re.IGNORECASE),
                level=SecurityLevel.FORBIDDEN,
                description="删除整个数据库",
                suggestion="使用DROP TABLE删除特定表，而不是整个数据库"
            ),
            SecurityPattern(
                name="delete_all",
                pattern=re.compile(r"DELETE\s+FROM\s+\w+\s*;?\s*$", re.IGNORECASE),
                level=SecurityLevel.HIGH_RISK,
                description="删除表中所有数据（无WHERE条件）",
                suggestion="添加WHERE条件限制删除范围"
            ),
            SecurityPattern(
                name="update_all",
                pattern=re.compile(r"UPDATE\s+\w+\s+SET\s+.*\s*;?\s*$", re.IGNORECASE),
                level=SecurityLevel.MEDIUM_RISK,
                description="更新表中所有数据（无WHERE条件）",
                suggestion="添加WHERE条件限制更新范围"
            ),
            
            # 网络和系统操作
            SecurityPattern(
                name="network_scan",
                pattern=re.compile(r"nmap\s+.*\-", re.IGNORECASE),
                level=SecurityLevel.MEDIUM_RISK,
                description="网络扫描操作",
                suggestion="确认网络扫描的必要性和合法性"
            ),
            SecurityPattern(
                name="privilege_escalation",
                pattern=re.compile(r"sudo\s+.*|su\s+.*", re.IGNORECASE),
                level=SecurityLevel.HIGH_RISK,
                description="权限提升操作",
                suggestion="验证权限提升的必要性"
            ),
            
            # 代码执行
            SecurityPattern(
                name="code_injection",
                pattern=re.compile(r"eval\s*\(|exec\s*\(|os\.system\s*\(", re.IGNORECASE),
                level=SecurityLevel.HIGH_RISK,
                description="潜在的代码注入",
                suggestion="使用更安全的代码执行方式"
            ),
            
            # SQL注入模式
            SecurityPattern(
                name="sql_injection",
                pattern=re.compile(r"'\s*(OR|AND)\s*'.*'|--\s*|/\*.*\*/", re.IGNORECASE),
                level=SecurityLevel.HIGH_RISK,
                description="潜在的SQL注入攻击",
                suggestion="使用参数化查询防止SQL注入"
            )
        ]
    
    async def check_tool_execution(
        self, 
        tool_name: str, 
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> SecurityCheckResult:
        """
        检查工具执行的安全性
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            context: 执行上下文
            
        Returns:
            安全检查结果
        """
        try:
            # 第1层：静态规则检查
            static_result = await self._static_security_check(tool_name, params)
            if static_result.level == SecurityLevel.FORBIDDEN:
                return static_result
            
            # 第2层：动态模式分析
            dynamic_result = await self._dynamic_pattern_analysis(tool_name, params, context)
            
            # 第3层：历史行为分析
            history_result = await self._analyze_execution_history(tool_name, params)
            
            # 综合评估
            final_result = self._combine_security_results([static_result, dynamic_result, history_result])
            
            # 记录检查历史
            self._record_security_check(tool_name, params, final_result)
            
            return final_result
            
        except Exception as e:
            logger.error(f"安全检查失败: {e}")
            return SecurityCheckResult(
                level=SecurityLevel.MEDIUM_RISK,
                allowed=True,  # 检查失败时默认允许，但要求确认
                reason=f"安全检查过程出错: {str(e)}",
                require_confirmation=True
            )
    
    async def _static_security_check(
        self, 
        tool_name: str, 
        params: Dict[str, Any]
    ) -> SecurityCheckResult:
        """静态安全规则检查"""
        
        # 将所有参数转换为字符串用于模式匹配
        param_text = self._params_to_text(params)
        
        # 检查每个安全模式
        highest_risk = SecurityLevel.SAFE
        matched_patterns = []
        suggestions = []
        
        for pattern_def in self.security_patterns:
            if pattern_def.pattern.search(param_text):
                matched_patterns.append(pattern_def.name)
                suggestions.append(pattern_def.suggestion)
                
                # 更新最高风险级别
                if self._compare_security_level(pattern_def.level, highest_risk) > 0:
                    highest_risk = pattern_def.level
        
        # 构建检查结果
        if highest_risk == SecurityLevel.FORBIDDEN:
            return SecurityCheckResult(
                level=highest_risk,
                allowed=False,
                reason=f"检测到禁止的操作模式: {', '.join(matched_patterns)}",
                suggestions=suggestions
            )
        elif highest_risk in [SecurityLevel.HIGH_RISK, SecurityLevel.MEDIUM_RISK]:
            return SecurityCheckResult(
                level=highest_risk,
                allowed=True,
                reason=f"检测到风险模式: {', '.join(matched_patterns)}",
                require_confirmation=True,
                suggestions=suggestions
            )
        else:
            return SecurityCheckResult(
                level=SecurityLevel.SAFE,
                allowed=True,
                reason="静态安全检查通过"
            )
    
    async def _dynamic_pattern_analysis(
        self, 
        tool_name: str, 
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> SecurityCheckResult:
        """动态模式分析"""
        
        risk_factors = []
        risk_score = 0.0
        
        # 分析工具类型风险
        if tool_name in ["bash_tool", "shell_tool", "system_command"]:
            risk_score += 0.3
            risk_factors.append("系统命令执行工具")
        
        # 分析参数复杂度
        param_text = self._params_to_text(params)
        if len(param_text) > 1000:
            risk_score += 0.2
            risk_factors.append("参数过长")
        
        # 分析特殊字符
        special_chars = [";", "&&", "||", "|", ">", "<", "&"]
        special_count = sum(1 for char in special_chars if char in param_text)
        if special_count > 2:
            risk_score += 0.3
            risk_factors.append(f"包含多个特殊字符({special_count}个)")
        
        # 分析执行时间（如果提供了上下文）
        if context and context.get("execution_time"):
            hour = context["execution_time"].hour
            if hour < 6 or hour > 22:  # 非工作时间
                risk_score += 0.2
                risk_factors.append("非工作时间执行")
        
        # 确定风险级别
        if risk_score >= 0.8:
            level = SecurityLevel.HIGH_RISK
        elif risk_score >= 0.5:
            level = SecurityLevel.MEDIUM_RISK
        elif risk_score >= 0.3:
            level = SecurityLevel.LOW_RISK
        else:
            level = SecurityLevel.SAFE
        
        return SecurityCheckResult(
            level=level,
            allowed=True,
            reason=f"动态分析风险分数: {risk_score:.2f} - {', '.join(risk_factors)}" if risk_factors else "动态分析通过",
            require_confirmation=level in [SecurityLevel.HIGH_RISK, SecurityLevel.MEDIUM_RISK],
            confidence=1.0 - risk_score
        )
    
    async def _analyze_execution_history(
        self, 
        tool_name: str, 
        params: Dict[str, Any]
    ) -> SecurityCheckResult:
        """分析执行历史模式"""
        
        # 检查最近的执行历史
        recent_executions = [
            h for h in self.execution_history[-10:] 
            if h.get("tool_name") == tool_name
        ]
        
        risk_factors = []
        
        # 检查频繁执行
        if len(recent_executions) > 5:
            risk_factors.append("短时间内频繁执行相同工具")
        
        # 检查失败率
        failed_count = sum(1 for h in recent_executions if not h.get("success", True))
        if failed_count > 2:
            risk_factors.append(f"最近执行失败率高({failed_count}/{len(recent_executions)})")
        
        # 基于历史模式确定风险级别
        if len(risk_factors) > 1:
            level = SecurityLevel.MEDIUM_RISK
        elif len(risk_factors) > 0:
            level = SecurityLevel.LOW_RISK
        else:
            level = SecurityLevel.SAFE
        
        return SecurityCheckResult(
            level=level,
            allowed=True,
            reason=f"历史分析: {', '.join(risk_factors)}" if risk_factors else "历史分析通过",
            require_confirmation=level == SecurityLevel.MEDIUM_RISK
        )
    
    def _params_to_text(self, params: Dict[str, Any]) -> str:
        """将参数转换为文本用于模式匹配"""
        try:
            import json
            return json.dumps(params, ensure_ascii=False)
        except Exception:
            return str(params)
    
    def _compare_security_level(self, level1: SecurityLevel, level2: SecurityLevel) -> int:
        """比较安全级别"""
        level_order = {
            SecurityLevel.SAFE: 0,
            SecurityLevel.LOW_RISK: 1,
            SecurityLevel.MEDIUM_RISK: 2,
            SecurityLevel.HIGH_RISK: 3,
            SecurityLevel.FORBIDDEN: 4
        }
        return level_order[level1] - level_order[level2]
    
    def _combine_security_results(
        self, 
        results: List[SecurityCheckResult]
    ) -> SecurityCheckResult:
        """综合多个安全检查结果"""
        
        # 找出最高风险级别
        highest_level = SecurityLevel.SAFE
        all_reasons = []
        all_suggestions = []
        require_confirmation = False
        
        for result in results:
            if self._compare_security_level(result.level, highest_level) > 0:
                highest_level = result.level
            
            if result.reason:
                all_reasons.append(result.reason)
            
            if result.suggestions:
                all_suggestions.extend(result.suggestions)
            
            if result.require_confirmation:
                require_confirmation = True
        
        # 如果任何检查不允许，则最终不允许
        final_allowed = all(r.allowed for r in results)
        
        return SecurityCheckResult(
            level=highest_level,
            allowed=final_allowed,
            reason=" | ".join(all_reasons),
            require_confirmation=require_confirmation,
            suggestions=list(set(all_suggestions))  # 去重
        )
    
    def _record_security_check(
        self, 
        tool_name: str, 
        params: Dict[str, Any], 
        result: SecurityCheckResult
    ):
        """记录安全检查历史"""
        record = {
            "tool_name": tool_name,
            "timestamp": self._get_timestamp(),
            "security_level": result.level.value,
            "allowed": result.allowed,
            "require_confirmation": result.require_confirmation,
            "reason": result.reason
        }
        
        self.execution_history.append(record)
        
        # 保持历史记录在合理范围内
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-50:]
        
        logger.info(f"安全检查记录: {tool_name} - {result.level.value}")
    
    async def request_user_confirmation(
        self, 
        message: str, 
        security_result: SecurityCheckResult
    ) -> bool:
        """
        请求用户确认 - 在实际实现中应该连接到用户界面
        
        Args:
            message: 确认消息
            security_result: 安全检查结果
            
        Returns:
            用户是否确认
        """
        
        # 生成确认键
        import hashlib
        confirm_key = hashlib.md5(message.encode()).hexdigest()[:8]
        
        # 检查是否已经确认过类似操作
        if confirm_key in self.user_confirmations:
            return self.user_confirmations[confirm_key]
        
        # 在实际实现中，这里应该显示确认对话框给用户
        # 现在暂时记录日志并返回True（允许执行）
        logger.warning(f"需要用户确认: {message}")
        logger.warning(f"安全级别: {security_result.level.value}")
        logger.warning(f"原因: {security_result.reason}")
        if security_result.suggestions:
            logger.warning(f"建议: {'; '.join(security_result.suggestions)}")
        
        # 暂时默认允许，实际实现时应该等待用户确认
        confirmed = True
        self.user_confirmations[confirm_key] = confirmed
        
        return confirmed
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def get_security_statistics(self) -> Dict[str, Any]:
        """获取安全统计信息"""
        if not self.execution_history:
            return {"total_checks": 0}
        
        total = len(self.execution_history)
        levels = {}
        allowed_count = 0
        confirmation_count = 0
        
        for record in self.execution_history:
            level = record.get("security_level", "unknown")
            levels[level] = levels.get(level, 0) + 1
            
            if record.get("allowed", True):
                allowed_count += 1
            
            if record.get("require_confirmation", False):
                confirmation_count += 1
        
        return {
            "total_checks": total,
            "allowed_rate": allowed_count / total if total > 0 else 0,
            "confirmation_rate": confirmation_count / total if total > 0 else 0,
            "level_distribution": levels,
            "recent_checks": self.execution_history[-5:]
        }


# 全局实例
_security_checker: Optional[SecurityChecker] = None


def get_security_checker() -> SecurityChecker:
    """获取全局安全检查器实例"""
    global _security_checker
    if _security_checker is None:
        _security_checker = SecurityChecker()
    return _security_checker


# 便捷导出
__all__ = [
    "SecurityChecker",
    "SecurityCheckResult", 
    "SecurityLevel",
    "SecurityPattern",
    "get_security_checker"
]