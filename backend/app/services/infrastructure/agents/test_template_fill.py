"""
模板填充系统测试脚本
==================

测试新的模板填充工具和domain层集成
"""

import asyncio
import logging
from typing import Dict, Any

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_template_fill_tool():
    """测试TemplateFillTool"""
    
    try:
        from .tools.data.report_tool import TemplateFillTool
        from .tools.core.base import ToolExecutionContext
        
        logger.info("=== 测试TemplateFillTool ===")
        
        # 创建工具实例
        tool = TemplateFillTool()
        
        # 准备测试数据
        test_input = {
            'template_content': '''
公司业绩报告
===========

公司名称：{company_name}
报告期间：{report_period}
销售收入：{revenue}万元
利润率：{profit_margin}%

业务总结：
{business_summary}

数据来源：{data_source}
生成时间：{generation_time}
            ''',
            'placeholders': {
                'company_name': '智能科技有限公司',
                'report_period': '2024年第一季度',
                'revenue': 1250.8,
                'profit_margin': 15.3,
                'business_summary': '本季度业务发展稳健，各项指标均达到预期目标。',
                'data_source': '财务系统',
                'generation_time': '2024-01-15 10:30:00'
            },
            'template_type': 'word',
            'fill_mode': 'smart',
            'add_descriptions': True,
            'generate_word_document': True,
            'document_title': '季度业绩报告',
            'enable_quality_check': True
        }
        
        # 创建执行上下文
        context = ToolExecutionContext(
            request_id="test_001",
            user_id="test_user",
            session_id="test_session"
        )
        
        # 执行工具
        logger.info("开始执行模板填充...")
        results = []
        async for result in tool.execute(test_input, context):
            results.append(result)
            logger.info(f"收到结果: {result.data.get('status', 'unknown')}")
        
        # 检查最终结果
        final_result = results[-1] if results else None
        if final_result and final_result.success:
            data = final_result.data
            logger.info("=== 模板填充成功 ===")
            logger.info(f"填充的占位符数量: {data.get('template_analysis', {}).get('filled_placeholders', 0)}")
            logger.info(f"生成了描述: {len(data.get('descriptions', {}))}")
            
            # 检查Word文档生成
            word_result = data.get('word_document')
            if word_result and word_result.get('success'):
                logger.info(f"Word文档生成成功: {word_result.get('word_document_path', 'N/A')}")
                
                # 检查质量检查结果
                quality_check = word_result.get('quality_check')
                if quality_check:
                    logger.info(f"质量检查分数: {quality_check.get('overall_score', 'N/A')}")
            else:
                logger.warning("Word文档生成失败或跳过")
            
            logger.info("✅ TemplateFillTool测试通过")
        else:
            logger.error("❌ TemplateFillTool测试失败")
            if final_result:
                logger.error(f"错误: {final_result.error}")
    
    except ImportError as e:
        logger.error(f"导入错误: {e}")
    except Exception as e:
        logger.error(f"测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()


async def test_context_builder():
    """测试上下文构建器的模板填充支持"""
    
    try:
        from .context.context_builder import AgentContextBuilder, ContextType, PlaceholderType, PlaceholderInfo, TemplateInfo, TaskInfo
        
        logger.info("=== 测试ContextBuilder模板填充支持 ===")
        
        builder = AgentContextBuilder()
        
        # 创建任务信息
        task_info = TaskInfo(
            task_id="test_template_fill",
            task_name="模板填充测试",
            task_type="template_fill",
            description="测试模板填充功能"
        )
        
        # 创建占位符
        placeholders = [
            PlaceholderInfo(
                name="company_name",
                type=PlaceholderType.TEMPLATE_VARIABLE,
                value="测试公司"
            ),
            PlaceholderInfo(
                name="fill_mode",
                type=PlaceholderType.FILL_MODE,
                value="smart"
            )
        ]
        
        # 创建模板信息
        templates = [
            TemplateInfo(
                template_id="test_template",
                name="测试模板",
                template_type="word",
                content="公司名称：{company_name}，这是一个测试模板。"
            )
        ]
        
        # 构建上下文
        context = builder.build_context(
            task_info=task_info,
            placeholders=placeholders,
            templates=templates
        )
        
        # 检查结果
        if context.context_type == ContextType.TEMPLATE_FILLING:
            logger.info("✅ 正确识别为模板填充上下文")
            
            # 检查工具偏好
            tool_prefs = context.tool_preferences
            if "template_fill_tool" in tool_prefs.get("preferred_tools", []):
                logger.info("✅ 正确配置了template_fill_tool偏好")
            else:
                logger.warning("⚠️  未找到template_fill_tool工具偏好")
        else:
            logger.error(f"❌ 上下文类型识别错误: {context.context_type}")
        
        logger.info("✅ ContextBuilder测试完成")
    
    except ImportError as e:
        logger.error(f"导入错误: {e}")
    except Exception as e:
        logger.error(f"测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()


async def test_domain_integration():
    """测试domain层集成"""
    
    try:
        from .tools.data.template_domain_integration import process_template_to_word
        
        logger.info("=== 测试Domain层集成 ===")
        
        # 准备模拟的模板填充结果
        template_fill_result = {
            'success': True,
            'filled_content': '这是一个测试报告\n\n公司名称：测试公司\n收入：1000万元',
            'domain_data': {
                'template_analysis': {
                    'total_placeholders': 2,
                    'filled_count': 2,
                    'missing_placeholders': [],
                    'complexity_score': 10,
                    'structure': {
                        'contains_tables': False,
                        'contains_images': False,
                        'paragraph_count': 2
                    }
                },
                'placeholder_data': {
                    'company_name': '测试公司',
                    'revenue': '1000'
                },
                'placeholder_descriptions': {
                    'company_name': '公司名称数据',
                    'revenue': '收入数据'
                },
                'word_generation_params': {
                    'preserve_formatting': True,
                    'document_style': 'professional'
                },
                'quality_check_params': {
                    'check_placeholder_completeness': True
                }
            },
            'metadata': {
                'template_type': 'word',
                'fill_mode': 'smart',
                'tool_version': '1.0.0'
            }
        }
        
        # 测试集成处理
        result = await process_template_to_word(
            template_fill_result=template_fill_result,
            title="集成测试报告",
            enable_quality_check=False  # 暂时关闭质量检查避免复杂依赖
        )
        
        if result.get('success'):
            logger.info("✅ Domain集成测试成功")
            logger.info(f"处理结果: {result.get('generation_metadata', {}).get('integration_version', 'N/A')}")
        else:
            logger.error(f"❌ Domain集成测试失败: {result.get('error', 'Unknown error')}")
    
    except ImportError as e:
        logger.error(f"导入错误: {e}")
    except Exception as e:
        logger.error(f"测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    
    logger.info("开始测试新的模板填充系统...")
    
    # 运行各个测试
    await test_context_builder()
    await test_domain_integration()
    await test_template_fill_tool()
    
    logger.info("所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())