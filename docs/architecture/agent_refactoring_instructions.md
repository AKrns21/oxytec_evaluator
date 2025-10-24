# Agent Refactoring Instructions v1.0

**Date:** 2025-10-23  
**Reason:** Clear separation of responsibilities between agents to avoid redundancy and prompt overload

---

## Overview: New Role Distribution

```
EXTRACTOR (technical cleanup only)
    ↓ extracted_facts.json + extraction_notes
PLANNER (data curator + orchestrator)
    ↓ Cleaned data + subagent tasks (parallel)
SUBAGENTS (domain experts with tools)
    ↓ All results
RISK_ASSESSOR (cross-functional synthesizer)
    ↓ Consolidated package (subagent results + cross-functional risks)
WRITER (report generator - sees only consolidated package)
```

---

## 1. EXTRACTOR Changes

### File: `prompt_extractor_v1_0_0.md`

### 🔴 TO REMOVE

#### A. Carcinogen Detection (Lines 47-94)
**Remove:**
- Entire section "CARCINOGENIC & HIGHLY TOXIC SUBSTANCES"
- All lists of Group 1/2A carcinogens
- Detection keywords
- Automatic escalation rules (lines 80-87)
- Expert warning context (lines 89-94)

**Rationale:** Carcinogen risk assessment is the responsibility of specialized subagents, not the extractor.

#### B. Data Quality Issues with Severity Rating (Lines 394-407)
**Remove:**
- Severity classification (CRITICAL/HIGH/MEDIUM/LOW)
- Impact descriptions
- Examples with business evaluations

**Rationale:** Severity rating and impact assessment is the planner's job, not the extractor's.

#### C. Carcinogen Flagging Examples (Lines 491-531)
**Remove:**
- Entire section "CRITICAL CARCINOGEN & TOXICITY DETECTION"
- Mandatory checks (lines 495-499)
- Example flagging JSON with severity ratings

**Rationale:** This is business logic that belongs in the planner/subagents.

#### D. Example Document in Prompt (Lines 96-109)
**Remove:**
- Embedded example document "Mathis_input.txt"

**Rationale:** Example documents should not be hardcoded in the prompt. They bloat the prompt and are not representative of all cases.

### 🟢 TO ADD

#### A. New Section: "EXTRACTION NOTES" (Insert after line 20)

```markdown
**EXTRACTION NOTES:**

When you encounter missing, unclear, or ambiguous data during extraction, add a note to the "extraction_notes" array:

{
  "extraction_notes": [
    {
      "field": "path.to.field (e.g., pollutant_list[0].cas_number)",
      "status": "not_provided_in_documents | missing_in_source | unclear_format | table_empty | extraction_uncertain",
      "note": "Brief description of what is missing/unclear"
    }
  ]
}

**Status Types:**
- `not_provided_in_documents`: Field exists in schema but is not mentioned anywhere in documents
- `missing_in_source`: Mentioned but incomplete (e.g., substance name without CAS number)
- `unclear_format`: Present but ambiguous (e.g., "m3/h" vs "Nm3/h" unclear, or "150" without unit)
- `table_empty`: Table structure exists but cells are empty
- `extraction_uncertain`: You are unsure if you interpreted the data correctly

**Examples:**

Document says: "Ethylacetat"
→ extraction_notes: {field: "pollutant_list[0].cas_number", status: "missing_in_source", note: "Ethylacetat mentioned without CAS number"}

Document says: "156 kg/Tag Ethylacetat"
→ extraction_notes: {field: "pollutant_list[0].concentration", status: "unclear_format", note: "Document states '156 kg/Tag' but unclear if this is concentration (mg/Nm3) or daily load (kg/day)"}

Document mentions "Ablufttemperatur" but no value given
→ extraction_notes: {field: "process_parameters.temperature.value", status: "not_provided_in_documents", note: "Temperature mentioned but no value provided"}

**DO NOT:**
- Add severity ratings (CRITICAL/HIGH/MEDIUM/LOW)
- Add impact descriptions ("Affects LEL calculations...")
- Make business judgments about what is important
- Propose solutions or workarounds

Your job is to FLAG what's missing, not to ASSESS its impact.
```

#### B. Technical Cleanup Rules (Insert after extraction_notes section)

```markdown
**TECHNICAL CLEANUP RULES:**

You MUST perform these automatic technical normalizations:

1. **Unit Normalization:**
   - Unicode → ASCII: "m³/h" → "m3/h", "°C" → "degC", "Â°C" → "degC"
   - Preserve original case: "Nm3/h" stays "Nm3/h" (do NOT lowercase)
   - Preserve ambiguity: If document doesn't specify "m3/h" vs "Nm3/h", extract as written and add extraction_note

2. **Number Formatting:**
   - Thousand separators: "1.200" (German) → 1200, "1,200" (English) → 1200
   - Decimal separators: Preserve "1.5" as 1.5, "1,5" as 1.5
   - Ranges: "10-20%" → extract as string "10-20%" in formulation_percentage field

3. **Text Preservation:**
   - Preserve original substance names exactly: "Ethylacetat" stays "Ethylacetat" (do NOT translate to "Ethyl acetate")
   - Preserve original wording in free-text fields
   - Do NOT correct spelling errors (that's not your job)

4. **Table Extraction:**
   - Extract ALL rows and columns, including empty cells (use null for empty)
   - Preserve header text exactly as written
   - Preserve row order

5. **CAS Number Extraction:**
   - Extract if present in document: "CAS: 141-78-6" → "141-78-6"
   - If missing: cas_number: null (do NOT look up!)
   - If ambiguous: Add extraction_note

**DO NOT:**
- Look up missing CAS numbers (planner's job)
- Translate substance names (planner's job)
- Validate if numbers are physically plausible (planner's job)
- Normalize "m3/h" vs "Nm3/h" unless document is explicit (flag ambiguity instead)
```

#### C. Update JSON Schema (Lines 110-410)

**Modify the schema to add:**

```json
{
  ...,
  "extraction_notes": [
    {
      "field": "string (JSON path to field, e.g., pollutant_list[0].cas_number)",
      "status": "string (not_provided_in_documents | missing_in_source | unclear_format | table_empty | extraction_uncertain)",
      "note": "string (brief description)"
    }
  ],
  "data_quality_issues": []  // DEPRECATED - Leave as empty array for backward compatibility
}
```

**Note for developers:** The `data_quality_issues` field should remain in the schema (empty array) for backward compatibility, but extraction_notes is the new field to populate.

### 🟡 TO MODIFY

#### Customer-Specific Questions (Lines 413-490)

**KEEP THIS SECTION** - Customer question detection is pure pattern matching and appropriate for the extractor.

**No changes needed** - This section is correctly scoped.

### ✅ VALIDATION CHECKLIST

After changes, verify:
- [ ] No business logic remains (no severity ratings, no impact assessments)
- [ ] extraction_notes section is clear and has examples
- [ ] Technical cleanup rules are explicit
- [ ] CAS lookup is explicitly forbidden
- [ ] Carcinogen detection is completely removed
- [ ] Example document "Mathis_input.txt" is removed
- [ ] JSON schema includes extraction_notes field

---

## 2. PLANNER Changes

### File: `prompt_planner_v1_0_0.md`

### 🔴 TO REMOVE

#### A. Direct Data Quality Issues Creation
**Remove or modify:**
- Any instructions that say "Create data_quality_issues with severity ratings"
- The planner should NOT directly populate data_quality_issues in its output JSON

**Rationale:** The planner's job is to delegate analysis to subagents, not to perform it himself.

### 🟢 TO ADD

#### A. New Section: "PHASE 1: DATA ENRICHMENT" (Insert before "Your job" section)

