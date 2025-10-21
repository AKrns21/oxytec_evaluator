"""Shared prompt fragments for agents.

This module contains reusable prompt components to ensure consistency
across all agents and reduce duplication.
"""

# Positive factors filtering guidance
POSITIVE_FACTORS_FILTER = """**POSITIVE FACTORS FILTERING (CRITICAL - PREVENT EXPERT CRITICISM):**

❌ DO NOT LIST AS POSITIVE FACTORS:
- Basic operational requirements: "continuous operation", "24/7 operation", "stable process control", "batch operation"
- Standard parameters: "flow rate in standard range", "temperature suitable", "pressure acceptable", "ambient temperature range 10-40 degC"
- Expected capabilities: "target value achievable with system", "no technical exclusion criteria", "proven technology for this application"
- Basic absence of problems: "no halogenated VOCs", "no ATEX issues", "no space constraints", "no dust", "no particles"
- Available infrastructure: "site has utilities", "sufficient space", "water available", "electricity available"
- Standard equipment features: "modular design possible", "proven technology", "established method", "Oxytec has experience"
- Normal parameter statements: "concentration in typical range", "volume flow in standard range", "suitable for NTP/UV/scrubber"

**SPECIFIC EXCLUSIONS (these appear frequently but are NOT positive factors):**
- ❌ "Kontinuierlicher Betrieb" / "Continuous operation" → Basic requirement for proper sizing
- ❌ "Ambient-Temperaturbereich liegt im Standardbereich" → Every industrial site has this
- ❌ "Keine halogenierten VOCs" → We can't treat halogens anyway, so their absence isn't a benefit to us
- ❌ "Volumenstrom im Standardbereich" → That's just normal sizing
- ❌ "TVOC-Konzentration behandelbar" → Expected capability, not an advantage
- ❌ "Oxytec-Systeme sind erprobt" → We wouldn't quote if technology wasn't proven
- ❌ "Keine ATEX-Zone erforderlich" → Standard installation approach

✅ DO LIST AS POSITIVE FACTORS (genuine advantages only - MUST include quantified benefit):
- Unusual chemical advantages WITH QUANTIFIED SAVINGS: "high VOC concentration enables autothermal operation (reduces energy costs by 40% vs dilute streams)"
- Existing compatible infrastructure WITH COST SAVINGS: "existing alkaline scrubber can be integrated (saves €150k CAPEX vs new installation)"
- Favorable process synergies WITH FINANCIAL IMPACT: "waste heat from process can pre-heat gas stream (€20k/year OPEX saving)"
- Customer technical capability WITH OPERATIONAL BENEFIT: "customer has in-house analytical lab (enables real-time optimization, reduces external testing costs €15k/year)"
- Regulatory advantages WITH COMPLIANCE BENEFIT: "site already has emission monitoring infrastructure (reduces compliance costs €30k, faster permit approval)"
- Unusual design advantages WITH CAPEX/OPEX IMPACT: "low dust load eliminates need for filtration stage (€80k CAPEX saving, -€12k/year filter replacement)"

**VALIDATION RULE (APPLY STRICTLY):**
For each positive factor, ask TWO questions:
1. "Would an expert say 'ja sonst würden wir das ja auch nicht machen' (yes, otherwise we wouldn't do this)?"
   If YES → Remove it (it's a basic requirement)
2. "Does this factor include a quantified cost/performance benefit compared to a typical project?"
   If NO → Remove it (it's too generic)

**BOTH criteria must be satisfied: genuine advantage AND quantified benefit**

**EXAMPLE FILTERING:**

WRONG: "Volumenstrom von 2800–3600 kg/h liegt im industriellen Standardbereich"
→ Expert: "That's just standard sizing, not an advantage!" ❌

WRONG: "Kontinuierlicher Produktionsbetrieb ermöglicht stabile Prozessführung"
→ Expert: "Ja sonst würden wir das ja auch nicht machen - continuous operation is assumed for proper design!" ❌

WRONG: "Ambient-Temperaturbereich (10–40 degC) liegt im Standardbereich für Oxytec-Anlagen"
→ Expert: "Every industrial site has this temperature range!" ❌

WRONG: "Keine halogenierten VOCs vorhanden, was Dioxinbildungsrisiko ausschließt"
→ Expert: "We can't treat halogens anyway with NTP/UV, so their absence isn't positive for us!" ❌

RIGHT: "Hohe VOC-Konzentration (1800 mg/Nm3) ermöglicht autotherme Betriebsweise mit 60% Energieeinsparung gegenüber verdünnten Strömen (<300 mg/Nm3)"
→ Expert: "Now that's a real technical advantage with quantified savings!" ✅

RIGHT: "Kunde hat bereits pH-Überwachung und Neutralisationsstation installiert, was direkte Integration des Wäschers ermöglicht (Einsparung €45k CAPEX)"
→ Expert: "That's genuinely helpful - most customers don't have this!" ✅

RIGHT: "Bestehende Dampfleitung (6 bar, 180 degC) kann für Katalysator-Regeneration genutzt werden (€35k CAPEX-Einsparung vs elektrische Heizung, -€8k/Jahr OPEX)"
→ Expert: "Excellent - that's a real project-specific advantage!" ✅

**MINIMUM STANDARD:** List 0-3 genuine positive factors with quantified benefits. **Better to list NONE than list basics or unquantified claims.**

**QUALITY CHECK:** If you list >3 positive factors, you're probably including basics. If any factor lacks a quantified benefit (€X saved, Y% reduction, Z improvement), remove it."""

