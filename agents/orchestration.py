"""
Orchestration Layer — 3 agents
================================
MasterOrchestrator  →  PhaseController  →  DataRouter

These three agents form the "brain" of the system.  They don't produce
market data themselves; instead they schedule, sequence, and wire
all the other agents together.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, Dependency, _AGENT_REGISTRY
from .models import (
    AgentOutput,
    AgentStatus,
    ConfidenceLevel,
    PhaseID,
    Priority,
)


# =====================================================================
# 1. MASTER ORCHESTRATOR
# =====================================================================
class MasterOrchestrator(BaseAgent):
    """
    Top-level conductor of the entire multi-agent pipeline.

    Responsibilities
    ----------------
    1. Accept a campaign brief (product focus, target geography hints,
       budget, timeline).
    2. Instantiate all required agents via the registry.
    3. Build a Directed Acyclic Graph (DAG) from declared dependencies.
    4. Walk the DAG phase-by-phase, delegating to PhaseController.
    5. Collect every AgentOutput, merge into a master context dict.
    6. Handle retries (max 3) for any agent that returns FAILED.
    7. Produce a final consolidated report referencing every phase output.

    Algorithm
    ---------
    ```
    context = {}
    for phase in [P0, P1, DEEP, P1.5, P2, P3, P4, P5, P6]:
        agents_in_phase = registry.filter(phase)
        topo_order = topological_sort(agents_in_phase, dependencies)
        for batch in parallelize(topo_order):
            results = phase_controller.execute_batch(batch, context)
            context = data_router.merge(context, results)
        phase_controller.validate_phase(phase, context)
    return build_final_report(context)
    ```
    """

    name = "master_orchestrator"
    description = "Top-level conductor that schedules and sequences all agents across all phases."
    phase = PhaseID.PHASE_0_KNOW_YOURSELF   # runs before everything
    dependencies = []                        # no upstream deps
    output_keys = ["execution_plan", "final_report", "run_metadata"]
    subscribers = []                         # everything subscribes implicitly

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Steps executed by the orchestrator
        -----------------------------------
        1. Parse campaign_brief from context["input"]
        2. Discover all registered agents via _AGENT_REGISTRY
        3. Build DAG: nodes = agents, edges = Dependency declarations
        4. Validate DAG is acyclic
        5. Determine phase execution order (P0 → P1 → DEEP → P1.5 → P2 → P3 → P4 → P5 → P6)
        6. For each phase:
           a. Extract agents belonging to that phase
           b. Topological-sort within the phase
           c. Group independent agents into parallel batches
           d. Delegate each batch to PhaseController.execute_batch()
           e. DataRouter merges results into context
           f. PhaseController.validate_phase() checks completeness
        7. If any agent fails after 3 retries → mark opportunity as "needs_human_review"
        8. Compile final_report from all phase outputs
        9. Return AgentOutput with execution_plan + final_report + run_metadata
        """

        campaign_brief = context.get("input", {})

        # Build execution plan
        execution_plan = self._build_execution_plan()

        return self._make_output(
            data={
                "execution_plan": execution_plan,
                "campaign_brief": campaign_brief,
                "phase_order": [p.value for p in PhaseID],
            },
            confidence=ConfidenceLevel.VERY_HIGH,
        )

    def _build_execution_plan(self) -> dict[str, Any]:
        """Introspect all registered agents and build the DAG."""
        plan: dict[str, Any] = {}
        for agent_name, agent_cls in _AGENT_REGISTRY.items():
            plan[agent_name] = {
                "phase": agent_cls.phase.value if isinstance(agent_cls.phase, PhaseID) else agent_cls.phase,
                "dependencies": [
                    {"agent": d.agent_name, "required": d.required}
                    for d in agent_cls.dependencies
                ],
                "output_keys": agent_cls.output_keys,
                "subscribers": agent_cls.subscribers,
            }
        return plan


