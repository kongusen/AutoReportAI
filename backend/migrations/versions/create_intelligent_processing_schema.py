"""Create intelligent processing schema

Revision ID: create_intelligent_processing_schema
Revises: af5d17599002
Create Date: 2024-01-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_intelligent_processing_schema'
down_revision = 'af5d17599002'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types if they don't exist
    connection = op.get_bind()
    
    # Check and create error category enum
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_type WHERE typname = 'errorcategoryenum'
        )
    """)).scalar()
    
    if not result:
        connection.execute(sa.text("""
            CREATE TYPE errorcategoryenum AS ENUM (
                'parsing_error', 'llm_error', 'field_matching_error', 'etl_error',
                'content_generation_error', 'validation_error', 'system_error'
            )
        """))
    
    # Check and create error severity enum
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_type WHERE typname = 'errorseverityenum'
        )
    """)).scalar()
    
    if not result:
        connection.execute(sa.text("""
            CREATE TYPE errorseverityenum AS ENUM (
                'low', 'medium', 'high', 'critical'
            )
        """))
    
    # Check and create feedback type enum
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_type WHERE typname = 'feedbacktypeenum'
        )
    """)).scalar()
    
    if not result:
        connection.execute(sa.text("""
            CREATE TYPE feedbacktypeenum AS ENUM (
                'correction', 'improvement', 'validation', 'complaint'
            )
        """))
    
    # Create placeholder_processing_history table if it doesn't exist
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'placeholder_processing_history'
        )
    """)).scalar()
    
    if not result:
        op.create_table('placeholder_processing_history',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('placeholder_text', sa.String(length=500), nullable=False),
            sa.Column('placeholder_type', sa.String(length=50), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('context_info', sa.JSON(), nullable=True),
            sa.Column('llm_understanding', sa.JSON(), nullable=True),
            sa.Column('field_mapping', sa.JSON(), nullable=True),
            sa.Column('processed_value', sa.Text(), nullable=True),
            sa.Column('processing_time_ms', sa.Integer(), nullable=True),
            sa.Column('confidence_score', sa.DECIMAL(precision=3, scale=2), nullable=True),
            sa.Column('success', sa.Boolean(), nullable=False, default=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('session_id', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_placeholder_processing_history_id'), 'placeholder_processing_history', ['id'], unique=False)
    
    # Create error_logs table if it doesn't exist
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'error_logs'
        )
    """)).scalar()
    
    if not result:
        op.create_table('error_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('error_id', sa.String(length=32), nullable=False),
            sa.Column('category', postgresql.ENUM(name='errorcategoryenum'), nullable=False),
            sa.Column('severity', postgresql.ENUM(name='errorseverityenum'), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('placeholder_text', sa.String(length=500), nullable=True),
            sa.Column('placeholder_type', sa.String(length=50), nullable=True),
            sa.Column('placeholder_description', sa.Text(), nullable=True),
            sa.Column('context_before', sa.Text(), nullable=True),
            sa.Column('context_after', sa.Text(), nullable=True),
            sa.Column('data_source_id', sa.Integer(), nullable=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('session_id', sa.String(length=255), nullable=True),
            sa.Column('stack_trace', sa.Text(), nullable=True),
            sa.Column('additional_data', sa.JSON(), nullable=True),
            sa.Column('resolved', sa.Boolean(), nullable=False, default=False),
            sa.Column('resolution_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['data_source_id'], ['enhanced_data_sources.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('error_id')
        )
        op.create_index(op.f('ix_error_logs_error_id'), 'error_logs', ['error_id'], unique=False)
        op.create_index(op.f('ix_error_logs_id'), 'error_logs', ['id'], unique=False)
    
    # Create user_feedbacks table if it doesn't exist
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'user_feedbacks'
        )
    """)).scalar()
    
    if not result:
        op.create_table('user_feedbacks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('feedback_id', sa.String(length=32), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('error_id', sa.String(length=32), nullable=True),
            sa.Column('feedback_type', postgresql.ENUM(name='feedbacktypeenum'), nullable=False),
            sa.Column('placeholder_text', sa.String(length=500), nullable=False),
            sa.Column('original_result', sa.Text(), nullable=False),
            sa.Column('corrected_result', sa.Text(), nullable=True),
            sa.Column('suggested_field', sa.String(length=255), nullable=True),
            sa.Column('confidence_rating', sa.Integer(), nullable=True),
            sa.Column('comments', sa.Text(), nullable=True),
            sa.Column('processed', sa.Boolean(), nullable=False, default=False),
            sa.Column('processing_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['error_id'], ['error_logs.error_id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('feedback_id')
        )
        op.create_index(op.f('ix_user_feedbacks_feedback_id'), 'user_feedbacks', ['feedback_id'], unique=False)
        op.create_index(op.f('ix_user_feedbacks_id'), 'user_feedbacks', ['id'], unique=False)
    
    # Create learning_rules table if it doesn't exist
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'learning_rules'
        )
    """)).scalar()
    
    if not result:
        op.create_table('learning_rules',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('rule_id', sa.String(length=32), nullable=False),
            sa.Column('placeholder_pattern', sa.String(length=500), nullable=False),
            sa.Column('field_mapping', sa.String(length=255), nullable=False),
            sa.Column('confidence_score', sa.DECIMAL(precision=3, scale=2), nullable=False),
            sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
            sa.Column('success_count', sa.Integer(), nullable=False, default=0),
            sa.Column('success_rate', sa.DECIMAL(precision=3, scale=2), nullable=False, default=0.0),
            sa.Column('created_from_feedback', sa.Boolean(), nullable=False, default=False),
            sa.Column('data_source_id', sa.Integer(), nullable=True),
            sa.Column('rule_metadata', sa.JSON(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, default=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['data_source_id'], ['enhanced_data_sources.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('rule_id')
        )
        op.create_index(op.f('ix_learning_rules_id'), 'learning_rules', ['id'], unique=False)
        op.create_index(op.f('ix_learning_rules_rule_id'), 'learning_rules', ['rule_id'], unique=False)
    
    # Create knowledge_base table if it doesn't exist
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'knowledge_base'
        )
    """)).scalar()
    
    if not result:
        op.create_table('knowledge_base',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('entry_id', sa.String(length=32), nullable=False),
            sa.Column('placeholder_signature', sa.String(length=255), nullable=False),
            sa.Column('successful_mappings', sa.JSON(), nullable=True),
            sa.Column('failed_mappings', sa.JSON(), nullable=True),
            sa.Column('user_corrections', sa.JSON(), nullable=True),
            sa.Column('pattern_analysis', sa.JSON(), nullable=True),
            sa.Column('confidence_metrics', sa.JSON(), nullable=True),
            sa.Column('usage_statistics', sa.JSON(), nullable=True),
            sa.Column('data_source_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['data_source_id'], ['enhanced_data_sources.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('entry_id')
        )
        op.create_index(op.f('ix_knowledge_base_entry_id'), 'knowledge_base', ['entry_id'], unique=False)
        op.create_index(op.f('ix_knowledge_base_id'), 'knowledge_base', ['id'], unique=False)
        op.create_index(op.f('ix_knowledge_base_placeholder_signature'), 'knowledge_base', ['placeholder_signature'], unique=False)
    
    # Create llm_call_logs table if it doesn't exist
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'llm_call_logs'
        )
    """)).scalar()
    
    if not result:
        op.create_table('llm_call_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('request_type', sa.String(length=50), nullable=False),
            sa.Column('prompt_template', sa.String(length=100), nullable=False),
            sa.Column('input_data', sa.JSON(), nullable=False),
            sa.Column('response_data', sa.JSON(), nullable=True),
            sa.Column('model_used', sa.String(length=100), nullable=False),
            sa.Column('tokens_used', sa.Integer(), nullable=True),
            sa.Column('processing_time_ms', sa.Integer(), nullable=True),
            sa.Column('cost_estimate', sa.DECIMAL(precision=10, scale=6), nullable=True),
            sa.Column('success', sa.Boolean(), nullable=False, default=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('session_id', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_llm_call_logs_id'), 'llm_call_logs', ['id'], unique=False)
    
    # Create field_mapping_cache table
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'field_mapping_cache'
        )
    """)).scalar()
    
    if not result:
        op.create_table('field_mapping_cache',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('placeholder_signature', sa.String(length=255), nullable=False),
            sa.Column('data_source_id', sa.Integer(), nullable=False),
            sa.Column('matched_field', sa.String(length=255), nullable=False),
            sa.Column('confidence_score', sa.DECIMAL(precision=3, scale=2), nullable=False),
            sa.Column('transformation_config', sa.JSON(), nullable=True),
            sa.Column('usage_count', sa.Integer(), nullable=False, default=1),
            sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['data_source_id'], ['enhanced_data_sources.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('placeholder_signature', 'data_source_id', name='uq_field_mapping_cache_signature_source')
        )
        op.create_index(op.f('ix_field_mapping_cache_id'), 'field_mapping_cache', ['id'], unique=False)
        op.create_index(op.f('ix_field_mapping_cache_placeholder_signature'), 'field_mapping_cache', ['placeholder_signature'], unique=False)
        op.create_index(op.f('ix_field_mapping_cache_data_source_id'), 'field_mapping_cache', ['data_source_id'], unique=False)
        op.create_index(op.f('ix_field_mapping_cache_last_used_at'), 'field_mapping_cache', ['last_used_at'], unique=False)
    
    # Create report_quality_scores table
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'report_quality_scores'
        )
    """)).scalar()
    
    if not result:
        op.create_table('report_quality_scores',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('report_id', sa.String(length=255), nullable=False),
            sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('overall_score', sa.DECIMAL(precision=3, scale=2), nullable=False),
            sa.Column('language_fluency_score', sa.DECIMAL(precision=3, scale=2), nullable=True),
            sa.Column('data_consistency_score', sa.DECIMAL(precision=3, scale=2), nullable=True),
            sa.Column('completeness_score', sa.DECIMAL(precision=3, scale=2), nullable=True),
            sa.Column('accuracy_score', sa.DECIMAL(precision=3, scale=2), nullable=True),
            sa.Column('formatting_score', sa.DECIMAL(precision=3, scale=2), nullable=True),
            sa.Column('quality_issues', sa.JSON(), nullable=True),
            sa.Column('improvement_suggestions', sa.JSON(), nullable=True),
            sa.Column('processing_time_ms', sa.Integer(), nullable=True),
            sa.Column('llm_analysis_used', sa.Boolean(), nullable=False, default=False),
            sa.Column('manual_review_required', sa.Boolean(), nullable=False, default=False),
            sa.Column('reviewer_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_report_quality_scores_id'), 'report_quality_scores', ['id'], unique=False)
        op.create_index(op.f('ix_report_quality_scores_report_id'), 'report_quality_scores', ['report_id'], unique=False)
        op.create_index(op.f('ix_report_quality_scores_template_id'), 'report_quality_scores', ['template_id'], unique=False)
        op.create_index(op.f('ix_report_quality_scores_user_id'), 'report_quality_scores', ['user_id'], unique=False)
        op.create_index(op.f('ix_report_quality_scores_overall_score'), 'report_quality_scores', ['overall_score'], unique=False)
        op.create_index(op.f('ix_report_quality_scores_created_at'), 'report_quality_scores', ['created_at'], unique=False)
    
    # Create additional performance indexes
    _create_performance_indexes(connection)


