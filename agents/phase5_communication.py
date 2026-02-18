"""
Phase 5 — Communication & Network  (4 agents)
================================================
ContactFinder  →  NetworkMapper  →  OutreachComposer  →  CampaignPlanner

Build contact lists, map relationship networks, compose personalized
outreach, and plan multi-channel campaigns.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, Dependency
from .models import (
    AgentOutput,
    CampaignPlan,
    ConfidenceLevel,
    ContactInfo,
    NetworkConnection,
    OutreachMessage,
    PhaseID,
)


# =====================================================================
# 26. CONTACT FINDER
# =====================================================================
class ContactFinder(BaseAgent):
    """
    Builds a comprehensive contact database for target companies,
    merging data from DecisionMakerProfiler with additional searches.

    Inputs
    ------
    - company_ranker.ranked_companies
    - decision_maker_profiler.decision_makers
    - company_profiler.company_profiles

    Outputs
    -------
    - contacts : dict[company_id, list[ContactInfo]]

    Algorithm
    ---------
    1. Start with decision_makers from Phase 2 (if available).
    2. For companies with < 2 contacts, enrich:
       a. LinkedIn search:
          - "[company name] [target title]" for each target role.
          - Roles to target (priority order):
            1. CEO / MD / General Manager
            2. VP Operations / Production Director
            3. Plant Manager
            4. Technical Director / CTO
            5. Procurement Manager / Head of Purchasing
            6. Packaging Manager
            7. Quality Manager
       b. Company website:
          - Contact page → general inquiries, department contacts.
          - Management team page → names and titles.
          - Press contact → alternative entry point.
       c. Email discovery:
          - Detect email pattern: first.last@domain, f.last@domain, etc.
          - Verify with SMTP check (if permissible).
       d. Phone numbers:
          - Company main line from website.
          - Direct lines from LinkedIn profiles (Premium).
    3. For each contact, classify:
       - role_in_decision: decision_maker / influencer / champion / gatekeeper
       - preferred_language: from country + LinkedIn profile language
    4. Add engagement notes:
       - Active on LinkedIn? → good for social selling.
       - Published articles? → reference in outreach.
       - Conference speaker? → potential meeting opportunity.
    5. Return dict[company_id → list[ContactInfo]].

    Quality gates
    -------------
    - Every A-tier company: ≥ 2 contacts, ≥ 1 decision_maker.
    - Every B-tier company: ≥ 1 contact.
    - At least 1 email per company.

    Subscribers
    -----------
    → OutreachComposer, CampaignPlanner
    """

    name = "contact_finder"
    description = "Builds comprehensive contact database with emails, phones, and role classification."
    phase = PhaseID.PHASE_5_COMMUNICATION
    dependencies = [
        Dependency(agent_name="company_ranker", required=True, data_keys=["ranked_companies"]),
        Dependency(agent_name="decision_maker_profiler", required=False, data_keys=["decision_makers"]),
        Dependency(agent_name="company_profiler", required=True, data_keys=["company_profiles"]),
    ]
    output_keys = ["contacts"]
    subscribers = ["outreach_composer", "campaign_planner"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load decision_makers as base contacts
        2. Identify companies with < 2 contacts
        3. For under-served companies:
           a. LinkedIn search for key roles
           b. Scrape company website for contact info
           c. Discover email patterns
           d. Find phone numbers
        4. Classify each contact's role_in_decision
        5. Set preferred_language
        6. Add engagement notes (LinkedIn activity, publications)
        7. Validate quality gates
        8. Return AgentOutput with contacts
        """

        contacts: dict[str, list[dict]] = {}

        return self._make_output(
            data={"contacts": contacts},
            confidence=ConfidenceLevel.MEDIUM,
        )


