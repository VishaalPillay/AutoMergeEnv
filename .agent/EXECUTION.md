# AutoMergeEnv — Execution Guide

> This document covers every step from a blank directory to a running, validated, Hugging Face–deployed environment. Follow sections in order. No step is optional.

---

## 1. Local Development Setup

### Prerequisites

```bash
# Verify these are installed
git --version          # >= 2.30
python --version       # >= 3.10
docker --version       # >= 24.0
pytest --version       # any
pip --version          # any
```

### Clone and install dependencies

```bash
git clone https://huggingface.co/spaces/<your-username>/AutoMergeEnv
cd AutoMergeEnv

pip install -r requirements.txt
```

### requirements.txt (complete, pinned)

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
pydantic==2.7.4
openai==1.35.3
pytest==8.2.2
httpx==0.27.0
python-dotenv==1.0.1
```

---

## 2. Task Repository Bootstrap

Run this **once** after cloning. It builds the four git repos that power the tasks. If you ever need to reset them, delete `tasks/` and re-run.

```bash
chmod +x setup_tasks.sh
bash setup_tasks.sh
```

### What setup_tasks.sh must do

The script creates four independent git repos under `tasks/`. Each repo has a `main` branch and a `feature-a` branch. When `reset()` calls `git merge feature-a --no-edit` on `main`, it produces the conflict state.

```bash
#!/bin/bash
set -e

# ─────────────────────────────────────────────
# TASK 1 — EASY: Textual conflict in one file
# ─────────────────────────────────────────────
rm -rf tasks/task_1_easy && mkdir -p tasks/task_1_easy
cd tasks/task_1_easy
git init && git branch -M main
git config user.email "env@automerge.ai" && git config user.name "AutoMerge"

cat > utils.py << 'EOF'
def shared_helper():
    return "shared"
EOF

cat > test_utils.py << 'EOF'
from utils import shared_helper, helper_a, helper_b

def test_shared(): assert shared_helper() == "shared"
def test_a(): assert helper_a() == "a"
def test_b(): assert helper_b() == "b"
EOF

git add . && git commit -m "Base: shared_helper and tests"

git checkout -b feature-a
cat > utils.py << 'EOF'
def shared_helper():
    return "shared"

def helper_a():
    return "a"
EOF
git commit -am "Dev A: adds helper_a"

git checkout main
cat > utils.py << 'EOF'
def shared_helper():
    return "shared"

def helper_b():
    return "b"
EOF
git commit -am "Dev B: adds helper_b"

cd ../..

# ─────────────────────────────────────────────
# TASK 2 — MEDIUM: Cross-file signature conflict
# ─────────────────────────────────────────────
rm -rf tasks/task_2_medium && mkdir -p tasks/task_2_medium
cd tasks/task_2_medium
git init && git branch -M main
git config user.email "env@automerge.ai" && git config user.name "AutoMerge"

cat > math_ops.py << 'EOF'
def multiply(a, b):
    return a * b
EOF

cat > app.py << 'EOF'
from math_ops import multiply

def compute(x, y):
    return multiply(x, y)
EOF

cat > test_app.py << 'EOF'
from app import compute
from math_ops import multiply

def test_multiply_basic(): assert multiply(3, 4) == 12
def test_compute(): assert compute(2, 5) == 10
def test_multiply_defaults(): assert multiply(3, 4, scale=1) == 12
EOF

git add . && git commit -m "Base: math_ops and app"

git checkout -b feature-a
cat > math_ops.py << 'EOF'
def multiply(a, b, scale: float = 1.0):
    return a * b * scale
EOF
git commit -am "Dev A: adds scale parameter to multiply"

git checkout main
cat > app.py << 'EOF'
from math_ops import multiply

def compute(x, y):
    return multiply(x, y)

def compute_scaled(x, y):
    # Uses old signature — will break after merge
    return multiply(x, y)
EOF
git commit -am "Dev B: adds compute_scaled using multiply (old signature)"

cd ../..

