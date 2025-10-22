**Prompt-Verbesserungen v1**
Datum: 20.10.2025

Drei kritische Anforderungen müssen erfüllt werden:

1. **RAG-Integration** für oxytec-Technologie-Constraints aus dem Vectorstore
2. **ATEX als Randnotiz**, nicht als Show-Stopper (da Installation meist außerhalb ATEX-Zone)
3. **Maximale Generizität** - keine Case-spezifischen Details in den Prompts

---

## KRITISCHE ANALYSE DER AKTUELLEN PROMPTS

### Hauptprobleme:

**Problem 1: Case-spezifische Details in Prompts**
- Planner-Beispiele nennen explizit "2-ethylhexanol", "surfactant production", "SO₂/SO₃"
- Subagent-Tasks sind zu sehr auf den PCC-Fall zugeschnitten
- Writer-Prompt erwähnt "Tensid-Produktion" als Beispiel

**Problem 2: Fehlende RAG-Integration**
- Es muss ein Vectorstore zeingerichtet werden auf den zugegriffen werden kann
- Technologie-Constraints (UV/Ozon, Wäscher) aus der JSON sind nicht verfügbar
- Subagenten "raten" was oxytec kann, statt nachzuschlagen

**Problem 3: ATEX-Übergewichtung**
- Risk Assessor behandelt ATEX als HIGH Risk (40%)
- Sollte eher MEDIUM-LOW sein mit Hinweis "meist außerhalb ATEX-Zone installiert"

**Problem 4: Plasma-Bias**
- Prompts fokussieren zu stark auf NTP
- UV/Ozon und Wäscher werden unterrepräsentiert
- Keine klare Guidance, wann welche Technologie passt

---

## VERBESSERUNGSVORSCHLÄGE

### 1. NEUES TOOL: `oxytec_knowledge_search`

**Zunächst muss ein neues Tool definiert werden für RAG-Zugriff:**

```python
# In app/agents/tools.py

async def oxytec_knowledge_search(query: str, max_results: int = 5) -> str:
    """
    Search oxytec's internal knowledge base (vectorstore) for technology 
    capabilities, application examples, and design guidelines.
    
    Use this tool to:
    - Find suitable oxytec technologies for specific pollutants/industries
    - Retrieve design parameters (GHSV, removal efficiencies, energy consumption)
    - Access case studies and application examples
    - Check technology limitations and constraints
    
    Args:
        query: Natural language search query (e.g., "UV ozone formaldehyde removal efficiency")
        max_results: Number of relevant documents to retrieve (default 5)
    
    Returns:
        Formatted text with relevant excerpts from oxytec documentation
    """
    # Implementation: Query vectorstore with embeddings
    # Return formatted results with source references
    pass

# Tool definition for Claude:
OXYTEC_KNOWLEDGE_TOOL = {
    "name": "oxytec_knowledge_search",
    "description": """Search oxytec's internal knowledge base for technology capabilities, 
    application examples, equipment specifications, and design guidelines. Use this to find 
    which oxytec technologies (NTP, UV/ozone, scrubbers) are suitable for specific pollutants 
    or industries, and retrieve performance data.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query describing pollutant, industry, or technical parameter"
            },
            "max_results": {
                "type": "integer",
                "description": "Number of results to return (1-10)",
                "default": 5
            }
        },
        "required": ["query"]
    }
}
```

---

### 2. EXTRACTOR.PY - Generischer machen

**Aktuelles Problem:** Zu spezifisch auf VOCs fokussiert.

**NEUER extraction_prompt:**

