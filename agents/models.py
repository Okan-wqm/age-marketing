"""
Shared data models used across all agents.
Every agent reads/writes these canonical structures so they can
interoperate without knowing each other's internals.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ── Enums ────────────────────────────────────────────────────────────

class PhaseID(Enum):
    PHASE_0_KNOW_YOURSELF = "phase_0"
    PHASE_1_REGION_DISCOVERY = "phase_1"
    DEEP_RESEARCH = "deep_research"
    PHASE_1_5_COMPANY_DISCOVERY = "phase_1_5"
    PHASE_2_COMPANY_INTEL = "phase_2"
    PHASE_3_GAP_ANALYSIS = "phase_3"
    PHASE_4_COMPETITOR_MARKET = "phase_4"
    PHASE_5_COMMUNICATION = "phase_5"
    PHASE_6_SALES = "phase_6"


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting_for_dependency"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ConfidenceLevel(Enum):
    VERY_HIGH = "very_high"      # >90 %
    HIGH = "high"                # 70-90 %
    MEDIUM = "medium"            # 50-70 %
    LOW = "low"                  # 30-50 %
    VERY_LOW = "very_low"        # <30 %


class Priority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


# ── Core envelope every agent produces ──────────────────────────────

@dataclass
class AgentOutput:
    """Canonical wrapper returned by every agent."""
    agent_id: str
    agent_name: str
    phase: PhaseID
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    data: dict[str, Any] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_agents: list[str] = field(default_factory=list)   # who should run next


# ── Phase 0 models ──────────────────────────────────────────────────

@dataclass
class ProductProfile:
    product_id: str
    name: str
    category: str                       # e.g. "packaging_machine"
    sub_category: str                   # e.g. "thermoform_fill_seal"
    description: str
    key_features: list[str] = field(default_factory=list)
    technical_specs: dict[str, str] = field(default_factory=dict)
    target_industries: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    price_range: dict[str, float] = field(default_factory=dict)  # min/max
    production_capacity: str = ""
    lead_time_days: int = 0


@dataclass
class Capability:
    capability_id: str
    name: str
    category: str               # engineering, manufacturing, service, R&D
    proficiency: str            # world-class / advanced / competent
    evidence: list[str] = field(default_factory=list)
    related_products: list[str] = field(default_factory=list)


@dataclass
class USP:
    usp_id: str
    statement: str              # one-liner
    explanation: str            # why this matters to buyer
    supporting_capabilities: list[str] = field(default_factory=list)
    vs_competitors: str = ""    # how we differ


# ── Phase 1 models ──────────────────────────────────────────────────

@dataclass
class RegionProfile:
    region_id: str
    country: str
    sub_region: str = ""                # e.g. "Bavaria" or "Midwest"
    gdp_usd: float = 0.0
    population: int = 0
    industrial_strength: float = 0.0    # 0-100 composite
    regulatory_complexity: float = 0.0  # 0-100 (higher = harder)
    ease_of_doing_business: float = 0.0
    relevant_sectors: list[str] = field(default_factory=list)
    language: str = ""
    currency: str = ""
    trade_agreements: list[str] = field(default_factory=list)
    opportunity_score: float = 0.0      # final weighted score


@dataclass
class RegulatoryInfo:
    region_id: str
    import_tariffs: dict[str, float] = field(default_factory=dict)
    required_certifications: list[str] = field(default_factory=list)
    local_standards: list[str] = field(default_factory=list)
    restrictions: list[str] = field(default_factory=list)
    incentives: list[str] = field(default_factory=list)
    notes: str = ""


# ── Deep Research models ────────────────────────────────────────────

@dataclass
class SectorProfile:
    sector_id: str
    name: str                           # e.g. "Dairy Processing"
    description: str
    global_market_size_usd: float = 0.0
    cagr_percent: float = 0.0           # compound annual growth rate
    top_countries: list[str] = field(default_factory=list)
    key_players: list[str] = field(default_factory=list)
    main_problems: list[str] = field(default_factory=list)
    technology_trends: list[str] = field(default_factory=list)
    regulatory_drivers: list[str] = field(default_factory=list)
    entry_barriers: list[str] = field(default_factory=list)
    age_relevance_score: float = 0.0    # how well AGE products fit


@dataclass
class CountryMarketEntry:
    country: str
    sector: str
    local_market_size_usd: float = 0.0
    growth_rate: float = 0.0
    local_competition_intensity: float = 0.0  # 0-100
    import_dependency: float = 0.0            # 0-100 %
    key_local_players: list[str] = field(default_factory=list)
    demand_drivers: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    opportunity_score: float = 0.0


@dataclass
class MarketProblem:
    problem_id: str
    sector: str
    country: str = ""                   # empty = global problem
    title: str = ""
    description: str = ""
    severity: float = 0.0               # 0-100
    affected_companies_count: int = 0
    current_solutions: list[str] = field(default_factory=list)
    solution_gaps: list[str] = field(default_factory=list)
    age_can_solve: bool = False
    age_solution_description: str = ""


@dataclass
class TradeShow:
    show_id: str
    name: str
    sector: str
    country: str
    city: str
    frequency: str                      # annual, biennial
    next_date: str = ""
    website: str = ""
    estimated_exhibitors: int = 0
    estimated_visitors: int = 0
    relevance_score: float = 0.0
    known_exhibitors: list[str] = field(default_factory=list)  # company names
    notes: str = ""


# ── Phase 1.5 / 2 — Company models ─────────────────────────────────

@dataclass
class CompanyProfile:
    company_id: str
    name: str
    country: str
    city: str = ""
    website: str = ""
    sector: str = ""
    sub_sector: str = ""
    employee_count: int = 0
    annual_revenue_usd: float = 0.0
    founded_year: int = 0
    ownership_type: str = ""            # public, private, family, PE-backed
    description: str = ""
    products_services: list[str] = field(default_factory=list)
    current_equipment: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    pain_points: list[str] = field(default_factory=list)
    discovery_source: str = ""          # how we found them
    validation_status: str = "unvalidated"
    fit_score: float = 0.0


@dataclass
class CompanyDeepIntel:
    """Deep research output about a company's origins, founders, network."""
    company_id: str
    founders: list[dict[str, str]] = field(default_factory=list)  # name, background
    key_executives: list[dict[str, str]] = field(default_factory=list)
    board_members: list[dict[str, str]] = field(default_factory=list)
    ownership_history: list[str] = field(default_factory=list)
    mergers_acquisitions: list[str] = field(default_factory=list)
    strategic_partnerships: list[str] = field(default_factory=list)
    investment_rounds: list[str] = field(default_factory=list)
    company_culture_notes: str = ""
    interesting_facts: list[str] = field(default_factory=list)
    potential_connections_to_age: list[str] = field(default_factory=list)
    news_sentiment: str = ""            # positive / neutral / negative


