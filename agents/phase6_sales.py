"""
Phase 6 — Sales & Proposal  (4 agents)
========================================
ProposalGenerator  →  PricingStrategist  →  ROICalculator  →  SalesPlaybookGenerator

The final phase: produce everything the sales team needs to
close deals — proposals, pricing, ROI models, and complete playbooks.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, Dependency
from .models import (
    AgentOutput,
    ConfidenceLevel,
    PhaseID,
    PricingStrategy,
    Proposal,
    ROIModel,
    SalesPlaybook,
)


# =====================================================================
# 30. PROPOSAL GENERATOR
# =====================================================================
class ProposalGenerator(BaseAgent):
    """
    Generates tailored proposals for high-priority opportunities.

    Inputs
    ------
    - opportunity_scorer.scored_opportunities
    - gap_detector.gap_map
    - usp_extractor.usps
    - market_positioner.positioning_map
    - company_profiler.company_profiles
    - market_problem_analyzer.market_problems

    Outputs
    -------
    - proposals : dict[company_id, Proposal]

    Algorithm
    ---------
    1. Filter scored_opportunities to CRITICAL and HIGH priority.
    2. For each opportunity:

       a. EXECUTIVE SUMMARY:
          - 2-3 sentences capturing:
            · The company's key challenge.
            · How AGE uniquely solves it.
            · Expected outcome / value.
          - Written from the buyer's perspective.

       b. PROBLEM STATEMENT:
          - Draw from gap_map: what specific needs/gaps exist?
          - Draw from market_problems: what sector-level challenges?
          - Quantify the cost of NOT solving:
            · Production downtime costs.
            · Compliance risk penalties.
            · Lost market opportunity.

       c. PROPOSED SOLUTION:
          - Which AGE products address the gaps?
          - Technical fit description.
          - Customization notes (if any modifications needed).
          - Implementation approach:
            · Phase 1: Assessment & design.
            · Phase 2: Manufacturing & testing.
            · Phase 3: Installation & commissioning.
            · Phase 4: Training & handover.
            · Phase 5: After-sales support.

       d. PRODUCTS INCLUDED:
          - List of specific AGE machines/systems.
          - Key specs relevant to this customer.
          - Capacity/throughput projections.

       e. PRICING SUMMARY (placeholder):
          - Will be filled by PricingStrategist.
          - Structure: equipment + installation + training + service plan.

       f. ROI SUMMARY (placeholder):
          - Will be filled by ROICalculator.

       g. TIMELINE:
          - Order to delivery estimate.
          - Installation schedule.
          - Full production ramp-up.

       h. TERMS:
          - Payment milestones.
          - Warranty terms.
          - Service level agreement.

    3. Return dict[company_id → Proposal].

    Quality gates
    -------------
    - Every CRITICAL opportunity has a proposal.
    - Every proposal has executive_summary, problem_statement, proposed_solution.
    - Proposals reference ≥ 2 company-specific data points.

    Subscribers
    -----------
    → PricingStrategist, ROICalculator, SalesPlaybookGenerator
    """

    name = "proposal_generator"
    description = "Generates tailored proposals for high-priority opportunities."
    phase = PhaseID.PHASE_6_SALES
    dependencies = [
        Dependency(agent_name="opportunity_scorer", required=True, data_keys=["scored_opportunities"]),
        Dependency(agent_name="gap_detector", required=True, data_keys=["gap_map"]),
        Dependency(agent_name="usp_extractor", required=True, data_keys=["usps"]),
        Dependency(agent_name="market_positioner", required=False, data_keys=["positioning_map"]),
        Dependency(agent_name="company_profiler", required=True, data_keys=["company_profiles"]),
        Dependency(agent_name="market_problem_analyzer", required=False, data_keys=["market_problems"]),
    ]
    output_keys = ["proposals"]
    subscribers = ["pricing_strategist", "roi_calculator", "sales_playbook_generator"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Filter scored_opportunities → CRITICAL + HIGH
        2. For each opportunity:
           a. Write executive_summary (company challenge → AGE solution → value)
           b. Write problem_statement (gaps + market problems + cost of inaction)
           c. Write proposed_solution (products + customization + implementation)
           d. List products_included with relevant specs
           e. Draft timeline
           f. Draft terms
        3. Leave pricing_summary and roi_summary as placeholders
        4. Validate quality gates
        5. Return AgentOutput with proposals
        """

        scored_opportunities = self._get_dep(context, "opportunity_scorer", "scored_opportunities") or []
        gap_map = self._get_dep(context, "gap_detector", "gap_map") or {}
        proposals: dict[str, dict] = {}

        return self._make_output(
            data={"proposals": proposals},
            confidence=ConfidenceLevel.HIGH,
        )


