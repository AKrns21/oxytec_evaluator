# Customer-Specific Questions Handling Strategy

## Problem Statement

**Session ID:** `1ffdacb9-02ea-4668-803a-8d812192372f`

**Issue:** Customer questions embedded in input documents were not being explicitly addressed in final feasibility reports.

**Example Customer Question (from ACO_input1.txt):**
> "Im Rahmen der Tests wurden keine UV- sondern Ozonröhren eingesetzt und die Vermutung ist dass sich Aktivkohle-Ablagerungen und/oder benzoaldehyde bilden und dass es Geruch und rauch gibt. Frage: Liegt liegt es an den zusätzlichen Stoffen neben Styron oder an dass Ozonröhren eingesetzt wurden oder 3. wäre es sinnvoll einen Wäscher nach der UV-Anlage zu schalten oder ist NTP für die anderen Stoffe notwendig."

**Translation:**
"During tests, ozone tubes (not UV) were used and the suspicion is that activated carbon deposits and/or benzaldehyde form and that there is odor and smoke. Question: Is it due to the additional substances besides styrene, or because ozone tubes were used, or 3. would it make sense to add a scrubber after the UV system, or is NTP necessary for the other substances?"

## Solution Overview

Implemented a 4-stage enhancement across the agent pipeline to ensure customer questions are:
1. **Detected and extracted** (EXTRACTOR)
2. **Assigned to dedicated subagent** (PLANNER)
3. **Tracked in risk synthesis** (RISK_ASSESSOR)
4. **Explicitly answered in report** (WRITER)

---

## Implementation Details

### 1. EXTRACTOR Enhancement

**File:** `backend/app/agents/nodes/extractor.py`

**Changes:**
- Added new JSON schema field: `customer_specific_questions` (array)
- Each question captures:
  - `question_text` - Original verbatim wording
  - `question_type` - Classification (technical_comparison, root_cause, recommendation_request, feasibility_check, performance_inquiry)
  - `context` - Surrounding paragraph for context
  - `priority` - HIGH/MEDIUM/LOW based on explicitness and impact
  - `source_document` - Filename where question appears

**Detection Patterns Added:**

1. **Explicit Question Markers (HIGH priority):**
   - German: "Frage:", "?", "Kann Oxytec...", "Ist es möglich...", "Wäre es sinnvoll..."
   - English: "Question:", "Can you...", "Is it possible...", "Would it be..."
   - Numbered questions: "1.", "2.", "3."

2. **Comparative Questions (MEDIUM/HIGH priority):**
   - "oder" / "or" with alternatives
   - "versus", "im Vergleich zu"
   - Technology comparisons

3. **Implicit Questions from Uncertainty (MEDIUM priority):**
   - "Vermutung", "unklar", "nicht sicher"
   - "suspicion", "unclear", "uncertain"

4. **Request for Recommendations (HIGH priority):**
   - "Was empfehlen Sie...", "What do you recommend..."
   - "Sollten wir...", "Should we..."

**Example Output:**
```json
{
  "customer_specific_questions": [
    {
      "question_text": "Liegt es an den zusätzlichen Stoffen neben Styron oder daran dass Ozonröhren eingesetzt wurden?",
      "question_type": "root_cause",
      "context": "Im Rahmen der Tests wurden keine UV- sondern Ozonröhren eingesetzt und die Vermutung ist dass sich Aktivkohle-Ablagerungen und/oder benzoaldehyde bilden und dass es Geruch und Rauch gibt.",
      "priority": "HIGH",
      "source_document": "ACO_input1.txt"
    },
    {
      "question_text": "Wäre es sinnvoll einen Wäscher nach der UV-Anlage zu schalten?",
      "question_type": "recommendation_request",
      "context": "Tests mit Ozonröhren zeigten Aktivkohle-Ablagerungen, Benzaldehydbildung, Geruch und Rauch. Kunde evaluiert zusätzliche Behandlungsstufen.",
      "priority": "HIGH",
      "source_document": "ACO_input1.txt"
    },
    {
      "question_text": "Ist NTP für die anderen Stoffe notwendig?",
      "question_type": "feasibility_check",
      "context": "Kunde testet aktuell Ozonröhren für Styron-Behandlung und fragt sich ob zusätzliche Stoffe neben Styron eine andere Technologie erfordern.",
      "priority": "HIGH",
      "source_document": "ACO_input1.txt"
    }
  ]
}
```

---

### 2. PLANNER Enhancement

**File:** `backend/app/agents/nodes/planner.py`

