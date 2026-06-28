from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.models.analysis_report import AnalysisReport, ReportType
from app.schemas.analysis import AnalysisReportResponse, RepositorySummary, RefactoringReport
from app.utils.security import verify_token

router = APIRouter()


async def get_current_user_id(request: Request) -> UUID:
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
    result = await db.execute(
        select(Repository).where(Repository.id == repository_id, Repository.user_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(404, "Repository not found")
    return repo


@router.get("/{repository_id}/summary", response_model=RepositorySummary)
async def get_summary(
    repository_id: UUID,
    repo = Depends(verify_repo_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnalysisReport)
        .where(AnalysisReport.repository_id == repository_id)
        .where(AnalysisReport.report_type == ReportType.SUMMARY)
        .order_by(AnalysisReport.generated_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    
    if report:
        return report.content
    
    # Return basic stats if no report yet
    return {
        "statistics": {},
        "architecture_type": "Unknown",
        "key_modules": [],
    }


@router.get("/{repository_id}/refactoring", response_model=RefactoringReport)
async def get_refactoring(
    repository_id: UUID,
    repo = Depends(verify_repo_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnalysisReport)
        .where(AnalysisReport.repository_id == repository_id)
        .where(AnalysisReport.report_type == ReportType.REFACTORING)
        .order_by(AnalysisReport.generated_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    
    if report:
        return report.content
    
    return {"issues": [], "summary": "No refactoring analysis available yet."}


@router.get("/{repository_id}/reports", response_model=list[AnalysisReportResponse])
async def list_reports(
    repository_id: UUID,
    repo = Depends(verify_repo_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnalysisReport)
        .where(AnalysisReport.repository_id == repository_id)
        .order_by(AnalysisReport.generated_at.desc())
    )
    return result.scalars().all()


@router.get("/{repository_id}/reports/{report_id}", response_model=AnalysisReportResponse)
async def get_report(
    repository_id: UUID,
    report_id: UUID,
    repo = Depends(verify_repo_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnalysisReport)
        .where(AnalysisReport.id == report_id)
        .where(AnalysisReport.repository_id == repository_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    return report