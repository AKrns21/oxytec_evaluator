# Test Case: Ammonia Scrubber for Wastewater Treatment

**Purpose**: Validate that the system correctly handles non-VOC pollutants and recommends scrubber technology over NTP.

## Expected Input Document Content

This test case simulates an inquiry from a wastewater treatment plant dealing with ammonia emissions.

### Pollutant Characterization
- **Primary Pollutant**: Ammonia (NH₃)
- **Concentration**: 50-150 mg/Nm³ (depending on process stage)
- **Secondary Pollutants**: H₂S traces (1-5 mg/Nm³), Odor (varies)

### Process Parameters
- **Exhaust Air Flow Rate**: 10,000 Nm³/h
- **Gas Temperature**: 25°C (ambient)
- **Relative Humidity**: 80-95% (wet exhaust)
- **Pressure**: Slight negative pressure (-2 mbar)
- **Operating Schedule**: Continuous (24/7)

### Industry and Process Context
- **Industry Sector**: Municipal wastewater treatment
- **Specific Process**: Biological treatment basins, sludge dewatering
- **Problem**: Odor complaints from neighboring residential area
- **Current Abatement**: None (direct exhaust to atmosphere)

### Requirements & Constraints
- **Target Removal Efficiency**: >90% NH₃ removal
- **Outlet Concentration Target**: <5 mg/Nm³ NH₃
- **Regulatory**: German TA Luft compliance
- **Space Constraints**: Limited footprint (outdoor installation, 4m x 3m max)
- **ATEX**: Zone 2 classification due to biogas traces
- **Budget**: CAPEX target <€150k, OPEX target <€20k/year

### Site Conditions
- **Available Utilities**: 400V 3-phase power, process water available, no steam
- **Installation Location**: Outdoor rooftop
- **Ambient Conditions**: -10°C to +35°C, coastal climate (corrosive)

### Customer Knowledge & Expectations
- Customer mentioned "wet scrubber" as preferred technology
- Aware of oxytec's UV/ozone systems but unsure if suitable for NH₃
- Previous pilot with NTP showed poor NH₃ removal (<30%)
- Looking for proven technology with low maintenance

## Expected System Behavior

### EXTRACTOR
- Should extract pollutant types: ammonia, H₂S, odor (not VOC-focused)
- Should capture customer's technology preference (scrubber)
- Should note previous NTP pilot failure
- Should flag data quality issues: H₂S concentration range large, biogas not quantified

### PLANNER
- Should create "Technology Screening" subagent with `oxytec_knowledge_search` tool
- Should create "Safety/ATEX" subagent with context that installation outside zone is typical
- Should create "Chemical Analysis" subagent focusing on NH₃ properties (high water solubility)
- Should create "Economic Analysis" subagent for CAPEX/OPEX comparison

### SUBAGENTS
- **Technology Screening**:
  - Should query RAG: "scrubber ammonia removal efficiency wastewater"
  - Should find that wet scrubbers are MOST suitable (NH₃ is highly water-soluble)
  - Should note NTP is NOT suitable for NH₃ (low reactivity with OH radicals)
  - Should recommend acidic scrubber (H₂SO₄ or HCl) for NH₃ absorption
- **Chemical Analysis**:
  - Should identify NH₃ as highly water-soluble (partition coefficient)
  - Should note that NH₃ does NOT react well with ozone/NTP
  - Should recommend scrubber as PRIMARY technology
- **ATEX Subagent**:
  - Should calculate Zone 2 requirements
  - Should note equipment can be installed OUTSIDE zone (typical oxytec practice)
  - Should classify ATEX as LOW-MEDIUM risk (€20-30k additional ductwork/explosion relief)

### RISK_ASSESSOR
- **Expected Risks**:
  - MEDIUM: Corrosion risk due to acidic scrubbing liquid (requires material selection: PP, PVDF)
  - MEDIUM: Wastewater disposal from scrubber (requires treatment or neutralization)
  - LOW: ATEX compliance (equipment outside zone, standard measures)
  - LOW: High humidity in exhaust (typical for wastewater, scrubber tolerates this)
- **Final Recommendation**: PROCEED or STRONG PROCEED
- **Confidence Level**: HIGH (NH₃ scrubbing is proven, well-documented technology)
- **Critical Risks**: NONE (no project-killing factors)

### WRITER
- **Technology Recommendation**: Should clearly state "Wet scrubber (saurer Wäscher) is MOST suitable"
- **Should explicitly mention**: "NTP and UV/ozone are NOT recommended for NH₃ (low reactivity)"
- **ATEX Positioning**: Brief mention as design consideration, not blocker
- **Overall Assessment**: GUT GEEIGNET or MACHBAR
- **Key advantages**: High removal efficiency (>95%), proven technology, low energy consumption
- **Challenges**: Corrosion management, wastewater handling

## Validation Checklist

After running this test case:

- [ ] EXTRACTOR captures ammonia as primary pollutant (not VOC)
- [ ] EXTRACTOR extracts customer knowledge (scrubber preference, previous NTP failure)
- [ ] PLANNER creates Technology Screening subagent with RAG tool
- [ ] Technology Screening subagent invokes `search_oxytec_knowledge` with ammonia queries
- [ ] RAG returns scrubber-related catalog pages (not NTP pages)
- [ ] RISK_ASSESSOR classifies ATEX as LOW-MEDIUM (not HIGH/CRITICAL)
- [ ] WRITER clearly recommends scrubber over NTP/UV
- [ ] Final report is in German with proper technical terminology
- [ ] Report explains WHY scrubber is better (water solubility, proven efficiency)

## Success Criteria

This test passes if:
1. System recommends scrubber technology (not NTP/UV/ozone)
2. Justification is based on NH₃ properties (high water solubility, low ozone reactivity)
3. ATEX is mentioned but not over-emphasized (LOW-MEDIUM risk)
4. Final recommendation is PROCEED/STRONG PROCEED
5. Report quality is professional and technology-agnostic
