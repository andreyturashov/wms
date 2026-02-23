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
- **Alembic** - Database migrations
- **Python 3.13** - Python version

## Frontend
- **React 19** - UI library for building user interfaces
- **TypeScript** - Typed JavaScript
- **Vite 8** - Next-generation frontend build tool (beta)
- **Tailwind CSS v4** - Utility-first CSS framework
- **Native Drag & Drop API** - Built-in browser drag and drop functionality for task management

## Development Tools
- **uv** - Modern Python package manager
- **Yarn** - JavaScript package manager
- **Make** - Build automation tool
- **Git** - Version control

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
- due_date (String, nullable)
- user_id (String, FK)
- created_at (DateTime)
- updated_at (DateTime)
