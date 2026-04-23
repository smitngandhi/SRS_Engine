from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SocialLoginProvider(StrictBaseModel):
    provider: str = Field(..., description="Social login provider (Google, Facebook, Apple, etc.)")
    oauth_version: str = Field(..., description="OAuth version used (OAuth 2.0, OpenID Connect)")


class EcommerceUserManagementSchema(StrictBaseModel):
    section_number: str = Field(default="2", description="Section number")
    section_title: str = Field(default="User Management Requirements", description="Section title")
    registration_methods: List[str] = Field(..., description="Supported registration methods (email, phone, social)")
    authentication_mechanisms: List[str] = Field(..., description="Authentication mechanisms (password, MFA, biometric)")
    social_login_providers: Optional[List[SocialLoginProvider]] = Field(default=None)
    profile_management_features: List[str] = Field(..., description="Profile management features (address book, preferences, etc.)")
    multi_tenancy_supported: bool = Field(..., description="Whether multi-tenancy (multiple stores/organizations) is supported")
    account_deletion_supported: bool = Field(..., description="Whether GDPR/CCPA right to erasure is supported")
