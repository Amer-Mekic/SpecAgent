from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ValidationReport(Base):
    __tablename__ = "validation_report"

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
        unique=True,
    )
    result: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Valid values: pass | flagged | rejected",
    )
    issues: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    suggestions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    requirement: Mapped["Requirement"] = relationship("Requirement", back_populates="validation_report")

    def __repr__(self) -> str:
        return f"ValidationReport(id={self.id!s}, requirement_id={self.requirement_id!s}, result={self.result!r})"
