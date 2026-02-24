# Skills & Technologies

## Backend
- **FastAPI** - Modern Python web framework for building APIs
- **SQLAlchemy (Async)** - SQL toolkit and ORM for database operations with async support
- **aiosqlite** - Asynchronous SQLite driver
- **Pydantic v2** - Data validation using Python type annotations
- **Pydantic Settings** - Configuration management via environment variables
- **JWT (Python-JOSE)** - JSON Web Token authentication
- **Bcrypt & Passlib** - Password hashing and verification
- **Uvicorn** - ASGI server for running FastAPI
- **Python 3.13** - Python version

## Frontend
- **React 19** - UI library for building user interfaces
- **TypeScript** - Typed JavaScript
- **Vite 8** - Next-generation frontend build tool (beta)
- **Tailwind CSS v4** - Utility-first CSS framework
- **Native Drag & Drop API** - Built-in browser drag and drop for task management
- **Inline Editing** - Double-click or pencil icon to edit task cards in place

## Testing
- **pytest** - Python testing framework
- **pytest-asyncio** - Async test support for FastAPI/SQLAlchemy
- **pytest-cov** - Code coverage reporting (100% line coverage)
- **pytest-xdist** - Parallel test execution across CPU cores
- **httpx** - Async HTTP client for API integration tests

## Development Tools
- **uv** - Modern Python package manager
- **Yarn** - JavaScript package manager
- **Make** - Build automation tool (`make test`, `make test-cov`, `make run`)
- **Git** - Version control
- **Postman** - API testing via VS Code extension

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user

### Tasks
- `GET /api/tasks` - Get all tasks for current user
- `GET /api/tasks/{task_id}` - Get specific task
- `POST /api/tasks` - Create new task
- `PUT /api/tasks/{task_id}` - Update task
- `DELETE /api/tasks/{task_id}` - Delete task
- `PUT /api/tasks/{task_id}/status` - Update task status
- `PUT /api/tasks/{task_id}/assign` - Assign agent to task

### Agents
- `GET /api/agents` - List agents (supports `?active_only=true`)
- `POST /api/agents` - Create new agent

## Database Schema

### Users Table
- id (String, PK)
- email (String, unique)
- username (String)
- password_hash (String)
- created_at (DateTime)

### Tasks Table
- id (String, PK)
- title (String)
- description (Text)
- status (String) - todo, in_progress, done
- priority (String) - low, medium, high
- agent_id (String, FK → agents.id, nullable)
- due_date (String, nullable)
- user_id (String, FK → users.id)
- created_at (DateTime)
- updated_at (DateTime)

### Agents Table
- id (String, PK)
- key (String, unique) - machine identifier
- name (String) - display name
- description (Text)
- is_active (Boolean)
- created_at (DateTime)
- updated_at (DateTime)
