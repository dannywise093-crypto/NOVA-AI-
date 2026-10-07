"""task heartbeat timestamps"""
from alembic import op
import sqlalchemy as sa

revision = "0007_task_heartbeat"
down_revision = "0006_task_leases"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("agent_tasks", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_agent_tasks_heartbeat_at", "agent_tasks", ["heartbeat_at"])

def downgrade() -> None:
    op.drop_index("ix_agent_tasks_heartbeat_at", table_name="agent_tasks")
    op.drop_column("agent_tasks", "heartbeat_at")
