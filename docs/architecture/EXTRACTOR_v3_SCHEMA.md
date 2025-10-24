# EXTRACTOR v3.0.0 Output Schema Definition

**Date:** 2025-10-24
**Status:** APPROVED ✅
**Architecture:** Content-First (preserves all page structure)

---

## Philosophy Change

### v2.0.0 (Schema-First - DEPRECATED):
```
PDF → Force into predefined schema → Data that doesn't fit = null
```

### v3.0.0 (Content-First - NEW):
```
PDF → Preserve ALL content structure → Add light metadata → PLANNER interprets
```

---

## Complete Schema

```json
{
  "document_metadata": {
    "document_type": "string (safety_data_sheet | measurement_report | inquiry | process_description | mixed)",
    "language": "string (de | en | mixed)",
    "total_pages": "integer",
    "extraction_method": "string (vision_api | text_extraction | mixed)",
    "has_tables": "boolean",
    "has_diagrams": "boolean",
    "filename": "string"
  },

  "pages": [
    {
      "page_number": "integer",
      "headers": ["string array - all headers on this page"],
      "body_text": "string - full page text content",
      "tables": [
        {
          "title": "string or null",
          "page_location": "integer (page number)",
          "interpretation_hint": "string (composition_data | voc_measurements | toxicity_data | process_parameters | regulatory_info | properties | other)",
          "headers": ["string array - table column headers"],
          "rows": [
            ["cell1", "cell2", "cell3", ...],
            ...
          ],
          "footnotes": ["string array - any footnotes for this table"]
        }
      ],
      "key_value_pairs": [
        {
          "key": "string",
          "value": "string"
        }
      ],
      "lists": [
        {
          "type": "string (bulleted | numbered | definition)",
          "items": ["string array"]
        }
      ],
      "diagrams_and_images": [
        {
          "type": "string (logo | diagram | chart | photo)",
          "description": "string - what the image shows",
          "labels_and_text": ["string array - any text/labels in image"]
        }
      ],
      "signatures_and_stamps": [
        {
          "type": "string (signature | stamp | seal)",
          "text": "string or null"
        }
      ],
      "content_categories": ["string array (product_identification | composition | safety | toxicity | regulatory | process_data | measurements | environmental | handling | disposal | transport)"]
    }
  ],

  "quick_facts": {
    "products_mentioned": ["string array - all product names found"],
    "cas_numbers_found": ["string array - all CAS numbers found"],
    "measurement_units_detected": ["string array - all units found (m3/h, mg/Nm3, ppm, degC, %)"],
    "sections_identified": ["string array - document sections (Section 1, Section 3, ABSCHNITT 8, etc.)"],
    "voc_svoc_detected": "boolean",
    "languages_detected": ["string array (de | en | fr | ...)"],
    "companies_mentioned": ["string array - company names"],
    "locations_mentioned": ["string array - cities, countries, addresses"]
  },

  "extraction_notes": [
    {
      "field": "string (JSON path: pages[0].tables[0].rows[2].cells[1])",
      "status": "string (extraction_uncertain | missing_in_source | unclear_format | table_empty | not_provided_in_documents)",
      "note": "string - technical description of the issue"
    }
  ]
}
```

---

## Field Specifications

### document_metadata

**Purpose:** High-level document classification

**Fields:**

- **document_type:**
  - `safety_data_sheet`: SDS/MSDS documents (Sicherheitsdatenblatt)
  - `measurement_report`: VOC measurements, analytical results
  - `inquiry`: Customer inquiries, questionnaires
  - `process_description`: Process flow diagrams, technical descriptions
  - `mixed`: Multiple document types combined

- **language:**
  - Primary language of document
  - `mixed` if multiple languages present

- **extraction_method:**
  - `vision_api`: Claude Vision used (image-based PDF)
  - `text_extraction`: PyMuPDF text extraction (text-based PDF)
  - `mixed`: Some pages vision, some text

### pages[]

**Purpose:** Preserve complete page-by-page structure

**Key Points:**
- One entry per PDF page
- ALL content preserved (no filtering at EXTRACTOR level)
- Structure matches Vision API output when possible

#### pages[].headers

- All h1, h2, h3 level headers on the page
- Section titles (ABSCHNITT 1, Section 8.2, etc.)
- Preserve original casing and language

#### pages[].body_text

- Full page text content
- Preserve paragraph structure
- Include all narrative text NOT in tables

#### pages[].tables[]