# =====================================================================
# 31. PRICING STRATEGIST
# =====================================================================
class PricingStrategist(BaseAgent):
    """
    Develops pricing strategies tailored to each opportunity.

    Inputs
    ------
    - competitor_analyzer.competitor_profiles  (competitor pricing)
    - financial_analyzer.financial_snapshots    (can they afford it?)
    - country_market_analyzer.country_market_matrix  (regional pricing context)
    - proposal_generator.proposals             (what we're proposing)
    - regulatory_analyzer.regulatory_map       (tariffs affect pricing)

    Outputs
    -------
    - pricing_strategies : dict[company_id, PricingStrategy]

    Algorithm
    ---------
    1. For each proposal:

       a. DETERMINE STRATEGY TYPE:
          - Value-based: If our solution is unique (high match_quality,
            no close competitor) → price based on value delivered.
          - Competitive: If strong competitor presence → price relative
            to competitors.
          - Penetration: If entering new market/region → price aggressively
            to win first references.
          - Cost-plus: Fallback — our cost + target margin.

       b. BASE PRICE CALCULATION:
          - Start from AGE's list price for included products.
          - Adjust for customization: +10-30% for custom work.
          - Adjust for volume: -5-15% for multi-machine orders.

       c. REGIONAL ADJUSTMENT:
          - Import tariffs from regulatory_map.
          - Shipping costs (based on distance).
          - Currency considerations.
          - Local labor costs for installation.

       d. COMPETITIVE ADJUSTMENT:
          - If competitor prices known:
            · Premium position: price at 100-120% of competitor.
            · Parity position: match within ±5%.
            · Value position: price at 80-95% of competitor.
          - Choice based on our positioning_map advantage.

       e. DISCOUNT RATIONALE:
          - Early adopter discount (first in region): -5-10%.
          - Reference customer discount (agree to case study): -3-5%.
          - Multi-year service contract: -5% on equipment.
          - Trade show special: -5% if ordered at show.

       f. BUNDLING OPTIONS:
          - Equipment + installation + training: -5% vs. separate.
          - Equipment + 3-year service plan: -8% vs. separate.
          - Full line (multiple machines): -10-15% vs. individual.

       g. PAYMENT TERMS:
          - Standard: 30% advance, 30% on delivery, 40% on commissioning.
          - Flexible: milestone-based for large projects.
          - Financing options: leasing, equipment financing.

    2. Return dict[company_id → PricingStrategy].

    Quality gates
    -------------
    - Every proposal must have a pricing strategy.
    - strategy_type must be justified.
    - base_price must be > 0.

    Subscribers
    -----------
    → ROICalculator, SalesPlaybookGenerator
    """

    name = "pricing_strategist"
    description = "Develops tailored pricing strategies considering competition, region, and value."
    phase = PhaseID.PHASE_6_SALES
    dependencies = [
        Dependency(agent_name="competitor_analyzer", required=False, data_keys=["competitor_profiles"]),
        Dependency(agent_name="financial_analyzer", required=False, data_keys=["financial_snapshots"]),
        Dependency(agent_name="country_market_analyzer", required=False, data_keys=["country_market_matrix"]),
        Dependency(agent_name="proposal_generator", required=True, data_keys=["proposals"]),
        Dependency(agent_name="regulatory_analyzer", required=False, data_keys=["regulatory_map"]),
    ]
    output_keys = ["pricing_strategies"]
    subscribers = ["roi_calculator", "sales_playbook_generator"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load proposals, competitor pricing, financials, market data, tariffs
        2. For each proposal:
           a. Determine strategy type (value/competitive/penetration/cost-plus)
           b. Calculate base price (list price + customization + volume)
           c. Apply regional adjustments (tariffs, shipping, currency)
           d. Apply competitive adjustments
           e. Design discount rationale
           f. Create bundling options
           g. Set payment terms
        3. Validate quality gates
        4. Return AgentOutput with pricing_strategies
        """

        proposals = self._get_dep(context, "proposal_generator", "proposals") or {}
        pricing_strategies: dict[str, dict] = {}

        return self._make_output(
            data={"pricing_strategies": pricing_strategies},
            confidence=ConfidenceLevel.MEDIUM,
        )


# =====================================================================
# 32. ROI CALCULATOR
# =====================================================================
class ROICalculator(BaseAgent):
    """
    Builds ROI models that quantify the financial benefit of buying
    AGE equipment — a key tool for justifying the investment.

    Inputs
    ------
    - gap_detector.gap_map              (what problems we solve)
    - pricing_strategist.pricing_strategies  (what it costs)
    - market_problem_analyzer.market_problems  (problem severity/cost)
    - company_profiler.company_profiles       (company context)

    Outputs
    -------
    - roi_models : dict[company_id, ROIModel]

    Algorithm
    ---------
    1. For each priced proposal:

       a. INVESTMENT CALCULATION:
          - Equipment cost from pricing_strategy.
          - Installation cost.
          - Training cost.
          - First-year service cost.
          - Total investment = sum of above.

       b. ANNUAL SAVINGS ESTIMATION:
          - Labor savings:
            · If replacing manual process: saved_operators × annual_wage.
            · If increasing speed: additional_output × margin_per_unit.
          - Waste reduction:
            · Current waste % - AGE machine waste % = saved material cost.
          - Downtime reduction:
            · Old machine downtime hours × hourly_production_value.
          - Energy savings:
            · New machine kW vs old machine kW × operating_hours × energy_cost.
          - Compliance savings:
            · Avoided fines or market-access gained.

       c. PAYBACK PERIOD:
          - payback_months = (investment / annual_savings) × 12.

       d. 5-YEAR ROI:
          - Total benefit = annual_savings × 5.
          - five_year_roi = ((Total benefit - investment) / investment) × 100.

       e. ASSUMPTIONS:
          - List all assumptions made:
            · "Operating 250 days/year, 16 hours/day"
            · "Current waste rate: 5%, AGE machine: 1.5%"
            · "Energy cost: €0.15/kWh"

       f. SENSITIVITY ANALYSIS:
          - Optimistic scenario: savings +20% → ROI.
          - Base scenario: as calculated.
          - Conservative scenario: savings -20% → ROI.
          - Break-even: what's the minimum savings for positive ROI?

    2. Return dict[company_id → ROIModel].

    Quality gates
    -------------
    - Every priced proposal has an ROI model.
    - payback_months must be calculated.
    - At least 3 assumptions per model.
    - Sensitivity analysis with ≥ 2 scenarios.

    Subscribers
    -----------
    → SalesPlaybookGenerator, ProposalGenerator (backfill)
    """

    name = "roi_calculator"
    description = "Builds financial ROI models with sensitivity analysis for each opportunity."
    phase = PhaseID.PHASE_6_SALES
    dependencies = [
        Dependency(agent_name="gap_detector", required=True, data_keys=["gap_map"]),
        Dependency(agent_name="pricing_strategist", required=True, data_keys=["pricing_strategies"]),
        Dependency(agent_name="market_problem_analyzer", required=False, data_keys=["market_problems"]),
        Dependency(agent_name="company_profiler", required=False, data_keys=["company_profiles"]),
    ]
    output_keys = ["roi_models"]
    subscribers = ["sales_playbook_generator"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load gap_map, pricing_strategies, market_problems, company_profiles
        2. For each priced proposal:
           a. Calculate total investment
           b. Estimate annual savings by category
           c. Calculate payback period
           d. Calculate 5-year ROI
           e. List assumptions
           f. Run sensitivity analysis (optimistic, base, conservative)
        3. Validate quality gates
        4. Return AgentOutput with roi_models
        """

        pricing_strategies = self._get_dep(context, "pricing_strategist", "pricing_strategies") or {}
        gap_map = self._get_dep(context, "gap_detector", "gap_map") or {}
        roi_models: dict[str, dict] = {}

        return self._make_output(
            data={"roi_models": roi_models},
            confidence=ConfidenceLevel.MEDIUM,
        )


# =====================================================================
# 33. SALES PLAYBOOK GENERATOR
# =====================================================================
class SalesPlaybookGenerator(BaseAgent):
    """
    The FINAL agent.  Produces a complete sales playbook per company
    that a sales representative can pick up and use immediately.

    This playbook is the culmination of ALL previous agents' work,
    synthesized into an actionable document.

    Inputs
    ------
    - proposal_generator.proposals
    - pricing_strategist.pricing_strategies
    - roi_calculator.roi_models
    - win_loss_analyzer.win_loss_patterns
    - outreach_composer.outreach_messages
    - company_profiler.company_profiles
    - company_deep_researcher.company_deep_intel
    - gap_detector.gap_map
    - market_positioner.positioning_map
    - contact_finder.contacts
    - campaign_planner.campaign_plans

    Outputs
    -------
    - playbooks : dict[company_id, SalesPlaybook]

    Algorithm
    ---------
    1. For each CRITICAL/HIGH opportunity:

       a. EXECUTIVE SUMMARY (2-3 sentences):
          - Who is this company?
          - Why are they a high-priority target?
          - What's our best angle of approach?

       b. COMPANY CONTEXT:
          - Industry, size, location.
          - Recent news and developments.
          - Financial health summary.
          - Key facts from deep research (founders, history, culture).

       c. KEY PAIN POINTS (prioritized list):
          - From gap_map and market_problems.
          - Each pain point with evidence source.
          - Urgency indicator.

       d. OUR SOLUTION FIT:
          - Which AGE products/capabilities address each pain point.
          - Match quality per gap.
          - Customization requirements.

       e. COMPETITIVE POSITIONING:
          - Who are we competing against for this deal?
          - Our advantages vs. each competitor.
          - Battle card summary from MarketPositioner.
          - Win factors to emphasize.
          - Loss factors to prepare for.

       f. OBJECTION HANDLERS:
          - Anticipated objections and pre-written responses:
            · "Too expensive" → ROI data + value justification.
            · "We already have a supplier" → switching cost analysis.
            · "Turkish supplier risk" → reference list + certifications.
            · "Don't know your brand" → case studies + trade show presence.
            · "Need local support" → service network details.
          - Derived from win_loss_patterns loss factors.

       g. PRICING GUIDANCE:
          - Recommended price range.
          - Discount authority levels.
          - Bundling recommendations.
          - Payment term flexibility.

       h. DECISION MAKERS:
          - Key contacts with role and influence.
          - Recommended approach for each person.
          - Warm introduction paths (if available).

       i. RECOMMENDED APPROACH:
          - Best first contact method.
          - Meeting request strategy.
          - Demo/pilot offering.
          - Reference customer to mention.

       j. MEETING AGENDA (for first meeting):
          - Opening: rapport building (use deep research facts).
          - Discovery: confirm our intelligence, learn more.
          - Present: address 1-2 key pain points.
          - Next steps: agree on technical assessment / factory visit.

       k. FOLLOW-UP CADENCE:
          - Post-meeting: thank you + materials.
          - Week 2: technical proposal.
          - Week 4: follow-up call.
          - Week 6: site visit invitation.
          - Week 8: formal proposal.

    2. Return dict[company_id → SalesPlaybook].

    Quality gates
    -------------
    - Every CRITICAL opportunity has a playbook.
    - Playbook must have all sections filled.
    - Objection handlers: ≥ 3 objections handled.
    - Decision makers: ≥ 1 person listed.

    Subscribers
    -----------
    → None (this is the terminal output).
    """

    name = "sales_playbook_generator"
    description = "Produces complete, actionable sales playbooks per company — the final deliverable."
    phase = PhaseID.PHASE_6_SALES
    dependencies = [
        Dependency(agent_name="proposal_generator", required=True, data_keys=["proposals"]),
        Dependency(agent_name="pricing_strategist", required=True, data_keys=["pricing_strategies"]),
        Dependency(agent_name="roi_calculator", required=True, data_keys=["roi_models"]),
        Dependency(agent_name="win_loss_analyzer", required=False, data_keys=["win_loss_patterns"]),
        Dependency(agent_name="outreach_composer", required=True, data_keys=["outreach_messages"]),
        Dependency(agent_name="company_profiler", required=True, data_keys=["company_profiles"]),
        Dependency(agent_name="company_deep_researcher", required=False, data_keys=["company_deep_intel"]),
        Dependency(agent_name="gap_detector", required=True, data_keys=["gap_map"]),
        Dependency(agent_name="market_positioner", required=False, data_keys=["positioning_map"]),
        Dependency(agent_name="contact_finder", required=True, data_keys=["contacts"]),
        Dependency(agent_name="campaign_planner", required=False, data_keys=["campaign_plans"]),
    ]
    output_keys = ["playbooks"]
    subscribers = []  # TERMINAL — no downstream agents

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load ALL dependency data
        2. Filter to CRITICAL/HIGH opportunities
        3. For each opportunity:
           a. Write executive_summary
           b. Write company_context (profile + deep intel)
           c. List key_pain_points from gaps
           d. Describe our_solution_fit
           e. Build competitive_positioning (battle cards)
           f. Write objection_handlers (≥3 objections)
           g. Summarize pricing_guidance
           h. List decision_makers with approach recommendations
           i. Write recommended_approach
           j. Draft meeting_agenda
           k. Define follow_up_cadence
        4. Validate quality gates
        5. Return AgentOutput with playbooks
        """

        proposals = self._get_dep(context, "proposal_generator", "proposals") or {}
        pricing_strategies = self._get_dep(context, "pricing_strategist", "pricing_strategies") or {}
        roi_models = self._get_dep(context, "roi_calculator", "roi_models") or {}
        playbooks: dict[str, dict] = {}

        return self._make_output(
            data={"playbooks": playbooks},
            confidence=ConfidenceLevel.HIGH,
        )
