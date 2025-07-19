"""fix_ai_provider_is_active_type

Revision ID: 0a61be0da7b1
Revises: 4f5a6b7c8d9e
Create Date: 2025-07-15 17:42:09.834622

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a61be0da7b1'
down_revision: Union[str, Sequence[str], None] = '4f5a6b7c8d9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Convert INTEGER to BOOLEAN with proper USING clause
    op.execute("ALTER TABLE ai_providers ALTER COLUMN is_active TYPE BOOLEAN USING (is_active::boolean)")
    

def downgrade() -> None:
    """Downgrade schema."""
    # Convert BOOLEAN back to INTEGER
    op.execute("ALTER TABLE ai_providers ALTER COLUMN is_active TYPE INTEGER USING (is_active::integer)")
