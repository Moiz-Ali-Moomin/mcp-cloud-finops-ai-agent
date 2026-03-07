# Cloud Provider Integrations

OpsYield MCP FinOps Server abstracts the complexities of querying AWS, GCP, Azure, and Kubernetes through a unified `Provider` interface (`CloudProvider`).

The system uses a **provider factory** (`opsyield/providers/factory.py`) to dynamically load providers at runtime. When the orchestrator executes, it iterates over all loaded providers, ensuring decoupled implementation and simple multi-account aggregation.

## Provider Architecture

All providers must implement a core interface detailing:
- `get_costs(start_date, end_date, metrics)` -> `List[NormalizedCost]`
- `get_infrastructure()` -> `List[Resource]`
- `get_status()` -> `Dict[str, Any]`

This ensures the Analysis Engine receives normalized, strongly-typed data regardless of the underlying cloud structure.

---

## Adding a New Provider

If you wish to add a new top-level provider (e.g., DigitalOcean, Alibaba), you must:
1. Create a collector module in `opsyield/collectors/<provider>`.
2. Create `opsyield/providers/<provider>.py`.
3. Implement a class inheriting from `CloudProvider`.
4. Register the class in `opsyield/providers/factory.py` inside the `_providers` registry dictionary.

Example:
```python
from opsyield.providers.base import CloudProvider
from opsyield.collectors.custom.collector import CustomCollector

class CustomProvider(CloudProvider):
    name = "custom"
    
    def __init__(self, config=None):
        self.collector = CustomCollector()
        
    async def get_costs(self):
        # Translate to NormalizedCost
        ...
```

---

## Amazon Web Services (AWS)
- **Authentication**: Uses `boto3`. Relies on standard chain (e.g., `~/.aws/credentials` or `AWS_ACCESS_KEY_ID`).
- **Billing**: Integrates with AWS Cost Explorer (`ce` service) utilizing the `GetCostAndUsage` API.
- **Resources**: Queries `ec2`, `rds`, and `s3` endpoints.

## Google Cloud Platform (GCP)
- **Authentication**: Uses `google-auth` typically via `GOOGLE_APPLICATION_CREDENTIALS` (Service Account JSON).
- **Billing**: Export to BigQuery is heavily utilized for granular SQL data mapping.
- **Resources**: Uses Google Cloud Compute API to list instances and disks.

## Microsoft Azure
- **Authentication**: Uses `azure-identity` (DefaultAzureCredential).
- **Billing**: Connects to the Azure Resource Manager cost APIs (`azure-mgmt-costmanagement`).
- **Resources**: Uses the Compute SDK (`azure-mgmt-compute`).

## Kubernetes (OpenCost)
- **Authentication**: Assumes internal networking access to the OpenCost API via `OPENCOST_URL`.
- **Billing**: Polls `/allocation` and `/assets` endpoints to group native cloud-provider node costs directly to Kubernetes namespaces, allowing granular pod-level reporting for AI agents.
