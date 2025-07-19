"""migrate_to_enhanced_data_source_only

Revision ID: 4f5a6b7c8d9e
Revises: 3e4f5a6b7c8d
Create Date: 2025-07-14 22:35:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f5a6b7c8d9e'
down_revision = '3e4f5a6b7c8d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 确保 enhanced_source_id 存在且为非空
    op.alter_column('etl_jobs', 'enhanced_source_id',
               existing_type=sa.Integer(),
               nullable=False)
    
    # 如果存在旧的 source_data_source_id，则删除
    try:
        op.drop_constraint('etl_jobs_source_data_source_id_fkey', 'etl_jobs', type_='foreignkey')
        op.drop_column('etl_jobs', 'source_data_source_id')
    except:
        # 如果列不存在则跳过
        pass


def downgrade() -> None:
    # 添加回 source_data_source_id（仅用于降级）
    op.add_column('etl_jobs', sa.Column('source_data_source_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'etl_jobs_source_data_source_id_fkey',
        'etl_jobs', 'data_sources',
        ['source_data_source_id'], ['id']
    )
    
    # 使 enhanced_source_id 可空
    op.alter_column('etl_jobs', 'enhanced_source_id',
               existing_type=sa.Integer(),
               nullable=True)
