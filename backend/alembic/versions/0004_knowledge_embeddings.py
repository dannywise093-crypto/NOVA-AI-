"""knowledge chunk embeddings"""
from alembic import op
import sqlalchemy as sa

revision = "0004_knowledge_embeddings"
down_revision = "0003_memories"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("knowledge_chunks", sa.Column("embedding", sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column("knowledge_chunks", "embedding")
