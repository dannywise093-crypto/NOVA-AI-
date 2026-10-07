from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.conversations.base import Conversation, Message
from app.db.conversation_repository import create_conversation, get_conversation, list_conversations, save_conversation
from app.db.session import get_session

router = APIRouter(tags=["conversations"])

class ConversationCreate(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    project_id: str | None = None

class MessageCreate(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=30)
    content: str = Field(min_length=1)

@router.post("/conversations", response_model=Conversation)
async def create(request: ConversationCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> Conversation:
    try:
        return await create_conversation(session, Conversation(id=request.id, title=request.title, project_id=request.project_id, owner_id=user.id))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.get("/conversations", response_model=list[Conversation])
async def list_all(project_id: str | None = None, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> list[Conversation]:
    return await list_conversations(session, user.id, project_id)

@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_one(conversation_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> Conversation:
    item = await get_conversation(session, conversation_id, user.id)
    if item is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return item

@router.post("/conversations/{conversation_id}/messages", response_model=Conversation)
async def add_message(conversation_id: str, request: MessageCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> Conversation:
    item = await get_conversation(session, conversation_id, user.id)
    if item is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    item.add_message(Message(id=request.id, role=request.role, content=request.content))
    return await save_conversation(session, item)