# ─────────────────────────────────────────────
# TASK 3 — HARD: Semantic conflict — NO markers
# ─────────────────────────────────────────────
rm -rf tasks/task_3_hard && mkdir -p tasks/task_3_hard
cd tasks/task_3_hard
git init && git branch -M main
git config user.email "env@automerge.ai" && git config user.name "AutoMerge"

cat > db.py << 'EOF'
schema = {"user_id": 12345}
EOF

cat > query.py << 'EOF'
from db import schema

def get_user():
    return schema.get("user_id")
EOF

cat > admin_query.py << 'EOF'
from db import schema

def get_admin_id():
    return schema.get("user_id", "admin")
EOF

cat > test_logic.py << 'EOF'
from query import get_user
from admin_query import get_admin_id

def test_get_user(): assert get_user() == 12345
def test_get_admin(): assert get_admin_id() == 12345
def test_admin_fallback():
    from db import schema
    original = schema.copy()
    schema.clear()
    assert get_admin_id() == "admin"
    schema.update(original)
EOF

git add . && git commit -m "Base: schema with user_id, query and admin_query"

git checkout -b feature-a
cat > db.py << 'EOF'
schema = {"account_id": 12345}
EOF
cat > query.py << 'EOF'
from db import schema

def get_user():
    return schema.get("account_id")
EOF
git commit -am "Dev A: Refactored user_id to account_id across schema and query.py"

git checkout main
# Dev B adds a new report module using the OLD key — no conflict, clean merge
cat > report.py << 'EOF'
from db import schema
from admin_query import get_admin_id

def generate_report():
    uid = schema.get("user_id")   # WILL BREAK after merge
    aid = get_admin_id()          # WILL BREAK after merge
    return {"user": uid, "admin": aid}
EOF

cat > test_logic.py << 'EOF'
from query import get_user
from admin_query import get_admin_id
from report import generate_report

def test_get_user(): assert get_user() == 12345
def test_get_admin(): assert get_admin_id() == 12345
def test_report():
    r = generate_report()
    assert r["user"] == 12345
    assert r["admin"] == 12345
def test_admin_fallback():
    from db import schema
    original = schema.copy()
    schema.clear()
    assert get_admin_id() == "admin"
    schema.update(original)
EOF
git add . && git commit -m "Dev B: added report.py and expanded tests using user_id"

# CRITICAL: This merge is CLEAN. No <<<<<<< markers. But tests will fail.
# git merge feature-a is called by env.reset() — NOT here.

cd ../..

# ─────────────────────────────────────────────────────────────
# TASK 4 — ADVERSARIAL: Both conflicting versions are wrong
# ─────────────────────────────────────────────────────────────
rm -rf tasks/task_4_adversarial && mkdir -p tasks/task_4_adversarial
cd tasks/task_4_adversarial
git init && git branch -M main
git config user.email "env@automerge.ai" && git config user.name "AutoMerge"

cat > calculator.py << 'EOF'
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b
EOF

cat > test_calculator.py << 'EOF'
import pytest
from calculator import divide

# The correct behavior: IEEE 754 float division with ZeroDivisionError on zero
def test_divide_basic():       assert divide(10, 4) == 2.5
def test_divide_half():        assert divide(1, 2) == 0.5
def test_divide_exact():       assert divide(9, 3) == 3.0
def test_divide_negative():    assert divide(-6, 2) == -3.0
def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)
EOF

git add . && git commit -m "Base: divide with IEEE 754 float and ZeroDivisionError"

git checkout -b feature-a
# Dev A changes to integer division — WRONG for the tests
cat > calculator.py << 'EOF'
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a // b   # Integer division — WRONG
EOF
git commit -am "Dev A: switched to integer division for performance"

git checkout main
# Dev B removes the zero check — also WRONG
cat > calculator.py << 'EOF'
def divide(a: float, b: float) -> float:
    return a / b   # No zero guard — WRONG
EOF
git commit -am "Dev B: removed zero check, Python raises naturally"

echo ""
echo "✅  All 4 task repos created successfully."
echo "    Run: bash setup_tasks.sh to regenerate if needed."

