from __future__ import annotations

from uuid import UUID

from pgvector.sqlalchemy import Vector
from sentence_transformers import SentenceTransformer
from sqlalchemy import cast, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_section import DocumentSection
from app.models.requirement import Requirement
from app.models.traceability_link import TraceabilityLink

_model = SentenceTransformer("all-MiniLM-L6-v2")


async def run_traceability(
    session_id: UUID,
    db: AsyncSession,
    top_k: int = 3,
) -> None:
    req_result = await db.execute(
        select(Requirement).where(Requirement.session_id == session_id)
    )
    requirements = req_result.scalars().all()
    if not requirements:
        await db.commit()
        return

    all_links: list[TraceabilityLink] = []

    for requirement in requirements:
        req_embedding = _model.encode(requirement.statement).tolist()

        distance_expr = DocumentSection.embedding.op("<=>")(
            cast(req_embedding, Vector(384))
        )
        similarity_expr = (literal(1.0) - distance_expr).label("similarity_score")

        section_result = await db.execute(
            select(
                DocumentSection.id,
                DocumentSection.source_identifier,
                similarity_expr,
            )
            .where(DocumentSection.session_id == session_id)
            .order_by(distance_expr)
            .limit(top_k)
        )

        for section_id, _source_identifier, similarity_score in section_result.all():
            all_links.append(
                TraceabilityLink(
                    requirement_id=requirement.id,
                    section_id=section_id,
                    similarity_score=float(similarity_score),
                )
            )

    if all_links:
        db.add_all(all_links)
    await db.commit()
