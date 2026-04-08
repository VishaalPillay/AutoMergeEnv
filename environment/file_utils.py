import os

def read_file(filepath: str, cwd: str = ".") -> str:
    """Reads a file and prepends line numbers for the agent's observation space."""
    full_path = os.path.join(cwd, filepath)
    if not os.path.exists(full_path):
        return f"Error: File {filepath} not found."
    
    with open(full_path, "r") as f:
        lines = f.readlines()
        
    # Appending 1-based line numbers to help the agent target replace_lines correctly
    return "".join([f"{i+1}: {line}" for i, line in enumerate(lines)])

def replace_lines(filepath: str, start_line: int, end_line: int, new_text: str, cwd: str = ".") -> str:
    """Replaces a specific block of lines in a target file safely."""
    full_path = os.path.join(cwd, filepath)
    if not os.path.exists(full_path):
        return f"Error: File {filepath} not found."

    with open(full_path, "r") as f:
        lines = f.readlines()

    # Convert 1-based line numbers from the LLM to 0-based array indices
    start_idx = start_line - 1
    end_idx = end_line

    if start_idx < 0 or end_idx > len(lines) or start_idx >= end_idx:
        return "Error: Invalid line ranges."

    # Ensure the new string merges cleanly by preserving line breaks
    if new_text and not new_text.endswith("\n"):
        new_text += "\n"

    # Swap the selected slice with the new chunk
    lines[start_idx:end_idx] = [new_text] if new_text else []

    with open(full_path, "w") as f:
        f.writelines(lines)

    return f"Successfully replaced lines {start_line} to {end_line} in {filepath}."