# Carcinogen and hazardous substance database
CARCINOGEN_DATABASE = """**CARCINOGENIC & HIGHLY TOXIC SUBSTANCES (IARC/OSHA/EU CLP):**

**GROUP 1 CARCINOGENS (Known human carcinogens - CRITICAL severity):**
- Formaldehyde (methanal, CH2O, CAS 50-00-0)
- Ethylene oxide (oxirane, ETO, CAS 75-21-8)
- 1,3-Butadiene (CAS 106-99-0)
- Benzene (CAS 71-43-2)
- Vinyl chloride (CAS 75-01-4)
- 1,2-Dichloroethane (ethylene dichloride, CAS 107-06-2)
- Acrolein (2-propenal, CAS 107-02-8) - also highly toxic

**GROUP 2A CARCINOGENS (Probable human carcinogens - HIGH severity):**
- Acetaldehyde (ethanal, CAS 75-07-0)
- Propylene oxide (methyloxirane, PO, CAS 75-56-9)
- Styrene (vinyl benzene, CAS 100-42-5)
- Trichloroethylene (TCE, CAS 79-01-6)

**HIGHLY TOXIC INORGANICS (CRITICAL severity):**
- Hydrogen sulfide (H2S, CAS 7783-06-4) - acute toxicity, 10 ppm OSHA PEL
- Hydrogen cyanide (HCN, CAS 74-90-8) - acute toxicity, 10 ppm IDLH
- Phosgene (COCl2, CAS 75-44-5) - acute toxicity, 0.1 ppm PEL
- Chlorine (Cl2, CAS 7782-50-5) - acute toxicity, 1 ppm PEL
- Ammonia (NH3, CAS 7664-41-7) - 300 ppm IDLH

**DETECTION KEYWORDS (case-insensitive, with common variants):**
- Ethylene oxide: "ethylene oxide", "ETO", "oxirane", "1,2-epoxyethane"
- Propylene oxide: "propylene oxide", "PO", "methyloxirane", "1,2-epoxypropane"
- Formaldehyde: "formaldehyde", "methanal", "formalin", "HCHO"
- Acetaldehyde: "acetaldehyde", "ethanal", "acetic aldehyde"
- H2S: "hydrogen sulfide", "H2S", "hydrogen sulphide", "dihydrogen sulfide"
- Benzene: "benzene", "benzol" (not benzyl or benzoyl)
- Acrolein: "acrolein", "acrylaldehyde", "propenal"

**AUTOMATIC ESCALATION RULES:**
1. ANY Group 1 carcinogen detected → Flag as "CARCINOGEN GROUP 1 (IARC)" in data_quality_issues
2. Concentration >10 ppm (or >10 mg/Nm3 for formaldehyde) → Severity: CRITICAL
3. Concentration 1-10 ppm → Severity: HIGH
4. Process involves ethylene/propylene oxide (surfactant production) → Flag "CARCINOGEN RISK IN PRODUCTION PROCESS"
5. Oxidation of alcohols expected → Flag "FORMALDEHYDE/ACETALDEHYDE FORMATION RISK (oxidation by-products)"
6. **VOCs from petroleum/oily products OR waste oil/bilge/sludge** → Flag "FORMALDEHYDE FORMATION RISK from petroleum VOC oxidation (petroleum products contain alcohols, aromatics, alkanes that produce formaldehyde during plasma/UV oxidation)"
7. **Industry: waste management, oil refining, petrochemical** → Flag "FORMALDEHYDE FORMATION RISK from petroleum-derived VOCs"

**EXPERT WARNING CONTEXT:**
- Surfactant production commonly uses ethylene oxide and propylene oxide (both Group 1/2A carcinogens)
- **Petroleum products (crude oil, bilge water, oily sludges, tank washings) contain complex VOC mixtures including alcohols, aromatics, and alkanes that produce formaldehyde when oxidized via NTP/UV/ozone**
- Even without detailed VOC speciation, petroleum-based VOCs should be assumed to generate formaldehyde during oxidation
- These carcinogens may not appear in exhaust gas measurements but form during the treatment process"""

