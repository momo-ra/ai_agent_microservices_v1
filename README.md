# AI Agent Microservices v2.0

A multi-plant AI agent service with dynamic database management and plant-specific access control.

## Features

- **Multi-Database Architecture**: Central database for users/plants, plant-specific databases for operational data
- **Dynamic Database Routing**: Automatic connection to the correct plant database based on request headers
- **Plant Access Control**: User permission validation for plant-specific data access
- **AI Chat Integration**: Intelligent chat system with plant-specific context
- **Query Processing**: SQL query transformation and execution with plant access validation
- **Health Monitoring**: Comprehensive health checks for all database connections

## Architecture

### Database Structure
- **Central Database**: Users, plants registry, global permissions
- **Plant Databases**: Operational data, chat sessions, workspaces, time series data

### API Design
- **RESTful API**: Standardized response format across all endpoints
- **Header-based Routing**: Uses `Plant-Id` and `x-user-id` headers for database routing
- **Middleware-based Security**: Plant access validation for all requests

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd ai_agent_microservices

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory:

```env
# Central Database
DB_USER=your_central_db_user
DB_PASSWORD=your_central_db_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=central_database

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT
JWT_SECRET=your_jwt_secret_key
JWT_ALGORITHM=HS256

# Plant Databases (example for Cairo plant)
CAIRO_USER=your_cairo_db_user
CAIRO_PASSWORD=your_cairo_db_password
CAIRO_HOST=localhost
CAIRO_PORT=5432
CAIRO_NAME=cairo_database
```

### 3. Database Setup

```bash
# Run database migrations
python -m alembic upgrade head

# Or initialize databases programmatically
python test_config.py
```

### 4. Start the Service

```bash
# Development
python main.py

# Production
uvicorn main:app --host 0.0.0.0 --port 8004
```

## API Usage

### Required Headers

All API requests must include:
- `Plant-Id`: Plant ID for database routing
- `x-user-id`: Authenticated user ID

### Example Request

```bash
curl -X POST "http://localhost:8004/api/v1/session" \
  -H "Plant-Id: 1" \
  -H "x-user-id: 123" \
  -H "Content-Type: application/json"
```

### Endpoints

#### Chat Endpoints
- `POST /api/v1/session` - Create chat session
- `GET /api/v1/session/{session_id}/history` - Get chat history
- `POST /api/v1/session/{session_id}/message` - Send message
- `GET /api/v1/session/{session_id}` - Get session info

#### Query Endpoints
- `POST /api/v1/query/transform` - Transform SQL query
- `POST /api/v1/query/execute` - Execute SQL query
- `POST /api/v1/query/analyze` - Analyze SQL query

#### System Endpoints
- `GET /health` - Service health check
- `GET /plants` - List active plants

## Configuration

See [CONFIGURATION.md](CONFIGURATION.md) for detailed configuration instructions.

## Database Schema

### Central Database
- `users` - User management
- `plants_registry` - Plant configuration
- `user_plant_access` - User-plant permissions
- `global_roles` - Global user roles
- `global_permissions` - Global permissions

### Plant Database
- `chat_sessions` - AI chat sessions
- `chat_messages` - Chat messages
- `workspaces` - Plant workspaces
- `tags` - Data tags
- `time_series` - Time series data
- And many more operational tables

## Development

### Project Structure

```
ai_agent_microservices/
├── core/                   # Core configuration
├── database.py            # Database management
├── main.py               # FastAPI application
├── middlewares/          # Authentication and access control
├── models/              # Database models
├── queries/             # Database queries
├── routers/             # API endpoints
├── schemas/             # Pydantic schemas
├── services/            # Business logic
└── utils/               # Utility functions
```

### Testing

```bash
# Run configuration test
python test_config.py

# Run health check
curl http://localhost:8004/health

# List active plants
curl http://localhost:8004/plants
```

## Migration from v1.0

1. Update your `.env` file with the new configuration format
2. Include required headers in all API requests
3. Update client code to handle the new response format
4. Test plant access permissions

See [CHANGELOG.md](CHANGELOG.md) for detailed migration instructions.

## Security

- Plant-level access control
- User permission validation
- Secure database routing
- Enhanced error handling

## Monitoring

- Health check endpoints
- Database connection monitoring
- Plant access logging
- Performance metrics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Add your license here]

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the configuration guide
