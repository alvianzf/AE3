# 01 · Patient context: adapting to the existing SQLite vault

The brief specified a MySQL patient database with clean
conditions/medications/labs columns. This repo has no MySQL — patient
("client") data lives in a per-practitioner SQLite vault
(`app/vault.py`), where clinical detail was, until this change, free-text
`record_entries` tagged only `lab`/`history`/`note`/`session_summary`
(no distinction between a condition and a medication at all).

**Decision (explicit, asked and answered)**: adapt `get_patient_context()`
to the existing vault rather than stand up a new database.

## What changed to make this work

`vault.KINDS` gained two entries: `"condition"` and `"medication"` — so
new entries can be tagged precisely. Existing entries stay filed under
`"history"`/`"note"`; there is no backfill migration.

## Two real gaps this surfaces rather than hides

1. **Historical entries are unclassified.** Anything recorded before this
   change is `"history"`/`"note"`, and `get_patient_context()` cannot
   tell a past condition from a current medication in that data — it
   returns them separately as `legacy_notes`, not guessed into one bucket
   or the other. A practitioner asking a drug-interaction question about
   a patient whose medications were only ever recorded as plain "history"
   notes won't get those surfaced as `medications` — they're in
   `legacy_notes`, included in the LLM-facing text block
   (`PatientContext.as_query_text()`) but not structurally distinguished.
2. **The questionnaire response is unstructured.** It's a free-form JSON
   blob (question text → answer text), included as supplementary text
   (`questionnaire_summary`), not parsed into conditions/medications
   fields.

Neither gap is silent: `PatientContext` has a `legacy_notes` field and a
`questionnaire_summary` field specifically so a caller (or a future
audit) can see that this data wasn't cleanly structured, not just get a
plausible-looking empty `medications: []`.
