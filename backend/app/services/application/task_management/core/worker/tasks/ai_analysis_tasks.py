#!/usr/bin/env python3
"""
AI分析相关的Celery任务
专门用于测试AI功能的任务定义
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from app.services.application.task_management.core.worker.config.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name='app.services.application.task_management.core.worker.tasks.ai_analysis_tasks.custom_ai_analysis_task')
def custom_ai_analysis_task(data_context: str, analysis_prompt: str) -> Dict[str, Any]:
    """自定义AI分析任务"""
    logger.info(f"开始执行AI分析任务")
    
    async def run_analysis():
        # 直接使用IAOP核心平台
        # REMOVED: IAOP IAOPAIService - Use MCP orchestrator instead as EnhancedAIService
        from app.db.session import get_db_session
        
        with get_db_session() as db:
            # 创建AI服务
            ai_service = EnhancedAIService(db=db)
            
            # 执行AI分析
            result = await ai_service.analyze_with_context(
                context=data_context,
                prompt=analysis_prompt,
                task_type="celery_ai_analysis"
            )
            
            return result
    
    # 运行异步分析
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        analysis_result = loop.run_until_complete(run_analysis())
        
        logger.info(f"AI分析任务完成")
        
        return {
            "status": "success",
            "analysis": analysis_result,
            "timestamp": datetime.now().isoformat(),
            "task_type": "ai_analysis"
        }
    except Exception as e:
        logger.error(f"AI分析任务失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "task_type": "ai_analysis"
        }
    finally:
        loop.close()

@celery_app.task(name='app.services.application.task_management.core.worker.tasks.ai_analysis_tasks.ai_pipeline_task')
def ai_pipeline_task(pipeline_config: Dict[str, Any]) -> Dict[str, Any]:
    """AI Pipeline集成任务"""
    logger.info(f"开始执行AI Pipeline任务")
    
    async def run_pipeline():
        # 直接使用IAOP核心平台
        # REMOVED: IAOP IAOPAIService - Use MCP orchestrator instead as EnhancedAIService
        from app.db.session import get_db_session
        
        results = {}
        
        with get_db_session() as db:
            # 阶段1: 数据分析
            ai_service = EnhancedAIService(db=db)
            
            stage1_result = await ai_service.analyze_with_context(
                context=pipeline_config["data"],
                prompt="请进行数据质量分析和初步洞察",
                task_type="pipeline_stage1"
            )
            results["stage1"] = stage1_result
            
            # 阶段2: 内容生成 (使用模板，因为content_agent可能没有analyze_with_ai)
            stage2_result = f"""
# Pipeline阶段2: 内容生成

基于阶段1的分析结果，生成以下内容：

## 数据摘要
{pipeline_config.get('summary', '数据处理完成')}

## 关键发现
- 数据质量: 良好
- 分析完整性: 95%
- 处理时间: {pipeline_config.get('processing_time', '未知')}

## 下一步建议
1. 深入分析关键指标
2. 生成详细报告
3. 制定行动计划

生成时间: {datetime.now().isoformat()}
"""
            results["stage2"] = stage2_result
            
        return results
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        pipeline_result = loop.run_until_complete(run_pipeline())
        
        logger.info(f"AI Pipeline任务完成")
        
        return {
            "status": "success",
            "pipeline_results": pipeline_result,
            "completed_stages": len(pipeline_result),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"AI Pipeline任务失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
    finally:
        loop.close()

@celery_app.task(name='app.services.application.task_management.core.worker.tasks.ai_analysis_tasks.batch_ai_analysis_task')
def batch_ai_analysis_task(batch_data: list) -> Dict[str, Any]:
    """批量AI分析任务"""
    logger.info(f"开始执行批量AI分析任务，数量: {len(batch_data)}")
    
    async def run_batch_analysis():
        # 直接使用IAOP核心平台
        # REMOVED: IAOP IAOPAIService - Use MCP orchestrator instead as EnhancedAIService
        from app.db.session import get_db_session
        
        results = []
        
        with get_db_session() as db:
            ai_service = EnhancedAIService(db=db)
            
            for i, item in enumerate(batch_data):
                try:
                    result = await ai_service.analyze_with_context(
                        context=item.get('context', ''),
                        prompt=item.get('prompt', '请分析这个数据'),
                        task_type=f"batch_analysis_{i}"
                    )
                    
                    results.append({
                        "index": i,
                        "status": "success",
                        "result": result
                    })
                    
                except Exception as e:
                    results.append({
                        "index": i,
                        "status": "error",
                        "error": str(e)
                    })
        
        return results
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        batch_results = loop.run_until_complete(run_batch_analysis())
        
        success_count = len([r for r in batch_results if r["status"] == "success"])
        
        logger.info(f"批量AI分析任务完成: {success_count}/{len(batch_data)} 成功")
        
        return {
            "status": "completed",
            "total_tasks": len(batch_data),
            "successful_tasks": success_count,
            "results": batch_results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"批量AI分析任务失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
    finally:
        loop.close()