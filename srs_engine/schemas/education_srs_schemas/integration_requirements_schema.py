from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LTIToolIntegration(StrictBaseModel):
    tool_name: str = Field(..., description="LTI tool name (e.g. Turnitin, Zoom, Kahoot)")
    lti_version: str = Field(..., description="LTI version (LTI 1.1, LTI 1.3/Advantage)")
    deep_linking_required: Optional[bool] = Field(default=None, description="Whether LTI Deep Linking is required")


class SSOConfiguration(StrictBaseModel):
    protocol: str = Field(..., description="SSO protocol (SAML 2.0, OAuth 2.0/OIDC, CAS)")
    identity_provider: Optional[str] = Field(default=None, description="Identity provider (Azure AD, Google, Okta)")


class EducationIntegrationRequirementsSchema(StrictBaseModel):
    section_number: str = Field(default="7", description="Section number")
    section_title: str = Field(default="Integration Requirements (LTI/SIS)", description="Section title")
    lti_integrations: List[LTIToolIntegration]
    sis_integration: str = Field(..., description="Student Information System integration approach (Clever, PowerSchool, Banner)")
    sso_configuration: SSOConfiguration
    third_party_app_marketplace: bool = Field(..., description="Whether a third-party app marketplace/ecosystem is supported")
    api_availability: bool = Field(..., description="Whether a public API is provided for integrations")
    lrs_integration: Optional[bool] = Field(
        default=None, description="Whether integration with a Learning Record Store (LRS) is required (xAPI)"
    )
