from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from ...schemas import domain as schemas
from ...core.responses import APIResponse
from ...core.database import get_db
from ...services.run_service import RunService

router = APIRouter()

@router.post("/", response_model=APIResponse[schemas.RunResponse])
async def create_run(run: schemas.RunCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    db_run = await RunService.create_run(db, background_tasks, run)
    return APIResponse(success=True, data=db_run)

@router.get("/", response_model=APIResponse[List[schemas.RunResponse]])
async def list_runs(db: AsyncSession = Depends(get_db)):
    runs = await RunService.get_runs(db)
    return APIResponse(success=True, data=runs)

@router.get("/{run_id}", response_model=APIResponse[schemas.RunResponse])
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    db_run = await RunService.get_run(db, run_id)
    return APIResponse(success=True, data=db_run)

@router.get("/{run_id}/activities", response_model=APIResponse[List[schemas.ActivityResponse]])
async def get_run_activities(run_id: str, db: AsyncSession = Depends(get_db)):
    activities = await RunService.get_activities(db, run_id)
    return APIResponse(success=True, data=activities)

@router.post("/{run_id}/events", response_model=APIResponse[schemas.ActivityResponse])
async def inject_event(run_id: str, event: schemas.ActivityCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    activity = await RunService.inject_activity(db, background_tasks, run_id, event)
    return APIResponse(success=True, data=activity)

@router.post("/{run_id}/instructions", response_model=APIResponse[schemas.ActivityResponse])
async def inject_instruction(run_id: str, instruction: schemas.ActivityCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    activity = await RunService.inject_activity(db, background_tasks, run_id, instruction)
    return APIResponse(success=True, data=activity)

@router.post("/{run_id}/terminate", response_model=APIResponse[Dict[str, str]])
async def terminate_run(run_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    await RunService.change_status(db, background_tasks, run_id, "completed")
    return APIResponse(success=True, message="Run terminated")

@router.post("/{run_id}/pause", response_model=APIResponse[Dict[str, str]])
async def pause_run(run_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    await RunService.change_status(db, background_tasks, run_id, "paused")
    return APIResponse(success=True, message="Run paused")

@router.post("/{run_id}/resume", response_model=APIResponse[Dict[str, str]])
async def resume_run(run_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    await RunService.change_status(db, background_tasks, run_id, "active")
    return APIResponse(success=True, message="Run resumed")
