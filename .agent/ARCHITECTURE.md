# AutoMergeEnv Architecture

## Domain
A Semantic Git Conflict Resolver environment. AI agents are tasked with resolving complex, multi-file Git merge conflicts where standard `git merge` fails or results in broken code.

## OpenEnv API Implementation
The environment wraps a local Git repository and exposes the OpenEnv specification via a FastAPI server.
- `reset()`: Performs `git reset --hard && git clean -fd`, checks out the base branch, triggers a conflicting merge, and returns the initial observation.
- `step(action)`: Applies file edits, runs tests, or executes git commands.
- `state()`: Returns unmerged paths, test statuses, and the current commit hash.

## Pydantic Interfaces (The Contract)
**Action Space (AutoMergeAction):**
- `command` (Literal): 'read_file', 'replace_lines', 'run_tests', 'git_status', 'git_add', 'commit_merge'
- `filepath` (Optional str)
- `start_line`, `end_line` (Optional int)
- `new_text` (Optional str)

**Observation Space (AutoMergeObservation):**
- `stdout` (str): Output of the command or file contents.
- `stderr` (str): Errors or compilation tracebacks.
- `has_unmerged_paths` (bool): True if `<<<<<<<` exists.
- `tests_passing` (bool): True if `pytest` returns exit code 0.

## Tasks & Grading
- **Task 1 (Easy):** Standard textual conflict in a single file. (Grader: `git merge --continue` succeeds).
- **Task 2 (Medium):** Cross-file signature conflict. (Grader: Syntax is valid, basic tests pass).
- **Task 3 (Hard):** Semantic conflict (clean merge, but broken logic). (Grader: Integration test suite passes).
- **Reward Shaping:** Penalize syntax errors (-0.1). Reward resolving conflict markers (+0.2). Reward passing tests (+0.4). Max score: 1.0.

## Overview

AutoMergeEnv is a fully deterministic, containerized OpenEnv environment that benchmarks AI agent capability against one of the most universal developer pain points: resolving Git merge conflicts. It spans three conflict archetypes — textual, cross-file semantic, and logic-level semantic — each requiring a progressively deeper understanding of developer intent, not just syntactic resolution.

The environment is designed to be zero-cloud, zero-external-dependency, and fully reproducible on 2 vCPU / 8 GB RAM hardware.

---

## Directory Structure

```
AutoMergeEnv/
├── server/
│   └── app.py                  # FastAPI server — all HTTP endpoints
├── environment/
│   ├── env.py                  # Core AutoMergeEnv class (reset/step/state)
│   ├── models.py               # All Pydantic models (Action, Observation, Reward)
│   └── graders.py              # Per-task deterministic reward functions
├── tasks/
│   ├── task_1_easy/            # Bare git repo (textual conflict)
│   ├── task_2_medium/          # Bare git repo (cross-file signature conflict)
│   ├── task_3_hard/            # Bare git repo (semantic/logic conflict — NO markers)
│   └── task_4_adversarial/     # Bare git repo (both versions wrong, intent in tests)
├── setup_tasks.sh              # Bootstraps all 4 task git repos from scratch
├── inference.py                # Baseline agent script (OpenAI client)
├── openenv.yaml                # OpenEnv spec metadata
├── Dockerfile                  # Container definition
├── requirements.txt
├── README.md
├── Architecture.md             # This file
└── Execution.md                # Step-by-step execution and deployment guide
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Container                       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               FastAPI Server  :7860                  │   │
│  │                                                      │   │
│  │  POST /reset    ←─ { task_id? }                      │   │
│  │  POST /step     ←─ { command, filepath, ... }        │   │
│  │  GET  /state    ←─ {}                                │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │              AutoMergeEnv (env.py)                   │   │
│  │                                                      │   │
│  │  reset(task_id?) → AutoMergeObservation              │   │
│  │  step(action)    → (Observation, Reward, Done, Info) │   │
│  │  state()         → AutoMergeState                    │   │
│  │                                                      │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │           Subprocess Layer                  │    │   │
│  │  │  git reset / merge / add / commit / log     │    │   │
│  │  │  pytest  /  grep  /  find  /  cat           │    │   │
│  │  └───────────────────┬─────────────────────────┘    │   │
│  └──────────────────────┼───────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │                  Task Repos (Linux FS)               │   │
│  │                                                      │   │
│  │  tasks/task_1_easy/        (git bare repo)           │   │
│  │  tasks/task_2_medium/      (git bare repo)           │   │
│  │  tasks/task_3_hard/        (git bare repo)           │   │
│  │  tasks/task_4_adversarial/ (git bare repo)           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
          ▲
          │  HTTP
          │
┌─────────┴─────────────────────────────────────────────────┐
│                   inference.py (Agent)                    │
│                                                           │
│  1. POST /reset  { task_id: "task_1_easy" }               │
│  2. while not done:                                       │
│       obs → LLM → action                                  │
│       POST /step { command, filepath, ... }               │
│  3. Emit [START] [STEP] [END] structured logs             │
└───────────────────────────────────────────────────────────┘
```

