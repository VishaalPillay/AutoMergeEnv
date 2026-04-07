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