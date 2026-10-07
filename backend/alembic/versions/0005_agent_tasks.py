"""persistent agent tasks"""
from alembic import op
import sqlalchemy as sa

revision = "0005_agent_tasks"
down_revision = "0004_knowledge_embeddings"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("owner_id", sa.String(100), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("conversation_id", sa.String(100), sa.ForeignKey("conversations.id"), nullable=True),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_tasks_owner_id", "agent_tasks", ["owner_id"])
    op.create_index("ix_agent_tasks_status", "agent_tasks", ["status"])

def downgrade() -> None:
    op.drop_index("ix_agent_tasks_status", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_owner_id", table_name="agent_tasks")
    op.drop_table("agent_tasks")
