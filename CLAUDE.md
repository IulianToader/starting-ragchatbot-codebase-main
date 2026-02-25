# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A full-stack RAG (Retrieval-Augmented Generation) chatbot for querying course materials. Python FastAPI backend with vanilla JS frontend, using ChromaDB for vector search and Anthropic Claude for AI-powered responses.

## Commands

```bash
# Install dependencies (including dev tools)
uv sync --group dev

# Run the application (backend + frontend on port 8000)
./run.sh
# OR
cd backend && uv run uvicorn app:app --reload --port 8000

# Run all quality checks (formatting + tests)
./scripts/check.sh

# Auto-fix formatting issues
./scripts/check.sh --fix

# Run black formatter directly
uv run black .

# Run tests
uv run pytest
```

## Architecture

**Single-process full-stack app**: FastAPI serves both the API and the frontend as static files on port 8000.

### Backend (`backend/`)

- **app.py** — FastAPI endpoints (`POST /api/query`, `GET /api/courses`). On startup, loads documents from `docs/` into the vector store.
- **rag_system.py** — Orchestrator that coordinates all components: document processing, vector search, AI generation, and session management.
- **vector_store.py** — ChromaDB wrapper with two collections: `course_catalog` (metadata) and `course_content` (searchable text chunks). Persists to `./chroma_db/`.
- **document_processor.py** — Parses course text files (title/link/instructor header, then `Lesson N: Title` sections) and chunks text by sentences with overlap.
- **ai_generator.py** — Claude API integration using tool-calling. Temperature 0, max 800 tokens. Handles multi-turn tool execution loops.
- **search_tools.py** — Defines `CourseSearchTool` for Claude's tool-use API. Supports filtering by course name, lesson number, and custom queries.
- **session_manager.py** — In-memory conversation history (lost on restart). Retains last 2 exchanges per session.
- **models.py** — Pydantic models: `Lesson`, `Course`, `CourseChunk`.
- **config.py** — Centralized `@dataclass` config loaded from environment. Key settings: chunk size 800, chunk overlap 100, max 5 search results.

### Frontend (`frontend/`)

Vanilla HTML/JS/CSS. Uses Marked.js (CDN) for markdown rendering. Sidebar shows course stats, main area is a chat interface. All API calls go to the same origin on port 8000.

### Data Flow

User query → `POST /api/query` → `RAGSystem.query()` → Claude called with search tools → `CourseSearchTool` executes semantic search against ChromaDB → results fed back to Claude → synthesized answer returned with source attribution.

## Key Configuration

- **Required**: `.env` file with `ANTHROPIC_API_KEY` (see `.env.example`)
- **Python**: 3.13+ (see `.python-version`)
- **Model**: `claude-sonnet-4-20250514`
- **Embeddings**: `all-MiniLM-L6-v2` via sentence-transformers

## Course Document Format

Text files in `docs/` follow this structure:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 0: [title]
Lesson Link: [url]
[content...]

Lesson 1: [title]
[content...]
```