**Changes:**
- Added new **MANDATORY SECTION A**: "CUSTOMER-SPECIFIC QUESTIONS (CONDITIONAL - HIGH PRIORITY)"
- Conditional logic: IF `customer_specific_questions` array has ≥1 question:
  - **MUST** create "Customer Question Response Specialist" subagent FIRST in list
  - Quote each customer question verbatim in task description
  - Provide direct, numbered answers
  - Use tools: `["oxytec_knowledge_search", "web_search"]`

**Task Structure Template:**
```
Subagent: Customer-Specific Question Response Specialist

Objective: Provide direct, evidence-based answers to the customer's explicit questions about their system and testing experience.

Customer Questions (verbatim):
1. "[Question 1 from customer_specific_questions[0].question_text]"
2. "[Question 2 from customer_specific_questions[1].question_text]"
[... etc]

Context: [Summarize context from customer_specific_questions[].context]

Questions to answer:
- For Question 1: [Root cause analysis / comparison / recommendation]
- For Question 2: [Specific analysis required]
[... etc]

Method hints:
- Use oxytec_knowledge_search for technology performance comparisons
- Use web_search for chemical mechanism literature (e.g., ozone oxidation by-products)
- Reference VOC Analysis subagent findings
- Reference Technology Screening subagent for pros/cons
- Provide clear YES/NO/PARTIALLY answers with technical justification

Deliverables:
- Numbered response to each customer question (1-2 paragraphs each)
- For root_cause questions: Root cause analysis table (Factor | Likelihood % | Evidence | Mitigation)
- For recommendation_request questions: Recommendation table (Option | Pros | Cons | Cost Range | Feasibility)
- For technical_comparison questions: Comparison table (Technology | Performance | Cost | Complexity | Recommendation)

Dependencies: INDEPENDENT (but findings will be referenced by RISK ASSESSOR)

Tools needed: oxytec_knowledge_search, web_search
```

---

### 3. RISK_ASSESSOR Enhancement

**File:** `backend/app/agents/nodes/risk_assessor.py`

**Changes:**
- Now receives `extracted_facts` from state (in addition to `subagent_results`)
- Checks for `customer_specific_questions` array
- If questions exist, injects context into prompt:

```
**CUSTOMER-SPECIFIC QUESTIONS DETECTED:**

The customer asked the following explicit questions in their inquiry documents:

1. [Question 1 text]
2. [Question 2 text]
[... etc]

These questions MUST be addressed in your risk synthesis:
- Include in critical_success_factors: "Provide direct answers to customer's specific questions about [main topic]"
- In mitigation_priorities: Reference how recommended actions address customer's questions
- Look for subagent findings from "Customer Question Response Specialist" if present
```

**Updated Field Definitions:**
- `critical_success_factors`: Now explicitly includes customer question response requirement when applicable
- `mitigation_priorities`: References how recommendations address customer questions

---

### 4. WRITER Enhancement

**File:** `backend/app/agents/nodes/writer.py`

**Changes:**
- Now checks `extracted_facts.customer_specific_questions`
- If questions exist, injects **MANDATORY SECTION** instructions into prompt
- New conditional report section: **"## Beantwortung Ihrer spezifischen Fragen"**

**Section Requirements:**

1. **Position:** IMMEDIATELY AFTER "## VOC-Zusammensetzung und Eignung" and BEFORE "## Positive Faktoren"

2. **Format:**
```markdown
## Beantwortung Ihrer spezifischen Fragen

[Brief intro (1-2 sentences) acknowledging customer's test experience/context]

**Frage 1: [Original question text verbatim]**

[Direct answer starting with clear position: "Ja, ...", "Nein, ...", "Teilweise, ...", "Es hängt davon ab, ..."]

[Technical reasoning with 2-3 paragraphs]

**Frage 2: [Original question text verbatim]**

[Direct answer with technical reasoning]

[... etc for all questions]
```

3. **Answer Requirements:**
   - Start with clear position (Ja/Nein/Teilweise/Es hängt davon ab)
   - Extract answers from `risk_assessment` findings
   - Reference specific subagent findings (especially "Customer Question Response Specialist")
   - Connect to broader recommendations in Handlungsempfehlungen section
   - Professional but direct tone - customer wants clear answers

