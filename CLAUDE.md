# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PrivateGPT is a production-ready AI project that provides a complete RAG (Retrieval Augmented Generation) pipeline with both high-level and low-level APIs. It allows users to ask questions about their documents using Large Language Models (LLMs) in a fully private, offline environment. The project follows OpenAI API standards and supports multiple LLM providers, embedding models, and vector stores.

## Development Commands

### Build and Run
- `make run` - Run the application (uses Poetry)
- `make dev` - Run in development mode with auto-reload (Linux/Mac)
- `make dev-windows` - Run in development mode with auto-reload (Windows)
- `poetry run python -m private_gpt` - Alternative way to run the application
- `docker-compose up` - Run with Docker (includes Ollama service)

### Testing and Quality
- `make test` - Run all tests using pytest
- `make test-coverage` - Run tests with coverage report
- `make check` - Run formatting and type checking (combines format + mypy)
- `make format` - Format code with black and ruff, fix linting issues
- `make black` - Check code formatting only
- `make ruff` - Check code linting only
- `make mypy` - Run type checking

### Data Management
- `make ingest [folder_path]` - Ingest documents from a folder
- `make wipe` - Clear all ingested data
- `make setup` - Setup the application
- `poetry run python scripts/ingest_folder.py [path]` - Alternative ingestion method

### Documentation
- `make api-docs` - Generate OpenAPI documentation

## Architecture

### Core Framework
- **API Framework**: FastAPI with dependency injection via `injector`
- **RAG Framework**: Built on LlamaIndex abstractions
- **Configuration**: YAML-based settings with environment variable overrides

### Directory Structure
```
private_gpt/
├── components/          # Dependency injection components
│   ├── embedding/       # Embedding model implementations
│   ├── llm/            # LLM implementations
│   ├── vector_store/   # Vector store implementations
│   ├── node_store/     # Node storage implementations
│   └── ingest/         # Document ingestion logic
├── server/             # FastAPI routers and services
│   ├── chat/           # Chat completions API
│   ├── completions/    # Text completions API
│   ├── embeddings/     # Embeddings API
│   ├── chunks/         # Document chunks retrieval API
│   ├── ingest/         # Document ingestion API
│   └── health/         # Health check endpoint
├── settings/           # Configuration management
├── ui/                 # Gradio web interface (optional)
└── open_ai/           # OpenAI API compatibility layer
```

### Key Architectural Patterns
- **Dependency Injection**: Components are decoupled via `injector` DI container defined in `di.py`
- **Service Layer**: Each API endpoint has a corresponding service class that handles business logic
- **Component Abstraction**: Uses LlamaIndex base classes (LLM, BaseEmbedding, VectorStore) allowing easy swapping of implementations
- **Settings Management**: Centralized configuration in `settings/settings.py` with YAML file loading

### Configuration Profiles
The application uses profile-based configuration via `PGPT_PROFILES` environment variable:
- `local` - Local development with file-based storage
- `docker` - Docker deployment configuration
- `mock` - Mock implementations for testing

### Main Components
- **LLM Component**: Manages language model implementations (LlamaCPP, OpenAI, Ollama, etc.)
- **Embedding Component**: Handles text embedding generation (HuggingFace, OpenAI, etc.)
- **Vector Store Component**: Manages vector database connections (Qdrant, Chroma, Postgres)
- **Ingest Component**: Processes and indexes documents

### API Structure
Each API follows a consistent pattern:
- `*_router.py` - FastAPI route definitions
- `*_service.py` - Business logic implementation
- Services use LlamaIndex abstractions, not concrete implementations

### Entry Points
- `private_gpt/main.py` - FastAPI app instance
- `private_gpt/launcher.py` - App factory with middleware and router setup
- `private_gpt/__main__.py` - CLI entry point

## Development Setup

### Dependencies
- Python 3.11 (exactly, not 3.12+)
- Poetry for dependency management
- Optional extras for specific integrations (UI, vector stores, LLM providers)

### Installation Extras
Use Poetry extras to install optional dependencies:
- `poetry install --extras "ui"` - Web interface
- `poetry install --extras "llms-ollama"` - Ollama LLM support
- `poetry install --extras "vector-stores-qdrant"` - Qdrant vector store
- See `pyproject.toml` for full list of available extras

### Pre-commit Hooks
The project uses pre-commit hooks for code quality:
- Black formatting
- Ruff linting
- MyPy type checking
- Pytest unit tests (on push)

### Testing
- Tests are in `tests/` directory
- Uses pytest with async support
- Fixtures in `tests/fixtures/` provide common test utilities
- Mock injector available for dependency injection in tests