```markdown
**PHASE 1: DATA ENRICHMENT (You perform this yourself)**

Before creating subagent tasks, you must clean and enrich the extracted data:

**1. CAS Number Lookup:**
- For any pollutant without cas_number: Use web_search to find it
- Query pattern: "[substance name] CAS number"
- Validate: CAS format is XXX-XX-X or XXXX-XX-X or XXXXX-XX-X
- Add to enriched_facts.json

**2. Standard Value Assumptions:**
- If oxygen_content_percent is null AND no process context suggests otherwise:
  - Assume 21% (atmospheric air)
  - Add note: "Assumed 21% O2 (atmospheric air) - not measured"
- If pressure.type is null: Assume "atmospheric"
- If humidity is null: Flag as "unknown - affects adsorption/oxidation performance"

**3. Unit Disambiguation:**
- If flow_rate has unit "m3/h" but temperature is known:
  - Calculate Nm3/h equivalent: Nm3/h = m3/h × (273.15 / (273.15 + T_celsius))
  - Add both values to enriched_facts
  - Note: "Calculated from actual m3/h using T=[X]°C"
- If unit is ambiguous (unclear from document): Keep as-is and add uncertainty note

**4. Inconsistency Resolution:**
- If multiple documents give different values for same parameter:
  - Priority: Most recent document > Measurement report > Questionnaire
  - Document which source was used
  - Flag other values as "conflicting data from [source]"

**5. Name Normalization:**
- Look up IUPAC names for substances if helpful (but preserve original name)
- Example: "Ethylacetat" → Add iupac_name: "Ethyl acetate", keep name: "Ethylacetat"

**OUTPUT: enriched_facts.json**
- Same structure as extracted_facts.json but with filled gaps
- Add field "enrichment_notes" documenting what you added/assumed
- Add field "data_uncertainties" for things you couldn't resolve

**TOOLS TO USE:**
- web_search for CAS lookups, substance properties
- Basic calculations for unit conversions (you can do this without tools)

**IMPORTANT:**
- Document every assumption you make
- Be conservative: Only add standard values where clearly applicable
- If uncertain, leave as null and flag for subagent investigation
```

#### B. New Section: "PHASE 2: SUBAGENT TASK CREATION" (Replace current "Your job" section)

```markdown
**PHASE 2: SUBAGENT TASK CREATION**

Now that you have clean, enriched data, decompose the analysis into specialized subagent tasks.

**YOUR ROLE: Pure Orchestrator**
- You delegate analysis, you do NOT perform it yourself
- You do NOT make technology recommendations
- You do NOT assess risks or classify severity
- You do NOT make business judgments

**DECISION LOGIC: Which Subagents to Create**

Analyze enriched_facts and data_uncertainties to decide which subagents are needed:

1. **VOC Chemistry Specialist** (ALWAYS create)
   - Trigger: Any VOCs in pollutant_list
   - Task: Analyze reactivity, oxidation pathways, by-products
   - Pass: pollutant_list, process_parameters

2. **Technology Screening Specialist** (ALWAYS create)
   - Trigger: Always needed
   - Task: Compare NTP, UV/ozone, scrubbers quantitatively
   - Pass: pollutant_list, process_parameters, requirements_and_constraints
   - Tools: ["oxytec_knowledge_search", "web_search"]

3. **Safety/ATEX Specialist** (CONDITIONAL)
   - Trigger: IF atex_classification is null OR oxygen_content unknown OR VOC concentration >10% LEL
   - Task: Calculate LEL, assess ATEX zone classification
   - Pass: pollutant_list, process_parameters, site_conditions
   - Note in task: "O2 assumed 21% - quantify uncertainty in LEL calculation"

4. **Carcinogen Risk Specialist** (CONDITIONAL)
   - Trigger: IF any substance name contains: formaldehyde, ethylene oxide, propylene oxide, benzene, acetaldehyde, H2S
            OR industry_sector contains: surfactant, ethoxylation, petroleum, waste oil, bilge
            OR any alcohol in VOC list (formaldehyde formation risk)
   - Task: Identify Group 1/2A carcinogens, assess formation risks, regulatory implications
   - Pass: pollutant_list, industry_and_process
   - Tools: ["web_search"]

5. **Flow/Mass Balance Specialist** (CONDITIONAL)
   - Trigger: IF flow_rate unit ambiguity OR need reactor sizing OR GHSV calculations
   - Task: Convert units, calculate mass loads, estimate residence times
   - Pass: pollutant_list, process_parameters

6. **Economic Analysis Specialist** (CONDITIONAL)
   - Trigger: IF budget_constraints mentioned OR customer asks for cost comparison
   - Task: Estimate CAPEX/OPEX ranges using product database
   - Pass: technology recommendations (depends on Technology Screening), process_parameters
   - Tools: ["product_database"]
   - **CRITICAL INSTRUCTION:** "Use ONLY product_database for cost data. If no pricing available, state 'Cost TBD - requires quotation'"

7. **Regulatory Compliance Specialist** (CONDITIONAL)
   - Trigger: IF regulatory_requirements mentions TA Luft, IED BAT, EPA, or IF carcinogens present
   - Task: Assess compliance requirements, emission limits, monitoring obligations
   - Pass: pollutant_list, requirements_and_constraints, carcinogen findings
   - Tools: ["web_search"]

8. **Customer Question Response Specialist** (HIGH PRIORITY - CONDITIONAL)
   - Trigger: IF customer_specific_questions array has ≥1 entry
   - Task: Provide direct, numbered answers to customer questions
   - Pass: customer_specific_questions, enriched_facts (relevant sections based on question content)
   - Tools: ["oxytec_knowledge_search", "web_search"]
   - **MUST BE FIRST in subagent list if created**

**CREATING SUBAGENT TASKS:**

For each subagent, provide:

1. **task** (string): Multi-paragraph description with:
   ```
   Subagent: [Name]
   
   Objective: [Narrow scope - what to investigate]
   
   Questions to answer:
   - [Specific question 1 with expected format]
   - [Specific question 2 with units/calculations needed]
   - [Question 3 with risk classification requirement]
   
   Method hints:
   - [Calculation methods, standard values to use]
   - [Databases/sources to cite: PubChem, NIST, etc.]
   - [Risk classification: CRITICAL (>80%), HIGH (30-80%), MEDIUM (10-30%), LOW (<10%)]
   - [Mitigation requirement: propose solutions for each challenge]
   
   Context from extraction/enrichment:
   - [Mention data gaps from extraction_notes/data_uncertainties]
   - [Mention assumptions made: "O2 assumed 21%", "Temperature estimated"]
   - [Instruct how to handle uncertainty: "Quantify ±X% impact on results"]
   
   Deliverables:
   - [Table/list format with columns specified]
   - [Risk classification table if applicable]
   - [Prioritized recommendations]
   
   Dependencies: INDEPENDENT (or specify if dependent on another subagent)
   
   Tools needed: [list tool names or "none"]
   ```

2. **relevant_content** (JSON string): Extract ONLY fields needed for this subagent
   - Example: "{\"pollutant_list\": [...], \"process_parameters\": {...}}"
   - Do NOT pass entire enriched_facts.json

3. **tools** (array): ["oxytec_knowledge_search"], ["product_database"], ["web_search"], or []

**CRITICAL DATA QUALITY INSTRUCTIONS TO SUBAGENTS:**

In each subagent task description, you MUST mention:
- Which data points are measured vs. assumed
- Which uncertainties exist (from extraction_notes/data_uncertainties)
- How to quantify the impact of missing/uncertain data
- What additional measurements would reduce uncertainty

**EXAMPLE:**

Bad task instruction:
"Calculate LEL for the VOC mixture."

Good task instruction:
"Calculate LEL for the VOC mixture. NOTE: O2 content was not measured - assumed 21% (atmospheric air). Quantify the sensitivity: If actual O2 is 18-24%, how does LEL percentage change? If LEL calc shows >50% LEL, classify as CRITICAL risk and recommend O2 measurement before final design."

**DO NOT:**
- Include your own risk assessments in the planning document
- Make technology recommendations ("I think NTP is better...")
- Create data_quality_issues with severity ratings (subagents do this)
- Perform calculations (subagents do this)
```

### 🟡 TO MODIFY

#### Current "OUTPUT JSON" Section

**Modify the output structure:**

```json
{
  "enrichment_summary": "Brief summary of Phase 1 work: what was looked up, what was assumed, what remains uncertain (50-200 words)",
  "subagents": [
    {
      "task": "...",
      "relevant_content": "{...}",
      "tools": [...]
    }
  ],
  "reasoning": "Brief planning strategy for Phase 2: why these subagents, in this order (50-200 words)"
}
```

**Remove:**
- Any direct data_quality_issues in planner output

### ✅ VALIDATION CHECKLIST

After changes, verify:
- [ ] Phase 1 (enrichment) instructions are clear and actionable
- [ ] CAS lookup with web_search is explicit
- [ ] Phase 2 (orchestration) emphasizes "pure orchestrator" role
- [ ] Decision logic for creating subagents is explicit
- [ ] Instructions to pass data uncertainties to subagents are clear
- [ ] No business judgments or technology recommendations in planner role
- [ ] Output JSON includes enrichment_summary
- [ ] Planner does NOT create data_quality_issues

---

## 3. SUBAGENT Changes

### File: `prompt_subagent_v1_0_0.md`

### 🟢 TO ADD

#### A. Input Clarification (Insert at beginning of "EXECUTION REQUIREMENTS")

