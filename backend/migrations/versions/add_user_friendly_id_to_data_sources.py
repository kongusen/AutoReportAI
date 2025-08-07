"""Add user-friendly ID fields to data sources

Revision ID: user_friendly_ids
Revises: a89cde1cb970
Create Date: 2025-07-29 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'user_friendly_ids'
down_revision = 'a89cde1cb970'
branch_labels = None
depends_on = None


def upgrade():
    """Add user-friendly ID fields"""
    # Add slug field for user-friendly IDs
    op.add_column('data_sources', sa.Column('slug', sa.String(), nullable=True))
    op.add_column('data_sources', sa.Column('display_name', sa.String(), nullable=True))
    
    # Create unique constraint on slug per user
    op.create_index('ix_data_sources_slug', 'data_sources', ['slug'])
    op.create_unique_constraint('uq_data_sources_user_slug', 'data_sources', ['user_id', 'slug'])
    
    # Create index for better performance
    op.create_index('ix_data_sources_display_name', 'data_sources', ['display_name'])


def downgrade():
    """Remove user-friendly ID fields"""
    op.drop_index('ix_data_sources_display_name', table_name='data_sources')
    op.drop_constraint('uq_data_sources_user_slug', 'data_sources', type_='unique')
    op.drop_index('ix_data_sources_slug', table_name='data_sources')
    op.drop_column('data_sources', 'display_name')
    op.drop_column('data_sources', 'slug')