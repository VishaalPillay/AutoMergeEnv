#!/bin/bash

Task 1: Easy
cd tasks/task_1_easy
git init
git branch -M main
echo -e "def calculate():\n    return 10" > utils.py
echo -e "from utils import calculate\ndef test_calculate():\n    assert calculate() > 0" > test_utils.py
git add .
git commit -m "Initial commit"

git checkout -b feature-a
echo -e "import math\n\ndef calculate():\n    return math.pi" > utils.py
git commit -am "Feature A changes"

git checkout main
echo -e "import os\n\ndef calculate():\n    return 100" > utils.py
git commit -am "Developer B changes"
git merge feature-a --no-edit || true
cd ../..

Task 2: Medium
cd tasks/task_2_medium
git init
git branch -M main
echo -e "def multiply(a, b):\n    return a * b" > math_ops.py
echo -e "from math_ops import multiply\ndef run():\n    return multiply(2, 3)" > app.py
echo -e "from app import run\ndef test_run():\n    assert run() == 6" > test_app.py
git add .
git commit -m "Base commit"

git checkout -b feature-a
echo -e "def multiply(a, b, multiplier=1):\n    return (a * b) * multiplier" > math_ops.py
git commit -am "Changed signature in math_ops.py"

git checkout main
echo -e "from math_ops import multiply\ndef run():\n    return multiply(2, 3)\n\ndef run_more():\n    return multiply(5, 5)" > app.py
echo -e "from app import run, run_more\ndef test_run():\n    assert run() == 6\n    assert run_more() == 25" > test_app.py
git commit -am "Added run_more using old signature"
git merge feature-a --no-edit || true
cd ../..

Task 3: Hard
cd tasks/task_3_hard
git init
git branch -M main
echo -e "schema = {'user_id': 12345}" > db.py
echo -e "from db import schema\ndef get_user():\n    return schema.get('user_id')" > query.py
echo -e "from query import get_user\ndef test_get_user():\n    assert get_user() == 12345" > test_logic.py
git add .
git commit -m "Base schema setup"

git checkout -b feature-a
echo -e "schema = {'account_id': 12345}" > db.py
echo -e "from db import schema\ndef get_user():\n    return schema.get('account_id')" > query.py
git commit -am "Refactored user_id to account_id"

git checkout main
echo -e "from db import schema\ndef get_admin():\n    return schema.get('user_id', 'admin')" > admin_query.py
echo -e "from query import get_user\nfrom admin_query import get_admin\ndef test_logic():\n    assert get_user() == 12345\n    assert get_admin() == 'admin'" > test_logic.py
git add .
git commit -m "Added admin query"
git merge feature-a --no-edit || true
cd ../..