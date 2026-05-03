from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.agents.validation import run_validation
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.requirement import Requirement
from app.models.session import Session
from app.models.traceability_link import TraceabilityLink
from app.models.user import User
from app.models.validation_report import ValidationReport

router = APIRouter(tags=["requirements"])

ALLOWED_FINALIZATION = {"draft", "reviewed", "final", "rejected"}


class RequirementUpdateRequest(BaseModel):
    statement: str | None = None
    finalization_status: str | None = None


def _serialize_requirement(requirement: Requirement) -> dict[str, object]:
    validation_report: dict[str, object] | None = None
    if requirement.validation_report is not None:
        validation_report = {
            "result": requirement.validation_report.result,
            "issues": requirement.validation_report.issues or [],
            "suggestions": requirement.validation_report.suggestions or [],
        }

    classification: dict[str, object] | None = None
    if requirement.classification is not None:
        classification = {
            "type": requirement.classification.type,
            "sub_category": requirement.classification.sub_category,
            "confidence": requirement.classification.confidence,
        }

    traceability_links: list[dict[str, object]] = []
    for link in requirement.traceability_links:
        source_identifier = None
        source_page = None
        if link.document_section is not None:
            source_identifier = link.document_section.source_identifier
            source_page = link.document_section.source_page

        traceability_links.append(
            {
                "section_id": str(link.section_id),
                "source_identifier": source_identifier,
                "source_page": source_page,
                "similarity_score": link.similarity_score,
            }
        )

    return {
        "id": str(requirement.id),
        "req_id": requirement.req_id,
        "statement": requirement.statement,
        "pipeline_status": requirement.status,
        "finalization_status": requirement.finalization_status,
        "edited_by": requirement.edited_by,
        "created_at": requirement.created_at.isoformat(),
        "updated_at": requirement.updated_at.isoformat(),
        "validation_report": validation_report,
        "classification": classification,
        "traceability_links": traceability_links,
    }


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


@router.get("/requirements/{session_id}")
async def get_requirements(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    result = await db.execute(
        select(Session)
        .options(
            joinedload(Session.requirements)
            .joinedload(Requirement.validation_report),
            joinedload(Session.requirements)
            .joinedload(Requirement.classification),
            joinedload(Session.requirements)
            .joinedload(Requirement.traceability_links)
            .joinedload(TraceabilityLink.document_section),
        )
        .where(Session.id == session_id)
    )
    session = result.unique().scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    requirements = sorted(session.requirements, key=lambda req: req.req_id)

    return {
        "session_id": str(session.id),
        "session_status": session.status,
        "requirements": [_serialize_requirement(requirement) for requirement in requirements],
    }


@router.put("/requirements/{requirement_id}")
async def update_requirement(
    requirement_id: UUID,
    payload: RequirementUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    if payload.statement is None and payload.finalization_status is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if payload.finalization_status is not None and payload.finalization_status not in ALLOWED_FINALIZATION:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid finalization_status")

    result = await db.execute(
        select(Requirement)
        .options(
            joinedload(Requirement.session),
            joinedload(Requirement.validation_report),
            joinedload(Requirement.classification),
            joinedload(Requirement.traceability_links).joinedload(TraceabilityLink.document_section),
        )
        .where(Requirement.id == requirement_id)
    )
    requirement = result.unique().scalar_one_or_none()

    if requirement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    if requirement.session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    now = datetime.now(timezone.utc)

    if payload.statement is not None:
        requirement.statement = payload.statement
        requirement.edited_by = "user"
        requirement.status = "raw"
        requirement.updated_at = now

    if payload.finalization_status is not None:
        requirement.finalization_status = payload.finalization_status
        requirement.updated_at = now

    await db.commit()
    await db.refresh(requirement)

    refreshed = await db.execute(
        select(Requirement)
        .options(
            joinedload(Requirement.validation_report),
            joinedload(Requirement.classification),
            joinedload(Requirement.traceability_links).joinedload(TraceabilityLink.document_section),
        )
        .where(Requirement.id == requirement_id)
    )
    updated_requirement = refreshed.unique().scalar_one()

    return _serialize_requirement(updated_requirement)

@router.put("/requirements/{requirement_id}/finalize")
async def finalize_requirement(
    requirement_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    result = await db.execute(
        select(Requirement)
        .options(joinedload(Requirement.session), joinedload(Requirement.validation_report))
        .where(Requirement.id == requirement_id)
    )
    requirement = result.unique().scalar_one_or_none()

    if requirement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    if requirement.session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    requirement.finalization_status = "final"
    requirement.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(requirement)

    return {
        "req_id": requirement.req_id,
        "statement": requirement.statement,
        "pipeline_status": requirement.status,
        "finalization_status": requirement.finalization_status,
        "validation_report": {
            "result": requirement.validation_report.result if requirement.validation_report else None,
            "issues": requirement.validation_report.issues if requirement.validation_report else [],
            "suggestions": requirement.validation_report.suggestions if requirement.validation_report else [],
        },
    }


@router.post("/requirements/{requirement_id}/revalidate")
async def revalidate_requirement(
    requirement_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    result = await db.execute(
        select(Requirement)
        .options(joinedload(Requirement.session), joinedload(Requirement.validation_report))
        .where(Requirement.id == requirement_id)
    )
    requirement = result.unique().scalar_one_or_none()

    if requirement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    if requirement.session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    validation_results = await run_validation(
        [{"req_id": requirement.req_id, "statement": requirement.statement}]
    )
    if not validation_results:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Validation failed")

    validation_result = validation_results[0]

    existing_report = requirement.validation_report
    issues = [issue.model_dump() for issue in validation_result.issues]
    suggestions = [issue.suggestion for issue in validation_result.issues]

    if existing_report is not None:
        existing_report.result = validation_result.result
        existing_report.issues = issues
        existing_report.suggestions = suggestions
    else:
        new_report = ValidationReport(
            requirement_id=requirement.id,
            result=validation_result.result,
            issues=issues,
            suggestions=suggestions,
        )
        db.add(new_report)

    requirement.status = "validated"
    requirement.updated_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "req_id": requirement.req_id,
        "statement": requirement.statement,
        "pipeline_status": "validated",
        "validation_report": {
            "result": validation_result.result,
            "issues": issues,
            "suggestions": suggestions,
        },
    }