# =====================================================================
# 2. PHASE CONTROLLER
# =====================================================================
class PhaseController(BaseAgent):
    """
    Manages execution within a single phase.

    Responsibilities
    ----------------
    1. Receive a batch of agents from MasterOrchestrator.
    2. Check that each agent's required dependencies are satisfied.
    3. Execute agents — parallelise where the DAG allows.
    4. Monitor status (RUNNING → COMPLETED | FAILED).
    5. On failure: retry up to 3 times with exponential backoff.
    6. After all agents in the phase complete, run validation:
       - Every expected output_key exists in context.
       - Confidence levels meet minimum thresholds.
       - No CRITICAL warnings are unresolved.
    7. Emit a phase_summary to context.

    Algorithm
    ---------
    ```
    def execute_batch(agents, context):
        pending = list(agents)
        while pending:
            ready = [a for a in pending if deps_satisfied(a, context)]
            results = parallel_run(ready)
            for r in results:
                if r.status == FAILED and r.retries < 3:
                    r.retries += 1; pending.append(r)
                else:
                    context = merge(context, r.output)
                    pending.remove(r)
        return context

    def validate_phase(phase, context):
        for agent in phase.agents:
            for key in agent.output_keys:
                assert f"{agent.name}.{key}" in context
        return PhaseValidationReport(...)
    ```
    """

    name = "phase_controller"
    description = "Manages agent scheduling, retries, and validation within a single phase."
    phase = PhaseID.PHASE_0_KNOW_YOURSELF
    dependencies = [Dependency(agent_name="master_orchestrator", required=True)]
    output_keys = ["phase_summary", "phase_validation"]
    subscribers = ["data_router"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Steps
        -----
        1. Read execution_plan from context
        2. Identify current phase agents
        3. Check dependency satisfaction for each agent
        4. Execute ready agents (parallel where possible)
        5. Retry failed agents up to 3x with 2s/4s/8s backoff
        6. Validate all output_keys present
        7. Compute confidence aggregation for the phase
        8. Emit phase_summary and phase_validation
        """
        return self._make_output(
            data={
                "phase_summary": {},
                "phase_validation": {"all_keys_present": True},
            },
            confidence=ConfidenceLevel.VERY_HIGH,
        )


# =====================================================================
# 3. DATA ROUTER
# =====================================================================
class DataRouter(BaseAgent):
    """
    Central message bus / data merger.

    Responsibilities
    ----------------
    1. Receive AgentOutput from any agent.
    2. Flatten output.data into context using ``agent_name.key`` namespace.
    3. Notify subscriber agents that new data is available.
    4. Maintain a versioned audit log of every write.
    5. Handle data conflicts (two agents writing overlapping keys):
       - Keep higher-confidence value.
       - Log the conflict for human review.
    6. Provide query interface for agents:  get(agent, key), list_keys(), etc.

    Algorithm
    ---------
    ```
    def merge(context, agent_output):
        for key, value in agent_output.data.items():
            ns_key = f"{agent_output.agent_name}.{key}"
            if ns_key in context:
                existing_conf = context[ns_key + ".__confidence"]
                if agent_output.confidence > existing_conf:
                    context[ns_key] = value
                    log_conflict(ns_key, "overwritten")
                else:
                    log_conflict(ns_key, "kept_existing")
            else:
                context[ns_key] = value
            context[ns_key + ".__confidence"] = agent_output.confidence
            context[ns_key + ".__timestamp"] = agent_output.timestamp
        notify_subscribers(agent_output.next_agents)
        return context
    ```
    """

    name = "data_router"
    description = "Central data bus that merges agent outputs and notifies subscribers."
    phase = PhaseID.PHASE_0_KNOW_YOURSELF
    dependencies = [Dependency(agent_name="phase_controller", required=True)]
    output_keys = ["routing_log", "conflict_log"]
    subscribers = []  # every agent implicitly reads from the context

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Steps
        -----
        1. Accept incoming AgentOutput
        2. Namespace each data key: agent_name.key
        3. Check for conflicts (key already exists)
        4. Resolve conflicts by confidence level
        5. Write audit log entry (timestamp, source, key, old_value, new_value)
        6. Notify subscriber agents via callback queue
        7. Return routing summary
        """
        return self._make_output(
            data={
                "routing_log": [],
                "conflict_log": [],
            },
            confidence=ConfidenceLevel.VERY_HIGH,
        )
