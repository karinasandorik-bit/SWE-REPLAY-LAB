"""OWL capability bootstrap planner: bounded, auditable and fail-closed.
This module never creates credentials, grants itself permissions, or executes payments.
"""
from dataclasses import dataclass, asdict
import json

@dataclass(frozen=True)
class Capability:
    name: str
    resource: str
    scope: str
    expires_at: int
    approved: bool = False

@dataclass(frozen=True)
class Task:
    name: str
    required_capability: str
    resource: str
    scope: str

def plan(task: Task, grants: list[Capability], now: int) -> dict:
    matched = [g for g in grants if g.name == task.required_capability
               and g.resource == task.resource and g.scope == task.scope
               and g.expires_at > now and g.approved]
    if matched:
        return {"task": task.name, "decision": "EXECUTE_ALLOWED",
                "grant": asdict(matched[0])}
    return {"task": task.name, "decision": "NEEDS_AUTHORIZATION",
            "request": {"capability": task.required_capability,
                        "resource": task.resource, "scope": task.scope},
            "next_step": "Use an existing connector or ask owner to approve a scoped grant"}

if __name__ == "__main__":
    tasks = [
        Task("postgres-recovery", "database-test-write", "owl_ablation_004", "isolated-schema"),
        Task("github-ci", "repository-workflow", "SWE-REPLAY-LAB", "manual-dispatch"),
    ]
    print(json.dumps([plan(t, [], 0) for t in tasks], indent=2))