**interpretation_hint values:**
- `composition_data`: SDS Section 3, ingredient lists, formulation tables
- `voc_measurements`: VOC/SVOC measurement results (mg/Nm3, ppm, %)
- `toxicity_data`: LD50, LC50, DNEL, PNEC values
- `process_parameters`: Flow rates, temperatures, pressures, humidity
- `regulatory_info`: H-codes, GHS classifications, transport info
- `properties`: Physical properties (density, viscosity, flash point)
- `other`: Cannot categorize or mixed content

**Table Structure:**
- **title:** Table caption or title (may be null)
- **headers:** Column headers EXACTLY as written
- **rows:** 2D array - preserve ALL rows including empty cells (use null)
- **footnotes:** Any footnotes referenced in table (¹⁾, ²⁾, etc.)

#### pages[].key_value_pairs[]

- Common pattern: "Key: Value" or "Key | Value"
- Examples:
  - `{"key": "Produktname", "value": "Voltabas 0302"}`
  - `{"key": "CAS", "value": "28961-43-5"}`
  - `{"key": "Ausgabedatum", "value": "4/19/2024"}`

#### pages[].content_categories[]

**Categories:**
- `product_identification`: Product names, codes, identifiers
- `composition`: Ingredients, CAS numbers, percentages
- `safety`: Safety warnings, protective equipment, first aid
- `toxicity`: Toxicity data, health effects
- `regulatory`: Legal requirements, classifications, transport
- `process_data`: Process conditions, operating parameters
- `measurements`: Measurement results, analytical data
- `environmental`: Environmental impact, disposal
- `handling`: Storage, handling instructions
- `disposal`: Waste disposal, decontamination
- `transport`: Shipping, packaging requirements

**Multiple categories per page allowed** - e.g., a page might have both `composition` and `safety`

### quick_facts

**Purpose:** Fast access to commonly needed entities (PLANNER can use without parsing pages[])

**Extraction Rules:**

- **products_mentioned:**
  - Any product names found
  - Brand names, chemical names, trade names
  - Example: ["Voltabas 0302", "Voltatex"]

- **cas_numbers_found:**
  - All CAS numbers in document (format: "108-88-3")
  - Normalize to standard format with dashes
  - Example: ["28961-43-5", "100-42-5", "13475-82-6"]

- **measurement_units_detected:**
  - All units found in document
  - Normalize: m³/h → m3/h, °C → degC
  - Example: ["m3/h", "mg/Nm3", "ppm", "%", "degC", "mbar"]

- **sections_identified:**
  - Document sections (SDS sections, report chapters)
  - Preserve original numbering
  - Example: ["Section 1", "Section 3", "Section 8", "Tabelle 2", "Tabelle 4"]

- **voc_svoc_detected:**
  - `true` if any VOC/SVOC mentioned
  - Keywords: "VOC", "SVOC", "flüchtige Verbindungen"

### extraction_notes[]

**Purpose:** Flag technical uncertainties for PLANNER to resolve

**Status Types:**

- `extraction_uncertain`: Not confident in interpretation
  - Example: "Polymer vs monomer classification unclear"

- `missing_in_source`: Data mentioned but incomplete
  - Example: "Substance name without CAS number"

- `unclear_format`: Ambiguous formatting
  - Example: "Two CAS numbers in one table cell"

- `table_empty`: Table structure exists but no data
  - Example: "Table headers present but all cells empty"

- `not_provided_in_documents`: Field mentioned but no value
  - Example: "Temperature mentioned but value TBD"

**Field Path Format:**
- Use JSON path notation
- Examples:
  - `pages[2].tables[0].rows[3]`
  - `pages[5].key_value_pairs[7].value`
  - `pages[1].body_text`

---

## Example Output (Datenblatt_test.pdf)

