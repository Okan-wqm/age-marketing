"""
Phase 2 — Company Intelligence  (5 agents)
=============================================
CompanyProfiler         — detailed company profiles
FinancialAnalyzer       — financial health assessment
TechStackAnalyzer       — current equipment & technology audit
CompanyDeepResearcher   — founders, history, network, connections
DecisionMakerProfiler   — key people who make purchasing decisions

These agents work on A-tier and B-tier ranked companies to build
intelligence dossiers used by Gap Analysis and Sales agents.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, Dependency
from .models import (
    AgentOutput,
    CompanyDeepIntel,
    CompanyProfile,
    ConfidenceLevel,
    ContactInfo,
    FinancialSnapshot,
    PhaseID,
    TechStackEntry,
)


# =====================================================================
# 14. COMPANY PROFILER
# =====================================================================
class CompanyProfiler(BaseAgent):
    """
    Builds detailed profiles for high-priority companies.

    Inputs
    ------
    - company_ranker.ranked_companies  (A and B tier only)

    Outputs
    -------
    - company_profiles : list[CompanyProfile]  (deeply enriched)

    Algorithm
    ---------
    1. Filter ranked_companies to A-tier and B-tier only.
    2. For each company:
       a. Website deep scrape:
          - Company description / about page.
          - Product/service pages → products_services list.
          - News / press releases → recent developments.
          - Careers page → growth signals (hiring = growing).
          - Contact page → locations, subsidiaries.
       b. Industry databases:
          - Search: "[company name] profile" on Kompass, D&B, Bloomberg.
          - Gather: SIC/NAICS codes, ownership_type, subsidiaries.
       c. News research:
          - Search: "[company name] news [last 12 months]"
          - Look for: expansion plans, new factories, new products,
            partnerships, management changes.
          - Sentiment analysis: positive/neutral/negative.
       d. Social media presence:
          - LinkedIn company page → employee count, growth trend.
          - Facebook/Instagram → B2C presence (relevant for consumer goods).
       e. Current equipment (if discoverable):
          - Search for photos/videos of their production lines.
          - Search: "[company name] packaging line equipment supplier"
          - Look at LinkedIn posts from their employees mentioning equipment.
       f. Pain points inference:
          - From news: mentions of "challenge", "problem", "shortage"
          - From careers: if hiring packaging engineers → likely upgrading
          - From industry context: map sector problems to this company
    3. Merge all data into enriched CompanyProfile.
    4. Return list[CompanyProfile].

    Quality gates
    -------------
    - Every A-tier company must have description, products_services, employee_count.
    - B-tier companies allowed to have partial data.
    - Missing critical data → confidence = LOW for that company.

    Subscribers
    -----------
    → TechStackAnalyzer, CompanyDeepResearcher, DecisionMakerProfiler,
      NeedAnalyzer, ContactFinder
    """

    name = "company_profiler"
    description = "Builds enriched company profiles via web scraping and databases."
    phase = PhaseID.PHASE_2_COMPANY_INTEL
    dependencies = [
        Dependency(agent_name="company_ranker", required=True, data_keys=["ranked_companies"]),
    ]
    output_keys = ["company_profiles"]
    subscribers = [
        "tech_stack_analyzer",
        "company_deep_researcher",
        "decision_maker_profiler",
        "need_analyzer",
        "contact_finder",
    ]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Filter ranked_companies → A-tier + B-tier
        2. For each company:
           a. Deep scrape website
           b. Query industry databases
           c. Search recent news
           d. Check LinkedIn company page
           e. Infer current equipment from public info
           f. Infer pain points from news + industry context
        3. Merge into enriched CompanyProfile
        4. Validate quality gates
        5. Return AgentOutput with company_profiles
        """

        ranked_companies = self._get_dep(context, "company_ranker", "ranked_companies") or []
        company_profiles: list[dict] = []

        return self._make_output(
            data={"company_profiles": company_profiles},
            confidence=ConfidenceLevel.MEDIUM,
        )


