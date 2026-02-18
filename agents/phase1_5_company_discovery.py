"""
Phase 1.5 — Company Discovery  (3 agents)
===========================================
CompanyDiscoveryAgent  →  CompanyValidator  →  CompanyRanker

Find, validate, and rank potential customer companies using MULTIPLE
discovery channels including trade show exhibitors, sector databases,
web search, and industry directories.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, Dependency
from .models import (
    AgentOutput,
    CompanyProfile,
    ConfidenceLevel,
    PhaseID,
)


# =====================================================================
# 11. COMPANY DISCOVERY AGENT
# =====================================================================
class CompanyDiscoveryAgent(BaseAgent):
    """
    Multi-channel company discovery engine.

    Uses 6+ discovery channels to build the broadest possible list
    of potential customers.

    Inputs
    ------
    - region_ranker.ranked_regions          (WHERE to look)
    - sector_deep_researcher.sector_profiles (WHAT sectors to look in)
    - country_market_analyzer.country_market_matrix  (local player hints)
    - trade_show_researcher.trade_shows     (exhibitor lists)
    - product_analyzer.product_profiles     (WHAT we sell → who buys this?)

    Outputs
    -------
    - raw_companies : list[CompanyProfile]  (unvalidated, may have dupes)

    Algorithm
    ---------
    Channel 1 — Trade Show Exhibitors:
      1. For each trade_show in trade_shows:
         a. Take known_exhibitors list.
         b. For each exhibitor:
            - Create CompanyProfile with discovery_source = "trade_show:{show_name}".
            - Fill: name, country (from show location), sector.

    Channel 2 — Industry Directory Search:
      2. For each (sector, country) in country_market_matrix:
         a. Search industry directories:
            - Kompass.com, ThomasNet, Europages, Alibaba (B2B).
            - "[sector] companies in [country]"
            - "[sector] manufacturers [country]"
         b. For each found company:
            - Create CompanyProfile with discovery_source = "directory:{directory_name}".

    Channel 3 — Web Search:
      3. For each (sector, country) pair (Tier 1 regions only):
         a. Search: "[sector] companies [country] list"
         b. Search: "[sector] producers [country]"
         c. Search: "[sector] [country] industry directory"
         d. Parse results → extract company names and websites.
         e. discovery_source = "web_search".

    Channel 4 — Trade Association Members:
      4. For each sector:
         a. Identify trade associations for that sector:
            - Dairy: IDF members, national dairy associations.
            - Meat: national meat processor associations.
            - Pharma: ISPE members, PDA members.
         b. Search: "[association name] member list"
         c. Extract member companies.
         d. discovery_source = "trade_association:{association_name}".

    Channel 5 — Competitor Customer Lists:
      5. Look at known competitors of AGE:
         a. Search: "[competitor name] customers"
         b. Search: "[competitor name] installations references"
         c. Companies using competitor equipment may need upgrades.
         d. discovery_source = "competitor_customers".

    Channel 6 — Country Market Key Players:
      6. country_market_matrix already lists key_local_players:
         a. Add each as CompanyProfile.
         b. discovery_source = "market_analysis".

    Channel 7 — LinkedIn / Social:
      7. For Tier 1 regions:
         a. Search: LinkedIn company search for "[sector] [country]"
         b. Look for companies with 50-5000 employees in target sectors.
         c. discovery_source = "linkedin".

    Deduplication:
      8. Merge entries that are clearly the same company:
         - Fuzzy match on company name + country.
         - Merge discovery_sources.

    Return list[CompanyProfile] — all unvalidated, tagged with source.

    Quality gates
    -------------
    - At least 100 raw companies found total.
    - At least 3 different discovery channels used.
    - Each Tier-1 region must have ≥ 10 companies.

    Subscribers
    -----------
    → CompanyValidator
    """

    name = "company_discovery"
    description = "Multi-channel company discovery across trade shows, directories, web, and associations."
    phase = PhaseID.PHASE_1_5_COMPANY_DISCOVERY
    dependencies = [
        Dependency(agent_name="region_ranker", required=True, data_keys=["ranked_regions"]),
        Dependency(agent_name="sector_deep_researcher", required=True, data_keys=["sector_profiles"]),
        Dependency(agent_name="country_market_analyzer", required=False, data_keys=["country_market_matrix"]),
        Dependency(agent_name="trade_show_researcher", required=False, data_keys=["trade_shows"]),
        Dependency(agent_name="product_analyzer", required=True, data_keys=["product_profiles"]),
    ]
    output_keys = ["raw_companies"]
    subscribers = ["company_validator"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load all dependency data
        2. Channel 1: Extract companies from trade show exhibitor lists
        3. Channel 2: Search industry directories per (sector, country)
        4. Channel 3: Web search for companies per (sector, country)
        5. Channel 4: Search trade association member lists
        6. Channel 5: Look for competitor customer references
        7. Channel 6: Add key_local_players from country market matrix
        8. Channel 7: LinkedIn company search (Tier 1 only)
        9. Deduplicate by fuzzy name + country matching
        10. Tag each with discovery_source
        11. Validate quality gates
        12. Return AgentOutput with raw_companies
        """

        raw_companies: list[dict] = []

        return self._make_output(
            data={"raw_companies": raw_companies},
            confidence=ConfidenceLevel.MEDIUM,
            sources=[
                "trade_shows", "kompass", "europages", "thomasnet",
                "web_search", "trade_associations", "linkedin",
            ],
        )


