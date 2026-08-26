# Django AI Interactive Professional Profile

This repository is Jeyker's recruiter-facing conversational engineering
portfolio. The frontend uses Vue 3, TypeScript, Nuxt UI and the Vercel AI SDK.
The backend uses FastAPI, LangChain and Google Gemini.

Responses stream over HTTP/SSE using the AI SDK UI Message Stream Protocol.
The interface supports custom message components, candidate-photo tool calls,
English/Spanish localization and light/dark themes.

The frontend is deployed through Azure Static Web Apps and GitHub Actions.
The backend has a Dockerfile and deployment commands for Azure Container
Registry and Azure Container Apps.

This project contains a curated file-based professional knowledge base.
Vector embeddings, pgvector retrieval, durable conversation persistence and
approval-gated contact actions are future work and must not be represented as
already implemented.
