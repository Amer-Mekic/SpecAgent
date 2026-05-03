from __future__ import annotations

import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.chat_message import ChatMessage
from app.models.requirement import Requirement
from app.models.session import Session
from app.models.user import User

router = APIRouter(tags=["chat"])

REVISED_PATTERN = re.compile(r"REVISED:\s*(.+)", re.IGNORECASE)


class ChatRequest(BaseModel):
    message: str
    requirement_id: UUID | None = None


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


def _extract_revised_statement(content: str) -> str | None:
    for line in content.splitlines():
        match = REVISED_PATTERN.search(line)
        if match:
            revised_statement = match.group(1).strip()
            if revised_statement:
                return revised_statement
    return None


@router.post("/chat/{session_id}")
async def chat_with_assistant(
    session_id: UUID,
    payload: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    await _get_owned_session(session_id, db, current_user)

    requirements_result = await db.execute(
        select(Requirement)
        .options(joinedload(Requirement.validation_report))
        .where(Requirement.session_id == session_id)
        .order_by(Requirement.req_id.asc())
    )
    requirements = list(requirements_result.scalars().all())

    requirements_lines = [f"- {req.req_id}: {req.statement}" for req in requirements]
    requirements_list = "\n".join(requirements_lines) if requirements_lines else "- No requirements extracted yet."

    focused_requirement: Requirement | None = None
    if payload.requirement_id is not None:
        focused_result = await db.execute(
            select(Requirement)
            .options(joinedload(Requirement.validation_report))
            .where(Requirement.id == payload.requirement_id)
        )
        focused_requirement = focused_result.unique().scalar_one_or_none()
        if focused_requirement is None or focused_requirement.session_id != session_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")

    system_prompt = (
        "You are a requirements engineering assistant helping to refine software requirements. "
        "The user has uploaded a document and the system has extracted the following requirements:\n\n"
        f"{requirements_list}\n\n"
        "Help the user refine, clarify, split, or improve requirements. "
        "When suggesting a revised requirement statement, always format it exactly as:\n"
        "REVISED: <the complete new requirement statement>\n"
        "so the user can apply it with one click."
    )

    if focused_requirement is not None:
        validation_result = "not validated"
        issues: list[object] = []
        if focused_requirement.validation_report is not None:
            validation_result = focused_requirement.validation_report.result
            issues = focused_requirement.validation_report.issues or []

        system_prompt += (
            "\n\n"
            f"The user is currently focused on {focused_requirement.req_id}:\n"
            f"{focused_requirement.statement}\n"
            f"Validation status: {validation_result}\n"
            f"Issues: {issues}"
        )

    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    history_messages = list(history_result.scalars().all())

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend({"role": msg.role, "content": msg.content} for msg in history_messages)
    messages.append({"role": "user", "content": payload.message})

    client = OpenAI(
        base_url=settings.NVIDIA_BASE_URL,
        api_key=settings.NVIDIA_API_KEY,
    )
    response = client.chat.completions.create(
        model=settings.NVIDIA_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=1024,
        stream=False,
    )

    assistant_content = response.choices[0].message.content or ""

    user_message = ChatMessage(
        session_id=session_id,
        requirement_id=payload.requirement_id,
        role="user",
        content=payload.message,
    )
    assistant_message = ChatMessage(
        session_id=session_id,
        requirement_id=payload.requirement_id,
        role="assistant",
        content=assistant_content,
    )

    db.add(user_message)
    db.add(assistant_message)
    await db.commit()

    revised_statement = _extract_revised_statement(assistant_content)

    return {
        "response": assistant_content,
        "revised_statement": revised_statement,
        "requirement_id": str(payload.requirement_id) if payload.requirement_id is not None else None,
    }
