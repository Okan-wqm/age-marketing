"""
Phase 4 — Competitor & Market Positioning  (4 agents)
======================================================
CompetitorMapper  →  CompetitorAnalyzer  →  MarketPositioner
                                         →  WinLossAnalyzer

Understand the competitive landscape so we can position AGE
optimally against each competitor per opportunity.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, Dependency
from .models import (
    AgentOutput,
    CompetitorProfile,
    ConfidenceLevel,
    PhaseID,
    PositioningEntry,
    WinLossPattern,
)


# =====================================================================
# 22. COMPETITOR MAPPER
# =====================================================================
class CompetitorMapper(BaseAgent):
    """
    Identifies and maps all relevant competitors per sector/region.

    Inputs
    ------
    - sector_deep_researcher.sector_profiles   (key_players in each sector)
    - company_ranker.ranked_companies          (current_equipment → competitors)
    - trade_show_researcher.trade_shows        (exhibitors who are competitors)

    Outputs
    -------
    - competitor_map : dict[sector, list[competitor_name]]

    Algorithm
    ---------
    1. Gather competitor candidates from multiple sources:
       a. Sector key_players that are equipment manufacturers
          (not food producers).
       b. Known AGE competitor list (if provided in input).
       c. Trade show exhibitors categorized as "machinery manufacturers".
       d. Companies appearing in ranked_companies'  known_suppliers
          or current_equipment fields.
    2. Deduplicate and categorize:
       - Global competitors (operate worldwide): Multivac, ULMA, GEA, etc.
       - Regional competitors (strong in specific regions).
       - Niche competitors (specific product category).
    3. Map each competitor to the sectors they serve.
    4. Return dict[sector → list[competitor_name]].

    Quality gates
    -------------
    - At least 5 unique competitors identified.
    - Every sector must have ≥ 2 competitors mapped.

    Subscribers
    -----------
    → CompetitorAnalyzer
    """

    name = "competitor_mapper"
    description = "Maps all relevant competitors per sector and region."
    phase = PhaseID.PHASE_4_COMPETITOR_MARKET
    dependencies = [
        Dependency(agent_name="sector_deep_researcher", required=True, data_keys=["sector_profiles"]),
        Dependency(agent_name="company_ranker", required=False, data_keys=["ranked_companies"]),
        Dependency(agent_name="trade_show_researcher", required=False, data_keys=["trade_shows"]),
    ]
    output_keys = ["competitor_map"]
    subscribers = ["competitor_analyzer"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Extract key_players from sector_profiles (filter to machine makers)
        2. Extract known_suppliers from ranked_companies
        3. Extract machinery exhibitors from trade_shows
        4. Add known AGE competitors from input (if available)
        5. Deduplicate
        6. Categorize: global / regional / niche
        7. Map competitor → sectors served
        8. Validate quality gates
        9. Return AgentOutput with competitor_map
        """

        sector_profiles = self._get_dep(context, "sector_deep_researcher", "sector_profiles") or []
        competitor_map: dict[str, list[str]] = {}

        return self._make_output(
            data={"competitor_map": competitor_map},
            confidence=ConfidenceLevel.MEDIUM,
        )


