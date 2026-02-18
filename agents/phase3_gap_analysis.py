"""
Phase 3 — Gap Analysis  (3 agents)
====================================
NeedAnalyzer  →  GapDetector  →  OpportunityScorer

These agents answer: "What does this company NEED, where do WE fit,
and how BIG is the opportunity?"
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, Dependency
from .models import (
    AgentOutput,
    CompanyNeed,
    ConfidenceLevel,
    GapEntry,
    PhaseID,
    Priority,
    ScoredOpportunity,
)


# =====================================================================
# 19. NEED ANALYZER
# =====================================================================
class NeedAnalyzer(BaseAgent):
    """
    Analyzes what each target company actually NEEDS right now.

    Combines company-specific data with sector/market problems to
    build a needs profile.

    Inputs
    ------
    - company_profiler.company_profiles
    - tech_stack_analyzer.tech_stacks
    - market_problem_analyzer.market_problems
    - sector_deep_researcher.sector_profiles

    Outputs
    -------
    - company_needs : dict[company_id, list[CompanyNeed]]

    Algorithm
    ---------
    1. For each profiled company:

       a. CAPACITY NEEDS:
          - Is the company growing? (revenue trend, hiring signals)
          - Are they expanding to new markets? (news)
          - Current capacity utilization estimate.
          - If growing + high utilization → NEED: additional capacity.
          - Urgency: 90 if expansion announced, 60 if growing steadily.

       b. QUALITY / COMPLIANCE NEEDS:
          - New regulations coming? (from sector_profiles.regulatory_drivers)
          - Current certifications vs. required certifications.
          - If gap exists → NEED: compliance upgrade.
          - Urgency: 95 if regulatory deadline approaching, 50 if proactive.

       c. EFFICIENCY NEEDS:
          - Current automation_level vs. industry average.
          - Machine ages → old machines = inefficient.
          - Labor cost trends in their country.
          - If manual + high labor costs → NEED: automation.
          - Urgency: 70 if labor shortage acute, 40 if cost optimization.

       d. PRODUCT INNOVATION NEEDS:
          - Are they launching new products?
          - Are consumer trends driving packaging changes?
            (sustainability, convenience, smaller portions)
          - NEED: new packaging capabilities.
          - Urgency: 80 if competitor already offering, 50 if trend emerging.

       e. REPLACEMENT NEEDS:
          - Machines > 10 years old → approaching end of life.
          - Machines > 15 years old → urgent replacement.
          - Discontinued models (spare parts unavailable).
          - NEED: equipment replacement.
          - Urgency: 85 if machine > 15 years, 60 if > 10 years.

       f. SUSTAINABILITY NEEDS:
          - EU PPWR compliance deadline.
          - Customer demands for sustainable packaging.
          - Current materials vs. required sustainable materials.
          - NEED: sustainable packaging equipment.
          - Urgency: 80 if in EU (regulation), 50 if voluntary.

    2. For each need, gather evidence:
       - Where did we find this signal?
       - How confident are we?
    3. Return dict[company_id → list[CompanyNeed]].

    Quality gates
    -------------
    - Every A-tier company must have ≥ 2 identified needs.
    - Each need must have ≥ 1 evidence item.
    - Companies with 0 needs → probably wrong fit, flag for review.

    Subscribers
    -----------
    → GapDetector
    """

    name = "need_analyzer"
    description = "Identifies specific equipment/capability needs for each target company."
    phase = PhaseID.PHASE_3_GAP_ANALYSIS
    dependencies = [
        Dependency(agent_name="company_profiler", required=True, data_keys=["company_profiles"]),
        Dependency(agent_name="tech_stack_analyzer", required=False, data_keys=["tech_stacks"]),
        Dependency(agent_name="market_problem_analyzer", required=True, data_keys=["market_problems"]),
        Dependency(agent_name="sector_deep_researcher", required=True, data_keys=["sector_profiles"]),
    ]
    output_keys = ["company_needs"]
    subscribers = ["gap_detector"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load company_profiles, tech_stacks, market_problems, sector_profiles
        2. For each company:
           a. Assess capacity needs (growth signals)
           b. Assess compliance needs (regulation gaps)
           c. Assess efficiency needs (automation level, machine age)
           d. Assess innovation needs (new products, trends)
           e. Assess replacement needs (old equipment)
           f. Assess sustainability needs (regulation, demand)
           g. Score urgency for each need
           h. Attach evidence
        3. Validate quality gates
        4. Return AgentOutput with company_needs
        """

        company_profiles = self._get_dep(context, "company_profiler", "company_profiles") or []
        tech_stacks = self._get_dep(context, "tech_stack_analyzer", "tech_stacks") or {}
        market_problems = self._get_dep(context, "market_problem_analyzer", "market_problems") or []
        company_needs: dict[str, list[dict]] = {}

        return self._make_output(
            data={"company_needs": company_needs},
            confidence=ConfidenceLevel.MEDIUM,
        )


