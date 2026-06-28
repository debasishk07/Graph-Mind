from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from app.config import get_settings
from app.database import get_db
from app.models.repository import Repository, RepositoryStatus
from app.models.file import File
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryUpdate,
    RepositoryResponse,
    RepositoryListResponse,
    RepositoryImportGitHub,
    RepositoryStatusResponse,
    RepositoryStats,
)
from app.services.auth_service import AuthService
from app.utils.security import verify_token
from app.workers.celery_app import parse_repository_task

router = APIRouter()
settings = get_settings()


async def get_current_user_id(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UUID:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header.split(" ")[1]
    user_id = verify_token(token, "access")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    repo_data: RepositoryCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    repository = Repository(
        user_id=user_id,
        name=repo_data.name,
        description=repo_data.description,
        github_url=str(repo_data.github_url) if repo_data.github_url else None,
        default_branch=repo_data.default_branch,
        status=RepositoryStatus.PENDING,
    )
    db.add(repository)
    await db.commit()
    await db.refresh(repository)
    return RepositoryResponse.model_validate(repository)


@router.post("/import/github", response_model=RepositoryResponse, status_code=status.HTTP_202_ACCEPTED)
async def import_from_github(
    import_data: RepositoryImportGitHub,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Create repository record
    repository = Repository(
        user_id=user_id,
        name=import_data.github_url.split("/")[-1].replace(".git", ""),
        github_url=str(import_data.github_url),
        default_branch=import_data.branch,
        status=RepositoryStatus.CLONING,
        status_message="Cloning repository...",
    )
    db.add(repository)
    await db.commit()
    await db.refresh(repository)

    # Queue parsing task
    parse_repository_task.delay(str(repository.id))

    return RepositoryResponse.model_validate(repository)


@router.post("/import/zip", response_model=RepositoryResponse, status_code=status.HTTP_202_ACCEPTED)
async def import_from_zip(
    file: UploadFile = File(...),
    name: str = Form(...),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Validate file
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")

    # Create repository record
    repository = Repository(
        user_id=user_id,
        name=name,
        status=RepositoryStatus.CLONING,
        status_message="Extracting ZIP...",
    )
    db.add(repository)
    await db.commit()
    await db.refresh(repository)

    # Save ZIP to temp location
    temp_dir = tempfile.mkdtemp(prefix=f"graphmind_{repository.id}_")
    zip_path = os.path.join(temp_dir, "repo.zip")

    try:
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract
        extract_path = os.path.join(temp_dir, "extracted")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)

        # Find the actual repo folder (ZIP might have a root folder)
        extracted_items = os.listdir(extract_path)
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_path, extracted_items[0])):
            repo_path = os.path.join(extract_path, extracted_items[0])
        else:
            repo_path = extract_path

        # Update status
        repository.status = RepositoryStatus.PARSING
        repository.status_message = "Scanning files..."
        repository.storage_path = repo_path
        await db.commit()

        # Queue parsing task
        parse_repository_task.delay(str(repository.id))

    except Exception as e:
        repository.status = RepositoryStatus.ERROR
        repository.status_message = f"Failed to extract ZIP: {str(e)}"
        await db.commit()
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail="Failed to process ZIP file")

    return RepositoryResponse.model_validate(repository)


@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    page: int = 1,
    page_size: int = 20,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size

    # Get total count
    total_result = await db.execute(
        select(func.count(Repository.id)).where(Repository.user_id == user_id)
    )
    total = total_result.scalar()

    # Get repositories
    result = await db.execute(
        select(Repository)
        .where(Repository.user_id == user_id)
        .order_by(Repository.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    repositories = result.scalars().all()

    return RepositoryListResponse(
        repositories=[RepositoryResponse.model_validate(r) for r in repositories],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    repository_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Repository)
        .where(Repository.id == repository_id, Repository.user_id == user_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    return RepositoryResponse.model_validate(repository)


@router.get("/{repository_id}/status", response_model=RepositoryStatusResponse)
async def get_repository_status(
    repository_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Repository)
        .where(Repository.id == repository_id, Repository.user_id == user_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    return RepositoryStatusResponse(
        id=repository.id,
        status=repository.status.value,
        status_message=repository.status_message,
        analysis_progress=repository.analysis_progress,
        current_stage=repository.status.value,
    )


@router.get("/{repository_id}/stats", response_model=RepositoryStats)
async def get_repository_stats(
    repository_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Repository)
        .where(Repository.id == repository_id, Repository.user_id == user_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get file count
    file_count_result = await db.execute(
        select(func.count(File.id)).where(File.repository_id == repository_id)
    )
    file_count = file_count_result.scalar()

    # Get language breakdown from files
    lang_result = await db.execute(
        select(File.language, func.count(File.id), func.sum(File.line_count))
        .where(File.repository_id == repository_id)
        .group_by(File.language)
    )
    languages = {}
    total_lines = 0
    for lang, count, lines in lang_result:
        if lang:
            languages[lang] = {"file_count": count, "line_count": lines or 0}
            total_lines += lines or 0

    return RepositoryStats(
        total_files=file_count,
        total_lines=total_lines,
        total_symbols=0,  # TODO: add symbol count
        total_relationships=0,  # TODO: add relationship count
        language_breakdown=languages,
        complexity_score=repository.complexity_score,
        circular_dep_count=0,
        dead_code_count=0,
    )


@router.patch("/{repository_id}", response_model=RepositoryResponse)
async def update_repository(
    repository_id: UUID,
    repo_data: RepositoryUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Repository)
        .where(Repository.id == repository_id, Repository.user_id == user_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    update_data = repo_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(repository, field, value)

    await db.commit()
    await db.refresh(repository)
    return RepositoryResponse.model_validate(repository)


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repository_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Repository)
        .where(Repository.id == repository_id, Repository.user_id == user_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")

    await db.delete(repository)
    await db.commit()