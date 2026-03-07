# Cloud Provider Integrations

OpsYield MCP FinOps Server abstracts the complexities of querying AWS, GCP, and Azure through a unified `Provider` interface.

## Provider Architecture

All providers must implement a core interface detailing:
- `get_cost_summary(start_date, end_date, metrics)`
- `get_idle_resources()`
- `get_optimization_recommendations()`

This ensures the Analysis Engine receives normalized data regardless of the underlying cloud structure.

---

## Amazon Web Services (AWS)

### Authentication
Uses `boto3`. Relies on the standard AWS credentials chain (e.g., `~/.aws/credentials` or `AWS_ACCESS_KEY_ID` environment variables).

### Billing API
Integrates with AWS Cost Explorer (`ce` service) utilizing the `GetCostAndUsage` API. Requires specific IAM permissions on the executing role.

### Resource Collectors
Queries `ec2`, `rds`, and `s3` endpoints to gather metadata on instance types, attachment states, and bucket sizes.

---

## Google Cloud Platform (GCP)

### Authentication
Uses `google-auth` and defaults to `google.auth.default()`. It typically relies on `GOOGLE_APPLICATION_CREDENTIALS` pointing to a local Service Account JSON file.

### Billing API
Unlike AWS, GCP recommends exporting detailed billing data to **BigQuery**. OpsYield integrates with BigQuery, running SQL queries against the exported billing table to generate aggregations.

### Resource Collectors
Uses Google Cloud Compute API to list instances and disks, identifying orphaned or underutilized resources.

---

## Microsoft Azure

### Authentication
Uses `azure-identity` (specifically `DefaultAzureCredential`), pulling from Environment Variables, Azure CLI, or Managed Identities.

### Billing API
Connects to the Azure Resource Manager and the specific `azure-mgmt-costmanagement` SDK to execute cost queries scoped to an Azure Subscription or Management Group.

### Resource Collectors
Uses the Compute SDK (`azure-mgmt-compute`) to analyze VMs and unattached managed disks.
