from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.agent import Agent
from app.models.user import User
from app.schemas.agent import AgentCreate, AgentResponse

router = APIRouter()


@router.get("", response_model=List[AgentResponse])
async def get_agents(
    active_only: bool = False,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Agent).order_by(Agent.name)
    if active_only:
        query = query.where(Agent.is_active.is_(True))

    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Agent).where(Agent.key == payload.key))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent with this key already exists",
        )

    agent = Agent(
        id=str(uuid.uuid4()),
        key=payload.key,
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent
