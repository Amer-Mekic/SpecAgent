from __future__ import annotations

import asyncio
import time
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.main import app
from app.models.requirement import Requirement
from app.models.session import Session
from app.models.traceability_link import TraceabilityLink
from app.core.config import settings


@pytest.mark.asyncio
async def test_pipeline_end_to_end() -> None:
    if not settings.NVIDIA_API_KEY:
        pytest.skip("NVIDIA_API_KEY is not configured")

    email = f"pipeline-{uuid.uuid4().hex[:10]}@example.com"
    password = "Secret123!"
    requirements_text = """The system shall require users to authenticate with email and password.
The system shall encrypt all personal data at rest using AES-256.
The system shall return search results in under 2 seconds for 95% of requests.
"""

    timeout_seconds = 500
    poll_interval_seconds = 3
    started = time.monotonic()
    final_status: str | None = None
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        timeout=60.0,
    ) as client:
        register_response = await client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "name": "Pipeline Test"},
        )
        assert register_response.status_code == 200

        login_response = await client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        upload_response = await client.post(
            "/api/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={
                "file": (
                    "pipeline_requirements.txt",
                    requirements_text.encode("utf-8"),
                    "text/plain",
                )
            },
        )
        assert upload_response.status_code == 200
        session_id = upload_response.json()["session_id"]
        print(f"session_id={session_id}")
        while time.monotonic() - started < timeout_seconds:
            async with SessionLocal() as db:
                result = await db.execute(select(Session).where(Session.id == session_id))
                session = result.scalar_one_or_none()
                assert session is not None
                final_status = session.status

            print(f"pipeline_status={final_status}")
            if final_status in {"complete", "failed"}:
                break

            await asyncio.sleep(poll_interval_seconds)

    # timeout_seconds = 500
    # poll_interval_seconds = 3
    # started = time.monotonic()
    # final_status: str | None = None

    # while time.monotonic() - started < timeout_seconds:
    #     async with SessionLocal() as db:
    #         result = await db.execute(select(Session).where(Session.id == session_id))
    #         session = result.scalar_one_or_none()
    #         assert session is not None
    #         final_status = session.status

    #     print(f"pipeline_status={final_status}")
    #     if final_status in {"complete", "failed"}:
    #         break

    #     await asyncio.sleep(poll_interval_seconds)

    assert final_status == "complete", f"Pipeline did not complete successfully. Final status: {final_status}"

    async with SessionLocal() as db:
        req_result = await db.execute(
            select(Requirement)
            .options(
                selectinload(Requirement.validation_report),
                selectinload(Requirement.classification),
                selectinload(Requirement.traceability_links),
            )
            .where(Requirement.session_id == session_id)
            .order_by(Requirement.req_id.asc())
        )
        requirements = list(req_result.scalars().all())

        link_result = await db.execute(
            select(TraceabilityLink)
            .join(Requirement, TraceabilityLink.requirement_id == Requirement.id)
            .where(Requirement.session_id == session_id)
        )
        links = list(link_result.scalars().all())

    print("\nExtracted requirements:")
    for req in requirements:
        validation = req.validation_report.result if req.validation_report else "missing"
        classification = req.classification.type if req.classification else "missing"
        sub_category = req.classification.sub_category if req.classification else None
        print(f"- {req.req_id}: {req.statement}")
        print(f"  validation={validation}")
        print(f"  classification={classification}, sub_category={sub_category}")

    print("\nTraceability links:")
    for link in links:
        print(
            "- requirement_id="
            f"{link.requirement_id} "
            f"section_id={link.section_id} "
            f"similarity_score={link.similarity_score:.4f}"
        )

    extraction_pass = len(requirements) > 0
    validation_pass = all(req.validation_report is not None for req in requirements) if requirements else False
    classification_pass = all(req.classification is not None for req in requirements) if requirements else False
    traceability_pass = len(links) > 0

    print("\nStage results:")
    print(f"- extraction: {'PASS' if extraction_pass else 'FAIL'}")
    print(f"- validation: {'PASS' if validation_pass else 'FAIL'}")
    print(f"- classification: {'PASS' if classification_pass else 'FAIL'}")
    print(f"- traceability: {'PASS' if traceability_pass else 'FAIL'}")

    assert extraction_pass
    assert validation_pass
    assert classification_pass
    assert traceability_pass
