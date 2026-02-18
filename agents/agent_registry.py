"""
Agent Registry & Data Flow Map
================================
Imports all agents to trigger registration, then provides
introspection utilities to visualize the DAG.
"""

from __future__ import annotations

# ── Import all agent modules to trigger __init_subclass__ registration ──
from . import orchestration          # noqa: F401  (3 agents)
from . import phase0_know_yourself   # noqa: F401  (3 agents)
from . import phase1_region_discovery  # noqa: F401  (3 agents)
from . import deep_research          # noqa: F401  (4 agents)
from . import phase1_5_company_discovery  # noqa: F401  (3 agents)
from . import phase2_company_intelligence  # noqa: F401  (5 agents)
from . import phase3_gap_analysis    # noqa: F401  (3 agents)
from . import phase4_competitor_market  # noqa: F401  (4 agents)
from . import phase5_communication   # noqa: F401  (4 agents)
from . import phase6_sales           # noqa: F401  (4 agents)

from .base import _AGENT_REGISTRY, list_agents, get_agent_class
from .models import PhaseID


def print_agent_summary() -> None:
    """Print a summary of all registered agents grouped by phase."""
    agents_by_phase: dict[str, list[str]] = {}
    for name, cls in _AGENT_REGISTRY.items():
        phase = cls.phase.value if isinstance(cls.phase, PhaseID) else str(cls.phase)
        agents_by_phase.setdefault(phase, []).append(name)

    phase_labels = {
        "phase_0": "Phase 0 — Know Yourself",
        "phase_1": "Phase 1 — Region Discovery",
        "deep_research": "Deep Research — Sector & Market",
        "phase_1_5": "Phase 1.5 — Company Discovery",
        "phase_2": "Phase 2 — Company Intelligence",
        "phase_3": "Phase 3 — Gap Analysis",
        "phase_4": "Phase 4 — Competitor & Market",
        "phase_5": "Phase 5 — Communication & Network",
        "phase_6": "Phase 6 — Sales & Proposal",
    }

    total = 0
    for phase_id in PhaseID:
        phase_key = phase_id.value
        agents = agents_by_phase.get(phase_key, [])
        label = phase_labels.get(phase_key, phase_key)
        print(f"\n{'='*60}")
        print(f"  {label}  ({len(agents)} agents)")
        print(f"{'='*60}")
        for a in sorted(agents):
            cls = _AGENT_REGISTRY[a]
            deps = [d.agent_name for d in cls.dependencies]
            subs = cls.subscribers
            print(f"  [{a}]")
            print(f"    → {cls.description}")
            print(f"    ← depends on: {deps or '(none)'}")
            print(f"    → feeds into: {subs or '(terminal)'}")
            print(f"    📤 outputs: {cls.output_keys}")
            print()
        total += len(agents)

    print(f"\n{'='*60}")
    print(f"  TOTAL: {total} agents registered")
    print(f"{'='*60}")


def print_data_flow_dag() -> None:
    """Print the full DAG as an adjacency list."""
    print("\n" + "="*60)
    print("  DATA FLOW — DIRECTED ACYCLIC GRAPH")
    print("="*60)
    print()

    for name in sorted(_AGENT_REGISTRY.keys()):
        cls = _AGENT_REGISTRY[name]
        subs = cls.subscribers
        if subs:
            for s in subs:
                for key in cls.output_keys:
                    print(f"  {name}.{key}  ──►  {s}")
        else:
            print(f"  {name}  ──►  (TERMINAL OUTPUT)")
        print()


def validate_dag() -> list[str]:
    """
    Validate the agent DAG for consistency:
    1. Every dependency reference points to a real agent.
    2. Every subscriber reference points to a real agent.
    3. No circular dependencies.
    Returns list of error messages (empty = valid).
    """
    errors: list[str] = []
    all_names = set(_AGENT_REGISTRY.keys())

    for name, cls in _AGENT_REGISTRY.items():
        # Check dependencies
        for dep in cls.dependencies:
            if dep.agent_name not in all_names:
                errors.append(
                    f"[{name}] depends on '{dep.agent_name}' which does not exist"
                )

        # Check subscribers
        for sub in cls.subscribers:
            if sub not in all_names:
                errors.append(
                    f"[{name}] lists subscriber '{sub}' which does not exist"
                )

    # Check for cycles via DFS
    visited: set[str] = set()
    in_stack: set[str] = set()

    def _dfs(node: str) -> bool:
        if node in in_stack:
            return True  # cycle found
        if node in visited:
            return False
        visited.add(node)
        in_stack.add(node)
        for sub in _AGENT_REGISTRY.get(node, type("_", (), {"subscribers": []})).subscribers:
            if sub in all_names and _dfs(sub):
                errors.append(f"Cycle detected involving '{node}' → '{sub}'")
                return True
        in_stack.discard(node)
        return False

    for name in all_names:
        _dfs(name)

    return errors


# ── CLI entry point ─────────────────────────────────────────────────

if __name__ == "__main__":
    print_agent_summary()
    print()
    errors = validate_dag()
    if errors:
        print("\n⚠️  DAG VALIDATION ERRORS:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("\n✅  DAG is valid — no broken references, no cycles.")
    print()
    print_data_flow_dag()
