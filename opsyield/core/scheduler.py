import asyncio
from typing import List
from .orchestrator import Orchestrator
from .logging import get_logger

logger = get_logger(__name__)

class Scheduler:
    def __init__(self, interval_minutes: int = 10, providers: List[str] = None):
        self.interval_minutes = interval_minutes
        self.providers = providers or ["aws", "gcp", "azure"]
        self.orchestrator = Orchestrator()
        self.running = False

    async def start(self):
        logger.info(f"Starting scheduler. Interval: {self.interval_minutes}m, Providers: {self.providers}")
        self.running = True
        while self.running:
            try:
                logger.info("Scheduler: Triggering analysis cycle...")
                # Run for all providers in parallel
                result = await self.orchestrator.aggregate_analysis(self.providers, days=30)
                
                # Here we would typically save the result to DB/Storage
                # For now, just log summary
                summary = result.summary
                logger.info(f"Analysis complete. Total Cost: ${summary.get('total_cost', 0):.2f}, Resources: {summary.get('resource_count')}")
                
            except Exception as e:
                logger.error(f"Scheduler cycle failed: {e}")

            logger.info(f"Sleeping for {self.interval_minutes} minutes...")
            await asyncio.sleep(self.interval_minutes * 60)

    def stop(self):
        self.running = False
