# Specs v15 / 15 — Domain-Mindful Tag Generation & Concept Extraction

## 1. Problem Statement & Root Cause
When non-clinical sources—such as clinic marketing brochures, commercial promotions, pricing packages, corporate announcements, or operational guidelines—were ingested into the system:
1. **Misclassification as Clinical Specialties**: The Reader agent frequently tagged marketing documents with generic clinical umbrella categories such as `"integrated medicine"` or `"integrative medicine"`. This happened because prompt instructions instructed the model to reuse existing library topic shelves without domain distinction, and the taxonomy lacked `"marketing"` and `"administrative"` document types.
2. **Clinical Graph Pollution**: During passage extraction (`extract_graph`), MedGemma attempted to extract clinical entities (`Condition`, `Procedure`, `Medication`) and verbs (`TREATS`, `CAUSES`) from marketing copy, extracting clinic names or promotional slogans as clinical procedures/conditions and fabricating false treatment relationships in the knowledge graph.

## 2. Architecture & Implementation Changes

### 2.1 Formal Document Taxonomy Extension
- Added `"marketing"` and `"administrative"` to `DOC_TYPES` in `app/graph/store.py` and `web/src/routes/(admin)/admin/library/+page.svelte`.
- Now supports explicit non-clinical document classification alongside `"article"`, `"book"`, `"presentation"`, `"education material"`, `"lecture notes"`, `"protocol"`, `"picture"`, `"chart"`, and `"other"`.

### 2.2 Reader Domain Mindfulness & Tag Sanitization (`app/ingestion/pipeline.py`)
- **System Instructions (`READER_SYSTEM`)**:
  - Distinguishes clinical/biomedical material from marketing, promotional, commercial, or operational copy.
  - Documents identified as promotional or marketing must have `doc_type: "marketing"`.
  - Commercial copy is assigned a low clinical evidence grade (1–3 out of 10).
  - Explicit rule: *Never* tag marketing or operational documents with clinical condition tags or broad clinical specialty labels (such as `"integrated medicine"`, `"integrative medicine"`, `"functional medicine"`, `"cardiology"`, `"oncology"`).
- **Prompt Guidance**:
  - Replaces blanket topic reuse with: *"reuse ONLY if genuinely relevant to the source's actual content"*.
- **Post-Processing Topic Sanitizer**:
  - Strips catch-all clinical specialty terms (`DISALLOWED_CLINICAL_TAGS_FOR_NON_CLINICAL`) from documents with `doc_type == "marketing"` or `"administrative"`.
  - Injects appropriate functional tags (e.g. `"marketing"`, `"administrative"`) if stripped topics leave the list devoid of domain labels.
  - Caps reliability grade at 3 for marketing copy.

### 2.3 Concept Extraction Gating & Graph Filtering (`app/ingestion/pipeline.py`)
- **Knowledge Graph Builder Instructions (`KG_BUILDER_SYSTEM`)**:
  - Passage relevance gate: If a passage is marketing, commercial, promotional, administrative, or contains no actionable biomedical facts, the agent returns empty extraction: `{"entities": [], "relationships": []}`.
  - Forbidden non-entities: Never extract clinic names, umbrella specialties, staff titles, or marketing slogans as entities.
  - Prohibits hallucinated treatment claims from marketing text.
- **Deterministic Post-Processing & Filtering (`extract_graph`)**:
  - Maintained `DISALLOWED_GENERIC_ENTITIES` blacklist covering terms like `"integrated medicine"`, `"integrative medicine"`, `"functional medicine"`, `"medicine"`, `"healthcare"`, `"wellness"`, `"clinic"`, `"hospital"`, `"treatment"`, etc.
  - Sanitizes and trims punctuation from extracted entity names.
  - Drops dangling and self-referential relationships where either head or tail was filtered out.
  - Deduplicates surviving entities and relationships.

## 3. Verification & Testing
- `tests/test_domain_mindful_ingestion.py`:
  - Verifies that marketing PDF brochures with hallucinated "integrated medicine" have those tags stripped, receive marketing tags, and have reliability grade capped <= 3.
  - Verifies that valid clinical guidelines retain clinical topics and high grades.
  - Verifies that `extract_graph` strips disallowed generic entities and drops associated relationships while preserving genuine clinical entities (e.g., Metformin TREATS Type 2 Diabetes).
  - Verifies that purely non-clinical text returns empty entity and relationship sets without error.
- Full test suite passed (17 tests passing).
- Web TypeScript check and production build verified with 0 errors.