```markdown
**INPUT DATA CONTEXT:**

The data you receive has been enriched by the Planner:
- Missing CAS numbers may have been looked up
- Standard assumptions may have been made (e.g., O2=21%)
- Unit conversions may have been performed

The task description will explicitly mention:
- Which values are measured vs. assumed
- Data gaps and uncertainties
- How to handle missing information

**YOUR RESPONSIBILITY:**
- Quantify how uncertainties affect your analysis
- Provide sensitivity analysis for key assumptions
- Propose measurements that would reduce uncertainty
```

### 🟡 TO MODIFY

#### Execution Requirements Section

**ADD to point 9 (Propose mitigation strategies):**

```markdown
9. **Propose mitigation strategies**: For EVERY identified challenge/risk, provide specific, actionable recommendations:
   - What technical/operational measures could address this risk?
   - What additional data/testing would reduce uncertainty?
   - What is the estimated effort/timeline for mitigation?
   - **COST RESTRICTION**: ONLY include cost estimates if retrieved from product_database tool. If not available, write "Cost TBD - requires product selection and quotation"
   - Are there "quick wins" that significantly reduce risk with minimal effort?
   - **NEW: If your analysis depends on an assumption (e.g., O2=21%), quantify the sensitivity:**
     - "If actual O2 is 18-24%, LEL changes by ±15%, risk classification unchanged"
     - "If flow is actually Nm3/h (not m3/h), reactor size increases 30%"
```

**ADD new point 12:**

```markdown
12. **Uncertainty quantification**: For each major conclusion, assess:
    - Data quality: HIGH (measured), MEDIUM (estimated with good basis), LOW (rough assumption)
    - Assumption sensitivity: "If assumption X is wrong by Y%, result changes by Z%"
    - Measurement needs: "Measuring [parameter] would reduce uncertainty from ±40% to ±10%"
```

### ✅ VALIDATION CHECKLIST

After changes, verify:
- [ ] Subagents understand they receive enriched data
- [ ] Uncertainty quantification requirements are explicit
- [ ] Sensitivity analysis is required for assumptions
- [ ] Cost restriction remains in place

---

## 4. RISK_ASSESSOR Changes

### File: `prompt_risk_assessor_v1_0_0.md`

### 🔴 TO REMOVE

#### A. "VETO POWER" Language
**Remove:**
- "Your assessment has VETO POWER over optimistic technical evaluations"
- Any implication that Risk Assessor overrules subagent findings

**Rationale:** Risk Assessor synthesizes, not overrules. Subagents are domain experts.

#### B. Re-assessment of Individual Subagent Work
**Remove or de-emphasize:**
- Instructions to re-evaluate individual technical findings
- Recalculating LEL, efficiency, costs, etc.

**Rationale:** Trust subagent expertise in their domains. Focus on interactions.

### 🟢 TO ADD

#### A. New Mission Statement (Replace current mission)

```markdown
**YOUR ROLE: Cross-Functional Risk Synthesizer**

You are NOT a technical reviewer who rechecks subagent calculations.
You are NOT a veto authority who overrules domain experts.

**YOU ARE:** A systems thinker who identifies risks that emerge from INTERACTIONS between domains.

**YOUR MISSION:**

1. **Identify Cross-Functional Risks:**
   - How do findings from different subagents combine to create bigger problems?
   - Example: VOC Agent says "formaldehyde formation" + Safety Agent says "ATEX Zone 2" + Economic Agent says "KAT needed +50k€"
     → YOU synthesize: "Carcinogenic by-product in ATEX zone requires expensive treatment + continuous monitoring + regulatory approval complexity → Project risk escalation"

2. **Recognize Risk Amplification:**
   - Single moderate risks that compound into severe problems
   - Cascade effects: One failure triggers others
   - Hidden dependencies between technical areas

3. **Find Blind Spots:**
   - Assumptions shared by ALL subagents that could be wrong
   - Data gaps that affect multiple domains
   - System-level risks no single subagent could see

4. **Assess Combined Uncertainty:**
   - If VOC Agent has ±20% uncertainty AND Flow Agent has ±15% uncertainty, what's the combined impact on reactor sizing?
   - Which uncertainties matter most for project success?

**WHAT YOU DO NOT DO:**
- Recalculate LEL values (trust Safety Agent)
- Re-evaluate technology selection (trust Technology Agent)
- Second-guess cost estimates (trust Economic Agent)
- Perform new domain-specific analyses

**WHAT YOU DO:**
- Synthesize findings into system-level view
- Identify risk interactions and combinations
- Assess whether multiple moderate risks add up to project failure
- Recommend system-level mitigation strategies
```

#### B. New Section: "ANALYSIS FRAMEWORK"

```markdown
**ANALYSIS FRAMEWORK:**

For each subagent result, extract:
1. Key findings (2-3 bullet points)
2. Risk classification and probability
3. Assumptions made
4. Uncertainties noted

Then perform:

**A. INTERACTION MATRIX:**
Create a mental model of how findings interact:

| Subagent A Finding | Subagent B Finding | Interaction Type | Combined Risk |
|--------------------|-------------------|------------------|---------------|
| Formaldehyde formation (70% prob) | ATEX Zone 2 required | Regulatory + Safety | CRITICAL: Carcinogen monitoring in ATEX zone |
| 2 parallel reactors needed | Limited space (per site_conditions) | Technical + Physical | HIGH: Modular design may not fit |

**B. ASSUMPTION CASCADE:**
Identify assumptions made by MULTIPLE subagents:
- If ALL subagents assumed O2=21%, what happens if it's actually 18%?
- If ALL subagents used "estimated" concentration, how does ±30% uncertainty propagate?

**C. FAILURE MODE COMBINATIONS:**
Which combinations of moderate problems create severe outcomes?
- MEDIUM: Fouling expected + MEDIUM: Limited maintenance access = HIGH: Unacceptable downtime
- MEDIUM: By-product formation + LOW: Customer inexperienced = HIGH: Operational complexity too great

**D. UNCERTAINTY AGGREGATION:**
Which uncertainties dominate project risk?
- If 5 subagents each have ±15% uncertainty, combined uncertainty might be ±35%
- Which measurement would reduce uncertainty most across multiple domains?

**E. SYSTEM-LEVEL MITIGATION:**
What actions address multiple risks simultaneously?
- Pilot test: Reduces technology uncertainty + validates by-product formation + demonstrates ATEX compliance
- O2 measurement: Resolves LEL calc + NTP power sizing + oxidation kinetics
```

#### C. New Output Format Section

```markdown
**OUTPUT FORMAT:**

{
  "subagent_summaries": [
    {
      "subagent": "VOC Chemistry Specialist",
      "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
      "risk_level": "CRITICAL | HIGH | MEDIUM | LOW",
      "confidence": "HIGH | MEDIUM | LOW"
    },
    ...
  ],
  
  "cross_functional_risks": [
    {
      "risk_description": "Clear description of the interaction risk",
      "affected_domains": ["VOC Chemistry", "Safety/ATEX", "Economic"],
      "combined_severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "probability_estimate": "% or qualitative",
      "evidence": "Which subagent findings support this",
      "mitigation": "System-level action that addresses multiple domains"
    },
    ...
  ],
  
  "assumption_cascade_analysis": [
    {
      "shared_assumption": "O2 = 21%",
      "affected_subagents": ["Safety", "VOC Chemistry", "Technology Screening"],
      "sensitivity": "If wrong by ±X%, impact is Y",
      "measurement_recommendation": "Measure O2 before final design"
    },
    ...
  ],
  
  "uncertainty_prioritization": [
    {
      "uncertainty_source": "VOC concentration (estimated, not measured)",
      "impact_domains": ["Reactor sizing", "Cost estimation", "Efficiency prediction"],
      "uncertainty_magnitude": "±30%",
      "risk_contribution": "HIGH - Dominates design uncertainty",
      "measurement_priority": "CRITICAL"
    },
    ...
  ],
  
  "combined_risk_assessment": {
    "overall_project_risk": "CRITICAL | HIGH | MEDIUM | LOW",
    "confidence_in_assessment": "HIGH | MEDIUM | LOW",
    "key_risk_drivers": ["Risk 1", "Risk 2", "Risk 3"],
    "project_killing_scenarios": ["Scenario 1: probability X%", ...],
    "required_actions_before_proceeding": ["Action 1", "Action 2", ...]
  },
  
  "recommendation": {
    "decision": "PROCEED | PROCEED_WITH_CAUTION | DO_NOT_PROCEED",
    "justification": "Based on combined risk analysis...",
    "conditions_for_proceed": ["Condition 1", "Condition 2", ...],
    "alternative_approaches": ["If X is too risky, consider Y"]
  }
}
```

### 🟡 TO MODIFY

