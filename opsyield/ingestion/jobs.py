"""
OpsYield Background Ingestion jobs
"""
import asyncio
import json
from ..storage.database import async_session_maker
from ..storage.repository import CloudAccountRepository, CostRepository
from ..providers.aws.cur_provider import AWSCurProvider
from ..core.logging import get_logger
# NOTE: other providers would be mapped similarly (gcp, azure)

logger = get_logger(__name__)

async def fetch_and_store_costs_for_account(account_id: str):
    logger.info(f"Starting cost collection for internal account_id: {account_id}")
    async with async_session_maker() as session:
        repo = CloudAccountRepository(session)
        cost_repo = CostRepository(session)
        
        account = await repo.get_by_id(account_id)
        if not account or not account.is_active:
            logger.warning(f"Account {account_id} not found or inactive.")
            return

        provider_costs = []
        try:
            creds = json.loads(account.credentials_json)
            
            if account.provider == "aws" and "athena_database" in creds:
                # AWS CUR flow
                provider = AWSCurProvider(
                    athena_database=creds["athena_database"],
                    athena_table=creds["athena_table"],
                    s3_output_location=creds["s3_output_location"],
                    aws_access_key_id=creds.get("aws_access_key_id"),
                    aws_secret_access_key=creds.get("aws_secret_access_key"),
                    role_arn=creds.get("role_arn")
                )
                provider_costs = await provider.get_costs(days=1)
            else:
                # Fallback to standard provider or mock
                logger.info(f"Skipping native collection for provider {account.provider} (not fully implemented in background)")
        except Exception as e:
            logger.error(f"Failed to fetch costs for account {account_id}: {e}")
            return

        # Store in DB
        for cost in provider_costs:
            try:
                await cost_repo.create({
                    "organization_id": account.organization_id,
                    "cloud_account_id": account.id,
                    "provider": cost.provider,
                    "service": cost.service,
                    "resource_id": getattr(cost, "resource_id", ""),
                    "region": cost.region,
                    "cost": cost.cost,
                    "currency": cost.currency,
                    "timestamp": cost.timestamp
                })
            except Exception as e:
                logger.error(f"Error saving cost record: {e}")

async def run_all_collectors():
    """Fetch costs for all active cloud accounts."""
    logger.info("Running global cost collector job")
    async with async_session_maker() as session:
        repo = CloudAccountRepository(session)
        # We need all active accounts across all orgs
        # Custom query for this job
        from sqlalchemy import select
        from ..storage.models import CloudAccount
        
        result = await session.execute(select(CloudAccount).where(CloudAccount.is_active == True))
        accounts = result.scalars().all()
        
    tasks = [fetch_and_store_costs_for_account(acc.id) for acc in accounts]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Completed global cost collector job")
