"""create enhanced data source table

Revision ID: 3f4a5b6c7d8e
Revises: add_connection_string
Create Date: 2025-07-14 14:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3f4a5b6c7d8e'
down_revision = 'add_connection_string'
branch_labels = None
depends_on = None


def upgrade():
    # 创建增强版数据源表
    op.create_table(
        'enhanced_data_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('source_type', sa.Enum('sql', 'csv', 'api', 'push', name='datasource_type'), nullable=False),
        sa.Column('sql_query_type', sa.Enum('single_table', 'multi_table', 'custom_view', name='sqlquery_type'), nullable=False),
        sa.Column('connection_string', sa.String(), nullable=True),
        sa.Column('base_query', sa.Text(), nullable=True),
        sa.Column('join_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('column_mapping', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('where_conditions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('wide_table_name', sa.String(), nullable=True),
        sa.Column('wide_table_schema', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('api_url', sa.String(), nullable=True),
        sa.Column('api_method', sa.String(), nullable=True),
        sa.Column('api_headers', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('api_body', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('push_endpoint', sa.String(), nullable=True),
        sa.Column('push_auth_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_sync_time', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # 创建索引
    op.create_index('ix_enhanced_data_sources_name', 'enhanced_data_sources', ['name'])
    op.create_index('ix_enhanced_data_sources_source_type', 'enhanced_data_sources', ['source_type'])
    op.create_index('ix_enhanced_data_sources_is_active', 'enhanced_data_sources', ['is_active'])


def downgrade():
    # 删除索引
    op.drop_index('ix_enhanced_data_sources_is_active', table_name='enhanced_data_sources')
    op.drop_index('ix_enhanced_data_sources_source_type', table_name='enhanced_data_sources')
    op.drop_index('ix_enhanced_data_sources_name', table_name='enhanced_data_sources')
    
    # 删除表
    op.drop_table('enhanced_data_sources')
    
    # 删除枚举类型
    op.execute('DROP TYPE IF EXISTS datasource_type')
    op.execute('DROP TYPE IF EXISTS sqlquery_type')
