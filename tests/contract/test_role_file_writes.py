"""keel roles change files with Edit and Write, not through Bash (System-ADR 0027); the Lead is not affected."""
from harness import ContractTest, project, tool_call

REFUSED = [
    "cat >> .keel/work/plans/p.md <<'EOF'\n## Anmerkung\nx\nEOF",
    "python3 - <<'EOF'\np='a.ts'\nEOF",
    "python3 -c \"open('a.ts','w').write('x')\"",
    "echo x > src/a.ts",
    "printf 'x' >> notes.md",
    "pnpm verify | tee out.log",
    "sed -i '' s/a/b/ src/a.ts",
    "cd src && perl -pi -e s/a/b/ a.ts",
    "node -e \"require('fs').writeFileSync('a','b')\"",
]
PASSED = [
    "pnpm verify 2>&1 | tail -30",
    "pnpm test > /dev/null 2>&1",
    'git commit -m "fix: a > b and c >> d"',
    "grep -n '>' src/a.ts",
    "sed -n 1,20p src/a.ts",
    "python3 scripts/x.py",
]


class RoleFileWriteTest(ContractTest):
    def call(self, p, cmd, role="keel:entwickler"):
        return self.hook("tool-gate", tool_call(p, "Bash", {"command": cmd}, agent_type=role), proj=p)

    def test_roles_are_sent_to_the_file_tools(self):
        p = project()
        self.seed_agent(p, ref="T-tb")
        for cmd in REFUSED:
            with self.subTest(cmd=cmd):
                r = self.call(p, cmd)
                self.assertBlocked(r)
                self.assertIn("Edit oder Write", r.json["hookSpecificOutput"]["permissionDecisionReason"])

    def test_other_commands_pass(self):
        p = project()
        self.seed_agent(p, ref="T-tb", calls=0)
        for cmd in PASSED:
            with self.subTest(cmd=cmd):
                self.assertPassed(self.call(p, cmd))

    def test_the_lead_is_not_affected(self):
        p = project()
        self.assertPassed(self.call(p, REFUSED[0], role=None))
