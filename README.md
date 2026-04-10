---
title: AutoMergeEnv
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# AutoMergeEnv

AutoMergeEnv is a fully deterministic, containerized [OpenEnv](https://huggingface.co/openenv) environment that benchmarks AI agent capability against one of the most universal developer pain points: **resolving Git merge conflicts**. It spans four conflict archetypes — textual, cross-file semantic, logic-level semantic (no markers), and adversarial (both sides wrong) — each requiring a progressively deeper understanding of developer intent, not just syntactic resolution. The environment is zero-cloud, zero-external-dependency, and fully reproducible on 2 vCPU / 8 GB RAM hardware.

---

## Action Space

All actions are submitted as structured JSON via `POST /step`.

| Command | Parameters | Description |
|---------|-----------|-------------|
| `read_file` | `filepath` (required) | Read a file's contents with 1-indexed line numbers |
| `replace_lines` | `filepath`, `start_line`, `end_line`, `new_text` (all required) | Replace a contiguous block of lines in a file |
| `run_tests` | — | Run `pytest -v --tb=short` and return stdout/stderr |
| `git_status` | — | Run `git status --short` to see modified/unmerged files |
| `git_add` | `filepath` (required) | Stage a file for commit |
| `commit_merge` | — | Commit the merge resolution. Sets `done=True` only on success |
| `list_files` | — | List all `.py` files in the repo (excludes `.git/`) |
| `search_code` | `filepath` (pattern) | Grep a regex/string pattern across all `.py` files |
| `show_diff` | — | Run `git diff HEAD` to see uncommitted changes |
| `git_log` | — | Show last 10 commits (`git log --oneline -10`) |

---

## Observation Space

Returned from both `/reset` and `/step` as the `observation` field.

| Field | Type | Description |
|-------|------|-------------|
| `stdout` | `str` | Command output, file contents, or test results |
| `stderr` | `str` | Error messages, tracebacks, or commit failure details |
| `has_unmerged_paths` | `bool` | `True` if conflict markers (`<<<<<<<`) exist in any file |
| `tests_passing` | `bool` | `True` if `pytest` exits with code 0 |
| `current_task` | `str` | The active task ID (e.g., `task_3_hard`) |
| `step_count` | `int` | Number of actions taken in the current episode |

---

## Tasks

| Task ID | Difficulty | Description | What Makes It Hard |
|---------|-----------|-------------|-------------------|
| `task_1_easy` | Easy | Textual conflict in a single file (`utils.py`) | Standard `<<<<<<<` markers — agent must keep both functions |
| `task_2_medium` | Medium | Cross-file function signature conflict | Markers in `math_ops.py`, but broken call in `app.py` must also be found and fixed |
| `task_3_hard` | Hard | Semantic conflict — clean merge, broken logic | **No conflict markers at all.** `git merge` succeeds cleanly, but tests fail because `user_id` was renamed to `account_id` and new files still use the old key. Agent must use `git_log` and `search_code` to discover and fix the rename |
| `task_4_adversarial` | Adversarial | Both conflicting versions are wrong | Markers in `calculator.py`, but neither side's implementation passes tests. Agent must read `test_calculator.py` to infer the correct IEEE 754 float division with `ZeroDivisionError` guard |

---

## Reward Function

Rewards are shaped per-step to provide continuous learning signal. Maximum score is **1.0**.

| Component | Value | Condition |
|-----------|-------|-----------|
| Action penalty | **-0.10** | Invalid action, bad parameters, or subprocess error |
| Conflicts resolved | **+0.20** | All `<<<<<<<` markers removed (awarded once per episode). For Task 3/4: only awarded after agent modifies at least one file |
| Code runs | **+0.40** | `pytest` exits with code 0 or 1 (code doesn't crash). Awarded once per episode |
| All tests pass | **+0.40** | `pytest` exits with code 0 (all tests green) |
| Efficiency bonus | **+0.10 × (1 − steps/20)** | Rewards solving in fewer steps. Only awarded when all tests pass |

Minimum returned reward: `0.01` (never exactly zero to avoid sparse signal confusion).

---

## Baseline Scores

Expected reward ranges for a capable agent:

| Task | Expected Reward | Notes |
|------|----------------|-------|
| `task_1_easy` | 0.90 – 1.00 | Straightforward marker resolution |
| `task_2_medium` | 0.70 – 1.00 | Requires cross-file reasoning |
| `task_3_hard` | 0.50 – 1.00 | Requires `git_log` + `search_code` for semantic understanding |
| `task_4_adversarial` | 0.40 – 1.00 | Requires reading tests and implementing from scratch |

---

## Docker Setup

### Build

```bash
docker build -t automergeenv . --no-cache
```

Task repositories are bootstrapped at build time via `setup_tasks.sh`, so they are baked into the image with zero startup latency.

### Run

```bash
docker run -p 7860:7860 automergeenv
```

The server starts on `http://localhost:7860`. Verify with:

```bash
curl http://localhost:7860/health
# → {"status": "ok"}
```

---

## Usage (Inference)

Set the required environment variables and run:

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="<your-token>"
export ENV_URL="http://localhost:7860"

python inference.py
```

The inference script loops over all 4 tasks, emitting structured `[START]`, `[STEP]`, and `[END]` log events for each. It must complete within **20 minutes**.

---

## API Reference

### `GET /health`
Returns `{"status": "ok"}`.

### `POST /reset`
```json
{"task_id": "task_1_easy"}
```
Returns: `AutoMergeObservation` — the initial state after triggering the merge.

### `POST /step`
```json
{"command": "read_file", "filepath": "utils.py"}
```
Returns: `{observation, reward, done, info}`.

### `GET /state`
Returns: `AutoMergeState` — current task, unmerged files, modified files, test status, episode history.

---

## Why This Environment Is Novel

AutoMergeEnv is the first OpenEnv environment to use **git commit history as an intent signal channel**. In Task 3, the only way to resolve the semantic conflict is to read `git log` and discover that a rename occurred — information invisible in the file contents alone. The adversarial Task 4 pushes further: both sides of the conflict are wrong, and the agent must **infer correct behaviour from the test suite**, ignoring both conflicting implementations. Combined with shaped per-step rewards, an efficiency bonus, and four difficulty tiers, AutoMergeEnv provides a rich, reproducible benchmark for evaluating agentic coding capability on a real-world developer workflow.