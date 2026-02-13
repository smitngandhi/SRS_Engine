from typing import List, Optional, Literal
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# SECTION 1: INTRODUCTION & PURPOSE
# ============================================================================

class DocumentScopeSection(StrictBaseModel):
    """
    Render as: PARAGRAPH
    Provides narrative overview of the software system
    """
    title: str = Field(default="1.1 Document Scope")
    software_overview: str = Field(..., description="High-level description of the medical device software")
    software_role: str = Field(..., description="How this software fits into the overall medical device")
    targeted_users: List[str] = Field(..., description="Types of users (clinicians, patients, technicians)")
    system_integration: str = Field(..., description="Where and how the software integrates with other systems")
    product_description: str = Field(..., description="Detailed product description including key capabilities")
    
    # RENDER NOTE: Display as flowing paragraphs with user list as bullets


class RegulatoryStandard(StrictBaseModel):
    """Table row for regulatory references"""
    standard_name: str = Field(..., description="e.g., IEC 62304, ISO 13485")
    version: str = Field(..., description="Standard version number")
    applicability: str = Field(..., description="How this standard applies to the software")
    section_reference: Optional[str] = Field(None, description="Specific sections that apply")


class InternalReference(StrictBaseModel):
    """Table row for internal SOP/procedure references"""
    document_id: str = Field(..., description="Internal document identifier")
    document_title: str = Field(..., description="Title of the internal document")
    document_type: str = Field(..., description="SOP, Work Instruction, Procedure, etc.")
    relevance: str = Field(..., description="Why this document is referenced")


class RegulatoryReferencesSection(StrictBaseModel):
    """
    Render as: TABLE
    Critical for audit trail and compliance verification
    """
    title: str = Field(default="1.2 Regulatory & Standards References")
    regulatory_standards: List[RegulatoryStandard] = Field(..., description="Applicable regulatory standards")
    internal_references: List[InternalReference] = Field(..., description="Internal QMS documents")
    
    # TABLE HEADERS: Standard Name | Version | Applicability | Section Reference
    # TABLE HEADERS: Doc ID | Title | Type | Relevance


class AcronymDefinition(StrictBaseModel):
    """Table row for acronyms and definitions"""
    term: str = Field(..., description="Acronym or abbreviation")
    definition: str = Field(..., description="Full expansion and meaning")
    context: Optional[str] = Field(None, description="Where this term is primarily used")


class AcronymsSection(StrictBaseModel):
    """
    Render as: TABLE
    Essential glossary for unambiguous communication
    """
    title: str = Field(default="1.3 Acronyms, Definitions, and Abbreviations")
    items: List[AcronymDefinition] = Field(..., description="List of all acronyms used in document")
    
    # TABLE HEADERS: Term | Definition | Context


class IntendedUseSection(StrictBaseModel):
    """
    Render as: PARAGRAPH
    Critical for regulatory classification and risk analysis
    """
    title: str = Field(default="1.4 Intended Use & Indications")
    clinical_purpose: str = Field(..., description="Medical purpose and clinical application")
    indications_for_use: str = Field(..., description="Specific medical indications")
    contraindications: List[str] = Field(default_factory=list, description="When NOT to use the device")
    intended_medical_benefit: str = Field(..., description="Expected patient/clinical benefit")
    
    # RENDER NOTE: Main text as paragraphs, contraindications as bulleted list


class UserProfile(StrictBaseModel):
    """Individual user type profile"""
    user_type: str = Field(..., description="e.g., Physician, Nurse, Patient, Technician")
    skill_level: str = Field(..., description="Expected technical competency")
    training_required: str = Field(..., description="Required training or certification")


class TargetPopulationSection(StrictBaseModel):
    """
    Render as: MIXED (Bullets + Paragraph)
    Important for usability and risk assessment
    """
    title: str = Field(default="1.5 Target Population & Environment")
    patient_demographics: str = Field(..., description="Age range, conditions, etc.")
    clinical_settings: List[str] = Field(..., description="Hospital, clinic, home use, etc.")
    user_profiles: List[UserProfile] = Field(..., description="Different types of users")
    environmental_conditions: List[str] = Field(..., description="Temperature, humidity, electrical requirements")
    
    # RENDER NOTE: Demographics as paragraph, settings/conditions as bullets, profiles as sub-bullets


class IntroductionPurposeSection(StrictBaseModel):
    """Complete Section 1: Introduction & Purpose"""
    section_title: str = Field(default="1. INTRODUCTION & PURPOSE")
    document_scope: DocumentScopeSection
    regulatory_references: RegulatoryReferencesSection
    acronyms: AcronymsSection
    intended_use: IntendedUseSection
    target_population: TargetPopulationSection