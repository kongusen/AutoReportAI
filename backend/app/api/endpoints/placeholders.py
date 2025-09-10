"""
占位符管理API路由

基于纯DAG架构的占位符处理API
提供占位符的基础CRUD操作
"""

import logging
from typing import Any, Dict, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.api import deps
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.base import APIResponse
from app.schemas.template_placeholder import (
    TemplatePlaceholder, 
    TemplatePlaceholderCreate, 
    TemplatePlaceholderUpdate
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=APIResponse[List[TemplatePlaceholder]])
async def get_placeholders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    template_id: str = Query(None, description="按模板ID过滤"),
) -> APIResponse[List[TemplatePlaceholder]]:
    """获取占位符列表"""
    try:
        logger.info(f"获取占位符列表，参数: template_id={template_id}, skip={skip}, limit={limit}")
        logger.info(f"当前用户: {current_user.id}")
        if template_id:
            placeholders = crud.template_placeholder.get_by_template(
                db=db, template_id=template_id
            )
        else:
            placeholders = crud.template_placeholder.get_multi(
                db=db, skip=skip, limit=limit
            )
        
        return APIResponse(
            success=True,
            data=[TemplatePlaceholder.from_orm(p) for p in placeholders],
            message="获取占位符列表成功"
        )
    except Exception as e:
        logger.error(f"获取占位符列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取占位符列表失败")


