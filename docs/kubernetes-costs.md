# Kubernetes Cost Intelligence via OpenCost

The Kubernetes environment is inherently multi-tenant, making traditional cloud-billing mechanisms like AWS Cost Explorer or Azure Cost Management ineffective at determining pod-level spend. 

OpsYield solves this using the **OpenCost REST API**, establishing Kubernetes as a top-level provider dynamically injected into the Orchestrator via the `ProviderFactory`.

## How It Works

1. **Integration Target**: OpenCost running inside the Kubernetes cluster.
2. **Data Collector (`opsyield/collectors/kubernetes`)**: Uses the asynchronous `httpx` HTTP client to communicate with the `http://<opencost-layer>:9003` endpoints.
3. **Data Provider (`opsyield/providers/kubernetes.py`)**: Subclasses `CloudProvider` to merge the JSON responses into standard unified dictionaries.

### Fetching Allocation Data (`/allocation`)

The `OpenCostClient.get_allocation()` method retrieves recent trailing node vs. container workload expense metrics. The Orchestrator subsequently organizes this data into `NormalizedCost` objects using the `<namespace>` taxonomy.

```json
{
  "provider": "kubernetes",
  "namespaces": {
      "payments": 140.25,
      "auth": 52.10
  }
}
```

This ensures an AI Agent answering a prompt ("Show me my spend across AWS and Kubernetes") can return uniform tabular data.

### Environment Requirements

You only need to define a single Environment Variable for this module to engage:

```bash
OPENCOST_URL=http://localhost:9003
```

By default, if this is not provided, the fallback logic will attempt `localhost:9003`. If connection fails during the `get_status()` parallel factory ping, the Kubernetes module drops out seamlessly without crashing the other cloud provider queries.