#### Quantified Output Requirements Section

**CHANGE FOCUS FROM:**
"Quantify individual failure scenarios (fouling rates, corrosion, costs)"

**TO:**
"Quantify combined risk scenarios:
- How do multiple moderate risks combine?
- What is the probability of simultaneous challenges?
- Which uncertainty dominates project risk?"

### ✅ VALIDATION CHECKLIST

After changes, verify:
- [ ] "VETO POWER" language removed
- [ ] Role changed from "reviewer" to "synthesizer"
- [ ] Focus is on cross-functional risks, not individual technical review
- [ ] Interaction matrix framework is clear
- [ ] Assumption cascade analysis is required
- [ ] Output format includes cross_functional_risks section
- [ ] Trust in subagent domain expertise is explicit

---

## 5. WRITER Changes

### File: `prompt_writer_v1_0_0.md`

### 🟢 TO ADD

#### A. Explicit Input Definition (Insert at beginning)

```markdown
**INPUTS YOU RECEIVE:**

1. **Subagent Reports:**
   - VOC Chemistry Specialist findings
   - Technology Screening recommendations
   - Safety/ATEX assessment
   - Economic analysis
   - Regulatory compliance review
   - (Other specialists as relevant)

2. **Risk Assessor Synthesis:**
   - Cross-functional risk analysis
   - Assumption cascade assessment
   - Combined risk evaluation
   - System-level recommendations

**INPUTS YOU DO NOT RECEIVE:**

❌ Original customer documents
❌ extracted_facts.json from Extractor
❌ enriched_facts.json from Planner
❌ Individual subagent prompts/instructions
❌ Any raw data

**CRITICAL RULE:**

If you find yourself wanting information from the original documents or raw data:
→ YOU ARE DOING SOMETHING WRONG

Everything you need is in the subagent reports and Risk Assessor synthesis.
If something is missing from those inputs, the problem is upstream (subagent scope or Risk Assessor synthesis), not with you.

**DO NOT:**
- Invent data or assumptions
- Make technical assessments beyond what subagents provided
- Add your own risk classifications
- Speculate on what documents might have said
```

#### B. Integration Guidance (Insert before "REPORTING STRUCTURE")

```markdown
**HOW TO INTEGRATE SUBAGENT FINDINGS:**

1. **For "VOC-Zusammensetzung und Eignung" section:**
   - Synthesize VOC Chemistry Specialist findings
   - Use Technology Screening Specialist recommendations
   - Incorporate any relevant findings from Carcinogen Risk Specialist

2. **For "Positive Faktoren" section:**
   - Extract positive findings from ALL subagents
   - Use Risk Assessor synthesis to understand which positives are most robust
   - Priority: Measurable benefits > Qualitative advantages

3. **For "Kritische Herausforderungen" section:**
   - Synthesize risk findings from ALL subagents
   - **CRITICAL:** Prioritize Risk Assessor's cross-functional risks over individual subagent risks
   - If Risk Assessor identified a CRITICAL combined risk, it MUST appear in this section
   - Include uncertainty-driven challenges from Risk Assessor's uncertainty_prioritization

4. **For "Zusammenfassung" section:**
   - Overall assessment MUST align with Risk Assessor's recommendation
   - If Risk Assessor says "DO_NOT_PROCEED", final assessment cannot be "GUT GEEIGNET"
   - If Risk Assessor identified project-killing combinations, summary must reflect this
   - Balance: Acknowledge positives but don't sugarcoat critical risks

**RISK ASSESSOR INTEGRATION PRIORITY:**

The Risk Assessor's cross_functional_risks and combined_risk_assessment have HIGHER priority than individual subagent findings when there is a conflict.

Why? Because Risk Assessor sees the system-level view that individual subagents cannot.

Example:
- VOC Agent: "Formaldehyde formation is manageable with KAT" (classified as MEDIUM)
- Safety Agent: "ATEX Zone 2 is standard, not a blocker" (classified as MEDIUM)
- Economic Agent: "KAT adds 45k€" (classified as MEDIUM)
- Risk Assessor: "COMBINATION of carcinogenic by-product + ATEX + expensive treatment + customer in Algeria (regulatory uncertainty) + customer inexperienced = CRITICAL combined risk"

→ Your report should reflect the CRITICAL assessment from Risk Assessor, not the individual MEDIUM ratings.
```

### 🟡 TO MODIFY

#### "RISK ASSESSMENT INTEGRATION" Section (currently in prompt)

**REPLACE with:**

```markdown
**RISK ASSESSOR INTEGRATION (MANDATORY):**

The Risk Assessor's synthesis MUST be reflected in your final report:

1. **Zusammenfassung:**
   - Final assessment (GUT GEEIGNET | MACHBAR | SCHWIERIG) must align with Risk Assessor's recommendation
   - If Risk Assessor says "DO_NOT_PROCEED", you cannot conclude "GUT GEEIGNET"
   - If Risk Assessor says "PROCEED_WITH_CAUTION", you likely conclude "MACHBAR" or "SCHWIERIG"

2. **Kritische Herausforderungen:**
   - **MUST include** Risk Assessor's cross-functional risks
   - Priority: System-level risks > Individual domain risks
   - Use Risk Assessor's probability estimates and combined severity classifications
   - Example: "Kombination aus karzinogenem Nebenprodukt, ATEX-Zone-2-Anforderung und kostenintensiver Katalysator-Nachbehandlung erhöht Projektkomplexität erheblich (Risiko: HOCH, Wahrscheinlichkeit 60%)"

3. **Positive Faktoren:**
   - Use Risk Assessor's confidence assessments
   - If Risk Assessor noted high uncertainty in a positive factor, acknowledge it
   - Example: "NTP gut geeignet für Ethylacetat (Wirkungsgrad >95% erwartet, Konfidenz: HOCH basierend auf Literatur)"

**CRITICAL:**
Do not create artificial balance. If Risk Assessor identified dominant critical risks, your report should reflect that reality, not seek 50/50 positive/negative balance.
```

### ✅ VALIDATION CHECKLIST

After changes, verify:
- [ ] Explicit input definition added (what Writer receives and does NOT receive)
- [ ] Integration guidance for each report section is clear
- [ ] Risk Assessor priority over individual subagents is explicit
- [ ] Rule against inventing data is emphasized
- [ ] Guidance on handling uncertainty/assumptions from Risk Assessor

---

## 6. Cross-Cutting Changes

### All Prompts

#### A. Cost Estimation Restriction (Verify in all prompts)

**Ensure this appears in:**
- PLANNER: When creating Economic Analysis subagent task
- SUBAGENT: In execution requirements
- RISK_ASSESSOR: When synthesizing economic findings

**Standard language:**
```
**COST ESTIMATION RESTRICTION:**
Cost information (CAPEX/OPEX/€ amounts) is ONLY permitted if retrieved from product_database tool with actual pricing data.
If cost estimation is needed but database pricing is unavailable, state: "Cost TBD - requires product selection and quotation"
NEVER use phrases like "estimated €X", "approximately €Y", "typical cost €Z" without database source.
```

#### B. Tool Usage Consistency

**Verify tool names are consistent:**
- `oxytec_knowledge_search` (not `oxytec_search` or `knowledge_search`)
- `product_database` (not `product_db` or `oxytec_products`)
- `web_search` (not `search_web` or `google_search`)

---

## 7. Testing & Validation

### After Implementation

**Test Case 1: Minimal Data (Stress Test)**
- Input: Only substance name, flow rate, temperature
- Expected: Extractor creates many extraction_notes, Planner enriches what's possible, creates subagents with explicit uncertainty instructions

**Test Case 2: Carcinogen Present**
- Input: Document mentions "Formaldehyd" or "ethylene oxide"
- Expected: Extractor does NOT flag it, Planner creates Carcinogen Risk Specialist subagent, Risk Assessor synthesizes carcinogen + other risks

**Test Case 3: Customer Questions**
- Input: Document contains "Frage: Ist NTP oder UV besser?"
- Expected: Extractor captures in customer_specific_questions, Planner creates Customer Question Response Specialist as FIRST subagent

**Test Case 4: Conflicting Data**
- Input: Two documents with different flow rates
- Expected: Extractor extracts both with notes, Planner resolves in enrichment, documents which source was used

**Test Case 5: Cost Request**
- Input: Customer asks "Was kostet das?"
- Expected: Planner creates Economic subagent with product_database tool, subagent uses ONLY database pricing or states "Cost TBD"

---

## 8. Migration Notes

### Backward Compatibility

**extracted_facts.json:**
- Keep `data_quality_issues` field as empty array `[]` for backward compatibility
- Add new `extraction_notes` field

