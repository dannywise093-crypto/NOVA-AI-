"""task execution leases"""
from alembic import op
import sqlalchemy as sa

revision = "0006_task_leases"
down_revision = "0005_agent_tasks"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("agent_tasks", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("agent_tasks", sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_agent_tasks_lease_until", "agent_tasks", ["lease_until"])

def downgrade() -> None:
    op.drop_index("ix_agent_tasks_lease_until", table_name="agent_tasks")
    op.drop_column("agent_tasks", "lease_until")
    op.drop_column("agent_tasks", "attempts")
