import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.file import File
    from app.models.repository import Repository
    from app.models.relationship import Relationship


class SymbolType(str, enum.Enum):
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
    metadata: Mapped[Optional[dict]] = mapped_column(nullable=True)

    file: Mapped["File"] = relationship(back_populates="symbols")
    repository: Mapped["Repository"] = relationship(back_populates="symbols")
    outgoing_relationships: Mapped[list["Relationship"]] = relationship(
        foreign_keys="Relationship.source_symbol_id",
        back_populates="source_symbol",
        cascade="all, delete-orphan",
    )
    incoming_relationships: Mapped[list["Relationship"]] = relationship(
        foreign_keys="Relationship.target_symbol_id",
        back_populates="target_symbol",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_symbols_repo_type", "repository_id", "symbol_type"),
        Index("ix_symbols_qualified_name", "qualified_name"),
    )

    def __repr__(self) -> str:
        return f"<Symbol(id={self.id}, name={self.name}, type={self.symbol_type})>"