# Oxytec experience validation database
OXYTEC_EXPERIENCE_CHECK = """**OXYTEC TECHNOLOGY EXPERIENCE VALIDATION:**

**PROVEN OXYTEC TECHNOLOGIES (with documented case studies):**

✅ **NTP (Non-Thermal Plasma) - CEA Series:**
- VOC oxidation (alcohols, ketones, esters, aromatics)
- Typical industries: Printing, coating, food, pharmaceutical
- Proven: TVOC 10-5000 mg/Nm³, flow rates 500-50,000 Nm³/h
- NOT proven: H2S >50 ppm (electrode corrosion), halogens >100 ppm (HCl formation)

✅ **UV/Ozone - CFA Series:**
- VOC oxidation (aromatics, alkanes, some oxygenates)
- Typical industries: Chemical, textile, automotive
- Proven: TVOC 50-2000 mg/Nm³, aromatic-rich streams
- NOT proven: High sulfur compounds (ozone quenching), heavy particulates

✅ **Wet Scrubbers - CWA Series:**
- Acid gas removal (SO₂, HCl, HF, NH₃)
- Water-soluble VOCs (alcohols, ketones, organic acids)
- Typical industries: Chemical, metal treatment, wastewater
- Proven: SO₂ up to 2000 mg/Nm³, NH₃ up to 500 ppm
- NOT proven: SO₃/H₂SO₄ mist removal (requires demister), non-volatile surfactants

✅ **Catalytic Oxidation - KAT Series:**
- Aldehyde destruction (formaldehyde, acetaldehyde)
- Ozone destruction
- Typical: Post-treatment after NTP/UV for by-product removal
- Proven: HCHO up to 50 ppm, ozone up to 100 ppm

**TECHNOLOGIES OXYTEC DOES NOT HAVE:**
❌ Thermal oxidation (RTO, RCO)
❌ Activated carbon systems (except small polishing units)
❌ Biofilters
❌ Membrane separation
❌ Cryogenic condensation
❌ SO₃/H₂SO₄ acid mist elimination (specialized demisters)
❌ Non-volatile surfactant removal from gas phase
❌ Heavy metal removal

**VALIDATION RULES:**

1. **If recommendation includes technology Oxytec doesn't have** → Add to technical_risks:
```json
{{
  "category": "Technical",
  "description": "Recommended solution requires [technology] which Oxytec does not manufacture or have case study experience with",
  "severity": "HIGH",
  "mitigation": "Partner with specialized vendor for [technology] or redesign solution using proven Oxytec technologies"
}}
```

2. **If pollutant/concentration exceeds proven range** → Add to technical_risks:
```json
{{
  "category": "Technical",
  "description": "No documented Oxytec case studies for [industry] with [pollutant] at [concentration] mg/Nm³. Nearest reference: [describe closest case]",
  "severity": "HIGH",
  "mitigation": "Request sales team review of similar projects. Consider pilot testing (6-12 months, €150-300k) before full-scale commitment"
}}
```

3. **If industry is new to Oxytec** → Add to commercial_risks:
```json
{{
  "category": "Commercial",
  "description": "Limited Oxytec experience in [industry] sector may result in unforeseen operational challenges",
  "severity": "MEDIUM",
  "mitigation": "Conduct thorough site visit, request extended performance guarantee period, consider phased implementation"
}}
```

**EXPERT FEEDBACK CONTEXT:**
Comment: "Mit SO3 demistern hat oxytec keine Erfahrungen" (Oxytec has no experience with SO₃ demisters)
→ Don't recommend technologies Oxytec hasn't deployed! Be honest about experience gaps."""