---

## Data Models (models.py)

### Action

```python
from pydantic import BaseModel
from typing import Literal, Optional

AllowedCommand = Literal[
    "read_file",
    "replace_lines",
    "run_tests",
    "git_status",
    "git_add",
    "commit_merge",
    "list_files",    # NEW: find all .py files in repo
    "search_code",   # NEW: grep pattern across repo (pattern in filepath field)
    "show_diff",     # NEW: git diff HEAD — shows what changed in merge
    "git_log",       # NEW: git log --oneline — exposes developer intent via commit msgs
]

class AutoMergeAction(BaseModel):
    command: AllowedCommand
    filepath: Optional[str] = None      # file path — or grep pattern for search_code
    start_line: Optional[int] = None    # for replace_lines
    end_line: Optional[int] = None      # for replace_lines
    new_text: Optional[str] = None      # for replace_lines
```

### Observation

```python
class AutoMergeObservation(BaseModel):
    stdout: str                         # command output, file content, test results
    stderr: str                         # errors, tracebacks
    has_unmerged_paths: bool            # True if <<<<<<< markers remain in any file
    tests_passing: bool                 # True if pytest exits with code 0
    current_task: str                   # e.g. "task_1_easy"
    step_count: int                     # steps taken in current episode
```

### Reward

```python
class AutoMergeReward(BaseModel):
    total: float                        # 0.0 – 1.0
    breakdown: dict                     # component scores for transparency
    done: bool
    info: dict                          # step_count, task_id, efficiency_bonus
```
```

### State

```python
class AutoMergeState(BaseModel):
    current_task: str
    unmerged_files: list[str]           # files still containing <<<<<<< markers
    modified_files: list[str]           # files changed since reset
    tests_passing: bool
    step_count: int
    episode_history: list[str]          # log of commands used this episode
```

---

## Core Environment Logic (env.py)

### `reset(task_id: Optional[str] = None)`

1. If a merge is in progress, run `git merge --abort` first (prevents state leakage between episodes).
2. Run `git reset --hard HEAD` and `git clean -fd` on the current repo.
3. If `task_id` is provided, set `self.current_repo = tasks/{task_id}`. Otherwise, pick a random task.
4. Run `git checkout main` and `git reset --hard main` to ensure we are on the correct branch.
5. Run `git merge feature-a --no-edit` to intentionally trigger the conflict state.
6. Run `git status --porcelain` and `pytest` to build the initial observation.
7. Return `AutoMergeObservation`.

### `step(action: AutoMergeAction)`

Dispatch table:

| Command | Implementation | Failure condition |
|---------|---------------|------------------|
| `read_file` | `cat -n {filepath}` | File not found |
| `replace_lines` | Read file → replace lines → write back | Out-of-range lines |
| `run_tests` | `pytest -v --tb=short` | Always succeeds (result in stdout) |
| `git_status` | `git status --short` | Never fails |
| `git_add` | `git add {filepath}` | File not found / not modified |
| `commit_merge` | `git commit --no-edit -m "Merge: resolved by agent"` | Unresolved conflicts remain |
| `list_files` | `find . -name "*.py" -not -path "./.git/*"` | Never fails |
| `search_code` | `grep -rn {filepath_field} --include=*.py` | No matches → "No matches found." |
| `show_diff` | `git diff HEAD` | Never fails |
| `git_log` | `git log --oneline -10` | Never fails |

After every action, run the reward function and return `(observation, reward, done, info)`.

### `commit_merge` guard

`done = True` is only set when the commit subprocess exits with code 0. If the commit fails (e.g., unresolved markers remain), `done = False`, `action_failed = True`, and the agent receives a `-0.1` penalty.

---

## Reward Function (graders.py)

```
Per-step reward:

  -0.10  Invalid action, bad parameters, subprocess error
  +0.20  All <<<<<<< conflict markers have been removed from all files
         (only awarded once — not re-awarded on subsequent steps)
  +0.40  pytest exits 0 or 1 (code runs without fatal crash)
  +0.40  pytest exits 0 (all tests pass — final success signal)
  +0.10  Efficiency bonus: max(0, 0.1 × (1 − step_count / 20))
         (rewards fewer steps for same outcome)

