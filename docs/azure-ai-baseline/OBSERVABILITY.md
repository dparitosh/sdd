# Observability (Azure AI Baseline)

Baseline expectation: end-to-end traceability across API requests, tool calls, retrieval operations, and agent orchestration.

## Recommended approach
- Use OpenTelemetry for traces/metrics/logs.
- Export traces to Application Insights.

## What to instrument
- FastAPI request spans (route, status, latency)
- Neo4j query spans (query name, duration, result size)
- ToolRegistry call spans (tool name, duration, success/failure)
- Retriever spans (query, top_k, index)
- Orchestrator spans (goal id, plan steps, retries)

## Redaction
Never log:
- credentials/API keys
- full prompts containing secrets
- raw PII

Prefer structured logging with fields:
- `correlation_id`, `request_id`, `tool_name`, `duration_ms`, `error_type`