cd ../..
```

---

## 3. Server Implementation Checklist

### server/app.py — Critical Implementation Requirements

#### ✅ /reset MUST accept task_id

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from environment.env import AutoMergeEnv

app = FastAPI(title="AutoMergeEnv")
env = AutoMergeEnv()

class ResetRequest(BaseModel):
    task_id: Optional[str] = None

@app.post("/reset")
async def reset(request: ResetRequest = ResetRequest()):
    observation = env.reset(task_id=request.task_id)
    return observation.model_dump()

@app.post("/step")
async def step(action: dict):
    from environment.models import AutoMergeAction
    parsed = AutoMergeAction(**action)
    result = env.step(parsed)
    return result.model_dump()

@app.get("/state")
async def state():
    return env.state().model_dump()

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### environment/env.py — Critical Implementation Requirements

#### ✅ reset() must abort in-progress merge before resetting

```python
def reset(self, task_id: Optional[str] = None) -> AutoMergeObservation:
    if self.current_repo:
        # Always abort any in-progress merge — prevents poisoned state between episodes
        run_command(["git", "merge", "--abort"], cwd=self.current_repo, allow_fail=True)
        run_command(["git", "reset", "--hard", "HEAD"], cwd=self.current_repo, allow_fail=True)
        run_command(["git", "clean", "-fd"], cwd=self.current_repo, allow_fail=True)

    if task_id:
        self.current_task = task_id
        self.current_repo = f"tasks/{task_id}"
    else:
        import random
        self.current_task = random.choice([
            "task_1_easy", "task_2_medium", "task_3_hard", "task_4_adversarial"
        ])
        self.current_repo = f"tasks/{self.current_task}"

    run_command(["git", "checkout", "main"], cwd=self.current_repo)
    run_command(["git", "reset", "--hard", "main"], cwd=self.current_repo)
    run_command(["git", "merge", "feature-a", "--no-edit"], cwd=self.current_repo, allow_fail=True)

    self._step_count = 0
    self._episode_history = []
    self._markers_reward_given = False
    self._code_runs_reward_given = False

    return self._build_observation()
```

#### ✅ commit_merge must NOT set done=True on failure

```python
elif action.command == "commit_merge":
    out, err, ret = run_command(
        ["git", "commit", "--no-edit", "-m", "Merge: resolved by agent"],
        cwd=self.current_repo
    )
    stdout = out
    stderr = err
    if ret != 0:
        action_failed = True
        done = False   # CRITICAL: do not end episode on failed commit
        stderr = f"Commit failed — unresolved conflicts or nothing staged. {err}"
    else:
        done = True
```

#### ✅ All 10 commands must be implemented

```python
elif action.command == "list_files":
    out, err, _ = run_command(
        ["find", ".", "-name", "*.py", "-not", "-path", "./.git/*"],
        cwd=self.current_repo
    )
    stdout = out or "No Python files found."

elif action.command == "search_code":
    if not action.filepath:
        stderr = "search_code requires a search pattern in the filepath field."
        action_failed = True
    else:
        out, err, _ = run_command(
            ["grep", "-rn", action.filepath, ".", "--include=*.py"],
            cwd=self.current_repo
        )
        stdout = out if out.strip() else "No matches found."

elif action.command == "show_diff":
    out, err, _ = run_command(["git", "diff", "HEAD"], cwd=self.current_repo)
    stdout = out or "No diff available."

elif action.command == "git_log":
    out, err, _ = run_command(
        ["git", "log", "--oneline", "-10"], cwd=self.current_repo
    )
    stdout = out
```

### environment/graders.py — Critical Implementation Requirements

#### ✅ Task 3/4 marker-removal guard

```python
def markers_resolved_reward(cwd: str, task_id: str, markers_reward_given: bool) -> float:
    if markers_reward_given:
        return 0.0   # Never award twice

    # For semantic tasks: only award if agent has actually changed something
    if task_id in ("task_3_hard", "task_4_adversarial"):
        out, _, _ = run_command(["git", "diff", "--name-only", "HEAD"], cwd=cwd)
        if not out.strip():
            return 0.0   # Agent hasn't done anything yet — no free reward

    if check_for_conflict_markers(cwd):
        return 0.0   # Markers still present

    return 0.20   # Markers are gone and (for semantic tasks) agent did real work