@router.get("/{placeholder_id}", response_model=APIResponse[TemplatePlaceholder])
async def get_placeholder(
    placeholder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[TemplatePlaceholder]:
    """获取单个占位符详情"""
    try:
        placeholder = crud.template_placeholder.get(db=db, id=placeholder_id)
        if not placeholder:
            raise HTTPException(status_code=404, detail="占位符不存在")
        
        return APIResponse(
            success=True,
            data=TemplatePlaceholder.from_orm(placeholder),
            message="获取占位符详情成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取占位符详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取占位符详情失败")


@router.post("/", response_model=APIResponse[TemplatePlaceholder])
async def create_placeholder(
    placeholder_in: TemplatePlaceholderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[TemplatePlaceholder]:
    """创建新占位符"""
    try:
        placeholder = crud.template_placeholder.create(
            db=db, obj_in=placeholder_in
        )
        return APIResponse(
            success=True,
            data=TemplatePlaceholder.from_orm(placeholder),
            message="创建占位符成功"
        )
    except Exception as e:
        logger.error(f"创建占位符失败: {e}")
        raise HTTPException(status_code=500, detail="创建占位符失败")


@router.put("/{placeholder_id}", response_model=APIResponse[TemplatePlaceholder])
async def update_placeholder(
    placeholder_id: str,
    placeholder_in: TemplatePlaceholderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[TemplatePlaceholder]:
    """更新占位符"""
    try:
        placeholder = crud.template_placeholder.get(db=db, id=placeholder_id)
        if not placeholder:
            raise HTTPException(status_code=404, detail="占位符不存在")
        
        placeholder = crud.template_placeholder.update(
            db=db, db_obj=placeholder, obj_in=placeholder_in
        )
        return APIResponse(
            success=True,
            data=TemplatePlaceholder.from_orm(placeholder),
            message="更新占位符成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新占位符失败: {e}")
        raise HTTPException(status_code=500, detail="更新占位符失败")


@router.delete("/{placeholder_id}", response_model=APIResponse[bool])
async def delete_placeholder(
    placeholder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[bool]:
    """删除占位符"""
    try:
        placeholder = crud.template_placeholder.get(db=db, id=placeholder_id)
        if not placeholder:
            raise HTTPException(status_code=404, detail="占位符不存在")
        
        crud.template_placeholder.remove(db=db, id=placeholder_id)
        return APIResponse(
            success=True,
            data=True,
            message="删除占位符成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除占位符失败: {e}")
        raise HTTPException(status_code=500, detail="删除占位符失败")


# 批量保存占位符配置
@router.post("/batch-save", response_model=APIResponse[List[TemplatePlaceholder]])
async def batch_save_placeholders(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[List[TemplatePlaceholder]]:
    """批量保存占位符配置"""
    try:
        template_id = request.get("template_id")
        placeholders_data = request.get("placeholders", [])
        
        if not template_id:
            raise HTTPException(status_code=400, detail="缺少template_id参数")
        
        # 验证模板存在性
        from app import crud as template_crud
        template = template_crud.template.get(db=db, id=template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        saved_placeholders = []
        
        for placeholder_data in placeholders_data:
            # 检查占位符是否已存在
            placeholder_name = placeholder_data.get("placeholder_name") or placeholder_data.get("name")
            existing = crud.template_placeholder.get_by_template_and_name(
                db=db, 
                template_id=template_id, 
                name=placeholder_name
            )
            
            if existing:
                # 更新现有占位符
                placeholder_update = TemplatePlaceholderUpdate(**{
                    k: v for k, v in placeholder_data.items() 
                    if k not in ["id", "template_id", "created_at", "updated_at"]
                })
                placeholder = crud.template_placeholder.update(
                    db=db, db_obj=existing, obj_in=placeholder_update
                )
            else:
                # 创建新占位符
                placeholder_create = TemplatePlaceholderCreate(
                    template_id=template_id,
                    **{k: v for k, v in placeholder_data.items() 
                       if k not in ["id", "template_id", "created_at", "updated_at"]}
                )
                placeholder = crud.template_placeholder.create(
                    db=db, obj_in=placeholder_create
                )
            
            saved_placeholders.append(placeholder)
        
        return APIResponse(
            success=True,
            data=[TemplatePlaceholder.from_orm(p) for p in saved_placeholders],
            message=f"成功保存 {len(saved_placeholders)} 个占位符配置"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量保存占位符配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量保存失败: {str(e)}")


# 单个占位符分析和SQL生成
@router.post("/analyze-single", response_model=APIResponse[Dict[str, Any]])
async def analyze_single_placeholder(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """分析单个占位符并生成SQL"""
    try:
        placeholder_name = request.get("placeholder_name")
        placeholder_text = request.get("placeholder_text")
        template_id = request.get("template_id")
        data_source_id = request.get("data_source_id")
        template_context = request.get("template_context", "")
        
        # 新增：时间上下文支持
        cron_expression = request.get("cron_expression")  # cron表达式
        execution_time = request.get("execution_time")    # 执行时间
        task_type = request.get("task_type", "manual")    # 任务类型
        
        if not all([placeholder_name, placeholder_text, template_id]):
            raise HTTPException(
                status_code=400, 
                detail="缺少必需参数: placeholder_name, placeholder_text, template_id"
            )
        
        # 获取数据源信息
        data_source_info = {}
        if data_source_id:
            from app.crud import data_source as crud_data_source
            data_source = crud_data_source.get(db, id=data_source_id)
            if data_source:
                data_source_info = {
                    "type": data_source.source_type.value if hasattr(data_source.source_type, 'value') else str(data_source.source_type),
                    "database": getattr(data_source, 'doris_database', 'unknown'),
                    "name": data_source.name
                }
        
        # 处理执行时间
        exec_time = None
        if execution_time:
            try:
                from datetime import datetime
                if isinstance(execution_time, str):
                    exec_time = datetime.fromisoformat(execution_time.replace('Z', '+00:00'))
                else:
                    exec_time = execution_time
            except Exception as e:
                logger.warning(f"解析执行时间失败: {execution_time}, 错误: {e}")
        
        # 使用ServiceOrchestrator进行单个占位符分析
        from app.services.infrastructure.ai.service_orchestrator import get_service_orchestrator
        
        # 记录分析开始
        logger.info(f"开始单个占位符分析: {placeholder_name}")
        logger.info(f"占位符格式: {placeholder_text}")
        logger.info(f"模板ID: {template_id}")
        logger.info(f"数据源信息: {data_source_info}")
        logger.info(f"任务类型: {task_type}")
        if cron_expression:
            logger.info(f"Cron表达式: {cron_expression}")
        if exec_time:
            logger.info(f"执行时间: {exec_time}")
        
        # 获取任务信息和具体参数
        task_params = request.get("task_params", {})
        
        # 获取服务编排器
        orchestrator = get_service_orchestrator()
        
        # 使用新架构进行单个占位符分析，包含时间上下文
        result = await orchestrator.analyze_single_placeholder_simple(
            user_id=str(current_user.id),
            placeholder_name=placeholder_name,
            placeholder_text=placeholder_text,
            template_id=template_id,
            template_context=template_context,
            data_source_info=data_source_info,
            task_params=task_params,
            cron_expression=cron_expression,
            execution_time=exec_time,
            task_type=task_type
        )
        
        logger.info(f"占位符 '{placeholder_name}' 分析完成，状态: {result.get('status', 'unknown')}")
        
        # 如果有错误，直接返回错误信息
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=f"分析失败: {result.get('error', {}).get('error_message', '未知错误')}")
  
        # 确保结果包含必要字段
        if "analyzed_at" not in result:
            result["analyzed_at"] = datetime.now().isoformat()
        
        # 新增：自动SQL验证和修复
        if data_source_id and result.get("status") == "success":
            generated_sql = result.get("generated_sql", {})
            sql_content = ""
            if isinstance(generated_sql, dict):
                sql_content = generated_sql.get(placeholder_name, "") or generated_sql.get("sql", "")
            elif isinstance(generated_sql, str):
                sql_content = generated_sql
            
            if sql_content and sql_content.strip():
                logger.info(f"开始自动验证和修复SQL: {placeholder_name}")
                try:
                    # 自动测试和修复SQL
                    fixed_sql, validation_result = await auto_validate_and_fix_sql(
                        sql=sql_content,
                        data_source_id=data_source_id,
                        placeholder_name=placeholder_name,
                        db=db,
                        max_attempts=3
                    )
                    
                    # 更新结果中的SQL
                    if fixed_sql != sql_content:
                        logger.info(f"SQL已自动修复: {placeholder_name}")
                        if isinstance(result["generated_sql"], dict):
                            result["generated_sql"][placeholder_name] = fixed_sql
                            result["generated_sql"]["sql"] = fixed_sql
                        else:
                            result["generated_sql"] = fixed_sql
                        
                        # 添加修复信息
                        result["auto_fixed"] = True
                        result["original_sql"] = sql_content
                        result["fix_attempts"] = validation_result.get("attempts", 1)
                        result["fix_errors"] = validation_result.get("errors", [])
                    
                    # 添加验证结果
                    result["sql_validated"] = validation_result.get("success", False)
                    result["validation_details"] = validation_result
                    
                except Exception as validation_error:
                    logger.warning(f"SQL自动验证失败，但不影响主流程: {validation_error}")
                    result["sql_validated"] = False
                    result["validation_error"] = str(validation_error)
        
        # 自动保存分析结果到数据库
        try:
            logger.info(f"开始保存占位符配置: {placeholder_name}")
            # 检查占位符是否已存在
            existing = crud.template_placeholder.get_by_template_and_name(
                db=db, 
                template_id=template_id, 
                name=placeholder_name
            )
            logger.info(f"查找现有占位符结果: {'找到' if existing else '未找到'}")
            
            # 从结果中提取必要的数据
            generated_sql = result.get("generated_sql", {})
            sql_content = ""
            if isinstance(generated_sql, dict):
                sql_content = generated_sql.get(placeholder_name, "") or generated_sql.get("sql", "")
            elif isinstance(generated_sql, str):
                sql_content = generated_sql
            
            analysis_result = result.get("analysis_result", {})
            analysis_text = ""
            if isinstance(analysis_result, dict):
                analysis_text = str(analysis_result.get("description", analysis_result.get("analysis_type", "")))
            elif isinstance(analysis_result, str):
                analysis_text = analysis_result
            
            placeholder_data = {
                "placeholder_name": placeholder_name,
                "placeholder_text": placeholder_text,
                "placeholder_type": "variable",
                "content_type": "text", 
                "generated_sql": sql_content,
                "confidence_score": result.get("confidence_score", 0.8),
                "sql_validated": result.get("sql_validated", False),
                "agent_analyzed": True,
                "is_active": True,
                "execution_order": 1,  # 修复：execution_order必须>=1
                "cache_ttl_hours": 24,
                "description": analysis_text[:500] if analysis_text else f"自动分析占位符: {placeholder_name}"
            }
            
            if existing:
                # 更新现有占位符
                placeholder_update = TemplatePlaceholderUpdate(**{
                    k: v for k, v in placeholder_data.items() 
                    if k not in ["id", "template_id", "created_at", "updated_at"]
                })
                result_obj = crud.template_placeholder.update(
                    db=db, db_obj=existing, obj_in=placeholder_update
                )
                logger.info(f"已更新占位符配置: {placeholder_name}, ID: {result_obj.id}")
            else:
                # 创建新占位符
                logger.info(f"准备创建新占位符，数据: {placeholder_data}")
                placeholder_create = TemplatePlaceholderCreate(
                    template_id=template_id,
                    **{k: v for k, v in placeholder_data.items() 
                       if k not in ["id", "template_id", "created_at", "updated_at"]}
                )
                result_obj = crud.template_placeholder.create(
                    db=db, obj_in=placeholder_create
                )
                logger.info(f"已保存新占位符配置: {placeholder_name}, ID: {result_obj.id}")
                
            # 确保数据库事务提交
            db.commit()
            logger.info(f"数据库事务已提交")
                
        except Exception as save_error:
            # 保存失败不影响主流程，只记录错误
            logger.error(f"保存占位符配置失败: {save_error}")
        
        return APIResponse(
            success=True,
            data=result,
            message=f"成功分析占位符 '{placeholder_name}' 并生成SQL"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"单个占位符分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


# SQL测试执行
@router.post("/test-sql", response_model=APIResponse[Dict[str, Any]])
async def test_placeholder_sql(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """测试占位符生成的SQL"""
    try:
        sql = request.get("sql")
        data_source_id = request.get("data_source_id")
        placeholder_name = request.get("placeholder_name", "未知占位符")
        
        if not sql:
            raise HTTPException(status_code=400, detail="缺少SQL参数")
        
        if not data_source_id:
            raise HTTPException(status_code=400, detail="缺少数据源ID")
        
        logger.info(f"开始测试占位符 '{placeholder_name}' 的SQL")
        logger.info(f"测试SQL: {sql}")
        
        # 获取数据源
        from app.crud import data_source as crud_data_source
        data_source = crud_data_source.get(db, id=data_source_id)
        if not data_source:
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        logger.info(f"使用数据源: {data_source.name} ({data_source.source_type})")
        
        # 根据数据源类型执行SQL测试
        if data_source.source_type.value == "doris" or str(data_source.source_type) == "doris":
            result = await test_sql_on_doris(data_source, sql, placeholder_name)
        else:
            # 其他数据源类型的处理
            result = {
                "success": False,
                "error": f"暂不支持 {data_source.source_type} 类型的数据源测试",
                "data": [],
                "row_count": 0,
                "execution_time_ms": 0
            }
        
        logger.info(f"SQL测试完成，结果: {result['success']}")
        
        return APIResponse(
            success=True,
            data={
                "placeholder_name": placeholder_name,
                "sql": sql,
                "test_result": result,
                "data_source_name": data_source.name,
                "tested_at": datetime.now().isoformat()
            },
            message=f"SQL测试{'成功' if result['success'] else '失败'}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SQL测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")


async def test_sql_on_doris(data_source, sql: str, placeholder_name: str) -> Dict[str, Any]:
    """在Doris数据源上测试SQL"""
    import time
    
    try:
        # 导入Doris连接器
        from app.services.data.connectors.doris_connector import DorisConnector
        
        # 创建连接器配置
        from app.services.data.connectors.doris_connector import DorisConfig
        from app.core.data_source_utils import DataSourcePasswordManager
        
        doris_config = DorisConfig(
            source_type='doris',
            name=data_source.name,
            description=f'Doris数据源: {data_source.name}',
            fe_hosts=data_source.doris_fe_hosts or ['localhost'],
            mysql_host=data_source.doris_fe_hosts[0] if data_source.doris_fe_hosts else 'localhost',
            mysql_port=data_source.doris_query_port or 9030,
            query_port=data_source.doris_query_port or 9030,
            username=data_source.doris_username or 'root',
            password=DataSourcePasswordManager.get_password(data_source.doris_password),
            database=data_source.doris_database or 'default',
            mysql_username=data_source.doris_username or 'root',
            mysql_password=DataSourcePasswordManager.get_password(data_source.doris_password),
            mysql_database=data_source.doris_database or 'default',
            http_port=data_source.doris_http_port or 8030,
            use_mysql_protocol=False  # 使用HTTP API确保稳定性
        )
        
        # 创建连接器
        connector = DorisConnector(config=doris_config)
        
        start_time = time.time()
        
        # 检查SQL是否包含占位符
        if '{{' in sql and '}}' in sql:
            logger.warning(f"SQL包含未替换的占位符，无法直接测试: {sql[:100]}...")
            return {
                "success": False,
                "error": "SQL包含占位符，无法直接测试。请先提供具体的参数值。",
                "data": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "placeholders_found": True
            }
        
        # 执行SQL（对于某些查询添加LIMIT限制）
        sql_upper = sql.strip().upper()
        if (sql_upper.startswith('SELECT') and 
            'LIMIT' not in sql_upper and 
            not sql_upper.startswith('SELECT * FROM (') and
            'SHOW' not in sql_upper and
            'DESCRIBE' not in sql_upper and 
            'DESC' not in sql_upper):
            # 只对普通SELECT查询且没有LIMIT的查询添加限制
            # 移除原始SQL末尾的分号，避免子查询语法错误
            clean_sql = sql.strip().rstrip(';')
            limited_sql = f"SELECT * FROM ({clean_sql}) AS subquery LIMIT 10"
        else:
            # 对于SHOW TABLES、DESCRIBE等命令，直接执行
            limited_sql = sql.strip()
        
        # 执行查询并确保资源正确清理
        try:
            result = await connector.execute_query(limited_sql)
        finally:
            # 确保连接器资源被正确清理
            if hasattr(connector, 'close'):
                await connector.close()
        
        execution_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        # result 是 DorisQueryResult 对象，需要转换为字典
        if hasattr(result, 'to_dict'):
            result_dict = result.to_dict()
        else:
            result_dict = result
        
        if result_dict.get("success", True) and hasattr(result, 'data') and not result.data.empty:
            return {
                "success": True,
                "data": result_dict.get("data", [])[:10],  # 限制显示前10行
                "columns": result_dict.get("columns", []),
                "row_count": result_dict.get("row_count", 0),
                "execution_time_ms": round(execution_time, 2),
                "message": "SQL执行成功"
            }
        else:
            error_msg = result_dict.get("error_message") if hasattr(result, 'error_message') else "查询返回空结果或执行失败"
            return {
                "success": False,
                "error": error_msg,
                "data": [],
                "row_count": 0,
                "execution_time_ms": round(execution_time, 2)
            }
            
    except Exception as e:
        logger.error(f"Doris SQL测试异常: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "row_count": 0,
            "execution_time_ms": 0
        }


# 批量验证和修复占位符
@router.post("/batch-validate", response_model=APIResponse[Dict[str, Any]])
async def batch_validate_placeholders(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """批量验证和修复模板占位符"""
    try:
        template_id = request.get("template_id")
        data_source_id = request.get("data_source_id") 
        time_context = request.get("time_context")
        force_repair = request.get("force_repair", False)
        
        if not template_id:
            raise HTTPException(status_code=400, detail="缺少template_id参数")
        
        if not data_source_id:
            raise HTTPException(status_code=400, detail="缺少data_source_id参数")
        
        logger.info(f"开始批量验证占位符: template_id={template_id}, force_repair={force_repair}")
        
        # 获取数据源信息
        from app.crud import data_source as crud_data_source
        data_source = crud_data_source.get(db, id=data_source_id)
        if not data_source:
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        data_source_info = {
            "type": data_source.source_type.value if hasattr(data_source.source_type, 'value') else str(data_source.source_type),
            "name": data_source.name,
            "database": getattr(data_source, 'doris_database', 'unknown'),
            "fe_hosts": getattr(data_source, 'doris_fe_hosts', ['localhost']),
            "username": getattr(data_source, 'doris_username', 'root'),
            "password": getattr(data_source, 'doris_password', ''),
            "query_port": getattr(data_source, 'doris_query_port', 9030)
        }
        
        # 创建占位符验证服务
        from app.services.domain.placeholder.placeholder_validation_service import (
            create_placeholder_validation_service
        )
        validation_service = create_placeholder_validation_service(str(current_user.id))
        
        # 执行批量验证和修复
        result = await validation_service.batch_repair_template_placeholders(
            template_id=template_id,
            data_source_info=data_source_info,
            time_context=time_context,
            force_repair=force_repair
        )
        
        return APIResponse(
            success=result["status"] != "error",
            data=result,
            message=result.get("message", "批量验证完成")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量验证占位符失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量验证失败: {str(e)}")


# 获取占位符修复状态
@router.get("/repair-status/{template_id}", response_model=APIResponse[Dict[str, Any]])
async def get_placeholder_repair_status(
    template_id: str,
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """获取模板占位符修复状态"""
    try:
        from app.services.domain.placeholder.placeholder_validation_service import (
            create_placeholder_validation_service
        )
        
        validation_service = create_placeholder_validation_service(str(current_user.id))
        status_info = await validation_service.get_placeholder_repair_status(template_id)
        
        return APIResponse(
            success=True,
            data=status_info,
            message="获取修复状态成功"
        )
        
    except Exception as e:
        logger.error(f"获取占位符修复状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取修复状态失败: {str(e)}")


# 生成报告任务
@router.post("/generate-report", response_model=APIResponse[Dict[str, Any]])
async def generate_report_task(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """启动完整的报告生成任务"""
    try:
        template_id = request.get("template_id")
        data_source_ids = request.get("data_source_ids", [])
        execution_context = request.get("execution_context", {})
        time_context = request.get("time_context")
        output_format = request.get("output_format", "docx")
        delivery_config = request.get("delivery_config")
        
        if not template_id:
            raise HTTPException(status_code=400, detail="缺少template_id参数")
        
        if not data_source_ids:
            raise HTTPException(status_code=400, detail="缺少data_source_ids参数")
        
        logger.info(f"启动报告生成任务: template_id={template_id}")
        
        # 创建任务执行服务
        from app.services.application.tasks.task_execution_service import (
            create_task_execution_service, TaskExecutionRequest
        )
        
        task_service = create_task_execution_service(str(current_user.id))
        
        # 生成任务ID
        import uuid
        task_id = f"report_{uuid.uuid4().hex[:8]}"
        
        # 构建任务执行请求
        execution_request = TaskExecutionRequest(
            task_id=task_id,
            template_id=template_id,
            data_source_ids=data_source_ids,
            user_id=str(current_user.id),
            execution_context=execution_context,
            time_context=time_context,
            output_format=output_format,
            delivery_config=delivery_config
        )
        
        # 异步执行任务
        import asyncio
        task_future = asyncio.create_task(task_service.execute_task(execution_request))
        
        return APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "status": "started",
                "message": "报告生成任务已启动",
                "template_id": template_id,
                "data_source_ids": data_source_ids,
                "started_at": datetime.now().isoformat()
            },
            message="报告生成任务已启动，正在后台执行"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动报告生成任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动任务失败: {str(e)}")


# 检查任务状态
@router.get("/task-status/{task_id}", response_model=APIResponse[Dict[str, Any]])
async def get_report_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """获取报告生成任务状态"""
    try:
        from app.services.application.tasks.task_execution_service import create_task_execution_service
        
        task_service = create_task_execution_service(str(current_user.id))
        task_status = task_service.get_task_status(task_id)
        
        if task_status is None:
            return APIResponse(
                success=True,
                data={"task_id": task_id, "status": "completed_or_not_found"},
                message="任务不存在或已完成"
            )
        
        # 格式化状态
        formatted_status = {
            "task_id": task_id,
            "status": task_status["status"].value if hasattr(task_status["status"], "value") else str(task_status["status"]),
            "current_step": task_status.get("current_step", ""),
            "progress": task_status.get("progress", 0.0),
            "start_time": task_status.get("start_time", datetime.now()).isoformat(),
            "updated_at": task_status.get("updated_at", datetime.now()).isoformat() if task_status.get("updated_at") else None,
            "error": task_status.get("error")
        }
        
        return APIResponse(
            success=True,
            data=formatted_status,
            message="获取任务状态成功"
        )
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


# 取消任务
@router.post("/cancel-task/{task_id}", response_model=APIResponse[bool])
async def cancel_report_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> APIResponse[bool]:
    """取消报告生成任务"""
    try:
        from app.services.application.tasks.task_execution_service import create_task_execution_service
        
        task_service = create_task_execution_service(str(current_user.id))
        success = await task_service.cancel_task(task_id)
        
        return APIResponse(
            success=success,
            data=success,
            message="任务已取消" if success else "任务未找到或无法取消"
        )
        
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


async def auto_validate_and_fix_sql(
    sql: str,
    data_source_id: str,
    placeholder_name: str,
    db: Session,
    max_attempts: int = 3
) -> tuple[str, dict]:
    """
    自动验证和修复SQL
    
    Args:
        sql: 待验证的SQL
        data_source_id: 数据源ID
        placeholder_name: 占位符名称
        db: 数据库会话
        max_attempts: 最大修复尝试次数
        
    Returns:
        tuple: (修复后的SQL, 验证结果详情)
    """
    from app.crud import data_source as crud_data_source
    
    logger.info(f"开始自动验证SQL: {placeholder_name}")
    current_sql = sql
    attempts = 0
    errors_encountered = []
    
    # 获取数据源
    data_source = crud_data_source.get(db, id=data_source_id)
    if not data_source:
        return sql, {"success": False, "error": "数据源不存在", "attempts": 0}
    
    for attempt in range(max_attempts):
        attempts += 1
        logger.info(f"SQL验证尝试 {attempt + 1}/{max_attempts}: {placeholder_name}")
        
        # 测试当前SQL
        try:
            test_result = await test_sql_with_data_source(
                sql=current_sql,
                data_source=data_source,
                placeholder_name=placeholder_name
            )
            
            if test_result.get("success", False):
                logger.info(f"SQL验证成功: {placeholder_name} (尝试 {attempts})")
                return current_sql, {
                    "success": True,
                    "attempts": attempts,
                    "errors": errors_encountered,
                    "final_result": test_result
                }
            else:
                error_message = test_result.get("error", "未知错误")
                errors_encountered.append({
                    "attempt": attempt + 1,
                    "sql": current_sql,
                    "error": error_message
                })
                logger.warning(f"SQL验证失败 (尝试 {attempt + 1}): {error_message}")
                
                # 尝试修复SQL
                if attempt < max_attempts - 1:  # 不是最后一次尝试
                    fixed_sql = apply_sql_fixes(current_sql, error_message, data_source)
                    if fixed_sql != current_sql:
                        logger.info(f"尝试修复SQL: {placeholder_name}")
                        current_sql = fixed_sql
                    else:
                        logger.warning(f"无法修复SQL错误: {error_message}")
                        break
                        
        except Exception as e:
            error_message = str(e)
            errors_encountered.append({
                "attempt": attempt + 1,
                "sql": current_sql,
                "error": error_message
            })
            logger.error(f"SQL测试异常 (尝试 {attempt + 1}): {error_message}")
            
            if attempt < max_attempts - 1:
                fixed_sql = apply_sql_fixes(current_sql, error_message, data_source)
                if fixed_sql != current_sql:
                    current_sql = fixed_sql
                else:
                    break
    
    logger.warning(f"SQL验证失败，已尝试 {attempts} 次: {placeholder_name}")
    return current_sql, {
        "success": False,
        "attempts": attempts,
        "errors": errors_encountered,
        "final_sql": current_sql
    }


async def test_sql_with_data_source(sql: str, data_source, placeholder_name: str) -> dict:
    """使用数据源连接测试SQL"""
    try:
        if data_source.source_type.value == "doris" or str(data_source.source_type) == "doris":
            return await test_sql_on_doris(data_source, sql, placeholder_name)
        else:
            return {
                "success": False,
                "error": f"暂不支持 {data_source.source_type} 类型的数据源自动验证",
                "data": [],
                "row_count": 0,
                "execution_time_ms": 0
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"SQL测试异常: {str(e)}",
            "data": [],
            "row_count": 0,
            "execution_time_ms": 0
        }


def apply_sql_fixes(sql: str, error_message: str, data_source) -> str:
    """
    根据错误信息自动修复SQL
    
    Args:
        sql: 原始SQL
        error_message: 错误信息
        data_source: 数据源对象
        
    Returns:
        修复后的SQL
    """
    fixed_sql = sql
    error_lower = error_message.lower()
    
    # 1. 语法错误修复
    if "syntax error" in error_lower or "encountered: ;" in error_lower:
        # 移除子查询中的分号
        if ";) as subquery" in fixed_sql.lower():
            fixed_sql = fixed_sql.replace(";)", ")")
            logger.info("修复: 移除子查询中的分号")
    
    # 2. 表不存在错误
    if "table" in error_lower and ("not exist" in error_lower or "doesn't exist" in error_lower):
        # 尝试添加数据库前缀
        if hasattr(data_source, 'doris_database') and data_source.doris_database:
            database_name = data_source.doris_database
            # 查找没有数据库前缀的表名
            import re
            table_pattern = r'\b(?:FROM|JOIN|UPDATE|INTO)\s+([a-zA-Z_]\w*)\b'
            matches = re.finditer(table_pattern, fixed_sql, re.IGNORECASE)
            for match in matches:
                table_name = match.group(1)
                if '.' not in table_name:  # 没有数据库前缀
                    qualified_table = f"{database_name}.{table_name}"
                    fixed_sql = fixed_sql.replace(table_name, qualified_table, 1)
                    logger.info(f"修复: 添加数据库前缀 {table_name} -> {qualified_table}")
    
    # 3. 列不存在错误
    if "column" in error_lower and ("not exist" in error_lower or "unknown column" in error_lower):
        # 尝试一些常见的列名映射
        column_mappings = {
            "created_at": ["create_time", "created_time", "create_date", "creation_date"],
            "updated_at": ["update_time", "updated_time", "update_date", "modification_date"],
            "id": ["pk_id", "primary_id", "row_id"],
        }
        
        for original, alternatives in column_mappings.items():
            if original in fixed_sql:
                for alternative in alternatives:
                    # 这里应该实际查询数据源来验证列是否存在，暂时使用第一个替代
                    fixed_sql = fixed_sql.replace(original, alternative, 1)
                    logger.info(f"修复: 列名映射 {original} -> {alternative}")
                    break
    
    # 4. 数据类型错误
    if "type" in error_lower and ("mismatch" in error_lower or "conversion" in error_lower):
        # 添加类型转换
        import re
        # 查找日期比较
        date_pattern = r"(\w+)\s*([><=]+)\s*'(\d{4}-\d{2}-\d{2}[^']*?)'"
        matches = re.finditer(date_pattern, fixed_sql)
        for match in matches:
            column_name, operator, date_value = match.groups()
            # 为日期列添加类型转换
            new_comparison = f"DATE({column_name}) {operator} '{date_value}'"
            fixed_sql = fixed_sql.replace(match.group(0), new_comparison, 1)
            logger.info(f"修复: 添加日期类型转换 {match.group(0)} -> {new_comparison}")
    
    # 5. 权限错误 - 尝试使用更简单的查询
    if "access denied" in error_lower or "permission" in error_lower:
        # 简化查询，移除可能需要特殊权限的功能
        if "information_schema" not in fixed_sql.lower():
            # 如果是复杂查询，尝试简化为基本的SELECT
            if fixed_sql.strip().upper().startswith("SELECT"):
                # 保持基本的SELECT结构，但添加LIMIT
                if "LIMIT" not in fixed_sql.upper():
                    fixed_sql = fixed_sql.rstrip(';') + " LIMIT 1"
                    logger.info("修复: 添加LIMIT以简化查询")
    
    # 6. 连接错误 - 调整超时和重试
    if "timeout" in error_lower or "connection" in error_lower:
        # 这种错误通常需要在连接器层面处理，SQL层面能做的有限
        # 可以尝试简化查询
        if "ORDER BY" in fixed_sql:
            fixed_sql = re.sub(r'\s+ORDER BY[^;]*', '', fixed_sql, flags=re.IGNORECASE)
            logger.info("修复: 移除ORDER BY以简化查询")
    
    return fixed_sql
