"""update_etl_job_enhanced_source_fk

Revision ID: 3e4f5a6b7c8d
Revises: create_enhanced_data_source
Create Date: 2025-07-14 15:20:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3e4f5a6b7c8d'
down_revision = 'create_enhanced_data_source'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 enhanced_source_id 外键
    op.add_column('etl_jobs', sa.Column('enhanced_source_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_etl_jobs_enhanced_source_id',
        'etl_jobs', 'enhanced_data_sources',
        ['enhanced_source_id'], ['id']
    )
    
    # 修改 source_data_source_id 为可空
    op.alter_column('etl_jobs', 'source_data_source_id',
               existing_type=sa.Integer(),
               nullable=True)


def downgrade() -> None:
    # 恢复 source_data_source_id 为非空
    op.alter_column('etl_jobs', 'source_data_source_id',
               existing_type=sa.Integer(),
               nullable=False)
    
    # 删除 enhanced_source_id 外键
    op.drop_constraint('fk_etl_jobs_enhanced_source_id', 'etl_jobs', type_='foreignkey')
    op.drop_column('etl_jobs', 'enhanced_source_id')
