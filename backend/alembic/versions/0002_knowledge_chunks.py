"""persistent project knowledge chunks"""
from alembic import op
import sqlalchemy as sa

revision = "0002_knowledge_chunks"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("knowledge_chunks",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("project_id", sa.String(100), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("artifact_id", sa.String(100), sa.ForeignKey("artifacts.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_knowledge_chunks_project_id", "knowledge_chunks", ["project_id"])
    op.create_index("ix_knowledge_chunks_artifact_id", "knowledge_chunks", ["artifact_id"])

def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_artifact_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_project_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
