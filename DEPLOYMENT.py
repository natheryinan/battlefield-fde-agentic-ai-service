
fde-agentic-ai-ops/
│
├── README.md
├── architecture/
│   ├── system_overview.png
│   ├── agent_flow.png
│   ├── deployment_diagram.png
│
├── src/
│   ├── agents/
│   │   ├── planner_agent.py
│   │   ├── executor_agent.py
│   │   ├── retrieval_agent.py
│   │   ├── tools/
│   │   │   ├── search_tool.py
│   │   │   ├── api_call_tool.py
│   │   │   ├── database_query_tool.py
│   │
│   ├── llm/
│   │   ├── prompt_templates.py
│   │   ├── inference_client.py
│   │   ├── rag_pipeline.py
│   │
│   ├── deployment/
│   │   ├── api/
│   │   │   ├── main.py
│   │   │   ├── routers/
│   │   ├── docker/
│   │   │   ├── Dockerfile
│   │   │   ├── entrypoint.sh
│   │   ├── k8s/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │
│   ├── ops/
│   │   ├── monitoring.py
│   │   ├── drift_detection.py
│   │   ├── evaluation_suite.py
│   │
│   ├── data/
│   │   ├── raw/
│   │   ├── processed/
│   │
│   ├── utils/
│   │   ├── logger.py
│   │   ├── config.py
│
├── notebooks/
│   ├── experiments.ipynb
│   ├── evaluation.ipynb
│
├── tests/
│   └── test_agents.py
│   └── test_rag.py
│
├── infra/
│   ├── terraform/
│   │   ├── main.tf
│   ├── cdk/
│       ├── app.py
│
└── requirements.txt