# =====================================================================
# 27. NETWORK MAPPER
# =====================================================================
class NetworkMapper(BaseAgent):
    """
    Maps relationship networks to find warm introduction paths.

    Answers: "Do we know someone who knows someone at this company?"

    Inputs
    ------
    - decision_maker_profiler.decision_makers
    - company_deep_researcher.company_deep_intel
    - contact_finder.contacts

    Outputs
    -------
    - network_map : list[NetworkConnection]

    Algorithm
    ---------
    1. Build a graph of people and relationships:
       a. AGE team members (input: our key people + their LinkedIn connections).
       b. Target company contacts.
       c. Board members from company_deep_intel.

    2. Find connections:
       a. Direct connections:
          - AGE person directly connected to target contact on LinkedIn.
       b. Second-degree connections:
          - AGE person → mutual connection → target contact.
       c. Shared contexts:
          - Same university alumni.
          - Same previous employer.
          - Same industry association membership.
          - Same trade show attendance.
          - Same conference speaking circuit.
       d. Board interlocks:
          - Board member sits on multiple relevant company boards.
          - → One warm intro can open multiple doors.

    3. Score connection strength (0-100):
       - Direct LinkedIn connection: 80
       - Same employer currently: 90
       - Same employer previously: 60
       - University alumni: 40
       - Industry association: 50
       - Trade show co-exhibitor: 30
       - Board interlock: 70

    4. Generate warm introduction recommendations:
       - Best path: "Ask [AGE person] to introduce to [target] via [context]."
       - Alternative paths ranked by strength.

    5. Return list[NetworkConnection].

    Quality gates
    -------------
    - At least attempt to find connections for all A-tier companies.
    - Log "no_connection_found" for companies with no path.

    Subscribers
    -----------
    → OutreachComposer, CampaignPlanner
    """

    name = "network_mapper"
    description = "Maps relationship networks to find warm introduction paths."
    phase = PhaseID.PHASE_5_COMMUNICATION
    dependencies = [
        Dependency(agent_name="decision_maker_profiler", required=False, data_keys=["decision_makers"]),
        Dependency(agent_name="company_deep_researcher", required=False, data_keys=["company_deep_intel"]),
        Dependency(agent_name="contact_finder", required=True, data_keys=["contacts"]),
    ]
    output_keys = ["network_map"]
    subscribers = ["outreach_composer", "campaign_planner"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load contacts, decision_makers, company_deep_intel
        2. Build people graph (AGE team + target contacts + board members)
        3. For each target contact:
           a. Search for direct AGE connections
           b. Search for second-degree paths
           c. Check shared contexts (alumni, associations, employers)
           d. Check board interlocks
        4. Score connection strength
        5. Generate warm introduction recommendations
        6. Validate quality gates
        7. Return AgentOutput with network_map
        """

        contacts = self._get_dep(context, "contact_finder", "contacts") or {}
        network_map: list[dict] = []

        return self._make_output(
            data={"network_map": network_map},
            confidence=ConfidenceLevel.LOW,  # network data is often incomplete
        )


# =====================================================================
# 28. OUTREACH COMPOSER
# =====================================================================
class OutreachComposer(BaseAgent):
    """
    Composes hyper-personalized outreach messages for each contact.

    Every message references:
    - The company's specific pain points.
    - AGE's relevant USPs.
    - Personal touches from deep research.
    - Competitive positioning.

    Inputs
    ------
    - contact_finder.contacts
    - gap_detector.gap_map
    - usp_extractor.usps
    - market_positioner.positioning_map
    - company_deep_researcher.company_deep_intel
    - win_loss_analyzer.win_loss_patterns
    - network_mapper.network_map

    Outputs
    -------
    - outreach_messages : list[OutreachMessage]

    Algorithm
    ---------
    1. For each A-tier company, for each primary contact:

       a. SELECT CHANNEL:
          - If warm introduction exists → warm email/LinkedIn referral.
          - If email known → cold email (primary).
          - If LinkedIn active → LinkedIn InMail (secondary).
          - If trade show upcoming → plan trade show meeting.

       b. COMPOSE SUBJECT LINE:
          - Reference a specific, relevant topic:
            · "[Company]'s [specific challenge] — how [peer company] solved it"
            · "Following up on [trade show name]"
            · "Idea for [company]'s [specific product line]"
          - A/B variant: test 2 subject lines per company.

       c. COMPOSE BODY:
          - Opening (personalized):
            · Reference something specific about the person or company.
            · "I noticed [company] recently [expansion/new product/news]."
            · "Your presentation at [conference] about [topic] resonated…"
            · If warm intro: "Our mutual contact [name] suggested I reach out."
          - Problem statement (from gap_map):
            · "Many [sector] companies face [specific problem]."
            · "With [regulation] coming, [challenge] is becoming critical."
          - Solution tease (from USPs + positioning):
            · "We've helped similar companies achieve [specific result]."
            · Brief mention of relevant AGE capability — NOT a full pitch.
          - Call to action:
            · "Would a 15-minute call next week make sense?"
            · "I'll be at [trade show] — could we meet?"
            · "Happy to share a case study from [similar company]."

       d. COMPOSE FOLLOW-UP PLAN:
          - Day 0: Initial outreach.
          - Day 3: LinkedIn connection request (if not already).
          - Day 7: Follow-up email (different angle).
          - Day 14: Share relevant content (article, case study).
          - Day 21: Final follow-up or phone call.

       e. LANGUAGE ADAPTATION:
          - Compose in contact's preferred_language.
          - Adjust tone for culture:
            · German: formal, technical, evidence-based.
            · American: direct, ROI-focused, casual.
            · Middle Eastern: relationship-focused, respectful.
            · Asian: hierarchical, long-term oriented.

    2. Create A/B variants for top 20 contacts.
    3. Return list[OutreachMessage].

    Quality gates
    -------------
    - Every A-tier company has ≥ 1 outreach message.
    - Every message has subject, body, and call_to_action non-empty.
    - Personalization score: message must reference ≥ 2 company-specific facts.

    Subscribers
    -----------
    → CampaignPlanner, SalesPlaybookGenerator
    """

    name = "outreach_composer"
    description = "Composes hyper-personalized outreach messages per contact and channel."
    phase = PhaseID.PHASE_5_COMMUNICATION
    dependencies = [
        Dependency(agent_name="contact_finder", required=True, data_keys=["contacts"]),
        Dependency(agent_name="gap_detector", required=True, data_keys=["gap_map"]),
        Dependency(agent_name="usp_extractor", required=True, data_keys=["usps"]),
        Dependency(agent_name="market_positioner", required=False, data_keys=["positioning_map"]),
        Dependency(agent_name="company_deep_researcher", required=False, data_keys=["company_deep_intel"]),
        Dependency(agent_name="win_loss_analyzer", required=False, data_keys=["win_loss_patterns"]),
        Dependency(agent_name="network_mapper", required=False, data_keys=["network_map"]),
    ]
    output_keys = ["outreach_messages"]
    subscribers = ["campaign_planner", "sales_playbook_generator"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load all dependency data
        2. For each A-tier company, for each primary contact:
           a. Select best channel (warm intro > email > LinkedIn > trade show)
           b. Compose personalized subject line (A/B variants)
           c. Compose body: opening → problem → solution tease → CTA
           d. Write follow-up plan (Day 0, 3, 7, 14, 21)
           e. Adapt language and tone for culture
        3. Create A/B variants for top 20
        4. Validate quality gates
        5. Return AgentOutput with outreach_messages
        """

        contacts = self._get_dep(context, "contact_finder", "contacts") or {}
        gap_map = self._get_dep(context, "gap_detector", "gap_map") or {}
        usps = self._get_dep(context, "usp_extractor", "usps") or []
        outreach_messages: list[dict] = []

        return self._make_output(
            data={"outreach_messages": outreach_messages},
            confidence=ConfidenceLevel.HIGH,
        )


# =====================================================================
# 29. CAMPAIGN PLANNER
# =====================================================================
class CampaignPlanner(BaseAgent):
    """
    Creates end-to-end campaign plans for organized market entry.

    Inputs
    ------
    - outreach_messages from OutreachComposer
    - network_map from NetworkMapper
    - company_ranker.ranked_companies
    - trade_show_researcher.trade_shows

    Outputs
    -------
    - campaign_plans : list[CampaignPlan]

    Algorithm
    ---------
    1. Group target companies by region and sector:
       - Germany + Dairy → Campaign "DACH Dairy Offensive"
       - USA + Meat → Campaign "NA Meat Processors"
       - etc.

    2. For each campaign:
       a. Target company list (from that region+sector).
       b. Campaign phases:
          - Phase A (Week 1-4): Awareness
            · LinkedIn content about sector challenges.
            · Industry publication article placement.
          - Phase B (Week 3-8): Direct outreach
            · Send personalized outreach_messages.
            · Follow-up cadence.
          - Phase C (Week 6-12): Events
            · Trade show attendance (if timing aligns).
            · Webinar for the sector.
            · Factory visit invitations.
          - Phase D (Week 10-16): Nurture
            · Case study sharing.
            · Technical whitepaper distribution.
            · Follow-up meetings.
       c. Channels:
          - Email, LinkedIn, phone, trade shows, webinars, content.
       d. Timeline in weeks.
       e. KPIs:
          - Response rate target: 15-25%.
          - Meeting booked rate: 5-10%.
          - Opportunity created rate: 3-5%.
          - Pipeline value target.

    3. Prioritize campaigns by aggregate opportunity_score.
    4. Ensure no resource conflicts (don't plan 5 trade shows same month).
    5. Return list[CampaignPlan].

    Quality gates
    -------------
    - At least 3 campaigns defined.
    - Each campaign has ≥ 5 target companies.
    - Each campaign has clear phases, channels, and KPIs.

    Subscribers
    -----------
    → SalesPlaybookGenerator (uses campaign context for playbooks)
    """

    name = "campaign_planner"
    description = "Creates multi-channel campaign plans grouped by region and sector."
    phase = PhaseID.PHASE_5_COMMUNICATION
    dependencies = [
        Dependency(agent_name="outreach_composer", required=True, data_keys=["outreach_messages"]),
        Dependency(agent_name="network_mapper", required=False, data_keys=["network_map"]),
        Dependency(agent_name="company_ranker", required=True, data_keys=["ranked_companies"]),
        Dependency(agent_name="trade_show_researcher", required=False, data_keys=["trade_shows"]),
    ]
    output_keys = ["campaign_plans"]
    subscribers = ["sales_playbook_generator"]

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execution steps
        ---------------
        1. Load outreach_messages, network_map, ranked_companies, trade_shows
        2. Group companies by region × sector → campaign buckets
        3. For each campaign:
           a. Select target companies
           b. Design 4-phase campaign structure
           c. Assign channels
           d. Set timeline
           e. Define KPIs
        4. Prioritize campaigns
        5. Check for resource conflicts
        6. Validate quality gates
        7. Return AgentOutput with campaign_plans
        """

        outreach_messages = self._get_dep(context, "outreach_composer", "outreach_messages") or []
        ranked_companies = self._get_dep(context, "company_ranker", "ranked_companies") or []
        campaign_plans: list[dict] = []

        return self._make_output(
            data={"campaign_plans": campaign_plans},
            confidence=ConfidenceLevel.HIGH,
        )