**Planner output:**
- Add `enrichment_summary` field
- Existing fields remain compatible

**Risk Assessor output:**
- Old structure can coexist with new structure
- Writer should handle both old format and new format gracefully during transition

### Rollout Strategy

**Phase 1: Extractor + Planner**
- Update Extractor to use extraction_notes instead of data_quality_issues
- Update Planner to perform enrichment and create better subagent tasks
- Test with historical cases

**Phase 2: Subagent + Risk Assessor**
- Update Subagent prompt with input context and uncertainty requirements
- Update Risk Assessor to focus on synthesis vs. review
- Test with Phase 1 outputs

**Phase 3: Writer**
- Update Writer with explicit input definition and Risk Assessor integration rules
- Test full pipeline

---

## 9. Summary of Key Changes

| Agent | Key Change | Impact |
|-------|-----------|--------|
| **EXTRACTOR** | Remove business logic, add extraction_notes | Simpler, more focused, ~50% shorter prompt |
| **PLANNER** | Add Phase 1 enrichment, pure orchestrator in Phase 2 | More powerful, ensures subagents get quality data |
| **SUBAGENT** | Emphasize uncertainty quantification, sensitivity analysis | More robust analyses with confidence levels |
| **RISK_ASSESSOR** | Shift from reviewer to synthesizer, focus on cross-functional risks | Identifies system-level risks, no redundant work |
| **WRITER** | Explicit input definition, Risk Assessor priority | Clearer role, better integration of synthesis |

---

## 10. Questions for Implementation Team

1. **Extractor backward compatibility:** Should we keep `data_quality_issues` as empty array, or remove field entirely and update downstream consumers?

2. **Planner enrichment phase:** Should CAS lookups be cached somewhere to avoid repeated web searches across sessions?

3. **Risk Assessor renaming:** Should we rename RISK_ASSESSOR to INTEGRATION_SYNTHESIZER in code, or keep name but change mission?

4. **Testing coverage:** Do we have test cases that cover all trigger conditions for subagent creation?

5. **Performance:** Phase 1 enrichment in Planner will add latency (web searches for CAS numbers). Is this acceptable?

---

## 11. ADDENDUM - Critical Enhancements (v1.1)

**Date Added:** 2025-10-23
**Reason:** Address identified gaps in error handling, validation, and conflict resolution
**Status:** Critical for PLANNER v2.0.0 and WRITER v1.1.0 implementation

This addendum provides **defensive coding strategies** to ensure robustness of the refactored architecture. These enhancements should be implemented during Phase 2-4 of the refactoring.

---

### 11.1 PLANNER Phase 1: Error Handling & Graceful Degradation

**Problem:** Phase 1 enrichment involves external tool calls (web_search) that can fail. Without error handling, a single failed CAS lookup could stall the entire workflow.

**Solution:** Add graceful degradation logic to PLANNER Phase 1.

#### 🟢 TO ADD to `planner_v2_0_0.py`

Insert this section AFTER "Phase 1: Data Enrichment" instructions:

```markdown
**PHASE 1 ERROR HANDLING (CRITICAL):**

Enrichment operations may fail (network timeout, rate limit, service unavailable). You MUST handle failures gracefully:

**1. CAS Number Lookup Failures:**

If web_search for CAS number fails:
- Leave cas_number as null (do NOT abort)
- Add to data_uncertainties:
  ```json
  {
    "field": "pollutant_list[0].cas_number",
    "uncertainty": "CAS lookup failed: [error type]",
    "impact": "Subagents cannot access substance properties from chemical databases. Recommend manual CAS lookup before final design.",
    "workaround": "Subagents will use substance name for literature search"
  }
  ```
- Continue with remaining enrichments

**Error Types:**
- `network_timeout`: Web search timed out after 10s
- `rate_limited`: Too many requests, try again later
- `service_unavailable`: Web search service is down
- `no_results_found`: Search completed but no CAS number found

**2. Partial Success Strategy:**

If some enrichments succeed and others fail:
- Document successes in enrichment_notes
- Document failures in data_uncertainties
- Proceed to Phase 2 (DO NOT abort entire workflow)

Example:
```json
{
  "enrichment_notes": [
    {"field": "pollutant_list[0].cas_number", "action": "looked_up", "source": "PubChem", "confidence": "HIGH"},
    {"field": "pollutant_list[1].cas_number", "action": "lookup_failed", "source": "web_search timeout", "confidence": "N/A"}
  ],
  "data_uncertainties": [
    {
      "field": "pollutant_list[1].cas_number",
      "uncertainty": "CAS lookup failed - network timeout",
      "impact": "Subagents will rely on substance name 'Toluol' for analysis"
    }
  ]
}
```

**3. Calculation Failures:**

If unit conversion calculation fails (e.g., temperature missing):
- Keep original value
- Add uncertainty note
- Flag for subagent investigation

Example:
```json
{
  "enrichment_notes": [
    {
      "field": "process_parameters.flow_rate_normalized",
      "action": "calculation_failed",
      "reason": "Temperature not provided - cannot convert m3/h to Nm3/h",
      "confidence": "N/A"
    }
  ],
  "data_uncertainties": [
    {
      "field": "process_parameters.flow_rate_normalized",
      "uncertainty": "Cannot normalize flow rate without temperature",
      "impact": "Reactor sizing may have ±30% uncertainty if volume is at non-standard conditions"
    }
  ]
}
```

**4. Tool Unavailability:**

If web_search tool is completely unavailable:
- Skip all CAS lookups
- Add enrichment_summary note: "CAS lookups skipped - web_search tool unavailable. Subagents will use substance names."
- Continue to Phase 2 (degraded mode, but functional)

**5. Maximum Retry Policy:**

- Retry web_search once on timeout (wait 2s)
- If second attempt fails: Record failure and continue
- DO NOT retry more than once (avoid workflow delays)

**VALIDATION RULE:**

Before proceeding to Phase 2, verify:
- enriched_facts has at least some data (not completely empty)
- enrichment_notes documents what was attempted
- data_uncertainties flags all failures with impact assessment

If enriched_facts is empty → ABORT and return error to user: "Critical failure: Unable to enrich extracted data. Manual review required."
```

#### Code Implementation Pattern

```python
# backend/app/agents/nodes/planner.py

async def enrich_cas_numbers(pollutant_list: list) -> tuple[list, list, list]:
    """Enrich CAS numbers with graceful error handling."""
    enrichment_notes = []
    data_uncertainties = []

    for i, pollutant in enumerate(pollutant_list):
        if pollutant.get("cas_number") is None:
            try:
                # Attempt CAS lookup with timeout
                cas_result = await web_search_with_retry(
                    query=f"{pollutant['name']} CAS number",
                    max_retries=1,
                    timeout=10
                )

                if cas_result:
                    pollutant["cas_number"] = cas_result
                    enrichment_notes.append({
                        "field": f"pollutant_list[{i}].cas_number",
                        "action": "looked_up",
                        "source": "web_search: PubChem",
                        "confidence": "HIGH"
                    })
                else:
                    # No results found
                    enrichment_notes.append({
                        "field": f"pollutant_list[{i}].cas_number",
                        "action": "lookup_failed",
                        "source": "web_search: no results",
                        "confidence": "N/A"
                    })
                    data_uncertainties.append({
                        "field": f"pollutant_list[{i}].cas_number",
                        "uncertainty": "CAS number not found in chemical databases",
                        "impact": "Subagents will use substance name for analysis"
                    })

            except TimeoutError:
                logger.warning("cas_lookup_timeout", substance=pollutant['name'])
                enrichment_notes.append({
                    "field": f"pollutant_list[{i}].cas_number",
                    "action": "lookup_failed",
                    "source": "web_search timeout",
                    "confidence": "N/A"
                })
                data_uncertainties.append({
                    "field": f"pollutant_list[{i}].cas_number",
                    "uncertainty": "CAS lookup failed - network timeout",
                    "impact": "Subagents cannot access chemical property databases"
                })

            except Exception as e:
                logger.error("cas_lookup_error", substance=pollutant['name'], error=str(e))
                # Continue with next pollutant
                data_uncertainties.append({
                    "field": f"pollutant_list[{i}].cas_number",
                    "uncertainty": f"CAS lookup failed - {type(e).__name__}",
                    "impact": "Manual CAS lookup recommended"
                })

    return pollutant_list, enrichment_notes, data_uncertainties
```

#### Test Requirements

