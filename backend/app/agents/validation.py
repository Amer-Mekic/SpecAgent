from pydantic_ai import Agent

from app.core.llm import get_nvidia_model
from app.schemas.requirement import ValidationResult

_model = get_nvidia_model()

validation_agent = Agent(
    model=_model,
   output_type=ValidationResult,
    model_settings={"temperature": 0.1},
    system_prompt="""
You are a software requirements quality analyst following
ISO/IEC/IEEE 29148 and the EARS methodology.

Validate the provided requirement against these five criteria:

1. AMBIGUITY - Contains vague or unmeasurable terms such as
   fast, user-friendly, secure, efficient, easy, reliable,
   flexible, scalable (without specific thresholds). Flag
   these and suggest measurable replacements.

2. INCOMPLETENESS - Missing necessary information such as
   trigger conditions, actor, system response, or measurable
   threshold. Flag and suggest what is missing.

3. INCONSISTENCY - Contradicts other requirements provided
   in context. Flag and identify the conflict.

4. UNVERIFIABLE - Cannot be objectively tested. Flag and
   suggest how to make it testable.

5. ATOMICITY - Describes more than one independent
   requirement. Flag and suggest how to split it.

result values:
  pass     - no issues found, requirement is well-formed
  flagged  - one or more issues found but requirement is
             salvageable with suggested improvements
  rejected - requirement is too vague or contradictory
             to be useful in its current form

IMPORTANT: A flagged requirement still proceeds through
the pipeline. Flagging is metadata for the user, not a
blocker. Only reject requirements that are completely
unusable.
""",
)


async def run_validation(requirements: list[dict]) -> list[ValidationResult]:
    statements_context = "\n".join(
        f"- {req['req_id']}: {req['statement']}" for req in requirements
    )
    results: list[ValidationResult] = []

    for req in requirements:
        prompt = (
            f"Requirement ID: {req['req_id']}\n"
            f"Requirement Statement: {req['statement']}\n\n"
            f"Other requirements context:\n{statements_context}"
        )
        result = await validation_agent.run(prompt)
        output = result.output

        # Guarantee output mapping remains aligned with orchestrator IDs.
        output.requirement_id = req["req_id"]
        results.append(output)

    return results
