from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class RepositoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    github_url: Optional[HttpUrl] = None
    default_branch: str = "main"


class RepositoryCreate(RepositoryBase):
    pass


class RepositoryImportGitHub(BaseModel):
    github_url: HttpUrl
    branch: Optional[str] = "main"


class RepositoryImportZip(BaseModel):
    pass  # multipart/form-data handled separately


class RepositoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_branch: Optional[str] = None


class LanguageBreakdown(BaseModel):
    language: str
    percentage: float
    file_count: int
    line_count: int


class RepositoryResponse(RepositoryBase):
    id: UUID
    user_id: UUID
    language_breakdown: Optional[dict] = None
    total_files: int = 0
    total_lines: int = 0
    status: str
    status_message: Optional[str] = None
    analysis_progress: int = 0
    storage_path: Optional[str] = None
    complexity_score: Optional[float] = None
    architecture_type: str
    created_at: datetime
    analyzed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RepositoryListResponse(BaseModel):
    repositories: list[RepositoryResponse]
    total: int
    page: int
    page_size: int


class RepositoryStatusResponse(BaseModel):
    id: UUID
    status: str
    status_message: Optional[str] = None
    analysis_progress: int
    current_stage: Optional[str] = None


class RepositoryStats(BaseModel):
    total_files: int
    total_lines: int
    total_symbols: int
    total_relationships: int
    language_breakdown: dict
    complexity_score: Optional[float] = None
    circular_dep_count: int = 0
    dead_code_count: int = 0