```json
{
  "document_metadata": {
    "document_type": "measurement_report",
    "language": "de",
    "total_pages": 8,
    "extraction_method": "vision_api",
    "has_tables": true,
    "has_diagrams": false,
    "filename": "Datenblatt_test.pdf"
  },

  "pages": [
    {
      "page_number": 1,
      "headers": [
        "DE : DEUTSCH",
        "SICHERHEITSDATENBLATT",
        "ABSCHNITT 1: Bezeichnung des Stoffs..."
      ],
      "body_text": "Erfüllt Verordnung (EG) Nr. 1907/2006 (REACH)...",
      "tables": [],
      "key_value_pairs": [
        {"key": "Produktname", "value": "Voltabas 0302"},
        {"key": "CAS", "value": "B13184567"},
        {"key": "Ausgabedatum", "value": "19 April 2024"}
      ],
      "lists": [],
      "diagrams_and_images": [
        {
          "type": "logo",
          "description": "Axalta company logo",
          "labels_and_text": ["AXALTA"]
        }
      ],
      "signatures_and_stamps": [],
      "content_categories": ["product_identification", "regulatory"]
    },
    {
      "page_number": 5,
      "headers": [
        "PRÜFBERICHT NR.: 250438",
        "Tabelle 2: 250438-P1, flüchtige Verbindungen (VOC und SVOC)"
      ],
      "body_text": "Zur Einstufung und Kennzeichnung...",
      "tables": [
        {
          "title": "Tabelle 2: 250438-P1, flüchtige Verbindungen (VOC und SVOC)",
          "page_location": 5,
          "interpretation_hint": "voc_measurements",
          "headers": ["CAS-Nr.", "Bezeichnung", "Einstufung VOC / SVOC", "Masse-[%]"],
          "rows": [
            ["100-42-5", "Styren", "VOC", "1,0 ± 0,07"],
            ["13475-82-6", "2,2,4,6,6-Pentamethylheptan", "VOC", "0,3 ± 0,02"],
            ["80-43-3", "Dicumylperoxid", "VOC", "0,4 ± 0,01"]
          ],
          "footnotes": ["¹⁾ Quantifizierung über DEA-Äquivalente"]
        }
      ],
      "key_value_pairs": [],
      "lists": [],
      "diagrams_and_images": [],
      "signatures_and_stamps": [],
      "content_categories": ["measurements", "composition"]
    }
  ],

  "quick_facts": {
    "products_mentioned": ["Voltabas 0302", "Voltatex"],
    "cas_numbers_found": [
      "28961-43-5", "100-42-5", "13475-82-6", "80-43-3",
      "37275-49-3", "97-90-5", "2358-84-1", "109-16-0"
    ],
    "measurement_units_detected": ["mg/Nm3", "%", "ppm", "degC", "mbar"],
    "sections_identified": ["Section 1", "Section 3", "Section 8", "Tabelle 2", "Tabelle 4"],
    "voc_svoc_detected": true,
    "languages_detected": ["de"],
    "companies_mentioned": ["Axalta Coating Systems", "ILF Magdeburg"],
    "locations_mentioned": ["Wuppertal", "Magdeburg"]
  },

  "extraction_notes": [
    {
      "field": "pages[6].tables[0].rows[0]",
      "status": "unclear_format",
      "note": "Two CAS numbers in one cell: '108-32-7\\n13475-82-6' (Propylencarbonat und Pentamethylheptan overlap)"
    },
    {
      "field": "pages[7].tables[0].rows[10]",
      "status": "extraction_uncertain",
      "note": "Compound marked with '?? Keine sichere qual. Analyse (kleiner 60%)' - identity uncertain"
    }
  ]
}
```

---

## Comparison: v2.0.0 vs v3.0.0

### v2.0.0 Output (Schema-First):
```json
{
  "pollutant_characterization": {
    "pollutant_list": [
      {
        "name": "Styren",
        "cas_number": "100-42-5",
        "concentration": null,  // ❌ Lost - was in table as "1,0 ± 0,07 %"
        "concentration_unit": null,
        "formulation_percentage": "1,0 ± 0,07 %",
        "category": "VOC"
      }
    ]
  },
  "process_parameters": {
    "flow_rate": {"value": null, "unit": null},  // ❌ Lost - wasn't in schema field
    "temperature": {"value": null, "unit": null}
  }
}
```

