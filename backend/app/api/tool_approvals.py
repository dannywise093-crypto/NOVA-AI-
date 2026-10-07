from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.tools.permissions import PermissionPolicy

router = APIRouter(tags=["tools"])
policy = PermissionPolicy()


class ToolApprovalRequest(BaseModel):
    tool: str = Field(min_length=1, max_length=200)
    arguments: dict[str, Any] = Field(default_factory=dict)
    approval_id: str = Field(min_length=1, max_length=200)


@router.post("/tools/approvals")
async def approve_tool(request: ToolApprovalRequest, user: User = Depends(get_current_user)) -> dict[str, object]:
    if not policy.approve(request.tool, request.arguments, request.approval_id):
        raise HTTPException(status_code=403, detail="Invalid or expired tool approval")
    return {"approved": True, "tool": request.tool}
