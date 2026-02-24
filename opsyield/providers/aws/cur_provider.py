"""
AWS CUR (Cost and Usage Report) Provider
Uses Athena to query CUR data for granular, resource-level cost and usage information.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

try:
    import boto3
    from botocore.exceptions import ClientError
    from botocore.config import Config
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

from ...core.models import NormalizedCost

logger = logging.getLogger("opsyield-aws-cur")

class AWSCurProvider:
    def __init__(
        self, 
        athena_database: str, 
        athena_table: str, 
        s3_output_location: str,
        region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        role_arn: Optional[str] = None
    ):
        self.athena_database = athena_database
        self.athena_table = athena_table
        self.s3_output_location = s3_output_location
        self.region = region
        
        if not HAS_BOTO3:
            logger.error("boto3 is not installed")
            return
            
        # Authentication
        session_kwargs = {}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key
            
        session = boto3.Session(**session_kwargs)
        
        if role_arn:
            sts = session.client('sts')
            assumed = sts.assume_role(
                RoleArn=role_arn,
                RoleSessionName="OpsYieldCURSession"
            )
            creds = assumed['Credentials']
            session = boto3.Session(
                aws_access_key_id=creds['AccessKeyId'],
                aws_secret_access_key=creds['SecretAccessKey'],
                aws_session_token=creds['SessionToken']
            )

        self.athena = session.client('athena', region_name=self.region, config=Config(retries={'max_attempts': 10}))

    async def get_costs(self, days: int = 30) -> List[NormalizedCost]:
        """Fetch resource level costs from CUR via Athena for the last N days."""
        if not HAS_BOTO3:
            return []
            
        return await asyncio.to_thread(self._sync_get_costs, days)

    def _sync_get_costs(self, days: int) -> List[NormalizedCost]:
        # Formulate query
        # We query line_item_usage_start_date, line_item_product_code, line_item_resource_id, line_item_unblended_cost
        
        query = f"""
        SELECT 
            line_item_usage_start_date as usage_date,
            line_item_product_code as service,
            product_region as region,
            line_item_resource_id as resource_id,
            line_item_usage_account_id as account_id,
            SUM(line_item_unblended_cost) as cost
        FROM {self.athena_database}.{self.athena_table}
        WHERE 
            line_item_usage_start_date >= current_date - interval '{days}' day
            AND line_item_line_item_type IN ('Usage', 'SavingsPlanCoveredUsage')
        GROUP BY 
            line_item_usage_start_date,
            line_item_product_code,
            product_region,
            line_item_resource_id,
            line_item_usage_account_id
        HAVING SUM(line_item_unblended_cost) > 0
        """
        
        try:
            response = self.athena.start_query_execution(
                QueryString=query,
                ResultConfiguration={'OutputLocation': self.s3_output_location}
            )
            query_execution_id = response['QueryExecutionId']
            
            # Wait for query to complete
            while True:
                status = self.athena.get_query_execution(QueryExecutionId=query_execution_id)
                state = status['QueryExecution']['Status']['State']
                if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                    break
                time.sleep(2)  # Wait before checking again
                
            if state != 'SUCCEEDED':
                logger.error(f"Athena query failed: {status['QueryExecution']['Status'].get('StateChangeReason')}")
                return []
                
            # Paginate through results
            results = []
            paginator = self.athena.get_paginator('get_query_results')
            pages = paginator.paginate(QueryExecutionId=query_execution_id)
            
            is_header = True
            for page in pages:
                for row in page['ResultSet']['Rows']:
                    if is_header:
                        is_header = False
                        continue
                        
                    data = row['Data']
                    # Athena result format: [date, service, region, resource_id, account_id, cost]
                    try:
                        timestamp_str = data[0].get('VarCharValue', '')
                        if not timestamp_str:
                            continue
                        
                        # Handle Athena timestamp format
                        try:
                            ts = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
                        except ValueError:
                            ts = datetime.strptime(timestamp_str.split('.')[0], "%Y-%m-%d %H:%M:%S")

                        cost_val = float(data[5].get('VarCharValue', 0.0))
                        if cost_val <= 0:
                            continue

                        norm_cost = NormalizedCost(
                            provider="aws",
                            service=data[1].get('VarCharValue', 'Unknown'),
                            region=data[2].get('VarCharValue', 'us-east-1'),
                            resource_id=data[3].get('VarCharValue', ''),
                            account_id=data[4].get('VarCharValue', ''),
                            cost=cost_val,
                            currency="USD",
                            timestamp=ts
                        )
                        results.append(norm_cost)
                    except Exception as e:
                        logger.warning(f"Error parsing Athena row: {e} - Row: {data}")
                        continue
                        
            return results
        except ClientError as e:
            logger.error(f"AWS Athena error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying CUR: {e}")
            return []
