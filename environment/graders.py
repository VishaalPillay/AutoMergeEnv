from environment.git_utils import run_command


def check_for_conflict_markers(cwd: str) -> bool:
    """Checks if standard Git conflict markers remain in any tracked file."""
    stdout, _, _ = run_command(["git", "grep", "<<<<<<<"], cwd=cwd)
    return bool(stdout.strip())


def calculate_step_reward(
    cwd: str,
    task_id: str,
    action_failed: bool,
    step_count: int,
    markers_reward_given: bool,
    code_runs_reward_given: bool,
):
    """
    Calculates per-step shaped reward.

    Returns:
        (reward, breakdown, all_tests_pass, markers_reward_given, code_runs_reward_given)
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
        return (
            max(0.01, reward),
            breakdown,
            all_tests_pass,
            markers_reward_given,
            code_runs_reward_given,
        )

    # Marker removal — award at most once, with Task 3/4 guard
    if not markers_reward_given:
        give_marker_reward = True
        if task_id in ("task_3_hard", "task_4_adversarial"):
            changed, _, _ = run_command(
                ["git", "diff", "--name-only", "HEAD"], cwd=cwd
            )
            if not changed.strip():
                give_marker_reward = False
        if give_marker_reward:
            still_has_markers = check_for_conflict_markers(cwd)
            if not still_has_markers:
                breakdown["conflicts_resolved"] = 0.20
                reward += 0.20
                markers_reward_given = True

    # Run tests
    _, _, ret = run_command(["pytest", "-v", "--tb=short", "-q"], cwd=cwd)

    if ret in (0, 1) and not code_runs_reward_given:
        breakdown["code_runs"] = 0.40
        reward += 0.40
        code_runs_reward_given = True

    if ret == 0:
        all_tests_pass = True
        breakdown["all_tests_pass"] = 0.40
        reward += 0.40
        eff = max(0.0, 0.10 * (1.0 - step_count / 20.0))
        breakdown["efficiency_bonus"] = round(eff, 3)
        reward += eff

    return (
        min(0.99, max(0.01, round(reward, 3))),
        breakdown,
        all_tests_pass,
        markers_reward_given,
        code_runs_reward_given,
    )