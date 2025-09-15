# Configuration Guide

This document explains how to configure the AI Agent Microservices for multi-plant database architecture.

## Environment Variables

Create a `.env` file in the root directory with the following variables:

### Central Database Configuration
```env
DB_USER=your_central_db_user
DB_PASSWORD=your_central_db_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=central_database
```

### Redis Configuration
```env
REDIS_HOST=localhost
REDIS_PORT=6379
```

### JWT Configuration
```env
JWT_SECRET=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
```

### Jobs Service Configuration
```env
JOBS_SERVICE_URL=http://localhost:8001
```

### Plant-specific Database Configurations

For each plant, you need to configure its database connection using the pattern:
`{PLANT_KEY}_{CONFIG_TYPE}`

Example for a plant with key "CAIRO":
```env
CAIRO_USER=your_cairo_db_user
CAIRO_PASSWORD=your_cairo_db_password
CAIRO_HOST=localhost
CAIRO_PORT=5432
CAIRO_NAME=cairo_database
```

Example for multiple plants:
```env
# Cairo Plant
CAIRO_USER=your_cairo_db_user
CAIRO_PASSWORD=your_cairo_db_password
CAIRO_HOST=localhost
CAIRO_PORT=5432
CAIRO_NAME=cairo_database

# Alexandria Plant
ALEX_USER=your_alex_db_user
ALEX_PASSWORD=your_alex_db_password
ALEX_HOST=localhost
ALEX_PORT=5432
ALEX_NAME=alex_database

# Suez Plant
SUEZ_USER=your_suez_db_user
SUEZ_PASSWORD=your_suez_db_password
SUEZ_HOST=localhost
SUEZ_PORT=5432
SUEZ_NAME=suez_database
```

## Database Setup

### Central Database
The central database should contain:
- Users table
- Plants registry table
- User plant access table
- Global roles and permissions

### Plant Databases
Each plant database should contain:
- Plant-specific operational data
- Chat sessions and messages
- Workspaces and tags
- Time series data

## API Usage

### Headers Required
All API requests must include:
- `Plant-Id`: The plant ID for database routing
- `x-user-id`: The authenticated user ID

### Example Request
```bash
curl -X POST "http://localhost:8004/api/v1/session" \
  -H "Plant-Id: 1" \
  -H "x-user-id: 123" \
  -H "Content-Type: application/json"
```

## Health Check

The service provides health check endpoints:
- `GET /health` - Overall service health
- `GET /plants` - List of active plants

## Migration from Single Database

If migrating from a single database architecture:

1. Update your `.env` file with the new configuration
2. Run database migrations for both central and plant databases
3. Update your client applications to include the required headers
4. Test the new endpoints to ensure proper functionality
