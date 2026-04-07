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


class AutoMergeReward(BaseModel):
    value: float
