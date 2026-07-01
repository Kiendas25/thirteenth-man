# 13th Man — Multi-Agent Cognitive Operating System

A multi-agent system built on the "13th Man" concept: an orchestrator (Jarvis) coordinates specialist agents activated on demand, while an adversarial verifier (the 13th Man) challenges every conclusion before it reaches the user.

## Architecture

```
User Request
    |
    v
  Jarvis (Orchestrator)
    |-- classifies task
    |-- selects specialists
    v
  Specialists (activated on demand)
    |-- Coding, Research, Writing, Security,
    |-- Financial, ML, Creativity, Auditing,
    |-- Automation, Knowledge
    v
  13th Man (Adversarial Verifier)
    |-- challenges conclusions
    |-- checks for flaws, risks, inconsistencies
    v
  Trust Layer
    |-- human approvals for sensitive actions
    |-- execution tracing
    |-- persistent memory
    v
  Final Answer
```

### Four Layers

1. **Orchestration** — Jarvis plans, decomposes, routes, and consolidates
2. **Specialists** — activated only when needed (not a parliament of 12 agents)
3. **Adversarial Verification** — the 13th Man falsifies with evidence and protocol
4. **Operational Control** — approvals, sandboxing, tracing, memory

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your OpenAI API key

# Run
python main.py
```

Open http://localhost:8000 in your browser.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/tasks` | Submit a task to the multi-agent system |
| GET | `/api/tasks` | List recent tasks |
| GET | `/api/tasks/{id}` | Get full task detail with trace |
| GET | `/api/agents` | List available specialist agents |
| GET | `/api/approvals` | List pending approvals |
| POST | `/api/approvals/{id}` | Approve or reject an action |
| GET | `/api/memory?q=` | Search memory entries |

## Specialist Agents

| Agent | Role |
|-------|------|
| Autonomous Coding | Technical execution (sandboxed) |
| Research & Intelligence | Breadth-first research |
| Technical Writing | Synthesis & documentation |
| Security & Compliance | Gatekeeper with veto power |
| Quant / Financial | Analysis (never executes orders) |
| Machine Learning | Models, pipelines, evaluation |
| Creativity & Ideation | Divergent thinking |
| AI Auditing | Output & trajectory evaluation |
| Workflow Automation | Integration & playbooks |
| Knowledge Management | Memory & retrieval infrastructure |

## The 13th Man Protocol

The adversarial verifier follows a strict falsification protocol:

1. Check logical consistency between specialist outputs
2. Challenge unstated assumptions
3. Find counter-examples that would break the solution
4. Verify claims are supported by evidence
5. Assess operational risks (injection, exfiltration, excessive autonomy)
6. Check completeness of the analysis

The 13th Man only approves when it **cannot refute** the conclusion.
