from celery import shared_task
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime, timedelta

from app.config import get_settings
from app.database import async_session_maker
from app.models.repository import Repository, RepositoryStatus
from app.models.chat_message import ChatMessage
from app.workers.celery_app import celery_app

settings = get_settings()


@shared_task
def cleanup_old_tasks():
    """Clean up old completed/error repositories and old chat messages."""
    import asyncio
    asyncio.run(_cleanup_old_tasks_async())


async def _cleanup_old_tasks_async():
    async with async_session_maker() as db:
        # Clean up old error/pending repositories older than 7 days
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        result = await db.execute(
            select(Repository)
            .where(Repository.status.in_([RepositoryStatus.ERROR, RepositoryStatus.PENDING]))
            .where(Repository.created_at < cutoff)
        )
        old_repos = result.scalars().all()
        
        for repo in old_repos:
            await db.delete(repo)
        
        # Clean up old chat messages older than 30 days
        chat_cutoff = datetime.utcnow() - timedelta(days=30)
        await db.execute(
            ChatMessage.__table__.delete()
            .where(ChatMessage.created_at < chat_cutoff)
        )
        
        await db.commit()
        print(f"Cleaned up {len(old_repos)} old repositories and old chat messages")