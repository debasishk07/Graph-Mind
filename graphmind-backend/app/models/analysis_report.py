import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.repository import Repository


class ReportType(str, enum.Enum):
    SUMMARY = "summary"
    DEAD_CODE = "dead_code"
    IMPACT = "impact"
    REFACTORING = "refactoring"
    ARCHITECTURE = "architecture"


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    repository: Mapped["Repository"] = relationship(back_populates="analysis_reports")

    __table_args__ = (
        Index("ix_analysis_reports_repo_type", "repository_id", "report_type"),
    )

    def __repr__(self) -> str:
        return f"<AnalysisReport(id={self.id}, type={self.report_type})>"


from sqlalchemy import func