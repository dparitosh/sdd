# Deployment Reference (Azure AI Baseline)

This repository stays runnable locally without Azure.

For Azure certification-style deployments, map components as:
- Container Apps / AKS: FastAPI backend + React frontend (static hosting or nginx)
- Azure OpenAI: LLM inference for planning/agent responses
- Azure AI Search: RAG index over MBSE documents, requirements, and graph extracts
- Key Vault: secrets
- Managed Identity: authentication to Search/Key Vault
- App Insights: traces/metrics

## Configuration
See `.env.example` for optional Azure settings.

## Security baseline checklist (high level)
- Enforce authn/authz at API boundary
- Tool allow-lists + read-only policies
- Audit trail for tool calls and data access
- Observability with redaction
