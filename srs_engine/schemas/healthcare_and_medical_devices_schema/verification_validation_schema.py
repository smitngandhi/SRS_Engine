from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TestScope(StrictBaseModel):
    test_type: Literal["Unit", "Integration", "System", "Validation", "Regression"] = Field(
        ..., description="Type of test planned"
    )
    description: str = Field(..., description="What this test type covers")
    responsible_party: Optional[str] = Field(default=None, description="Who performs this test (dev, QA, independent)")


class AcceptanceCriteria(StrictBaseModel):
    req_id: str = Field(..., description="Requirement ID this acceptance criterion maps to")
    pass_condition: str = Field(..., description="Condition that must be true for the test to pass")
    fail_condition: str = Field(..., description="Condition that indicates test failure")


class TestMethod(StrictBaseModel):
    test_id: str = Field(..., description="Unique test method ID (e.g. TM-001)")
    linked_req_id: str = Field(..., description="Requirement ID being tested")
    method: Literal["Analysis", "Inspection", "Demonstration", "Test"] = Field(
        ..., description="Verification method per IEC 62304"
    )
    protocol_reference: Optional[str] = Field(default=None, description="Reference to test protocol document")
    tool_used: Optional[str] = Field(default=None, description="Tool or framework used for testing")


class HealthcareVerificationValidationSchema(StrictBaseModel):
    section_number: str = Field(default="7", description="Section number")
    section_title: str = Field(default="Verification & Validation Planning", description="Section title")
    test_scope: List[TestScope]
    acceptance_criteria: List[AcceptanceCriteria]
    test_methods: List[TestMethod]