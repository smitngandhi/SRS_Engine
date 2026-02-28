from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ParentalConsentMechanism(StrictBaseModel):
    consent_method: str = Field(..., description="Consent collection method (online form, paper, email verification)")
    verifiable: bool = Field(..., description="Whether consent is verifiable (COPPA requirement)")
    consent_withdrawal_supported: bool = Field(..., description="Whether parents can withdraw consent")


class DataRetentionPolicy(StrictBaseModel):
    data_category: str = Field(..., description="Category of student data (grades, attendance, behavioral, biometric)")
    retention_period: str = Field(..., description="Retention period (e.g. 3 years after graduation)")
    deletion_method: str = Field(..., description="Method for secure deletion after retention period")


class EducationStudentDataPrivacySchema(StrictBaseModel):
    section_number: str = Field(default="2", description="Section number")
    section_title: str = Field(default="Student Data Privacy (FERPA/COPPA)", description="Section title")
    ferpa_applicable: bool = Field(..., description="Whether FERPA applies (US educational institution)")
    coppa_applicable: bool = Field(..., description="Whether COPPA applies (children under 13)")
    data_minimization_policy: str = Field(..., description="Description of data minimization approach")
    parental_consent: Optional[ParentalConsentMechanism] = Field(default=None)
    student_record_access_controls: List[str] = Field(
        ..., description="Access controls for student records (role-based, consent-based)"
    )
    data_retention_policies: List[DataRetentionPolicy]
    third_party_sharing_policy: str = Field(..., description="Policy on sharing student data with third parties")