def check_for_conflict_markers(cwd: str) -> bool:
    out, _, ret = run_command(
        ["grep", "-rn", "<<<<<<<", ".", "--include=*.py"],
        cwd=cwd
    )
    return bool(out.strip())


def calculate_step_reward(
    cwd: str,
    task_id: str,
    action_failed: bool,
    step_count: int,
    markers_reward_given: bool,
    code_runs_reward_given: bool,
) -> tuple[float, dict, bool]:
    """
    Returns: (total_reward, breakdown_dict, all_tests_pass)
    """
    reward = 0.0
    breakdown = {
        "action_penalty": 0.0,
        "conflicts_resolved": 0.0,
        "code_runs": 0.0,
        "all_tests_pass": 0.0,
        "efficiency_bonus": 0.0,
    }
    all_tests_pass = False

    if action_failed:
        breakdown["action_penalty"] = -0.10
        reward -= 0.10
        return max(0.01, reward), breakdown, all_tests_pass

    # Marker removal reward (given at most once per episode)
    m_reward = markers_resolved_reward(cwd, task_id, markers_reward_given)
    breakdown["conflicts_resolved"] = m_reward
    reward += m_reward

    # Run tests
    _, _, ret = run_command(["pytest", "-v", "--tb=short", "-q"], cwd=cwd)

    if ret in (0, 1) and not code_runs_reward_given:
        breakdown["code_runs"] = 0.40
        reward += 0.40

    if ret == 0:
        all_tests_pass = True
        breakdown["all_tests_pass"] = 0.40
        reward += 0.40
        # Efficiency bonus — only on final success
        eff = max(0.0, 0.10 * (1.0 - step_count / 20.0))
        breakdown["efficiency_bonus"] = round(eff, 3)
        reward += eff

    return min(1.0, max(0.01, round(reward, 3))), breakdown, all_tests_pass
```

---

## 4. inference.py — Structured Log Format

The evaluator parses stdout. Deviate from this format and your score will be recorded as 0.

```python
#!/usr/bin/env python3
"""
AutoMergeEnv Baseline Inference Script
Uses OpenAI client pointing at API_BASE_URL / MODEL_NAME.
"""
import os, json, time
from openai import OpenAI

API_BASE_URL = os.environ["API_BASE_URL"]
MODEL_NAME   = os.environ["MODEL_NAME"]
ENV_URL      = os.environ.get("ENV_URL", "http://localhost:7860")

client = OpenAI(api_key=os.environ.get("HF_TOKEN", "dummy"), base_url=API_BASE_URL)

import httpx
http = httpx.Client(base_url=ENV_URL, timeout=60)

TASKS = ["task_1_easy", "task_2_medium", "task_3_hard", "task_4_adversarial"]
MAX_STEPS = 25

SYSTEM_PROMPT = """You are an expert software engineer resolving Git merge conflicts.
You control a real git repository via structured JSON actions.

Available commands:
- {"command": "git_status"}
- {"command": "git_log"}
- {"command": "show_diff"}
- {"command": "list_files"}
- {"command": "read_file", "filepath": "utils.py"}
- {"command": "search_code", "filepath": "PATTERN"}
- {"command": "replace_lines", "filepath": "utils.py", "start_line": 3, "end_line": 7, "new_text": "..."}
- {"command": "run_tests"}
- {"command": "git_add", "filepath": "utils.py"}
- {"command": "commit_merge"}

Rules:
1. ALWAYS start with git_status, git_log, and list_files to understand the situation.
2. For Task 3 (hard): the merge may be CLEAN but tests still fail. Read git_log carefully.
3. Use search_code to find all usages of a symbol before renaming it.
4. Only call commit_merge when run_tests passes (exit 0).
5. Respond with ONLY a valid JSON object — no markdown, no explanation.
"""

