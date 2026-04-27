from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.classification import run_classification
from app.agents.extraction import run_extraction
from app.agents.validation import run_validation
from app.models.classification import Classification
from app.models.document_section import DocumentSection
from app.models.requirement import Requirement
from app.models.session import Session
from app.models.validation_report import ValidationReport
from app.services.traceability import run_traceability


async def get_sections(session_id: UUID, db: AsyncSession) -> list[DocumentSection]:
    result = await db.execute(
        select(DocumentSection)
        .where(DocumentSection.session_id == session_id)
        .order_by(DocumentSection.section_index.asc())
    )
    return list(result.scalars().all())


async def update_session_status(session_id: UUID, status: str, db: AsyncSession) -> None:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        return

    session.status = status
    await db.commit()


def get_req_by_req_id(req_id: str, saved_list: list[tuple[Requirement, dict]]) -> Requirement:
    for req, _raw in saved_list:
        if req.req_id == req_id:
            return req
    raise ValueError(f"Requirement with req_id {req_id} not found in saved list")


async def run_pipeline(session_id: UUID, db: AsyncSession) -> None:
    try:
        sections = await get_sections(session_id, db)
        chunks = [section.content for section in sections]

        if not chunks:
            await update_session_status(session_id, "failed", db)
            return

        await update_session_status(session_id, "extracting", db)
        raw_requirements = await run_extraction(chunks)

        saved_requirements: list[tuple[Requirement, dict]] = []
        for req_data in raw_requirements:
            req = Requirement(
                session_id=session_id,
                req_id=req_data["req_id"],
                statement=req_data["statement"],
                status="raw",
                finalization_status="draft",
                edited_by="system",
            )
            db.add(req)
            saved_requirements.append((req, req_data))

        await db.commit()
        for req, _ in saved_requirements:
            await db.refresh(req)

        await update_session_status(session_id, "validating", db)
        req_dicts = [
            {"req_id": req.req_id, "statement": req.statement}
            for req, _ in saved_requirements
        ]
        validation_results = await run_validation(req_dicts)

        for v_result in validation_results:
            req = get_req_by_req_id(v_result.requirement_id, saved_requirements)
            report = ValidationReport(
                requirement_id=req.id,
                result=v_result.result,
                issues=[issue.model_dump() for issue in v_result.issues],
                suggestions=[issue.suggestion for issue in v_result.issues],
            )
            req.status = "validated"
            db.add(report)

        await db.commit()

        await update_session_status(session_id, "classifying", db)
        classification_results = await run_classification(req_dicts)

        for c_result in classification_results:
            req = get_req_by_req_id(c_result.requirement_id, saved_requirements)
            classification = Classification(
                requirement_id=req.id,
                type=c_result.type,
                sub_category=c_result.sub_category,
                confidence=c_result.confidence,
            )
            req.status = "classified"
            db.add(classification)

        await db.commit()

        await update_session_status(session_id, "tracing", db)
        await run_traceability(session_id, db)

        for req, _ in saved_requirements:
            req.status = "traced"
        await db.commit()

        await update_session_status(session_id, "complete", db)
    except Exception:
        await update_session_status(session_id, "failed", db)
        raise
