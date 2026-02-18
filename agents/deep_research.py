"""
Deep Research Layer  (4 agents)
================================
SectorDeepResearcher  →  CountryMarketAnalyzer  →  MarketProblemAnalyzer
TradeShowResearcher   (runs in parallel with the above)

These agents perform DEEP, multi-source research that feeds into
company discovery and gap analysis.  They answer the fundamental
questions:
  - Which sectors does the customer actually serve?
  - Which countries have those sectors?
  - What are the main problems in each sector?
  - How big is the market?
  - Which trade shows gather the right companies?
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, Dependency
from .models import (
    AgentOutput,
    ConfidenceLevel,
    CountryMarketEntry,
    MarketProblem,
    PhaseID,
    SectorProfile,
    TradeShow,
)


# =====================================================================
# 7. SECTOR DEEP RESEARCHER
# =====================================================================
class SectorDeepResearcher(BaseAgent):
    """
    Performs deep research into every sector that AGE products can serve.

    This is NOT a surface-level lookup.  The agent digs into industry
    reports, news, academic papers, and market databases to build a
    rich profile of each sector.

    Inputs
    ------
    - product_analyzer.product_profiles   (target_industries per product)
    - region_ranker.ranked_regions         (which regions to focus on)

    Outputs
    -------
    - sector_profiles : list[SectorProfile]

    Algorithm
    ---------
    1. Collect all unique target_industries from product_profiles.
       Example raw list: ["dairy", "meat", "pharma", "cosmetics",
                          "ready_meals", "bakery", "cheese"]
    2. Group into canonical sectors:
       - "dairy" + "cheese" → Dairy & Cheese Processing
       - "meat" → Meat Processing
       - "pharma" → Pharmaceutical Packaging
       - "cosmetics" → Cosmetics & Personal Care Packaging
       - "ready_meals" → Ready Meal / Convenience Food Packaging
       - "bakery" → Bakery & Confectionery Packaging
    3. For EACH sector, perform deep research:
       a. Global market size (USD):
          - Search industry reports (Mordor Intelligence, Grand View
            Research, Statista, IMARC, MarketResearch.com).
          - Cross-validate at least 2 sources.
          - Record CAGR (compound annual growth rate).
       b. Top countries where this sector is strongest:
          - Look at production output data.
          - Look at export/import volumes.
          - Map to ranked_regions to verify we have overlap.
       c. Key players (global top 10-20):
          - Who are the biggest companies in this sector?
          - These become potential AGE customers OR reference points.
       d. Main problems & pain points:
          - What are the sector's biggest challenges RIGHT NOW?
          - Examples for dairy: shelf-life extension, sustainability
            regulations, clean-label demand, labor shortage.
          - For each problem, assess severity (0-100).
       e. Technology trends:
          - Automation, Industry 4.0, IoT in packaging.
          - New materials (biodegradable, recyclable).
          - Regulatory-driven changes (EU PPWR for example).
       f. Regulatory drivers:
          - EU Packaging & Packaging Waste Regulation (PPWR).
          - FDA Food Safety Modernization Act (FSMA).
          - Local regulations that force equipment upgrades.
       g. Entry barriers:
          - Established supplier relationships?
          - Technical certifications required?
          - Language/culture barriers?
       h. AGE relevance score:
          - How well do AGE's products actually fit this sector?
          - Score 0-100 based on product-sector match quality.
    4. Return list[SectorProfile] sorted by age_relevance_score.

    Research methodology
    --------------------
    - Primary: Web search for "[sector] market size [year]",
      "[sector] industry challenges [year]", "[sector] packaging trends".
    - Secondary: Company annual reports of top players.
    - Tertiary: Trade association publications (e.g., IDF for dairy,
      IFFA for meat).
    - Cross-validate: every market-size figure must appear in ≥2 sources.

    Quality gates
    -------------
    - Every sector must have global_market_size_usd > 0.
    - Every sector must have ≥3 main_problems.
    - Every sector must have ≥3 top_countries.
    - Cross-validation failures → confidence = LOW for that field.

    Subscribers
    -----------
    → CountryMarketAnalyzer, MarketProblemAnalyzer,
      CompanyDiscoveryAgent, CompetitorMapper
    """

    name = "sector_deep_researcher"
    description = "Deep multi-source research into each sector AGE products serve."
    phase = PhaseID.DEEP_RESEARCH
    dependencies = [
        Dependency(agent_name="product_analyzer", required=True, data_keys=["product_profiles"]),
        Dependency(agent_name="region_ranker", required=True, data_keys=["ranked_regions"]),
    ]
    output_keys = ["sector_profiles"]
    subscribers = [
        "country_market_analyzer",
        "market_problem_analyzer",
        "company_discovery",
        "competitor_mapper",
    ]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Extract all target_industries from product_profiles
        2. Canonicalize into sector names
        3. For each sector:
           a. SEARCH: "[sector] market size 2025-2030 report"
              → Extract global_market_size_usd, cagr_percent
           b. SEARCH: "[sector] top producing countries"
              → Build top_countries list
           c. SEARCH: "[sector] leading companies worldwide"
              → Build key_players list
           d. SEARCH: "[sector] industry challenges problems 2025"
              → Build main_problems list with severity scores
           e. SEARCH: "[sector] packaging technology trends"
              → Build technology_trends list
           f. SEARCH: "[sector] packaging regulations [region]"
              → Build regulatory_drivers list
           g. ANALYZE: entry_barriers from regulatory complexity +
              existing supplier concentration
           h. COMPUTE: age_relevance_score = product_feature_match(
                sector_needs, age_capabilities)
        4. Cross-validate market sizes across ≥2 sources
        5. Sort by age_relevance_score descending
        6. Validate quality gates
        7. Return AgentOutput with sector_profiles
        """

        product_profiles = self._get_dep(context, "product_analyzer", "product_profiles") or []
        ranked_regions = self._get_dep(context, "region_ranker", "ranked_regions") or []
        sector_profiles: list[dict] = []

        return self._make_output(
            data={"sector_profiles": sector_profiles},
            confidence=ConfidenceLevel.MEDIUM,
            sources=["industry_reports", "trade_associations", "market_databases"],
        )


