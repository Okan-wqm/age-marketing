# AGE Marketing Intelligence — Report Folder Structure

Bu klasör yapısı, tüm agentların birbirleriyle **haberleşme kanalıdır**.
Bir agent çalıştığında çıktısını ilgili klasöre yazar.
Sonraki agent, ihtiyacı olan veriyi ilgili klasörden okur.

---

## Klasör Haritası

```
reports/
│
├── phase0_know_yourself/
│   ├── product_profiles.md          ← ProductAnalyzer yazar
│   ├── capabilities.md              ← CapabilityMapper yazar
│   └── usps.md                      ← USPExtractor yazar
│
├── phase1_region_discovery/
│   ├── regions.md                   ← RegionScanner yazar
│   ├── regulatory_map.md            ← RegulatoryAnalyzer yazar
│   └── ranked_regions.md            ← RegionRanker yazar
│
├── deep_research/
│   ├── sector_profiles/
│   │   ├── dairy_processing.md      ← SectorDeepResearcher yazar (her sektör ayrı dosya)
│   │   ├── meat_processing.md
│   │   ├── pharma_packaging.md
│   │   └── ...
│   ├── country_markets/
│   │   ├── germany.md               ← CountryMarketAnalyzer yazar (her ülke ayrı dosya)
│   │   ├── usa.md
│   │   ├── france.md
│   │   └── ...
│   ├── market_problems/
│   │   ├── global_problems.md       ← MarketProblemAnalyzer yazar
│   │   ├── germany_dairy.md         ← Ülke+sektör bazlı problemler
│   │   └── ...
│   └── trade_shows/
│       ├── interpack.md             ← TradeShowResearcher yazar (her fuar ayrı dosya)
│       ├── iffa.md
│       ├── anuga_foodtec.md
│       └── ...
│
├── phase1_5_company_discovery/
│   ├── raw_companies/
│   │   ├── batch_tradeshow.md       ← CompanyDiscovery yazar (kanal bazlı)
│   │   ├── batch_directories.md
│   │   ├── batch_web_search.md
│   │   └── batch_associations.md
│   ├── validated_companies/
│   │   ├── company_list.md          ← CompanyValidator yazar
│   │   └── rejected_companies.md
│   └── ranked_companies/
│       └── ranked_list.md           ← CompanyRanker yazar (A/B/C tier)
│
├── phase2_company_intelligence/
│   ├── company_profiles/
│   │   ├── {company_name}.md        ← CompanyProfiler yazar (her firma ayrı dosya)
│   │   └── ...
│   ├── financial_snapshots/
│   │   ├── {company_name}.md        ← FinancialAnalyzer yazar
│   │   └── ...
│   ├── tech_stacks/
│   │   ├── {company_name}.md        ← TechStackAnalyzer yazar
│   │   └── ...
│   ├── deep_intel/
│   │   ├── {company_name}.md        ← CompanyDeepResearcher yazar
│   │   └── ...
│   └── decision_makers/
│       ├── {company_name}.md        ← DecisionMakerProfiler yazar
│       └── ...
│
├── phase3_gap_analysis/
│   ├── company_needs/
│   │   ├── {company_name}.md        ← NeedAnalyzer yazar
│   │   └── ...
│   ├── gap_map/
│   │   ├── {company_name}.md        ← GapDetector yazar
│   │   └── ...
│   └── scored_opportunities/
│       └── opportunity_ranking.md   ← OpportunityScorer yazar
│
├── phase4_competitor_market/
│   ├── competitor_map/
│   │   └── competitor_map.md        ← CompetitorMapper yazar
│   ├── competitor_profiles/
│   │   ├── {competitor_name}.md     ← CompetitorAnalyzer yazar
│   │   └── ...
│   ├── positioning/
│   │   └── positioning_map.md       ← MarketPositioner yazar
│   └── win_loss_patterns/
│       └── patterns.md              ← WinLossAnalyzer yazar
│
├── phase5_communication/
│   ├── contacts/
│   │   ├── {company_name}.md        ← ContactFinder yazar
│   │   └── ...
│   ├── network_map/
│   │   └── connections.md           ← NetworkMapper yazar
│   ├── outreach_messages/
│   │   ├── {company_name}.md        ← OutreachComposer yazar
│   │   └── ...
│   └── campaign_plans/
│       ├── {campaign_name}.md       ← CampaignPlanner yazar
│       └── ...
│
└── phase6_sales/
    ├── proposals/
    │   ├── {company_name}.md        ← ProposalGenerator yazar
    │   └── ...
    ├── pricing_strategies/
    │   ├── {company_name}.md        ← PricingStrategist yazar
    │   └── ...
    ├── roi_models/
    │   ├── {company_name}.md        ← ROICalculator yazar
    │   └── ...
    └── playbooks/
        ├── {company_name}.md        ← SalesPlaybookGenerator yazar
        └── ...
```

---

## Kurallar

1. Her agent **sadece kendi klasörüne yazar**, başka agentın klasörüne yazmaz.
2. Her agent **bağımlı olduğu agentın klasöründen okur**.
3. Dosya isimleri tutarlı olmalı — aynı firma her yerde aynı isimle geçmeli.
4. Her rapor dosyasının başında metadata bölümü olmalı:
   - Yazan agent adı
   - Tarih
   - Confidence seviyesi
   - Kaynak listesi
5. Bir agent çalışmadan önce, bağımlı olduğu klasörlerde gerekli dosyaların var olup olmadığını kontrol etmeli.
