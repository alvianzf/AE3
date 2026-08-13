# 12 · Verification

v1's success criteria (grounded answers, citation, grade threshold,
refusal on no match, conversational follow-up, erasure, deep-document
recall — [v1/01-overview.md](../v1/01-overview.md#success-criteria)) still
hold and are still tested by `verify.py` against the shared library and
retrieval pipeline, unchanged.

What's new for v2:

| # | Criterion | How verified |
|---|---|---|
| 1 | A practitioner signup is invisible in the public directory until admin-approved | Sign up, assert `GET /api/practitioners` excludes them; approve; assert it now includes them |
| 2 | A contact form submission reaches the right practitioner and shows up in their portal and the admin's stats | Submit on a coach's detail page; assert the row appears in both `GET /api/me/contacts` (that practitioner) and `GET /api/admin/stats` |
| 3 | Basic practitioners cannot reach any Pro-only route | Assert `POST /api/me/consult` and `/api/me/clients` 403/404 for a Basic account |
| 4 | Upgrading to Pro creates exactly one vault, and downgrading preserves it | Upgrade → assert vault file exists; cancel subscription (test-mode webhook) → assert vault file still exists but portal routes are blocked |
| 5 | Practitioner A cannot read Practitioner B's clients under any client id, guessed or real | Attempt cross-tenant fetch with a real client id from another vault; assert 404, not data |
| 6 | A Pro consultation call is billed against the practitioner's own Anthropic key, not the platform's | Assert the API key used in the outbound Anthropic call matches the practitioner's stored (decrypted) key, via a test double on the Anthropic client |
| 7 | Client erasure redacts vault audit detail while keeping the rows, same as v1 | Same test as v1's patient erasure, run against a vault instead of the single patient DB |
| 8 | A questionnaire edit does not alter answers already submitted against the prior version | Submit a response, edit the questionnaire, assert the stored response still carries the original `questionnaire_version` and its original question text is recoverable |
| 9 | Wearable connect writes a connection row and fixture data, and is labeled as fixture data, not silently presented as live | Connect a test client to a wearable provider; assert `wearable_connections` and `wearable_data_points` are populated, and that the API response or portal UI marks it as sample data |

Criteria 1-8 are testable without any real Stripe or OAuth credentials
(Stripe test mode, mocked OAuth callback). Criterion 9's fixture-data
requirement makes it testable the same way even before real vendor
integration exists.