# =====================================================================
# 20. GAP DETECTOR
# =====================================================================
class GapDetector(BaseAgent):
    """
    Matches company needs against AGE capabilities to find gaps
    where AGE is uniquely positioned to help.

    Inputs
    ------
    - need_analyzer.company_needs
    - capability_mapper.capabilities
    - usp_extractor.usps

    Outputs
    -------
    - gap_map : dict[company_id, list[GapEntry]]

    Algorithm
    ---------
    1. For each company, for each need:
       a. Search capabilities list for matches:
          - Semantic matching: need.category → capability.category
            · "capacity" → "high-speed production", "scalable design"
            · "compliance" → "FDA-compliant", "CE-marked", "hygienic design"
            · "efficiency" → "automation", "reduced changeover time"
            · "replacement" → any matching product category
          - Feature matching: need.description keywords → capability features.
       b. For each matching capability:
          - Compute match_quality (0-100):
            · 90-100: Perfect match, exactly what they need.
            · 70-89:  Strong match with minor customization.
            · 50-69:  Partial match, significant customization needed.
            · 30-49:  Weak match, only partially addresses need.
            · <30:    Stretch, not a natural fit.
          - Describe required_customization (if any).
       c. If need has no matching capability → skip (no gap for us).
       d. Create GapEntry for each match.
    2. For each company, sort gaps by match_quality descending.
    3. Cross-reference with USPs:
       - If a gap aligns with a USP → boost match_quality by 10%.
       - This is where we TRULY differentiate.
    4. Return dict[company_id → list[GapEntry]].

    Quality gates
    -------------
    - At least 50% of A-tier companies have ≥ 1 gap with match_quality > 70.
    - Companies with 0 gaps → re-evaluate ranking (should they be here?).

    Subscribers
    -----------
    → OpportunityScorer, MarketPositioner, OutreachComposer, ProposalGenerator
    """

    name = "gap_detector"
    description = "Matches company needs vs AGE capabilities to find opportunity gaps."
    phase = PhaseID.PHASE_3_GAP_ANALYSIS
    dependencies = [
        Dependency(agent_name="need_analyzer", required=True, data_keys=["company_needs"]),
        Dependency(agent_name="capability_mapper", required=True, data_keys=["capabilities"]),
        Dependency(agent_name="usp_extractor", required=True, data_keys=["usps"]),
    ]
    output_keys = ["gap_map"]
    subscribers = ["opportunity_scorer", "market_positioner", "outreach_composer", "proposal_generator"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load company_needs, capabilities, usps
        2. For each company, for each need:
           a. Find matching capabilities (semantic + feature matching)
           b. Score match_quality
           c. Note required_customization
           d. Boost if aligned with USP
        3. Sort gaps per company by match_quality
        4. Validate quality gates
        5. Return AgentOutput with gap_map
        """

        company_needs = self._get_dep(context, "need_analyzer", "company_needs") or {}
        capabilities = self._get_dep(context, "capability_mapper", "capabilities") or []
        usps = self._get_dep(context, "usp_extractor", "usps") or []
        gap_map: dict[str, list[dict]] = {}

        return self._make_output(
            data={"gap_map": gap_map},
            confidence=ConfidenceLevel.MEDIUM,
        )


# =====================================================================
# 21. OPPORTUNITY SCORER
# =====================================================================
class OpportunityScorer(BaseAgent):
    """
    Scores and ranks every company opportunity for final prioritization.

    Inputs
    ------
    - gap_detector.gap_map
    - financial_analyzer.financial_snapshots
    - market_problem_analyzer.market_problems
    - company_ranker.ranked_companies  (for base fit_score)

    Outputs
    -------
    - scored_opportunities : list[ScoredOpportunity]

    Algorithm
    ---------
    1. For each company that has ≥ 1 gap:
       a. GAP SCORE (weight 0.30):
          - Average match_quality across all gaps.
          - Bonus for multiple gaps (compound opportunity).

       b. FINANCIAL SCORE (weight 0.20):
          - financial_health: strong=1.0, moderate=0.7, weak=0.3, unknown=0.5
          - Budget signals: each signal adds +5 (cap at 20).

       c. URGENCY SCORE (weight 0.20):
          - Max urgency across all needs.
          - Normalize to 0-1 scale.

       d. PROBLEM ALIGNMENT SCORE (weight 0.15):
          - How many market_problems (age_can_solve=True) match this company?
          - More problems we solve = stronger position.

       e. BASE FIT SCORE (weight 0.15):
          - From CompanyRanker.fit_score, normalize to 0-1.

    2. total_score = weighted sum × 100.

    3. Revenue potential estimation:
       - Based on gap types:
         · Full line replacement: €200K-€2M
         · Single machine: €50K-€500K
         · Service/upgrade: €20K-€100K
       - Adjust by company size and region.

    4. Win probability estimation:
       - Based on: gap match quality, competitor presence, financial health,
         our network connections, timing of need.
       - P(win): 0.0 - 1.0

    5. Assign priority:
       - CRITICAL: total_score > 85 AND win_probability > 0.5
       - HIGH: total_score > 70 OR (total_score > 60 AND win_probability > 0.6)
       - MEDIUM: total_score > 50
       - LOW: everything else

    6. Sort by total_score descending.
    7. Return list[ScoredOpportunity].

    Quality gates
    -------------
    - At least 10 opportunities with priority CRITICAL or HIGH.
    - Score distribution should differentiate (std_dev > 10).

    Subscribers
    -----------
    → WinLossAnalyzer, ProposalGenerator, SalesPlaybookGenerator
    """

    name = "opportunity_scorer"
    description = "Final scoring and prioritization of every company opportunity."
    phase = PhaseID.PHASE_3_GAP_ANALYSIS
    dependencies = [
        Dependency(agent_name="gap_detector", required=True, data_keys=["gap_map"]),
        Dependency(agent_name="financial_analyzer", required=False, data_keys=["financial_snapshots"]),
        Dependency(agent_name="market_problem_analyzer", required=True, data_keys=["market_problems"]),
        Dependency(agent_name="company_ranker", required=True, data_keys=["ranked_companies"]),
    ]
    output_keys = ["scored_opportunities"]
    subscribers = ["win_loss_analyzer", "proposal_generator", "sales_playbook_generator"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load gap_map, financial_snapshots, market_problems, ranked_companies
        2. For each company with gaps:
           a. Compute gap_score (avg match_quality + multi-gap bonus)
           b. Compute financial_score (health + budget signals)
           c. Compute urgency_score (max urgency of needs)
           d. Compute problem_alignment_score
           e. Compute base_fit_score
           f. total_score = weighted sum × 100
        3. Estimate revenue_potential by gap type × company size
        4. Estimate win_probability
        5. Assign priority tier
        6. Sort by total_score
        7. Validate quality gates
        8. Return AgentOutput with scored_opportunities
        """

        gap_map = self._get_dep(context, "gap_detector", "gap_map") or {}
        financial_snapshots = self._get_dep(context, "financial_analyzer", "financial_snapshots") or {}
        scored_opportunities: list[dict] = []

        return self._make_output(
            data={"scored_opportunities": scored_opportunities},
            confidence=ConfidenceLevel.HIGH,
        )