```python
extraction_prompt = f"""You are an agent responsible for extracting all explicit facts from industrial exhaust air treatment inquiry documents. These may include questionnaires, measurement reports, safety documents, permits, or process descriptions.

**Constraints:**
- Output only ONE valid JSON object following the schema below
- Do not add commentary, bullet points, or prose outside the JSON
- If a field is unknown use null or ""
- Always preserve original wording, units, decimal separators, and table structure
- For tables: include all rows/columns exactly as seen
- Properly escape all special characters in JSON strings (replace curly quotes with straight quotes)

**CRITICAL: Flag data quality issues**
For each missing or anomalous parameter, add an entry to "data_quality_issues" array:
- Duplicate identifiers (CAS numbers, substance names)
- Unusual parameter ranges (e.g., very low/high temperatures, pressures)
- Missing critical parameters (humidity, oxygen content, particle load)
- Inconsistent units or incompatible values

Documents:
{combined_text}

Extract the following information (if available):

1. **Pollutant Characterization**:
   - List of pollutants with names, concentrations, and units
   - Pollutant categories: VOCs, odors, inorganic gases (NH₃, H₂S, SO₂, HCl, etc.), particulates, bioaerosols
   - Total pollutant load (TVOC, Total-C, odor units, etc.)
   - Any measurement data tables (preserve all rows/columns)
   - Chemical formulas and CAS numbers where available

2. **Process Parameters**:
   - Exhaust air flow rate (preserve exact units: m³/h, Nm³/h, kg/h, etc.)
   - Gas temperature (exact value and unit)
   - Pressure (exact value and unit; note if positive/negative)
   - Humidity/relative humidity/dew point
   - Oxygen content (if specified)
   - Particulate/aerosol load (if specified)
   - Operating schedule (continuous, batch, hours per day, seasonal)

3. **Current Abatement Systems** (if any):
   - Existing treatment technologies in place
   - Current removal efficiencies or outlet concentrations
   - Problems with existing systems (fouling, OPEX, compliance issues)
   - Maintenance schedules and costs

4. **Industry and Process Context**:
   - Industry sector (chemical, food, printing, coating, wastewater, etc.)
   - Specific processes generating exhaust air
   - Production volumes or capacity
   - Raw materials used (relevant to pollutant composition)

5. **Requirements & Constraints**:
   - Target removal efficiency (%) or outlet concentration limits
   - Regulatory requirements (TA Luft, IED BAT, local permits, emission limits)
   - Space constraints (footprint, height, weight limits)
   - Energy consumption limits or targets
   - Budget constraints (CAPEX/OPEX)
   - ATEX classification (if mentioned: Zone 0/1/2, explosive atmospheres)
   - Safety requirements (fire protection, corrosion resistance, etc.)

6. **Site Conditions**:
   - Available utilities (electricity voltage/phases, water, compressed air, steam)
   - Installation location (indoor/outdoor, rooftop, ground level)
   - Ambient conditions (temperature range, humidity, corrosive environment)
   - Access constraints

7. **Timeline & Project Phase**:
   - Project timeline or urgency
   - Current project phase (inquiry, feasibility, detailed design, tender)

8. **Data Quality Issues** (CRITICAL - always populate):
   - List all missing standard parameters (e.g., "Humidity not specified")
   - Flag anomalies (e.g., "Duplicate CAS 104-76-7 for different substances")
   - Note unusual values (e.g., "Gas temperature 10°C unusually low for industrial exhaust")
   - Estimate impact: CRITICAL (prevents sizing), HIGH (±30% uncertainty), MEDIUM (±10-20%), LOW (<10%)

Return ONLY a valid JSON object. Preserve all original wording, numbers, and units exactly as they appear.
"""
```

**NEUE JSON-Schema-Ergänzung:**

```python
# In extraction_prompt, ergänze:
"""
JSON Schema must include:
{
  "pollutant_analysis": {
    "voc_compounds": [...],  // if VOCs present
    "inorganic_gases": [...],  // SO₂, NH₃, H₂S, HCl, etc.
    "odors": {...},  // odor units, description
    "particulates": {...},  // PM10, aerosols, mist
    "bioaerosols": {...}  // bacteria, spores (if applicable)
  },
  "process_parameters": {...},
  "current_abatement": {...},
  "application_context": {...},
  "requirements_constraints": {...},
  "site_conditions": {...},
  "data_quality_issues": [
    {
      "issue": "Missing parameter X",
      "impact": "CRITICAL/HIGH/MEDIUM/LOW",
      "typical_range": "For this industry: X-Y units",
      "recommendation": "Specific measurement method or assumption"
    }
  ]
}
"""
```

---

### 3. PLANNER.PY - Maximal generisch & mit RAG

**Hauptänderungen:**
- Entferne ALLE case-spezifischen Beispiele (SO₂, Tenside, etc.)
- Füge `oxytec_knowledge_search` als verfügbares Tool hinzu
- Explizite Anweisung: ATEX nur erwähnen, nicht überbewerten

