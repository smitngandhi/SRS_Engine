from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class HazardIdentification(StrictBaseModel):
    """Individual hazard - TABLE ROW"""
    hazard_id: str = Field(..., description="Unique hazard ID (HAZ-001)")
    hazard_description: str = Field(..., description="What could go wrong")
    hazardous_situation: str = Field(..., description="Circumstances leading to harm")
    potential_harm: str = Field(..., description="Type of injury or damage")
    severity: Literal["Catastrophic", "Critical", "Serious", "Minor", "Negligible"] = Field(..., description="Harm severity")
    probability: Literal["Frequent", "Probable", "Occasional", "Remote", "Improbable"] = Field(..., description="Likelihood of occurrence")
    risk_level: Literal["Unacceptable", "Undesirable", "Acceptable with Review", "Acceptable"] = Field(..., description="Initial risk assessment")


class HazardIdentificationSection(StrictBaseModel):
    """
    Render as: TABLE
    Core of ISO 14971 risk management
    """
    title: str = Field(default="6.1 Hazard Identification")
    methodology: str = Field(..., description="How hazards were identified (FMEA, FTA, etc.)")
    hazards: List[HazardIdentification] = Field(..., description="All identified hazards")
    
    # TABLE HEADERS: Hazard ID | Hazard | Situation | Harm | Severity | Probability | Risk Level


class RiskControlMeasure(StrictBaseModel):
    """Risk mitigation measure - TABLE ROW"""
    control_id: str = Field(..., description="Unique control ID (RC-001)")
    hazard_id: str = Field(..., description="Related hazard ID")
    control_type: Literal["Inherent Safety", "Protective Measure", "Information for Safety"] = Field(..., description="Type of risk control")
    control_description: str = Field(..., description="How risk is controlled")
    related_requirements: List[str] = Field(..., description="Requirements implementing this control")
    residual_severity: str = Field(..., description="Severity after control")
    residual_probability: str = Field(..., description="Probability after control")
    residual_risk: str = Field(..., description="Remaining risk level")
    verification_method: str = Field(..., description="How control effectiveness is verified")


class RiskControlMeasuresSection(StrictBaseModel):
    """
    Render as: TABLE
    Shows how risks are mitigated through requirements
    """
    title: str = Field(default="6.2 Risk Control Measures")
    control_strategy: str = Field(..., description="Overall approach to risk control")
    controls: List[RiskControlMeasure] = Field(..., description="All risk controls")
    
    # TABLE HEADERS: Control ID | Hazard ID | Type | Control | Requirements | Residual S | Residual P | Risk | Verification


class SOUPComponent(StrictBaseModel):
    """Software of Unknown Provenance / Off-The-Shelf component - TABLE ROW"""
    soup_id: str = Field(..., description="Unique SOUP ID (SOUP-001)")
    component_name: str = Field(..., description="Name of third-party component")
    version: str = Field(..., description="Version number")
    manufacturer: str = Field(..., description="Who developed it")
    purpose: str = Field(..., description="Why it's used in the system")
    safety_classification: str = Field(..., description="Safety class of this SOUP")
    known_anomalies: List[str] = Field(default_factory=list, description="Known bugs or issues")
    risk_controls: List[str] = Field(..., description="How risks from SOUP are controlled")
    validation_evidence: str = Field(..., description="Evidence of SOUP suitability")


class SOUPAnalysisSection(StrictBaseModel):
    """
    Render as: TABLE
    IEC 62304 requirement for third-party software
    """
    title: str = Field(default="6.3 SOUP/OTS Analysis")
    soup_policy: str = Field(..., description="How SOUP is evaluated and managed")
    components: List[SOUPComponent] = Field(..., description="All SOUP components")
    
    # TABLE HEADERS: SOUP ID | Name | Version | Manufacturer | Purpose | Safety Class | Anomalies | Controls | Validation


class HazardRiskAnalysisSection(StrictBaseModel):
    """Complete Section 6: Hazard & Risk Analysis Results"""
    section_title: str = Field(default="6. HAZARD & RISK ANALYSIS RESULTS")
    note: str = Field(default="Detailed risk analysis may be in separate Risk Management File per ISO 14971")
    hazard_identification: HazardIdentificationSection
    risk_control_measures: RiskControlMeasuresSection
    soup_analysis: SOUPAnalysisSection
