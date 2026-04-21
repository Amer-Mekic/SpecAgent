from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Classification(Base):
    __tablename__ = "classification"

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
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Valid values: functional | non-functional",
    )
    sub_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    requirement: Mapped["Requirement"] = relationship("Requirement", back_populates="classification")

    def __repr__(self) -> str:
        return f"Classification(id={self.id!s}, requirement_id={self.requirement_id!s}, type={self.type!r})"
