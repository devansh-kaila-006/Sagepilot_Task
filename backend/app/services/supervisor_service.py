from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from typing import List
from ..models import domain as models
from ..schemas import domain as schemas
from ..core.exceptions import NotFoundException, BadRequestException
import logging

logger = logging.getLogger(__name__)

class SupervisorService:
    @staticmethod
    async def create_supervisor(db: AsyncSession, supervisor_in: schemas.SupervisorCreate) -> models.Supervisor:
        try:
            db_supervisor = models.Supervisor(**supervisor_in.model_dump())
            db.add(db_supervisor)
            await db.commit()
            await db.refresh(db_supervisor)
            return db_supervisor
        except SQLAlchemyError as e:
            logger.error(f"Database error creating supervisor: {e}")
            await db.rollback()
            raise BadRequestException("Failed to create supervisor due to database error.")

    @staticmethod
    async def get_supervisors(db: AsyncSession) -> List[models.Supervisor]:
        try:
            result = await db.execute(select(models.Supervisor))
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching supervisors: {e}")
            raise BadRequestException("Failed to fetch supervisors.")

    @staticmethod
    async def get_supervisor(db: AsyncSession, supervisor_id: int) -> models.Supervisor:
        try:
            result = await db.execute(select(models.Supervisor).where(models.Supervisor.id == supervisor_id))
            db_supervisor = result.scalars().first()
            if not db_supervisor:
                raise NotFoundException("Supervisor not found")
            return db_supervisor
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching supervisor: {e}")
            raise BadRequestException("Failed to fetch supervisor.")
