from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List, Optional

from app.database import get_db
from app.models.chat_message import ChatMessage, MessageRole
from app.schemas.analysis import ChatRequest, ChatResponse, ChatHistoryResponse

router = APIRouter()


@router.post("/{repository_id}", response_model=ChatResponse)
async def chat(
    repository_id: UUID,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    # Save user message
    user_msg = ChatMessage(
        repository_id=repository_id,
        user_id=request.user_id,
        role=MessageRole.USER,
        content=request.message,
    )
    db.add(user_msg)
    await db.commit()
    
    # TODO: Implement RAG pipeline
    # For now, return placeholder
    assistant_content = "RAG pipeline not yet implemented. This will answer questions about your codebase using vector search + graph context."
    
    # Save assistant message
    assistant_msg = ChatMessage(
        repository_id=repository_id,
        user_id=request.user_id,
        role=MessageRole.ASSISTANT,
        content=assistant_content,
    )
    db.add(assistant_msg)
    await db.commit()
    
    return ChatResponse(
        message=assistant_content,
        context_symbols=[],
    )


@router.get("/{repository_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    repository_id: UUID,
    user_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.repository_id == repository_id)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    
    return ChatHistoryResponse(
        messages=[{
            "id": str(m.id),
            "role": m.role.value,
            "content": m.content,
            "context_symbols": m.context_symbols,
            "created_at": m.created_at,
        } for m in reversed(messages)]
    )


@router.delete("/{repository_id}/history")
async def clear_chat_history(
    repository_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        ChatMessage.__table__.delete()
        .where(ChatMessage.repository_id == repository_id)
        .where(ChatMessage.user_id == user_id)
    )
    await db.commit()
    return {"message": "History cleared"}