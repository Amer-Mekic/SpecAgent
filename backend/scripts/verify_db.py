from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select, text

from app.core.database import SessionLocal, enable_pgvector
from app.models import Requirement, Session, User

EXPECTED_TABLES = {
    "user",
    "session",
    "document_section",
    "requirement",
    "validation_report",
    "classification",
    "traceability_link",
    "export",
    "chat_message",
}


async def verify_tables_exist() -> None:
    async with SessionLocal() as db:
        result = await db.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
        )
        existing_tables = {row[0] for row in result.fetchall()}

    missing_tables = EXPECTED_TABLES - existing_tables
    if missing_tables:
        raise RuntimeError(f"Missing expected tables: {sorted(missing_tables)}")


async def verify_vector_extension() -> None:
    async with SessionLocal() as db:
        result = await db.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        extension = result.scalar_one_or_none()

    if extension != "vector":
        raise RuntimeError("pgvector extension is not enabled")


async def verify_insert_read_delete() -> None:
    test_suffix = uuid.uuid4().hex[:8]

    async with SessionLocal() as db:
        user = User(
            email=f"verify_{test_suffix}@example.com",
            name="verify-user",
            password="$2b$12$examplehashedpasswordforverificationonly",
        )
        db.add(user)
        await db.flush()

        session = Session(
            user_id=user.id,
            document_name="verify_document.txt",
            document_hash=f"{test_suffix}".ljust(64, "a"),
            status="pending",
        )
        db.add(session)
        await db.flush()

        requirement = Requirement(
            session_id=session.id,
            req_id="REQ-VERIFY-001",
            statement="The system shall support database verification.",
            status="raw",
            finalization_status="draft",
            edited_by="system",
        )
        db.add(requirement)
        await db.commit()

        saved_user = await db.scalar(select(User).where(User.id == user.id))
        saved_session = await db.scalar(select(Session).where(Session.id == session.id))
        saved_requirement = await db.scalar(select(Requirement).where(Requirement.id == requirement.id))

        print(saved_user)
        print(saved_session)
        print(saved_requirement)

        await db.delete(saved_user)
        await db.commit()


async def main() -> None:
    await enable_pgvector()
    await verify_tables_exist()
    await verify_vector_extension()
    await verify_insert_read_delete()
    print("Database setup verified successfully")


if __name__ == "__main__":
    asyncio.run(main())
