"""persistent user memories"""
from alembic import op
import sqlalchemy as sa

revision = "0003_memories"
down_revision = "0002_knowledge_chunks"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("memories",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("owner_id", sa.String(100), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", sa.String(100), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(50), nullable=False, server_default="fact"),
        sa.Column("importance", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_memories_owner_id", "memories", ["owner_id"])
    op.create_index("ix_memories_project_id", "memories", ["project_id"])

def downgrade() -> None:
    op.drop_index("ix_memories_project_id", table_name="memories")
    op.drop_index("ix_memories_owner_id", table_name="memories")
    op.drop_table("memories")
