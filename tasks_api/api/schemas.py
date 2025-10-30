"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel


class ReviewFetchRequest(BaseModel):
    """Schema for review fetch task requests."""

    etablissement_id: int


class ReviewFetchResponse(BaseModel):
    """Schema for review fetch task responses."""

    status: str
    etablissement_id: int
    message: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "etablissement_id": 1,
                "message": "Full import completed",
            }
        }
