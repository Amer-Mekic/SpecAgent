from pydantic_ai import Agent

from app.core.llm import get_nvidia_model
from app.schemas.requirement import ClassificationResult, ClassificationResultWrapper

_model = get_nvidia_model()

classification_agent = Agent(
    model=_model,
    output_type=ClassificationResultWrapper,
    model_settings={"temperature": 0.1},
    system_prompt="""
You are a software requirements classification specialist.

Classify each requirement as exactly one of:

FUNCTIONAL - describes what the system shall DO. Specifies
a behavior, feature, or capability.

NON-FUNCTIONAL - describes a quality the system MUST HAVE.
Sub-categories:
  performance   - speed, throughput, latency, capacity
  security      - authentication, authorization, encryption
  usability     - ease of use, accessibility, learnability
  reliability   - uptime, fault tolerance, error recovery
  maintainability - modularity, testability, code quality
  portability   - browser support, OS compatibility

When in doubt: actions are functional, qualities are non-functional.
""",
)


async def run_classification(requirements: list[dict]) -> list[ClassificationResult]:
    statements_context = "\n".join(
        f"- {req['req_id']}: {req['statement']}" for req in requirements
    )
    prompt = (
        f"Classify each of the following requirements:\n\n"
        f"{statements_context}\n\n"
        f"Return a classification result for every requirement listed."
    )

    result = await classification_agent.run(prompt)
    outputs = result.output.classifications

    for i, output in enumerate(outputs):
        if i < len(requirements):
            output.requirement_id = requirements[i]["req_id"]

    return outputs