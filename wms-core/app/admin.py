"""SQLAdmin configuration – provides a web-based admin panel at /admin."""

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqlalchemy import select

from app.api.auth import verify_password, create_access_token, settings
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.comment import Comment
from app.models.task import Task
from app.models.user import User

from datetime import timedelta
from jose import JWTError, jwt


# ---------------------------------------------------------------------------
# Authentication backend – uses the existing users table + JWT tokens
# ---------------------------------------------------------------------------


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = form.get("username", "")  # sqladmin login form field is "username"
        password = form.get("password", "")

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            return False

        token = create_access_token(
            data={"sub": user.id},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        request.session.update({"token": token})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> RedirectResponse | bool:
        token = request.session.get("token")
        if not token:
            return RedirectResponse(request.url_for("admin:login"), status_code=302)
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            if payload.get("sub") is None:
                return RedirectResponse(request.url_for("admin:login"), status_code=302)
        except JWTError:
            return RedirectResponse(request.url_for("admin:login"), status_code=302)
        return True


# ---------------------------------------------------------------------------
# Model views
# ---------------------------------------------------------------------------


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"

    column_list = [User.id, User.email, User.username, User.created_at]
    column_searchable_list = [User.email, User.username]
    column_sortable_list = [User.email, User.username, User.created_at]
    column_default_sort = ("created_at", True)

    # Hide password hash from the detail/edit views
    form_excluded_columns = [User.password_hash]
    column_details_exclude_list = [User.password_hash]


class TaskAdmin(ModelView, model=Task):
    name = "Task"
    name_plural = "Tasks"
    icon = "fa-solid fa-list-check"

    column_list = [
        Task.id,
        Task.title,
        Task.status,
        Task.priority,
        Task.user_id,
        Task.agent_id,
        Task.assigned_user_id,
        Task.due_date,
        Task.created_at,
    ]
    column_searchable_list = [Task.title, Task.description]
    column_sortable_list = [Task.title, Task.status, Task.priority, Task.created_at]
    column_default_sort = ("created_at", True)


class AgentAdmin(ModelView, model=Agent):
    name = "Agent"
    name_plural = "Agents"
    icon = "fa-solid fa-robot"

    column_list = [
        Agent.id,
        Agent.key,
        Agent.name,
        Agent.is_active,
        Agent.created_at,
    ]
    column_searchable_list = [Agent.key, Agent.name]
    column_sortable_list = [Agent.key, Agent.name, Agent.is_active, Agent.created_at]
    column_default_sort = ("created_at", True)


class CommentAdmin(ModelView, model=Comment):
    name = "Comment"
    name_plural = "Comments"
    icon = "fa-solid fa-comment"

    column_list = [
        Comment.id,
        Comment.task_id,
        Comment.content,
        Comment.user_id,
        Comment.agent_id,
        Comment.parent_id,
        Comment.created_at,
    ]
    column_searchable_list = [Comment.content]
    column_sortable_list = [Comment.created_at]
    column_default_sort = ("created_at", True)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

ALL_VIEWS = [UserAdmin, TaskAdmin, AgentAdmin, CommentAdmin]


def setup_admin(app, engine) -> Admin:
    """Create and mount the admin panel on the given FastAPI app."""
    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    admin = Admin(
        app,
        engine,
        title="WMS Admin",
        authentication_backend=authentication_backend,
    )
    for view in ALL_VIEWS:
        admin.add_view(view)
    return admin
