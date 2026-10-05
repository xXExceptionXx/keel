"""Unattended runs (System-ADR 0025): keel's own commands, the project's test commands and safe git run without a
permission prompt; everything else gets no answer and goes through Claude Code's permission flow."""
import json
import subprocess

from harness import BASH, REPO, ContractTest, Result, project, tool_call

R = str(REPO)
ALLOWED = [
    f'python3 "{R}/scripts/due.py" "$PWD" --json',
    'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/frontmatter.py" set .keel/work/tasks/T-1.md status=fertig',
    f'bash {R}/scripts/gate.sh "$PWD" T-1',
    '"${CLAUDE_PLUGIN_ROOT}/bin/keel" doctor --project "$PWD"',
    "npm test --silent",
    "npm test --silent -- tests/a.test.ts",
    "git status --short",
    "git log --all --format=%H -1",
    "git add .keel && git commit -m \"Architecture report 2026-10-05\"",
    "git switch -c feature/x staging",
    "git merge --no-ff --no-commit feature/x",
    "git push -u origin feature/x",
    "git pull --ff-only",
    "date +%F",
    'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/due.py" "$PWD" --json 2>/dev/null',
    'git -C "$PWD" commit -q -m "Route audit findings" -m "Co-Authored-By: Claude <noreply@anthropic.com>"',
    'git commit -m "fix: a; b && c"',
    "git status\ngit log -1",
    "npm test --silent 2>&1 | tail -30",
    f'python3 "{R}/scripts/due.py" "$PWD" --json; echo "EXIT $?"; grep -E "base|model" .keel/config.yaml',
    "cat .keel/config.yaml; ls .keel/work/epics/",
    "sed -n 1,20p .keel/work/tasks/T-tb.md",
    "sed -n '/## Einwand/,$p' .keel/work/tasks/T-tb.md",
    "mkdir -p tests/regression && git mv a.py tests/regression/a.py",
    "git branch -d feature/x",
    "git push origin --delete feature/x",
    "git push -q origin --delete feature/x; git status -sb | head -1",
    "git branch --list 'feature/*'",
    "git -C \"$PWD\" branch -r --merged staging",
    "sed -n '/## Entscheidungen/,/^## [A-Z]/p' .keel/work/tasks/T-tb.md",
    'grep -n -A40 "DuplicateEventInput" src/a.ts | head -90',
]
NOT_ALLOWED = [
    "rm -rf build",
    "npm install left-pad",
    "curl https://example.com",
    "git push origin main",
    "git push --force origin feature/x",
    "git push origin +feature/x",
    "git commit --amend -m x",
    "git branch -D feature/x",
    "git reset --hard HEAD",
    "git clean -fd",
    "git checkout -- src/a.ts",
    "git pull",
    "git -C /tmp status",
    'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/due.py" "$(cat /etc/passwd)"',
    "python3 /tmp/x.py",
    "python3 -c 'print(1)'",
    "git status > /tmp/out.txt",
    "git log; rm -rf build",
    "echo $HOME",
    "echo '$x' $HOME",
    "git commit -F- <<EOF\nx\nEOF",
    "git status &",
    "(git status)",
    "git status\nrm -rf build",
    "git log < /etc/passwd",
    "cat ~/.ssh/id_rsa",
    "cat /etc/passwd",
    "sed -i s/a/b/ src/a.ts",
    "find . -name x -delete",
    "mkdir -p /tmp/x",
    "git push origin --delete main",
    "git branch -d main",
    "git branch feature/neu",
    "git branch -m alt neu",
    "grep -r x /etc",
]


class AllowTest(ContractTest):
    def call(self, p, cmd, role=None):
        return self.hook("allow", tool_call(p, "Bash", {"command": cmd}, agent_type=role), proj=p,
                         env={"CLAUDE_PLUGIN_ROOT": R})

    def decision(self, r):
        return ((r.json or {}).get("hookSpecificOutput") or {}).get("permissionDecision")

    def test_keel_and_project_commands_are_allowed(self):
        p = project()
        for cmd in ALLOWED:
            with self.subTest(cmd=cmd):
                r = self.call(p, cmd)
                self.assertEqual((r.rc, self.decision(r)), (0, "allow"), r)

    def test_everything_else_gets_no_answer(self):
        p = project()
        for cmd in NOT_ALLOWED:
            with self.subTest(cmd=cmd):
                r = self.call(p, cmd)
                self.assertEqual((r.rc, r.json), (0, None), r)

    def test_configured_prefixes_are_allowed(self):
        p = project()
        cfg = p / ".keel" / "config.yaml"
        cfg.write_text(cfg.read_text().replace("befehle: []", "befehle: [pnpm vitest]"))
        self.assertEqual(self.decision(self.call(p, "pnpm vitest run tests/unit/a.test.ts")), "allow")
        self.assertIsNone(self.call(p, "pnpm add left-pad").json)

    def test_only_inside_a_keel_project(self):
        p = project()
        (p / ".keel" / "config.yaml").unlink()
        self.assertIsNone(self.call(p, "git status").json)

    def test_the_guard_and_the_role_gates_still_win(self):
        p = project()
        def event(cmd, role=None):
            payload = tool_call(p, "Bash", {"command": cmd}, agent_type=role)
            proc = subprocess.run([BASH, str(REPO / "bin" / "keel"), "hook", "pre-tool-use"], input=json.dumps(payload),
                                  capture_output=True, text=True, env=self.env({"CLAUDE_PLUGIN_ROOT": R}), cwd=str(p))
            return Result(proc, self.metrics, p)
        self.assertEqual(self.decision(event("git status")), "allow")
        self.assertEqual(self.decision(event("git push -f")), "deny")
        self.seed_agent(p, ref="T-tb", calls=500)
        self.assertEqual(self.decision(event("git status", role="keel:entwickler")), "deny")  # tool budget
