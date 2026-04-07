from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from environment.models import AutoMergeAction, AutoMergeObservation, AutoMergeReward


class AutoMergeStepResult(BaseModel):
    observation: AutoMergeObservation
    reward: AutoMergeReward
    done: bool
    info: dict[str, Any]


class AutoMergeEnv:
    def __init__(self) -> None:
        self._closed: bool = False
        self._step_count: int = 0

    async def reset(self) -> AutoMergeObservation:
        self._step_count = 0
        self._closed = False
        # TODO: Initialize git repo state and trigger a deterministic conflicted merge.
        return AutoMergeObservation(
            stdout="Environment reset (mock).",
            stderr="",
            has_unmerged_paths=True,
            tests_passing=False,
        )

    async def step(self, action: AutoMergeAction) -> AutoMergeStepResult:
        self._step_count += 1
        # TODO: Route actions to git/file/test operations and compute shaped reward.
        observation = AutoMergeObservation(
            stdout=f"Executed command: {action.command} (mock).",
            stderr="",
            has_unmerged_paths=True,
            tests_passing=False,
        )
        reward = AutoMergeReward(value=0.0)
        return AutoMergeStepResult(
            observation=observation,
            reward=reward,
            done=False,
            info={"step_count": self._step_count, "mock": True},
        )

    async def state(self) -> AutoMergeObservation:
        # TODO: Return live repo state (unmerged paths, test status, commit hash info).
        return AutoMergeObservation(
            stdout=f"Current state requested at step {self._step_count} (mock).",
            stderr="",
            has_unmerged_paths=True,
            tests_passing=False,
        )

    async def close(self) -> None:
        # TODO: Release repository/session resources if needed.
        self._closed = True
