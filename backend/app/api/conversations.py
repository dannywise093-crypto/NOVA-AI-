from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.conversations.base import Conversation, Message
from app.conversations.runtime import conversation_store

router = APIRouter(tags=["conversations"])
store = conversation_store

class ConversationCreate(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    project_id: str | None = None

class MessageCreate(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=30)
    content: str = Field(min_length=1)

def owned(conversation: Conversation, user: User) -> Conversation:
    if conversation.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@router.post("/conversations", response_model=Conversation)
async def create_conversation(request: ConversationCreate, user: User = Depends(get_current_user)) -> Conversation:
    try:
        return store.create(Conversation(id=request.id, title=request.title, project_id=request.project_id, owner_id=user.id))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.get("/conversations", response_model=list[Conversation])
async def list_conversations(project_id: str | None = None, user: User = Depends(get_current_user)) -> list[Conversation]:
    return [item for item in store.list(project_id) if item.owner_id == user.id]

@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str, user: User = Depends(get_current_user)) -> Conversation:
    conversation = store.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return owned(conversation, user)

@router.post("/conversations/{conversation_id}/messages", response_model=Conversation)
async def add_message(conversation_id: str, request: MessageCreate, user: User = Depends(get_current_user)) -> Conversation:
    conversation = store.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    owned(conversation, user)
    conversation.add_message(Message(id=request.id, role=request.role, content=request.content))
    return store.save(conversation)
