"""
数据库性能索引优化
添加关键查询字段的索引以提高查询性能
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime

# 添加数据库索引以优化查询性能
def add_performance_indexes():
    """添加性能优化索引"""
    
    # 1. Tasks表索引优化
    print("Adding indexes for tasks table...")
    
    # 用户相关查询索引
    op.create_index('idx_tasks_owner_id_created_at', 'tasks', ['owner_id', 'created_at'])
    op.create_index('idx_tasks_owner_id_status', 'tasks', ['owner_id', 'status'])
    op.create_index('idx_tasks_owner_id_active', 'tasks', ['owner_id', 'is_active'])
    
    # 状态和时间索引
    op.create_index('idx_tasks_status_updated_at', 'tasks', ['status', 'updated_at'])
    op.create_index('idx_tasks_active_status', 'tasks', ['is_active', 'status'])
    
    # 外键复合索引
    op.create_index('idx_tasks_template_id_active', 'tasks', ['template_id', 'is_active'])
    op.create_index('idx_tasks_data_source_id_active', 'tasks', ['data_source_id', 'is_active'])
    
    # 2. ReportHistory表索引优化
    print("Adding indexes for report_history table...")
    
    # 任务相关查询索引
    op.create_index('idx_report_history_task_id_generated_at', 'report_history', ['task_id', 'generated_at'])
    op.create_index('idx_report_history_task_id_status', 'report_history', ['task_id', 'status'])
    
    # 时间范围查询索引
    op.create_index('idx_report_history_generated_at_status', 'report_history', ['generated_at', 'status'])
    
    # 3. DataSources表索引优化  
    print("Adding indexes for data_sources table...")
    
    # 用户数据源查询索引
    op.create_index('idx_data_sources_user_id_active', 'data_sources', ['user_id', 'is_active'])
    op.create_index('idx_data_sources_user_id_created_at', 'data_sources', ['user_id', 'created_at'])
    
    # 数据源类型查询索引
    op.create_index('idx_data_sources_source_type_active', 'data_sources', ['source_type', 'is_active'])
    
    # 4. Templates表索引优化
    print("Adding indexes for templates table...")
    
    # 用户模板查询索引
    op.create_index('idx_templates_user_id_active', 'templates', ['user_id', 'is_active'])
    op.create_index('idx_templates_user_id_public', 'templates', ['user_id', 'is_public'])
    
    # 公共模板查询索引
    op.create_index('idx_templates_public_active', 'templates', ['is_public', 'is_active'])
    
    # 5. TaskExecution表索引优化
    print("Adding indexes for task_executions table...")
    
    # 任务执行查询索引
    op.create_index('idx_task_executions_task_id_created_at', 'task_executions', ['task_id', 'created_at'])
    op.create_index('idx_task_executions_status_created_at', 'task_executions', ['execution_status', 'created_at'])
    
    # 执行时间范围查询索引
    op.create_index('idx_task_executions_started_completed', 'task_executions', ['started_at', 'completed_at'])
    
    # 6. Users表索引优化（如果需要）
    print("Adding indexes for users table...")
    
    # 用户状态查询索引
    op.create_index('idx_users_active_created_at', 'users', ['is_active', 'created_at'])
    
    # 7. ETLJobs表索引优化
    print("Adding indexes for etl_jobs table...")
    
    # 数据源相关查询索引  
    op.create_index('idx_etl_jobs_data_source_id_active', 'etl_jobs', ['data_source_id', 'is_active'])
    op.create_index('idx_etl_jobs_data_source_id_created_at', 'etl_jobs', ['data_source_id', 'created_at'])
    
    # 状态查询索引
    op.create_index('idx_etl_jobs_status_updated_at', 'etl_jobs', ['status', 'updated_at'])
    
    # 8. LLM相关表索引优化
    print("Adding indexes for llm tables...")
    
    # LLM服务器索引
    op.create_index('idx_llm_servers_active_created_at', 'llm_servers', ['is_active', 'created_at'])
    
    # LLM模型索引
    op.create_index('idx_llm_models_server_id_active', 'llm_models', ['server_id', 'is_active'])
    op.create_index('idx_llm_models_model_type_active', 'llm_models', ['model_type', 'is_active'])
    
    print("All performance indexes have been added successfully!")

def remove_performance_indexes():
    """移除性能索引（用于回滚）"""
    
    print("Removing performance indexes...")
    
    # 移除所有创建的索引
    indexes_to_remove = [
        'idx_tasks_owner_id_created_at',
        'idx_tasks_owner_id_status', 
        'idx_tasks_owner_id_active',
        'idx_tasks_status_updated_at',
        'idx_tasks_active_status',
        'idx_tasks_template_id_active',
        'idx_tasks_data_source_id_active',
        'idx_report_history_task_id_generated_at',
        'idx_report_history_task_id_status',
        'idx_report_history_generated_at_status',
        'idx_data_sources_user_id_active',
        'idx_data_sources_user_id_created_at',
        'idx_data_sources_source_type_active',
        'idx_templates_user_id_active',
        'idx_templates_user_id_public',
        'idx_templates_public_active',
        'idx_task_executions_task_id_created_at',
        'idx_task_executions_status_created_at',
        'idx_task_executions_started_completed',
        'idx_users_active_created_at',
        'idx_etl_jobs_data_source_id_active',
        'idx_etl_jobs_data_source_id_created_at',
        'idx_etl_jobs_status_updated_at',
        'idx_llm_servers_active_created_at',
        'idx_llm_models_server_id_active',
        'idx_llm_models_model_type_active'
    ]
    
    for index_name in indexes_to_remove:
        try:
            op.drop_index(index_name)
            print(f"Dropped index: {index_name}")
        except Exception as e:
            print(f"Warning: Could not drop index {index_name}: {e}")
    
    print("Performance indexes removal completed!")

if __name__ == "__main__":
    print("Database Performance Index Optimization Script")
    print("=" * 50)
    print(f"Started at: {datetime.now()}")
    
    try:
        add_performance_indexes()
        print(f"\nCompleted at: {datetime.now()}")
        print("Database indexing optimization successful!")
    except Exception as e:
        print(f"Error during index creation: {e}")
        print("Attempting to rollback...")
        try:
            remove_performance_indexes()
        except Exception as rollback_error:
            print(f"Rollback failed: {rollback_error}")