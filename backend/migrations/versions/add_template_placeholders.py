"""Add template placeholders tables

Revision ID: add_template_placeholders
Revises: 
Create Date: 2024-12-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_template_placeholders'
down_revision = '6d1e4bc38b74_add_table_schema_and_relationship_models'  # 基于您已有的最新迁移
branch_labels = None
depends_on = None


def upgrade():
    # 创建模板占位符配置表
    op.create_table('template_placeholders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('placeholder_name', sa.String(length=255), nullable=False),
        sa.Column('placeholder_text', sa.String(length=500), nullable=False),
        sa.Column('placeholder_type', sa.String(length=50), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        
        # Agent分析结果存储
        sa.Column('agent_analyzed', sa.Boolean(), nullable=False, default=False),
        sa.Column('target_database', sa.String(length=100), nullable=True),
        sa.Column('target_table', sa.String(length=100), nullable=True),
        sa.Column('required_fields', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('generated_sql', sa.Text(), nullable=True),
        sa.Column('sql_validated', sa.Boolean(), nullable=False, default=False),
        
        # 执行配置
        sa.Column('execution_order', sa.Integer(), nullable=False, default=1),
        sa.Column('cache_ttl_hours', sa.Integer(), nullable=False, default=24),
        sa.Column('is_required', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        
        # Agent配置
        sa.Column('agent_workflow_id', sa.String(length=100), nullable=True),
        sa.Column('agent_config', postgresql.JSON(astext_type=sa.Text()), nullable=True, default=sa.text("'{}'::json")),
        
        # 元数据
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False, default=0.0),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('template_id', 'placeholder_name', name='uq_template_placeholder_name')
    )

    # 创建占位符值存储表
    op.create_table('placeholder_values',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('placeholder_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('data_source_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # 执行结果
        sa.Column('raw_query_result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('processed_value', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('formatted_text', sa.Text(), nullable=True),
        
        # 执行元数据
        sa.Column('execution_sql', sa.Text(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=False, default=0),
        sa.Column('success', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        
        # 缓存管理
        sa.Column('cache_key', sa.String(length=255), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('hit_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_hit_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['placeholder_id'], ['template_placeholders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ondelete='CASCADE'),
        sa.Index('ix_placeholder_values_cache_key', 'cache_key'),
        sa.Index('ix_placeholder_values_expires_at', 'expires_at'),
        sa.Index('ix_placeholder_values_placeholder_datasource', 'placeholder_id', 'data_source_id')
    )

    # 创建模板执行历史表
    op.create_table('template_execution_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('data_source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # 执行信息
        sa.Column('execution_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        
        # 阶段标记
        sa.Column('analysis_completed', sa.Boolean(), nullable=False, default=False),
        sa.Column('sql_validation_completed', sa.Boolean(), nullable=False, default=False),
        sa.Column('data_extraction_completed', sa.Boolean(), nullable=False, default=False),
        sa.Column('report_generation_completed', sa.Boolean(), nullable=False, default=False),
        
        # 性能指标
        sa.Column('total_duration_ms', sa.Integer(), nullable=True),
        sa.Column('analysis_duration_ms', sa.Integer(), nullable=True),
        sa.Column('extraction_duration_ms', sa.Integer(), nullable=True),
        sa.Column('generation_duration_ms', sa.Integer(), nullable=True),
        
        # 结果信息
        sa.Column('placeholders_analyzed', sa.Integer(), nullable=False, default=0),
        sa.Column('placeholders_extracted', sa.Integer(), nullable=False, default=0),
        sa.Column('cache_hit_rate', sa.Float(), nullable=False, default=0.0),
        sa.Column('output_file_path', sa.String(length=500), nullable=True),
        sa.Column('output_file_size', sa.Integer(), nullable=True),
        
        # 错误信息
        sa.Column('error_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('failed_placeholders', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        
        sa.Column('start_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id']),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.Index('ix_template_execution_history_template_time', 'template_id', 'start_time')
    )

    # 创建索引以提高查询性能
    op.create_index('ix_template_placeholders_template_id', 'template_placeholders', ['template_id'])
    op.create_index('ix_template_placeholders_analyzed', 'template_placeholders', ['agent_analyzed', 'is_active'])
    op.create_index('ix_template_placeholders_execution_order', 'template_placeholders', ['template_id', 'execution_order'])


def downgrade():
    # 删除索引
    op.drop_index('ix_template_placeholders_execution_order', table_name='template_placeholders')
    op.drop_index('ix_template_placeholders_analyzed', table_name='template_placeholders')
    op.drop_index('ix_template_placeholders_template_id', table_name='template_placeholders')
    
    # 删除表
    op.drop_table('template_execution_history')
    op.drop_table('placeholder_values')
    op.drop_table('template_placeholders')