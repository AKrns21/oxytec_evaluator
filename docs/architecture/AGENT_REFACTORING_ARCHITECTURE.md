# Agent Refactoring Architecture

**Date:** 2025-10-23
**Version:** 1.0
**Reference:** `agent_refactoring_instructions.md`

---

## Visual Overview

### Current Problem: Role Overlap and Redundancy

```
┌─────────────────────────────────────────────────────────────────┐
│  EXTRACTOR (overloaded with business logic)                     │
│  ❌ Technical extraction                                        │
│  ❌ Carcinogen detection & flagging                            │
│  ❌ Data quality severity assessment                           │
│  ❌ Business impact evaluation                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  PLANNER (unclear responsibilities)                             │
│  ⚠️  Sometimes creates data_quality_issues                     │
│  ⚠️  Sometimes makes technology recommendations                │
│  ⚠️  Unclear when to delegate vs do itself                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  SUBAGENTS (receive raw, uncleaned data)                        │
│  ⚠️  Missing CAS numbers                                       │
│  ⚠️  Unit ambiguities (m3/h vs Nm3/h)                          │
│  ⚠️  No context on data quality                                │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  RISK_ASSESSOR (acting as technical reviewer)                   │
│  ❌ Re-calculating LEL values (redundant with Safety Subagent) │
│  ❌ Re-evaluating cost estimates (redundant with Economic)     │
│  ❌ "VETO POWER" over subagent findings                        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  WRITER (unclear what sources to trust)                         │
│  ⚠️  Receives raw extraction + subagent results + risk report  │
│  ⚠️  No clear priority rules                                   │
│  ⚠️  Sometimes invents data to fill gaps                       │
└─────────────────────────────────────────────────────────────────┘
```

**Problems:**
1. **Role overlap:** EXTRACTOR, PLANNER, and SUBAGENTS all assess severity
2. **Data quality:** SUBAGENTS work with uncleaned, incomplete data
3. **Redundancy:** RISK_ASSESSOR rechecks what SUBAGENTS already analyzed
4. **Trust hierarchy:** WRITER doesn't know which source is authoritative

---

