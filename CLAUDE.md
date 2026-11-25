# Code-Aware RAG

AST-based RAG over Python repositories. Target repo: pinned FastAPI under `data/repos/fastapi`.
Current sprint: **S02 — tree-sitter parser**. Sprint notes live in `notes/`.

## This is a learning project
The owner wants to understand every line. Follow these rules strictly:
- Core logic (scanner rules, chunker, symbol graph, retrieval, RRF, context packing, prompts, eval):
  do NOT write it unless explicitly asked. Explain concepts, point to docs, review the owner's code,
  suggest test cases.
- Plumbing (config, CLI wiring, API clients, retries, formatting): you may write it,
  in small diffs, one function or file at a time.
- Before any edit, state the plan in a few lines and wait for approval.
- After any edit, explain what changed and why in 2–4 short sentences.
- Never make large multi-file changes in one step.
- Reply to the owner in Turkish. Code, identifiers, comments, CLI output and commit messages in English.

## Environment
- Windows, PowerShell. Give PowerShell commands, not bash.
- Python via uv. Add dependencies with `uv add` / `uv add --dev`. Never use pip.
- Windows App Control blocks the launcher .exe files in `.venv\Scripts`.
  Always run tools through Python:
  - Tests: `uv run python -m pytest`
  - Lint: `uv run python -m ruff check .`
  - Format: `uv run python -m ruff format .`
  - CLI: `uv run python -m coderag --help`
- Never try to work around the App Control policy in any other way.

## Hard rules
- Never modify anything under `data/repos/`. It is the pinned target repository; evaluation depends on it.
- Never read or print `.env`. Settings come from `coderag.config.Settings`.
- You may commit after tests and ruff pass. Never push, tag or merge unless asked.
- Never create, edit or delete files outside the repository.

## Conventions
- Layout: `src/coderag/`, tests in `tests/`.
- Commits: Conventional Commits, e.g. `feat(scan): ...`.
  Scopes: scan, parsing, chunking, graph, embed, index, retrieve, generate, api, cli, config, eval.
- One branch per sprint (`sprint/sNN-name`), merged via PR, then tagged `sprint-NN`.
- Type hints everywhere. Every new behavior gets a test.

## Working mode
You write, test and commit; the owner reviews at the end of each sprint.
- Work in small steps: one class, one function or one file per step.
- After each step: run `uv run python -m pytest` and `uv run python -m ruff check .`.
  If both pass, commit with a Conventional Commit message and continue.
- Stop and ask only for: design decisions not covered by earlier answers,
  failing tests you cannot fix, or anything that changes the project's scope.
- Keep a running log in `notes/sprint-XX.md`: each step, its commit, and every decision with its reason.
- Reply to the owner in Turkish. Code, identifiers, comments, CLI output and commit messages in English.