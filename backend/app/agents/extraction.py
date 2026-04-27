from pydantic_ai import Agent

from app.core.llm import get_nvidia_model
from app.schemas.requirement import ExtractionResult

_model = get_nvidia_model()

extraction_agent = Agent(
    model=_model,
    output_type=ExtractionResult,
    model_settings={"temperature": 0.1},
    system_prompt="""
You are a software requirements extraction specialist.

Your task is to identify software requirements from the
provided text chunk. A software requirement describes
what a system SHALL do (functional) or a quality the
system MUST have (non-functional).

EXTRACT if the statement:
- Describes a system capability or behavior
- Describes a system quality attribute (performance,
  security, usability, reliability)
- Contains modal verbs: shall, must, should, will,
  needs to, has to

DO NOT EXTRACT:
- General descriptions or background context
- Opinions or preferences without system obligation
- Questions or issues raised without a resolution
- Duplicate statements already captured

Return every extracted requirement as a complete,
standalone statement. If the text contains no
requirements, return an empty list.
""",
)


async def run_extraction(chunks: list[str]) -> list[dict]:
    unique_statements: set[str] = set()
    extracted: list[dict] = []

    for chunk in chunks:
        result = await extraction_agent.run(chunk)
        for req in result.output.requirements:
            statement = req.statement.strip()
            if not statement or statement in unique_statements:
                continue

            unique_statements.add(statement)
            extracted.append(
                {
                    "statement": statement,
                    "confidence": float(req.confidence),
                    "source_chunk": req.source_chunk,
                }
            )

    for idx, req in enumerate(extracted, start=1):
        req["req_id"] = f"REQ-{idx:03d}"

    return extracted
