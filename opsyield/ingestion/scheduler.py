import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from .jobs import run_all_collectors
from ..core.logging import get_logger

logger = get_logger(__name__)

jobstores = {
    'default': MemoryJobStore()
}

scheduler = AsyncIOScheduler(jobstores=jobstores)

def setup_scheduler():
    # Run every hour at minute 0
    scheduler.add_job(
        run_all_collectors, 
        trigger=CronTrigger(minute=0), 
        id="global_cost_collector", 
        name="Global Cost Collector Job", 
        replace_existing=True
    )
    logger.info("Configured APScheduler with Background Jobs")

def start_scheduler():
    if not scheduler.running:
        setup_scheduler()
        scheduler.start()
        logger.info("Scheduler started.")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down.")
