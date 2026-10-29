#!/usr/bin/env python3
"""PreToolUse hook: blocks commits/pushes on main and badly named branches (see CLAUDE.md)."""
import json
import re
import shlex
import subprocess
import sys

BRANCH_RE = re.compile(r"^(feature|fix|hotfix|docs|chore|refactor)/[a-z0-9][a-z0-9._-]*$")
CREATE_FLAGS = {"checkout": {"-b", "-B"}, "switch": {"-c", "-C", "--create", "--force-create"}, "worktree": {"-b", "-B"}}


def current_branch(cwd):
    out = subprocess.run(["git", "branch", "--show-current"], cwd=cwd, capture_output=True, text=True)
    return out.stdout.strip()


def git_args(tokens):
    """Arguments after `git` and its global options (-C dir, -c k=v...), or None if not a git call."""
    if not tokens or tokens[0] != "git":
        return None
    i = 1
    while i < len(tokens) and tokens[i].startswith("-"):
        i += 2 if tokens[i] in ("-C", "-c") else 1
    return tokens[i:]


def targets_main(refspec):
    return refspec.lstrip("+").split(":")[-1] in ("main", "refs/heads/main")


def is_branch(name, cwd):
    return subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{name}"],
                          cwd=cwd, capture_output=True).returncode == 0


def check(command, cwd):
    branch = current_branch(cwd)
    # shortcut: splits on shell operators naively (quoted `&&` breaks it), enough for git one-liners
    for segment in re.split(r"&&|\|\||[;|\n]", command):
        try:
            args = git_args(shlex.split(segment))
        except ValueError:
            continue
        if not args:
            continue
        sub, rest = args[0], args[1:]

        new = next((rest[i + 1] for i, a in enumerate(rest[:-1]) if a in CREATE_FLAGS.get(sub, ())), None)
        if sub == "branch" and rest and not rest[0].startswith("-"):
            new = rest[0]
        if new is not None:
            if not BRANCH_RE.match(new):
                return f"Nom de branche refusé : '{new}'. Format : <feature|fix|hotfix|docs|chore|refactor>/<kebab-case>."
            branch = new
        elif sub in ("checkout", "switch") and rest and is_branch(rest[-1], cwd):
            branch = rest[-1]

        if sub == "commit" and branch == "main":
            return "Commit interdit sur main. Crée une branche (feature/, fix/...) et passe par une PR."
        if sub == "push":
            refspecs = [a for a in rest if not a.startswith("-")][1:]
            if any(targets_main(r) for r in refspecs) or (not refspecs and branch == "main") \
                    or ("HEAD" in refspecs and branch == "main"):
                return "Push interdit sur main. Pousse ta branche et ouvre une PR."
    return None


def main():
    data = json.load(sys.stdin)
    reason = check(data.get("tool_input", {}).get("command", ""), data.get("cwd"))
    if reason:
        print(reason, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
