# FDE — Financial Decision Engine (Agentic AI Architecture)

A modular, research-grade **multi-agent financial decision system** integrating
reinforcement learning, risk-aware signal routing, adversarial robustness,
and human-interpretable decision scaffolding.

This monorepo serves as both an **engineering playground** and a **systems architecture prototype**
for enterprise-scale AI decision automation across trading, pricing, risk, and strategic planning domains.

---

## 🎯 Objectives

- Model complex decision environments using **multi-agent RL personas**
- Explore **risk–reward tradeoffs** under uncertainty and adversarial noise
- Prototype **route-based execution engines** for dynamic signal allocation
- Build an architecture that is:
  - composable
  - introspectable
  - simulation-first
  - production-adaptable

---

## 🧠 Core Concepts

### 🧩 Agent Personas
The system organizes logic into cooperative / adversarial personas such as:

- **Alpha** — opportunity seeking, signal extraction  
- **Convexity** — asymmetric payoff hunting  
- **Guardian** — downside control & safety margins  
- **Liquidity** — execution & capital flow stability  
- **Router** — allocates authority across personas  

Each persona reasons independently and contributes to a **shared decision surface**.

---

## 🛠️ Repository Structure

architecture/ — system diagrams, patterns, conceptual scaffolding
engine/ — core execution + routing logic
kernel/ — foundational primitives & shared utilities
personas/ — agent persona modules and behavior definitions
notebooks/ — research, simulations, exploratory modeling
infra/ — deployment & environment scaffolding
pp-gate-worker/ — Cloudflare worker experiments (gating / telemetry)
tiny_universe/ — lightweight simulation sandboxes
assets/ — diagrams, artifacts, visual models
docs/ — design notes and long-form architecture writing



---

## 🧪 Experiments & Simulation Focus

This project emphasizes **sandbox-first development**:

- scenario replay & counterfactual testing  
- robustness under perturbation and noise  
- explainable routing decisions  
- persona-level outcome attribution  

The goal is understanding **how** the system reasons — not just whether it performs.

---

## 🚧 Status

> ⚠️ Work-in-progress, evolving architecture.  
> Modules may be experimental, speculative, or intentionally exploratory.

This repo is intended for **research, iteration, and conceptual validation** —
not a drop-in production trading system.

---

## 🌌 Philosophy

FDE is built on the belief that **financial and strategic decision systems** should be:

- transparent instead of opaque  
- multi-perspective instead of monolithic  
- resilient instead of brittle  
- human-interpretable instead of black-box  

This project explores what that future could look like.

---

## 👤 Author

**Yinan Yang**  
Architect & Builder — Agentic AI Systems, Decision Intelligence, and RL-Driven Simulation

- Portfolio & research interests: multi-agent architectures, risk-aware routing,
  adversarial robustness, and interpretable decision pipelines.
- This project reflects an ongoing exploration of **how complex financial reasoning
  can be structured, modularized, and made auditable**.

If you are evaluating this work for collaboration, research alignment,
or advanced architecture roles, feel free to connect.


