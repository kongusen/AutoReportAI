"""
IAOP使用示例 - 演示完整的架构使用方式

包含：
- 配置管理
- 服务初始化
- Agent执行
- 中间件和钩子
- API使用
"""

import asyncio
import logging
from datetime import datetime

# 导入IAOP组件
from app.services.iaop import (
    initialize_iaop_system,
    shutdown_iaop_system,
    get_iaop_integrator,
    with_iaop_context
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_usage_example():
    """基础使用示例"""
    logger.info("=== IAOP基础使用示例 ===")
    
    # 初始化IAOP系统
    integrator = await initialize_iaop_system()
    
    try:
        # 获取系统状态
        status = integrator.get_system_status()
        logger.info(f"系统状态: {status['status']}")
        
        # 获取配置
        config = integrator.get_config()
        logger.info(f"调试模式: {config.system.debug}")
        logger.info(f"API端口: {config.api.port}")
        
        # 获取服务
        service_factory = integrator.get_service_factory()
        iaop_service = await service_factory.get_iaop_service()
        
        # 生成报告示例
        from app.services.iaop.api.schemas import ReportGenerationRequest, TaskType
        
        request = ReportGenerationRequest(
            placeholder_text="显示销售额前10的商品",
            task_type=TaskType.DATA_QUERY,
            data_source_context={"database": "sales"},
            template_context={"chart_type": "bar"}
        )
        
        # 使用服务生成报告
        result = await iaop_service.generate_report(request)
        logger.info(f"报告生成结果: {result.success}")
        
    finally:
        # 关闭系统
        await shutdown_iaop_system()


async def advanced_configuration_example():
    """高级配置示例"""
    logger.info("=== IAOP高级配置示例 ===")
    
    from app.services.iaop.core import ConfigManager, SystemConfig, AgentConfig
    
    # 创建自定义配置
    config_manager = ConfigManager()
    
    # 从字典加载配置
    custom_config = {
        "system": {
            "debug": True,
            "log_level": "DEBUG",
            "max_concurrent_tasks": 20
        },
        "agent": {
            "execution_timeout": 90,
            "max_concurrent_agents": 10
        },
        "api": {
            "port": 8888,
            "include_debug_info": True
        },
        "custom": {
            "company": "CustomCompany",
            "features": {
                "experimental_mode": True,
                "advanced_analytics": True
            }
        }
    }
    
    config_manager.load_from_dict(custom_config)
    
    # 使用自定义配置初始化系统
    from app.services.iaop.core.integration import IAOPIntegrator
    
    integrator = IAOPIntegrator(config_manager)
    await integrator.initialize()
    
    try:
        # 验证配置
        config = integrator.get_config()
        logger.info(f"自定义调试模式: {config.system.debug}")
        logger.info(f"自定义API端口: {config.api.port}")
        logger.info(f"自定义功能开关: {config.custom.get('features', {})}")
        
        # 获取配置摘要
        summary = config_manager.get_config_summary()
        logger.info(f"配置摘要: {summary}")
        
    finally:
        await integrator.shutdown()


async def middleware_and_hooks_example():
    """中间件和钩子示例"""
    logger.info("=== IAOP中间件和钩子示例 ===")
    
    integrator = await initialize_iaop_system()
    
    try:
        # 获取中间件管理器
        middleware_manager = integrator.get_middleware_manager()
        
        # 执行中间件
        from app.services.iaop.core.middleware import MiddlewareType
        
        context_data = {
            "request_id": "test_123",
            "request": {
                "placeholder_text": "测试占位符",
                "task_type": "data_query"
            }
        }
        
        # 执行预请求中间件
        pre_results = await middleware_manager.execute_middlewares(
            MiddlewareType.PRE_REQUEST, 
            context_data
        )
        logger.info(f"预请求中间件结果: {len(pre_results)} 个中间件执行")
        
        # 模拟请求处理完成
        context_data.update({
            "success": True,
            "execution_time": 2.5,
            "result": {"data": "processed"}
        })
        
        # 执行后请求中间件
        post_results = await middleware_manager.execute_middlewares(
            MiddlewareType.POST_REQUEST,
            context_data
        )
        logger.info(f"后请求中间件结果: {len(post_results)} 个中间件执行")
        
        # 获取中间件状态
        middleware_status = middleware_manager.get_middleware_status()
        logger.info("中间件状态获取完成")
        
        # 获取钩子管理器
        hook_manager = integrator.get_hook_manager()
        
        # 触发钩子
        from app.services.iaop.core.hooks import HookType
        
        hook_results = await hook_manager.trigger_hook(
            HookType.REQUEST_START,
            "example_source",
            {
                "request_id": "test_123",
                "placeholder_text": "测试钩子",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        logger.info(f"钩子触发结果: {len(hook_results)} 个钩子执行")
        
        # 获取钩子统计
        hook_stats = hook_manager.get_hook_stats()
        logger.info("钩子统计获取完成")
        
    finally:
        await shutdown_iaop_system()


@with_iaop_context
async def agent_execution_example(integrator):
    """Agent执行示例"""
    logger.info("=== IAOP Agent执行示例 ===")
    
    # 获取服务工厂
    service_factory = integrator.get_service_factory()
    
    # 获取Agent注册器
    agent_registry = await service_factory.get_agent_registry()
    
    # 获取上下文管理器
    context_manager = await service_factory.get_context_manager()
    
    # 创建执行上下文
    execution_context = context_manager.create_context(
        user_id="test_user",
        task_id="test_task"
    )
    
    # 获取占位符解析Agent
    placeholder_agent = agent_registry.get_agent("placeholder_parser")
    if placeholder_agent:
        # 准备输入数据
        input_data = {
            "placeholder_text": "显示{{数据源}}中{{时间范围}}的{{指标}}趋势",
            "template_vars": {
                "数据源": "sales_data",
                "时间范围": "最近30天", 
                "指标": "销售额"
            }
        }
        
        # 执行Agent
        result = await placeholder_agent.execute(execution_context, input_data)
        logger.info(f"占位符解析结果: {result.get('success', False)}")
        
        if result.get('success'):
            parsed_data = result.get('output', {})
            logger.info(f"解析后的数据: {parsed_data}")
    
    # 清理上下文
    context_manager.cleanup_context(execution_context.session_id)


async def complete_workflow_example():
    """完整工作流示例"""
    logger.info("=== IAOP完整工作流示例 ===")
    
    integrator = await initialize_iaop_system()
    
    try:
        # 获取IAOP服务
        service_factory = integrator.get_service_factory()
        iaop_service = await service_factory.get_iaop_service()
        
        # 模拟批量处理占位符
        from app.services.iaop.api.schemas import PlaceholderRequest, ExecutionMode
        
        placeholder_request = PlaceholderRequest(
            template_content="报告模板：显示{{商品类别}}的{{指标}}数据，生成{{图表类型}}图表。",
            variables={
                "商品类别": "electronics",
                "指标": "销售额",
                "图表类型": "柱状"
            },
            execution_mode=ExecutionMode.PIPELINE
        )
        
        # 处理占位符
        batch_result = await iaop_service.process_placeholders(placeholder_request)
        logger.info(f"批量处理结果: {batch_result.success}")
        
        if batch_result.success:
            for idx, result in enumerate(batch_result.results):
                logger.info(f"任务 {idx + 1}: {result.success}")
        
        # 获取系统状态
        system_status = await iaop_service.get_system_status()
        logger.info(f"系统状态: 运行中，已处理 {system_status.total_requests} 个请求")
        
    finally:
        await shutdown_iaop_system()


async def main():
    """主函数 - 运行所有示例"""
    print("开始IAOP使用示例演示...")
    print("=" * 50)
    
    try:
        # 基础使用示例
        await basic_usage_example()
        print()
        
        # 高级配置示例
        await advanced_configuration_example()
        print()
        
        # 中间件和钩子示例
        await middleware_and_hooks_example()
        print()
        
        # Agent执行示例
        await agent_execution_example()
        print()
        
        # 完整工作流示例
        await complete_workflow_example()
        print()
        
        print("所有示例执行完成！")
        
    except Exception as e:
        logger.error(f"示例执行失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())