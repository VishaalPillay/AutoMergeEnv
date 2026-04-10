from __future__ import annotations

import json
import os
from typing import List, Optional

import httpx
from openai import OpenAI

SYSTEM_PROMPT = """\
You are an autonomous agent resolving semantic Git merge conflicts safely and
deterministically. You have access to 10 commands:

1. read_file      — Read a file's contents (requires filepath)
2. replace_lines  — Replace lines in a file (requires filepath, start_line, end_line, new_text)
3. run_tests      — Run pytest to check if tests pass
4. git_status     — Show git status (modified/unmerged files)
5. git_add        — Stage a file for commit (requires filepath)
6. commit_merge   — Commit the merge resolution (ends episode if successful)
7. list_files     — List all .py files in the repo
8. search_code    — Grep a pattern across all .py files (pattern goes in filepath field)
9. show_diff      — Show git diff HEAD (what changed since last commit)
10. git_log       — Show last 10 commits (useful for understanding developer intent)

Strategy:
- Start with git_status to see unmerged files
- Use read_file to inspect conflicted files
- Use replace_lines to fix conflicts (remove markers, keep correct code)
- Use run_tests to verify your fix
- Use git_add on each fixed file, then commit_merge

IMPORTANT: If tests fail after reset but has_unmerged_paths is False, you are on
a semantic conflict task. Use git_log to read the commit history for renamed symbols.
Use search_code to find all files using the old symbol name. Fix them all before committing.

For adversarial tasks where both conflict sides may be wrong, read
test files first to understand the correct expected behaviour, then implement
from scratch.

Prefer minimal, correct edits and verify via tests before committing.
Return your action as a JSON object matching the AutoMergeAction schema.
"""

TASKS = ["task_1_easy", "task_2_medium", "task_3_hard", "task_4_adversarial"]


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


def _llm_plan_action(client: OpenAI, model_name: str, state_payload: dict) -> dict:
    """Ask the LLM to produce a structured action JSON for the current state."""
    valid_commands = [
        "read_file", "replace_lines", "run_tests", "git_status",
        "git_add", "commit_merge", "list_files", "search_code",
        "show_diff", "git_log",
    ]

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Current observation:\n{json.dumps(state_payload, indent=2)}\n\n"
                        "Return the next action as a JSON object with keys: "
                        "command, filepath (optional), start_line (optional), "
                        "end_line (optional), new_text (optional).\n"
                        "Respond with ONLY the JSON, no markdown."
                    ),
                },
            ],
            max_tokens=512,
            temperature=0.0,
        )
        raw = completion.choices[0].message.content.strip()

        # Try to parse as JSON
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[: raw.rfind("```")]
            raw = raw.strip()

        try:
            action = json.loads(raw)
            if isinstance(action, dict) and action.get("command") in valid_commands:
                return action
        except json.JSONDecodeError:
            pass

        # Fallback: find a command keyword in the response
        for cmd in valid_commands:
            if cmd in raw:
                return {"command": cmd}

        return {"command": "git_status"}
    except Exception:
        return {"command": "git_status"}


def main() -> None:
    api_base_url = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
    model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
    hf_token = os.getenv("HF_TOKEN", "dummy_token")
    env_url = os.getenv("ENV_URL", "http://localhost:7860")

    for task_id in TASKS:
        log_start(task=task_id, env=env_url, model=model_name)

        rewards: List[float] = []
        error: Optional[str] = None
        done = False
        step_count = 0

        try:
            client = _build_llm_client(api_base_url=api_base_url, hf_token=hf_token)
            with httpx.Client(timeout=60.0) as http_client:
                # Request the specific task from env
                reset_resp = http_client.post(
                    f"{env_url}/reset", json={"task_id": task_id}
                )
                reset_resp.raise_for_status()
                state_payload = reset_resp.json()

                MAX_STEPS = 25
                for step_num in range(1, MAX_STEPS + 1):
                    step_count = step_num

                    action_dict = _llm_plan_action(
                        client=client,
                        model_name=model_name,
                        state_payload=state_payload,
                    )

                    step_resp = http_client.post(
                        f"{env_url}/step", json=action_dict
                    )
                    step_resp.raise_for_status()
                    step_data = step_resp.json()

                    reward_data = step_data.get("reward", {})
                    raw_reward = float(reward_data.get("value", 0.01))
                    reward_val = max(0.01, min(0.99, raw_reward))

                    done = bool(step_data.get("done", False))
                    rewards.append(reward_val)

                    log_step(
                        step=step_count,
                        action=action_dict.get("command", "unknown"),
                        reward=reward_val,
                        done=done,
                        error=None,
                    )

                    if done:
                        break

                    state_payload = step_data.get("observation", {})

        except Exception as exc:
            error = str(exc)
            step_count = max(step_count, 1)
            log_step(
                step=step_count, action="error", reward=0.01, done=True, error=error
            )
            done = True
            if not rewards:
                rewards.append(0.01)
        finally:
            score = rewards[-1] if rewards else 0.01
            score = max(0.01, min(0.99, score))
            log_end(
                success=(error is None),
                steps=step_count,
                score=score,
                rewards=rewards,
            )


if __name__ == "__main__":
    main()