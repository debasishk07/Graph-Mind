import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.symbol import Symbol


class RelationshipType(str, enum.Enum):
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
        Index("ix_relationships_source_target", "source_symbol_id", "target_symbol_id"),
        Index("ix_relationships_repo_type", "repository_id", "relationship_type"),
    )

    def __repr__(self) -> str:
        return f"<Relationship(source={self.source_symbol_id} -> target={self.target_symbol_id}, type={self.relationship_type})>"