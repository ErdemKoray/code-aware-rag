# Code-Aware RAG

A retrieval-augmented generation system that answers questions about a Python codebase with precise `file:line` citations.

> **Status:** Early development. The project skeleton is in place; the indexing and retrieval pipeline is being built sprint by sprint.

## Why

Classic RAG splits documents into fixed-size chunks. On source code this breaks functions in half, separates methods from their classes, and loses the relationships between symbols. Questions like *"which dependencies does this endpoint use?"* or *"where is the OAuth2 password flow defined?"* end up answered from fragments.

Code-Aware RAG splits code along its real structure instead: functions, classes, methods and module-level blocks, parsed from the syntax tree. It also stores how symbols relate to each other (calls, imports, inheritance), so answers can follow the code the way a developer would.

## How it works (planned)

```
Repository ──► Scanner ──► Parser (tree-sitter) ──► Chunker
                                                      │
                     ┌────────────────────────────────┤
                     ▼                                ▼
          Symbol graph (SQLite)          Dense + sparse vectors (Qdrant)

Question ──► Hybrid search ──► Rerank ──► Graph expansion
         ──► Context packing ──► LLM answer with file:line citations
```

- **Structure-aware chunking:** each chunk is a complete logical unit with its signature, docstring, decorators and parent class.
- **Hybrid search:** semantic search combined with exact identifier matching, so names like `OAuth2PasswordBearer` are never lost.
- **Symbol graph:** callers, callees and parent classes are pulled in when they help answer the question.
- **Grounded answers:** every claim cites a file and line range; if the context does not contain the answer, the system says so.
- **Measured, not assumed:** a hand-built question set and ablation studies compare this approach against fixed-size chunking.

## Tech stack

| Layer | Choice |
|---|---|
| Language & tooling | Python 3.11+, uv, ruff, pytest |
| Parsing | tree-sitter |
| Embeddings & reranking | Voyage AI |
| Vector store | Qdrant |
| Symbol graph | SQLite |
| Answer generation | Claude (Anthropic API) |
| Interfaces | CLI (Typer), HTTP API (FastAPI) |

## Roadmap

| Milestone | Goal | Status |
|---|---|---|
| M0 | Project skeleton, config, CLI stubs | Done |
| M1 | Structure-aware chunker validated on the target repo | Planned |
| M2 | Incremental indexing with dense + sparse vectors | Planned |
| M3 | Hybrid retrieval with reranking and graph expansion | Planned |
| M4 | Cited answers via CLI and HTTP API | Planned |
| M5 | Evaluation and ablation results | Planned |

## Getting started

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), git.

```bash
git clone https://github.com/<your-username>/code-aware-rag
cd code-aware-rag
uv sync
cp .env.example .env
```

Fill in your API keys in `.env` when needed (not required for the current stage).

Clone the target repository at its pinned version:

```bash
git clone https://github.com/fastapi/fastapi data/repos/fastapi
git -C data/repos/fastapi checkout <TAG>
```

Check the setup:

```bash
uv run rag --help
uv run pytest
```

## Target repository

Development and evaluation run against a pinned version of the [FastAPI](https://github.com/fastapi/fastapi) source code, so results stay comparable over time.

- Tag: `<TAG>`
- Commit: `<SHA>`

## Project structure

```
src/coderag/
  config.py     # settings loaded from .env
  cli.py        # `rag` command-line entry point
tests/          # unit tests
notes/          # sprint notes and design decisions
data/repos/     # target repositories (not committed)
```