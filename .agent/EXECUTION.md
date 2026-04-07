# Phased Execution Plan

## Phase 1: OpenEnv Core Specification [ ]
- [ ] Implement `environment/models.py` with exact Pydantic types defined in ARCHITECTURE.md.
- [ ] Scaffold `environment/env.py` with mock async methods (`reset`, `step`, `state`, `close`).
- [ ] Create `openenv.yaml` with required metadata.

## Phase 2: Infrastructure & API Server [ ]
- [ ] Implement `server.py` using FastAPI to expose `/reset`, `/step`, `/state` mapping to `env.py`.
- [ ] Create `Dockerfile` using `python:3.11-slim`. Install `git` and `pytest`. Ensure it starts the FastAPI server.
- [ ] Write `inference.py` using the OpenAI client. STRICTLY map the `[START]`, `[STEP]`, `[END]` stdout format.

## Phase 3: Git Operations & Core Logic [ ]
- [ ] Implement `environment/git_utils.py` using Python's `subprocess` to handle `git status`, `git add`, `git merge`.
- [ ] Implement file reading and the `replace_lines` logic safely.
- [ ] Wire the Git utilities into `environment/env.py`.

## Phase 4: Task Generation & Graders [ ]
- [ ] Scaffold `tasks/task_1_easy/`, initialize a git repo, and script the creation of a conflicted state.
- [ ] Scaffold `tasks/task_2_medium/`.
- [ ] Scaffold `tasks/task_3_hard/`.
- [ ] Implement deterministic reward shaping in `environment/graders.py`.