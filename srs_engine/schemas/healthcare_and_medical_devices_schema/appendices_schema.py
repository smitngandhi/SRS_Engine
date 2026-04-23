from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AppendixReference(StrictBaseModel):
    document_title: str = Field(..., description="Title of the referenced document")
    document_id: Optional[str] = Field(default=None, description="Document identifier or SOP number")
    document_type: str = Field(..., description="Type of document (DHF, SDS, SOP, Risk File, etc.)")
    location: Optional[str] = Field(default=None, description="Location or path to the document")


class HealthcareAppendicesSchema(StrictBaseModel):
    section_number: str = Field(default="9", description="Section number")
    section_title: str = Field(default="Appendices", description="Section title")
    referenced_documents: List[AppendixReference]
    additional_notes: Optional[str] = Field(default=None, description="Any additional notes or clarifications")