## New Architecture: Clear Separation of Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│  EXTRACTOR v2.0.0 (pure technical cleanup)                      │
│  ✅ Extract raw data from documents                            │
│  ✅ Normalize units (Unicode → ASCII)                          │
│  ✅ Flag missing/unclear data (extraction_notes)               │
│  ✅ NO severity assessment                                     │
│  ✅ NO carcinogen detection                                    │
│  ✅ NO business logic                                          │
│                                                                 │
│  Output: extracted_facts.json + extraction_notes[]             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  PLANNER v2.0.0 (data curator + orchestrator)                   │
│                                                                 │
│  PHASE 1: DATA ENRICHMENT (Planner does this himself)          │
│  ✅ Look up missing CAS numbers (web_search)                   │
│  ✅ Apply standard assumptions (O₂=21% if not measured)        │
│  ✅ Disambiguate units (m3/h → Nm3/h if temp known)            │
│  ✅ Resolve conflicts (multi-document data)                    │
│  ✅ Normalize names (Ethylacetat → IUPAC: Ethyl acetate)       │
│                                                                 │
│  Output: enriched_facts.json + enrichment_notes[]              │
│                                                                 │
│  PHASE 2: SUBAGENT ORCHESTRATION (Pure delegation)             │
│  ✅ Decide which subagents to create (conditional logic)       │
│  ✅ Create detailed task descriptions                          │
│  ✅ Pass enriched data + uncertainty context                   │
│  ✅ NO technology recommendations                              │
│  ✅ NO risk assessments                                        │
│                                                                 │
│  Output: subagent_definitions[] with enriched context          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  SUBAGENTS v1.1.0 (domain experts with clean data)             │
│                                                                 │
│  1. VOC Chemistry Specialist                                   │
│     ✅ Analyze reactivity, oxidation pathways                  │
│     ✅ Identify by-product formation risks                     │
│     ✅ Quantify uncertainty (if O₂=21% ±3%, impact ±X%)        │
│                                                                 │
│  2. Technology Screening Specialist                            │
│     ✅ Compare NTP/UV/scrubber quantitatively                  │
│     ✅ Use oxytec_knowledge_search + product_database          │
│                                                                 │
│  3. Safety/ATEX Specialist (CONDITIONAL)                       │
│     ✅ Calculate LEL, assess ATEX zone                         │
│     ✅ Note assumptions: "O₂ assumed 21% - measure for final"  │
│                                                                 │
│  4. Carcinogen Risk Specialist (CONDITIONAL)                   │
│     ✅ Identify Group 1/2A carcinogens                         │
│     ✅ Assess formation risks during treatment                 │
│                                                                 │
│  5. Flow/Mass Balance Specialist (CONDITIONAL)                 │
│  6. Economic Analysis Specialist (CONDITIONAL)                 │
│  7. Regulatory Compliance Specialist (CONDITIONAL)             │
│  8. Customer Question Response Specialist (CONDITIONAL)        │
│                                                                 │
│  ALL SUBAGENTS:                                                │
│  ✅ Receive enriched data (not raw extraction)                 │
│  ✅ Know which values are measured vs assumed                  │
│  ✅ Quantify sensitivity to assumptions                        │
│  ✅ Propose mitigation strategies                              │
│                                                                 │
│  Output: Parallel execution → subagent_results[]               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  RISK_ASSESSOR v2.0.0 (cross-functional synthesizer)            │
│                                                                 │
│  ✅ Identify INTERACTION risks (not individual domain risks)   │
│     Example: VOC Agent says "formaldehyde formation" +         │
│              Safety Agent says "ATEX Zone 2" +                 │
│              Economic Agent says "KAT needed +€50k"            │
│     → Combined risk: "Carcinogen monitoring in ATEX zone +     │
│                       expensive treatment → High complexity"   │
│                                                                 │
│  ✅ Assumption cascade analysis                                │
│     "If ALL agents assumed O₂=21%, what if it's 18%?"          │
│                                                                 │
│  ✅ Uncertainty aggregation                                    │
│     "5 agents with ±15% uncertainty → combined ±35%"           │
│                                                                 │
│  ✅ System-level mitigation                                    │
│     "Pilot test addresses 3 risks simultaneously"              │
│                                                                 │
│  ✅ NO recalculation of LEL, costs, efficiency                 │
│  ✅ NO re-evaluation of individual subagent work               │
│  ✅ Trust domain experts                                       │
│                                                                 │
│  Output: cross_functional_risks[] + combined_assessment        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  WRITER v1.1.0 (report generator with clear inputs)            │
│                                                                 │
│  INPUTS:                                                        │
│  ✅ Subagent reports (domain-specific findings)                │
│  ✅ Risk Assessor synthesis (cross-functional risks)           │
│                                                                 │
│  NOT INPUTS:                                                   │
│  ❌ extracted_facts.json                                       │
│  ❌ enriched_facts.json                                        │
│  ❌ Original documents                                         │
│                                                                 │
│  PRIORITY RULES:                                               │
│  1️⃣  Risk Assessor's cross-functional risks > individual risks│
│  2️⃣  If Risk Assessor says CRITICAL, report reflects it       │
│  3️⃣  No artificial balance (don't sugarcoat real risks)       │
│  4️⃣  Never invent data - use only what subagents provided     │
│                                                                 │
│  Output: German feasibility report (structured markdown)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Transformation

### Before: Raw → Analyzed → Re-analyzed

```
Documents → EXTRACTOR (raw + severity) → PLANNER (partial enrichment)
           ↓
    SUBAGENTS (work with gaps) → RISK_ASSESSOR (rechecks everything)
           ↓
    WRITER (confused about sources)
```

### After: Raw → Enriched → Specialized → Synthesized

```
Documents → EXTRACTOR (raw + flags)
           ↓
    PLANNER Phase 1: Enrichment (CAS lookup, assumptions, units)
           ↓
    PLANNER Phase 2: Orchestration (conditional subagent creation)
           ↓
    SUBAGENTS (enriched data + uncertainty context) [PARALLEL]
           ↓
    RISK_ASSESSOR (cross-functional synthesis, NO recalculation)
           ↓
    WRITER (clear priority: Risk Assessor > Subagents)
```

---

## Key Architectural Principles

### 1. Single Responsibility Principle

| Agent | Responsibility | Does NOT Do |
|-------|----------------|-------------|
| **EXTRACTOR** | Extract raw data, flag gaps | Assess severity, detect carcinogens, make judgments |
| **PLANNER** | Enrich data, orchestrate subagents | Analyze risks, recommend technologies, perform calculations |
| **SUBAGENTS** | Domain-specific analysis | Cross-functional synthesis, second-guess other domains |
| **RISK_ASSESSOR** | Synthesize interactions | Recalculate domain-specific findings, overrule experts |
| **WRITER** | Generate report from synthesis | Invent data, perform new analysis, second-guess Risk Assessor |

### 2. Data Quality Progression

```
Stage 1: RAW DATA (EXTRACTOR output)
- Original units from documents
- Missing fields → null
- Ambiguities → extraction_notes

Stage 2: ENRICHED DATA (PLANNER Phase 1 output)
- CAS numbers looked up
- Standard assumptions applied (documented)
- Units disambiguated (if possible)
- Conflicts resolved (with source priority)
- enrichment_notes: what was added/assumed

Stage 3: ANALYZED DATA (SUBAGENTS output)
- Domain-specific findings
- Uncertainty quantified
- Sensitivity to assumptions calculated
- Mitigation strategies proposed

Stage 4: SYNTHESIZED DATA (RISK_ASSESSOR output)
- Cross-functional risk interactions
- Assumption cascade analysis
- System-level recommendations
```

### 3. Trust Hierarchy

```
WRITER's trust hierarchy (highest → lowest):

1. RISK_ASSESSOR cross_functional_risks
   (System-level view, sees interactions)

2. RISK_ASSESSOR combined_assessment
   (Overall project risk with confidence)

3. SUBAGENT findings (domain-specific)
   (Trust experts in their domains)

4. PLANNER enrichment_notes
   (Context on assumptions made)

5. EXTRACTOR extraction_notes
   (What was missing in original data)
```

**Rule:** If conflict exists, higher trust level wins.

**Example:**
- VOC Subagent: "Formaldehyde formation: MEDIUM risk (manageable)"
- Safety Subagent: "ATEX Zone 2: MEDIUM risk (standard)"
- Economic Subagent: "KAT cost: MEDIUM impact (+€45k)"
- **Risk Assessor:** "COMBINATION of carcinogen + ATEX + cost = **CRITICAL** combined risk"

→ WRITER reports: **CRITICAL** (Risk Assessor synthesis overrides individual MEDIUM ratings)

### 4. Conditional Logic for Subagents

**PLANNER decides which subagents to create based on data:**

| Subagent | Trigger Condition |
|----------|-------------------|
| **VOC Chemistry** | ALWAYS (any VOCs present) |
| **Technology Screening** | ALWAYS (core recommendation needed) |
| **Safety/ATEX** | IF atex_classification=null OR O₂ unknown OR VOC >10% LEL |
| **Carcinogen Risk** | IF keywords detected OR high-risk industry (surfactant, petroleum) |
| **Flow/Mass Balance** | IF unit ambiguity OR GHSV calculations needed |
| **Economic Analysis** | IF budget_constraints mentioned OR customer asks for cost |
| **Regulatory Compliance** | IF TA Luft/IED BAT/EPA mentioned OR carcinogens present |
| **Customer Questions** | IF customer_specific_questions.length ≥ 1 (HIGH PRIORITY) |

**Result:** Typical inquiries create 3-5 subagents, complex inquiries create 7-8.

---

## Schema Changes

### EXTRACTOR Output (v2.0.0)

```json
{
  "extraction_notes": [
    {
      "field": "pollutant_list[0].cas_number",
      "status": "missing_in_source",
      "note": "Ethylacetat mentioned without CAS number"
    },
    {
      "field": "process_parameters.oxygen_content_percent",
      "status": "not_provided_in_documents",
      "note": "O₂ content not measured - affects LEL calculations"
    }
  ],
  "data_quality_issues": [],  // DEPRECATED - empty for backward compatibility
  "pollutant_list": [...],
  "process_parameters": {...}
}
```

### PLANNER Output (v2.0.0)

```json
{
  "enrichment_summary": "Looked up 3 CAS numbers via web_search. Assumed O₂=21% (atmospheric air) - not measured. Converted m3/h to Nm3/h using T=45°C. Resolved flow rate conflict: used measurement report (2800 m3/h) over questionnaire (3000 m3/h).",

  "enriched_facts": {
    "pollutant_list": [
      {
        "name": "Ethylacetat",
        "iupac_name": "Ethyl acetate",  // NEW: normalized
        "cas_number": "141-78-6",  // NEW: looked up
        "concentration": 1800,
        "unit": "mg/Nm3"  // NEW: disambiguated from mg/m3
      }
    ],
    "process_parameters": {
      "oxygen_content_percent": 21,  // NEW: assumed
      "flow_rate": 2800,
      "flow_rate_normalized": 2450  // NEW: calculated Nm3/h
    }
  },

  "enrichment_notes": [
    {
      "field": "pollutant_list[0].cas_number",
      "action": "looked_up",
      "source": "web_search: PubChem",
      "confidence": "HIGH"
    },
    {
      "field": "process_parameters.oxygen_content_percent",
      "action": "assumed",
      "value": 21,
      "rationale": "No O₂ measurement - assumed atmospheric air (21%)",
      "confidence": "MEDIUM"
    }
  ],

  "data_uncertainties": [
    {
      "field": "process_parameters.oxygen_content_percent",
      "uncertainty": "±3%",
      "impact": "Affects LEL calculation (±15% impact on safety margin)"
    }
  ],

  "subagents": [
    {
      "task": "Subagent: VOC Chemistry Specialist\n\nObjective: Analyze ethyl acetate reactivity and oxidation pathways.\n\nQuestions to answer:\n- What are the primary oxidation products of ethyl acetate in NTP/UV?\n- Is formaldehyde or acetaldehyde formation expected? (Quantify probability)\n- What is the oxidation efficiency for ethyl acetate at 1800 mg/Nm3?\n\nMethod hints:\n- Use stoichiometry: CH3COOC2H5 + O3 → products\n- Cite literature: typical efficiency for esters in NTP\n- Risk classification: CRITICAL (>80% prob), HIGH (30-80%), MEDIUM (10-30%), LOW (<10%)\n\nContext from enrichment:\n- O₂ content assumed 21% (not measured) - quantify impact if actual O₂ is 18-24%\n- CAS number was looked up (not in original docs)\n- Flow rate converted from m3/h to Nm3/h using T=45°C\n\nDeliverables:\n- Table: Substance | Oxidation Products | Formation Probability | Risk Level\n- Mitigation strategies with quantified cost/timeline\n\nDependencies: INDEPENDENT\n\nTools needed: [\"web_search\"]",

      "relevant_content": "{\"pollutant_list\": [{\"name\": \"Ethylacetat\", \"cas_number\": \"141-78-6\", \"concentration\": 1800}], \"process_parameters\": {\"oxygen_content_percent\": 21, \"temperature\": 45}}",

      "tools": ["web_search"]
    }
  ],

  "reasoning": "Created 3 subagents: VOC Chemistry (analyze ethyl acetate), Technology Screening (compare NTP/UV/scrubber), Safety/ATEX (LEL calc with O₂ uncertainty). Did NOT create Carcinogen specialist (no high-risk keywords). Did NOT create Economic specialist (customer didn't ask for cost)."
}
```

### RISK_ASSESSOR Output (v2.0.0)

```json
{
  "subagent_summaries": [
    {
      "subagent": "VOC Chemistry Specialist",
      "key_findings": [
        "Ethyl acetate oxidation efficiency >90% expected",
        "Formaldehyde formation risk: LOW (5% probability)",
        "No halogenated by-products"
      ],
      "risk_level": "LOW",
      "confidence": "HIGH"
    }
  ],

  "cross_functional_risks": [
    {
      "risk_description": "O₂ content uncertainty (assumed 21%, not measured) affects both LEL safety calculation (Safety Agent) and NTP power sizing (Technology Agent). If actual O₂ is 18%, LEL increases 15% (reduces safety margin) AND NTP power requirement increases 20% (+€8k CAPEX).",
      "affected_domains": ["Safety/ATEX", "Technology Screening", "Economic"],
      "combined_severity": "HIGH",
      "probability_estimate": "40% (likely O₂ is not exactly 21%)",
      "evidence": "Safety Agent noted ±15% LEL sensitivity; Technology Agent calculated ±20% power impact",
      "mitigation": "Measure O₂ content before final design (€1k, 1 week) - reduces uncertainty from ±35% to ±5%, prevents €8k oversizing or LEL miscalculation"
    }
  ],

  "assumption_cascade_analysis": [
    {
      "shared_assumption": "O₂ = 21% (atmospheric air)",
      "affected_subagents": ["Safety/ATEX", "VOC Chemistry", "Technology Screening"],
      "sensitivity": "If O₂ = 18%: LEL +15%, oxidation efficiency -10%, NTP power +20%",
      "measurement_recommendation": "O₂ sensor (€1k) CRITICAL before final design"
    }
  ],

  "uncertainty_prioritization": [
    {
      "uncertainty_source": "O₂ content (assumed, not measured)",
      "impact_domains": ["Safety margin", "Reactor sizing", "Cost estimation"],
      "uncertainty_magnitude": "±3% absolute, ±15% relative impact",
      "risk_contribution": "HIGH - Dominates system uncertainty",
      "measurement_priority": "CRITICAL"
    }
  ],

  "combined_risk_assessment": {
    "overall_project_risk": "MEDIUM",
    "confidence_in_assessment": "MEDIUM",
    "key_risk_drivers": [
      "O₂ uncertainty affects safety + sizing + cost",
      "No pilot test data for ethyl acetate at this concentration"
    ],
    "project_killing_scenarios": [
      "Actual O₂ <18% → LEL >80% → ATEX Zone 1 required → +€40k CAPEX (15% probability)"
    ],
    "required_actions_before_proceeding": [
      "Measure O₂ content (€1k, 1 week)",
      "Confirm no dust/particles (affects pre-filtration, +€20k if needed)"
    ]
  },

  "recommendation": {
    "decision": "PROCEED_WITH_CAUTION",
    "justification": "Technical solution is feasible, but O₂ uncertainty creates 40% probability of design changes. Measurement resolves this.",
    "conditions_for_proceed": [
      "O₂ measurement confirms 18-24% range",
      "Customer confirms no particulates (filtration not needed)"
    ],
    "alternative_approaches": [
      "If O₂ <18%: Use catalytic oxidation instead of NTP (no LEL concerns, +€30k)"
    ]
  }
}
```

---

## Migration Path

### Phase 1: Infrastructure (✅ COMPLETE)

- Prompt versioning system
- Shared fragments library
- Database schema updates
- Documentation

### Phase 2: EXTRACTOR + PLANNER (2 weeks)

**Week 1:**
- EXTRACTOR v2.0.0: Remove business logic, add extraction_notes
- Test with 10 historical inquiries
- A/B compare with v1.0.0

**Week 2:**
- PLANNER v2.0.0: Add Phase 1 enrichment, conditional subagent creation
- Test CAS lookup, unit conversion, conflict resolution
- Validate subagent creation logic

### Phase 3: SUBAGENT + RISK_ASSESSOR (1 week)

- SUBAGENT v1.1.0: Add uncertainty quantification
- RISK_ASSESSOR v2.0.0: Shift to synthesizer role
- Test cross-functional risk detection

### Phase 4: WRITER (1 week)

- WRITER v1.1.0: Add Risk Assessor priority rules
- Test full pipeline end-to-end
- Generate 5 feasibility reports

### Phase 5: Production Rollout (2 weeks)

- Week 1: 20% traffic to new system
- Week 2: 100% migration

---

## Success Metrics

### Quality Improvements (Target)

| Metric | Baseline (v1.0.0) | Target (v2.0.0) |
|--------|-------------------|-----------------|
| **Extractor Prompt Length** | 12,000 chars | 6,000 chars (-50%) |
| **Data Completeness** | 70% (missing CAS, O₂, etc.) | 90% (enrichment fills gaps) |
| **Cross-Functional Risks Identified** | 0-1 per report | 2-4 per report |
| **False Positive Factors** | 5-8 per report | 0-2 per report |
| **Uncertainty Quantified** | Rarely | Every critical claim |
| **Engineer Feedback** | "Too many basics listed" | "Only genuine advantages" |

### Performance Metrics (Maintain)

| Metric | Baseline | Target |
|--------|----------|--------|
| **Total Processing Time** | 50-70 seconds | 50-70 seconds (no regression) |
| **Token Usage** | 150k-200k tokens | 150k-200k tokens (±10%) |
| **Error Rate** | <1% | <1% |

---

## Rollback Plan

If quality/performance degrades:

1. **Immediate:** Change config to previous version
   ```python
   # backend/app/config.py
   extractor_prompt_version = "v1.0.0"  # Rollback from v2.0.0
   ```

2. **Short-term:** Investigate root cause
   ```bash
   pytest tests/integration/ -v --pdb
   ```

3. **Long-term:** Fix issues, create v2.0.1 (patch) or v2.1.0 (minor)

**Rollback triggers:**
- Error rate >5%
- Token usage >1.5x baseline
- >3 engineer complaints in first week

---

## Conclusion

This refactoring establishes **clear boundaries** between agents:
- EXTRACTOR: Technical cleanup only
- PLANNER: Data curator + orchestrator
- SUBAGENTS: Domain experts
- RISK_ASSESSOR: Cross-functional synthesizer
- WRITER: Report generator with clear priorities

**Key Innovation:** PLANNER's Phase 1 enrichment ensures SUBAGENTS work with high-quality, complete data, eliminating redundant lookups and improving analysis quality.

**Result:** Simpler prompts, clearer roles, better output quality, easier maintenance.
