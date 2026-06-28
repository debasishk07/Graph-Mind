from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.analysis import (
    GraphResponse,
    GraphNodeDetail,
    PathResponse,
    ImpactAnalysisResponse,
    DeadCodeReport,
    RepositorySummary,
    RepositoryStats,
)
from app.services.graph_service import GraphService
from app.utils.security import verify_token
from app.models.user import User

router = APIRouter()


async def get_current_user_id(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UUID:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header.split(" ")[1]
    user_id = verify_token(token, "access")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


async def verify_repo_access(
    repository_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from app.models.repository import Repository
    from sqlalchemy import select
    result = await db.execute(
        select(Repository).where(Repository.id == repository_id, Repository.user_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("/{repository_id}", response_model=GraphResponse)
async def get_graph(
    repository_id: UUID,
    depth: int = Query(2, ge=1, le=5),
    focus: Optional[str] = None,
    filter_types: Optional[str] = None,
    repo = Depends(verify_repo_access),
    db: AsyncSession = Depends(get_db),
):
    graph_service = GraphService(db)
    filter_list = filter_types.split(",") if filter_types else None
    return await graph_service.get_graph_data(repository_id, depth, focus, filter_list)


@router.get("/{repository_id}/node/{symbol_id}", response_model=GraphNodeDetail)
async def get_node_detail(
    repository_id: UUID,
    symbol_id: str,
    repo = Depends(verify_repo_access),
    db: AsyncSession = Depends(get_db),
):
    graph_service = GraphService(db)
    result = await graph_service.get_node_detail(repository_id, symbol_id)
    if not result:
        raise HTTPException(status_code=404, detail="Node not found")
    return result


@router.get("/{repository_id}/path", response_model=PathResponse)
async def find_path(
    repository_id: UUID,
    from_id: str = Query(...),
    to_id: str = Query(...),
    repo = Depends(verify_repo_access),
    db: AsyncSession = Depends(get_db),
):
    graph_service = GraphService(db)
    path = await graph_service.find_path(repository_id, from_id, to_id)
    if not path:
        raise HTTPException(status_code=404, detail="No path found")
    return {"path": path, "distance": len(path) - 1}


@router.get("/{repository_id}/impact/{symbol_id}", response_model=ImpactAnalysisResponse)
async def get_impact(
    repository_id: UUID,
    symbol_id: str,
    repo = Depends(verify_repo_access),
    db: AsyncSession = Depends(get_db),
):
    graph_service = GraphService(db)
    result = await graph_service.get_impact_analysis(repository_id, symbol_id)
    if not result:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return result


@router.get("/{repository_id}/dead-code", response_model=DeadCodeReport)
async def get_dead_code(
    repository_id: UUID,
    repo = Depends(verify_repo_access),
    db: AsyncSession = Depends(get_db),
):
    graph_service = GraphService(db)
    return await graph_service.get_dead_code_report(repository_id)


@router.get("/{repository_id}/layers")
async def get_layers(
    repository_id: UUID,
    repo = Depends(verify_repo_access),
    db: AsyncSession = Depends(get_db),
):
    graph_service = GraphService(db)
    return await graph_service.get_layers(repository_id)


@router.get("/{repository_id}/cycles")
async def get_cycles(
    repository_id: UUID,
    repo = Depends(verify_repo_access),
    db: AsyncSession = Depends(get_db),
):
    graph_service = GraphService(db)
    report = await graph_service.get_dead_code_report(repository_id)
    return {"circular_cycles": report["circular_cycles"]}