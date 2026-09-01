import uuid
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from typing import List
from ..models import domain as models
from ..schemas import domain as schemas
from ..core.exceptions import NotFoundException, BadRequestException
import logging

logger = logging.getLogger(__name__)

class RunService:
    @staticmethod
    async def create_run(db: AsyncSession, background_tasks: BackgroundTasks, run_in: schemas.RunCreate) -> models.Run:
        try:
            # Verify supervisor
            sup_result = await db.execute(select(models.Supervisor).where(models.Supervisor.id == run_in.supervisor_id))
            if not sup_result.scalars().first():
                raise NotFoundException("Supervisor not found")

            new_run_id = str(uuid.uuid4())
            db_run = models.Run(
                id=new_run_id,
                order_id=run_in.order_id,
                supervisor_id=run_in.supervisor_id,
                status="active",
                state={}
            )
            db.add(db_run)

            start_event = models.Activity(
                run_id=new_run_id,
                type="event",
                payload={"event": "run_started", "message": "Order run initiated"}
            )
            db.add(start_event)
            await db.commit()
            await db.refresh(db_run)

            from ..agent import trigger_agent
            background_tasks.add_task(trigger_agent, new_run_id)

            return db_run
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error creating run: {e}")
            await db.rollback()
            raise BadRequestException("Failed to create run.")

    @staticmethod
    async def get_runs(db: AsyncSession) -> List[models.Run]:
        try:
            result = await db.execute(select(models.Run).order_by(models.Run.created_at.desc()))
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching runs: {e}")
            raise BadRequestException("Failed to fetch runs.")

    @staticmethod
    async def get_run(db: AsyncSession, run_id: str) -> models.Run:
        try:
            result = await db.execute(select(models.Run).where(models.Run.id == run_id))
            db_run = result.scalars().first()
            if not db_run:
                raise NotFoundException("Run not found")
            return db_run
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching run: {e}")
            raise BadRequestException("Failed to fetch run.")

    @staticmethod
    async def get_activities(db: AsyncSession, run_id: str) -> List[models.Activity]:
        try:
            result = await db.execute(
                select(models.Activity)
                .where(models.Activity.run_id == run_id)
                .order_by(models.Activity.created_at.asc(), models.Activity.id.asc())
            )
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching activities: {e}")
            raise BadRequestException("Failed to fetch activities.")

    @staticmethod
    async def inject_activity(db: AsyncSession, background_tasks: BackgroundTasks, run_id: str, activity_in: schemas.ActivityCreate) -> models.Activity:
        try:
            result = await db.execute(select(models.Run).where(models.Run.id == run_id))
            db_run = result.scalars().first()
            if not db_run:
                raise NotFoundException("Run not found")
            
            if db_run.status == "completed":
                raise BadRequestException("Cannot send events to a completed run")

            activity = models.Activity(
                run_id=run_id,
                type=activity_in.type,
                payload=activity_in.payload
            )
            db.add(activity)
            await db.commit()
            await db.refresh(activity)

            from ..agent import trigger_agent
            background_tasks.add_task(trigger_agent, run_id)
            
            return activity
        except (NotFoundException, BadRequestException):
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error injecting activity: {e}")
            await db.rollback()
            raise BadRequestException("Failed to inject activity.")

    @staticmethod
    async def change_status(db: AsyncSession, background_tasks: BackgroundTasks, run_id: str, new_status: str):
        try:
            result = await db.execute(select(models.Run).where(models.Run.id == run_id))
            db_run = result.scalars().first()
            if not db_run:
                raise NotFoundException("Run not found")
            
            if db_run.status == "completed" and new_status != "completed":
                raise BadRequestException("Cannot change status of a completed run")
            
            db_run.status = new_status
            
            if new_status == "completed":
                activity = models.Activity(run_id=run_id, type="complete", payload={"reason": "Manual status change"})
                db.add(activity)

            await db.commit()

            if new_status == "active":
                from ..agent import trigger_agent
                background_tasks.add_task(trigger_agent, run_id)
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error changing status: {e}")
            await db.rollback()
            raise BadRequestException("Failed to change status.")
