from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document_section import DocumentSection
from app.models.validation_report import ValidationReport
from app.models.classification import Classification
from app.models.traceability_link import TraceabilityLink
from app.models.chat_message import ChatMessage
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.requirement import Requirement
from app.models.session import Session
from app.models.user import User
from app.services.document import (
    chunk_and_embed,
    compute_document_hash,
    extract_text_by_type,
    save_sections_to_db,
    validate_file_type,
)

router = APIRouter(prefix="/upload", tags=["upload"])

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
UPLOAD_ROOT = Path(__file__).resolve().parents[3] / "exports"


async def _clone_session_data(source: Session, target: Session, db: AsyncSession) -> None:
    section_id_map: dict = {}
    requirement_id_map: dict = {}

    # 1) Clone sections
    for src_sec in source.document_sections:
        new_sec = DocumentSection(
            session_id=target.id,
            section_index=src_sec.section_index,
            content=src_sec.content,
            embedding=src_sec.embedding,
            source_page=src_sec.source_page,
            source_page_end=src_sec.source_page_end,
            source_identifier=src_sec.source_identifier,
            document_type=src_sec.document_type,
        )
        db.add(new_sec)
        await db.flush()
        section_id_map[src_sec.id] = new_sec.id

    # 2) Clone requirements (+ 1:1 children)
    for src_req in source.requirements:
        new_req = Requirement(
            session_id=target.id,
            req_id=src_req.req_id,
            statement=src_req.statement,
            status=src_req.status,
            finalization_status=src_req.finalization_status,
            edited_by=src_req.edited_by,
        )
        db.add(new_req)
        await db.flush()
        requirement_id_map[src_req.id] = new_req.id

        if src_req.validation_report:
            db.add(
                ValidationReport(
                    requirement_id=new_req.id,
                    result=src_req.validation_report.result,
                    issues=src_req.validation_report.issues,
                    suggestions=src_req.validation_report.suggestions,
                )
            )

        if src_req.classification:
            db.add(
                Classification(
                    requirement_id=new_req.id,
                    type=src_req.classification.type,
                    sub_category=src_req.classification.sub_category,
                    confidence=src_req.classification.confidence,
                )
            )

    # 3) Clone traceability links (many-to-many bridge)
    for src_req in source.requirements:
        for src_link in src_req.traceability_links:
            db.add(
                TraceabilityLink(
                    requirement_id=requirement_id_map[src_link.requirement_id],
                    section_id=section_id_map[src_link.section_id],
                    similarity_score=src_link.similarity_score,
                )
            )

    # 4) Clone chat messages (remap optional requirement_id)
    for src_msg in source.chat_messages:
        db.add(
            ChatMessage(
                session_id=target.id,
                requirement_id=(
                    requirement_id_map.get(src_msg.requirement_id)
                    if src_msg.requirement_id is not None
                    else None
                ),
                role=src_msg.role,
                content=src_msg.content,
            )
        )

    await db.commit()


@router.post("")
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    file_bytes = await file.read()

    if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 10 MB limit")

    doc_type = validate_file_type(file_bytes, file.filename or "")
    doc_hash = compute_document_hash(file_bytes)

    existing_result = await db.execute(
    select(Session)
    .options(
        selectinload(Session.document_sections),
        selectinload(Session.requirements).selectinload(Requirement.validation_report),
        selectinload(Session.requirements).selectinload(Requirement.classification),
        selectinload(Session.requirements).selectinload(Requirement.traceability_links),
        selectinload(Session.chat_messages),
    )
    .where(
        Session.document_hash == doc_hash,
        Session.status == "complete",
    )
    .order_by(Session.created_at.desc())
    )
    existing_session = existing_result.scalars().first()
    if existing_session is not None:
        new_session = Session(
            user_id=current_user.id,
            document_name=file.filename or "uploaded-document",
            document_hash=doc_hash,
            status="complete",
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)

        await _clone_session_data(existing_session, new_session, db)

        return {
            "session_id": str(new_session.id),
            "cached": True,
            "message": "Document previously processed. Results restored from cache.",
        }

    session = Session(
        user_id=current_user.id,
        document_name=file.filename or "uploaded-document",
        document_hash=doc_hash,
        status="processing",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    try:
        upload_path = UPLOAD_ROOT / str(session.id) / f"{uuid4()}.{doc_type}"
        upload_path.parent.mkdir(parents=True, exist_ok=True)
        upload_path.write_bytes(file_bytes)

        sections = extract_text_by_type(file_bytes, doc_type)
        if not sections:
            session.status = "failed"
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No text could be extracted from this document",
            )

        chunks = chunk_and_embed(sections)
        await save_sections_to_db(chunks, session.id, db)

        session.status = "complete"
        await db.commit()
    except HTTPException:
        await db.rollback()
        session.status = "failed"
        await db.commit()
        raise
    except Exception as exc:
        await db.rollback()
        session.status = "failed"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return {
        "session_id": str(session.id),
        "cached": False,
        "document_name": file.filename,
        "document_type": doc_type,
        "sections_created": len(chunks),
        "message": "Document uploaded and preprocessed. Ready for agent pipeline.",
    }
