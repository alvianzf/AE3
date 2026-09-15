# Lab intake: practitioners and clients can both record patient data

## The gap

`app/patient/context.py`'s `get_patient_context()` has read
conditions/medications/labs from `record_entries` since the module was
written (`v5`) — `as_query_text()` folds them into every seed search,
traversal judgment, and Reasoner call. Nothing ever wrote a `lab`,
`condition`, or `medication` entry: `vault.add_entry()` was only ever
called for `session_summary`. Found live, 2026-09-14: every real
client's `recent_labs` was empty not because no labs existed, but
because there was no way to record one. A placeholder-text bug in the
Reasoner (`[patient data]` standing in for a value it didn't have)
traced back to this same root cause.

## What was built

**Backend** (`app/vault.py`, `app/main.py`): `vault.list_entries()`
and `vault.delete_entry()` (new — `add_entry()` already existed).
Three practitioner-facing routes (`GET`/`POST`/`DELETE
/api/me/clients/{id}/entries`, full CRUD, any kind except
`session_summary`) and three client-facing ones (`GET`/`POST`/`DELETE
/api/me/entries`, scoped to the client's own record via their own
session — `practitioner_id`/`client_id` come from `session
["practitioner_id"]`/`session["id"]`, never a route param).

**Privacy boundary**: a client's self-reported entries are marked with
a `"[patient-reported] "` content prefix — no schema change, since
`record_entries` has no author column. This does real work, not just
cosmetic labeling:
- The client-facing `GET` only returns entries carrying that prefix —
  a practitioner's private clinical notes/conditions/medications about
  a client are never exposed back to that client.
- The client-facing `DELETE` checks for the prefix before deleting —
  a client can only remove what they themselves added, never a
  practitioner's entry, even one about them.
- The practitioner-facing panel strips the prefix for display and
  shows a "Patient-reported" chip instead, so provenance is visible
  without the raw marker leaking into the UI.

**Frontend**: a "Record" panel on the practitioner's client detail
page (`clients/[id]/+page.svelte` — add/list/remove, any kind); a new
"Health record" page in the client portal (`client/record/+page.svelte`
— add/list/remove, self-reported only), added to the client nav.
Linked from the consult page's patient widget ("Edit patient record").

## Verified live

Full round-trip through `get_patient_context().as_query_text()` on
production (an isolated scratch client, cleaned up after): a recorded
lab entry appeared correctly formatted with its real date. Privacy/
permission boundary verified directly: a practitioner-authored entry
and a client-authored entry both visible to `list_entries()` (the
practitioner's own view), but only the client-authored one passed the
client-facing filter; a client's delete attempt against the
practitioner's entry correctly blocked before calling `delete_entry()`
at all.

## What this does not change

`get_patient_context()`'s reading logic (`app/patient/context.py`) is
untouched — it already read these fields correctly; this is the
missing write path, not a change to how retrieval uses patient
context. Also fixed in the same pass (not a schema/endpoint change):
`as_query_text()` used to silently omit the labs/legacy-notes/
questionnaire lines when empty instead of stating "none recorded" the
way conditions/medications already did — an omitted line reads as "not
checked," which is exactly the ambiguity a placeholder papers over.
Now always stated explicitly.
