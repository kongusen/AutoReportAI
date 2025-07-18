"""update_etl_job_enhanced_source_fk

Revision ID: 3e4f5a6b7c8d
Revises: 3f4a5b6c7d8e
Create Date: 2025-07-14 15:20:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3e4f5a6b7c8d'
down_revision = '3f4a5b6c7d8e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 enhanced_source_id 外键（必需）
    op.add_column('etl_jobs', sa.Column('enhanced_source_id', sa.Integer(), nullable=False))
    op.create_foreign_key(
        'fk_etl_jobs_enhanced_source_id',
        'etl_jobs', 'enhanced_data_sources',
        ['enhanced_source_id'], ['id']
    )
    
    # 删除旧的 source_data_source_id 外键和列
    op.drop_constraint('etl_jobs_source_data_source_id_fkey', 'etl_jobs', type_='foreignkey')
    op.drop_column('etl_jobs', 'source_data_source_id')


def downgrade() -> None:
    # 添加回 source_data_source_id
    op.add_column('etl_jobs', sa.Column('source_data_source_id', sa.Integer(), nullable=False))
    op.create_foreign_key(
        'etl_jobs_source_data_source_id_fkey',
        'etl_jobs', 'data_sources',
        ['source_data_source_id'], ['id']
    )
    
    # 删除 enhanced_source_id 外键和列
    op.drop_constraint('fk_etl_jobs_enhanced_source_id', 'etl_jobs', type_='foreignkey')
    op.drop_column('etl_jobs', 'enhanced_source_id')
