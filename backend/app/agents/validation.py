from pydantic_ai import Agent

from app.core.llm import get_nvidia_model
from app.schemas.requirement import ValidationResult, ValidationResultWrapper

_model = get_nvidia_model()

validation_agent = Agent(
    model=_model,
    output_type=ValidationResultWrapper,
    model_settings={"temperature": 0.1},
    system_prompt="""
You are a software requirements validation agent.

Your task is to validate software requirements according to
ISO/IEC/IEEE 29148 and the EARS methodology.

Evaluate each requirement against these five criteria:

1. Ambiguity - vague, subjective, or non-measurable terms
2. Incompleteness - missing actor, trigger, condition, or constraint
3. Inconsistency - contradicts other requirements in context
4. Verifiability - cannot be objectively tested
5. Atomicity - describes more than one independent function

Classification rules:
- pass: satisfies all criteria, no changes needed
- flagged: has issues but can be improved
- rejected: completely unusable

Be conservative: if in doubt, result should be pass.
Only flag SERIOUS problems. Do not flag standard domain terms.
""",
)


async def run_validation(requirements: list[dict]) -> list[ValidationResult]:
    statements_context = "\n".join(
        f"- {req['req_id']}: {req['statement']}" for req in requirements
    )
    prompt = (
        f"Validate each of the following requirements:\n\n"
        f"{statements_context}\n\n"
        f"Return a validation result for every requirement listed."
    )

    result = await validation_agent.run(prompt)
    outputs = result.output.validations

    # Align requirement_ids in order if model didn't set them correctly
    for i, output in enumerate(outputs):
        if i < len(requirements):
            output.requirement_id = requirements[i]["req_id"]

    return outputs