Total maximum: 1.1 (capped to 1.0 in output)
Minimum returned: 0.01 (never exactly zero to avoid sparse signal confusion)
```

### Task 3 reward guard

Because Task 3 (semantic conflict) has no `<<<<<<<` markers after `git merge`, the `+0.20` marker-removal reward is only awarded if the agent has actually *modified* at least one file since reset. This prevents a free `+0.20` at episode start.

```python
def markers_resolved_reward(cwd: str, task_id: str) -> float:
    if task_id == "task_3_hard" or task_id == "task_4_adversarial":
        # Only award if agent has made changes
        out, _, _ = run_command(["git", "diff", "--name-only", "HEAD"], cwd=cwd)
        if not out.strip():
            return 0.0
    if check_for_conflict_markers(cwd):
        return 0.0
    return 0.20
```

---

## The 4 Tasks

### Task 1 — Easy: Textual Conflict

**Repo structure:** `utils.py` (one file)
**Conflict type:** Two developers added different imports and functions to the exact same lines.
**What appears after merge:** Standard `<<<<<<< HEAD / ======= / >>>>>>>` markers in `utils.py`.
**Agent must:** Remove markers, keep both functions, `git_add`, `commit_merge`.
**Grader:** Score 1.0 if `git merge` completes, syntax is valid, and `pytest` exits 0.

### Task 2 — Medium: Cross-File Signature Conflict

**Repo structure:** `math_ops.py`, `app.py`, `test_app.py`
**Conflict type:** Developer A changed a function signature in `math_ops.py`. Developer B added a feature in `app.py` using the old signature. Markers appear in `math_ops.py`.
**Agent must:** Resolve marker in `math_ops.py`, find the broken call in `app.py`, update it, then commit.
**Grader:** Score 1.0 only if `pytest test_app.py` exits 0.

### Task 3 — Hard: Semantic / Logic Conflict (No Markers)

**Repo structure:** `db.py`, `query.py`, `admin_query.py`, `test_logic.py`
**Conflict type:** Developer A renamed `user_id → account_id` in `db.py` on `feature-a`. Developer B (on `main`) added `admin_query.py` using the old `user_id` key. The merge is **completely clean** — no markers. But `pytest` fails.
**Agent must:** Run tests, read failure output, use `git_log` to see Developer A's commit message ("Refactored user_id to account_id"), use `search_code` to find all usages of `user_id`, fix them, commit.
**Grader:** Score 1.0 only if all integration tests pass.

### Task 4 — Adversarial: Both Sides Are Wrong

**Repo structure:** `calculator.py`, `test_calculator.py`
**Conflict type:** Developer A changed `divide(a, b)` to return `a // b` (integer division). Developer B changed it to return `float(a) / b`. Markers appear in `calculator.py`. But the test suite requires IEEE 754 behaviour: `divide(1, 2)` must equal `0.5`, and `divide(10, 0)` must raise `ZeroDivisionError`. Neither conflicting version passes the tests.
**Agent must:** Read the test file to understand the intent, implement a version that satisfies both requirements, resolve markers, commit.
**Grader:** Score 1.0 only if all tests pass with the agent's implementation.

