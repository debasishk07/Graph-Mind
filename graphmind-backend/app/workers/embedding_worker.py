from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.config import get_settings
from app.database import async_session_maker
from app.models.repository import Repository, RepositoryStatus
from app.models.symbol import Symbol
from app.workers.celery_app import celery_app
from app.utils.socketio import emit_progress

settings = get_settings()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_embeddings_task(self, repository_id: str):
    """Generate embeddings for all symbols in a repository."""
    import asyncio

    async def _generate():
        async with async_session_maker() as db:
            await _generate_embeddings_async(db, UUID(repository_id))

    asyncio.run(_generate())


async def _generate_embeddings_async(db: AsyncSession, repository_id: UUID):
    """Async embedding generation logic."""
    # Get repository
    result = await db.execute(
        select(Repository).where(Repository.id == repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        return

    # Update status
    repository.status = RepositoryStatus.EMBEDDING
    repository.status_message = "Generating embeddings..."
    repository.analysis_progress = 80
    await db.commit()

    await emit_progress(str(repository_id), "embedding", 80, "Generating embeddings...")

    # Get all symbols without embeddings
    result = await db.execute(
        select(Symbol)
        .where(Symbol.repository_id == repository_id)
        .where(Symbol.embedding_id.is_(None))
    )
    symbols = result.scalars().all()

    if not symbols:
        repository.status = RepositoryStatus.READY
        repository.status_message = "Analysis complete"
        repository.analysis_progress = 100
        await db.commit()
        await emit_progress(str(repository_id), "ready", 100, "Analysis complete")
        return

    # Initialize embedding model
    try:
        from fastembed import TextEmbedding
        model = TextEmbedding(model_name=settings.embedding_model)
    except Exception as e:
        print(f"Failed to load embedding model: {e}")
        repository.status = RepositoryStatus.ERROR
        repository.status_message = f"Failed to load embedding model: {e}"
        await db.commit()
        return

    # Initialize Qdrant client
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
        qdrant = QdrantClient(url=settings.qdrant_url)
    except Exception as e:
        print(f"Failed to connect to Qdrant: {e}")
        repository.status = RepositoryStatus.ERROR
        repository.status_message = f"Failed to connect to Qdrant: {e}"
        await db.commit()
        return

    # Create collection if not exists
    collection_name = f"repo_{repository_id}"
    try:
        collections = qdrant.get_collections()
        collection_names = [c.name for c in collections.collections]
        if collection_name not in collection_names:
            qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
    except Exception as e:
        print(f"Failed to create collection: {e}")

    # Generate embeddings in batches
    batch_size = 100
    total = len(symbols)
    
    for i in range(0, total, batch_size):
        batch = symbols[i:i + batch_size]
        
        # Prepare texts for embedding
        texts = []
        for symbol in batch:
            text_parts = [
                f"File: {symbol.file.path if symbol.file else 'unknown'}",
                f"Language: {symbol.file.language if symbol.file else 'unknown'}",
                f"Type: {symbol.symbol_type.value}",
                f"Name: {symbol.name}",
                f"Qualified: {symbol.qualified_name or 'unknown'}",
            ]
            if symbol.docstring:
                text_parts.append(f"Docs: {symbol.docstring}")
            if symbol.signature:
                text_parts.append(f"Signature: {symbol.signature}")
            texts.append("\n".join(text_parts))

        # Generate embeddings
        try:
            embeddings = list(model.embed(texts))
        except Exception as e:
            print(f"Failed to generate embeddings for batch: {e}")
            continue

        # Upsert to Qdrant
        points = []
        for j, (symbol, embedding) in enumerate(zip(batch, embeddings)):
            point_id = str(symbol.id)
            points.append(PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload={
                    "symbol_id": str(symbol.id),
                    "file_path": symbol.file.path if symbol.file else "unknown",
                    "name": symbol.name,
                    "type": symbol.symbol_type.value,
                    "language": symbol.file.language if symbol.file else "unknown",
                }
            ))
            # Update symbol with embedding ID
            symbol.embedding_id = point_id

        try:
            qdrant.upsert(collection_name=collection_name, points=points)
        except Exception as e:
            print(f"Failed to upsert to Qdrant: {e}")

        # Update progress
        progress = 80 + int(((i + len(batch)) / total) * 20)
        repository.analysis_progress = progress
        await db.commit()
        await emit_progress(str(repository_id), "embedding", progress, f"Embedded {i + len(batch)}/{total} symbols")

    # Finalize
    repository.status = RepositoryStatus.READY
    repository.status_message = "Analysis complete"
    repository.analysis_progress = 100
    await db.commit()
    await emit_progress(str(repository_id), "ready", 100, "Analysis complete")