"""add_doris_to_datasourcetype_enum

Revision ID: aa3b7bd0a07f
Revises: user_friendly_ids
Create Date: 2025-08-06 15:56:13.281285

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa3b7bd0a07f'
down_revision: Union[str, Sequence[str], None] = 'user_friendly_ids'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add 'doris' to the datasourcetype enum
    op.execute("ALTER TYPE datasourcetype ADD VALUE 'doris';")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: Removing values from an enum in PostgreSQL is not straightforward
    # and generally not recommended in production environments.
    # This operation is not supported in a simple way.
    pass
