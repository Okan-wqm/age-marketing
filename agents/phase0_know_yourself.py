"""
Phase 0 — Know Yourself  (3 agents)
=====================================
ProductAnalyzer  →  CapabilityMapper  →  USPExtractor

These agents introspect AGE's own products, capabilities, and unique
selling propositions BEFORE looking outward.  Every subsequent phase
depends on their output.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, Dependency
from .models import (
    AgentOutput,
    Capability,
    ConfidenceLevel,
    PhaseID,
    ProductProfile,
    USP,
)


# =====================================================================
# 1. PRODUCT ANALYZER
# =====================================================================
class ProductAnalyzer(BaseAgent):
    """
    Builds a structured profile of every AGE product / product-line.

    Inputs
    ------
    - context["input"]["product_catalog"]   (raw catalog data or URL)
    - context["input"]["technical_docs"]    (spec sheets, optional)

    Outputs
    -------
    - product_profiles : list[ProductProfile]

    Algorithm
    ---------
    1. Ingest raw product catalog (PDF, CSV, URL, or manual JSON).
    2. For each product:
       a. Extract name, category, sub_category.
       b. Parse technical specifications → dict (speed, dimensions, power,
          materials, output capacity).
       c. Identify target industries from description + spec context.
          - Use keyword mapping: "dairy" → Dairy Processing,
            "pharma" → Pharmaceutical Packaging, etc.
       d. Extract certifications (CE, FDA, ATEX, etc.).
       e. Determine price range (if available) or flag as "needs_input".
       f. Estimate production capacity from specs.
       g. Set lead_time_days from catalog or default.
    3. Cross-reference products to find product families
       (e.g., TFS-200 / TFS-400 / TFS-600 are one family with scale variants).
    4. Tag each product with an internal product_id (slug form).
    5. Return list[ProductProfile].

    Quality gates
    -------------
    - Every product MUST have ≥1 target_industry.
    - Every product MUST have ≥3 key_features.
    - If either check fails → confidence = LOW + warning.

    Subscribers
    -----------
    → CapabilityMapper, USPExtractor, RegionScanner,
      SectorDeepResearcher, CompanyDiscoveryAgent
    """

    name = "product_analyzer"
    description = "Parses AGE product catalog into structured ProductProfile objects."
    phase = PhaseID.PHASE_0_KNOW_YOURSELF
    dependencies = []  # first agent — no deps
    output_keys = ["product_profiles"]
    subscribers = [
        "capability_mapper",
        "usp_extractor",
        "region_scanner",
        "sector_deep_researcher",
        "company_discovery",
    ]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Read context["input"]["product_catalog"]
        2. Detect format (PDF / CSV / JSON / URL)
        3. Parse into raw records
        4. For each record → build ProductProfile:
           a. name, category, sub_category from record
           b. key_features = extract_features(record["description"])
           c. technical_specs = parse_specs(record)
           d. target_industries = infer_industries(record)
           e. certifications = extract_certs(record)
           f. price_range = parse_price(record)  # may be empty
           g. production_capacity = parse_capacity(record)
           h. lead_time_days = parse_lead_time(record)  # default 90
        5. Group into product families by prefix similarity
        6. Validate quality gates:
           - if len(p.target_industries) == 0 → warning
           - if len(p.key_features) < 3 → warning
        7. Set confidence based on data completeness
        8. Return AgentOutput with product_profiles
        """

        raw_catalog = context.get("input", {}).get("product_catalog", [])
        profiles: list[dict] = []

        # (Actual implementation will parse real data here)

        return self._make_output(
            data={"product_profiles": profiles},
            confidence=ConfidenceLevel.HIGH,
        )


