# 06 · Client portal

Clinic speaks to a client directly for the first time in this version — v1
was explicit that "Clinic never speaks to a patient." That constraint is
gone here.

## Signup

Regular self-service signup on the public website: name, email, password.
No invitation required. After signup, a client either:

- picks a practitioner from the directory themselves, or
- is already associated with one because a Pro practitioner created their
  record first ([05](05-practitioner-portal.md)) and they're completing the
  signup that record started.

Either path lands the client's identity and clinical data in that
practitioner's vault ([02](02-data-model.md)) — a client belongs to exactly
one practitioner in this version; there is no multi-practitioner client
relationship.

## Initial questionnaire

On first login (or right after signup), the client completes the admin's
currently-active questionnaire ([04](04-admin-portal.md#3-questionnaire-admin)).
The response is stored in their practitioner's vault, tagged with the
questionnaire's version at time of submission.

## File upload

A client can upload files — lab work PDFs and similar — which are stored
under that practitioner's vault-files directory
([02](02-data-model.md#filesystem)), same id-not-filename convention v1 used
for library originals. These become available to the practitioner as record
entries.

## Wearable integration

OAuth connect flow for **Oura, Whoop, and Garmin**. The connect button and
callback are real — a client authorizes the app with the vendor, and a
`wearable_connections` row is written ([02](02-data-model.md)).

**What's not real yet:** the data behind a connection is fixture/dummy data,
not a live pull from the vendor's API. `wearable_data_points` is populated
with representative sample values on connect. This is a deliberate scope cut
for this version, not an oversight — building against three real vendor APIs
(auth scopes, rate limits, data normalization per provider) is separable
work from proving the connect flow and the data model shape it needs to
land in. Swapping fixture data for a live pull later should not require a
schema change.

## What's explicitly not here

No booking, no telehealth video, no client-initiated payments — all out of
scope for this version ([01](01-overview.md)).
