from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ...schemas import domain as schemas
from ...core.responses import APIResponse
from ...core.database import get_db
from ...services.supervisor_service import SupervisorService

router = APIRouter()

@router.post("/", response_model=APIResponse[schemas.SupervisorResponse])
async def create_supervisor(supervisor: schemas.SupervisorCreate, db: AsyncSession = Depends(get_db)):
    db_supervisor = await SupervisorService.create_supervisor(db, supervisor)
    return APIResponse(success=True, data=db_supervisor)

@router.get("/", response_model=APIResponse[List[schemas.SupervisorResponse]])
async def list_supervisors(db: AsyncSession = Depends(get_db)):
    supervisors = await SupervisorService.get_supervisors(db)
    return APIResponse(success=True, data=supervisors)

@router.get("/{id}", response_model=APIResponse[schemas.SupervisorResponse])
async def get_supervisor(id: int, db: AsyncSession = Depends(get_db)):
    db_supervisor = await SupervisorService.get_supervisor(db, id)
    return APIResponse(success=True, data=db_supervisor)
