from __future__ import annotations

import os
import random
from typing import Any, Optional

from pydantic import BaseModel

from environment.models import (
    AutoMergeAction,
    AutoMergeObservation,
    AutoMergeReward,
    AutoMergeState,
)
from environment.file_utils import read_file, replace_lines
from environment.git_utils import run_command, check_git_status
from environment.graders import calculate_step_reward


class AutoMergeStepResult(BaseModel):
    observation: AutoMergeObservation
    reward: AutoMergeReward
    done: bool
    info: dict[str, Any]


class AutoMergeEnv:
    TASK_DIRS = [
        "tasks/task_1_easy",
        "tasks/task_2_medium",
        "tasks/task_3_hard",
        "tasks/task_4_adversarial",
    ]

    def __init__(self) -> None:
        self._closed: bool = False
        self._step_count: int = 0
        self._episode_history: list[str] = []
        self._markers_reward_given: bool = False
        self._code_runs_reward_given: bool = False
        self.current_task: str = ""
        self.current_repo: str = ""

    # ------------------------------------------------------------------
    # reset  (FIX 1 + FIX 2)
    # ------------------------------------------------------------------
    def reset(self, task_id: Optional[str] = None) -> AutoMergeObservation:
        # Zero out per-episode state
        self._step_count = 0
        self._episode_history = []
        self._markers_reward_given = False
        self._code_runs_reward_given = False
        self._closed = False

        # Resolve task directory
        if task_id:
            self.current_task = task_id
            self.current_repo = f"tasks/{task_id}"
        else:
            self.current_repo = random.choice(self.TASK_DIRS)
            self.current_task = os.path.basename(self.current_repo)

        # FIX 2: Abort any in-progress merge first (allow_fail=True by design —
        # run_command uses check=False)
        run_command(["git", "merge", "--abort"], cwd=self.current_repo)
        run_command(["git", "reset", "--hard", "HEAD"], cwd=self.current_repo)
        run_command(["git", "clean", "-fd"], cwd=self.current_repo)
        run_command(["git", "checkout", "main"], cwd=self.current_repo)
        run_command(["git", "reset", "--hard", "main"], cwd=self.current_repo)

        # Re-trigger the merge conflict
        merge_out, merge_err, _ = run_command(
            ["git", "merge", "feature-a", "--no-edit"], cwd=self.current_repo
        )

        # Build and return initial observation
        obs = self._build_observation()
        obs.stdout = merge_out or "Merge completed."
        obs.stderr = merge_err
        return obs

    # ------------------------------------------------------------------
    # step  (FIX 3 + FIX 7 + FIX 9)
    # ------------------------------------------------------------------
    def step(self, action: AutoMergeAction) -> AutoMergeStepResult:
        self._step_count += 1
        self._episode_history.append(action.command)
        done = False
        stdout = ""
        stderr = ""
        action_failed = False

        try:
            if action.command == "read_file":
                if action.filepath:
                    stdout = read_file(action.filepath, cwd=self.current_repo)
                else:
                    stderr = "Missing filepath"
                    action_failed = True

            elif action.command == "replace_lines":
                if (
                    action.filepath
                    and action.start_line is not None
                    and action.end_line is not None
                ):
                    new_text = action.new_text if action.new_text is not None else ""
                    stdout = replace_lines(
                        action.filepath,
                        action.start_line,
                        action.end_line,
                        new_text,
                        cwd=self.current_repo,
                    )
                else:
                    stderr = "Missing arguments for replace_lines"
                    action_failed = True

            elif action.command == "run_tests":
                out, err, _ = run_command(
                    ["pytest", "-v", "--tb=short"], cwd=self.current_repo
                )
                stdout = out
                stderr = err

            elif action.command == "git_status":
                stdout = check_git_status(cwd=self.current_repo)

            elif action.command == "git_add":
                if action.filepath:
                    out, err, ret = run_command(
                        ["git", "add", action.filepath], cwd=self.current_repo
                    )
                    stdout = out
                    stderr = err
                    if ret != 0:
                        action_failed = True
                else:
                    stderr = "Missing filepath"
                    action_failed = True

            # FIX 3: commit_merge only sets done=True when ret == 0
            elif action.command == "commit_merge":
                out, err, ret = run_command(
                    ["git", "commit", "--no-edit", "-m", "Merge: resolved by agent"],
                    cwd=self.current_repo,
                )
                stdout = out
                stderr = err
                if ret != 0:
                    action_failed = True
                    done = False
                    stderr = f"Commit failed — unresolved conflicts or nothing staged. {err}"
                else:
                    done = True

            # FIX 7: New commands
            elif action.command == "list_files":
                out, err, _ = run_command(
                    ["find", ".", "-name", "*.py", "-not", "-path", "./.git/*"],
                    cwd=self.current_repo,
                )
                stdout = out or "No Python files found."

            elif action.command == "search_code":
                if not action.filepath:
                    stderr = "search_code requires a pattern in the filepath field."
                    action_failed = True
                else:
                    out, err, _ = run_command(
                        ["grep", "-rn", action.filepath, ".", "--include=*.py"],
                        cwd=self.current_repo,
                    )
                    stdout = out if out.strip() else "No matches found."

            elif action.command == "show_diff":
                out, err, _ = run_command(
                    ["git", "diff", "HEAD"], cwd=self.current_repo
                )
                stdout = out or "No diff (working tree is clean)."

            elif action.command == "git_log":
                out, err, _ = run_command(
                    ["git", "log", "--oneline", "-10"], cwd=self.current_repo
                )
                stdout = out

            else:
                stderr = f"Unknown command: {action.command}"
                action_failed = True

        except Exception as e:
            stderr = str(e)
            action_failed = True

        # FIX 8 integration: call the new shaped reward function
        reward_val, breakdown, all_tests_pass, self._markers_reward_given, self._code_runs_reward_given = (
            calculate_step_reward(
                cwd=self.current_repo,
                task_id=self.current_task,
                action_failed=action_failed,
                step_count=self._step_count,
                markers_reward_given=self._markers_reward_given,
                code_runs_reward_given=self._code_runs_reward_given,
            )
        )

        obs = self._build_observation()
        # Override stdout/stderr with command output
        if stdout or stderr:
            obs.stdout = stdout
            obs.stderr = stderr
        else:
            obs.stdout = "Command completed with no output."

        # FIX 9: Enriched info dict
        info = {
            "step_count": self._step_count,
            "task_id": self.current_task,
            "has_unmerged_paths": obs.has_unmerged_paths,
            "tests_passing": obs.tests_passing,
            "episode_history": self._episode_history[-5:],
            "reward_breakdown": breakdown,
            "markers_resolved": self._markers_reward_given,
            "code_runs_rewarded": self._code_runs_reward_given,
        }

        reward = AutoMergeReward(
            value=reward_val,
            breakdown=breakdown,
            done=done,
            info=info,
        )

        return AutoMergeStepResult(
            observation=obs,
            reward=reward,
            done=done,
            info=info,
        )

    # ------------------------------------------------------------------
    # state  (FIX 10)
    # ------------------------------------------------------------------
    def state(self) -> AutoMergeState:
        out, _, _ = run_command(
            ["git", "status", "--porcelain"], cwd=self.current_repo
        )

        unmerged_files: list[str] = []
        modified_files: list[str] = []
        for line in out.splitlines():
            if len(line) < 3:
                continue
            xy = line[:2]
            filepath = line[3:].strip()
            if xy in ("UU", "UD", "DU", "DD", "AA", "AU", "UA"):
                unmerged_files.append(filepath)
            elif xy.strip():
                modified_files.append(filepath)

        _, _, ret = run_command(["pytest", "-q"], cwd=self.current_repo)
        tests_passing = ret == 0

        return AutoMergeState(
            current_task=self.current_task,
            unmerged_files=unmerged_files,
            modified_files=modified_files,
            tests_passing=tests_passing,
            step_count=self._step_count,
            episode_history=list(self._episode_history),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_observation(self) -> AutoMergeObservation:
        """Build observation by inspecting git status and running tests."""
        out, _, _ = run_command(
            ["git", "status", "--porcelain"], cwd=self.current_repo
        )

        has_unmerged = False
        for line in out.splitlines():
            if len(line) >= 2 and line[0:2] in (
                "UU", "UD", "DU", "DD", "AA", "AU", "UA"
            ):
                has_unmerged = True
                break

        _, _, ret = run_command(["pytest", "-q"], cwd=self.current_repo)
        tests_passing = ret == 0

        return AutoMergeObservation(
            stdout="",
            stderr="",
            has_unmerged_paths=has_unmerged,
            tests_passing=tests_passing,
            current_task=self.current_task,
            step_count=self._step_count,
        )

    async def close(self) -> None:
        self._closed = True