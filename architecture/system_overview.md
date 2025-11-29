# System Overview

This document describes the high-level architecture of the Battlefield Agentic FDE AI Ops system.

- **API Layer**: FastAPI service exposing `/plan` and `/run-mission`.
- **Agent Layer**: Planner, Retrieval, and Execution agents composing an agentic workflow.
- **LLM Layer**: `LLMClient` abstraction that can wrap OpenAI, Anthropic, or local models.
- **Ops Layer**: Monitoring + evaluation hooks for real-world reliability.

In a real FDRE deployment this would be extended with:
- RAG / search backend (vector DB, BM25, hybrid retrieval).
- Kubernetes deployment and Terraform-managed infrastructure.
- Observability stack (metrics, logs, traces).
