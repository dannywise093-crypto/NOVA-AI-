from app.db.models import Base
from app.db.session import engine
from app.db.knowledge_repository import KnowledgeChunkRow


async def create_schema() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