# =====================================================================
# 23. COMPETITOR ANALYZER
# =====================================================================
class CompetitorAnalyzer(BaseAgent):
    """
    Deep analysis of each competitor: products, pricing, strengths,
    weaknesses, market share, strategy.

    Inputs
    ------
    - competitor_mapper.competitor_map
    - sector_deep_researcher.sector_profiles

    Outputs
    -------
    - competitor_profiles : list[CompetitorProfile]

    Algorithm
    ---------
    1. For each competitor:
       a. Website deep scan:
          - Product portfolio → what machines do they make?
          - Key differentiators they claim.
          - Innovation / R&D highlights.
          - Global presence / factory locations.
       b. Product comparison:
          - Side-by-side features vs. AGE products.
          - Speed, capacity, material compatibility.
          - Technology level (Industry 4.0, automation).
       c. Pricing intelligence:
          - Public price lists (rare but sometimes available).
          - Tender results (public sector).
          - Sales rep conversations / industry word-of-mouth.
          - Position: premium / mid-range / value.
       d. Market share estimation:
          - Revenue of competitor ÷ total sector market size.
          - Installed base estimation.
       e. Strengths analysis:
          - What do customers praise?
          - Awards, certifications, innovation track record.
          - Service network coverage.
          - Brand reputation.
       f. Weaknesses analysis:
          - Common complaints (from forums, reviews, LinkedIn posts).
          - Service gaps (slow response, expensive spare parts).
          - Technology gaps vs. state of the art.
          - Geographic blind spots.
       g. Key customers:
          - Reference projects mentioned on website.
          - Case studies.
          - LinkedIn connections.
       h. Threat level (0-100):
          - Direct product overlap with AGE.
          - Market share in our target regions.
          - Pricing aggressiveness.
          - Brand strength.
    2. Return list[CompetitorProfile].

    Quality gates
    -------------
    - Every competitor must have ≥ 2 strengths and ≥ 2 weaknesses.
    - pricing_strategy must be filled.
    - threat_level must be scored.

    Subscribers
    -----------
    → MarketPositioner, WinLossAnalyzer, PricingStrategist
    """

    name = "competitor_analyzer"
    description = "Deep analysis of each competitor's products, pricing, strengths, and weaknesses."
    phase = PhaseID.PHASE_4_COMPETITOR_MARKET
    dependencies = [
        Dependency(agent_name="competitor_mapper", required=True, data_keys=["competitor_map"]),
        Dependency(agent_name="sector_deep_researcher", required=False, data_keys=["sector_profiles"]),
    ]
    output_keys = ["competitor_profiles"]
    subscribers = ["market_positioner", "win_loss_analyzer", "pricing_strategist"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load competitor_map → flat list of unique competitors
        2. For each competitor:
           a. Deep scan website (products, claims, locations)
           b. Compare products vs AGE feature-by-feature
           c. Estimate pricing strategy
           d. Estimate market share
           e. Analyze strengths and weaknesses
           f. Find key customers / references
           g. Score threat_level
        3. Validate quality gates
        4. Return AgentOutput with competitor_profiles
        """

        competitor_map = self._get_dep(context, "competitor_mapper", "competitor_map") or {}
        competitor_profiles: list[dict] = []

        return self._make_output(
            data={"competitor_profiles": competitor_profiles},
            confidence=ConfidenceLevel.MEDIUM,
        )


# =====================================================================
# 24. MARKET POSITIONER
# =====================================================================
class MarketPositioner(BaseAgent):
    """
    Creates AGE's competitive positioning map against each competitor.

    Inputs
    ------
    - competitor_analyzer.competitor_profiles
    - usp_extractor.usps
    - gap_detector.gap_map

    Outputs
    -------
    - positioning_map : list[PositioningEntry]

    Algorithm
    ---------
    1. Define positioning dimensions:
       - Price competitiveness
       - Product quality / precision
       - Technology / innovation level
       - Service & support
       - Speed / throughput
       - Customization flexibility
       - Sustainability
       - Industry 4.0 / digital capabilities
       - Global reach / local support
       - Brand reputation / track record

    2. For each dimension:
       a. Score AGE (0-100) based on USPs and capabilities.
       b. Score each competitor (0-100) based on CompetitorProfiles.
       c. Determine our_advantage (True if we score > all competitors).
       d. Write narrative:
          - Where we win: "AGE outperforms on X because of Y."
          - Where we lose: "Competitor Z leads on X; we can mitigate by…"
          - Where we're equal: "Parity on X; differentiate on other factors."

    3. Build overall positioning statement:
       - "AGE is the [quality/value/innovation] leader in [sector],
          offering [USP1] and [USP2] that competitors lack."

    4. Create competitor-specific battle cards:
       - vs. Multivac: emphasize [USP], they're weak on [gap].
       - vs. ULMA: price advantage, comparable quality.
       - etc.

    5. Return list[PositioningEntry].

    Quality gates
    -------------
    - At least 6 dimensions scored.
    - AGE must have advantage on ≥ 2 dimensions (else our USPs are weak).

    Subscribers
    -----------
    → OutreachComposer, ProposalGenerator, SalesPlaybookGenerator
    """

    name = "market_positioner"
    description = "Creates competitive positioning map with battle cards per competitor."
    phase = PhaseID.PHASE_4_COMPETITOR_MARKET
    dependencies = [
        Dependency(agent_name="competitor_analyzer", required=True, data_keys=["competitor_profiles"]),
        Dependency(agent_name="usp_extractor", required=True, data_keys=["usps"]),
        Dependency(agent_name="gap_detector", required=False, data_keys=["gap_map"]),
    ]
    output_keys = ["positioning_map"]
    subscribers = ["outreach_composer", "proposal_generator", "sales_playbook_generator"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load competitor_profiles, usps, gap_map
        2. Define 10 positioning dimensions
        3. Score AGE on each dimension from USPs/capabilities
        4. Score each competitor from competitor_profiles
        5. Determine advantage per dimension
        6. Write narrative for each dimension
        7. Build overall positioning statement
        8. Create competitor-specific battle cards
        9. Validate quality gates
        10. Return AgentOutput with positioning_map
        """

        competitor_profiles = self._get_dep(context, "competitor_analyzer", "competitor_profiles") or []
        usps = self._get_dep(context, "usp_extractor", "usps") or []
        positioning_map: list[dict] = []

        return self._make_output(
            data={"positioning_map": positioning_map},
            confidence=ConfidenceLevel.HIGH,
        )


# =====================================================================
# 25. WIN/LOSS ANALYZER
# =====================================================================
class WinLossAnalyzer(BaseAgent):
    """
    Identifies patterns that predict wins and losses against
    specific competitors.

    Inputs
    ------
    - competitor_analyzer.competitor_profiles
    - opportunity_scorer.scored_opportunities

    Outputs
    -------
    - win_loss_patterns : list[WinLossPattern]

    Algorithm
    ---------
    1. Analyze competitor weaknesses + our strengths to find WIN patterns:
       a. For each competitor weakness:
          - If AGE has a corresponding strength → WIN FACTOR.
          - Example: Competitor has slow service response + AGE has 24h service
            → Win factor: "Service response superiority".
       b. For each market problem where AGE has solution but competitor doesn't:
          - → Win factor: "Unique solution for [problem]".
       c. Price advantage scenarios:
          - If AGE is more cost-effective → Win factor in price-sensitive markets.

    2. Analyze competitor strengths + our weaknesses to find LOSS patterns:
       a. For each competitor strength where AGE is weaker:
          - → LOSS FACTOR.
          - Example: Competitor has stronger brand in Germany.
       b. Mitigation recommendation for each loss factor:
          - Can we improve? Or should we avoid this battleground?

    3. Assess frequency:
       - How often does each pattern likely apply?
       - Based on how many target companies fall into that scenario.

    4. Generate recommended actions:
       - Win factors → emphasize in sales pitch.
       - Loss factors → prepare objection handlers.

    5. Return list[WinLossPattern].

    Quality gates
    -------------
    - At least 3 win factors and 2 loss factors identified.
    - Each pattern must have recommended_action.

    Subscribers
    -----------
    → SalesPlaybookGenerator, OutreachComposer
    """

    name = "win_loss_analyzer"
    description = "Identifies win/loss patterns against each competitor."
    phase = PhaseID.PHASE_4_COMPETITOR_MARKET
    dependencies = [
        Dependency(agent_name="competitor_analyzer", required=True, data_keys=["competitor_profiles"]),
        Dependency(agent_name="opportunity_scorer", required=True, data_keys=["scored_opportunities"]),
    ]
    output_keys = ["win_loss_patterns"]
    subscribers = ["sales_playbook_generator", "outreach_composer"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load competitor_profiles and scored_opportunities
        2. For each competitor:
           a. Match their weaknesses vs our strengths → win factors
           b. Match their strengths vs our weaknesses → loss factors
        3. Assess problem-solution uniqueness → win factors
        4. Assess price positioning → win/loss factors
        5. Score frequency of each pattern
        6. Write recommended_action for each
        7. Validate quality gates
        8. Return AgentOutput with win_loss_patterns
        """

        competitor_profiles = self._get_dep(context, "competitor_analyzer", "competitor_profiles") or []
        scored_opportunities = self._get_dep(context, "opportunity_scorer", "scored_opportunities") or []
        win_loss_patterns: list[dict] = []

        return self._make_output(
            data={"win_loss_patterns": win_loss_patterns},
            confidence=ConfidenceLevel.MEDIUM,
        )
