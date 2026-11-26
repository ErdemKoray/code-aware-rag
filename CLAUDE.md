# Code-Aware RAG

AST-based RAG over Python repositories. Target repo: pinned FastAPI under `data/repos/fastapi`.
Current sprint: **S03 — chunker**. Sprint notes live in `notes/`.

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
- Never create, edit or delete files outside the repository. The only exceptions are tool caches
  (uv, ruff, pytest) and pytest's temporary directories. Put temporary scripts and their output
  under `data/out/` (gitignored).

## Conventions
- Layout: `src/coderag/`, tests in `tests/`.
- Commits: Conventional Commits, e.g. `feat(scan): ...`.
  Scopes: scan, parsing, chunking, graph, embed, index, retrieve, generate, api, cli, config, eval.
- One branch per sprint (`sprint/sNN-name`), merged via PR, then tagged `sprint-NN`.
- Type hints everywhere. Every new behavior gets a test.

## Working mode
You write, test and commit; the owner reviews at the end of each sprint.
- At the start of a sprint, present the plan and the design decisions, then wait for the
  owner's approval.
- After approval, write all the code, including core logic.
- Work in small steps: one class, one function or one file per step.
- After each step: run `uv run python -m pytest`, `uv run python -m ruff check .` and
  `uv run python -m ruff format --check .`. If all pass, commit with a Conventional Commit
  message and continue.
- Stop and ask only for: design decisions not covered by earlier answers,
  failing tests you cannot fix, or anything that changes the project's scope.
- Keep a running log in `notes/sprint-XX.md`: each step, its commit, and every decision with its reason.
- Reply to the owner in Turkish. Code, identifiers, comments, CLI output and commit messages in English.