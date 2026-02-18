"""
Base agent class and agent registry.
Every concrete agent inherits from BaseAgent.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .models import AgentOutput, AgentStatus, ConfidenceLevel, PhaseID

logger = logging.getLogger(__name__)


# ── Agent registry — auto-populated by __init_subclass__ ────────────

_AGENT_REGISTRY: dict[str, type["BaseAgent"]] = {}


def get_agent_class(name: str) -> type["BaseAgent"]:
    return _AGENT_REGISTRY[name]


def list_agents() -> list[str]:
    return sorted(_AGENT_REGISTRY.keys())


# ── Dependency descriptor ──────────────────────────────────────────

@dataclass
class Dependency:
    """Declares that this agent needs output from another agent."""
    agent_name: str
    required: bool = True        # False = nice-to-have, run without if unavailable
    data_keys: list[str] = field(default_factory=list)  # specific keys needed


# ── Base agent ──────────────────────────────────────────────────────

class BaseAgent(ABC):
    """
    Abstract base for every agent in the system.

    Subclasses MUST set the class-level attributes and implement `run()`.
    The orchestrator reads metadata to build the execution DAG.
    """

    # ── class-level metadata (override in subclass) ─────────────
    name: str = ""
    description: str = ""
    phase: PhaseID = PhaseID.PHASE_0_KNOW_YOURSELF
    dependencies: list[Dependency] = []
    output_keys: list[str] = []          # top-level keys this agent writes
    subscribers: list[str] = []          # agents that consume our output

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.name:                     # skip registration for intermediate ABCs
            _AGENT_REGISTRY[cls.name] = cls

    def __init__(self) -> None:
        self.status = AgentStatus.IDLE
        self._run_count = 0

    # ── lifecycle hooks ─────────────────────────────────────────
    def pre_run(self, context: dict[str, Any]) -> None:
        """Optional hook before run(). Override for validation."""
        pass

    @abstractmethod
    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execute the agent's core logic.

        Parameters
        ----------
        context : dict
            Shared state populated by previously-completed agents.
            Keys follow the pattern  ``agent_name.output_key``.

        Returns
        -------
        AgentOutput with this agent's results.
        """
        ...

    def post_run(self, output: AgentOutput, context: dict[str, Any]) -> None:
        """Optional hook after run(). Override for cleanup / metrics."""
        pass

    # ── convenience helpers ─────────────────────────────────────
    def _get_dep(self, context: dict[str, Any], agent_name: str, key: str) -> Any:
        """Safely retrieve a dependency value from context."""
        return context.get(f"{agent_name}.{key}")

    def _make_output(
        self,
        data: dict[str, Any],
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        sources: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> AgentOutput:
        return AgentOutput(
            agent_id=f"{self.name}_{id(self)}",
            agent_name=self.name,
            phase=self.phase,
            confidence=confidence,
            data=data,
            sources=sources or [],
            warnings=warnings or [],
            next_agents=list(self.subscribers),
        )