# =====================================================================
# 12. COMPANY VALIDATOR
# =====================================================================
class CompanyValidator(BaseAgent):
    """
    Validates and enriches raw company data.

    Inputs
    ------
    - company_discovery.raw_companies

    Outputs
    -------
    - validated_companies : list[CompanyProfile]  (cleaned, enriched)

    Algorithm
    ---------
    1. For each raw company:
       a. Website validation:
          - Attempt to resolve the website URL.
          - If no website → search: "[company name] [country] official website".
          - If still no website → flag as "unverifiable".
       b. Basic data enrichment:
          - Scrape website for:
            · Employee count (from "About" page or LinkedIn)
            · Annual revenue (if public, or from financial databases)
            · Founded year
            · Products/services description
            · Certifications (ISO, FSSC, BRC, etc.)
          - discovery_source remains from Channel, add "validated" flag.
       c. Sector confirmation:
          - Verify the company actually operates in the target sector.
          - Read their product/service descriptions.
          - If sector mismatch → drop from list.
       d. Size filter:
          - Drop companies that are too small (< 20 employees) — unlikely
            to buy industrial equipment.
          - Drop companies that are too big and already have corporate
            procurement (> 50,000 employees) — different sales process.
          - Keep: 20-50,000 employees sweet spot.
       e. Duplicate check (second pass):
          - Compare against already-validated list.
          - Merge if duplicate, keeping richer data.
    2. Set validation_status = "validated" for passing companies.
    3. Return list[CompanyProfile] (validated, enriched).

    Quality gates
    -------------
    - At least 60% of raw_companies pass validation.
    - Every validated company has website and sector confirmed.
    - If pass rate < 40% → warning + confidence = LOW.

    Subscribers
    -----------
    → CompanyRanker
    """

    name = "company_validator"
    description = "Validates, enriches, and filters raw company data."
    phase = PhaseID.PHASE_1_5_COMPANY_DISCOVERY
    dependencies = [
        Dependency(agent_name="company_discovery", required=True, data_keys=["raw_companies"]),
    ]
    output_keys = ["validated_companies"]
    subscribers = ["company_ranker"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load raw_companies
        2. For each company:
           a. Validate/find website
           b. Enrich: employee_count, revenue, founded_year
           c. Confirm sector from website content
           d. Apply size filter (20-50K employees)
           e. Check for duplicates
        3. Set validation_status = "validated"
        4. Compute pass rate
        5. Validate quality gates
        6. Return AgentOutput with validated_companies
        """

        raw_companies = self._get_dep(context, "company_discovery", "raw_companies") or []
        validated_companies: list[dict] = []

        return self._make_output(
            data={"validated_companies": validated_companies},
            confidence=ConfidenceLevel.MEDIUM,
        )


# =====================================================================
# 13. COMPANY RANKER
# =====================================================================
class CompanyRanker(BaseAgent):
    """
    Scores and ranks validated companies by fit with AGE's offering.

    Inputs
    ------
    - company_validator.validated_companies
    - sector_deep_researcher.sector_profiles
    - country_market_analyzer.country_market_matrix
    - market_problem_analyzer.market_problems

    Outputs
    -------
    - ranked_companies : list[CompanyProfile]  (with fit_score set)

    Algorithm
    ---------
    1. For each validated company, compute fit_score from 5 dimensions:

       a. Sector fit (weight 0.25):
          - Does their sector match a high age_relevance_score sector?
          - Score = sector_profile.age_relevance_score / 100

       b. Size fit (weight 0.20):
          - Sweet spot: 100-5000 employees.
          - < 100: score = employee_count / 100
          - 100-5000: score = 1.0
          - > 5000: score = max(0.5, 1.0 - (employee_count - 5000) / 50000)

       c. Region fit (weight 0.20):
          - Tier 1 region → 1.0
          - Tier 2 region → 0.7
          - Tier 3 region → 0.4

       d. Problem alignment (weight 0.20):
          - Count of market_problems where:
            · problem.sector matches company.sector
            · problem.country matches company.country
            · problem.age_can_solve = True
          - Score = min(1.0, problem_count / 5)

       e. Discovery richness (weight 0.15):
          - Companies found through multiple channels = higher signal.
          - 1 channel → 0.3
          - 2 channels → 0.6
          - 3+ channels → 1.0

    2. fit_score = weighted sum of above (0-100 scale).
    3. Sort by fit_score descending.
    4. Assign tiers:
       - A-tier: top 15% → "high_priority"
       - B-tier: next 25% → "medium_priority"
       - C-tier: rest → "low_priority"
    5. Return list[CompanyProfile] with fit_score and tier.

    Quality gates
    -------------
    - At least 10 A-tier companies.
    - fit_score distribution should not be uniform (we want differentiation).

    Subscribers
    -----------
    → CompanyProfiler, FinancialAnalyzer, CompanyDeepResearcher,
      CompetitorMapper, ContactFinder
    """

    name = "company_ranker"
    description = "Scores and ranks validated companies by multi-dimensional fit."
    phase = PhaseID.PHASE_1_5_COMPANY_DISCOVERY
    dependencies = [
        Dependency(agent_name="company_validator", required=True, data_keys=["validated_companies"]),
        Dependency(agent_name="sector_deep_researcher", required=True, data_keys=["sector_profiles"]),
        Dependency(agent_name="country_market_analyzer", required=False, data_keys=["country_market_matrix"]),
        Dependency(agent_name="market_problem_analyzer", required=False, data_keys=["market_problems"]),
    ]
    output_keys = ["ranked_companies"]
    subscribers = [
        "company_profiler",
        "financial_analyzer",
        "company_deep_researcher",
        "competitor_mapper",
        "contact_finder",
    ]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load validated_companies, sector_profiles, country_market_matrix, market_problems
        2. For each company:
           a. Compute sector_fit from sector_profile.age_relevance_score
           b. Compute size_fit from employee_count
           c. Compute region_fit from region tier
           d. Compute problem_alignment from market_problems match
           e. Compute discovery_richness from source count
           f. fit_score = weighted sum × 100
        3. Sort by fit_score descending
        4. Assign tiers: A / B / C
        5. Validate quality gates
        6. Return AgentOutput with ranked_companies
        """

        validated_companies = self._get_dep(context, "company_validator", "validated_companies") or []
        ranked_companies: list[dict] = []

        return self._make_output(
            data={"ranked_companies": ranked_companies},
            confidence=ConfidenceLevel.HIGH,
        )