def _create_performance_indexes(connection):
    """Create performance indexes for existing tables"""
    
    # Check if tables exist before creating indexes
    tables_to_index = [
        ('placeholder_processing_history', [
            ('template_id', False),
            ('user_id', False),
            ('placeholder_type', False),
            ('success', False),
            ('created_at', False),
            ('confidence_score', False),
            (['template_id', 'success'], False),
            (['placeholder_type', 'confidence_score'], False),
            (['created_at', 'success'], False),  # 时间和状态组合索引
            (['user_id', 'created_at'], False),  # 用户和时间组合索引
        ]),
        ('error_logs', [
            ('category', False),
            ('severity', False),
            ('resolved', False),
            ('data_source_id', False),
            ('user_id', False),
            ('created_at', False),
            (['category', 'severity'], False),
            (['resolved', 'created_at'], False),  # 解决状态和时间组合索引
            (['category', 'resolved'], False),   # 分类和解决状态组合索引
        ]),
        ('user_feedbacks', [
            ('user_id', False),
            ('feedback_type', False),
            ('processed', False),
            ('created_at', False),
            (['processed', 'created_at'], False),  # 处理状态和时间组合索引
        ]),
        ('learning_rules', [
            ('data_source_id', False),
            ('active', False),
            ('success_rate', False),
            ('usage_count', False),
            ('created_at', False),
            ('last_updated', False),
            (['active', 'success_rate'], False),
            (['data_source_id', 'active'], False),  # 数据源和激活状态组合索引
            (['success_rate', 'usage_count'], False),  # 成功率和使用次数组合索引
        ]),
        ('knowledge_base', [
            ('data_source_id', False),
            ('created_at', False),
            ('last_updated', False),
            (['data_source_id', 'last_updated'], False),  # 数据源和更新时间组合索引
        ]),
        ('llm_call_logs', [
            ('request_type', False),
            ('model_used', False),
            ('success', False),
            ('user_id', False),
            ('created_at', False),
            ('processing_time_ms', False),
            ('tokens_used', False),
            (['request_type', 'success'], False),
            (['model_used', 'created_at'], False),  # 模型和时间组合索引
            (['success', 'created_at'], False),     # 成功状态和时间组合索引
            (['user_id', 'created_at'], False),     # 用户和时间组合索引
        ]),
        ('field_mapping_cache', [
            ('last_used_at', False),
            ('usage_count', False),
            (['usage_count', 'last_used_at'], False),  # 使用次数和最后使用时间组合索引
            (['data_source_id', 'usage_count'], False),  # 数据源和使用次数组合索引
        ]),
        ('report_quality_scores', [
            ('overall_score', False),
            ('created_at', False),
            ('manual_review_required', False),
            (['overall_score', 'created_at'], False),  # 评分和时间组合索引
            (['manual_review_required', 'created_at'], False),  # 审核状态和时间组合索引
        ]),
    ]
    
    for table_name, indexes in tables_to_index:
        # Check if table exists
        result = connection.execute(sa.text(f"""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = '{table_name}'
            )
        """)).scalar()
        
        if result:
            for index_info in indexes:
                if isinstance(index_info[0], list):
                    # Composite index
                    columns = index_info[0]
                    unique = index_info[1]
                    index_name = f"ix_{table_name}_{'_'.join(columns)}"
                    
                    # Check if index exists
                    index_exists = connection.execute(sa.text(f"""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_indexes 
                            WHERE indexname = '{index_name}'
                        )
                    """)).scalar()
                    
                    if not index_exists:
                        try:
                            op.create_index(index_name, table_name, columns, unique=unique)
                        except Exception as e:
                            print(f"Warning: Could not create index {index_name}: {e}")
                else:
                    # Single column index
                    column = index_info[0]
                    unique = index_info[1]
                    index_name = f"ix_{table_name}_{column}"
                    
                    # Check if index exists
                    index_exists = connection.execute(sa.text(f"""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_indexes 
                            WHERE indexname = '{index_name}'
                        )
                    """)).scalar()
                    
                    if not index_exists:
                        try:
                            op.create_index(index_name, table_name, [column], unique=unique)
                        except Exception as e:
                            print(f"Warning: Could not create index {index_name}: {e}")
    
    # Create partitioning setup for LLM call logs
    _setup_llm_logs_partitioning(connection)