def call_llm(messages):
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        max_tokens=512,
        temperature=0.0,
    )
    return resp.choices[0].message.content.strip()

def run_episode(task_id: str) -> dict:
    # Reset
    obs = http.post("/reset", json={"task_id": task_id}).json()

    print(json.dumps({
        "event": "START",
        "task_id": task_id,
        "timestamp": time.time(),
        "initial_observation": obs,
    }))

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Task: {task_id}\nInitial state:\n{json.dumps(obs, indent=2)}\n\nBegin. Respond with your first action as JSON."},
    ]

    total_reward = 0.0
    done = False
    step = 0

    while not done and step < MAX_STEPS:
        raw = call_llm(messages)

        try:
            action = json.loads(raw)
        except json.JSONDecodeError:
            action = {"command": "git_status"}  # safe fallback

        result = http.post("/step", json=action).json()
        reward  = result.get("reward", 0.0)
        done    = result.get("done", False)
        info    = result.get("info", {})
        obs_new = result.get("observation", {})

        total_reward = reward  # last reward reflects cumulative signal

        print(json.dumps({
            "event": "STEP",
            "task_id": task_id,
            "step": step + 1,
            "action": action,
            "reward": reward,
            "done": done,
            "info": info,
            "observation_summary": {
                "has_unmerged_paths": obs_new.get("has_unmerged_paths"),
                "tests_passing": obs_new.get("tests_passing"),
            },
        }))

        messages.append({"role": "assistant", "content": raw})
        messages.append({
            "role": "user",
            "content": f"Result:\n{json.dumps(result, indent=2)}\n\nNext action:"
        })
        step += 1

    print(json.dumps({
        "event": "END",
        "task_id": task_id,
        "total_steps": step,
        "final_reward": total_reward,
        "success": done and obs_new.get("tests_passing", False),
        "timestamp": time.time(),
    }))

    return {"task_id": task_id, "reward": total_reward, "steps": step}

if __name__ == "__main__":
    results = []
    for task_id in TASKS:
        result = run_episode(task_id)
        results.append(result)

    print(json.dumps({"event": "SUMMARY", "results": results}))
```

---

## 5. Dockerfile

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    grep \
    findutils \
    && rm -rf /var/lib/apt/lists/*

# Configure git identity for the container
RUN git config --global user.email "env@automerge.ai" \
 && git config --global user.name "AutoMergeEnv" \
 && git config --global init.defaultBranch main

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bootstrap all task repos at build time (deterministic, fast)
RUN bash setup_tasks.sh

# Expose HF Spaces port
EXPOSE 7860

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
```

> **Note:** Running `setup_tasks.sh` at Docker build time means task repos are baked into the image. Each container starts in a known state with no setup latency.

---

## 6. Validation Checklist (Run Before Every Submission)

### 6.1 openenv validate

```bash
openenv validate .
# Must output: ✅ All checks passed
```

### 6.2 Docker build and run

```bash
docker build -t automergeenv . --no-cache
docker run -p 7860:7860 automergeenv
# Wait for: INFO: Application startup complete.
```

### 6.3 Endpoint smoke tests

```bash
# Health check
curl http://localhost:7860/health
# Expected: {"status":"ok"}

# Reset to specific task
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task_1_easy"}'
# Expected: observation JSON with has_unmerged_paths: true

# Step with git_status
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"command": "git_status"}'
# Expected: step result with reward > 0

# State check
curl http://localhost:7860/state
# Expected: full state JSON

# Task 3 reset — MUST have has_unmerged_paths: false (semantic conflict)
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task_3_hard"}'
# Expected: has_unmerged_paths: false, tests_passing: false
```

### 6.4 Inference script

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="<your_key>"
export ENV_URL="http://localhost:7860"

python inference.py
# Must complete without exception
# Must emit [START], [STEP], [END] events for all 4 tasks
# Runtime must be < 20 minutes
```

### 6.5 Grader score range check

```bash
python - << 'EOF'
import httpx, json

http = httpx.Client(base_url="http://localhost:7860", timeout=60)