# =====================================================================
# 15. FINANCIAL ANALYZER
# =====================================================================
class FinancialAnalyzer(BaseAgent):
    """
    Assesses financial health and CAPEX signals for target companies.

    Inputs
    ------
    - company_ranker.ranked_companies  (A-tier focus)

    Outputs
    -------
    - financial_snapshots : dict[company_id, FinancialSnapshot]

    Algorithm
    ---------
    1. For each A-tier company:
       a. Public companies:
          - Fetch financial data from annual reports, Yahoo Finance,
            or equivalent local stock exchanges.
          - Extract: revenue trend (3-5 years), profit margin, debt ratio.
          - Look at CAPEX line items → equipment investment signals.
       b. Private companies:
          - Search for available financial data (some countries have
            mandatory filing: UK Companies House, German Bundesanzeiger).
          - If no data → estimate from employee count, industry benchmarks.
       c. Investment signals:
          - Recent funding rounds (for PE-backed companies).
          - Recent M&A activity (acquiring = has money to spend).
          - New factory construction or expansion announcements.
          - Government grants received.
       d. Financial health assessment:
          - strong: positive revenue growth, healthy margins, active CAPEX.
          - moderate: stable, some growth, moderate investment.
          - weak: declining revenue, high debt, no recent CAPEX.
       e. Budget signals (can they afford AGE equipment?):
          - Annual revenue > 10x typical AGE machine price → likely yes.
          - Recent CAPEX investments → budget available.
          - PE-backed with growth mandate → budget likely.
    2. Return dict[company_id → FinancialSnapshot].

    Quality gates
    -------------
    - At least basic financial_health rating for all A-tier companies.
    - Revenue data for > 50% of A-tier companies.
    - If < 30% have revenue data → confidence = LOW.

    Subscribers
    -----------
    → OpportunityScorer, PricingStrategist
    """

    name = "financial_analyzer"
    description = "Assesses financial health and CAPEX signals for target companies."
    phase = PhaseID.PHASE_2_COMPANY_INTEL
    dependencies = [
        Dependency(agent_name="company_ranker", required=True, data_keys=["ranked_companies"]),
    ]
    output_keys = ["financial_snapshots"]
    subscribers = ["opportunity_scorer", "pricing_strategist"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Filter ranked_companies → A-tier
        2. For each company:
           a. Check if public → fetch financial filings
           b. If private → search for mandatory filings or estimate
           c. Compute revenue_trend, profit_margin, debt_ratio
           d. Identify CAPEX signals
           e. Assess financial_health: strong/moderate/weak
           f. Evaluate budget_signals
        3. Validate quality gates
        4. Return AgentOutput with financial_snapshots
        """

        ranked_companies = self._get_dep(context, "company_ranker", "ranked_companies") or []
        financial_snapshots: dict[str, dict] = {}

        return self._make_output(
            data={"financial_snapshots": financial_snapshots},
            confidence=ConfidenceLevel.MEDIUM,
        )


# =====================================================================
# 16. TECH STACK ANALYZER
# =====================================================================
class TechStackAnalyzer(BaseAgent):
    """
    Audits the current technology and equipment of target companies.
    This is CRITICAL for identifying upgrade opportunities.

    Inputs
    ------
    - company_profiler.company_profiles

    Outputs
    -------
    - tech_stacks : dict[company_id, TechStackEntry]

    Algorithm
    ---------
    1. For each profiled company:
       a. Current machinery:
          - Search: "[company] packaging equipment" / "[company] production line"
          - Check company website for supplier acknowledgments.
          - Look at LinkedIn employee profiles:
            · "Machine operator at [company] — operates [brand] TFS-400"
            · "Maintenance engineer — responsible for [brand] packaging line"
          - Check YouTube/social media for factory tours or product videos.
          - Search press releases: "[company] installs new [equipment]"
       b. Machine age estimation:
          - If installation date known → calculate age.
          - If not → estimate from model number (older models = older machines).
          - Flag machines > 8 years old → upgrade candidates.
       c. Software systems:
          - Search for mentions of ERP (SAP, Oracle, Microsoft Dynamics).
          - Search for MES/SCADA systems.
          - This matters for Industry 4.0 / connectivity selling points.
       d. Automation level:
          - manual: mostly hand-operated processes.
          - semi: some automated lines, some manual.
          - full: fully automated production.
       e. Industry 4.0 readiness:
          - Score 0-100 based on: IoT sensors, data analytics usage,
            connected machines, digital twin mentions.
       f. Known suppliers:
          - Which equipment brands do they currently use?
          - Are these AGE competitors? → competitive displacement opportunity.
       g. Upgrade signals:
          - Old machines (> 8 years).
          - Hiring automation/packaging engineers.
          - Expansion/new factory announcements.
          - Regulatory compliance gaps (need new equipment to comply).
    2. Return dict[company_id → TechStackEntry].

    Quality gates
    -------------
    - At least basic automation_level for 70% of A-tier companies.
    - At least some known_suppliers for 50% of A-tier companies.
    - Machine data scarce → confidence = LOW but still valuable.

    Subscribers
    -----------
    → NeedAnalyzer, GapDetector
    """

    name = "tech_stack_analyzer"
    description = "Audits current equipment, machinery, and technology of target companies."
    phase = PhaseID.PHASE_2_COMPANY_INTEL
    dependencies = [
        Dependency(agent_name="company_profiler", required=True, data_keys=["company_profiles"]),
    ]
    output_keys = ["tech_stacks"]
    subscribers = ["need_analyzer", "gap_detector"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load company_profiles
        2. For each company:
           a. Search for current machinery/equipment
           b. Check LinkedIn employee profiles for equipment mentions
           c. Check videos/photos for production line visibility
           d. Estimate machine ages
           e. Identify software systems (ERP, MES)
           f. Assess automation_level
           g. Score Industry 4.0 readiness
           h. List known suppliers → check if AGE competitors
           i. Identify upgrade signals
        3. Validate quality gates
        4. Return AgentOutput with tech_stacks
        """

        company_profiles = self._get_dep(context, "company_profiler", "company_profiles") or []
        tech_stacks: dict[str, dict] = {}

        return self._make_output(
            data={"tech_stacks": tech_stacks},
            confidence=ConfidenceLevel.LOW,  # equipment data is often hard to find
        )


# =====================================================================
# 17. COMPANY DEEP RESEARCHER
# =====================================================================
class CompanyDeepResearcher(BaseAgent):
    """
    Deep-dives into company ORIGINS, FOUNDERS, KEY PEOPLE, HISTORY,
    and NETWORK CONNECTIONS.

    This agent finds things that surface-level research misses:
    - Who founded the company? What's their background?
    - Who are the board members? Do we have any mutual connections?
    - What's the ownership history? Any recent acquisitions?
    - What strategic partnerships do they have?
    - Are there any personal connections to AGE or Turkey?

    These insights enable hyper-personalized outreach.

    Inputs
    ------
    - company_profiler.company_profiles  (A-tier companies)

    Outputs
    -------
    - company_deep_intel : dict[company_id, CompanyDeepIntel]

    Algorithm
    ---------
    1. For each A-tier company:

       a. FOUNDER RESEARCH:
          - Search: "[company name] founder" / "who founded [company]"
          - Search: "[company name] history founding story"
          - Look at company website "About Us" / "Our Story" pages.
          - For each founder:
            · Name, nationality, educational background.
            · Previous companies / career path.
            · Current role (still active? chairman? retired?).
            · Personal interests, philanthropic activities.
            · Any connection to Turkey, Turkish business, Turkish universities?

       b. KEY EXECUTIVE RESEARCH:
          - LinkedIn search: "[company name] CEO" / "CFO" / "CTO" /
            "VP Operations" / "VP Procurement" / "Plant Manager"
          - For each executive:
            · Name, title, time in role.
            · Career history (where did they work before?).
            · Educational background (university, MBA).
            · Conference speaking appearances.
            · Published articles or interviews.
            · Social media presence.

       c. BOARD MEMBER RESEARCH:
          - Search: "[company name] board of directors"
          - For each board member:
            · Name, other board seats.
            · Professional background.
            · Network value: do they sit on other company boards
              we could sell to? (= warm introduction potential)

       d. OWNERSHIP HISTORY:
          - Who owned this company over time?
          - Family-owned → Private Equity → Public IPO?
          - Recent ownership changes (PE buyout = growth investment signal).
          - Parent company / holding group.

       e. M&A ACTIVITY:
          - Has this company acquired others? (= growing aggressively)
          - Has this company been acquired? (= new budget from parent)
          - Pending M&A? (= wait or opportunity?)

       f. STRATEGIC PARTNERSHIPS:
          - Joint ventures, technology partnerships.
          - Research collaborations with universities.
          - Long-term supplier agreements.

       g. INVESTMENT & FUNDING:
          - VC/PE investment rounds.
          - Government grants.
          - EU Horizon / innovation project participation.

       h. POTENTIAL CONNECTIONS TO AGE:
          - Did any executive study in Turkey?
          - Does the company import from Turkey already?
          - Are there Turkish employees or executives?
          - Shared industry association memberships?
          - Same PE firm that has Turkish portfolio?
          - Any mutual contacts in professional networks?

       i. NEWS SENTIMENT:
          - Aggregate recent news: positive (growth, awards, partnerships)
            vs. negative (layoffs, lawsuits, recalls).
          - Overall sentiment: positive / neutral / negative.

       j. INTERESTING FACTS:
          - Unusual facts that could be conversation starters.
          - Awards won, sustainability initiatives, innovations.
          - Cultural values alignment with AGE.

    2. Return dict[company_id → CompanyDeepIntel].

    Research methodology
    --------------------
    - LinkedIn deep search (people, posts, connections).
    - Company registries (UK Companies House, German Handelsregister,
      French Infogreffe, etc.).
    - News aggregators for company mentions.
    - Crunchbase / PitchBook for funding data.
    - Google Scholar for academic connections.
    - Industry conference speaker lists.

    Quality gates
    -------------
    - Every A-tier company must have ≥1 founder or ≥1 key_executive.
    - potential_connections_to_age is mandatory (even if empty list).
    - If no data found at all → confidence = VERY_LOW + warning.

    Subscribers
    -----------
    → DecisionMakerProfiler, NetworkMapper, OutreachComposer
    """

    name = "company_deep_researcher"
    description = "Deep research into company origins, founders, executives, and network connections."
    phase = PhaseID.PHASE_2_COMPANY_INTEL
    dependencies = [
        Dependency(agent_name="company_profiler", required=True, data_keys=["company_profiles"]),
    ]
    output_keys = ["company_deep_intel"]
    subscribers = ["decision_maker_profiler", "network_mapper", "outreach_composer"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load company_profiles → filter A-tier
        2. For each A-tier company:
           a. Research founders (search, website, LinkedIn)
           b. Research key executives (LinkedIn, press)
           c. Research board members (filings, LinkedIn)
           d. Trace ownership history (registries)
           e. Find M&A activity (news, Crunchbase)
           f. Identify strategic partnerships
           g. Find investment/funding data
           h. Search for connections to AGE / Turkey
           i. Aggregate news sentiment
           j. Collect interesting facts
        3. Build CompanyDeepIntel for each
        4. Validate quality gates
        5. Return AgentOutput with company_deep_intel
        """

        company_profiles = self._get_dep(context, "company_profiler", "company_profiles") or []
        company_deep_intel: dict[str, dict] = {}

        return self._make_output(
            data={"company_deep_intel": company_deep_intel},
            confidence=ConfidenceLevel.MEDIUM,
            sources=["linkedin", "company_registries", "crunchbase", "news_aggregators"],
        )


# =====================================================================
# 18. DECISION MAKER PROFILER
# =====================================================================
class DecisionMakerProfiler(BaseAgent):
    """
    Identifies and profiles the people who MAKE or INFLUENCE
    equipment purchasing decisions at target companies.

    Inputs
    ------
    - company_profiler.company_profiles
    - company_deep_researcher.company_deep_intel

    Outputs
    -------
    - decision_makers : dict[company_id, list[ContactInfo]]

    Algorithm
    ---------
    1. For each profiled company, identify decision-making roles:
       a. PRIMARY decision makers (typically sign off on CAPEX):
          - CEO / Managing Director (at SMEs)
          - VP Operations / COO
          - VP Manufacturing / Production Director
          - CFO (approves budget)
       b. INFLUENCERS (recommend but don't approve):
          - Plant Manager
          - Packaging Manager
          - Quality Manager
          - Engineering Manager / Head of Engineering
          - Procurement Manager
       c. CHAMPIONS (our internal advocates):
          - Technical engineers who see the value.
          - R&D managers looking for innovation.
          - Process engineers frustrated with current equipment.
       d. GATEKEEPERS (can block access):
          - Procurement department (formal process)
          - IT department (for Industry 4.0 integration)

    2. For each identified person:
       a. Find on LinkedIn:
          - Full name, current title, time in role.
          - Career history.
          - University / education.
          - Shared connections with AGE team.
       b. Find contact info:
          - Business email (from website contact page, email patterns).
          - Direct phone (from LinkedIn Premium or company directory).
          - LinkedIn profile URL.
       c. Assess their role_in_decision:
          - decision_maker, influencer, champion, or gatekeeper.
       d. Determine preferred_language from country/profile.
       e. Notes:
          - Any speaking engagements about packaging/production?
          - Published articles on industry topics?
          - Active on LinkedIn (posts, comments)?

    3. Rank contacts by accessibility × influence.
    4. Return dict[company_id → list[ContactInfo]].

    Quality gates
    -------------
    - Every A-tier company must have ≥ 2 identified contacts.
    - At least 1 decision_maker per A-tier company.
    - If only gatekeeper found → warning.

    Subscribers
    -----------
    → ContactFinder, NetworkMapper, OutreachComposer
    """

    name = "decision_maker_profiler"
    description = "Identifies and profiles purchasing decision makers at target companies."
    phase = PhaseID.PHASE_2_COMPANY_INTEL
    dependencies = [
        Dependency(agent_name="company_profiler", required=True, data_keys=["company_profiles"]),
        Dependency(agent_name="company_deep_researcher", required=False, data_keys=["company_deep_intel"]),
    ]
    output_keys = ["decision_makers"]
    subscribers = ["contact_finder", "network_mapper", "outreach_composer"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load company_profiles and company_deep_intel
        2. For each company:
           a. Search LinkedIn for key roles (CEO, VP Ops, Plant Manager, etc.)
           b. Cross-reference with deep_intel executives
           c. For each person:
              - Name, title, career history
              - Contact info (email pattern, phone, LinkedIn)
              - role_in_decision classification
              - preferred_language
              - Activity level / accessibility notes
           d. Rank by influence × accessibility
        3. Validate quality gates
        4. Return AgentOutput with decision_makers
        """

        company_profiles = self._get_dep(context, "company_profiler", "company_profiles") or []
        company_deep_intel = self._get_dep(context, "company_deep_researcher", "company_deep_intel") or {}
        decision_makers: dict[str, list[dict]] = {}

        return self._make_output(
            data={"decision_makers": decision_makers},
            confidence=ConfidenceLevel.MEDIUM,
            sources=["linkedin", "company_websites", "email_patterns"],
        )
