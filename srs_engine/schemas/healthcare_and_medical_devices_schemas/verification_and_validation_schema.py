from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TestScopeSection(StrictBaseModel):
    """
    Render as: BULLETS
    Overview of testing strategy
    """
    title: str = Field(default="7.1 Test Scope")
    testing_overview: str = Field(..., description="Overall V&V approach")
    test_levels: List[str] = Field(..., description="Unit, Integration, System, Acceptance")
    test_types: List[str] = Field(..., description="Functional, Performance, Security, Usability")
    test_environment: str = Field(..., description="Where testing is conducted")
    test_data_strategy: str = Field(..., description="Real vs synthetic data approach")
    
    # RENDER NOTE: Overview as paragraph, levels and types as bullets


class AcceptanceCriterion(StrictBaseModel):
    """Acceptance criteria for requirement - TABLE ROW"""
    req_id: str = Field(..., description="Related requirement ID")
    test_objective: str = Field(..., description="What is being tested")
    pass_criteria: str = Field(..., description="Conditions for passing")
    fail_criteria: str = Field(..., description="Conditions for failing")
    measurement_method: str = Field(..., description="How success is measured")


class AcceptanceCriteriaSection(StrictBaseModel):
    """
    Render as: TABLE
    Clear pass/fail definitions
    """
    title: str = Field(default="7.2 Acceptance Criteria")
    overview: str = Field(..., description="How acceptance is determined")
    criteria: List[AcceptanceCriterion] = Field(..., description="All acceptance criteria")
    
    # TABLE HEADERS: Req ID | Test Objective | Pass Criteria | Fail Criteria | Measurement


class TestMethod(StrictBaseModel):
    """Test method and protocol - TABLE ROW"""
    req_id: str = Field(..., description="Related requirement ID")
    test_id: str = Field(..., description="Unique test ID (TC-001)")
    test_method: Literal["Test", "Analysis", "Inspection", "Demonstration"] = Field(..., description="Verification method")
    test_type: str = Field(..., description="Unit, Integration, System, etc.")
    test_description: str = Field(..., description="What the test does")
    protocol_reference: str = Field(..., description="Test protocol document reference")
    responsible_role: str = Field(..., description="Who executes this test")


class TestMethodsSection(StrictBaseModel):
    """
    Render as: TABLE
    Links requirements to specific tests
    """
    title: str = Field(default="7.3 Test Methods & Protocols")
    overview: str = Field(..., description="Test execution approach")
    methods: List[TestMethod] = Field(..., description="All test methods")
    
    # TABLE HEADERS: Req ID | Test ID | Method | Type | Description | Protocol | Responsible


class VerificationValidationSection(StrictBaseModel):
    """Complete Section 7: Verification & Validation Planning"""
    section_title: str = Field(default="7. VERIFICATION & VALIDATION PLANNING")
    test_scope: TestScopeSection
    acceptance_criteria: AcceptanceCriteriaSection
    test_methods: TestMethodsSection