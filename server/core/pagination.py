"""
Pagination utilities for list API endpoints.

Provides paginated response models and helper functions for offset-based pagination
to handle large datasets efficiently.
"""

from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Query

T = TypeVar('T')

class PaginationParams(BaseModel):
    """Query parameters for pagination."""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=50, ge=1, le=200, description="Items per page (max 200)")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: List[T] = Field(description="List of items for this page")
    total: int = Field(description="Total number of items across all pages")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Number of items per page")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")
    total_pages: int = Field(description="Total number of pages")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "page_size": 50,
                "has_next": True,
                "has_previous": False,
                "total_pages": 2
            }
        }


def paginate(
    query: Query,
    page: int = 1,
    page_size: int = 50,
    max_page_size: int = 200
) -> tuple[List, int]:
    """
    Apply pagination to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query object to paginate
        page: Page number (1-indexed, default=1)
        page_size: Number of items per page (default=50)
        max_page_size: Maximum allowed page size (default=200)

    Returns:
        Tuple of (items, total_count)

    Raises:
        ValueError: If page or page_size are invalid
    """
    # Validate inputs
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 50
    if page_size > max_page_size:
        page_size = max_page_size

    # Get total count before pagination
    total = query.count()

    # Calculate offset
    offset = (page - 1) * page_size

    # Apply pagination to query
    items = query.offset(offset).limit(page_size).all()

    return items, total


def create_paginated_response(
    items: List[T],
    total: int,
    page: int,
    page_size: int
) -> dict:
    """
    Create a paginated response dictionary.

    Args:
        items: List of items for this page
        total: Total number of items
        page: Current page number (1-indexed)
        page_size: Items per page

    Returns:
        Dictionary matching PaginatedResponse schema
    """
    total_pages = (total + page_size - 1) // page_size  # Ceiling division

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": page < total_pages,
        "has_previous": page > 1,
        "total_pages": total_pages
    }