---

## HTTP API Reference

### `POST /reset`

```json
// Request (task_id is optional — omit for random)
{ "task_id": "task_1_easy" }

// Response: AutoMergeObservation
{
  "stdout": "Auto-merging utils.py\nCONFLICT (content): Merge conflict in utils.py\n...",
  "stderr": "",
  "has_unmerged_paths": true,
  "tests_passing": false,
  "current_task": "task_1_easy",
  "step_count": 0
}
```

### `POST /step`

```json
// Request: AutoMergeAction
{ "command": "read_file", "filepath": "utils.py" }
{ "command": "replace_lines", "filepath": "utils.py", "start_line": 3, "end_line": 9, "new_text": "def helper_a():\n    pass\n" }
{ "command": "search_code", "filepath": "user_id" }
{ "command": "git_log" }
{ "command": "show_diff" }
{ "command": "run_tests" }
{ "command": "git_add", "filepath": "utils.py" }
{ "command": "commit_merge" }

// Response: AutoMergeStepResult
{
  "observation": { "stdout": "...", "stderr": "", "has_unmerged_paths": false, "tests_passing": true, "current_task": "task_1_easy", "step_count": 4 },
  "reward": 0.6,
  "done": false,
  "info": {
    "step_count": 4,
    "task_id": "task_1_easy",
    "reward_breakdown": {
      "conflicts_resolved": true,
      "code_runs": true,
      "all_tests_pass": false,
      "efficiency_bonus": 0.08
    }
  }
}
```

### `GET /state`

```json
// Response: AutoMergeState
{
  "current_task": "task_1_easy",
  "unmerged_files": ["utils.py"],
  "modified_files": [],
  "tests_passing": false,
  "step_count": 1,
  "episode_history": ["git_status", "read_file"]
}
```

---

## openenv.yaml

```yaml
name: AutoMergeEnv
version: "1.0.0"
description: >
  An OpenEnv environment where AI agents resolve Git merge conflicts across
  four difficulty levels, including semantic conflicts with no visible markers.
domain: DevOps / Software Engineering
tasks:
  - id: task_1_easy
    difficulty: easy
    description: Textual conflict in a single file
  - id: task_2_medium
    difficulty: medium
    description: Cross-file function signature conflict
  - id: task_3_hard
    difficulty: hard
    description: Semantic conflict — clean merge, broken logic, no markers
  - id: task_4_adversarial
    difficulty: adversarial
    description: Both conflicting versions are wrong — agent must read test intent
reward_range: [0.0, 1.0]
max_steps_per_episode: 30
action_space: structured
observation_space: text
infrastructure:
  vcpu: 2
  memory_gb: 8
  runtime_limit_minutes: 20
```

---

## Infrastructure Constraints

| Constraint | Value |
|-----------|-------|
| vCPU | 2 |
| RAM | 8 GB |
| Docker build limit | 10 minutes |
| Inference runtime limit | 20 minutes |
| External network calls | None (fully offline) |
| External cloud services | None |
| Port | 7860 (Hugging Face Spaces default) |

---

## Design Decisions & Rationale

**Why Git over a mock file system?**
Real Git gives deterministic, reproducible conflict states that exactly mirror developer experience. It also lets us use `git log` as a signal channel for developer intent — a novel mechanic no other OpenEnv environment uses.

**Why subprocess over a Git library (e.g. GitPython)?**
Subprocess output matches exactly what a real developer sees, making the agent's training signal authentic. It also avoids dependencies that can fail silently.

**Why Pydantic for the action space?**
Structured JSON actions prevent the LLM from generating malformed unified diffs or shell injection. The agent picks from a fixed command vocabulary and fills typed fields.

**Why four tasks instead of three?**
The adversarial fourth task targets a failure mode unique to merge resolution: both sides of a conflict being wrong. This is the highest-signal task for distinguishing frontier models from weaker ones, and it fills a gap in existing benchmarks.

**Why an efficiency bonus?**
A binary pass/fail at the end creates sparse gradients for RL training. The efficiency bonus provides a continuous signal that rewards agents for solving conflicts in fewer steps — directly useful for RL fine-tuning.
