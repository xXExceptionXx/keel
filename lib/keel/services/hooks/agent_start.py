"""SubagentStart (observer): bind the parked task or plan reference and the ADR state to the agent id, start its
tool counter and clock. Lebenszeichen: the agent_start event carries the Lead's model."""
from keel.services.hooks.base import keel_role
from keel.store import transcripts


def run(hook):
    role = keel_role(hook.text("agent_type"))
    if not role:
        return None
    hook.role = role
    agent_id = hook.agent_id = hook.text("agent_id")
    rt = hook.runtime
    ref = hook.ref = rt.take(role)
    rt.start_agent(agent_id, role, ref)
    hook.try_record("agent_start", {"role": role, "agent_id": agent_id, "ref": ref,
                                    "lead_model": transcripts.last_model(hook.text("transcript_path"))})
    return None
