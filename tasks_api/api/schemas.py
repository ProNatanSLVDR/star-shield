"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel


class ReviewFetchRequest(BaseModel):
    """Schema for review fetch task requests."""

    etablissement_id: int


class ReviewFetchResponse(BaseModel):
    """Schema for review fetch task responses."""

    etablissement_id: int

    class Config:
        json_schema_extra = {
            "example": {
                "etablissement_id": 1,
            }
        }
