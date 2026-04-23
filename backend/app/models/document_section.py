from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentSection(Base):
    __tablename__ = "document_section"

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
    section_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True) # Page number of chunk in source document (null for txt files or non-page-based sources)
    source_page_end: Mapped[int | None] = mapped_column(Integer, nullable=True) # end page if chunk spans multiple pages
    source_identifier: Mapped[str | None] = mapped_column(Text, nullable=True) # — flexible field for non-page sources
# — for email threads imported as pdf: "Email 3 - From: John, 2024-01-15"
# — for TXT files: "Lines 45-67"
    document_type: Mapped[str] = mapped_column(Text, nullable=True, comment="Valid values: pdf | docx | txt | email") # pdf | docx | txt | email (as pdf, but with email chat data);  — drives which source metadata is populated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    session: Mapped["Session"] = relationship("Session", back_populates="document_sections")
    traceability_links: Mapped[list["TraceabilityLink"]] = relationship(
        "TraceabilityLink",
        back_populates="document_section",
    )

    def __repr__(self) -> str:
        return f"DocumentSection(id={self.id!s}, session_id={self.session_id!s}, section_index={self.section_index})"
