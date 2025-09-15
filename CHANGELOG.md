# Changelog - AI Agent Microservices v2.0

## Major Changes

### 1. Multi-Database Architecture
- **Central Database**: Manages users, plants registry, and global permissions
- **Plant-Specific Databases**: Each plant has its own database for operational data
- **Dynamic Database Routing**: Automatic connection to the correct plant database based on headers

### 2. Enhanced Configuration System
- **Environment-based Configuration**: Central and plant-specific database configurations
- **Dynamic Plant Database URLs**: Automatic generation of database URLs for each plant
- **Improved Error Handling**: Better validation and error messages for missing configurations

### 3. Updated Schema System
- **New Response Models**: Enhanced AI response schema with validation
- **Type Safety**: Better type definitions for all API responses
- **Schema Validation**: Automatic validation of AI responses against defined schemas

### 4. Plant Access Control
- **Plant Access Middleware**: Validates user access to specific plants
- **Header-based Routing**: Uses `Plant-Id` and `x-user-id` headers for database routing
- **Permission Validation**: Ensures users can only access authorized plant data

## File Changes

### Core Files
- **`main.py`**: Added health check endpoints and plant listing
- **`core/config.py`**: Enhanced with plant-specific database configuration
- **`database.py`**: Implemented multi-database architecture with dynamic routing
- **`schemas/schema.py`**: Fixed syntax error and enhanced response models

### Services
- **`services/ai_agent_service.py`**: Added schema validation for AI responses
- **`services/query_service.py`**: Added plant access validation for queries

### Routers
- **`routers/endpoints.py`**: Updated to use plant access middleware
- **`routers/query_endpoint.py`**: Enhanced with plant access validation

### Middleware
- **`middlewares/plant_access_middleware.py`**: New middleware for plant access validation

### Documentation
- **`CONFIGURATION.md`**: Comprehensive configuration guide
- **`CHANGELOG.md`**: This changelog file

## API Changes

### New Endpoints
- `GET /health` - Service health check
- `GET /plants` - List active plants

### Required Headers
All API requests now require:
- `Plant-Id`: Plant ID for database routing
- `x-user-id`: Authenticated user ID

### Response Format
All responses now use the standardized `ResponseModel` format with:
- `status`: Success/failure status
- `data`: Response data
- `message`: Human-readable message
- `status_code`: HTTP status code

## Database Changes

### Central Database Tables
- `users` - User management
- `plants_registry` - Plant configuration
- `user_plant_access` - User-plant permissions
- `global_roles` - Global user roles
- `global_permissions` - Global permissions

### Plant Database Tables
- `chat_sessions` - AI chat sessions
- `chat_messages` - Chat messages
- `workspaces` - Plant workspaces
- `tags` - Data tags
- `time_series` - Time series data
- And many more operational tables

## Migration Guide

### For Developers
1. Update your `.env` file with the new configuration format
2. Include required headers in all API requests
3. Update client code to handle the new response format
4. Test plant access permissions

### For Database Administrators
1. Set up central database with required tables
2. Configure plant-specific databases
3. Update environment variables for each plant
4. Run database migrations

## Breaking Changes

1. **Required Headers**: All API requests must include `Plant-Id` and `x-user-id` headers
2. **Database Architecture**: Single database replaced with multi-database system
3. **Response Format**: Standardized response format across all endpoints
4. **Configuration**: New environment variable structure required

## Backward Compatibility

- Old `get_db()` function is deprecated but still available
- Legacy endpoints will show deprecation warnings
- Gradual migration path provided for existing clients

## Security Enhancements

- Plant-level access control
- User permission validation
- Secure database routing
- Enhanced error handling

## Performance Improvements

- Database connection pooling
- Cached plant database connections
- Optimized query execution
- Better error handling and logging
