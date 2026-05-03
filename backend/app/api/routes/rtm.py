from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.requirement import Requirement
from app.models.session import Session
from app.models.traceability_link import TraceabilityLink
from app.models.user import User
from app.services.export import generate_rtm_pdf

router = APIRouter(tags=["rtm"])


async def _get_owned_session(
    session_id: UUID,
    db: AsyncSession,
    current_user: User,
) -> Session:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return session


@router.get("/rtm/{session_id}")
async def get_traceability_matrix(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    session = await _get_owned_session(session_id, db, current_user)

    requirements_result = await db.execute(
        select(Requirement)
        .options(
            joinedload(Requirement.classification),
            joinedload(Requirement.validation_report),
            joinedload(Requirement.traceability_links).joinedload(TraceabilityLink.document_section),
        )
        .where(Requirement.session_id == session_id, (Requirement.status == "validated") | (Requirement.status == "classified") | (Requirement.status == "traced"))
        .order_by(Requirement.req_id.asc())
    )
    requirements = list(requirements_result.unique().scalars().all())

    rows: list[dict[str, object]] = []
    for requirement in requirements:
        sorted_links = sorted(
            requirement.traceability_links,
            key=lambda link: link.similarity_score,
            reverse=True,
        )
        top_sources = []
        for link in sorted_links[:3]:
            source_identifier = None
            source_page = None
            if link.document_section is not None:
                source_identifier = link.document_section.source_identifier
                source_page = link.document_section.source_page

            top_sources.append(
                {
                    "source_identifier": source_identifier,
                    "source_page": source_page,
                    "similarity_score": link.similarity_score,
                }
            )

        rows.append(
            {
                "req_id": requirement.req_id,
                "statement": requirement.statement,
                "type": requirement.classification.type if requirement.classification else None,
                "sub_category": requirement.classification.sub_category if requirement.classification else None,
                "validation_result": requirement.validation_report.result if requirement.validation_report else None,
                "finalization_status": requirement.finalization_status,
                "sources": top_sources,
            }
        )

    return {
        "session_id": str(session.id),
        "document_name": session.document_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_requirements": len(rows),
        "rows": rows,
    }


@router.post("/rtm/{session_id}/export")
async def export_rtm_pdf(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    session = await _get_owned_session(session_id, db, current_user)

    requirements_result = await db.execute(
        select(Requirement)
        .options(
            joinedload(Requirement.classification),
            joinedload(Requirement.validation_report),
            joinedload(Requirement.traceability_links).joinedload(TraceabilityLink.document_section),
        )
        .where(Requirement.session_id == session_id, (Requirement.status == "validated") | (Requirement.status == "classified") | (Requirement.status == "traced"))
        .order_by(Requirement.req_id.asc())
    )
    requirements = list(requirements_result.unique().scalars().all())

    rows: list[dict[str, object]] = []
    for requirement in requirements:
        sorted_links = sorted(
            requirement.traceability_links,
            key=lambda link: link.similarity_score,
            reverse=True,
        )
        top_sources = []
        for link in sorted_links[:3]:
            source_identifier = None
            source_page = None
            if link.document_section is not None:
                source_identifier = link.document_section.source_identifier
                source_page = link.document_section.source_page

            top_sources.append(
                {
                    "source_identifier": source_identifier,
                    "source_page": source_page,
                    "similarity_score": link.similarity_score,
                }
            )

        rows.append(
            {
                "req_id": requirement.req_id,
                "statement": requirement.statement,
                "type": requirement.classification.type if requirement.classification else None,
                "sub_category": requirement.classification.sub_category if requirement.classification else None,
                "validation_result": requirement.validation_report.result if requirement.validation_report else None,
                "finalization_status": requirement.finalization_status,
                "sources": top_sources,
            }
        )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No requirements to export.",
        )

    pdf_path = await generate_rtm_pdf(
        session_id=session.id,
        session_name=session.document_name,
        rows=rows,
        db=db,
    )

    return FileResponse(path=pdf_path, filename="RTM.pdf", media_type="application/pdf")
