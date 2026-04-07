from __future__ import annotations

import os
from typing import List, Optional

import httpx
from openai import OpenAI

SYSTEM_PROMPT = (
    "You are an autonomous agent resolving semantic Git merge conflicts safely and "
    "deterministically. Prefer minimal, correct edits and verify via tests."
)


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(
    step: int,
    action: str,
    reward: float,
    done: bool,
    error: Optional[str],
) -> None:
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={str(done).lower()} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


def _build_llm_client(api_base_url: str, hf_token: str) -> OpenAI:
    return OpenAI(base_url=api_base_url, api_key=hf_token)


def _llm_plan_action(client: OpenAI, model_name: str, state_payload: dict) -> str:
    # Baseline placeholder call to keep the OpenAI client integrated in Phase 2.
    # The planner currently defaults to "git_status" regardless of response.
    _ = client.responses.create(
        model=model_name,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Current state: {state_payload}"},
            {
                "role": "user",
                "content": (
                    "Return the next command as one of: read_file, replace_lines, "
                    "run_tests, git_status, git_add, commit_merge."
                ),
            },
        ],
        max_output_tokens=16,
    )
    return "git_status"


def main() -> None:
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:7860")
    model_name = os.getenv("MODEL_NAME", "gpt-4.1-mini")
    hf_token = os.getenv("HF_TOKEN", "")

    env_url = "http://localhost:7860"
    task_name = "automerge_task"
    rewards: List[float] = []

    log_start(task=task_name, env=env_url, model=model_name)

    error: Optional[str] = None
    done = False
    step_count = 0

    try:
        client = _build_llm_client(api_base_url=api_base_url, hf_token=hf_token)
        with httpx.Client(timeout=30.0) as http_client:
            reset_resp = http_client.post(f"{env_url}/reset")
            reset_resp.raise_for_status()

            state_resp = http_client.get(f"{env_url}/state")
            state_resp.raise_for_status()
            state_payload = state_resp.json()

            action_cmd = _llm_plan_action(
                client=client,
                model_name=model_name,
                state_payload=state_payload,
            )

            step_payload = {"command": action_cmd}
            step_resp = http_client.post(f"{env_url}/step", json=step_payload)
            step_resp.raise_for_status()
            step_data = step_resp.json()

            reward_val = float(step_data.get("reward", {}).get("value", 0.0))
            done = bool(step_data.get("done", False))
            step_count = 1
            rewards.append(reward_val)

            log_step(
                step=step_count,
                action=action_cmd,
                reward=reward_val,
                done=done,
                error=None,
            )
    except Exception as exc:
        error = str(exc)
        step_count = max(step_count, 1)
        log_step(
            step=step_count,
            action="error",
            reward=0.0,
            done=True,
            error=error,
        )
        done = True
        if not rewards:
            rewards.append(0.0)
    finally:
        score = rewards[-1] if rewards else 0.0
        log_end(success=(error is None), steps=step_count, score=score, rewards=rewards)


if __name__ == "__main__":
    main()
