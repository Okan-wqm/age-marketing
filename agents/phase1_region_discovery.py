"""
Phase 1 — Region Discovery  (3 agents)
========================================
RegionScanner  →  RegulatoryAnalyzer  →  RegionRanker

Identify and rank the most promising geographic markets
for AGE products before drilling into individual companies.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, Dependency
from .models import (
    AgentOutput,
    ConfidenceLevel,
    PhaseID,
    RegionProfile,
    RegulatoryInfo,
)


# =====================================================================
# 4. REGION SCANNER
# =====================================================================
class RegionScanner(BaseAgent):
    """
    Scans global regions for potential market opportunity.

    Inputs
    ------
    - product_analyzer.product_profiles
    - context["input"]["geography_hints"]  (optional user hints like "focus Europe")

    Outputs
    -------
    - regions : list[RegionProfile]

    Algorithm
    ---------
    1. Start with a master country/region list (200+ countries).
    2. Apply coarse filter based on product target_industries:
       a. For each target_industry, look up which countries have
          significant activity in that sector.
          - Use industry databases, World Bank data, UN Comtrade.
       b. Score each country:  industry_relevance × GDP_weight.
    3. Apply geography_hints (if provided) as boosters/filters:
       - "focus Europe" → multiply EU countries by 2x.
       - "exclude sanctioned" → remove sanctioned countries.
    4. For surviving countries, gather:
       a. GDP (nominal USD)
       b. Population
       c. Industrial output as % of GDP → industrial_strength
       d. Ease of doing business index
       e. Primary language, currency
       f. Active trade agreements (with Türkiye specifically)
    5. Compute initial opportunity_score =
         (industrial_strength × 0.3) +
         (ease_of_business × 0.2) +
         (sector_match × 0.4) +
         (trade_agreement_bonus × 0.1)
    6. Return top 30-50 regions as list[RegionProfile].

    Quality gates
    -------------
    - At least 10 regions with opportunity_score > 50.
    - Every region must have GDP and population filled.

    Subscribers
    -----------
    → RegulatoryAnalyzer, RegionRanker, SectorDeepResearcher,
      CountryMarketAnalyzer, CompanyDiscoveryAgent, TradeShowResearcher
    """

    name = "region_scanner"
    description = "Scans global regions and scores them for market opportunity."
    phase = PhaseID.PHASE_1_REGION_DISCOVERY
    dependencies = [
        Dependency(agent_name="product_analyzer", required=True, data_keys=["product_profiles"]),
    ]
    output_keys = ["regions"]
    subscribers = [
        "regulatory_analyzer",
        "region_ranker",
        "sector_deep_researcher",
        "country_market_analyzer",
        "company_discovery",
        "trade_show_researcher",
    ]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load product_profiles → extract target_industries
        2. Load geography_hints (optional)
        3. Build master country list
        4. For each country:
           a. Compute sector_match = count of matching industries / total
           b. Fetch GDP, population, industrial_strength
           c. Fetch ease_of_doing_business
           d. Check trade agreements with Turkey
        5. Apply geography_hints as multipliers/filters
        6. Compute opportunity_score (weighted formula)
        7. Sort descending, take top 30-50
        8. Validate quality gates
        9. Return AgentOutput with regions
        """

        product_profiles = self._get_dep(context, "product_analyzer", "product_profiles") or []
        geography_hints = context.get("input", {}).get("geography_hints", {})
        regions: list[dict] = []

        return self._make_output(
            data={"regions": regions},
            confidence=ConfidenceLevel.MEDIUM,
        )


