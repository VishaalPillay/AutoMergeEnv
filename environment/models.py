from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

AllowedCommand = Literal[
    "read_file",
    "replace_lines",
    "run_tests",
    "git_status",
    "git_add",
    "commit_merge",
    "list_files",
    "search_code",
    "show_diff",
    "git_log",
]


class AutoMergeAction(BaseModel):
    command: AllowedCommand
    filepath: Optional[str] = None
    start_line: Optional[int] = Field(default=None, ge=1)
    end_line: Optional[int] = Field(default=None, ge=1)
    new_text: Optional[str] = None


class AutoMergeObservation(BaseModel):
    stdout: str
    stderr: str
    has_unmerged_paths: bool
    tests_passing: bool
    current_task: str = ""
    step_count: int = 0


class AutoMergeReward(BaseModel):
    value: float
    breakdown: dict
    done: bool
    info: dict


class AutoMergeState(BaseModel):
    current_task: str
    unmerged_files: list[str]
    modified_files: list[str]
    tests_passing: bool
    step_count: int
    episode_history: list[str]