# Unit formatting instructions (avoid encoding issues)
UNIT_FORMATTING_INSTRUCTIONS = """**UNIT FORMATTING (avoid encoding issues):**
Use plain ASCII characters for all units:
- Exponents: Write "m^3" or "m3" (not m³), "h^-1" or "h-1" (not h⁻¹)
- Temperature: Write "degC" or just "C" (not °C)
- Degrees: Write "deg" (not °)
- Micro: Write "ug" or "micro-g" (not μg)
- Subscripts: Write CO2, H2O, SO2 (not CO₂, H₂O, SO₂)

**Examples:**
✅ CORRECT: 5000 m3/h, 45 degC, 3.5 h-1, 850 mg/Nm3
❌ WRONG: 5000 m³/h, 45 °C, 3.5 h⁻¹, 850 mg/Nm³ (Unicode chars cause encoding errors)"""


# Confidence level criteria
CONFIDENCE_CRITERIA = """**CONFIDENCE LEVEL GUIDELINES:**

HIGH CONFIDENCE (>80% certainty):
- Claim supported by multiple independent sources (measurements, case studies, literature)
- Parameter values are directly measured (not estimated or assumed)
- Similar projects exist with documented outcomes
- Uncertainty in numerical estimates: <10%
- Example: "HIGH confidence: Toluene concentration 850 mg/Nm3 (measured via GC-MS in customer report Table 3)"

MEDIUM CONFIDENCE (50-80% certainty):
- Claim supported by single source or indirect evidence
- Parameter values are estimated using standard methods
- Similar projects exist but with some differences
- Uncertainty in numerical estimates: 10-30%
- Example: "MEDIUM confidence: Humidity estimated at 60% RH typical for chemical industry (actual measurement pending)"

LOW CONFIDENCE (<50% certainty):
- Claim based on expert judgment or broad analogy
- Parameter values are rough order-of-magnitude estimates
- No directly comparable projects found
- Uncertainty in numerical estimates: >30%
- Example: "LOW confidence: OPEX estimated at €20-40k/year based on similar scale (wide range due to missing operational data)"

**WHEN TO STATE CONFIDENCE:**
- For all quantitative estimates (efficiency, cost, sizing, risk probability)
- For technology selection recommendations
- For critical conclusions affecting go/no-go decisions
- Not needed for factual statements from customer documents ("The flow rate is 5000 m3/h" - this is a fact, not a claim)"""


# Mitigation strategy examples
MITIGATION_STRATEGY_EXAMPLES = """**MITIGATION STRATEGY EXAMPLES:**

❌ POOR: "Further investigation needed to assess corrosion risk"
✅ GOOD: "Commission 3-month material corrosion test with SS316L, Hastelloy C-276, and PTFE-coated samples in simulated exhaust conditions (€8k, 12 weeks). Expected outcome: Select optimal construction material, reduce long-term corrosion risk from HIGH (60%) to LOW (10%). Alternative quick win: Install pH monitoring and automated caustic dosing system to neutralize acids (€12k, 2 weeks to install, prevents 80% of corrosion scenarios)."

❌ POOR: "VOC analysis incomplete"
✅ GOOD: "Request detailed VOC speciation via GC-MS at 3 time points over production cycle to capture concentration variability (€2k, 2 weeks). This reduces sizing uncertainty from ±40% to ±10%, prevents over/under-sizing (potential €50k CAPEX impact). Immediate action: Phone call with customer EHS manager to discuss existing air quality monitoring data (0 cost, 1 day)."

❌ POOR: "ATEX compliance may be an issue"
✅ GOOD: "Current VOC concentration (850 mg/Nm3 toluene) is ~8% LEL - below Zone 2 threshold. Recommended approach: Install equipment outside ATEX zone with 3m ductwork extension (€5k, standard solution). If client requires in-zone installation: Specify Zone 2 Category 3 electrical equipment per IEC 60079 (+€15k CAPEX, 4 weeks longer lead time, reduces installation risk from MEDIUM 40% to LOW 10%)."

**KEY ELEMENTS OF GOOD MITIGATIONS:**
1. Specific action with concrete deliverable
2. Cost estimate (order of magnitude: €X k/M)
3. Timeline (days/weeks/months)
4. Quantified risk reduction (X% → Y%)
5. Alternatives (quick wins vs comprehensive solutions)"""
