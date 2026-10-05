"""The checks behind the Claude Code hooks, one module per step (System-ADR 0022). The dispatcher in
keel.interfaces.hooks reads the payload, runs the steps of an event and turns their results into the answer."""