def _setup_llm_logs_partitioning(connection):
    """Setup partitioning for LLM call logs table"""
    try:
        # Check if the table is already partitioned
        is_partitioned = connection.execute(sa.text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_partitioned_table 
                WHERE schemaname = 'public' AND tablename = 'llm_call_logs'
            )
        """)).scalar()
        
        if not is_partitioned:
            # Note: Converting existing table to partitioned table requires data migration
            # For now, we'll create a comment indicating partitioning strategy
            connection.execute(sa.text("""
                COMMENT ON TABLE llm_call_logs IS 
                'Partitioning strategy: Monthly partitions by created_at. 
                 Implement partitioning during low-traffic periods.
                 Partition naming: llm_call_logs_YYYY_MM'
            """))
            
            # Create a function to help with future partitioning
            connection.execute(sa.text("""
                CREATE OR REPLACE FUNCTION create_llm_logs_partition(
                    partition_date DATE
                ) RETURNS TEXT AS $$$
                DECLARE
                    partition_name TEXT;
                    start_date DATE;
                    end_date DATE;
                BEGIN
                    -- Calculate partition boundaries
                    start_date := DATE_TRUNC('month', partition_date);
                    end_date := start_date + INTERVAL '1 month';
                    
                    -- Generate partition name
                    partition_name := 'llm_call_logs_' || TO_CHAR(start_date, 'YYYY_MM');
                    
                    -- Create partition table (when main table is partitioned)
                    -- This is a placeholder for future implementation
                    
                    RETURN partition_name;
                END;
                $$ LANGUAGE plpgsql;
            """))
            
            print("LLM call logs partitioning strategy documented. Manual partitioning setup required.")
        
    except Exception as e:
        print(f"Warning: Could not setup LLM logs partitioning: {e}")


def downgrade():
    # Drop tables in reverse order
    op.drop_table('report_quality_scores')
    op.drop_table('field_mapping_cache')
    op.drop_table('llm_call_logs')
    op.drop_table('knowledge_base')
    op.drop_table('learning_rules')
    op.drop_table('user_feedbacks')
    op.drop_table('error_logs')
    op.drop_table('placeholder_processing_history')
    
    # Drop enum types
    connection = op.get_bind()
    connection.execute(sa.text("DROP TYPE IF EXISTS feedbacktypeenum"))
    connection.execute(sa.text("DROP TYPE IF EXISTS errorseverityenum"))
    connection.execute(sa.text("DROP TYPE IF EXISTS errorcategoryenum"))