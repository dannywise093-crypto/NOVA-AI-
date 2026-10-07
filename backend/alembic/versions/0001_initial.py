"""initial NOVA workspace schema"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("users",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("projects",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("owner_id", sa.String(100), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_table("conversations",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("owner_id", sa.String(100), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", sa.String(100), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_conversations_owner_id", "conversations", ["owner_id"])
    op.create_index("ix_conversations_project_id", "conversations", ["project_id"])
    op.create_table("messages",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("conversation_id", sa.String(100), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_table("artifacts",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("project_id", sa.String(100), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_artifacts_project_id", "artifacts", ["project_id"])

def downgrade() -> None:
    op.drop_index("ix_artifacts_project_id", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_project_id", table_name="conversations")
    op.drop_index("ix_conversations_owner_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("ix_projects_owner_id", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
