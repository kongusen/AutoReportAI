"""
IAOP迁移指南 - 展示如何将现有AI服务调用迁移到IAOP平台

这个文件提供了具体的迁移示例和最佳实践
"""

import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class IAOPMigrationGuide:
    """IAOP迁移指南"""
    
    @staticmethod
    def show_migration_examples():
        """展示迁移示例"""
        
        print("=" * 60)
        print("IAOP平台迁移指南")
        print("=" * 60)
        
        print("\n1. 基础AI服务替换:")
        print("=" * 40)
        print("原代码:")
        print("""
# 避免循环导入，直接引用本地类
from .ai_service_adapter import IAOPAIService as EnhancedAIService

def some_function(db: Session):
    ai_service = EnhancedAIService(db)
    result = await ai_service.analyze_placeholder_requirements(placeholder_data, data_source_id)
    return result
        """)
        
        print("新代码 (方式1 - 直接替换):")
        print("""
from app.services.iaop.integration import get_integrated_ai_service

def some_function(db: Session):
    ai_service = get_integrated_ai_service(db)  # 自动使用IAOP或fallback
    result = await ai_service.analyze_placeholder_requirements(placeholder_data, data_source_id)
    return result
        """)
        
        print("新代码 (方式2 - 显式使用代理):")
        print("""
from app.services.iaop.integration import get_ai_service_proxy

def some_function(db: Session):
    ai_proxy = get_ai_service_proxy(db, use_iaop=True)
    result = await ai_proxy.analyze_placeholder_requirements(placeholder_data, data_source_id)
    return result
        """)
        
        print("\n2. 模板处理迁移:")
        print("=" * 40)
        print("原代码:")
        print("""
# 在模板处理中使用传统AI服务
from app.services.domain.placeholder.hybrid_placeholder_manager import create_hybrid_placeholder_manager

def process_template(db: Session, template_id: str, data_source_id: str):
    manager = create_hybrid_placeholder_manager(db)
    result = manager.parse_and_store_placeholders(template_id, template_content, False)
    return result
        """)
        
        print("新代码:")
        print("""
# 使用IAOP平台处理模板
from app.services.iaop.integration import process_template_with_iaop

def process_template(db: Session, template_id: str, data_source_id: str, user_id: str):
    result = await process_template_with_iaop(db, template_id, data_source_id, user_id)
    return result
        """)
        
        print("\n3. 任务处理迁移:")
        print("=" * 40)
        print("原代码:")
        print("""
# 传统任务执行
from app.services.application.orchestration.cached_agent_orchestrator import CachedAgentOrchestrator

def execute_task(db: Session, task_id: str, user_id: str):
    orchestrator = CachedAgentOrchestrator(db, user_id=user_id)
    result = await orchestrator._execute_phase1_analysis(template_id, data_source_id, False)
    return result
        """)
        
        print("新代码:")
        print("""
# 使用IAOP平台执行任务
from app.services.iaop.integration import process_task_with_iaop

def execute_task(db: Session, task_id: str, user_id: str):
    result = await process_task_with_iaop(db, task_id, user_id)
    return result
        """)
        
        print("\n4. 配置和控制:")
        print("=" * 40)
        print("""
# 环境变量配置
IAOP_ENABLED=true                          # 启用IAOP平台
IAOP_INTEGRATION_MODE=hybrid_primary       # 混合模式，IAOP优先
IAOP_FALLBACK_STRATEGY=traditional         # 失败时fallback到传统服务
IAOP_TIMEOUT_SECONDS=30                    # IAOP处理超时时间
IAOP_MAX_RETRIES=2                         # 最大重试次数
IAOP_ENABLE_CACHING=true                   # 启用缓存
IAOP_ENABLE_LOGGING=true                   # 启用日志
IAOP_LOG_LEVEL=INFO                        # 日志级别

# 编程方式配置
# 配置预设已移至系统配置，不再需要单独的配置类
from app.core.config import settings
# 配置通过环境变量或系统配置管理，无需手动预设
        """)
        
        print("\n5. 监控和调试:")
        print("=" * 40)
        print("""
# 检查服务状态
from app.services.iaop.integration import get_ai_service_proxy

async def check_status(db: Session):
    proxy = get_ai_service_proxy(db)
    health = await proxy.health_check()
    metrics = proxy.get_service_metrics()
    return {"health": health, "metrics": metrics}

# 切换服务模式
proxy.switch_to_iaop()        # 切换到IAOP模式
proxy.switch_to_traditional() # 切换到传统模式
        """)
        
        print("\n6. API端点迁移:")
        print("=" * 40)
        print("""
# 现有的API端点无需修改，只需要更新服务注入
# 例如在 app/api/endpoints/tasks.py 中:

# 原来:
# # 避免循环导入，直接引用本地类
from .ai_service_adapter import IAOPAIService as EnhancedAIService
# ai_service = EnhancedAIService(db)

# 现在:
from app.services.iaop.integration import get_integrated_ai_service
ai_service = get_integrated_ai_service(db)

# 其余代码保持不变，接口完全兼容
        """)
        
        print("\n=" * 60)
        print("迁移完成！IAOP平台已成功集成到现有系统中。")
        print("=" * 60)
    
    @staticmethod
    def create_migration_checklist() -> Dict[str, Any]:
        """创建迁移检查清单"""
        return {
            "pre_migration": {
                "backup_created": False,
                "iaop_config_reviewed": False,
                "dependencies_checked": False,
                "test_environment_prepared": False
            },
            "migration_steps": {
                "ai_service_calls_updated": False,
                "template_processing_migrated": False,
                "task_execution_migrated": False,
                "api_endpoints_updated": False,
                "configuration_applied": False
            },
            "post_migration": {
                "health_check_passed": False,
                "performance_tested": False,
                "fallback_tested": False,
                "monitoring_configured": False,
                "documentation_updated": False
            },
            "rollback_plan": {
                "traditional_service_available": True,
                "rollback_procedure_documented": False,
                "rollback_tested": False
            }
        }
    
    @staticmethod
    def validate_migration(db: Session) -> Dict[str, Any]:
        """验证迁移状态"""
        from ..integration import get_ai_service_proxy
        
        results = {
            "migration_status": "unknown",
            "iaop_available": False,
            "traditional_available": False,
            "performance_comparison": {},
            "recommendations": []
        }
        
        try:
            # 测试IAOP服务
            proxy = get_ai_service_proxy(db, use_iaop=True)
            iaop_health = await proxy._get_iaop_service().health_check()
            results["iaop_available"] = iaop_health.get("status") == "healthy"
            
            # 测试传统服务
            traditional_health = await proxy._get_traditional_service().health_check()
            results["traditional_available"] = traditional_health.get("status") == "healthy"
            
            # 确定迁移状态
            if results["iaop_available"] and results["traditional_available"]:
                results["migration_status"] = "hybrid_ready"
                results["recommendations"].append("两个服务都可用，可以安全使用混合模式")
            elif results["iaop_available"]:
                results["migration_status"] = "iaop_only"
                results["recommendations"].append("仅IAOP可用，建议检查传统服务配置")
            elif results["traditional_available"]:
                results["migration_status"] = "traditional_only"
                results["recommendations"].append("仅传统服务可用，建议检查IAOP配置")
            else:
                results["migration_status"] = "error"
                results["recommendations"].append("所有服务都不可用，需要检查系统配置")
            
        except Exception as e:
            results["migration_status"] = "error"
            results["error"] = str(e)
            results["recommendations"].append(f"迁移验证失败: {e}")
        
        return results
    
    @staticmethod
    def performance_comparison_test(db: Session, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """性能对比测试"""
        import time
        from ..integration import get_ai_service_proxy
        
        results = {
            "iaop_performance": {},
            "traditional_performance": {}, 
            "comparison": {}
        }
        
        try:
            proxy = get_ai_service_proxy(db)
            
            # 测试IAOP性能
            proxy.switch_to_iaop()
            start_time = time.time()
            iaop_result = await proxy.analyze_placeholder_requirements(
                test_data.get("placeholder_data", {}),
                test_data.get("data_source_id", "test")
            )
            iaop_time = time.time() - start_time
            
            results["iaop_performance"] = {
                "execution_time": iaop_time,
                "success": iaop_result.get("success", False),
                "processing_method": iaop_result.get("processing_method", "unknown")
            }
            
            # 测试传统服务性能
            proxy.switch_to_traditional()
            start_time = time.time()
            traditional_result = await proxy.analyze_placeholder_requirements(
                test_data.get("placeholder_data", {}),
                test_data.get("data_source_id", "test")
            )
            traditional_time = time.time() - start_time
            
            results["traditional_performance"] = {
                "execution_time": traditional_time,
                "success": traditional_result.get("success", False),
                "processing_method": traditional_result.get("processing_method", "unknown")
            }
            
            # 性能对比
            if iaop_time > 0 and traditional_time > 0:
                speed_ratio = traditional_time / iaop_time
                if speed_ratio > 1.1:
                    results["comparison"]["winner"] = "iaop"
                    results["comparison"]["improvement"] = f"IAOP比传统服务快 {(speed_ratio-1)*100:.1f}%"
                elif speed_ratio < 0.9:
                    results["comparison"]["winner"] = "traditional"
                    results["comparison"]["improvement"] = f"传统服务比IAOP快 {(1/speed_ratio-1)*100:.1f}%"
                else:
                    results["comparison"]["winner"] = "tie"
                    results["comparison"]["improvement"] = "性能相近"
            
        except Exception as e:
            results["error"] = str(e)
        
        return results


def run_migration_guide():
    """运行迁移指南"""
    guide = IAOPMigrationGuide()
    
    print("开始IAOP迁移指南...")
    guide.show_migration_examples()
    
    checklist = guide.create_migration_checklist()
    print(f"\n迁移检查清单已创建，包含 {len(checklist)} 个主要类别")
    
    print("\n迁移指南运行完成！")
    print("请根据上述示例更新您的代码，并使用环境变量控制IAOP集成行为。")


if __name__ == "__main__":
    run_migration_guide()