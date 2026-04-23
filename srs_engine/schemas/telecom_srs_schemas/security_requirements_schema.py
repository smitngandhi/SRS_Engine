from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuthenticationRequirement(StrictBaseModel):
    mechanism: str = Field(..., description="Authentication mechanism (5G-AKA, EAP-AKA', EAP-TLS)")
    spec_reference: str = Field(..., description="3GPP spec defining this mechanism (e.g. TS 33.501)")


class EncryptionRequirement(StrictBaseModel):
    algorithm: str = Field(..., description="Encryption algorithm (NEA0, 128-NEA1/SNOW 3G, 128-NEA2/AES)")
    applied_to: str = Field(..., description="What this encryption protects (RRC, NAS, UP data)")
    mandatory: bool = Field(..., description="Whether this encryption is mandatory (true) or optional (false)")


class LawfulInterceptionRequirement(StrictBaseModel):
    li_standard: str = Field(..., description="Lawful interception standard (ETSI TS 101 671, 3GPP TS 33.127)")
    target_id_types: List[str] = Field(..., description="Target identifier types supported (IMSI, IMEI, MSISDN)")
    delivery_mechanism: str = Field(..., description="Mechanism for delivering intercepted content to LEA")


class TelecomSecurityRequirementsSchema(StrictBaseModel):
    section_number: str = Field(default="8", description="Section number")
    section_title: str = Field(default="Security Requirements", description="Section title")
    authentication_requirements: List[AuthenticationRequirement]
    encryption_requirements: List[EncryptionRequirement]
    integrity_protection_algorithms: List[str] = Field(
        ..., description="Integrity protection algorithms (NIA0, 128-NIA1, 128-NIA2)"
    )
    lawful_interception: Optional[LawfulInterceptionRequirement] = Field(default=None)
    suci_privacy: bool = Field(..., description="Whether SUCI (Subscription Concealed Identifier) privacy is required")
