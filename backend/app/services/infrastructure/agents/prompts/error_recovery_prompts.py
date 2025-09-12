"""
错误恢复指令系统
================

为Agent提供智能错误恢复策略和指令。
当Agent遇到错误或异常情况时，提供相应的恢复方案。
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """错误类型枚举"""
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    MEMORY_ERROR = "memory_error"
    TIMEOUT_ERROR = "timeout_error"
    VALIDATION_ERROR = "validation_error"
    PERMISSION_ERROR = "permission_error"
    RESOURCE_NOT_FOUND = "resource_not_found"
    PROCESSING_ERROR = "processing_error"


class ErrorRecoveryPrompts:
    """错误恢复提示词集合"""
    
    NETWORK_ERROR_RECOVERY = """
网络连接错误恢复策略：

1. **重试机制**
   - 等待3-5秒后重试
   - 最多重试3次
   - 使用指数退避策略

2. **降级处理**
   - 使用缓存数据
   - 使用默认值
   - 简化操作范围

3. **用户通知**
   - 说明网络问题
   - 提供预估恢复时间
   - 建议替代方案
"""

    DATABASE_ERROR_RECOVERY = """
数据库错误恢复策略：

1. **连接问题**
   - 检查数据库连接池
   - 重新建立连接
   - 使用备份数据源

2. **查询优化**
   - 简化复杂查询
   - 分批处理大数据集
   - 添加适当的索引建议

3. **事务处理**
   - 回滚未完成事务
   - 检查数据一致性
   - 重新执行关键操作
"""

    MEMORY_ERROR_RECOVERY = """
内存不足错误恢复策略：

1. **数据分页**
   - 将大数据集分批处理
   - 限制单次查询结果数量
   - 使用流式处理

2. **内存优化**
   - 清理不必要的变量
   - 使用生成器而非列表
   - 实施垃圾回收

3. **处理降级**
   - 减少并发任务
   - 简化数据结构
   - 使用外部存储
"""

    TIMEOUT_ERROR_RECOVERY = """
超时错误恢复策略：

1. **任务分解**
   - 将长任务分解为小任务
   - 实施检查点机制
   - 支持断点续传

2. **优化性能**
   - 减少数据传输量
   - 优化算法复杂度
   - 并行处理可能的部分

3. **用户体验**
   - 显示处理进度
   - 提供取消选项
   - 异步处理结果通知
"""

    VALIDATION_ERROR_RECOVERY = """
验证错误恢复策略：

1. **数据清理**
   - 自动修正常见格式问题
   - 移除无效字符
   - 标准化数据格式

2. **智能建议**
   - 提供修正建议
   - 显示正确格式示例
   - 高亮问题字段

3. **部分接受**
   - 处理有效部分数据
   - 记录问题数据项
   - 提供手动修正界面
"""

    PERMISSION_ERROR_RECOVERY = """
权限错误恢复策略：

1. **权限检查**
   - 验证当前用户权限
   - 请求必要权限升级
   - 使用替代认证方式

2. **功能降级**
   - 提供只读功能
   - 限制敏感操作
   - 使用公共数据

3. **用户指导**
   - 说明权限要求
   - 提供获取权限步骤
   - 联系管理员选项
"""

    GENERAL_ERROR_RECOVERY = """
通用错误恢复策略：

1. **错误分析**
   - 记录详细错误信息
   - 分析错误模式
   - 识别根本原因

2. **恢复尝试**
   - 按严重程度排序恢复策略
   - 逐步尝试不同方案
   - 监控恢复效果

3. **用户沟通**
   - 提供清晰错误说明
   - 建议具体解决步骤
   - 估计修复时间
"""


def get_error_recovery_prompt(error_type: ErrorType) -> str:
    """
    获取特定错误类型的恢复提示词
    
    Args:
        error_type: 错误类型
        
    Returns:
        对应的恢复提示词
    """
    
    recovery_map = {
        ErrorType.NETWORK_ERROR: ErrorRecoveryPrompts.NETWORK_ERROR_RECOVERY,
        ErrorType.DATABASE_ERROR: ErrorRecoveryPrompts.DATABASE_ERROR_RECOVERY,
        ErrorType.MEMORY_ERROR: ErrorRecoveryPrompts.MEMORY_ERROR_RECOVERY,
        ErrorType.TIMEOUT_ERROR: ErrorRecoveryPrompts.TIMEOUT_ERROR_RECOVERY,
        ErrorType.VALIDATION_ERROR: ErrorRecoveryPrompts.VALIDATION_ERROR_RECOVERY,
        ErrorType.PERMISSION_ERROR: ErrorRecoveryPrompts.PERMISSION_ERROR_RECOVERY
    }
    
    return recovery_map.get(error_type, ErrorRecoveryPrompts.GENERAL_ERROR_RECOVERY)


def get_complete_error_recovery_instructions(
    error_type: ErrorType,
    context: Dict[str, Any] = None,
    additional_info: str = ""
) -> str:
    """
    获取完整的错误恢复指令
    
    Args:
        error_type: 错误类型
        context: 错误上下文信息
        additional_info: 额外信息
        
    Returns:
        完整的恢复指令
    """
    
    base_prompt = get_error_recovery_prompt(error_type)
    
    instructions = f"""
# 错误恢复指令

## 错误类型
{error_type.value}

## 恢复策略
{base_prompt}

## 上下文信息
"""
    
    if context:
        for key, value in context.items():
            instructions += f"- {key}: {value}\n"
    
    if additional_info:
        instructions += f"\n## 额外信息\n{additional_info}\n"
    
    instructions += """
## 执行要求
1. 按照优先级顺序尝试恢复策略
2. 记录每次尝试的结果
3. 如果所有策略都失败，请求人工干预
4. 保持与用户的及时沟通

## 成功标准
- 系统恢复正常功能
- 用户能继续正常操作
- 数据完整性得到保证
- 错误原因已被解决或缓解
"""
    
    return instructions


# 便捷函数
def create_recovery_strategy(
    error_type: ErrorType,
    severity: str = "medium",
    auto_retry: bool = True
) -> Dict[str, Any]:
    """
    创建错误恢复策略
    
    Args:
        error_type: 错误类型
        severity: 错误严重程度 (low, medium, high, critical)
        auto_retry: 是否自动重试
        
    Returns:
        恢复策略配置
    """
    
    return {
        "error_type": error_type.value,
        "severity": severity,
        "auto_retry": auto_retry,
        "max_retries": 3 if auto_retry else 0,
        "retry_delay": 5,  # 秒
        "recovery_prompt": get_error_recovery_prompt(error_type),
        "escalate_after_failures": 3
    }


__all__ = [
    "ErrorType",
    "ErrorRecoveryPrompts",
    "get_error_recovery_prompt",
    "get_complete_error_recovery_instructions",
    "create_recovery_strategy"
]