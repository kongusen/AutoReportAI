"""
IAOP集成模块 - 提供与现有系统的无缝集成

这个模块提供了将IAOP平台集成到现有系统的所有必要组件：
- 系统桥接器：连接IAOP平台与现有数据模型
- AI服务适配器：替代现有AI服务的IAOP版本  
- 服务替换器：智能路由和fallback机制
"""

from .system_bridge import (
    IAOPSystemBridge,
    get_iaop_bridge,
    process_template_with_iaop,
    process_task_with_iaop
)

from .ai_service_adapter import (
    IAOPAIService,
    get_iaop_ai_service,
    IAOPAIRequest,
    IAOPAIResponse
)

from .service_replacer import (
    AIServiceProxy,
    get_ai_service_proxy,
    create_enhanced_ai_service,
    configure_ai_service_routing,
    IAOPServiceConfig
)

__all__ = [
    # 系统桥接
    "IAOPSystemBridge",
    "get_iaop_bridge", 
    "process_template_with_iaop",
    "process_task_with_iaop",
    
    # AI服务适配
    "IAOPAIService",
    "get_iaop_ai_service",
    "IAOPAIRequest",
    "IAOPAIResponse",
    
    # 服务替换
    "AIServiceProxy",
    "get_ai_service_proxy",
    "create_enhanced_ai_service",
    "configure_ai_service_routing",
    "IAOPServiceConfig"
]


def setup_iaop_integration(db_session, enable_iaop: bool = True):
    """
    设置IAOP集成 - 一键配置函数
    
    Args:
        db_session: 数据库会话
        enable_iaop: 是否启用IAOP（True=IAOP优先，False=传统服务）
    
    Returns:
        配置好的AI服务代理
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 配置AI服务路由
        ai_proxy = AIServiceProxy(db_session, use_iaop=enable_iaop)
        
        # 如果启用IAOP，进行初始化检查
        if enable_iaop:
            bridge = get_iaop_bridge(db_session)
            # 这里可以添加初始化逻辑
            
        logger.info(f"IAOP集成设置完成，IAOP启用: {enable_iaop}")
        return ai_proxy
        
    except Exception as e:
        logger.error(f"IAOP集成设置失败: {e}")
        # Fallback到传统服务
        return AIServiceProxy(db_session, use_iaop=False)


def get_integrated_ai_service(db_session):
    """
    获取集成的AI服务 - 这是现有代码的直接替换点
    
    现有代码中的：
    # 避免循环导入，直接使用本地IAOP服务
    from .ai_service_adapter import IAOPAIService as EnhancedAIService
    service = EnhancedAIService(db)
    
    可以替换为：
    from app.services.iaop.integration import get_integrated_ai_service
    service = get_integrated_ai_service(db)
    """
    return create_enhanced_ai_service(db_session)