# =====================================================================
# 2. CAPABILITY MAPPER
# =====================================================================
class CapabilityMapper(BaseAgent):
    """
    Maps AGE's organizational capabilities beyond just products.

    Inputs
    ------
    - product_analyzer.product_profiles
    - context["input"]["company_info"]   (optional extra info about AGE)

    Outputs
    -------
    - capabilities : list[Capability]

    Algorithm
    ---------
    1. Start from product_profiles → extract implied capabilities:
       a. If products include TFS machines → capability "Thermoform-Fill-Seal Engineering"
       b. If products span multiple material types → "Multi-Material Processing"
       c. If certifications include FDA → "FDA-Compliant Design"
    2. Enrich from company_info (if provided):
       a. R&D team size → R&D capability level
       b. Manufacturing facilities → production capability
       c. Service network → after-sales capability
       d. Export history → international logistics capability
    3. Rate each capability:
       - world-class: best-in-industry evidence
       - advanced: above average, proven track record
       - competent: meets expectations
    4. Link capabilities to relevant products via related_products[].
    5. Identify capability clusters:
       - "End-to-end packaging solutions" (design + build + install + service)
       - "Hygienic design expertise" (if multiple cleanroom/food-grade products)
    6. Return list[Capability].

    Quality gates
    -------------
    - At least 5 capabilities identified, else confidence = LOW.
    - Each capability must have ≥1 evidence item.

    Subscribers
    -----------
    → USPExtractor, GapDetector
    """

    name = "capability_mapper"
    description = "Maps AGE organizational capabilities from products and company info."
    phase = PhaseID.PHASE_0_KNOW_YOURSELF
    dependencies = [
        Dependency(agent_name="product_analyzer", required=True, data_keys=["product_profiles"]),
    ]
    output_keys = ["capabilities"]
    subscribers = ["usp_extractor", "gap_detector"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load product_profiles from context
        2. capability_candidates = []
        3. For each product:
           a. Infer engineering capability from product category
           b. Infer material capability from specs
           c. Infer compliance capability from certifications
        4. Load company_info (optional):
           a. Add R&D capability (team size, patents)
           b. Add manufacturing capability (facility count, ISO)
           c. Add service capability (network reach, SLA)
           d. Add logistics/export capability
        5. Deduplicate similar capabilities
        6. Rate each: world-class / advanced / competent
        7. Validate quality gates
        8. Return AgentOutput with capabilities
        """

        product_profiles = self._get_dep(context, "product_analyzer", "product_profiles") or []
        capabilities: list[dict] = []

        return self._make_output(
            data={"capabilities": capabilities},
            confidence=ConfidenceLevel.HIGH,
        )


# =====================================================================
# 3. USP EXTRACTOR
# =====================================================================
class USPExtractor(BaseAgent):
    """
    Distills AGE's Unique Selling Propositions from products + capabilities.

    Inputs
    ------
    - product_analyzer.product_profiles
    - capability_mapper.capabilities

    Outputs
    -------
    - usps : list[USP]

    Algorithm
    ---------
    1. Cross-reference products × capabilities to find differentiators:
       a. Capabilities that are "world-class" → strong USP candidates.
       b. Product features that appear rarely in the market → USP candidates.
    2. For each USP candidate:
       a. Write a one-liner statement.
       b. Write buyer-facing explanation ("this matters because…").
       c. Link to supporting capabilities.
       d. Draft a "vs_competitors" differentiation note.
    3. Rank USPs by impact:
       - High impact: solves a known, widespread buyer pain point.
       - Medium impact: differentiates but not mission-critical.
       - Low impact: nice-to-have.
    4. Select top 5-8 USPs (avoid dilution).
    5. Return list[USP].

    Quality gates
    -------------
    - Minimum 3 USPs, else confidence = LOW.
    - Every USP must have ≥1 supporting_capability.

    Subscribers
    -----------
    → GapDetector, OutreachComposer, MarketPositioner, ProposalGenerator
    """

    name = "usp_extractor"
    description = "Distills top unique selling propositions from products and capabilities."
    phase = PhaseID.PHASE_0_KNOW_YOURSELF
    dependencies = [
        Dependency(agent_name="product_analyzer", required=True, data_keys=["product_profiles"]),
        Dependency(agent_name="capability_mapper", required=True, data_keys=["capabilities"]),
    ]
    output_keys = ["usps"]
    subscribers = ["gap_detector", "outreach_composer", "market_positioner", "proposal_generator"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load product_profiles and capabilities
        2. Find world-class capabilities → primary USP candidates
        3. Find unique product features (rare in market) → secondary USP candidates
        4. For each candidate:
           a. statement = synthesize_one_liner(capability, products)
           b. explanation = explain_buyer_value(statement)
           c. supporting_capabilities = link_capabilities(candidate)
           d. vs_competitors = draft_differentiation(candidate)
        5. Rank by buyer impact: high / medium / low
        6. Take top 5-8
        7. Validate quality gates
        8. Return AgentOutput with usps
        """

        product_profiles = self._get_dep(context, "product_analyzer", "product_profiles") or []
        capabilities = self._get_dep(context, "capability_mapper", "capabilities") or []
        usps: list[dict] = []

        return self._make_output(
            data={"usps": usps},
            confidence=ConfidenceLevel.HIGH,
        )