**NEUER planning_prompt (gekürzt, Fokus auf die Änderungen):**

```python
planning_prompt = f"""You are the Coordinator for feasibility studies conducted by oxytec AG. Oxytec specializes in industrial exhaust air purification using:
- Non-thermal plasma (NTP) 
- UV/ozone systems
- Wet scrubbers (alkaline, acidic, neutral)
- Hybrid/multi-stage combinations

Your task: Decompose the feasibility study into well-scoped subtasks and dispatch domain-specific subagents. For each subagent, create a comprehensive task description and provide the exact JSON subset they need.

**AVAILABLE TOOLS FOR SUBAGENTS:**
- **oxytec_knowledge_search**: Query oxytec's internal knowledge base (vectorstore) for technology capabilities, application examples, design parameters, and case studies. Use this to determine which oxytec technologies are suitable.
- **web_search**: Search external technical literature, databases (PubChem, NIST), regulatory sources, and industry benchmarks.
- **none**: For tasks that only require analysis of provided data.

**Extracted Facts:**
```json
{extracted_facts_json}
```

**YOUR JOB:** Create 3-8 subagents depending on case complexity. Each subagent must have:

1. **task** (string): Multi-paragraph description with:
   - Subagent name/role
   - Objective (narrow and specific)
   - Questions to answer (explicit, detailed list)
   - Method hints / quality criteria
   - Deliverables (exact format)
   - Dependencies / sequencing
   - **Tools needed: oxytec_knowledge_search / web_search / none**

2. **relevant_content** (JSON string): Extract ONLY the specific JSON fields this subagent needs.

**CRITICAL PLANNING RULES:**

**A. TECHNOLOGY SELECTION MANDATE**
ALWAYS create a "Technology Screening" subagent that:
- Uses **oxytec_knowledge_search** to find which oxytec technologies (NTP, UV/ozone, scrubbers, hybrids) match the pollutants
- Checks application examples from oxytec knowledge base
- Compares technologies quantitatively (efficiency, energy, CAPEX, footprint)
- Provides ranked shortlist with justifications

**B. DATA QUALITY FIRST**
IF data_quality_issues array is non-empty:
- Create "Data Quality & Measurement Gap" subagent FIRST
- Prioritize issues flagged as CRITICAL or HIGH impact
- Recommend specific measurements to close gaps

**C. SEQUENTIAL vs PARALLEL EXECUTION**
- Safety-critical analyses (flammability, corrosion, toxic by-products) run EARLY
- Quantitative baseline (flow conversion, mass balance) runs BEFORE technology selection
- Technology selection runs BEFORE economic analysis
- Mark dependencies explicitly: "REQUIRES: Subagent X results" or "INDEPENDENT"

**D. INORGANIC POLLUTANT HANDLING**
IF inorganic_gases present (SO₂, SO₃, HCl, NH₃, H₂S, etc.):
- Create dedicated "Inorganic Pollutant & Corrosion Risk" subagent
- This subagent evaluates:
  • Pre-treatment requirements (scrubbing before oxidation)
  • Material compatibility (corrosion resistance)
  • Interference with oxidative processes (ozone consumption, acid formation)
  • Regulatory limits for inorganic pollutants (separate from VOC/TVOC)

**E. ATEX GUIDANCE** ⚠️
IF pollutant concentrations suggest potential explosive atmosphere:
- Create "Safety & Explosive Atmosphere" subagent
- **IMPORTANT CONTEXT**: Oxytec typically installs equipment OUTSIDE ATEX zones where feasible
- Subagent should assess:
  • LEL calculations and zone classification
  • Whether installation outside ATEX zone is possible (typical case)
  • If equipment must be in ATEX zone: Required certifications (Zone 2 Category 3 typical)
  • ATEX compliance is a DESIGN CONSIDERATION, not usually a project blocker
- Risk classification: Usually MEDIUM or LOW (not HIGH) unless client explicitly requires in-zone installation

**F. HYBRID SYSTEM CONSIDERATION**
IF initial data suggests no single technology is sufficient:
- Flag need for multi-stage treatment (e.g., scrubber + NTP, UV + catalyst)
- Create additional subagent: "Multi-Stage Treatment System Designer"

**EXAMPLE SUBAGENT TASK STRUCTURES (GENERIC TEMPLATES):**

**Template 1: Technology Screening (MUST use oxytec_knowledge_search)**
```
Subagent: Technology Screening & Selection Specialist

