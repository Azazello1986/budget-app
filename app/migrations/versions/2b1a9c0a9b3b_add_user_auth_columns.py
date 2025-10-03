"""add user auth columns

Revision ID: 2b1a9c0a9b3b
Revises: e3f294fc3778
Create Date: 2025-10-03 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b1a9c0a9b3b'
down_revision: Union[str, Sequence[str], None] = 'e3f294fc3778'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add auth-related columns to user (idempotent)."""
    # Use IF NOT EXISTS to avoid errors if columns already present
    op.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255)')
    op.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS ssh_public_key TEXT')


def downgrade() -> None:
    """Downgrade schema: drop auth-related columns from user (idempotent)."""
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS ssh_public_key')
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS hashed_password')


