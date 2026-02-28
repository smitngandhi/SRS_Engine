from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchCapability(StrictBaseModel):
    search_type: str = Field(..., description="Search type (full-text, faceted, semantic/AI)")
    filter_attributes: List[str] = Field(..., description="Filterable product attributes")
    sort_options: List[str] = Field(..., description="Sorting options (price, relevance, rating, newest)")


class EcommerceProductCatalogSchema(StrictBaseModel):
    section_number: str = Field(default="3", description="Section number")
    section_title: str = Field(default="Product Catalog Requirements", description="Section title")
    pim_system: Optional[str] = Field(default=None, description="Product Information Management system used/integrated")
    max_product_count: Optional[int] = Field(default=None, description="Maximum number of products in catalog")
    category_depth: Optional[int] = Field(default=None, description="Maximum category hierarchy depth")
    search: SearchCapability
    product_recommendation_engine: bool = Field(..., description="Whether AI/ML product recommendations are required")
    multi_language_support: bool = Field(..., description="Whether multi-language catalog is required")
    media_types_supported: List[str] = Field(..., description="Supported media types (images, video, 3D models)")