```python
# tests/integration/test_planner_error_handling.py

def test_planner_cas_lookup_timeout():
    """Test graceful handling when CAS lookup times out."""
    extracted_facts = {
        "pollutant_list": [{"name": "Ethylacetat", "cas_number": None}]
    }

    with mock.patch('web_search', side_effect=TimeoutError):
        result = await planner_node({"extracted_facts": extracted_facts})

    # Should not crash
    assert "enriched_facts" in result
    assert "data_uncertainties" in result
    assert len(result["data_uncertainties"]) == 1
    assert "timeout" in result["data_uncertainties"][0]["uncertainty"].lower()

    # Should still create subagents
    assert len(result["subagent_definitions"]) >= 2

def test_planner_partial_cas_success():
    """Test handling when some CAS lookups succeed and others fail."""
    extracted_facts = {
        "pollutant_list": [
            {"name": "Ethylacetat", "cas_number": None},
            {"name": "Toluol", "cas_number": None},
            {"name": "Unknown Substance XYZ", "cas_number": None}
        ]
    }

    def mock_search(query):
        if "Ethylacetat" in query:
            return "141-78-6"
        elif "Toluol" in query:
            return "108-88-3"
        else:
            return None  # No results for unknown substance

    with mock.patch('web_search', side_effect=mock_search):
        result = await planner_node({"extracted_facts": extracted_facts})

    assert result["enriched_facts"]["pollutant_list"][0]["cas_number"] == "141-78-6"
    assert result["enriched_facts"]["pollutant_list"][1]["cas_number"] == "108-88-3"
    assert result["enriched_facts"]["pollutant_list"][2]["cas_number"] is None

    # Should document partial success
    assert len(result["enrichment_notes"]) == 3
    assert len(result["data_uncertainties"]) == 1
```

---

### 11.2 PLANNER Phase 1: Enrichment Validation & Self-Checks

**Problem:** PLANNER performs calculations (unit conversions, normalization) but is not a domain expert. Incorrect assumptions (e.g., using °F as °C) can propagate errors.

**Solution:** Add self-validation checks and confidence levels to enrichment.

#### 🟢 TO ADD to `planner_v2_0_0.py`

Insert this section AFTER "Unit Disambiguation" in Phase 1:

```markdown
**ENRICHMENT VALIDATION & CONFIDENCE LEVELS:**

After performing any calculation or assumption, you MUST validate and document confidence:

**1. Unit Validation:**

Before unit conversion, check for ambiguity:

Temperature units:
- If value >50 and unit not specified → Likely °F (not °C)
  Example: "113" without unit → Assume °F (45°C) if in US context, °C if in Europe
  Add uncertainty: "Temperature unit unclear - assumed [°F/°C] based on [location/typical range]"

- If value <50 and unit not specified → Likely °C
  Example: "45" without unit → Assume °C

Flow rate units:
- "m3/h" vs "Nm3/h" ambiguity:
  - If temperature provided: Can calculate Nm3/h
  - If temperature missing: Cannot normalize
  - Add uncertainty: "Flow rate normalization requires temperature - using actual conditions"

**2. Calculation Confidence Levels:**

For every calculated value, assign confidence:

```json
{
  "field": "process_parameters.flow_rate_normalized",
  "action": "calculated",
  "formula": "Nm3/h = m3/h × (273.15 / (273.15 + T_celsius))",
  "inputs": {"flow_rate": 2800, "temperature": 45, "unit": "degC"},
  "result": 2450,
  "confidence": "HIGH",
  "assumptions": ["Ideal gas law", "1 atm pressure", "Temperature in Celsius"]
}
```

**Confidence Criteria:**

- **HIGH:** Direct measurement converted using standard formula, all inputs reliable
  - Example: "Flow rate measured, temperature measured, standard formula applied"

- **MEDIUM:** Estimation used for one input, or standard assumption applied
  - Example: "Flow rate measured, O2 assumed 21% (atmospheric), LEL calculated"

- **LOW:** Multiple assumptions, or rough order-of-magnitude estimate
  - Example: "Humidity estimated based on industry average, flow rate from questionnaire (not measured)"

**3. Reasonableness Checks:**

After calculation, verify result is physically plausible:

Flow rate normalized (Nm3/h):
- Check: 0.5 < (Nm3/h / m3/h) < 1.5
- If outside range: Add uncertainty "Conversion factor seems unusual - verify temperature unit"

Oxygen content:
- Check: 10% < O2 < 25%
- If outside range: Flag as "O2 value outside atmospheric range - verify measurement"

VOC concentration after unit conversion:
- Check: Resulting concentration is same order of magnitude as original
- If differs by >10x: Add uncertainty "Unit conversion resulted in large change - verify original unit"

**4. Formula Documentation:**

Always document the formula used:

```json
{
  "field": "process_parameters.flow_rate_normalized",
  "formula": "Nm3/h = m3/h × (273.15 K / (273.15 K + T_celsius)) × (P_actual / 1.013 bar)",
  "reference": "Ideal gas law, assuming 1 atm reference pressure",
  "inputs_used": {
    "m3_per_hour": 2800,
    "temperature_celsius": 45,
    "pressure_bar": 1.013
  },
  "calculated_result": 2450,
  "confidence": "HIGH"
}
```

**5. Flag for Subagent Re-Validation:**

If confidence is MEDIUM or LOW, instruct relevant subagent to verify:

In subagent task description:
```
"NOTE: Flow rate normalization was calculated with confidence MEDIUM (temperature assumed from typical range).
Flow/Mass Balance Specialist should verify: If actual temperature differs by ±10°C, how does Nm3/h change?
Provide sensitivity analysis."
```

**VALIDATION RULE:**

Before proceeding to Phase 2:
- All calculations have documented confidence level
- All assumptions are explicitly stated
- Any MEDIUM/LOW confidence enrichments are flagged for subagent re-validation
```

#### Code Implementation Pattern

```python
# backend/app/agents/nodes/planner.py

def normalize_flow_rate(flow_rate_m3h: float, temp_celsius: float, pressure_bar: float = 1.013) -> dict:
    """Normalize flow rate to standard conditions with validation."""

    # Reasonableness check on inputs
    if temp_celsius < -50 or temp_celsius > 200:
        return {
            "result": None,
            "confidence": "LOW",
            "error": f"Temperature {temp_celsius}°C outside typical range (-50 to 200°C) - verify unit"
        }

    # Calculate
    conversion_factor = 273.15 / (273.15 + temp_celsius)
    flow_rate_nm3h = flow_rate_m3h * conversion_factor * (pressure_bar / 1.013)

    # Reasonableness check on result
    if not (0.5 < conversion_factor < 1.5):
        confidence = "LOW"
        warning = f"Conversion factor {conversion_factor:.2f} is unusual - verify temperature unit"
    else:
        confidence = "HIGH"
        warning = None

    return {
        "result": round(flow_rate_nm3h, 1),
        "formula": "Nm3/h = m3/h × (273.15 / (273.15 + T_celsius)) × (P / 1.013)",
        "inputs": {
            "m3_per_hour": flow_rate_m3h,
            "temperature_celsius": temp_celsius,
            "pressure_bar": pressure_bar
        },
        "confidence": confidence,
        "assumptions": ["Ideal gas law", "Reference: 0°C, 1.013 bar"],
        "warning": warning
    }
```

#### Test Requirements

```python
# tests/unit/test_planner_validation.py

def test_temperature_unit_detection():
    """Test that planner detects likely temperature unit errors."""

    # Fahrenheit used as Celsius (common error)
    result = normalize_flow_rate(flow_rate_m3h=2800, temp_celsius=113)
    assert result["confidence"] == "LOW"
    assert "verify" in result["warning"].lower()

    # Reasonable Celsius value
    result = normalize_flow_rate(flow_rate_m3h=2800, temp_celsius=45)
    assert result["confidence"] == "HIGH"
    assert result["warning"] is None

def test_calculation_documentation():
    """Test that all calculations are fully documented."""
    result = normalize_flow_rate(flow_rate_m3h=2800, temp_celsius=45)

    assert "formula" in result
    assert "inputs" in result
    assert "confidence" in result
    assert "assumptions" in result
    assert result["result"] is not None
```

---

### 11.3 PLANNER Phase 2: Subagent Creation Limits & Merging Rules

**Problem:** Complex inquiries could trigger 7-8 subagents, increasing cost and coordination complexity. No guidance on maximum limits or merging strategies.

**Solution:** Add explicit subagent limits and merging rules.

#### 🟢 TO ADD to `planner_v2_0_0.py`

Insert this section AFTER "Decision Logic: Which Subagents to Create":

