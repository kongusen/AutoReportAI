"""
Task Status Constants

任务状态常量定义
"""

class TaskStatus:
    """任务状态常量"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    QUERYING = "querying"
    PROCESSING = "processing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    STARTED = "started"
    CANCELLED = "cancelled"
