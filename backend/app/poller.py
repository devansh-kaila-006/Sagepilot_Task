import logging
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.future import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .core.database import async_session
from .models import domain as models

logger = logging.getLogger(__name__)

async def poll_sleeping_runs():
    logger.debug("Polling for sleeping runs to wake up...")
    
    # Needs to run in a separate context to avoid import cycles, but we can just import trigger_agent locally
    from .agent import trigger_agent
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    async with async_session() as db:
        result = await db.execute(
            select(models.Run)
            .where(models.Run.status == "sleeping")
            .where(models.Run.next_wake_at <= now)
        )
        runs_to_wake = list(result.scalars().all())
        
        stale_threshold = now - timedelta(minutes=5)
        stale_result = await db.execute(
            select(models.Run)
            .where(models.Run.status.in_(["active", "processing"]))
            .where(models.Run.next_wake_at.is_(None))
            .where(models.Run.updated_at < stale_threshold)
        )
        stale_runs = list(stale_result.scalars().all())
        
        runs_to_wake.extend(stale_runs)
        
        for run in runs_to_wake:
            logger.info(f"Waking up run {run.id} due to schedule or crash recovery")
            
            # Record wake event
            activity = models.Activity(
                run_id=run.id,
                type="wake",
                payload={"reason": "scheduled_or_recovery"}
            )
            db.add(activity)
            
            # Update status
            run.status = "active"
            run.next_wake_at = None
            # Same-value writes are skipped by SQLAlchemy, so bump updated_at
            # explicitly to prevent the next poll tick from re-claiming this run.
            run.updated_at = now
            await db.commit()
            
            # Fire and forget the agent trigger
            asyncio.create_task(trigger_agent(run.id))

def start_poller():
    scheduler = AsyncIOScheduler()
    # Poll every 10 seconds for POC purposes
    scheduler.add_job(poll_sleeping_runs, 'interval', seconds=10)
    scheduler.start()
    logger.info("Background poller started.")
