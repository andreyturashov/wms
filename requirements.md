# WMS - Task Management System

A Trello/Asana-like task management application with Kanban boards.

## Overview
Create a task management system application which is clone of trello, asana, etc

## Technical Stack

### Backend (wms-core):
- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT tokens
- **API**: REST API with OpenAPI/Swagger docs

### Frontend (wms-front):
- **Framework**: React with TypeScript
- **Build Tool**: Vite
- **State Management**: React Query or Context API
- **Styling**: Tailwind CSS

## Features

### Core Features
1. **Task Management**
   - Create, read, update, delete tasks
   - Task fields: title, description, status, priority, due date

2. **Board/Column System**
   - Kanban-style columns (To Do, In Progress, Done)
   - Drag and drop tasks between columns

3. **User Authentication**
   - User registration and login
   - JWT-based authentication

### API Endpoints

#### Auth
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

#### Tasks
- `GET /api/tasks` - Get all tasks (with filters)
- `POST /api/tasks` - Create new task
- `GET /api/tasks/{id}` - Get task by ID
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task
- `PUT /api/tasks/{id}/status` - Update task status (column)

## Data Models

### User
- id (UUID)
- email (unique)
- username
- password_hash
- created_at

### Task
- id (UUID)
- title
- description
- status (todo/in_progress/done)
- priority (low/medium/high)
- due_date (optional)
- user_id (FK to User)
- created_at
- updated_at

## Project Structure

```
wms/
├── requirements.md
├── wms-core/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── router.py
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── models/
│   │   │   └── task.py
│   │   ├── schemas/
│   │   │   └── task.py
│   │   └── db/
│   │       ├── session.py
│   │       └── base.py
│   ├── migrations/
│   ├── tests/
│   ├── pyproject.toml
│   └── README.md
└── wms-front/
    ├── src/
    │   ├── components/
    │   ├── pages/
    │   ├── hooks/
    │   ├── api/
    │   ├── App.tsx
    │   └── main.tsx
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    └── README.md
```