```markdown
**SUBAGENT CREATION LIMITS (CRITICAL):**

To maintain cost efficiency and parallelization benefits:

**Maximum Subagents: 6**

Rationale:
- Parallel execution benefit peaks at 5-6 concurrent tasks
- Beyond 6: Diminishing returns, increased coordination overhead
- Cost constraint: Each subagent incurs LLM API cost

**Priority Ranking:**

When >6 subagents are triggered, use this priority system:

**Tier 0 - MANDATORY (always create):**
1. VOC Chemistry Specialist
2. Technology Screening Specialist

**Tier 1 - HIGH PRIORITY (safety-critical):**
3. Carcinogen Risk Specialist (if triggered)
4. Safety/ATEX Specialist (if triggered)

**Tier 2 - MEDIUM PRIORITY (commercial/regulatory):**
5. Regulatory Compliance Specialist (if triggered)
6. Customer Question Response Specialist (if triggered)
7. Economic Analysis Specialist (if triggered)

**Tier 3 - LOW PRIORITY (can be absorbed):**
8. Flow/Mass Balance Specialist (can be merged into Technology Screening)

**Subagent Merging Rules:**

If >6 subagents triggered, apply these merging strategies:

**Merge Rule 1: Safety & Carcinogen**
If BOTH Safety/ATEX AND Carcinogen Risk are triggered:
→ Create single "Safety & Carcinogen Risk Specialist"
- Task combines: LEL calculations + carcinogen detection + ATEX compliance
- Rationale: Both are safety-critical, overlapping regulatory concerns

**Merge Rule 2: Economic & Regulatory**
If BOTH Economic Analysis AND Regulatory Compliance are triggered:
→ Create single "Commercial Viability Specialist"
- Task combines: Cost estimation + regulatory compliance costs
- Rationale: Regulatory costs are part of CAPEX/OPEX

**Merge Rule 3: Absorb Flow/Mass Balance**
If Flow/Mass Balance triggered AND Technology Screening exists:
→ Absorb flow calculations into Technology Screening task
- Add to Technology Screening: "Include reactor sizing calculations and mass balance"
- Rationale: Technology selection requires sizing anyway

**Decision Tree Example:**

Scenario: Petroleum bilge water inquiry triggers 7 subagents

Triggered:
1. VOC Chemistry (MANDATORY)
2. Technology Screening (MANDATORY)
3. Safety/ATEX (O2 unknown)
4. Carcinogen Risk (petroleum + formaldehyde)
5. Regulatory Compliance (carcinogen present)
6. Flow/Mass Balance (unit ambiguity)
7. Economic Analysis (budget constraint)

Total: 7 subagents (exceeds limit of 6)

**Apply merging:**
- Merge Safety/ATEX + Carcinogen Risk → "Safety & Carcinogen Specialist"
- Absorb Flow/Mass Balance into Technology Screening

**Final subagents (6 total):**
1. VOC Chemistry Specialist
2. Technology Screening Specialist (with flow calculations)
3. Safety & Carcinogen Risk Specialist (merged)
4. Regulatory Compliance Specialist
5. Economic Analysis Specialist
6. Customer Question Response Specialist (if questions exist)

**Implementation in Output:**

Document merging decisions in reasoning field:

```json
{
  "reasoning": "8 subagents initially triggered. Applied merging: (1) Combined Safety/ATEX + Carcinogen Risk into single Safety & Carcinogen specialist due to overlapping regulatory concerns. (2) Absorbed Flow/Mass Balance into Technology Screening (reactor sizing required anyway). Final: 6 subagents, respecting cost/complexity limits."
}
```

**Exception: Customer Questions**

If Customer Question Response Specialist is triggered, it MUST be created (high business priority).
If this causes >6 subagents: Merge Economic + Regulatory instead.

**VALIDATION RULE:**

Before returning subagent_definitions:
- Count total subagents
- If >6: Apply merging rules
- Document merging decisions in reasoning field
- Verify mandatory subagents (VOC Chemistry, Technology Screening) are included
```

#### Code Implementation Pattern

```python
# backend/app/agents/nodes/planner.py

def apply_subagent_limits(triggered_subagents: list[dict], max_subagents: int = 6) -> tuple[list[dict], str]:
    """Apply subagent creation limits and merging rules."""

    if len(triggered_subagents) <= max_subagents:
        return triggered_subagents, ""

    reasoning = []
    merged_subagents = []

    # Separate by priority
    mandatory = [s for s in triggered_subagents if s["priority"] == "MANDATORY"]
    high = [s for s in triggered_subagents if s["priority"] == "HIGH"]
    medium = [s for s in triggered_subagents if s["priority"] == "MEDIUM"]
    low = [s for s in triggered_subagents if s["priority"] == "LOW"]

    # Always include mandatory
    merged_subagents.extend(mandatory)

    # Check if merging rules apply
    safety_atex = next((s for s in high if "Safety" in s["name"]), None)
    carcinogen = next((s for s in high if "Carcinogen" in s["name"]), None)

    if safety_atex and carcinogen:
        # Merge safety and carcinogen
        merged_subagents.append({
            "name": "Safety & Carcinogen Risk Specialist",
            "task": f"{safety_atex['task']}\n\nADDITIONALLY:\n{carcinogen['task']}",
            "tools": list(set(safety_atex.get("tools", []) + carcinogen.get("tools", [])))
        })
        reasoning.append("Merged Safety/ATEX + Carcinogen Risk into single specialist (overlapping safety concerns)")
        high.remove(safety_atex)
        high.remove(carcinogen)

    # Add remaining high priority
    merged_subagents.extend(high)

    # Add medium priority until limit reached
    remaining_slots = max_subagents - len(merged_subagents)
    merged_subagents.extend(medium[:remaining_slots])

    if len(medium) > remaining_slots:
        reasoning.append(f"Omitted {len(medium) - remaining_slots} lower-priority subagents to respect 6-subagent limit")

    reasoning_text = "; ".join(reasoning)
    return merged_subagents, reasoning_text
```

#### Test Requirements

```python
# tests/unit/test_planner_limits.py

def test_subagent_merging():
    """Test that planner merges subagents when >6 are triggered."""

    triggered = [
        {"name": "VOC Chemistry", "priority": "MANDATORY"},
        {"name": "Technology Screening", "priority": "MANDATORY"},
        {"name": "Safety/ATEX", "priority": "HIGH"},
        {"name": "Carcinogen Risk", "priority": "HIGH"},
        {"name": "Regulatory", "priority": "MEDIUM"},
        {"name": "Economic", "priority": "MEDIUM"},
        {"name": "Flow/Mass Balance", "priority": "LOW"},
        {"name": "Customer Questions", "priority": "MEDIUM"}
    ]

    result, reasoning = apply_subagent_limits(triggered, max_subagents=6)

    assert len(result) <= 6
    assert any("Safety & Carcinogen" in s["name"] for s in result)
    assert "merged" in reasoning.lower() or "absorbed" in reasoning.lower()

def test_customer_questions_priority():
    """Test that customer questions are always included."""

    triggered = [
        {"name": "VOC Chemistry", "priority": "MANDATORY"},
        {"name": "Technology Screening", "priority": "MANDATORY"},
        {"name": "Customer Questions", "priority": "MEDIUM", "has_questions": True},
        # ... 5 more subagents
    ]

    result, _ = apply_subagent_limits(triggered, max_subagents=6)

    assert any("Customer Questions" in s["name"] for s in result)
```

---

### 11.4 WRITER: Conflict Resolution Between Risk Assessor & Subagents

**Problem:** Risk Assessor has "higher priority" than subagents, but what if Risk Assessor is wrong or overestimates a risk? WRITER needs rules for handling disagreements.

**Solution:** Add conflict resolution protocol based on confidence levels and evidence transparency.

#### 🟢 TO ADD to `writer_v1_1_0.py`

Insert this section AFTER "Risk Assessor Integration Priority":

```markdown
**CONFLICT RESOLUTION PROTOCOL:**

If Risk Assessor and a Subagent provide conflicting assessments, follow this protocol:

**1. Identify Conflicts:**

A conflict exists when:
- Risk Assessor classifies a risk as CRITICAL/HIGH
- Subagent's domain-specific analysis shows LOW/MEDIUM for the same risk
- OR: Risk probabilities differ by >30% (e.g., Risk Assessor: 70%, Subagent: 10%)

**2. Compare Confidence Levels:**

Check confidence metadata in both outputs:

Risk Assessor:
```json
{
  "cross_functional_risks": [
    {
      "risk_description": "Formaldehyde formation creates ATEX monitoring complexity",
      "combined_severity": "CRITICAL",
      "confidence": "MEDIUM"
    }
  ]
}
```

Subagent (VOC Chemistry):
```json
{
  "findings": [
    {
      "substance": "Ethyl acetate",
      "formation_probability": "5%",
      "evidence": "Thermodynamic calculations + 3 literature sources",
      "confidence": "HIGH"
    }
  ]
}
```

**Decision Rule:**

If Subagent confidence > Risk Assessor confidence:
→ **Present both perspectives** (do NOT hide the conflict)

**3. Transparency in Report:**

When conflict exists, use this format in "Kritische Herausforderungen":

```markdown
**Formaldehyd-Bildungsrisiko (Konflikt in Bewertung):**

