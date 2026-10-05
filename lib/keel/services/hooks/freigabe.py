"""PermissionRequest (observer): a tool call needs a permission that no rule and no allow step gives. In an
interactive session the human sees the prompt; in an unattended run Claude Code denies the call, and only the role
that made it learns why. Either way the request is recorded as freigabe_fehlt, so the next briefing can decide it
(System-ADR 0025): the agenda lists the missing permissions with the rule Claude Code suggests. This step never
answers the request."""
import os

from keel.services.hooks.base import keel_role

COMMAND_CHARS = 300


def _suggestions(payload):
    out = []
    for s in payload.get("permission_suggestions") or []:
        if not isinstance(s, dict):
            continue
        for rule in s.get("rules") or []:
            if isinstance(rule, dict) and rule.get("toolName"):
                content = rule.get("ruleContent")
                out.append(f"{rule['toolName']}({content})" if content else rule["toolName"])
    return out[:3]


def run(hook):
    if not os.path.isfile(os.path.join(str(hook.project), ".keel", "config.yaml")):
        return None
    tool_input = hook.get("tool_input") or {}
    what = tool_input.get("command") or tool_input.get("file_path") or tool_input.get("url") or ""
    hook.record("freigabe_fehlt", {
        "role": keel_role(hook.text("agent_type")) or ("lead" if not hook.text("agent_type") else ""),
        "agent_id": hook.text("agent_id"),
        "tool": hook.text("tool_name"),
        "befehl": str(what)[:COMMAND_CHARS],
        "vorschlag": _suggestions(hook.payload),
    })
    return None
