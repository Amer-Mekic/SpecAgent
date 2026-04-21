# SpecAgent — CLAUDE.md

## What This Project Is
SpecAgent is a web application that automates software requirements 
extraction, validation, classification, and traceability from 
unstructured documents (PDF, DOCX, TXT). It uses a pipeline of 
three LLM-based AI agents built with PydanticAI, a FastAPI backend, 
a React frontend, and PostgreSQL with pgvector for vector similarity 
search.

## Tech Stack
- Backend: Python, FastAPI, PydanticAI, SQLAlchemy, PostgreSQL, 
  pgvector, sentence-transformers, python-jose, passlib
- Frontend: React (Vite), axios, react-router-dom
- Database: PostgreSQL 18 + pgvector extension via Docker
- LLM: Anthropic Claude API (or OpenAI — configured via .env)

## Project Structure
backend/
  app/
    agents/          # extraction.py, validation.py, classification.py
    services/        # traceability.py, document.py, export.py
    api/routes/      # upload.py, requirements.py, chat.py, rtm.py, 
                     # export.py, auth.py
    models/          # SQLAlchemy models matching ER diagram
    schemas/         # Pydantic schemas for agent I/O
    core/            # config.py, database.py, security.py
    main.py
frontend/
  src/
    components/
    pages/
    hooks/
    api/

## Database Schema (key tables)
- USER: id, email, name, password (bcrypt), created_at
- SESSION: id, user_id (FK), document_name, document_hash, status, 
  created_at
- DOCUMENT_SECTION: id, session_id (FK), section_index, content, 
  embedding (vector), created_at
- REQUIREMENT: id, session_id (FK), req_id, statement, 
  pipeline_status (raw|validated|classified|traced),
  finalization_status (draft|reviewed|final|rejected), created_at
- VALIDATION_REPORT: id, requirement_id (FK), result 
  (pass|flagged|rejected), issues (JSON), suggestions (JSON)
- CLASSIFICATION: id, requirement_id (FK), type 
  (functional|non-functional), sub_category, confidence (float)
- TRACEABILITY_LINK: id, requirement_id (FK), section_id (FK), 
  similarity_score (float)
- CHAT_MESSAGE: id, session_id (FK), requirement_id (FK nullable), 
  role (user|assistant), content
- EXPORT: id, session_id (FK), format, file_path, version (int), 
  prev_export_id (FK nullable), created_at

## Agent Pipeline
Upload → preprocess (chunk + embed with sentence-transformers) → 
ExtractionAgent (LLM) → ValidationAgent (LLM) → 
ClassificationAgent (LLM) → TraceabilityService (pgvector SQL, 
no LLM) → results saved to DB

Agents do NOT communicate with each other. The orchestrator 
(run_pipeline function) calls each agent sequentially and passes 
outputs forward. Agents are PydanticAI agents with typed 
result_type schemas.

## Key Design Decisions
- Traceability is a plain Python function using pgvector cosine 
  similarity — NOT an LLM agent
- Validation result does NOT block the pipeline — flagged 
  requirements still proceed to classification and traceability
- pipeline_status and finalization_status are separate fields — 
  pipeline_status is set by the system, finalization_status by 
  the user
- JWT auth: every endpoint except /auth/register and /auth/login 
  requires a valid JWT. Session ownership is verified on every 
  data query.
- Cache: document hash stored in SESSION.document_hash — if same 
  hash exists, copy results without re-running agents

## API Endpoints
POST   /api/auth/register
POST   /api/auth/login
POST   /api/upload
GET    /api/requirements/{session_id}
PUT    /api/requirements/{requirement_id}
POST   /api/requirements/{requirement_id}/revalidate
POST   /api/chat/{session_id}
GET    /api/rtm/{session_id}
POST   /api/export/{session_id}

## Environment Variables (see .env.example)
DATABASE_URL, ANTHROPIC_API_KEY, SECRET_KEY, DEBUG

## What NOT to Do
- Do not use merge when updating feature branches — use rebase
- Do not hardcode API keys anywhere
- Do not add LLM calls to the traceability service
- Do not make agents call each other directly
- Do not encrypt passwords with anything other than bcrypt
- Do not use wildcard CORS in production