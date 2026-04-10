#!/bin/bash
set -e

git config --global user.email "env@automerge.ai"
git config --global user.name "AutoMergeEnv"
git config --global init.defaultBranch main

# ─────────────────────────────────────────────
# TASK 1 — EASY: Textual conflict in one file
# ─────────────────────────────────────────────
echo "=== Setting up Task 1: Easy (Textual Conflict) ==="
rm -rf tasks/task_1_easy && mkdir -p tasks/task_1_easy
cd tasks/task_1_easy
git init

cat > utils.py << 'EOF'
def shared_helper():
    return "shared"
EOF

cat > test_utils.py << 'EOF'
from utils import shared_helper, helper_a, helper_b

def test_shared():
    assert shared_helper() == "shared"

def test_a():
    assert helper_a() == "a"

def test_b():
    assert helper_b() == "b"
EOF

git add .
git commit -m "Base: shared_helper and tests"

git checkout -b feature-a
cat > utils.py << 'EOF'
def shared_helper():
    return "shared"

def helper_a():
    return "a"
EOF
git commit -am "Dev A: adds helper_a"

git checkout main
cat > utils.py << 'EOF'
def shared_helper():
    return "shared"

def helper_b():
    return "b"
EOF
git commit -am "Dev B: adds helper_b"

echo "Task 1 created."
cd ../..

# ─────────────────────────────────────────────
# TASK 2 — MEDIUM: Cross-file signature conflict
# ─────────────────────────────────────────────
echo "=== Setting up Task 2: Medium (Cross-File Signature Conflict) ==="
rm -rf tasks/task_2_medium && mkdir -p tasks/task_2_medium
cd tasks/task_2_medium
git init

cat > math_ops.py << 'EOF'
def multiply(a, b):
    return a * b
EOF

cat > app.py << 'EOF'
from math_ops import multiply

def compute(x, y):
    return multiply(x, y)
EOF

cat > test_app.py << 'EOF'
from app import compute
from math_ops import multiply

def test_multiply_basic():
    assert multiply(3, 4) == 12

def test_compute():
    assert compute(2, 5) == 10

def test_multiply_defaults():
    assert multiply(3, 4, scale=1) == 12
EOF

git add .
git commit -m "Base: math_ops and app"

git checkout -b feature-a
cat > math_ops.py << 'EOF'
def multiply(a, b, scale: float = 1.0):
    return a * b * scale
EOF
git commit -am "Dev A: adds scale parameter to multiply"

git checkout main
cat > app.py << 'EOF'
from math_ops import multiply

def compute(x, y):
    return multiply(x, y)

def compute_scaled(x, y):
    return multiply(x, y)
EOF
git commit -am "Dev B: adds compute_scaled using multiply (old signature)"

echo "Task 2 created."
cd ../..

# ─────────────────────────────────────────────
# TASK 3 — HARD: Semantic conflict — NO markers
# ─────────────────────────────────────────────
echo "=== Setting up Task 3: Hard (Semantic Conflict — Clean Merge, No Markers) ==="
rm -rf tasks/task_3_hard && mkdir -p tasks/task_3_hard
cd tasks/task_3_hard
git init

# --- Base commit: db.py and query.py use user_id ---
cat > db.py << 'EOF'
schema = {"user_id": 12345}
EOF

cat > query.py << 'EOF'
from db import schema

def get_user():
    return schema.get("user_id")
EOF

cat > test_logic.py << 'EOF'
from query import get_user

def test_get_user():
    assert get_user() == 12345
EOF

git add .
git commit -m "Base: schema with user_id, query"

# --- feature-a: rename user_id -> account_id in db.py and query.py ONLY ---
git checkout -b feature-a

cat > db.py << 'EOF'
schema = {"account_id": 12345}
EOF

cat > query.py << 'EOF'
from db import schema

def get_user():
    return schema.get("account_id")
EOF

git commit -am "Refactored user_id to account_id in db and query"

# --- main: add report.py, admin_query.py — all use OLD user_id ---
git checkout main

cat > report.py << 'EOF'
from db import schema

def generate_report():
    uid = schema.get("user_id")
    return f"Report for user {uid}"
EOF

cat > admin_query.py << 'EOF'
from db import schema

def get_admin():
    return schema.get("user_id", "admin")
EOF

cat > test_logic.py << 'EOF'
from query import get_user
from admin_query import get_admin
from report import generate_report

def test_get_user():
    assert get_user() == 12345

def test_get_admin():
    assert get_admin() == 12345

def test_generate_report():
    assert "12345" in generate_report()
EOF

git add .
git commit -m "Added report.py and admin_query.py using user_id"

# CRITICAL: The merge is done by env.reset(), NOT here.
# feature-a only touches db.py and query.py.
# main only adds report.py, admin_query.py, and updates test_logic.py.
# These are disjoint file sets → git merge will be CLEAN (no markers).
# But tests will fail because report.py and admin_query.py use "user_id"
# while db.py (from feature-a) now has "account_id".

echo "Task 3 created."
cd ../..

# ─────────────────────────────────────────────────────────────
# TASK 4 — ADVERSARIAL: Both conflicting versions are wrong
# ─────────────────────────────────────────────────────────────
echo "=== Setting up Task 4: Adversarial (Both Sides Wrong) ==="
rm -rf tasks/task_4_adversarial && mkdir -p tasks/task_4_adversarial
cd tasks/task_4_adversarial
git init

# --- Base commit: correct divide() with IEEE 754 float and zero check ---
cat > calculator.py << 'EOF'
def divide(a, b):
    """IEEE 754 float division. Raises ZeroDivisionError when b == 0."""
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return float(a) / float(b)
EOF

cat > test_calculator.py << 'EOF'
import pytest
from calculator import divide

def test_basic_division():
    assert divide(10, 2) == 5.0

def test_float_division():
    assert divide(1, 2) == 0.5

def test_negative_division():
    assert divide(-10, 2) == -5.0

def test_zero_numerator():
    assert divide(0, 5) == 0.0

def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_large_numbers():
    assert divide(1000000, 3) == pytest.approx(333333.333333, rel=1e-4)
EOF

git add .
git commit -m "Base: divide with IEEE 754 float and ZeroDivisionError"

# --- feature-a: changes to integer division (WRONG) ---
git checkout -b feature-a

cat > calculator.py << 'EOF'
def divide(a, b):
    """Integer division for performance."""
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a // b
EOF

git commit -am "Dev A: switched to integer division for performance"

# --- main: removes zero check (ALSO WRONG) ---
git checkout main

cat > calculator.py << 'EOF'
def divide(a, b):
    """Fast float division without safety checks."""
    return float(a) / float(b)
EOF

git commit -am "Dev B: removed zero check for speed"

echo "Task 4 created."
cd ../..


echo ""
echo "=================================================="
echo "  All 4 task repos created successfully."
echo "=================================================="