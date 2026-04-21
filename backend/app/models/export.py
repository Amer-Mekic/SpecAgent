from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Export(Base):
    __tablename__ = "export"

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
    format: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Valid values: pdf | docx",
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("export.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session: Mapped["Session"] = relationship("Session", back_populates="exports")
    parent: Mapped["Export | None"] = relationship(
        "Export",
        foreign_keys=[parent_id],
        back_populates="children",
        remote_side=[id],
    )
    children: Mapped[list["Export"]] = relationship(
        "Export",
        back_populates="parent",
    )

    def __repr__(self) -> str:
        return f"Export(id={self.id!s}, session_id={self.session_id!s}, version={self.version})"
