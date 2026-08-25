# awesome-ai-profile
> An AI-powered interactive professional profile and engineering portfolio.

[Link to the platform](https://proud-mud-0ed95371e.7.azurestaticapps.net/)

Instead of reading a static résumé, recruiters can talk to an AI assistant that understands Jeyker Salinas' professional background, projects, technical skills, education and engineering decisions.

The goal of this repository is twofold:

1. Build a useful interactive portfolio for recruiters.
2. Demonstrate, with working software, the skills companies currently expect from AI Engineers: software engineering, LLMs, RAG, agents, tool calling, evaluation, observability, cloud deployment and CI/CD.

---

## Product idea

A recruiter opens the application and sees a simple conversational interface.

Suggested prompts might include:

- Why should we hire Jeyker?
- What AI projects has Jeyker built?
- Does Jeyker have production experience with Vue and TypeScript?
- What is his experience with RAG and LLM applications?
- Is he comfortable working full stack?
- What technologies were used to build this CV?
- Show me evidence that he can deploy software.
- Send Jeyker a message.
- Summarize Jeyker's experience for an AI Engineer role.
- Why should we hire Jeyker?
- What has he actually built with AI?
- Explain this project's architecture.
- Is this just an LLM wrapper?
- What are Jeyker's weaknesses?
- Why is this CV talking to me?
- Why is this profile unnecessarily overengineered?
- Convince me to hire Jeyker in 30 seconds

The assistant does not answer from a hard-coded FAQ.

It retrieves relevant information from a curated knowledge base containing the CV, project descriptions, technical notes and selected professional history, then builds a grounded response.

For some requests, the assistant can use tools. For example, a recruiter may ask the assistant to send Jeyker a contact message. Tool execution must be explicit, auditable and protected against abuse.

---

# Why this project exists

AI Engineer roles increasingly sit between Software Engineering, Machine Learning and Product Engineering.

Companies are looking for engineers who can:

- build applications with LLMs;
- implement RAG;
- build tool-using AI agents;
- expose AI functionality through APIs;
- work with structured and unstructured data;
- evaluate model outputs;
- monitor AI systems;
- deploy services to cloud infrastructure;
- use Docker and CI/CD;
- reason about latency, reliability, cost and security;
- communicate technical decisions clearly.

This repository is designed to demonstrate those capabilities in one small but complete system.

---

# Architecture

```text
                         ┌────────────────────────────┐
                         │        Recruiter           │
                         └──────────────┬─────────────┘
                                        │
                                        ▼
                         ┌────────────────────────────┐
                         │ Vue 3 + TypeScript         │
                         │ Interactive Chat UI        │
                         └──────────────┬─────────────┘
                                        │ HTTPS / SSE
                                        ▼
                         ┌────────────────────────────┐
                         │ FastAPI Backend            │
                         │ Auth · Rate Limit · API    │
                         └──────────────┬─────────────┘
                                        │
                                        ▼
                         ┌────────────────────────────┐
                         │ AI Agent / Orchestrator    │
                         │ LangGraph                  │
                         └───────┬─────────┬──────────┘
                                 │         │
                      retrieve   │         │ tools
                                 ▼         ▼
                    ┌────────────────┐   ┌──────────────────┐
                    │ RAG Pipeline   │   │ Tool Layer       │
                    │ embeddings     │   │ contact/email    │
                    │ reranking      │   │ profile actions  │
                    └───────┬────────┘   └──────────────────┘
                            │
                            ▼
                    ┌────────────────┐
                    │ PostgreSQL     │
                    │ + pgvector     │
                    └────────────────┘

                            │
                            ▼
                    ┌────────────────┐
                    │ LLM Provider   │
                    │ swappable      │
                    └────────────────┘

             Observability · Evals · CI/CD · Cloud
```

---

# Proposed technology stack

## Frontend

- Vue 3
- TypeScript
- Vite
- Nuxt UI + Tailwind CSS
- Vercel AI SDK for Vue (`@ai-sdk/vue`)
- Browser-detected English/Spanish localization with English fallback and a persistent language switcher
- System-aware light/dark themes using the Django brand palette
- Pinia
- Vue Router
- Vitest
- Playwright
- HTTP/SSE with the AI SDK UI Message Stream Protocol

Why Vue?

Because the project should demonstrate deep engineering ability rather than hide existing experience. The frontend will be kept intentionally polished and strongly typed while most new learning happens in the AI, backend and infrastructure layers.

---

## Backend

- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- pytest

Responsibilities:

- chat API;
- streaming responses;
- orchestration entry point;
- authentication/security controls;
- tool execution;
- retrieval APIs;
- health checks;
- telemetry;
- persistence.

---

## LLM and agent layer

Initial stack:

- LangGraph for orchestration
- provider-independent LLM interface
- structured outputs with Pydantic
- tool/function calling
- explicit agent state
- retry/fallback policies

Possible providers:

- Gemini free/low-cost tier during development;
- local models through Ollama for local experimentation;
- another hosted provider can be added through the same abstraction.

The architecture should avoid coupling the application to a single model vendor.

---

# RAG

The assistant will receive factual context about Jeyker from a small curated knowledge base.

Example sources:

```text
knowledge/
├── cv.md
├── profile.md
├── education.md
├── projects/
│   ├── rag-education-platform.md
│   ├── conversational-ai-platform.md
│   ├── realtime-monitoring.md
│   └── vue-migration.md
└── skills/
    ├── frontend.md
    ├── backend.md
    ├── ai.md
    └── cloud.md
```

Pipeline:

```text
documents
   ↓
clean / chunk
   ↓
embeddings
   ↓
pgvector
   ↓
semantic retrieval
   ↓
optional reranking
   ↓
context
   ↓
LLM
   ↓
grounded answer + sources
```

The UI should expose the sources used for important factual answers.

This is important: the goal is not merely to demonstrate that an LLM can talk. It is to demonstrate that an AI system can produce traceable answers based on controlled information.

---

# Agent tools

The assistant will gradually gain a small number of safe tools.

### `get_profile_section`

Returns structured CV information.

### `search_experience`

Searches projects and professional experience.

### `create_contact_request`

Stores a recruiter contact request.

### `send_contact_email`

Optional advanced feature.

Sends a message to Jeyker after server-side validation and abuse protection.

The AI model never receives raw email credentials.

All tools will have:

- typed schemas;
- validation;
- authorization rules;
- rate limits;
- audit logs;
- explicit success/error responses.

---

# Security and responsible AI

Because this is a public-facing AI application, security is part of the project rather than an afterthought.

Planned controls:

- prompt-injection-aware retrieval;
- system prompt isolation;
- strict tool schemas;
- server-side tool authorization;
- input size limits;
- rate limiting;
- secrets stored outside source control;
- PII minimization;
- audit logs for side effects;
- allow-listed tool behavior;
- output validation;
- dependency scanning.

The assistant must never invent professional experience that does not exist in the knowledge base.

When evidence is insufficient, it should say so.

---

# Evaluation

AI systems need tests beyond unit tests.

A small evaluation dataset will contain questions such as:

```json
{
  "question": "Does Jeyker have experience with RAG?",
  "expected_facts": [
    "FastAPI",
    "LlamaIndex",
    "LangChain",
    "vector databases"
  ]
}
```

Evaluation dimensions:

- answer correctness;
- groundedness;
- retrieval relevance;
- hallucination rate;
- tool-call correctness;
- latency;
- token usage;
- estimated cost.

The repository will include repeatable offline evaluations so changes to prompts, models or retrieval can be compared instead of judged by intuition.

---

# Observability / LLMOps

Planned telemetry:

- request latency;
- model latency;
- retrieval latency;
- prompt/model version;
- token consumption;
- tool calls;
- failures;
- traces;
- user feedback.

Potential tooling:

- OpenTelemetry
- Langfuse or Phoenix
- structured application logs

The exact vendor is secondary.

The objective is to understand what the AI system is doing in production.

---

# Database

PostgreSQL will store:

- recruiter sessions;
- conversations;
- messages;
- contact requests;
- knowledge metadata;
- evaluation results;
- audit events.

`pgvector` will store embeddings.

Using PostgreSQL + pgvector keeps the first production architecture intentionally simple while still demonstrating vector search.

A dedicated vector database can later be evaluated if scale or functionality justifies it.

---

# Containerization

Services will run locally with Docker Compose.

```text
docker-compose.yml

frontend
backend
postgres + pgvector
optional local LLM
observability service
```

Production images will use multi-stage Docker builds.

---

# CI/CD

GitHub Actions will eventually run:

```text
push / pull request
        ↓
frontend lint + typecheck
        ↓
frontend tests
        ↓
backend lint
        ↓
backend tests
        ↓
AI evaluation smoke tests
        ↓
build Docker images
        ↓
security/dependency checks
        ↓
deploy
```

The repository should always show whether the current commit passes CI.

---

# Cloud

The first cloud deployment should intentionally use a small number of managed services.

A possible AWS architecture:

```text
CloudFront / static hosting
          │
          ▼
     Vue frontend

          │
          ▼

 Application Load Balancer
          │
          ▼
 ECS Fargate / container
     FastAPI backend
          │
     ┌────┴─────┐
     ▼          ▼
 RDS Postgres   External/managed LLM
 + pgvector
```

Supporting AWS services may include:

- S3
- CloudFront
- ECS/Fargate
- ECR
- RDS PostgreSQL
- Secrets Manager
- CloudWatch
- IAM

The deployment target may change during implementation if another platform produces a substantially cheaper architecture, but the project must demonstrate the same concepts:

**container → cloud service → managed database → secrets → monitoring → CI/CD.**

---

# Engineering principles

This project intentionally prioritizes:

1. working software over architectural theatre;
2. simple architecture before distributed architecture;
3. measurable AI behavior over impressive demos;
4. typed interfaces between components;
5. production concerns from the beginning;
6. incremental delivery;
7. documentation of engineering trade-offs.

Technologies will only be added when they solve a real problem.

For example, Kubernetes will not be introduced merely to list Kubernetes on a CV. A deployment experiment may be added later to demonstrate orchestration concepts, but the main application should remain economically reasonable to operate.

---

# Development roadmap

## Phase 0 — Back to coding

Goal: restore development rhythm.

- [X] Create monorepo structure.
- [ ] Create Vue 3 + TypeScript application.
- [ ] Create FastAPI application.
- [ ] Add `/health` endpoint.
- [ ] Connect frontend to backend.
- [ ] Add formatting, linting and basic tests.
- [ ] Add Dockerfiles.
- [ ] Run entire project locally with one command.

**Proof unlocked:** Vue, TypeScript, Python, FastAPI, Git, APIs, Docker.

---

## Phase 1 — Build the chat

Goal: create the smallest useful product.

- [ ] Build responsive recruiter chat UI.
- [ ] Add predefined prompt suggestions.
- [ ] Add streaming responses.
- [ ] Connect backend to an LLM.
- [ ] Create provider abstraction.
- [ ] Add structured API errors.
- [ ] Persist conversations.

Example prompt suggestions:

- Why should we hire Jeyker?
- What makes this CV different?
- Tell me about Jeyker's AI experience.
- What has Jeyker built with Vue?
- Explain the architecture of this application.

**Proof unlocked:** LLM integration, product engineering, streaming APIs, UX.

---

## Phase 2 — RAG CV

Goal: make answers factual and traceable.

- [ ] Convert CV/profile information into curated documents.
- [ ] Implement document ingestion.
- [ ] Implement chunking.
- [ ] Generate embeddings.
- [ ] Add PostgreSQL + pgvector.
- [ ] Implement semantic retrieval.
- [ ] Build grounded prompts.
- [ ] Show sources in the UI.
- [ ] Add retrieval tests.

**Proof unlocked:** RAG, embeddings, vector search, data pipelines, PostgreSQL.

---

## Phase 3 — Agentic AI

Goal: move from chatbot to controlled agent.

- [ ] Add LangGraph.
- [ ] Model agent state explicitly.
- [ ] Implement tool calling.
- [ ] Add `search_experience`.
- [ ] Add `get_profile_section`.
- [ ] Add `create_contact_request`.
- [ ] Add confirmation boundaries for side effects.
- [ ] Add tool audit logs.
- [ ] Test invalid and malicious tool requests.

**Proof unlocked:** agents, LangGraph, function calling, orchestration, responsible tool execution.

---

## Phase 4 — AI evaluation

Goal: prove that the assistant works reliably.

- [ ] Create recruiter-question evaluation dataset.
- [ ] Create retrieval metrics.
- [ ] Test expected facts.
- [ ] Measure hallucinations.
- [ ] Measure latency.
- [ ] Track model/token usage.
- [ ] Add regression evaluation to CI.
- [ ] Compare at least two models.

**Proof unlocked:** evals, benchmarking, LLMOps, model selection.

---

## Phase 5 — Production engineering

Goal: treat the project as real software.

- [ ] Add unit tests.
- [ ] Add API integration tests.
- [ ] Add Playwright E2E tests.
- [ ] Add rate limiting.
- [ ] Add structured logging.
- [ ] Add tracing.
- [ ] Add health/readiness checks.
- [ ] Add retry and timeout policies.
- [ ] Add prompt/model versioning.
- [ ] Add security headers.
- [ ] Add dependency vulnerability checks.

**Proof unlocked:** testing, security, observability, reliability.

---

## Phase 6 — Cloud deployment

Goal: demonstrate ownership from code to production.

- [ ] Build production Docker images.
- [ ] Push images to a container registry.
- [ ] Provision managed PostgreSQL.
- [ ] Deploy backend container.
- [ ] Deploy frontend.
- [ ] Configure secrets.
- [ ] Configure HTTPS.
- [ ] Configure logs and monitoring.
- [ ] Configure domain.
- [ ] Document architecture and cost.

**Proof unlocked:** AWS/cloud, deployment, managed infrastructure, networking, production operations.

---

## Phase 7 — CI/CD

Goal: make deployments reproducible.

- [ ] Add GitHub Actions.
- [ ] Run lint/type checks automatically.
- [ ] Run backend tests.
- [ ] Run frontend tests.
- [ ] Run AI smoke evals.
- [ ] Build Docker images.
- [ ] Deploy from the main branch.
- [ ] Add rollback strategy.

**Proof unlocked:** GitHub Actions, CI/CD, release engineering.

---

## Phase 8 — Advanced AI engineering

Only after the core application is working:

- [ ] Add model routing.
- [ ] Add semantic caching.
- [ ] Add reranking.
- [ ] Add conversation memory strategy.
- [ ] Add prompt caching where supported.
- [ ] Experiment with local/open-source models.
- [ ] Compare RAG configurations.
- [ ] Experiment with MCP integration.
- [ ] Add human-in-the-loop workflows.
- [ ] Add automated red-team cases.
- [ ] Evaluate multimodal CV/project inputs.

**Proof unlocked:** advanced GenAI engineering without blocking the MVP.

---

# Skills coverage matrix

| Market requirement | Evidence in this project |
|---|---|
| Python | FastAPI backend and AI services |
| JavaScript / TypeScript | Vue application |
| LLM APIs | Provider integration |
| Prompt engineering | Versioned grounded prompts |
| Context engineering | RAG + conversation state |
| RAG | CV knowledge retrieval |
| Embeddings | Document ingestion pipeline |
| Vector search | pgvector |
| AI Agents | LangGraph workflow |
| Tool calling | Contact/profile/search tools |
| APIs | REST + streamed chat endpoints |
| SQL | PostgreSQL persistence |
| Data engineering | ingestion + transformation pipeline |
| Docker | local and production containers |
| Cloud | production deployment |
| AWS/Azure/GCP concepts | deployment architecture |
| CI/CD | GitHub Actions |
| MLOps / LLMOps | model/prompt/eval lifecycle |
| Evaluation | regression dataset + metrics |
| Observability | traces, logs and metrics |
| Security | validation, secrets, rate limits |
| Testing | unit, integration and E2E |
| Git | feature-based development history |
| Product thinking | recruiter-focused UX |
| Communication | architecture docs and ADRs |

---

# What this project deliberately does NOT claim

This project does not attempt to pretend that integrating an LLM API is equivalent to training foundation models.

It distinguishes between:

- software engineering;
- applied AI engineering;
- machine learning engineering;
- model research.

The main focus is **Applied / Generative AI Engineering**: building reliable products and systems around modern AI models.

Traditional ML experiments may be added separately where they provide useful evidence.

---

# Repository structure

```text
jeyker-ai-cv/
├── apps/
│   ├── web/                 # Vue 3 + TypeScript
│   └── api/                 # FastAPI
│
├── packages/
│   └── shared/              # shared contracts/schema if useful
│
├── ai/
│   ├── agents/
│   ├── prompts/
│   ├── retrieval/
│   ├── tools/
│   └── evals/
│
├── knowledge/
│   ├── cv.md
│   ├── profile.md
│   ├── education.md
│   ├── projects/
│   └── skills/
│
├── infrastructure/
│   ├── docker/
│   └── cloud/
│
├── docs/
│   ├── architecture.md
│   ├── decisions/
│   └── threat-model.md
│
├── .github/
│   └── workflows/
│
├── docker-compose.yml
└── README.md
```

---

# Architecture Decision Records

Important engineering decisions will be documented under `docs/decisions`.

Examples:

```text
ADR-001 — Why Vue instead of React?
ADR-002 — Why FastAPI?
ADR-003 — Why PostgreSQL + pgvector?
ADR-004 — Why LangGraph?
ADR-005 — Choosing the initial LLM provider
ADR-006 — Why not Kubernetes yet?
ADR-007 — RAG chunking strategy
ADR-008 — Tool-call security model
```

This is part of the portfolio.

A recruiter should be able to inspect not only what was built, but **why engineering decisions were made**.

---

# Definition of done

The project is successful when a recruiter can:

1. open a public URL;
2. ask a question about Jeyker;
3. receive a grounded, useful answer;
4. inspect the information sources;
5. ask how the application itself works;
6. see its architecture;
7. inspect automated tests and evaluations;
8. see a green CI pipeline;
9. inspect the cloud deployment architecture;
10. verify the implementation in this repository.

At that point the repository itself becomes part of the CV.

---

# The CV line this project should eventually earn

> **Jeyker AI CV — Production-oriented GenAI application built with Vue 3, TypeScript and FastAPI, featuring RAG over professional knowledge, pgvector semantic search, LangGraph agent orchestration and tool calling, automated LLM evaluations, observability, Docker-based deployment and CI/CD to cloud infrastructure.**

That sentence should only be added to the CV once the corresponding features actually exist.

---

# First milestone

Do not begin with LangGraph.

Do not begin with cloud.

Do not begin with embeddings.

The first milestone is intentionally boring:

```text
Vue page
   ↓
POST /chat
   ↓
FastAPI
   ↓
"Hello, recruiter."
```

Then commit it.

Every later capability should be introduced through a small working increment.

The objective is not to prove everything in one weekend.

The objective is to build a repository whose commit history becomes evidence of how an AI Engineer works.
