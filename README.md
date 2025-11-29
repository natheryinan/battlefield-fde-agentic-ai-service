# battlefield-agentic-fde-ai-ops

Forward-Deployed **Battlefield Agentic AI Ops** — an end-to-end reference system
for the **Forward-Deployed Research Engineer (FDRE)** role.

This repo shows how you think and operate as an FDE:

- Own the **full lifecycle**: prototype → ship → monitor → iterate
- Build **agentic / LLM systems** that survive real-world conditions
- Treat deployment, reliability, and observability as **first-class features**

---

## 🧠 System Overview

The system exposes a simple but realistic agentic pipeline:

1. A `PlannerAgent` decomposes a user task into structured steps.
2. A `RetrievalAgent` (stub) would talk to a RAG / search layer.
3. An `ExecutionAgent` (stub) would call tools / APIs to execute each step.
4. A FastAPI service exposes HTTP endpoints for planning and running missions.
5. An Ops layer provides hooks for logging, drift detection, and evaluation.

This is intentionally lightweight so it can run on a laptop, but the structure
mirrors how a production FDE system would be organized.

---

## 🚀 Quickstart

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# run the API
uvicorn src.deployment.api.main:app --reload
```

Then open: `http://127.0.0.1:8000/docs`

Try the `/plan` and `/run-mission` endpoints.

---

## 📂 Project Layout

```text
battlefield-agentic-fde-ai-ops/
├── README.md
├── requirements.txt
├── architecture/
│   └── system_overview.md
├── src/
│   ├── agents/
│   │   ├── planner_agent.py
│   │   ├── retrieval_agent.py
│   │   ├── execution_agent.py
│   │   └── tools/
│   │       ├── search_tool.py
│   │       └── echo_tool.py
│   ├── llm/
│   │   ├── inference_client.py
│   │   └── prompt_templates.py
│   ├── deployment/
│   │   └── api/
│   │       └── main.py
│   ├── ops/
│   │   ├── monitoring.py
│   │   └── evaluation_suite.py
│   └── utils/
│       ├── config.py
│       └── logger.py
├── notebooks/
│   └── experiments.ipynb
├── tests/
│   ├── test_agents.py
│   └── test_api.py
└── infra/
    └── terraform/
        └── main.tf
```

You can gradually replace the stubs with real logic (RAG, vector DBs,
Kubernetes manifests, Terraform modules, etc.) while keeping the same
battlefield-proven layout.

---

## 🧪 FDE Story You Can Tell

This repo lets you tell a clear story in interviews:

- How you design **agentic systems** (Planner / Retrieval / Execution agents)
- How you wrap them in a **clean API** ready for embedding at a customer
- How you think about **observability, evaluation, and iteration**
- How you would extend this into a **multi-tenant, production deployment**

