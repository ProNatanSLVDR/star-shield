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


class AiResponseResult(BaseModel):
    """Schema for AI response generation results."""

    etablissement_id: int
    total_reviews: int
    responded: int
    failed: int
    pending: int = 0
    flagged: int = 0
    errors: list[str]

    class Config:
        json_schema_extra = {
            "example": {
                "etablissement_id": 1,
                "total_reviews": 5,
                "responded": 3,
                "failed": 1,
                "pending": 1,
                "flagged": 0,
                "errors": ["Failed to process review abc123: API error"],
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