@dataclass
class FinancialSnapshot:
    company_id: str
    revenue_trend: list[dict[str, float]] = field(default_factory=list)  # year: amount
    profit_margin: float = 0.0
    debt_ratio: float = 0.0
    capex_trend: str = ""               # increasing / stable / decreasing
    recent_investments: list[str] = field(default_factory=list)
    financial_health: str = ""          # strong / moderate / weak
    budget_signals: list[str] = field(default_factory=list)


@dataclass
class TechStackEntry:
    company_id: str
    current_machines: list[str] = field(default_factory=list)
    machine_ages: dict[str, int] = field(default_factory=dict)   # machine: years
    software_systems: list[str] = field(default_factory=list)     # ERP, MES, etc.
    automation_level: str = ""          # manual / semi / full
    industry_4_0_readiness: float = 0.0  # 0-100
    known_suppliers: list[str] = field(default_factory=list)
    upgrade_signals: list[str] = field(default_factory=list)


# ── Phase 3 — Gap & Opportunity ─────────────────────────────────────

@dataclass
class CompanyNeed:
    company_id: str
    need_id: str
    category: str              # capacity, quality, efficiency, compliance, new_product
    description: str = ""
    urgency: float = 0.0       # 0-100
    evidence: list[str] = field(default_factory=list)


@dataclass
class GapEntry:
    gap_id: str
    company_id: str
    need_id: str
    our_capability_id: str
    gap_description: str = ""
    match_quality: float = 0.0   # 0-100
    required_customization: str = ""