**Risk Assessor Einschätzung (Konfidenz: MITTEL):**
Die Kombination aus möglicher Formaldehyd-Bildung und ATEX-Zone-2-Anforderung wurde als KRITISCH eingestuft (kombinierte Schwere durch Überschneidung von Sicherheitsanforderungen).

**VOC-Chemie-Spezialist Analyse (Konfidenz: HOCH, basierend auf thermodynamischen Berechnungen):**
Die Wahrscheinlichkeit der Formaldehyd-Bildung aus Ethylacetat bei NTP-Oxidation beträgt 5% (3 Literaturquellen + stöchiometrische Analyse). Bei dieser niedrigen Wahrscheinlichkeit ist das Einzelrisiko als NIEDRIG einzustufen.

**Empfehlung:**
Vor Endauslegung experimentelle Validierung durchführen (Pilot-Test mit GC-MS-Analyse der Oxidationsprodukte, €12k, 4 Wochen). Dies reduziert Unsicherheit von 5-70% auf <2% und ermöglicht fundierte ATEX-Klassifizierung.
```

**4. Conflict Resolution Decision Tree:**

```
IF Subagent confidence = HIGH AND Risk Assessor confidence = MEDIUM/LOW:
  → Present both perspectives
  → Recommend validation experiment
  → Do NOT hide subagent's evidence

ELSE IF Risk Assessor confidence = HIGH AND Subagent confidence = MEDIUM/LOW:
  → Trust Risk Assessor (system-level view may reveal what subagent missed)
  → Mention subagent's finding as "jedoch" (however) note

ELSE IF both confidence = HIGH but disagree:
  → This is a critical conflict - escalate
  → Report format: "Widersprüchliche Bewertungen mit hoher Konfidenz - manuelle Prüfung erforderlich"
  → List both analyses with full evidence

ELSE IF both confidence = LOW/MEDIUM:
  → Emphasize uncertainty
  → Recommend additional data collection before decision
```

**5. DO NOT Create False Consensus:**

❌ WRONG:
"Formaldehyd-Bildung ist möglich und stellt ein Risiko dar."
(Hides the 5% vs 70% disagreement)

✅ CORRECT:
"Formaldehyd-Bildung: Risk Assessor bewertet als KRITISCH (70% Wahrscheinlichkeit, Konfidenz MITTEL), jedoch zeigt VOC-Chemie-Analyse 5% Wahrscheinlichkeit (Konfidenz HOCH basierend auf Thermodynamik). Empfehlung: Experimentelle Validierung zur Klärung."

**6. Escalation Criteria:**

Escalate to human review (add to "Empfehlung" section) if:
- Both parties have HIGH confidence but disagree
- Risk Assessor classifies as CRITICAL but subagent shows negligible risk with strong evidence
- Multiple subagents contradict Risk Assessor's synthesis

Format:
```markdown
**⚠️ Hinweis für Prüfung:**
Widersprüchliche Risikobewertungen mit hoher Konfidenz identifiziert. Manuelle technische Prüfung vor Angebotsabgabe empfohlen.
```

**VALIDATION RULE:**

Before finalizing report:
- Check for conflicts (risk level differs by >2 categories)
- If conflict found: Verify both perspectives are documented
- If high-confidence conflict: Verify escalation note is included
```

#### Code Implementation Pattern

```python
# backend/app/agents/nodes/writer.py

def detect_conflicts(risk_assessor_output: dict, subagent_results: list[dict]) -> list[dict]:
    """Detect conflicts between Risk Assessor and Subagents."""

    conflicts = []

    for cross_risk in risk_assessor_output.get("cross_functional_risks", []):
        ra_severity = cross_risk["combined_severity"]  # CRITICAL, HIGH, MEDIUM, LOW
        ra_confidence = cross_risk.get("confidence", "MEDIUM")

        # Find related subagent finding
        for subagent in subagent_results:
            for finding in subagent.get("findings", []):
                if is_related(cross_risk["risk_description"], finding["description"]):
                    subagent_severity = finding.get("severity", "MEDIUM")
                    subagent_confidence = finding.get("confidence", "MEDIUM")

                    # Check for conflict
                    severity_gap = severity_to_number(ra_severity) - severity_to_number(subagent_severity)

                    if abs(severity_gap) >= 2:  # 2+ level difference
                        conflicts.append({
                            "risk_topic": cross_risk["risk_description"],
                            "risk_assessor": {
                                "severity": ra_severity,
                                "confidence": ra_confidence,
                                "reasoning": cross_risk.get("evidence", "")
                            },
                            "subagent": {
                                "name": subagent["name"],
                                "severity": subagent_severity,
                                "confidence": subagent_confidence,
                                "evidence": finding.get("evidence", "")
                            },
                            "resolution": resolve_conflict(ra_confidence, subagent_confidence)
                        })

    return conflicts

def resolve_conflict(ra_conf: str, sub_conf: str) -> str:
    """Determine how to resolve conflict based on confidence levels."""

    if sub_conf == "HIGH" and ra_conf in ["MEDIUM", "LOW"]:
        return "present_both_favor_subagent"
    elif ra_conf == "HIGH" and sub_conf in ["MEDIUM", "LOW"]:
        return "trust_risk_assessor"
    elif ra_conf == "HIGH" and sub_conf == "HIGH":
        return "escalate"
    else:
        return "emphasize_uncertainty"
```

#### Test Requirements

```python
# tests/integration/test_writer_conflict_resolution.py

def test_conflict_detection():
    """Test that writer detects conflicts between Risk Assessor and subagents."""

    risk_assessor_output = {
        "cross_functional_risks": [
            {
                "risk_description": "Formaldehyde formation",
                "combined_severity": "CRITICAL",
                "confidence": "MEDIUM"
            }
        ]
    }

    subagent_results = [
        {
            "name": "VOC Chemistry Specialist",
            "findings": [
                {
                    "description": "Formaldehyde formation from ethyl acetate",
                    "probability": "5%",
                    "severity": "LOW",
                    "confidence": "HIGH",
                    "evidence": "3 literature sources + thermodynamic calc"
                }
            ]
        }
    ]

    conflicts = detect_conflicts(risk_assessor_output, subagent_results)

    assert len(conflicts) == 1
    assert conflicts[0]["resolution"] == "present_both_favor_subagent"

def test_report_includes_both_perspectives():
    """Test that final report documents both conflicting perspectives."""

    # ... setup conflict scenario ...

    report = await writer_node(state_with_conflict)

    # Report should include both Risk Assessor and Subagent views
    assert "Risk Assessor" in report["final_report"]
    assert "VOC-Chemie-Spezialist" in report["final_report"]
    assert "Konfidenz" in report["final_report"]
    assert "Empfehlung" in report["final_report"]  # Should have resolution recommendation
```

---

### 11.5 Implementation Priority

These enhancements should be implemented in this order:

**Phase 2 (PLANNER v2.0.0):**
1. ✅ **Section 11.1** - Error handling (CRITICAL - prevents workflow failures)
2. ✅ **Section 11.2** - Enrichment validation (HIGH - prevents error propagation)
3. ✅ **Section 11.3** - Subagent limits (MEDIUM - cost control)

**Phase 4 (WRITER v1.1.0):**
4. ✅ **Section 11.4** - Conflict resolution (HIGH - ensures report quality)

---

### 11.6 Validation Checklist - Addendum Items

After implementing addendum sections, verify:

**PLANNER v2.0.0:**
- [ ] Error handling: CAS lookup timeout doesn't crash workflow
- [ ] Error handling: Partial success documented correctly
- [ ] Validation: Temperature unit detection works
- [ ] Validation: Calculation confidence levels assigned
- [ ] Validation: Reasonableness checks flag outliers
- [ ] Limits: >6 subagents triggers merging rules
- [ ] Limits: Mandatory subagents always included
- [ ] Limits: Merging decisions documented in reasoning

**WRITER v1.1.0:**
- [ ] Conflict detection: Identifies disagreements
- [ ] Conflict resolution: Compares confidence levels
- [ ] Transparency: Both perspectives documented in report
- [ ] Escalation: High-confidence conflicts flagged for review

---

**End of Addendum v1.1**

For questions about addendum enhancements, contact: Andreas