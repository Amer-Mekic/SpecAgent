from pydantic_ai import Agent

from app.core.llm import get_nvidia_model
from app.schemas.requirement import ClassificationResult

_model = get_nvidia_model()

classification_agent = Agent(
    model=_model,
    output_type=ClassificationResult,
    model_settings={"temperature": 0.1},
    system_prompt="""
You are a software requirements classification specialist.

Classify each requirement as exactly one of:

FUNCTIONAL - describes what the system shall DO. Specifies
a behavior, feature, or capability. Usually follows the
pattern: The system shall [action] [object] [condition].
Examples: user authentication, data export, search,
file upload, notification sending.

NON-FUNCTIONAL - describes a quality the system MUST HAVE.
Does not describe behavior but constrains how the system
performs.
Sub-categories:
  performance   - speed, throughput, latency, capacity
  security      - authentication, authorization, encryption,
                  data protection
  usability     - ease of use, accessibility, learnability
  reliability   - uptime, fault tolerance, error recovery
  maintainability - modularity, testability, code quality
  portability   - browser support, OS compatibility,
                  deployment environments

When in doubt between functional and non-functional,
ask: does this describe a system action or a system
quality? Actions are functional. Qualities are
non-functional.
""",
)


async def run_classification(requirements: list[dict]) -> list[ClassificationResult]:
    results: list[ClassificationResult] = []

    for req in requirements:
        prompt = (
            f"Requirement ID: {req['req_id']}\n"
            f"Requirement Statement: {req['statement']}"
        )
        result = await classification_agent.run(prompt)
        output = result.output

        # Guarantee output mapping remains aligned with orchestrator IDs.
        output.requirement_id = req["req_id"]
        results.append(output)

    return results
