from pydantic import BaseModel, Field


class RawRequirement(BaseModel):
    statement: str = Field(
        description=(
            "The complete requirement statement extracted verbatim or minimally "
            "cleaned from the text. Must describe what a system shall do or a "
            "quality it must have."
        )
    )
    confidence: float = Field(
        description=(
            "Confidence that this is a genuine software requirement. "
            "Between 0.0 and 1.0."
        )
    )
    source_chunk: str = Field(
        description="The exact text fragment this requirement was extracted from."
    )


class ExtractionResult(BaseModel):
    requirements: list[RawRequirement] = Field(
        description=(
            "All software requirements identified in the provided text chunk. "
            "Empty list if none found."
        )
    )


class ValidationIssue(BaseModel):
    issue_type: str = Field(
        description=(
            "Category of the issue. One of: ambiguity | incompleteness | "
            "inconsistency | unverifiable | non-atomic"
        )
    )
    description: str = Field(
        description="Specific explanation of the issue found in this requirement."
    )
    suggestion: str = Field(
        description="Concrete rewrite suggestion to fix this issue."
    )


class ValidationResult(BaseModel):
    requirement_id: str = Field(
        description=(
            "The req_id of the requirement being validated, e.g. REQ-001"
        )
    )
    result: str = Field(
        description="Overall validation outcome. One of: pass | flagged | rejected"
    )
    issues: list[ValidationIssue] = Field(
        description="List of detected issues. Empty if result is pass."
    )
    improved_statement: str | None = Field(
        description=(
            "A rewritten version of the requirement that fixes all detected "
            "issues. None if result is pass."
        )
    )


class ClassificationResult(BaseModel):
    requirement_id: str = Field(
        description=(
            "The req_id of the requirement being classified, e.g. REQ-001"
        )
    )
    type: str = Field(
        description="Requirement category. One of: functional | non-functional"
    )
    sub_category: str | None = Field(
        description=(
            "For non-functional only. One of: performance | security | "
            "usability | reliability | maintainability | portability. "
            "None for functional."
        )
    )
    confidence: float = Field(
        description="Classification confidence between 0.0 and 1.0."
    )
    reasoning: str = Field(
        description="One sentence explaining why this classification was chosen."
    )
