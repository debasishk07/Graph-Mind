import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RepositoryStatus(enum.Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    EMBEDDING = "embedding"
    READY = "ready"
    ERROR = "error"


class ArchitectureType(enum.Enum):
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


class File(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    path: Mapped[str] = mapped_column(String(1000), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    line_count: Mapped[int] = mapped_column(Integer, default=0)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    complexity_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    is_entry_point: Mapped[bool] = mapped_column(default=False)
    is_test_file: Mapped[bool] = mapped_column(default=False)

    repository: Mapped["Repository"] = relationship(back_populates="files")
    symbols: Mapped[list["Symbol"]] = relationship(back_populates="file", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("repository_id", "path", name="uq_file_repo_path"),
        Index("idx_files_repo_language", "repository_id", "language"),
    )


class SymbolType(enum.Enum):
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    INTERFACE = "interface"
    ROUTE = "route"
    MODEL = "model"
    VARIABLE = "variable"
    ENUM = "enum"
    TYPE_ALIAS = "type_alias"


class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    qualified_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, index=True)
    symbol_type: Mapped[SymbolType] = mapped_column(Enum(SymbolType), nullable=False, index=True)
    start_line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    docstring: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_exported: Mapped[bool] = mapped_column(default=False)
    is_dead_code: Mapped[bool] = mapped_column(default=False, index=True)
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    complexity_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    file: Mapped["File"] = relationship(back_populates="symbols")
    repository: Mapped["Repository"] = relationship(back_populates="symbols")
    outgoing_relationships: Mapped[list["Relationship"]] = relationship(
        foreign_keys="Relationship.source_symbol_id", back_populates="source_symbol", cascade="all, delete-orphan"
    )
    incoming_relationships: Mapped[list["Relationship"]] = relationship(
        foreign_keys="Relationship.target_symbol_id", back_populates="target_symbol", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_symbols_repo_type", "repository_id", "symbol_type"),
        Index("idx_symbols_qualified_name", "qualified_name"),
    )


class RelationshipType(enum.Enum):
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    USES = "USES"
    DEPENDS_ON = "DEPENDS_ON"
    REFERENCES = "REFERENCES"


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_symbol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_symbol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[RelationshipType] = mapped_column(Enum(RelationshipType), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    is_dynamic: Mapped[bool] = mapped_column(default=False)
    line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    repository: Mapped["Repository"] = relationship(back_populates="relationships")
    source_symbol: Mapped["Symbol"] = relationship(
        foreign_keys=[source_symbol_id], back_populates="outgoing_relationships"
    )
    target_symbol: Mapped["Symbol"] = relationship(
        foreign_keys=[target_symbol_id], back_populates="incoming_relationships"
    )

    __table_args__ = (
        Index("idx_relationships_repo_type", "repository_id", "relationship_type"),
    )


class ReportType(enum.Enum):
    SUMMARY = "summary"
    DEAD_CODE = "dead_code"
    IMPACT = "impact"
    REFACTORING = "refactoring"


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    repository: Mapped["Repository"] = relationship(back_populates="analysis_reports")


class MessageRole(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    context_symbols: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    repository: Mapped["Repository"] = relationship(back_populates="chat_messages")
    user: Mapped["User"] = relationship(back_populates="chat_messages")