for task_id in ["task_1_easy", "task_2_medium", "task_3_hard", "task_4_adversarial"]:
    obs = http.post("/reset", json={"task_id": task_id}).json()
    result = http.post("/step", json={"command": "run_tests"}).json()
    reward = result["reward"]
    assert 0.0 <= reward <= 1.0, f"Reward out of range for {task_id}: {reward}"
    print(f"✅ {task_id}: reward={reward}")

print("All grader range checks passed.")
EOF
```

### 6.6 Reset idempotency check

```bash
python - << 'EOF'
import httpx

http = httpx.Client(base_url="http://localhost:7860", timeout=60)

for i in range(3):
    obs = http.post("/reset", json={"task_id": "task_1_easy"}).json()
    assert obs["has_unmerged_paths"] is True, f"Reset {i} produced clean state — merge abort failed"
    assert obs["step_count"] == 0, f"Reset {i} did not zero step count"
    print(f"✅ Reset {i}: has_unmerged_paths=True, step_count=0")

print("Idempotency check passed.")
EOF
```

---

## 7. Hugging Face Spaces Deployment

### 7.1 Repository setup

```bash
# Your HF Space must be tagged with: openenv
# Space SDK: Docker
# Port: 7860
```

### 7.2 Set Space secrets (Settings → Variables and Secrets)

| Secret | Value |
|--------|-------|
| `HF_TOKEN` | Your HF API token |
| `API_BASE_URL` | `https://api.openai.com/v1` (or your LLM endpoint) |
| `MODEL_NAME` | `gpt-4o-mini` (or your model) |

### 7.3 Push to HF

```bash
git remote add hf https://huggingface.co/spaces/<username>/AutoMergeEnv
git push hf main
```

### 7.4 Verify Space is live

```bash
HF_SPACE_URL="https://<username>-automergeenv.hf.space"

curl ${HF_SPACE_URL}/health
# Expected: {"status":"ok"}

curl -X POST ${HF_SPACE_URL}/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task_1_easy"}'
# Must return 200 with observation JSON
```

---

## 8. Baseline Scores (Reference)

These are the expected baseline scores running `gpt-4o-mini` at temperature 0.

| Task | Expected Reward | Notes |
|------|----------------|-------|
| `task_1_easy` | 0.60 – 0.80 | Usually resolves markers, sometimes fails tests |
| `task_2_medium` | 0.40 – 0.60 | Often misses the broken call in `app.py` |
| `task_3_hard` | 0.20 – 0.40 | Rarely traces the schema rename via git_log |
| `task_4_adversarial` | 0.10 – 0.30 | Almost never reads test intent before resolving |

If your baseline scores are significantly higher than these on `task_3_hard` or `task_4_adversarial`, your grader likely has a bug (awarding reward too easily).

---

## 9. Common Failure Modes & Fixes

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| `task_3_hard` reset returns `has_unmerged_paths: true` | `git merge feature-a` is creating textual conflicts — Task 3 setup is wrong | Re-read Task 3 in `setup_tasks.sh`: `feature-a` must only touch `db.py` and `query.py`; `main` must only touch `admin_query.py` |
| `reset()` occasionally returns poisoned state | Prior merge was in-progress when reset was called | Add `git merge --abort` as the very first command in `reset()` with `allow_fail=True` |
| `commit_merge` ends episode even when commit fails | Missing return code check | Check `ret != 0` and set `done = False`, `action_failed = True` |
| Task 3 awards `+0.20` at episode start | No guard on marker-removal reward for semantic tasks | Apply `markers_resolved_reward()` guard that checks agent has made changes |
| `inference.py` fails on Phase 2 eval | `task_id` not passed to `/reset` | Ensure `ResetRequest` model is accepted by the endpoint |
| Docker build fails on `setup_tasks.sh` | Git identity not configured | Add `RUN git config --global user.email` and `user.name` before running setup |
| `/state` returns 500 | `episode_history` not initialized on first call | Initialize `self._episode_history = []` and `self.current_task = None` in `__init__` |
