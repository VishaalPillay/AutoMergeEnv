import subprocess
from typing import Tuple, List

def run_command(cmd: List[str], cwd: str = ".") -> Tuple[str, str, int]:
    """
    Executes a shell command and returns a tuple of (stdout, stderr, return_code).
    Using check=False ensures the environment doesn't crash if a git command or test fails.
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False 
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), -1

def check_git_status(cwd: str = ".") -> str:
    stdout, _, _ = run_command(["git", "status", "--short"], cwd=cwd)
    return stdout