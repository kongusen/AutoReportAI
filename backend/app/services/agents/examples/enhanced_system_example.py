"""
增强Agent系统使用示例

展示如何使用完整的增强Agent系统，包括：
- 智能Agent编排
- 知识共享机制
- 跨Agent协作
- 用户个性化

Usage Example:
    python enhanced_system_example.py
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List

from ..orchestration import SmartOrchestrator, OrchestrationRequest, ExecutionMode
from ..enhanced import (
    EnhancedDataQueryAgent, 
    EnhancedContentGenerationAgent,
    EnhancedAnalysisAgent, 
    EnhancedVisualizationAgent
)
from ..knowledge import (
    KnowledgeShareManager, 
    KnowledgeContext, 
    AgentKnowledgeIntegrator
)


class EnhancedAgentSystemDemo:
    """增强Agent系统演示"""
    
    def __init__(self):
        # 初始化知识管理器
        self.knowledge_manager = KnowledgeShareManager()
        
        # 初始化增强Agents
        self.data_agent = EnhancedDataQueryAgent()
        self.content_agent = EnhancedContentGenerationAgent()
        self.analysis_agent = EnhancedAnalysisAgent()
        self.viz_agent = EnhancedVisualizationAgent()
        
        # 初始化智能编排器
        self.orchestrator = SmartOrchestrator()
        
        # 注册Agents到编排器
        self.orchestrator.register_agent("data_query", self.data_agent)
        self.orchestrator.register_agent("content_generation", self.content_agent)
        self.orchestrator.register_agent("analysis", self.analysis_agent)
        self.orchestrator.register_agent("visualization", self.viz_agent)
    
    async def demo_intelligent_orchestration(self):
        """演示智能编排功能"""
        print("=== 智能编排演示 ===")
        
        # 复杂用户请求
        user_request = """
        我需要分析销售数据的趋势，包括：
        1. 查询最近3个月的销售数据
        2. 进行趋势分析和异常检测
        3. 生成分析报告
        4. 创建可视化图表
        请帮我完成这些任务
        """
        
        context = {
            "user_id": "demo_user_001",
            "session_id": "demo_session_001",
            "data_source": "sales_db",
            "time_range": "3_months"
        }
        
        try:
            # 使用智能编排器处理请求
            orchestration_request = OrchestrationRequest(
                user_request=user_request,
                context=context,
                execution_mode=ExecutionMode.PIPELINE,
                user_id="demo_user_001"
            )
            
            result = await self.orchestrator.orchestrate_request(orchestration_request)
            
            print(f"编排结果: {result.success}")
            print(f"执行的Agent数量: {len(result.agent_results)}")
            print(f"生成的洞察: {len(result.insights)}")
            
            # 显示执行流程
            for i, agent_result in enumerate(result.agent_results, 1):
                print(f"步骤 {i}: {agent_result.agent_id} - {'成功' if agent_result.success else '失败'}")
            
            return result
            
        except Exception as e:
            print(f"编排失败: {e}")
            return None
    
    async def demo_knowledge_sharing(self):
        """演示知识共享功能"""
        print("\n=== 知识共享演示 ===")
        
        # 模拟一些Agent执行历史
        agent_results = [
            {
                'agent_id': 'enhanced_data_query_agent',
                'execution_time': 2.5,
                'success': True,
                'data_size': 1000,
                'timestamp': datetime.now().timestamp()
            },
            {
                'agent_id': 'enhanced_analysis_agent', 
                'execution_time': 5.2,
                'success': True,
                'data_size': 1000,
                'timestamp': datetime.now().timestamp()
            },
            {
                'agent_id': 'enhanced_content_generation_agent',
                'execution_time': 1.8,
                'success': True,
                'data_size': 500,
                'timestamp': datetime.now().timestamp()
            }
        ]
        
        try:
            # 生成跨Agent洞察
            insights = await self.knowledge_manager.generate_insights(agent_results)
            print(f"生成了 {len(insights)} 个洞察:")
            
            for insight in insights:
                print(f"- {insight.insight_type}: {insight.insight_content}")
            
            # 分享知识
            knowledge_id = await self.knowledge_manager.share_knowledge(
                agent_id="demo_system",
                knowledge_type="best_practice",
                content={
                    "practice": "数据查询->分析->内容生成流水线",
                    "performance": "平均执行时间 3.17秒",
                    "success_rate": 1.0
                },
                tags=["pipeline", "data_analysis", "best_practice"],
                confidence=0.9
            )
            print(f"知识已分享，ID: {knowledge_id}")
            
            # 获取推荐
            recommendations = await self.knowledge_manager.get_recommendations(
                agent_id="enhanced_data_query_agent",
                context={"task_type": "data_query", "user_id": "demo_user_001"},
                recommendation_type="best_practice"
            )
            print(f"获得 {len(recommendations)} 个推荐")
            
            return insights, recommendations
            
        except Exception as e:
            print(f"知识共享演示失败: {e}")
            return [], []
    
    async def demo_user_personalization(self):
        """演示用户个性化功能"""
        print("\n=== 用户个性化演示 ===")
        
        user_id = "demo_user_001"
        
        try:
            # 模拟用户交互历史
            interactions = [
                {
                    'type': 'query',
                    'fields': ['sales_amount', 'date', 'region'],
                    'filters': [{'operator': 'gte', 'field': 'date'}],
                    'time_range': '3_months'
                },
                {
                    'type': 'content_feedback',
                    'style': 'professional',
                    'length': 'medium',
                    'score': 0.9
                },
                {
                    'type': 'content_feedback',
                    'style': 'technical',
                    'length': 'long',
                    'score': 0.7
                }
            ]
            
            # 学习用户模式
            await self.knowledge_manager.learn_from_interactions(user_id, interactions)
            print("已学习用户交互模式")
            
            # 获取用户洞察
            user_insights = await self.knowledge_manager.get_user_insights(user_id)
            print(f"用户洞察:")
            print(f"- 总模式数: {user_insights['total_patterns']}")
            print(f"- 推荐数: {len(user_insights['recommendations'])}")
            
            for pattern_type, patterns in user_insights['patterns_by_type'].items():
                print(f"- {pattern_type}: {len(patterns)} 个模式")
            
            return user_insights
            
        except Exception as e:
            print(f"用户个性化演示失败: {e}")
            return None
    
    async def demo_enhanced_agents(self):
        """演示增强Agent功能"""
        print("\n=== 增强Agent演示 ===")
        
        demo_data = [
            {"date": "2024-01-01", "sales": 1000, "region": "North"},
            {"date": "2024-01-02", "sales": 1200, "region": "South"},
            {"date": "2024-01-03", "sales": 800, "region": "East"},
            {"date": "2024-01-04", "sales": 1500, "region": "West"},
            {"date": "2024-01-05", "sales": 900, "region": "North"},
        ]
        
        try:
            # 演示增强数据查询Agent
            print("1. 增强数据查询Agent:")
            from ..enhanced.enhanced_data_query_agent import SemanticQueryRequest
            query_request = SemanticQueryRequest(
                query="显示北部地区的销售数据",
                data_source="demo_data",
                natural_language=True,
                semantic_enhancement=True
            )
            
            # 模拟查询结果
            print("- 语义查询解析完成")
            print("- 智能字段映射完成")
            print("- 查询优化完成")
            
            # 演示增强分析Agent
            print("\n2. 增强分析Agent:")
            from ..enhanced.enhanced_analysis_agent import MLAnalysisRequest
            analysis_request = MLAnalysisRequest(
                data=demo_data,
                analysis_type="comprehensive",
                target_variable="sales",
                enable_feature_engineering=True
            )
            
            analysis_result = await self.analysis_agent.execute_ml_analysis(analysis_request)
            print(f"- 机器学习分析: {'成功' if analysis_result.success else '失败'}")
            if analysis_result.success:
                metadata = analysis_result.data.metadata
                print(f"- 生成洞察: {len(metadata.get('insights', []))}")
            
            # 演示增强内容生成Agent
            print("\n3. 增强内容生成Agent:")
            from ..enhanced.enhanced_content_generation_agent import ContextualContentRequest
            content_request = ContextualContentRequest(
                content_type="analysis_report",
                data={"analysis_results": "销售数据显示上升趋势"},
                conversation_id="demo_conversation",
                style_requirements={"tone": "professional", "formality": "high"},
                quality_criteria={"min_length": 100}
            )
            
            content_result = await self.content_agent.execute_contextual(
                content_request, 
                user_id="demo_user_001"
            )
            print(f"- 上下文内容生成: {'成功' if content_result.success else '失败'}")
            if content_result.success:
                print(f"- 个性化应用: {content_result.metadata.get('personalized', False)}")
            
            # 演示增强可视化Agent  
            print("\n4. 增强可视化Agent:")
            from ..enhanced.enhanced_visualization_agent import SmartVisualizationRequest
            viz_request = SmartVisualizationRequest(
                data=demo_data,
                chart_purpose="trend_analysis", 
                target_audience="business_users",
                enable_smart_recommendations=True,
                enable_storytelling=True
            )
            
            viz_result = await self.viz_agent.execute_smart_visualization(viz_request)
            print(f"- 智能可视化: {'成功' if viz_result.success else '失败'}")
            if viz_result.success:
                recommendations = viz_result.data.metadata.get('chart_recommendations', [])
                print(f"- 图表推荐: {len(recommendations)}")
            
            return True
            
        except Exception as e:
            print(f"增强Agent演示失败: {e}")
            return False
    
    async def demo_system_integration(self):
        """演示系统集成"""
        print("\n=== 系统集成演示 ===")
        
        try:
            # 获取系统统计
            kb_stats = await self.knowledge_manager.get_knowledge_statistics()
            print("知识库统计:")
            print(f"- 总知识项: {kb_stats['total_knowledge_items']}")
            print(f"- 平均置信度: {kb_stats['avg_confidence']:.3f}")
            print(f"- 平均使用率: {kb_stats['avg_usage']:.1f}")
            
            # 健康检查
            health_checks = []
            for agent_name, agent in [
                ("数据查询Agent", self.data_agent),
                ("内容生成Agent", self.content_agent), 
                ("分析Agent", self.analysis_agent),
                ("可视化Agent", self.viz_agent)
            ]:
                try:
                    health = await agent.health_check()
                    health_checks.append((agent_name, health.get('healthy', False)))
                except:
                    health_checks.append((agent_name, False))
            
            print("\nAgent健康状态:")
            for name, healthy in health_checks:
                print(f"- {name}: {'健康' if healthy else '异常'}")
            
            # 编排器状态
            orchestrator_health = await self.orchestrator.health_check()
            print(f"- 智能编排器: {'健康' if orchestrator_health.get('healthy', False) else '异常'}")
            
            return all(healthy for _, healthy in health_checks) and orchestrator_health.get('healthy', False)
            
        except Exception as e:
            print(f"系统集成检查失败: {e}")
            return False
    
    async def run_complete_demo(self):
        """运行完整演示"""
        print("🚀 增强Agent系统完整演示")
        print("=" * 50)
        
        try:
            # 1. 智能编排演示
            orchestration_result = await self.demo_intelligent_orchestration()
            
            # 2. 知识共享演示
            insights, recommendations = await self.demo_knowledge_sharing()
            
            # 3. 用户个性化演示
            user_insights = await self.demo_user_personalization()
            
            # 4. 增强Agent演示
            agents_success = await self.demo_enhanced_agents()
            
            # 5. 系统集成演示
            system_healthy = await self.demo_system_integration()
            
            # 总结
            print("\n" + "=" * 50)
            print("📊 演示总结:")
            print(f"✅ 智能编排: {'成功' if orchestration_result else '失败'}")
            print(f"✅ 知识共享: {len(insights)} 个洞察, {len(recommendations)} 个推荐")
            print(f"✅ 用户个性化: {'完成' if user_insights else '失败'}")
            print(f"✅ 增强Agents: {'全部成功' if agents_success else '部分失败'}")
            print(f"✅ 系统健康: {'良好' if system_healthy else '异常'}")
            
            print("\n🎉 增强Agent系统演示完成！")
            print("系统已实现:")
            print("- 4个增强Agent (数据查询、内容生成、分析、可视化)")
            print("- 智能编排和协作")
            print("- 跨Agent知识共享")
            print("- 用户行为学习和个性化")
            print("- 实时性能优化")
            
        except Exception as e:
            print(f"演示执行失败: {e}")


async def main():
    """主函数"""
    demo = EnhancedAgentSystemDemo()
    await demo.run_complete_demo()


if __name__ == "__main__":
    asyncio.run(main())