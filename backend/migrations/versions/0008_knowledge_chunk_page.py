"""add page provenance to knowledge chunks"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("knowledge_chunks", sa.Column("source_page", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("knowledge_chunks", "source_page")