# =====================================================================
# 5. REGULATORY ANALYZER
# =====================================================================
class RegulatoryAnalyzer(BaseAgent):
    """
    Analyzes import regulations, tariffs, and certifications per region.

    Inputs
    ------
    - region_scanner.regions
    - product_analyzer.product_profiles  (to know which HS codes apply)

    Outputs
    -------
    - regulatory_map : dict[region_id, RegulatoryInfo]

    Algorithm
    ---------
    1. For each region in regions[]:
       a. Determine applicable HS codes from product categories.
       b. Look up import tariffs for those HS codes in that country.
          - Data sources: WTO tariff database, national customs sites.
       c. Identify required certifications:
          - EU → CE marking, specific EN standards.
          - USA → FDA (food contact), UL (electrical).
          - Each country may have national standards.
       d. Check for import restrictions:
          - Sanctions, quotas, local-content requirements.
       e. Identify incentives:
          - Free trade zones, investment incentives, tax holidays.
    2. Compute regulatory_complexity score (0-100):
       - Factors: number of certs required, tariff level,
         restriction count, bureaucracy index.
    3. Flag "deal-breaker" regulations (e.g., outright import bans)
       → warning in output.
    4. Return dict mapping region_id → RegulatoryInfo.

    Quality gates
    -------------
    - Every region must have at least tariff data.
    - Regions missing cert info → confidence = LOW for that entry.

    Subscribers
    -----------
    → RegionRanker, PricingStrategist
    """

    name = "regulatory_analyzer"
    description = "Analyzes tariffs, certifications, and import regulations per region."
    phase = PhaseID.PHASE_1_REGION_DISCOVERY
    dependencies = [
        Dependency(agent_name="region_scanner", required=True, data_keys=["regions"]),
        Dependency(agent_name="product_analyzer", required=True, data_keys=["product_profiles"]),
    ]
    output_keys = ["regulatory_map"]
    subscribers = ["region_ranker", "pricing_strategist"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load regions and product_profiles
        2. Determine HS codes for each product category
        3. For each region:
           a. Query tariff databases for HS codes
           b. Look up required certifications
           c. Check for restrictions / bans
           d. Identify incentives (FTZs, tax holidays)
           e. Compute regulatory_complexity score
        4. Flag deal-breakers as warnings
        5. Validate quality gates
        6. Return AgentOutput with regulatory_map
        """

        regions = self._get_dep(context, "region_scanner", "regions") or []
        regulatory_map: dict[str, dict] = {}

        return self._make_output(
            data={"regulatory_map": regulatory_map},
            confidence=ConfidenceLevel.MEDIUM,
        )


# =====================================================================
# 6. REGION RANKER
# =====================================================================
class RegionRanker(BaseAgent):
    """
    Produces a final ranked list of target regions by combining
    opportunity scores with regulatory feasibility.

    Inputs
    ------
    - region_scanner.regions
    - regulatory_analyzer.regulatory_map
    - product_analyzer.product_profiles

    Outputs
    -------
    - ranked_regions : list[RegionProfile]  (re-scored and sorted)

    Algorithm
    ---------
    1. For each region:
       a. Load base opportunity_score from RegionScanner.
       b. Load regulatory_complexity from RegulatoryAnalyzer.
       c. Compute regulatory_penalty = regulatory_complexity × -0.3
       d. Compute incentive_bonus (if incentives exist) = +5 per incentive, cap 15
       e. Check if AGE already has required certifications:
          - certs_we_have = product_profiles[*].certifications
          - certs_needed = regulatory_map[region].required_certifications
          - cert_gap_count = len(certs_needed - certs_we_have)
          - cert_penalty = cert_gap_count × -3
       f. final_score = opportunity_score + regulatory_penalty +
                        incentive_bonus + cert_penalty
    2. Sort by final_score descending.
    3. Assign tiers:
       - Tier 1: top 20% → "primary_target"
       - Tier 2: next 30% → "secondary_target"
       - Tier 3: rest → "monitor"
    4. Return list[RegionProfile] with updated opportunity_score
       and tier annotation.

    Quality gates
    -------------
    - At least 5 Tier-1 regions.
    - If fewer → warn and expand Tier-1 threshold.

    Subscribers
    -----------
    → SectorDeepResearcher, CountryMarketAnalyzer,
      CompanyDiscoveryAgent, TradeShowResearcher
    """

    name = "region_ranker"
    description = "Final ranking of target regions combining opportunity + regulatory feasibility."
    phase = PhaseID.PHASE_1_REGION_DISCOVERY
    dependencies = [
        Dependency(agent_name="region_scanner", required=True, data_keys=["regions"]),
        Dependency(agent_name="regulatory_analyzer", required=True, data_keys=["regulatory_map"]),
        Dependency(agent_name="product_analyzer", required=True, data_keys=["product_profiles"]),
    ]
    output_keys = ["ranked_regions"]
    subscribers = [
        "sector_deep_researcher",
        "country_market_analyzer",
        "company_discovery",
        "trade_show_researcher",
    ]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load regions, regulatory_map, product_profiles
        2. Build cert inventory from all products
        3. For each region:
           a. Get base opportunity_score
           b. Compute regulatory_penalty
           c. Compute incentive_bonus
           d. Compute cert_gap_count and cert_penalty
           e. final_score = sum of above
        4. Sort by final_score descending
        5. Assign tiers (Tier 1 / 2 / 3)
        6. Validate: at least 5 Tier-1 regions
        7. Return AgentOutput with ranked_regions
        """

        regions = self._get_dep(context, "region_scanner", "regions") or []
        regulatory_map = self._get_dep(context, "regulatory_analyzer", "regulatory_map") or {}
        ranked_regions: list[dict] = []

        return self._make_output(
            data={"ranked_regions": ranked_regions},
            confidence=ConfidenceLevel.HIGH,
        )
