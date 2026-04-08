from __future__ import annotations

import os
import random
from typing import Any

from pydantic import BaseModel

from environment.models import AutoMergeAction, AutoMergeObservation, AutoMergeReward
from environment.file_utils import read_file, replace_lines
from environment.git_utils import run_command, check_git_status
from environment.graders import calculate_reward


class AutoMergeStepResult(BaseModel):
    observation: AutoMergeObservation
    reward: AutoMergeReward
    done: bool
    info: dict[str, Any]


class AutoMergeEnv:
    def __init__(self) -> None:
        self._closed: bool = False
        self._step_count: int = 0
        self.task_paths = ["tasks/task_1_easy", "tasks/task_2_medium", "tasks/task_3_hard"]
        self.current_repo = ""

    async def reset(self) -> AutoMergeObservation:
        self._step_count = 0
        self._closed = False
        
        # Select a task randomly
        self.current_repo = random.choice(self.task_paths)
        
        # Run a hard reset to ensure a clean state
        run_command(["git", "reset", "--hard"], cwd=self.current_repo)
        run_command(["git", "clean", "-fd"], cwd=self.current_repo)
        
        # Re-trigger the merge conflict
        run_command(["git", "merge", "feature-a", "--no-edit"], cwd=self.current_repo)
        
        return await self.state()

    async def step(self, action: AutoMergeAction) -> AutoMergeStepResult:
        self._step_count += 1
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
                if action.filepath and action.start_line is not None and action.end_line is not None:
                    new_text = action.new_text if action.new_text is not None else ""
                    stdout = replace_lines(action.filepath, action.start_line, action.end_line, new_text, cwd=self.current_repo)
                else:
                    stderr = "Missing arguments for replace_lines"
                    action_failed = True
                    
            elif action.command == "run_tests":
                out, err, _ = run_command(["pytest"], cwd=self.current_repo)
                stdout = out
                stderr = err
                
            elif action.command == "git_status":
                stdout = check_git_status(cwd=self.current_repo)
                
            elif action.command == "git_add":
                if action.filepath:
                    out, err, ret = run_command(["git", "add", action.filepath], cwd=self.current_repo)
                    stdout = out
                    stderr = err
                    if ret != 0:
                        action_failed = True
                else:
                    stderr = "Missing filepath"
                    action_failed = True
                    
            elif action.command == "commit_merge":
                out, err, ret = run_command(["git", "commit", "--no-edit"], cwd=self.current_repo)
                stdout = out
                stderr = err
                done = True
                if ret != 0:
                    action_failed = True
                    
            else:
                stderr = f"Unknown command: {action.command}"
                action_failed = True
                
        except Exception as e:
            stderr = str(e)
            action_failed = True

        reward_val = calculate_reward(self.current_repo, action_failed=action_failed)
        reward = AutoMergeReward(value=reward_val)
        
        obs = await self.state()
        
        # Set stdout/stderr to the command output
        if stdout or stderr:
            obs.stdout = stdout
            obs.stderr = stderr
        else:
            obs.stdout = "Command completed with no output."
            
        return AutoMergeStepResult(
            observation=obs,
            reward=reward,
            done=done,
            info={"step_count": self._step_count}
        )

    async def state(self) -> AutoMergeObservation:
        out, err, _ = run_command(["git", "status", "--porcelain"], cwd=self.current_repo)
        
        # Check for unmerged paths by looking for "U" in the git status output
        # E.g. "UU", "UD", "DU", "DD", "AA", "AU", "UA" indicates unmerged/conflict.
        has_unmerged = False
        for line in out.splitlines():
            if len(line) >= 2 and line[0:2] in ("UU", "UD", "DU", "DD", "AA", "AU", "UA"):
                has_unmerged = True
                break
                
        # Run tests to see if they are passing
        _, _, ret = run_command(["pytest"], cwd=self.current_repo)
        tests_passing = (ret == 0)
        
        return AutoMergeObservation(
            stdout="",
            stderr="",
            has_unmerged_paths=has_unmerged,
            tests_passing=tests_passing,
        )

    async def close(self) -> None:
        self._closed = True
