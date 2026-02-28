from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentScope(StrictBaseModel):
    software_overview: str = Field(..., description="Overview of the software and its role")
    targeted_users: List[str] = Field(..., description="Targeted users of the system")
    integrated_system: str = Field(..., description="System where the software is integrated")
    high_level_description: str = Field(..., description="High-level product description")


class RegulatoryReferences(StrictBaseModel):
    regulatory_standards: List[str] = Field(..., description="Regulatory standards and versions (e.g. IEC 62304 v2.0)")
    internal_qms_sop_references: List[str] = Field(..., description="Internal QMS SOP references")
    design_control_procedures: List[str] = Field(..., description="Design control procedures referenced")


class AcronymsDefinitions(StrictBaseModel):
    term: str = Field(..., description="Term or acronym")
    definition: str = Field(..., description="Definition or expansion")


class IntendedUse(StrictBaseModel):
    intended_use_statement: str = Field(..., description="Clear statement of why the device exists")
    clinical_indications: List[str] = Field(..., description="Clinical indications for use")
    contraindications: Optional[List[str]] = Field(default=None, description="Known contraindications")


class TargetPopulationEnvironment(StrictBaseModel):
    patient_types: List[str] = Field(..., description="Patient types the device targets")
    clinical_settings: List[str] = Field(..., description="Clinical settings (ICU, ER, home, etc.)")
    user_profiles: List[str] = Field(..., description="User profiles (clinician, nurse, patient)")


class HealthcareIntroductionSchema(StrictBaseModel):
    section_number: str = Field(default="1", description="Section number")
    section_title: str = Field(default="Introduction & Purpose", description="Section title")
    document_scope: DocumentScope
    regulatory_references: RegulatoryReferences
    acronyms_and_definitions: List[AcronymsDefinitions]
    intended_use: IntendedUse
    target_population_environment: TargetPopulationEnvironment