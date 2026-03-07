# Architecture Overview

The OpsYield MCP FinOps Server is designed as a modular, extensible backend providing real-time cloud cost intelligence to AI agents (such as Claude). This document outlines the high-level architecture, the flow of operations, and the core components of the system.

## System Architecture

The server acts as a middleman between an AI client and various cloud providers. It uses the Model Context Protocol (MCP) to standardize communication, taking natural language intents from an AI agent, translating them into structured queries, fetching data from cloud APIs, and synthesizing actionable recommendations.

### Core Layers

1.  **Transport Layer**: Handles the MCP standard communication over `stdio` or `SSE`.
2.  **API / Entrypoint Layer**: Defines the tools and exposed operations (e.g., `analyze_costs`, `find_idle_resources`).
3.  **Orchestrator**: Acts as the central nervous system. It routes incoming requests to the appropriate cloud provider implementations using the dynamic `ProviderFactory`.
4.  **Providers**: Wrappers around collectors that normalize inputs and outputs into standard `Resource` or `NormalizedCost` objects.
5.  **Collectors**: Native integrations that talk directly to cloud SDKs or REST APIs (like OpenCost, AWS Boto3, Azure SDK).
6.  **Analysis Engine**: Processes the raw data fetched by the collectors to uncover insights (e.g., cost spikes, underutilized assets).
7.  **Optimization Engine**: Generates specific, actionable recommendations based on the analysis.

## MCP Server Flow

1.  **Initialization**: The AI Client sends an `initialize` request to the MCP server.
2.  **Discovery**: The Client requests a list of available tools. The Server replies with functions like `get_cost_summary` and `analyze_waste`.
3.  **Execution Request**: The user asks the AI "What are my AWS costs this month?" The AI translates this to a tool call (`get_cost_summary`, `provider=aws`).
4.  **Orchestration**: The Orchestrator receives the parsed request and injects the proper Provider abstraction.
5.  **Data Collection**: The assigned Provider calls its nested Collector to query the respective provider’s API.
6.  **Processing**: The Analysis Engine transforms the raw structured JSON into cost trends and identifying metadata.
7.  **Response Synthesis**: The server returns a structured Markdown/JSON payload back to the AI Client.

## Orchestration Pipeline

The orchestrator sits at the heart of the system. It uses a Factory pattern (`opsyield/providers/factory.py`) to instantiate the right cloud client dynamically based on the requested `provider` or the ambient configuration. 

It is responsible for cross-cloud aggregation if a request queries multiple providers simultaneously. For example, a single prompt "What are my costs?" forces the orchestrator to ping the factory for all registered active providers (AWS, GCP, Azure, Kubernetes) and aggregates the Normalized schema into a unified response for the AI Agent.

## Analysis & Optimization Strategies

-   **Analysis Engine**: Uses heuristics and historical data comparisons (e.g., month-over-month) to highlight statistically significant spend changes.
-   **Optimization Strategies**: Implements discrete logic blocks specific to resource types:
    -   *Idle Compute*: Checks CPU/Network utilization metrics via CloudMonitor/CloudWatch.
    -   *Orphaned Disks*: Scans for unattached EBS/Persistent Disks.
    -   *Rightsizing*: Suggests smaller instance families based on max observed peak usage.
