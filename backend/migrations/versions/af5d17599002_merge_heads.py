"""merge_heads

Revision ID: af5d17599002
Revises: 9aab47d2e221, placeholder_mapping_001
Create Date: 2025-07-16 20:28:31.957129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af5d17599002'
down_revision: Union[str, Sequence[str], None] = ('9aab47d2e221', 'placeholder_mapping_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
