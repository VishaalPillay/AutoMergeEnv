from environment.git_utils import run_command

def check_for_conflict_markers(cwd: str) -> bool:
    """Checks if standard Git conflict markers remain in the directory."""
    stdout, _, _ = run_command(["git", "grep", "<<<<<<<"], cwd=cwd)
    return bool(stdout.strip())

def calculate_reward(cwd: str, action_failed: bool = False) -> float:
    """Calculates the progressive reward based on the repository state."""
    if action_failed:
        # Penalizes blind guessing or bad API calls
        return -0.1 

    reward = 0.0
    
    # Check if conflict markers are resolved
    has_markers = check_for_conflict_markers(cwd)
    if not has_markers:
        reward += 0.2 

    # Run the integration test suite
    stdout, stderr, returncode = run_command(["pytest"], cwd=cwd)

    # Return code 0 = pass, 1 = test failures. Anything higher usually means a fatal syntax crash.
    if returncode in (0, 1):
        reward += 0.4 

    # All tests pass successfully
    if returncode == 0:
        reward += 0.4 

    return min(reward, 1.0)