# =====================================================================
# 8. COUNTRY MARKET ANALYZER
# =====================================================================
class CountryMarketAnalyzer(BaseAgent):
    """
    Creates a country × sector matrix showing exactly where opportunity
    exists.  Answers: "For each sector, which countries are the best
    markets, and how big is the local opportunity?"

    Inputs
    ------
    - sector_deep_researcher.sector_profiles
    - region_ranker.ranked_regions

    Outputs
    -------
    - country_market_matrix : list[CountryMarketEntry]

    Algorithm
    ---------
    1. Build the cross-product: ranked_regions × sector_profiles.
       - Only keep combos where the sector exists in that country
         (sector.top_countries includes country OR industrial_strength > 40).
    2. For each valid (country, sector) pair:
       a. Local market size:
          - global_market_size × country_share_estimate.
          - Validate with local industry data if available.
       b. Growth rate:
          - Global CAGR adjusted for local economic growth rate.
       c. Local competition intensity:
          - Number of local manufacturers / importers.
          - Presence of dominant incumbents (0-100 scale).
       d. Import dependency:
          - What % of equipment in this sector is imported?
          - Higher import dependency = better for AGE (we're an exporter).
       e. Key local players:
          - Companies in this country, in this sector.
          - These are potential customers!
       f. Demand drivers:
          - Why would companies in this country+sector buy new equipment?
          - Population growth, export demands, regulation changes,
            aging equipment fleet, new product launches.
       g. Risks:
          - Currency volatility, political instability, payment risk.
       h. Opportunity score:
          - local_market_size_weight(0.3) +
            growth_rate_weight(0.2) +
            import_dependency_weight(0.2) +
            competition_intensity_inverse_weight(0.15) +
            risk_inverse_weight(0.15)
    3. Sort by opportunity_score descending.
    4. Return list[CountryMarketEntry].

    Research methodology
    --------------------
    - National statistics offices for local production data.
    - UN Comtrade for import/export of packaging machinery (HS 8422).
    - Local industry associations.
    - World Bank for macro indicators.

    Quality gates
    -------------
    - Every entry must have local_market_size_usd > 0.
    - At least 3 demand_drivers per entry.
    - Entries with no local data → confidence = LOW.

    Subscribers
    -----------
    → MarketProblemAnalyzer, CompanyDiscoveryAgent, PricingStrategist
    """

    name = "country_market_analyzer"
    description = "Builds country × sector opportunity matrix with local market intelligence."
    phase = PhaseID.DEEP_RESEARCH
    dependencies = [
        Dependency(agent_name="sector_deep_researcher", required=True, data_keys=["sector_profiles"]),
        Dependency(agent_name="region_ranker", required=True, data_keys=["ranked_regions"]),
    ]
    output_keys = ["country_market_matrix"]
    subscribers = ["market_problem_analyzer", "company_discovery", "pricing_strategist"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load sector_profiles and ranked_regions
        2. Build valid (country, sector) pairs
        3. For each pair:
           a. Estimate local_market_size_usd
           b. Adjust growth_rate for local conditions
           c. Assess local_competition_intensity
           d. Estimate import_dependency (% imported equipment)
           e. List key_local_players
           f. Identify demand_drivers
           g. Assess risks
           h. Compute opportunity_score (weighted formula)
        4. Sort by opportunity_score descending
        5. Validate quality gates
        6. Return AgentOutput with country_market_matrix
        """

        sector_profiles = self._get_dep(context, "sector_deep_researcher", "sector_profiles") or []
        ranked_regions = self._get_dep(context, "region_ranker", "ranked_regions") or []
        country_market_matrix: list[dict] = []

        return self._make_output(
            data={"country_market_matrix": country_market_matrix},
            confidence=ConfidenceLevel.MEDIUM,
            sources=["un_comtrade", "national_statistics", "world_bank"],
        )


# =====================================================================
# 9. MARKET PROBLEM ANALYZER
# =====================================================================
class MarketProblemAnalyzer(BaseAgent):
    """
    Digs deep into the PROBLEMS that companies face in each sector/country,
    and maps which problems AGE can solve.

    This is where we find the "pain" that drives purchasing decisions.

    Inputs
    ------
    - sector_deep_researcher.sector_profiles   (sector-level problems)
    - country_market_analyzer.country_market_matrix  (country context)
    - product_analyzer.product_profiles        (what we can solve)
    - capability_mapper.capabilities           (how well we solve it)

    Outputs
    -------
    - market_problems : list[MarketProblem]

    Algorithm
    ---------
    1. Start with sector-level main_problems from SectorDeepResearcher.
    2. For each problem, localize to countries:
       a. Is this problem worse in certain countries?
          - e.g., "labor shortage" is worse in Germany/Japan than India.
          - e.g., "sustainability regulation" is stronger in EU than MENA.
       b. Create country-specific variants of global problems.
    3. Research ADDITIONAL country-specific problems:
       a. Search: "[country] [sector] industry challenges"
       b. Search: "[country] food safety issues" (for food sectors)
       c. Search: "[country] packaging equipment problems"
       d. Identify problems unique to that country:
          - Infrastructure issues (power reliability, water quality)
          - Local regulation (halal certification for MENA, etc.)
          - Supply chain issues (distance from spare parts)
    4. For each problem:
       a. Assess severity (0-100):
          - 90-100: Critical, forces immediate action (regulatory deadline).
          - 70-89:  Major, significant cost/risk impact.
          - 50-69:  Moderate, nice to solve but not urgent.
          - 30-49:  Minor, optimization opportunity.
          - 0-29:   Low, awareness-level.
       b. Estimate affected_companies_count from market data.
       c. List current_solutions (what are they doing now?).
       d. Identify solution_gaps (what's missing from current solutions?).
       e. Evaluate: Can AGE solve this?
          - Match problem against product features + capabilities.
          - If yes → age_can_solve = True, write age_solution_description.
    5. Prioritize problems AGE can solve with highest severity first.
    6. Return list[MarketProblem].

    Research methodology
    --------------------
    - Industry forums and complaint threads.
    - Trade publication articles about sector challenges.
    - Company annual reports mentioning "challenges" or "risks".
    - Direct observation from trade shows.
    - Regulatory body announcements.

    Quality gates
    -------------
    - At least 10 problems where age_can_solve = True.
    - Every problem must have severity > 0 and description non-empty.
    - If age_can_solve = True, age_solution_description must be non-empty.

    Subscribers
    -----------
    → NeedAnalyzer, OpportunityScorer, ProposalGenerator
    """

    name = "market_problem_analyzer"
    description = "Deep-dives into market problems per sector/country and maps AGE solutions."
    phase = PhaseID.DEEP_RESEARCH
    dependencies = [
        Dependency(agent_name="sector_deep_researcher", required=True, data_keys=["sector_profiles"]),
        Dependency(agent_name="country_market_analyzer", required=True, data_keys=["country_market_matrix"]),
        Dependency(agent_name="product_analyzer", required=True, data_keys=["product_profiles"]),
        Dependency(agent_name="capability_mapper", required=True, data_keys=["capabilities"]),
    ]
    output_keys = ["market_problems"]
    subscribers = ["need_analyzer", "opportunity_scorer", "proposal_generator"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load sector_profiles → extract main_problems per sector
        2. Load country_market_matrix → get country context
        3. Load product_profiles + capabilities → solution matching
        4. For each sector.main_problem:
           a. Create global MarketProblem entry
           b. Localize to each relevant country:
              - Adjust severity based on local conditions
              - Add country-specific notes
        5. Research additional country-specific problems:
           a. Search for local industry challenges
           b. Search for local regulation-driven problems
           c. Search for infrastructure problems
        6. For each problem:
           a. Score severity (0-100)
           b. Count affected companies
           c. List current solutions
           d. Identify solution gaps
           e. Match against AGE products → age_can_solve
           f. If solvable → write age_solution_description
        7. Sort: age_can_solve=True first, then by severity desc
        8. Validate quality gates
        9. Return AgentOutput with market_problems
        """

        sector_profiles = self._get_dep(context, "sector_deep_researcher", "sector_profiles") or []
        country_market_matrix = self._get_dep(context, "country_market_analyzer", "country_market_matrix") or []
        product_profiles = self._get_dep(context, "product_analyzer", "product_profiles") or []
        capabilities = self._get_dep(context, "capability_mapper", "capabilities") or []
        market_problems: list[dict] = []

        return self._make_output(
            data={"market_problems": market_problems},
            confidence=ConfidenceLevel.MEDIUM,
            sources=["industry_publications", "regulatory_bodies", "trade_forums"],
        )


# =====================================================================
# 10. TRADE SHOW RESEARCHER
# =====================================================================
class TradeShowResearcher(BaseAgent):
    """
    Researches relevant trade shows, exhibitions, and industry events
    to find:
    (a) events AGE should attend/exhibit at, and
    (b) companies that exhibit there (= potential customers).

    This agent is a powerful company discovery channel because
    exhibitors at sector-specific trade shows are EXACTLY the kind
    of companies that buy packaging equipment.

    Inputs
    ------
    - sector_deep_researcher.sector_profiles
    - region_ranker.ranked_regions

    Outputs
    -------
    - trade_shows : list[TradeShow]

    Algorithm
    ---------
    1. For each sector in sector_profiles:
       a. Search for global trade shows:
          - "[sector] trade show exhibition [year]"
          - "[sector] expo packaging machinery"
       b. Known key shows database:
          - interpack (Düsseldorf) — packaging general
          - IFFA (Frankfurt) — meat processing
          - Anuga FoodTec (Cologne) — food technology
          - ProPak (various cities) — processing & packaging
          - PACK EXPO (Chicago/Las Vegas) — North America
          - Gulfood Manufacturing (Dubai) — MENA region
          - China International Packaging Exhibition
          - Anutec (India) — Indian food processing
          - FachPack (Nuremberg) — European packaging
          - PPMA Show (Birmingham) — UK processing/packaging
          - Seoul Food (Korea) — Asian food industry
          - Djazagro (Algiers) — North Africa food
       c. For each found show:
          - name, sector, country, city, frequency
          - next_date (when is the next edition?)
          - website
          - estimated_exhibitors and estimated_visitors
    2. For each show in top regions (ranked_regions Tier 1-2):
       a. Scrape exhibitor list (if publicly available):
          - Search: "[show name] exhibitor list [year]"
          - Many shows publish exhibitor directories online.
       b. Categorize exhibitors:
          - Packaging machine manufacturers (= competitors)
          - Food/pharma/cosmetics producers (= customers!)
          - Ingredient/material suppliers (= not relevant)
       c. Extract companies that are CUSTOMERS (not competitors):
          - Add to known_exhibitors list.
    3. Score relevance:
       relevance_score =
         (sector_match × 0.4) +
         (region_match × 0.3) +
         (exhibitor_count × 0.2) +
         (recency × 0.1)
    4. Return list[TradeShow] sorted by relevance_score.

    Research methodology
    --------------------
    - Trade show databases: 10times.com, eventseye.com, tradefairdates.com
    - Individual show websites for exhibitor lists.
    - Industry association event calendars.
    - Past years' exhibitor PDFs/databases.

    Quality gates
    -------------
    - At least 5 relevant trade shows found.
    - At least 3 shows with known_exhibitors > 0.
    - Each show must have next_date filled.

    Subscribers
    -----------
    → CompanyDiscoveryAgent (feeds exhibitor companies into the funnel)
    """

    name = "trade_show_researcher"
    description = "Researches sector trade shows and extracts exhibitor lists for company discovery."
    phase = PhaseID.DEEP_RESEARCH
    dependencies = [
        Dependency(agent_name="sector_deep_researcher", required=True, data_keys=["sector_profiles"]),
        Dependency(agent_name="region_ranker", required=True, data_keys=["ranked_regions"]),
    ]
    output_keys = ["trade_shows"]
    subscribers = ["company_discovery"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load sector_profiles → list of sectors
        2. Load ranked_regions → priority countries
        3. For each sector:
           a. Search for relevant trade shows globally
           b. Check known shows database for matches
           c. For each found show:
              - Gather metadata (name, city, dates, size)
              - Check if it's in a priority region
        4. For top-relevance shows:
           a. Search for exhibitor lists
           b. Parse exhibitor directories
           c. Categorize: customer vs competitor vs supplier
           d. Extract customer companies → known_exhibitors
        5. Compute relevance_score for each show
        6. Sort by relevance_score descending
        7. Validate quality gates
        8. Return AgentOutput with trade_shows
        """

        sector_profiles = self._get_dep(context, "sector_deep_researcher", "sector_profiles") or []
        ranked_regions = self._get_dep(context, "region_ranker", "ranked_regions") or []
        trade_shows: list[dict] = []

        return self._make_output(
            data={"trade_shows": trade_shows},
            confidence=ConfidenceLevel.MEDIUM,
            sources=["trade_show_databases", "exhibitor_directories", "industry_associations"],
        )
