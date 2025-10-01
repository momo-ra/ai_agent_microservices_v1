from typing import TypeVar, Generic, List, Any, Dict
from pydantic import BaseModel, Field
from fastapi import Query

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Reusable pagination parameters"""
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of records to return")
    
    @property
    def offset(self) -> int:
        """Alias for skip for SQL queries"""
        return self.skip
    
    def get_slice(self) -> tuple[int, int]:
        """Get slice indices for list slicing"""
        return self.skip, self.skip + self.limit


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model"""
    items: List[T] = Field(..., description="List of items in current page")
    total: int = Field(..., description="Total number of items across all pages")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum items per page")
    has_more: bool = Field(..., description="Whether there are more items available")
    
    @property
    def page(self) -> int:
        """Current page number (1-indexed)"""
        return (self.skip // self.limit) + 1 if self.limit > 0 else 1
    
    @property
    def total_pages(self) -> int:
        """Total number of pages"""
        return (self.total + self.limit - 1) // self.limit if self.limit > 0 else 1


def get_pagination_params(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
) -> PaginationParams:
    """
    FastAPI dependency for pagination parameters.
    
    Usage in endpoints:
        @router.get("/items")
        async def get_items(pagination: PaginationParams = Depends(get_pagination_params)):
            # Use pagination.skip and pagination.limit
            pass
    """
    return PaginationParams(skip=skip, limit=limit)


def create_paginated_response(
    items: List[Any],
    total: int,
    skip: int,
    limit: int
) -> Dict[str, Any]:
    """
    Create a standardized paginated response dictionary.
    
    Args:
        items: List of items for current page
        total: Total count of items across all pages
        skip: Number of items skipped
        limit: Maximum items per page
    
    Returns:
        Dictionary with paginated response structure
    """
    has_more = (skip + len(items)) < total
    
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": has_more,
        "page": (skip // limit) + 1 if limit > 0 else 1,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1
    }


def paginate_list(
    items: List[Any],
    skip: int = 0,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Paginate an in-memory list.
    
    Args:
        items: Full list of items to paginate
        skip: Number of items to skip
        limit: Maximum items per page
    
    Returns:
        Paginated response dictionary
    """
    total = len(items)
    paginated_items = items[skip:skip + limit]
    
    return create_paginated_response(
        items=paginated_items,
        total=total,
        skip=skip,
        limit=limit
    )