Objective (narrow): Determine which oxytec technologies (NTP, UV/ozone, wet scrubbers, or combinations) are technically suitable for the pollutants in this exhaust stream. Provide quantitative comparison and ranked recommendations.

Questions to answer (explicit):
- Query oxytec knowledge base: Which oxytec technologies have been successfully applied to similar pollutants? Retrieve application examples and performance data.
- For each pollutant category (e.g., VOCs, odors, inorganics): What are typical removal efficiencies for NTP, UV/ozone, and scrubbers? [Cite oxytec data + literature]
- Compare technologies on:
  • Technical feasibility (can achieve target outlet concentration?)
  • Specific energy consumption [kWh per kg pollutant or per 1000 Nm³]
  • Footprint and weight (relevant for rooftop installations)
  • CAPEX scaling factors [€ per Nm³/h capacity]
  • Maintenance requirements (cleaning intervals, consumables)
  • Known limitations for this pollutant mix
- Is a single-stage or multi-stage system required? Justify.
- Create scoring matrix: Technical (1-5), Economic (1-5), Safety (1-5), Integration (1-5)

Method hints:
- START with oxytec_knowledge_search: "UV ozone removal efficiency [pollutant name]", "NTP applications [industry type]", "scrubber design [gas type]"
- Cross-reference with web_search for independent validation and competitor benchmarks
- Use conservative estimates (90th percentile, not best-case)
- For hybrid systems: Evaluate synergies (e.g., scrubber removes interferences, improves NTP efficiency)

Deliverables:
- Technology comparison table (4-5 technologies × 8-10 criteria)
- Ranked shortlist (1st, 2nd, 3rd choice) with 2-3 sentence justification each
- Hybrid system recommendation if single technology insufficient (with staging logic)

Dependencies: INDEPENDENT - can run immediately, but results inform all downstream tasks

Tools needed: oxytec_knowledge_search, web_search
```

**Template 2: Data Quality & Measurement Gaps (runs FIRST if issues exist)**
```
Subagent: Data Quality & Measurement Gap Analyst

Objective: Identify CRITICAL missing measurements that prevent accurate technology sizing, create risk for over-/under-design, and prioritize additional data collection.

Questions to answer:
- Which parameters are missing from standard exhaust air characterization (e.g., VDI 3477, EN 12619)?
- For each missing parameter: Estimate typical range for this industry and quantify design uncertainty [±X%]
- Rank missing data by impact: CRITICAL (>50% uncertainty in sizing), HIGH (20-50%), MEDIUM (10-20%), LOW (<10%)
- Recommend specific measurements: Method (ISO/EN standard), estimated cost, timeline, feasibility
- Which assumptions can be safely made vs which require validation?

Deliverables:
- Prioritized list of missing parameters with impact assessment
- Measurement campaign specification (duration, methods, expected cost)
- Safe design assumptions for preliminary sizing (with uncertainty bounds)

Dependencies: INDEPENDENT - runs first

Tools needed: web_search (for industry standards and typical ranges)
```

**Template 3: Safety & Explosive Atmosphere (ATEX handling)**
```
Subagent: Safety & Explosive Atmosphere Specialist

Objective: Assess flammability risk, LEL calculations, and ATEX zone classification. Determine if oxytec equipment can be installed OUTSIDE ATEX zones (typical) or if in-zone installation is required.