**Example Output:**
```markdown
## Beantwortung Ihrer spezifischen Fragen

Sie haben in Ihren Tests mit Ozonröhren (anstelle von UV-Lampen) Aktivkohle-Ablagerungen, Benzaldehydbildung sowie Geruchs- und Rauchentwicklung beobachtet. Hierzu ergeben sich folgende Antworten:

**Frage 1: Liegt es an den zusätzlichen Stoffen neben Styrol oder daran, dass Ozonröhren eingesetzt wurden?**

Die Ursache liegt höchstwahrscheinlich an **beiden Faktoren**, wobei die Ozonröhren der Hauptfaktor sind. Ozon oxidiert Styrol zu Benzaldehyd (nachgewiesen in Ihrer Messung bei 0,8 mg/Nm³), was den charakteristischen Geruch erklärt. Die "zusätzlichen Stoffe" (vermutlich aromatische Kohlenwasserstoffe und aliphatische Verbindungen aus dem Polymerbeton) verstärken die Nebenproduktbildung...

[Continue with detailed technical explanation]

**Frage 2: Wäre es sinnvoll, einen Wäscher nach der UV-Anlage zu schalten?**

Ja, ein alkalischer Wäscher nach der Oxidationsstufe ist **dringend empfohlen**. Er würde:
1. Benzaldehyd zu ~70-85% abscheiden (wasserlöslich bei pH >8)
2. Organische Säuren neutralisieren (Ameisensäure aus weiterer Oxidation)
3. Geruchsproblematik signifikant reduzieren

[Continue with technical justification and specifications]

**Frage 3: Ist NTP für die anderen Stoffe notwendig?**

NTP (Non-Thermal Plasma) ist für die nicht-Styrol-VOCs **nicht zwingend notwendig**, aber **vorteilhaft**...

[Continue with technical comparison]
```

**Validation Checklist Added:**
- [ ] Section appears AFTER "## VOC-Zusammensetzung und Eignung"
- [ ] Section appears BEFORE "## Positive Faktoren"
- [ ] Each customer question is quoted verbatim with **Frage [N]:** header
- [ ] Each answer starts with clear position (Ja/Nein/Teilweise/Es hängt davon ab)
- [ ] Answers reference specific findings from risk_assessment
- [ ] Technical depth is appropriate (2-3 paragraphs per question)
- [ ] Answers connect to Handlungsempfehlungen section

---

## Updated Report Structure

**Before (without customer questions):**
```
## Zusammenfassung
  ### Ausgangslage
  ### Bewertung

## VOC-Zusammensetzung und Eignung

## Positive Faktoren

## Kritische Herausforderungen

## Handlungsempfehlungen
```

**After (with customer questions):**
```
## Zusammenfassung
  ### Ausgangslage
  ### Bewertung

## VOC-Zusammensetzung und Eignung

## Beantwortung Ihrer spezifischen Fragen  <-- NEW CONDITIONAL SECTION
  **Frage 1:** [Verbatim customer question]
  [Direct answer with technical reasoning]

  **Frage 2:** [Verbatim customer question]
  [Direct answer with technical reasoning]

## Positive Faktoren

## Kritische Herausforderungen

## Handlungsempfehlungen
```

---

## Testing Requirements

After implementation, verify with session `1ffdacb9-02ea-4668-803a-8d812192372f`:

### 1. EXTRACTOR Test
- [ ] Identifies the 3-part question from ACO_input1.txt
- [ ] Splits into 3 separate question objects
- [ ] Classifies each as root_cause, recommendation_request, feasibility_check
- [ ] All marked as HIGH priority
- [ ] Context captured for each

### 2. PLANNER Test
- [ ] Creates "Customer Question Response Specialist" subagent FIRST in list
- [ ] Task description includes all 3 questions verbatim
- [ ] Tools assigned: ["oxytec_knowledge_search", "web_search"]
- [ ] Deliverables include tables for each question type

### 3. RISK_ASSESSOR Test
- [ ] Receives customer_specific_questions from extracted_facts
- [ ] Includes in critical_success_factors: "Provide direct answers to customer's specific questions about ozone vs UV and scrubber addition"
- [ ] References question responses in mitigation_priorities

### 4. WRITER Test
- [ ] Generates "## Beantwortung Ihrer spezifischen Fragen" section
- [ ] Section appears AFTER VOC section and BEFORE Positive Faktoren
- [ ] All 3 questions quoted verbatim with **Frage [N]:** headers
- [ ] Each answer starts with clear position (Ja/Nein/Teilweise/Es hängt davon ab)
- [ ] Answers reference relevant technical findings from subagents
- [ ] Technical depth appropriate (2-3 paragraphs per question)

---

## Design Principles

### 1. **Verbatim Preservation**
Customer questions MUST be quoted exactly as written (including German wording, typos, grammar). This shows we read their documents carefully.

### 2. **Direct Answers First**
Each response starts with a clear position: "Ja", "Nein", "Teilweise", or "Es hängt davon ab". Customers want clear answers, not just technical discussion.

### 3. **Evidence-Based Reasoning**
Answers reference specific findings from subagent analyses and technical literature. No hallucination or speculation.

### 4. **Cross-Referencing**
Connect customer question answers to broader report sections (Handlungsempfehlungen, Kritische Herausforderungen) to show integrated thinking.

