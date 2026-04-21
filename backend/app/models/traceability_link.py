from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TraceabilityLink(Base):
    __tablename__ = "traceability_link"
    __table_args__ = (
        UniqueConstraint("requirement_id", "section_id", name="uq_traceability_requirement_section"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requirement.id", ondelete="CASCADE"),
        nullable=False,
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_section.id", ondelete="CASCADE"),
        nullable=False,
    )
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    requirement: Mapped["Requirement"] = relationship("Requirement", back_populates="traceability_links")
    document_section: Mapped["DocumentSection"] = relationship("DocumentSection", back_populates="traceability_links")

    def __repr__(self) -> str:
        return (
            f"TraceabilityLink(id={self.id!s}, requirement_id={self.requirement_id!s}, "
            f"section_id={self.section_id!s}, similarity_score={self.similarity_score})"
        )
