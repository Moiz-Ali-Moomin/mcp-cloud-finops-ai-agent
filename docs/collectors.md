# Collectors Architecture

In OpsYield, **Collectors** denote the lowest-level access abstraction into a specific infrastructure platform or billing system. 

While the *Provider* acts as a manager parsing and standardizing data to be orchestrated, the *Collector* executes the actual I/O network calls.

## Design Philosophy

- **Stateless Operation**: Collectors should never cache state (the orchestrator handles caching limits). Every `collect()` invocation creates an independent network request stream.
- **Provider-specific Outputs**: Collectors are not forced to return a `NormalizedCost` object. They typically return RAW API schemas (dicts) or standard SDK structures. Normalization is intentionally pushed up to the `Provider`.
- **Paginated Recovery**: Because cloud structures can contain thousands of resources, collectors are responsible for fully paginating API queries automatically.
- **Asynchronous Priority**: Wherever an Async HTTP Client (like `httpx`) is available, or an async SDK framework is present, collectors should exploit it to unblock the main thread. If a blocking SDK like Boto3 must be used, the Collector handles wrapping calls in `asyncio.to_thread()`.

## Examples of Core Collectors

### 1. `collectors/kubernetes/collector.py`
Connects to OpenCost REST `/allocation` API. 
*Input*: OpenCost URL.
*Output*: A dictionary aggregating OpenCost's proprietary schema window blocks into raw namespace accumulations.

### 2. `collectors/aws/ec2.py`
Connects to Boto3's generic client APIs. 
*Input*: AWS Regions.
*Output*: Parsed dict components representing Security Groups, Block Devices mappings, and instance types. 

## Flow

```
+--------------------+
| Analysis Engine    | <- Analyzes normalized patterns
+--------------------+
         ^
+--------------------+
| Orchestrator       | <- Aggregates and loops
+--------------------+
         ^
+--------------------+
| Provider Factory   | <- Normalizes Schema (CloudProvider)
+--------------------+
         ^
+====================+
|     Collectors     | <- Executes raw Paginated I/O
+====================+
```
