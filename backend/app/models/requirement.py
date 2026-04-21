from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Requirement(Base):
    __tablename__ = "requirement"
    __table_args__ = (
        UniqueConstraint("session_id", "req_id", name="uq_requirement_session_req_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("session.id", ondelete="CASCADE"),
        nullable=False,
    )
    req_id: Mapped[str] = mapped_column(String(20), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="raw",
        server_default="raw",
        comment="Valid values: raw | validated | classified | traced",
    )
    finalization_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
        server_default="draft",
        comment="Valid values: draft | reviewed | final | rejected",
    )
    edited_by: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Valid values: system | user",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    session: Mapped["Session"] = relationship("Session", back_populates="requirements")
    validation_report: Mapped["ValidationReport | None"] = relationship(
        "ValidationReport",
        back_populates="requirement",
        uselist=False,
        cascade="all, delete-orphan",
    )
    classification: Mapped["Classification | None"] = relationship(
        "Classification",
        back_populates="requirement",
        uselist=False,
        cascade="all, delete-orphan",
    )
    traceability_links: Mapped[list["TraceabilityLink"]] = relationship(
        "TraceabilityLink",
        back_populates="requirement",
        cascade="all, delete-orphan",
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="requirement",
    )

    def __repr__(self) -> str:
        return f"Requirement(id={self.id!s}, req_id={self.req_id!r}, status={self.status!r})"
