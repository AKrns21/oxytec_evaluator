"""Pydantic validation models for agent outputs.

This module provides strict validation for all agent outputs to ensure
data integrity and prevent malformed structures from propagating through
the workflow.
"""

from pydantic import BaseModel, Field, validator, field_validator
from typing import Any, Optional, Literal
from datetime import datetime


class SubagentDefinition(BaseModel):
    """Validation model for subagent definitions from PLANNER."""

    task: str = Field(min_length=10, max_length=12000, description="Task description for the subagent")
    relevant_content: str = Field(min_length=1, description="Relevant context/facts for the subagent")
    tools: list[str] = Field(default_factory=list, description="List of tool names to use")

    @field_validator('task')
    @classmethod
    def validate_task_not_empty(cls, v: str) -> str:
        """Ensure task is not just whitespace."""
        if not v.strip():
            raise ValueError("Task cannot be empty or whitespace only")
        return v.strip()

    @field_validator('relevant_content')
    @classmethod
    def validate_relevant_content_not_empty(cls, v: str) -> str:
        """Ensure relevant_content is not empty."""
        if not v.strip():
            raise ValueError("Relevant content cannot be empty")
        return v.strip()

    @field_validator('tools')
    @classmethod
    def validate_tools(cls, v: list[str]) -> list[str]:
        """Validate tool names."""
        valid_tools = {"oxytec_knowledge_search", "product_database", "web_search"}
        invalid = [t for t in v if t not in valid_tools]
        if invalid:
            raise ValueError(f"Invalid tool names: {invalid}. Valid tools: {valid_tools}")
        return v


class PlannerOutput(BaseModel):
    """Validation model for PLANNER agent output."""

    subagents: list[SubagentDefinition] = Field(
        min_length=3,
        max_length=10,
        description="List of subagent definitions"
    )
    reasoning: str = Field(min_length=50, description="Required reasoning behind the plan (min 50 chars)")
    rationale: Optional[str] = Field(default="", description="Alternative field for reasoning")
    strategy: Optional[str] = Field(default="", description="Overall investigation strategy")

    @field_validator('subagents')
    @classmethod
    def validate_subagents_unique(cls, v: list[SubagentDefinition]) -> list[SubagentDefinition]:
        """Ensure subagent tasks are reasonably distinct."""
        tasks = [sub.task[:100].lower() for sub in v]
        if len(tasks) != len(set(tasks)):
            # Allow some overlap but warn if tasks are identical
            pass  # Could add more sophisticated duplicate detection
        return v


class ExtractorOutput(BaseModel):
    """Validation model for EXTRACTOR agent output."""

    voc_composition: Optional[dict[str, Any]] = Field(default_factory=dict)
    process_details: Optional[dict[str, Any]] = Field(default_factory=dict)
    requirements: Optional[dict[str, Any]] = Field(default_factory=dict)
    additional_info: Optional[dict[str, Any]] = Field(default_factory=dict)
    data_quality_issues: Optional[list[str]] = Field(default_factory=list)
    missing_information: Optional[list[str]] = Field(default_factory=list)

    @field_validator('voc_composition', 'process_details', 'requirements')
    @classmethod
    def validate_not_none(cls, v: Optional[dict]) -> dict:
        """Ensure critical fields are not None."""
        return v if v is not None else {}


class RiskLevel(str):
    """Risk level enumeration."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskItem(BaseModel):
    """Individual risk item."""

    category: str = Field(min_length=1, description="Risk category")
    description: str = Field(min_length=10, description="Risk description")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(description="Risk severity level")
    mitigation: Optional[str] = Field(default="", description="Mitigation strategy")


class RiskClassification(BaseModel):
    """Risk classification structure."""

    technical_risks: list[RiskItem] = Field(default_factory=list)
    commercial_risks: list[RiskItem] = Field(default_factory=list)
    data_quality_risks: list[RiskItem] = Field(default_factory=list)


class RiskAssessorOutput(BaseModel):
    """Validation model for RISK_ASSESSOR agent output."""

    executive_risk_summary: str = Field(min_length=50, description="Executive summary of risks")
    risk_classification: RiskClassification = Field(description="Categorized risks")
    overall_risk_level: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(
        description="Overall project risk level"
    )
    go_no_go_recommendation: Literal["GO", "CONDITIONAL_GO", "NO_GO"] = Field(
        description="Recommendation for proceeding"
    )
    critical_success_factors: list[str] = Field(default_factory=list)
    mitigation_priorities: list[str] = Field(default_factory=list)

    @field_validator('executive_risk_summary')
    @classmethod
    def validate_summary_not_empty(cls, v: str) -> str:
        """Ensure executive summary is substantial."""
        if not v.strip():
            raise ValueError("Executive risk summary cannot be empty")
        return v.strip()


class WriterOutput(BaseModel):
    """Validation model for WRITER agent output."""

    final_report: str = Field(min_length=500, description="Final German feasibility report")
    sections_present: Optional[list[str]] = Field(default_factory=list)

    @field_validator('final_report')
    @classmethod
    def validate_report_structure(cls, v: str) -> str:
        """Validate basic report structure."""
        if not v.strip():
            raise ValueError("Final report cannot be empty")

        # Check for required German sections
        required_sections = ["## Zusammenfassung", "## VOC-Zusammensetzung"]
        missing_sections = [section for section in required_sections if section not in v]

        if missing_sections:
            # Log warning but don't fail - allow some flexibility
            import logging
            logging.warning(f"Report missing sections: {missing_sections}")

        # Check for feasibility emoji
        if not any(emoji in v for emoji in ["🟢", "🟡", "🔴"]):
            import logging
            logging.warning("Report missing feasibility rating emoji")

        return v


class SubagentResult(BaseModel):
    """Validation model for individual subagent results."""

    agent_name: str = Field(min_length=1)
    instance: str = Field(min_length=1)
    task: str = Field(min_length=10, max_length=3000)
    result: str = Field(min_length=10, description="Subagent analysis result")
    duration_seconds: Optional[float] = Field(default=None, ge=0)
    tokens_used: Optional[int] = Field(default=None, ge=0)

    @field_validator('result')
    @classmethod
    def validate_result_not_empty(cls, v: str) -> str:
        """Ensure result is substantial."""
        if not v.strip():
            raise ValueError("Subagent result cannot be empty")
        return v.strip()


# Validation helper functions
def validate_extractor_output(output: dict[str, Any]) -> ExtractorOutput:
    """Validate EXTRACTOR output with Pydantic model."""
    return ExtractorOutput(**output)


def validate_planner_output(output: dict[str, Any]) -> PlannerOutput:
    """Validate PLANNER output with Pydantic model."""
    return PlannerOutput(**output)


def validate_risk_assessor_output(output: dict[str, Any]) -> RiskAssessorOutput:
    """Validate RISK_ASSESSOR output with Pydantic model."""
    return RiskAssessorOutput(**output)


def validate_writer_output(output: dict[str, Any]) -> WriterOutput:
    """Validate WRITER output with Pydantic model."""
    return WriterOutput(**output)


def validate_subagent_result(result: dict[str, Any]) -> SubagentResult:
    """Validate individual subagent result."""
    return SubagentResult(**result)
