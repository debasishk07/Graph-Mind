import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.file import File
    from app.models.symbol import Symbol
    from app.models.relationship import Relationship
    from app.models.analysis_report import AnalysisReport
    from app.models.chat_message import ChatMessage


class RepositoryStatus(str, enum.Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    EMBEDDING = "embedding"
    READY = "ready"
    ERROR = "error"


class ArchitectureType(str, enum.Enum):
    MVC = "MVC"
    MICROSERVICES = "Microservices"
    MONOLITH = "Monolith"
    LAYERED = "Layered"
    MODULAR = "Modular"
    UNKNOWN = "Unknown"


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    language_breakdown: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    total_lines: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[RepositoryStatus] = mapped_column(
        Enum(RepositoryStatus), default=RepositoryStatus.PENDING, nullable=False, index=True
    )
    status_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analysis_progress: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    complexity_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    architecture_type: Mapped[ArchitectureType] = mapped_column(
        Enum(ArchitectureType), default=ArchitectureType.UNKNOWN, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship(back_populates="repositories")
    files: Mapped[list["File"]] = relationship(back_populates="repository", cascade="all, delete-orphan")
    symbols: Mapped[list["Symbol"]] = relationship(back_populates="repository", cascade="all, delete-orphan")
    relationships: Mapped[list["Relationship"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    analysis_reports: Mapped[list["AnalysisReport"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_repositories_user_id_created_at", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Repository(id={self.id}, name={self.name}, status={self.status})>"