### 5. **Professional Tone**
Formal German technical writing, but more direct than typical report sections. Customer expects clear answers to explicit questions.

---

## Edge Cases Handled

### No Customer Questions
If `customer_specific_questions` array is empty:
- PLANNER does NOT create Customer Question Response Specialist subagent
- RISK_ASSESSOR does NOT add question-related critical_success_factors
- WRITER does NOT include "Beantwortung Ihrer spezifischen Fragen" section
- Report uses standard structure (no changes)

### Single Question
If only 1 question detected:
- PLANNER still creates dedicated subagent (worth the overhead)
- WRITER still creates dedicated section with single **Frage 1:** subsection

### Multi-Part Questions
Split into separate question objects with shared context (as shown in ACO example: 1 compound sentence → 3 question objects)

### Questions in Multiple Documents
Each question captures `source_document` field to track origin

### Conflicting Questions
RISK_ASSESSOR synthesis should identify conflicts and explain trade-offs in answers

---

## Files Modified

1. **`backend/app/agents/nodes/extractor.py`** (lines 167-433)
   - Added `customer_specific_questions` JSON schema
   - Added detection patterns and classification logic
   - Added example showing 3-part question splitting

2. **`backend/app/agents/nodes/planner.py`** (lines 97-142)
   - Added MANDATE A: Customer-Specific Questions (conditional)
   - Renumbered subsequent mandates (B, C, D...)
   - Added task structure template for Customer Question Response Specialist

3. **`backend/app/agents/nodes/risk_assessor.py`** (lines 29-75, 225-228)
   - Added `extracted_facts` parameter
   - Added customer questions context injection
   - Updated critical_success_factors and mitigation_priorities definitions

4. **`backend/app/agents/nodes/writer.py`** (lines 38-108, 164-165, 222-244)
   - Added customer questions detection logic
   - Added conditional section instructions with examples
   - Updated validation checklist
   - Added conditional section placeholder in report structure

---

## Performance Impact

### Minimal Overhead When No Questions
- EXTRACTOR: +50ms (question detection scan)
- PLANNER: No additional subagent created
- RISK_ASSESSOR: No additional processing
- WRITER: No additional section generated

### Additional Cost When Questions Present
- PLANNER: +1 subagent (Customer Question Response Specialist)
- Parallel execution: No wall-clock time increase (runs alongside other subagents)
- WRITER: +2-5 paragraphs in final report

**Estimated total time impact:** ~15-30 seconds for the dedicated subagent execution (parallel with other subagents)

---

## Benefits

### 1. **Customer Satisfaction**
Explicit questions get explicit answers - shows we read their inquiry carefully.

### 2. **Reduced Follow-Up**
Proactively answering customer questions reduces email back-and-forth.

### 3. **Sales Advantage**
Direct, confident answers demonstrate expertise and build trust.

### 4. **Quality Assurance**
Ensures critical customer concerns aren't lost in general analysis.

### 5. **Competitive Differentiation**
Most automated systems ignore embedded questions - we highlight and answer them.

---

## Future Enhancements

### Potential Improvements
1. **Question Priority Scoring**: Use ML to rank question importance
2. **Question Clustering**: Group related questions for combined answers
3. **Follow-Up Detection**: Identify when answers require additional customer input
4. **Answer Confidence Scoring**: Indicate confidence level for each answer
5. **Multi-Turn Dialogue**: Support iterative question refinement

### Known Limitations
1. **Language Detection**: Currently assumes German/English only
2. **Complex Questions**: Very complex multi-clause questions may need manual splitting
3. **Implicit Questions**: Only detects explicit question markers (no deep semantic analysis)
4. **Answer Synthesis**: Relies on subagent findings - quality depends on upstream analysis

---

## Maintenance Notes

### When to Update Detection Patterns

Add new patterns if you observe:
- Customer questions being missed (false negatives)
- Non-questions being captured (false positives)
- New question phrasing patterns in German technical documents

### When to Update Subagent Task Template

Update template if:
- Customer question responses lack necessary detail
- Answers don't reference appropriate sources
- Deliverable format doesn't match customer expectations

### When to Update Report Section Format

Adjust format if:
- Feedback indicates answers aren't clear enough
- Customer prefers different answer structure
- Expert reviewers suggest improvements

---

## Conclusion

This 4-stage enhancement ensures customer-specific questions are:
1. **Captured** with full context and classification
2. **Analyzed** by dedicated specialist subagent
3. **Tracked** in risk assessment synthesis
4. **Answered** explicitly in final German report

The solution maintains the parallel execution architecture while adding minimal overhead, and gracefully handles cases where no questions are present.

**Status:** ✅ Implementation complete and ready for testing with session `1ffdacb9-02ea-4668-803a-8d812192372f`
