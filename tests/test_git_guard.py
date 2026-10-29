import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).parents[1] / ".claude" / "hooks" / "git_guard.py"


@pytest.fixture
def repo(tmp_path):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-b", "main")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "--allow-empty", "-m", "init")
    git("branch", "fix/existing")
    return tmp_path


def blocked(command, cwd):
    payload = json.dumps({"tool_input": {"command": command}, "cwd": str(cwd)})
    return subprocess.run([sys.executable, str(HOOK)], input=payload, text=True).returncode == 2


@pytest.mark.parametrize("command", [
    "git commit -m 'x'",
    "git add . && git commit -m x",
    "git -C . commit -m x",
    "git push",
    "git push origin",
    "git push origin main",
    "git push -f origin HEAD:main",
    "git push origin +fix/a:refs/heads/main",
    "git checkout -b wip",
    "git switch -c Feature/Thing",
    "git branch my-branch",
    "git switch fix/existing && git push origin main",
    "git switch fix/existing && git push --all",
    "git push --mirror origin",
])
def test_blocks(repo, command):
    assert blocked(command, repo)


@pytest.mark.parametrize("command", [
    "git status",
    "git pull --ff-only",
    "git switch -c fix/thing && git commit -m x",
    "git checkout -b feature/new-ui && git push -u origin feature/new-ui",
    "git switch fix/existing && git commit -m x && git push",
    "git branch -d fix/existing",
    "ls && echo main",
])
def test_allows(repo, command):
    assert not blocked(command, repo)