**Problems:**
- ❌ concentration vs formulation_percentage confusion
- ❌ Process parameters not found (document didn't have flow_rate field)
- ❌ Table structure lost (can't see headers, other columns)
- ❌ Page context lost (which page was this from?)

### v3.0.0 Output (Content-First):
```json
{
  "pages": [
    {
      "page_number": 5,
      "tables": [
        {
          "title": "Tabelle 2: VOC measurements",
          "interpretation_hint": "voc_measurements",
          "headers": ["CAS", "Bezeichnung", "Einstufung", "Masse-[%]"],
          "rows": [
            ["100-42-5", "Styren", "VOC", "1,0 ± 0,07"]
          ]
        }
      ]
    }
  ],
  "quick_facts": {
    "cas_numbers_found": ["100-42-5"],
    "measurement_units_detected": ["%"]
  }
}
```

**Benefits:**
- ✅ ALL data preserved (full table with headers)
- ✅ Context maintained (page 5, table structure)
- ✅ PLANNER interprets (is "1,0 ± 0,07 %" a concentration or formulation?)
- ✅ Can see relationships (Styren → VOC → 1.0%)

---

## Design Principles

### 1. Preserve Over Interpret
**v3.0.0:** Keep all content, add light hints
**NOT:** Force into predefined categories

### 2. Page Context Matters
**v3.0.0:** Maintain page numbers, table locations
**NOT:** Flatten everything into one structure

### 3. PLANNER is the Interpreter
**v3.0.0:** EXTRACTOR preserves, PLANNER decides meaning
**NOT:** EXTRACTOR decides what's important

### 4. No Data Loss
**v3.0.0:** If it's in the PDF, it's in the output
**NOT:** Discard content that doesn't fit schema

### 5. Structure Aids Understanding
**v3.0.0:** Keep tables as tables, lists as lists
**NOT:** Convert everything to flat key-value pairs

---

## Usage by Downstream Agents

### PLANNER Phase 1 (Enrichment):
```python
# Find composition tables
for page in extracted_facts["pages"]:
    for table in page["tables"]:
        if table["interpretation_hint"] == "composition_data":
            # Extract pollutants from rows
            for row in table["rows"]:
                pollutant = {
                    "name": row[0],
                    "cas": row[1],
                    "percentage": row[2]
                }
                # Enrich: Look up missing CAS via web_search
                if not pollutant["cas"]:
                    pollutant["cas"] = await web_search(f"{pollutant['name']} CAS number")
```

### PLANNER Phase 2 (Subagent Creation):
```python
# Find VOC measurement pages
voc_pages = [
    p for p in extracted_facts["pages"]
    if any(t["interpretation_hint"] == "voc_measurements" for t in p["tables"])
]

# Create subagent with ONLY relevant pages
create_subagent({
    "name": "VOC Chemistry Expert",
    "task": "Analyze VOC composition and reactivity",
    "context": {
        "relevant_pages": voc_pages,  # Only pages 5, 6, 7
        "quick_facts": extracted_facts["quick_facts"]["cas_numbers_found"]
    }
})
```

### SUBAGENT:
```python
# Receives filtered content
context = agent_definition["context"]
relevant_pages = context["relevant_pages"]

# Can reference specific tables
for page in relevant_pages:
    for table in page["tables"]:
        if table["interpretation_hint"] == "voc_measurements":
            # Analyze this specific table
            analyze_voc_composition(table)
```

---

## Migration from v2.0.0

### Breaking Changes:
1. Output schema completely different
2. No more `pollutant_characterization.pollutant_list[]`
3. No more `process_parameters.flow_rate`
4. Must read from `pages[]` structure

### Migration Code Pattern:
```python
# OLD (v2.0.0)
pollutants = extracted_facts["pollutant_characterization"]["pollutant_list"]
for p in pollutants:
    print(p["name"], p["cas_number"])

# NEW (v3.0.0)
for page in extracted_facts["pages"]:
    for table in page["tables"]:
        if table["interpretation_hint"] == "composition_data":
            for row in table["rows"]:
                name = row[0]
                cas = row[1]
                print(name, cas)
```

---

## Validation Rules

### document_metadata:
- `document_type` must be one of enum values
- `total_pages` must match len(pages[])
- `language` must be ISO 639-1 code

### pages[]:
- `page_number` must be sequential (1, 2, 3, ...)
- At least one of: headers, body_text, tables, key_value_pairs must be non-empty

### tables[]:
- If headers present, all rows must have same number of cells
- `interpretation_hint` must be one of enum values

### quick_facts:
- `cas_numbers_found` must be valid CAS format (digits-digits-digit)
- `voc_svoc_detected` must be boolean

### extraction_notes[]:
- `status` must be one of enum values
- `field` must be valid JSON path

---

## Token Impact

**v2.0.0:** ~3,200 tokens (prompt only)
**v3.0.0:** ~3,500 tokens (prompt) + ~500 tokens (schema examples)
**Total:** ~4,000 tokens

**Why larger?**
- More detailed schema definition
- interpretation_hint examples for tables
- content_categories examples for pages

**Offset:**
- PLANNER filters content → subagents receive less
- Overall pipeline: similar or lower token usage

---

**Document Version:** 1.0
**Status:** APPROVED ✅
**Next Step:** Create EXTRACTOR v3.0.0 prompt using prompt-engineering-specialist
