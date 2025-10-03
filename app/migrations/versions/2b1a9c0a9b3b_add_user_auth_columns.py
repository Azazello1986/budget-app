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
    """Upgrade schema: add auth-related columns to user."""
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('hashed_password', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('ssh_public_key', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema: drop auth-related columns from user."""
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('ssh_public_key')
        batch_op.drop_column('hashed_password')


