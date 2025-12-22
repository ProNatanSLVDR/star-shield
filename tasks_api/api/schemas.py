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


class EnqueueRefreshResponse(BaseModel):
    """Schema for enqueue refresh all response."""

    total: int
    enqueued: int
    failed: int
    errors: list[str]

    class Config:
        json_schema_extra = {
            "example": {
                "total": 10,
                "enqueued": 9,
                "failed": 1,
                "errors": ["Failed to enqueue task for etablissement 5: Connection error"],
            }
        }