@dataclass
class ScoredOpportunity:
    opportunity_id: str
    company_id: str
    gap_ids: list[str] = field(default_factory=list)
    total_score: float = 0.0
    revenue_potential_usd: float = 0.0
    win_probability: float = 0.0
    priority: Priority = Priority.MEDIUM
    reasoning: str = ""


# ── Phase 4 — Competitor models ─────────────────────────────────────

@dataclass
class CompetitorProfile:
    competitor_id: str
    name: str
    country: str
    products: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    market_share_estimate: float = 0.0
    pricing_strategy: str = ""
    key_customers: list[str] = field(default_factory=list)
    threat_level: float = 0.0  # 0-100


@dataclass
class PositioningEntry:
    dimension: str             # price, quality, service, innovation, etc.
    our_score: float = 0.0
    competitor_scores: dict[str, float] = field(default_factory=dict)
    our_advantage: bool = False
    narrative: str = ""


@dataclass
class WinLossPattern:
    pattern_id: str
    pattern_type: str          # "win_factor" or "loss_factor"
    description: str = ""
    frequency: float = 0.0     # how often this appears
    affected_competitors: list[str] = field(default_factory=list)
    recommended_action: str = ""


# ── Phase 5 — Contact & Communication ──────────────────────────────

@dataclass
class ContactInfo:
    contact_id: str
    company_id: str
    name: str
    title: str = ""
    department: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    role_in_decision: str = ""  # champion, decision_maker, influencer, gatekeeper
    preferred_language: str = ""
    notes: str = ""


@dataclass
class NetworkConnection:
    source_person: str
    target_person: str
    relationship_type: str = ""  # colleague, board_member, industry_peer, alumni
    strength: float = 0.0       # 0-100
    shared_context: str = ""     # "both on VDMA board"


@dataclass
class OutreachMessage:
    message_id: str
    contact_id: str
    channel: str = ""            # email, linkedin, phone, trade_show
    subject: str = ""
    body: str = ""
    personalization_notes: str = ""
    call_to_action: str = ""
    follow_up_plan: str = ""
    a_b_variant: str = ""        # "A" or "B"


@dataclass
class CampaignPlan:
    campaign_id: str
    target_companies: list[str] = field(default_factory=list)
    phases: list[dict[str, Any]] = field(default_factory=list)
    timeline_weeks: int = 0
    channels: list[str] = field(default_factory=list)
    kpis: dict[str, float] = field(default_factory=dict)


# ── Phase 6 — Sales & Proposal ──────────────────────────────────────

@dataclass
class Proposal:
    proposal_id: str
    company_id: str
    title: str = ""
    executive_summary: str = ""
    problem_statement: str = ""
    proposed_solution: str = ""
    products_included: list[str] = field(default_factory=list)
    customization_notes: str = ""
    pricing_summary: dict[str, float] = field(default_factory=dict)
    roi_summary: str = ""
    timeline: str = ""
    terms: str = ""


@dataclass
class PricingStrategy:
    company_id: str
    strategy_type: str = ""     # value-based, competitive, cost-plus, penetration
    base_price: float = 0.0
    discount_rationale: str = ""
    bundling_options: list[str] = field(default_factory=list)
    payment_terms: str = ""
    competitor_price_range: dict[str, float] = field(default_factory=dict)


@dataclass
class ROIModel:
    company_id: str
    investment_usd: float = 0.0
    annual_savings_usd: float = 0.0
    payback_months: int = 0
    five_year_roi_percent: float = 0.0
    assumptions: list[str] = field(default_factory=list)
    sensitivity_scenarios: dict[str, float] = field(default_factory=dict)


@dataclass
class SalesPlaybook:
    company_id: str
    executive_summary: str = ""
    company_context: str = ""
    key_pain_points: list[str] = field(default_factory=list)
    our_solution_fit: str = ""
    competitive_positioning: str = ""
    objection_handlers: dict[str, str] = field(default_factory=dict)
    pricing_guidance: str = ""
    decision_makers: list[str] = field(default_factory=list)
    recommended_approach: str = ""
    meeting_agenda: str = ""
    follow_up_cadence: str = ""
