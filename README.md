# Code-Aware RAG

[![CI](https://github.com/ErdemKoray/code-aware-rag/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ErdemKoray/code-aware-rag/actions/workflows/ci.yml)

A retrieval-augmented generation system that answers questions about a Python codebase with precise `file:line` citations.

> **Status:** Early development. The file scanner, the tree-sitter parser and the structure-aware chunker work; chunk metadata and validation of the chunker are next. Indexing, retrieval and answering are not implemented yet.

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
| Language & tooling | Python 3.12+, uv, ruff, pytest |
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
| M1 | Structure-aware chunker validated on the target repo | In progress |
| M2 | Incremental indexing with dense + sparse vectors | Planned |
| M3 | Hybrid retrieval with reranking and graph expansion | Planned |
| M4 | Cited answers via CLI and HTTP API | Planned |
| M5 | Evaluation and ablation results | Planned |

## Getting started

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), git.

```bash
git clone https://github.com/ErdemKoray/code-aware-rag
cd code-aware-rag
uv sync
cp .env.example .env
```

Fill in your API keys in `.env` when needed (not required for the current stage).

Clone the target repository at its pinned version:

```bash
git clone https://github.com/fastapi/fastapi data/repos/fastapi
git -C data/repos/fastapi checkout 0.143.0
```

Check the setup:

```bash
uv run rag --help
uv run pytest
```

> **Windows Application Control:** if it blocks the launcher executables in `.venv\Scripts`, run the tools through Python instead: `uv run python -m coderag --help`, `uv run python -m pytest`, `uv run python -m ruff check .`

## Commands

### `rag scan [PATH]`

Lists the `.py` files that would be indexed. Without `PATH` it scans the pinned FastAPI clone.

```bash
uv run rag scan
uv run rag scan path/to/project
```

The report shows:

- how many files are included, and how many of them are tests (tests are tagged, not excluded);
- how many files are excluded, per reason: `symlink`, `gitignored`, `too_large`, `unreadable`;
- the pruned directories (version control, virtual environments, caches, `build`, `dist`, and also `docs_src` and `scripts`) and any directory that could not be listed;
- the five largest files and the scan time.

Only the root `.gitignore` is honoured. The size limit is `MAX_FILE_SIZE_BYTES` (default `500000`). The exit code is 2 if the path is missing, is not a directory or cannot be listed.

### `rag parse-debug FILE`

Parses one file with tree-sitter and prints its top-level syntax nodes with 1-based, inclusive line ranges.

```bash
uv run rag parse-debug data/repos/fastapi/fastapi/params.py
```

```text
has_error: False
import_statement       L1-1
import_from_statement  L2-2
...
class_definition       L19-23  name=ParamTypes
...
```

A file with syntax errors is still printed, with `has_error: True` and exit code 0. The exit code is 2 if the file cannot be read.

### `rag chunk-debug FILE`

Splits one file into chunks and prints each chunk's kind, line range, size and name.

```bash
uv run rag chunk-debug data/repos/fastapi/fastapi/encoders.py
```

```text
has_error: False
chunks: 9 (max size: 4000 bytes)
module    L1-49     1307 B  defines: Color, PyExtraColor
function  L52-54     111 B  isoformat
...
function  L129-218  2777 B  jsonable_encoder  [1/3]
...
```

Chunks follow the code structure:

- a module-level function, with its decorators and the comments directly above it, is one `function` chunk;
- a class with methods is split into a `class_header` (up to the first method), one `method` chunk per method and `class_block` chunks for code between them; a class without methods stays a single `class` chunk;
- the remaining module code forms `module` chunks; definitions inside `if` or `try` blocks stay there and are listed as `defines`;
- a chunk larger than `MAX_CHUNK_BYTES` (default `4000`) is cut into parts (`[1/3]`) between parameters and statements, by lines only as a last resort.

Every non-blank line belongs to exactly one chunk. Exit codes are the same as for `parse-debug`.

`rag index`, `rag search` and `rag ask` are not implemented yet.

## Target repository

Development and evaluation run against a pinned version of the [FastAPI](https://github.com/fastapi/fastapi) source code, so results stay comparable over time. A test checks that the local clone is at this version.

- Tag: `0.143.0`
- Commit: `f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007`

## Project structure

```
src/coderag/
  __main__.py     # `python -m coderag` entry point
  cli.py          # `rag` command-line interface
  config.py       # settings loaded from the environment and .env
  scan.py         # finds the .py files to index
  parsing/
    python.py     # tree-sitter parser and line ranges
  chunking/
    model.py      # the Chunk record and its ids
    chunker.py    # splits a file along its structure
    split.py      # cuts oversized chunks at syntax boundaries
tests/            # unit tests (those that need the clone are skipped without it)
notes/            # sprint notes and design decisions (in Turkish)
data/repos/       # target repositories (not committed)
data/out/         # temporary output (not committed)
```

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## License

[MIT](LICENSE)