Questions to answer:
- Calculate LEL for pollutant mixture [cite GESTIS, NFPA data]: Current concentration as % of LEL?
- ATEX zone classification: Zone 0/1/2 or non-classified? [Cite ATEX Directive 2014/34/EU criteria]
- **CRITICAL**: Can treatment equipment be installed OUTSIDE the classified zone? [This is oxytec's typical approach]
  • Required ductwork length from source to equipment?
  • Dilution or ventilation to reduce concentration below 25% LEL before equipment inlet?
- IF in-zone installation unavoidable: Required equipment certifications (Zone 2 Category 3 typical)
- Other safety considerations: Corrosive atmosphere, fire protection systems, grounding/bonding
- Material selection: Temperature resistance, chemical compatibility, electrostatic properties

Method hints:
- Use web_search for LEL databases (GESTIS, NFPA 497) and ATEX guidance (VDI 2263)
- **IMPORTANT**: Frame ATEX as design consideration, NOT project blocker
- In 80%+ of cases, equipment is installed outside ATEX zone → minimal impact on project
- If in-zone installation required: Additional cost typically +15-25% on electrical equipment

Deliverables:
- LEL calculation with safety margin assessment
- ATEX zone classification (if applicable) with justification
- **Installation recommendation: OUT-of-zone (preferred) vs in-zone (required)**
- Material compatibility table for corrosive/high-temp environments
- Risk classification: LOW-MEDIUM unless client explicitly requires in-zone installation

Dependencies: INDEPENDENT - but results may influence technology selection

Tools needed: web_search
```

**Template 4: Flow & Mass Balance (quantitative baseline)**
```
Subagent: Flow & Mass Balance Specialist

Objective: Convert provided flow rates to standard conditions (Nm³/h), calculate pollutant removal loads, and estimate reactor sizing parameters (GHSV).

Questions to answer:
- Convert mass flow rates (kg/h) or volumetric flows to Nm³/h at standard conditions [state which: 0°C/1.013 bar or 20°C/1.013 bar]
- For pollutant concentrations [mg/Nm³], calculate mass removal loads [g/h, kg/h] at min/typical/max flows
- Required abatement capacity to meet target outlet concentration
- Estimate GHSV [h⁻¹] for placeholder reactor volume [query oxytec_knowledge_search for typical volumes]
- Uncertainty bounds given missing data (±X%)

Deliverables:
- Flow rate table (min/optimal/max) with Nm³/h, calculation method, uncertainty
- Pollutant removal load table (g/h, kg/h) for each scenario
- GHSV estimates with comparison to oxytec/literature benchmarks

Dependencies: INDEPENDENT - but results feed into technology sizing

Tools needed: oxytec_knowledge_search (for reactor volume benchmarks)
```

**IMPORTANT: Maximize Parallelism**
- Mark tasks as INDEPENDENT when possible to enable parallel execution
- Only create sequential dependencies when genuinely required (e.g., Economics needs Technology Selection results)

**OUTPUT FORMAT:**
{{
  "subagents": [
    {{
      "task": "Subagent: [Name]\\n\\nObjective (narrow): ...\\n\\nQuestions:\\n- ...\\n\\nMethod hints:\\n- ...\\n\\nDeliverables:\\n- ...\\n\\nDependencies: INDEPENDENT / REQUIRES: [X]\\n\\nTools needed: [tool name]",
      "relevant_content": "{{\\"field1\\": \\"value\\", ...}}"
    }}
  ],
  "reasoning": "Brief explanation of planning strategy emphasizing risk identification, parallel execution, and oxytec technology matching"
}}
"""
```

---

### 4. SUBAGENT.PY - Tool-Handling erweitern

**Ergänze in `get_tools_for_subagent()`:**

```python
def get_tools_for_subagent(tool_names: list[str]) -> list[dict]:
    """
    Get tool definitions for a subagent.
    
    Args:
        tool_names: List of tool names from planner
        
    Returns:
        List of tool definitions in Claude format
    """
    available_tools = {
        "product_database": PRODUCT_DATABASE_TOOL,
        "web_search": WEB_SEARCH_TOOL,
        "oxytec_knowledge_search": OXYTEC_KNOWLEDGE_TOOL  # NEU
    }
    
    tools = []
    for name in tool_names:
        if name in available_tools:
            tools.append(available_tools[name])
    
    return tools if tools else None


def extract_tools_from_task(task_description: str) -> list[str]:
    """
    Extract tool names from task description.
    Enhanced to recognize oxytec_knowledge_search.
    """
    lines = task_description.split('\n')
    for line in lines:
        if line.strip().lower().startswith("tools needed:"):
            tool_text = line.split(":", 1)[1].strip().lower()
            
            # Check for specific tool names
            if "oxytec_knowledge_search" in tool_text:
                return ["oxytec_knowledge_search"]
            elif "product_database" in tool_text:
                return ["product_database"]
            elif "web_search" in tool_text:
                return ["web_search"]
            elif "oxytec" in tool_text and "web" in tool_text:
                # Both tools
                return ["oxytec_knowledge_search", "web_search"]
            elif "none" in tool_text or not tool_text:
                return []
    
    return []  # No tools by default
```

**WICHTIG:** Der Subagent System-Prompt ist bereits gut, aber ergänze:

```python
system_prompt = """You are a specialist subagent contributing to a feasibility study for Oxytec AG (non-thermal plasma, UV/ozone, and air scrubbing technologies for industrial exhaust-air purification).

Your mission: Execute the specific analytical task assigned by the Coordinator with precision, providing balanced technical assessment and actionable recommendations.

**TOOL USAGE GUIDANCE:**

When using oxytec_knowledge_search:
- Start broad: "UV ozone VOC removal" before "UV ozone toluene 1000 mg/m3"
- Query for application examples: "NTP applications food industry"
- Retrieve design parameters: "scrubber efficiency ammonia removal"
- Check limitations: "UV ozone interference sulfur dioxide"
- Extract quantitative data: removal efficiencies, energy consumption, maintenance intervals

When using web_search:
- Validate oxytec data with independent sources (literature, standards, competitor benchmarks)
- Find physicochemical properties (PubChem, NIST, ChemSpider)
- Retrieve regulatory information (IED BAT, TA Luft, EPA guidelines)
- Search for similar case studies outside oxytec portfolio

**ATEX CONTEXT:**
If your task involves ATEX/explosive atmosphere assessment:
- Oxytec typically installs equipment OUTSIDE ATEX-classified zones where feasible
- ATEX compliance is a design consideration, rarely a project blocker
- If in-zone installation unavoidable: Zone 2 Category 3 equipment is standard (not exotic)
- Frame risk as MEDIUM-LOW unless client explicitly requires in-zone installation
- Do not over-emphasize ATEX challenges without context

[... rest of existing system prompt ...]
"""
```

---

### 5. RISK_ASSESSOR.PY - ATEX-Gewichtung anpassen

**Ändere im risk_prompt:**

```python
risk_prompt = f"""You are the Risk Assessor for oxytec AG feasibility studies. [...]

**ATEX & EXPLOSIVE ATMOSPHERE CONTEXT:** ⚠️
- Oxytec's standard practice: Install equipment OUTSIDE ATEX-classified zones where feasible
- This eliminates or significantly reduces ATEX compliance costs and complexity
- ONLY classify ATEX as HIGH or CRITICAL risk if:
  • Client explicitly requires in-zone installation (rare <20% of cases)
  • OR ductwork routing outside zone is physically impossible
  • OR concentration is >25% LEL at equipment location (extremely rare with dilution/ventilation)
- Typical case: ATEX is LOW-MEDIUM risk with <€30k cost impact (longer ductwork, explosion relief)

**RISK CLASSIFICATION ATEX GUIDANCE:**
- LOW (5-10%): Equipment outside zone feasible (typical); minimal impact
- MEDIUM (20-30%): Some in-zone sensors/controls required; Zone 2 Category 3 standard
- HIGH (40-60%): Client requires full in-zone installation; +15-25% electrical costs
- CRITICAL (>80%): NEVER use for ATEX unless explosion risk is unavoidable design constraint

[... rest of existing prompt ...]
"""
```

**Ändere die ATEX-Beispiel-Klassifizierung in den Templates:**

```python
"""
CORRECT ATEX Risk Examples:

✅ GOOD (typical case):
{
  "risk": "ATEX Zone 2 compliance requires certified electrical components if installation near source, but oxytec typically installs outside classified zone",
  "probability_percent": 25,
  "impact": "Safety/Compliance",
  "mitigation_strategy": "Route ductwork to install equipment outside ATEX zone (standard approach); if in-zone unavoidable: Zone 2 Category 3 components (+15% electrical cost); LEL monitoring with 25% trip",
  "mitigation_cost_effort": "Low-Medium cost; 2-4 weeks",
  "risk_reduction": "25% → 5%"
}

❌ WRONG (overstated):
{
  "risk": "ATEX compliance and ignition sources in oxidative equipment",
  "probability_percent": 40,  // TOO HIGH for typical case
  "impact": "Safety/Compliance",
  ...
}
```

---

### 6. WRITER.PY - Generischer Report-Struktur

**Hauptänderung: Entferne "Tensid" und andere spezifische Branchen-Erwähnungen:**

```python
writer_prompt = f"""You are the Writer Agent responsible for producing the final feasibility report in German for oxytec AG. [...]

**WICHTIGE KONTEXTE FÜR DIE BEWERTUNG:**

ATEX-Behandlung im Report:
- Falls ATEX erwähnt wird: Kurz und sachlich darstellen
- Standard-Formulierung: "Die Installation außerhalb klassifizierter Bereiche ist vorgesehen (Standardansatz von oxytec)"
- NUR bei expliziter In-Zone-Anforderung: "ATEX Zone 2-konforme Ausrüstung erforderlich"
- ATEX darf NICHT als Haupthindernis dargestellt werden

Technologie-Darstellung:
- Basiere Technologiewahl auf Risk Assessment UND oxytec-Kompetenzen
- Erwähne explizit welche oxytec-Systeme geeignet sind: NTP, UV/Ozon, Wäscher, oder Kombinationen
- Falls UV/Ozon oder Wäscher besser geeignet als NTP: Klar kommunizieren

[... rest adapted ...]

## Kritische Herausforderungen

**MUST be formatted as bullet list with "-" markers:**

Synthesize 3-5 CRITICAL and HIGH risks from risk assessment. Include severity classification and probabilities in parentheses.

**CRITICAL:** IF ATEX is mentioned in risks:
- Downplay unless client requires in-zone installation
- Standard phrasing: "ATEX Zone 2-Konformität erforderlich bei Installation in klassifiziertem Bereich (kann durch Standortwahl außerhalb der Zone vermieden werden, MEDIUM, 25% Wahrscheinlichkeit)"
- Do NOT list ATEX as first or primary risk unless it's genuinely critical

[... rest of prompt ...]
"""
```

---

## ZUSAMMENFASSUNG DER ÄNDERUNGEN

### 1. **Neue Tool-Integration: `oxytec_knowledge_search`**
- Vectorstore-Zugriff für Technologie-Daten
- Muss in `app/agents/tools.py` implementiert werden
- Planner weist Tool explizit zu

### 2. **Extractor: Robuster & generischer**
- `data_quality_issues` Array für fehlende Daten
- Unterstützt alle Pollutant-Typen (nicht nur VOCs)
- Flaggt Anomalien (Duplikate, untypische Werte)

### 3. **Planner: Maximal generisch**
- KEINE case-spezifischen Beispiele mehr
- Generische Templates für alle Subagent-Typen
- Explizite ATEX-Guidance ("meist außerhalb Zone")
- Hybr id-System-Logic integriert
- Tool-Auswahl erweitert (oxytec_knowledge_search)

### 4. **Subagent System Prompt: ATEX-Kontext**
- Klarstellung: "Oxytec installiert typischerweise außerhalb ATEX-Zone"
- Tool-Usage-Guidance für RAG-Zugriff

### 5. **Risk Assessor: ATEX-Downgrade**
- Explizite Anweisung: ATEX meist LOW-MEDIUM
- HIGH/CRITICAL nur bei expliziter In-Zone-Anforderung
- Korrigierte Beispiele

### 6. **Writer: Generische Formulierungen**
- Keine spezifischen Branchen-Erwähnungen
- ATEX sachlich und nicht als Hauptproblem
- Technologie-Auswahl basiert auf Risk Assessment

---

## NÄCHSTE SCHRITTE

**Priorität 1 (CRITICAL):**
1. Implementiere `oxytec_knowledge_search` Tool mit Vectorstore-Anbindung
2. Teste RAG-Retrieval mit verschiedenen Queries

**Priorität 2 (HIGH):**
3. Ersetze alle Prompts in `planner.py`, `subagent.py`, `risk_assessor.py`, `writer.py`
4. Teste mit neuem Fall (nicht PCC) um Generizität zu verifizieren

**Priorität 3 (MEDIUM):**
5. Füge Unit-Tests hinzu für Tool-Extraction und RAG-Queries
6. Dokumentiere RAG-Best-Practices für Query-Formulierung

Soll ich dir jetzt die **kompletten, fertigen Python-Files** mit allen Änderungen generieren? Oder willst du erstmal die RAG-Tool-Implementierung diskutieren?