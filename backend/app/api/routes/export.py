from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.requirement import Requirement
from app.models.session import Session
from app.models.traceability_link import TraceabilityLink
from app.models.user import User
from app.services.export import generate_srs_docx, generate_srs_pdf

router = APIRouter(tags=["export"])


class ExportRequest(BaseModel):
    format: Literal["docx", "pdf"]


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


@router.post("/export/{session_id}")
async def export_session_srs(
    session_id: UUID,
    payload: ExportRequest,
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
        .where(
            Requirement.session_id == session_id,
            Requirement.finalization_status == "final",
        )
        .order_by(Requirement.req_id.asc())
    )
    requirements = list(requirements_result.unique().scalars().all())

    if not requirements:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No approved requirements to export. "
                "Mark requirements as final before exporting."
            ),
        )

    if payload.format == "docx":
        file_path, version, _changes = await generate_srs_docx(
            session_id=session.id,
            session_name=session.document_name,
            requirements=requirements,
            db=db,
        )
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif payload.format == "pdf":
        file_path, version, _changes = await generate_srs_pdf(
            session_id=session.id,
            session_name=session.document_name,
            requirements=requirements,
            db=db,
        )
        media_type = "application/pdf"
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid export format")

    filename = f"SRS_v{version}.{payload.format}"
    return FileResponse(path=file_path, filename=filename, media_type=media_type)
