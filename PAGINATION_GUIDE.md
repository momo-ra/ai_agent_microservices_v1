# Pagination System Guide

This guide explains how to use the reusable pagination system in your application.

## Overview

The pagination system provides:
- **Reusable pagination parameters** via dependency injection
- **Standardized pagination responses** with metadata
- **Helper functions** for paginating lists and database results
- **No code duplication** - define pagination once, use everywhere

## Quick Start

### 1. Basic Usage in Endpoints

Replace individual `skip` and `limit` parameters with the `PaginationParams` dependency:

**Before:**
```python
@router.get("/items")
async def get_items(
    skip: int = 0,
    limit: int = 100
):
    items = await db.get_items(skip=skip, limit=limit)
    return {"items": items}
```

**After:**
```python
from utils.pagination import get_pagination_params, PaginationParams

@router.get("/items")
async def get_items(
    pagination: PaginationParams = Depends(get_pagination_params)
):
    items = await db.get_items(skip=pagination.skip, limit=pagination.limit)
    return {"items": items}
```

### 2. Creating Paginated Responses

Use `create_paginated_response` to return standardized pagination metadata:

```python
from utils.pagination import get_pagination_params, create_paginated_response, PaginationParams

@router.get("/items")
async def get_items(
    pagination: PaginationParams = Depends(get_pagination_params)
):
    # Get total count from database
    total = await db.count_items()
    
    # Get paginated items
    items = await db.get_items(skip=pagination.skip, limit=pagination.limit)
    
    # Create paginated response
    paginated_data = create_paginated_response(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit
    )
    
    return success_response(data=paginated_data, message="Items retrieved successfully")
```

### 3. Paginating In-Memory Lists

For in-memory data, use `paginate_list`:

```python
from utils.pagination import paginate_list, PaginationParams

@router.get("/filtered-items")
async def get_filtered_items(
    pagination: PaginationParams = Depends(get_pagination_params)
):
    # Get all items
    all_items = await db.get_all_items()
    
    # Apply filtering
    filtered_items = [item for item in all_items if item.is_active]
    
    # Paginate the filtered list
    paginated_data = paginate_list(
        items=filtered_items,
        skip=pagination.skip,
        limit=pagination.limit
    )
    
    return success_response(data=paginated_data, message="Filtered items retrieved")
```

## Pagination Response Structure

All paginated responses include the following fields:

```json
{
  "items": [...],           // Array of items for the current page
  "total": 150,             // Total number of items across all pages
  "skip": 0,                // Number of items skipped
  "limit": 100,             // Maximum items per page
  "has_more": true,         // Whether there are more items available
  "page": 1,                // Current page number (1-indexed)
  "total_pages": 2          // Total number of pages
}
```

## API Query Parameters

Clients can control pagination using these query parameters:

- `skip` (default: 0): Number of records to skip
- `limit` (default: 100, max: 1000): Maximum records per page

**Example API calls:**

```bash
# First page (default)
GET /api/items

# First page explicit
GET /api/items?skip=0&limit=10

# Second page
GET /api/items?skip=10&limit=10

# Third page with 50 items per page
GET /api/items?skip=100&limit=50
```

## Examples from Your Codebase

### Example 1: User Artifacts

```python
@router.get("/user/artifacts", response_model=ResponseModel)
async def get_all_user_artifacts(
    pagination: PaginationParams = Depends(get_pagination_params),
    artifact_service: ArtifactService = Depends(get_artifact_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Get all artifacts for the authenticated user across all sessions"""
    try:
        result = await artifact_service.get_all_user_artifacts(
            db=db,
            user_id=auth_data.get("user_id"),
            auth_data=auth_data,
            skip=pagination.skip,
            limit=pagination.limit
        )
        
        if result:
            return success_response(data=result, message="User artifacts retrieved successfully")
        else:
            return fail_response(message="Failed to retrieve user artifacts", status_code=500)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)
```

### Example 2: Search with Pagination

```python
@router.get("/user/sessions/search", response_model=ResponseModel)
async def search_sessions(
    q: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Search chat sessions for the logged-in user"""
    try:
        sessions = await chat_service.search_sessions(
            db=db,
            user_id=auth_data.get("user_id"),
            search_term=q,
            skip=pagination.skip,
            limit=pagination.limit
        )
        return success_response(
            data={
                "sessions": sessions,
                "total_count": len(sessions),
                "skip": pagination.skip,
                "limit": pagination.limit,
                "search_term": q
            },
            message="Search completed successfully"
        )
    except Exception as e:
        return fail_response(message=str(e), status_code=500)
```

## Advanced Features

### PaginationParams Properties

The `PaginationParams` class provides useful properties:

```python
pagination = PaginationParams(skip=20, limit=10)

# Get offset (alias for skip)
offset = pagination.offset  # Returns: 20

# Get slice indices for list slicing
start, end = pagination.get_slice()  # Returns: (20, 30)
```

### Custom Pagination Limits

You can customize the default and maximum limits by modifying the `get_pagination_params` function:

```python
def get_pagination_params(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return")
) -> PaginationParams:
    return PaginationParams(skip=skip, limit=limit)
```

## Migration Checklist

To migrate an existing endpoint to use the new pagination system:

1. ✅ Import pagination utilities:
   ```python
   from utils.pagination import get_pagination_params, PaginationParams
   ```

2. ✅ Replace individual parameters:
   ```python
   # Remove: skip: int = 0, limit: int = 100
   # Add: pagination: PaginationParams = Depends(get_pagination_params)
   ```

3. ✅ Update function calls:
   ```python
   # Replace: skip=skip, limit=limit
   # With: skip=pagination.skip, limit=pagination.limit
   ```

4. ✅ Update response data (if needed):
   ```python
   # Replace: "skip": skip, "limit": limit
   # With: "skip": pagination.skip, "limit": pagination.limit
   ```

## Benefits

✅ **No Repetition**: Define pagination once, use everywhere  
✅ **Consistency**: All endpoints use the same pagination parameters  
✅ **Type Safety**: Pydantic validation ensures valid parameters  
✅ **Auto Documentation**: FastAPI auto-generates OpenAPI docs  
✅ **Easy Maintenance**: Change pagination logic in one place  
✅ **Client-Friendly**: Standard pagination response format

## Summary

The pagination system makes it easy to add pagination to any endpoint without repeating code. Simply inject `PaginationParams` via dependency injection, use the `skip` and `limit` values in your database queries, and optionally use helper functions for standardized responses.

