# Spec 09: Practitioner Consult Session Opening AI Patient & History Summary

## Overview
Every consultation session in the Practitioner portal (`/practitioner/consult`) begins with an AI-generated clinical briefing that synthesizes the patient's baseline profile and all recorded health and consultation histories strictly up until that consultation session's point in time (`started_at`).

## Architecture & Data Flow

### 1. Database & Schema
- `sessions` table in the practitioner's vault now includes `initial_summary TEXT`.
- `ensure_schema` runs `ALTER TABLE sessions ADD COLUMN IF NOT EXISTS initial_summary TEXT;` to support existing practitioner vaults.
- Sessions preserve the opening summary indefinitely alongside `turns` for longitudinal auditability.

### 2. Up-To Consultation Point Boundary
- `vault.get_patient_history_up_to(practitioner_id, client_id, consultation_point)`:
  - Strictly queries `record_entries` where `created_at <= consultation_point`.
  - Strictly queries `intake_notes` where `updated_at <= consultation_point`.
  - Strictly queries `questionnaire_responses` where `submitted_at <= consultation_point`.
  - Strictly queries prior `sessions` where `started_at < consultation_point`, along with their recorded summaries.
  - Ensures no future patient data or subsequent consultation outcomes leak into historical consultation sessions.

### 3. AI Briefing Synthesis
- `reasoner.generate_consult_intake_summary(history_data, consultation_point)`:
  - Dispatches to `Role.REASONER` with prompt `CONSULT_INTAKE_SYSTEM`.
  - Structured Markdown output sections:
    - `## Patient Overview`: Name, DOB, Country, Consultation Timestamp.
    - `## Active Clinical Profile`: Active conditions, current medications, recent labs/diagnostics, and clinical notes / intake responses.
    - `## Prior Consultations & Clinical Trajectory`: Chronological summary of prior consult sessions, outcomes, and progress up to this point. (Explicitly notes "No prior consultation sessions recorded before this consultation." if none).
    - `## Consultation Focus & Recommendations`: Targeted clinical considerations and recommended focal points for the practitioner in this session.
  - Robust deterministic fallback (`format_deterministic_consult_summary`) ensures 100% reliability, zero downtime, and zero hallucinations if the external LLM is offline or in testing.

### 4. API Endpoints
- `POST /api/me/clients/{client_id}/sessions/init`:
  - Initializes a new consultation session with timestamp `now_ts`.
  - Generates the opening AI summary up to `now_ts` and writes it to `sessions.initial_summary`.
  - Returns `{ id, client_id, title: "Consultation Session", started_at, initial_summary, turns: [] }`.
- `GET /api/me/clients/{client_id}/sessions/{session_id}`:
  - Returns session details, turns, documents, and `initial_summary`.
  - If `initial_summary` is missing (legacy session), lazily generates and saves it using `started_at` as the historical boundary.
- `POST /api/me/consult`:
  - Accepts `session_id`. If title is default `"Consultation Session"`, updates title to the first question asked.
  - Preprends opening AI briefing and prior discussion history into the consultation context for multi-turn continuity.

### 5. Frontend UI (`/practitioner/consult`)
- Selecting a client or clicking "New session" initiates the session and displays a smooth progress indicator while generating the briefing.
- Renders an **AI Clinical Briefing & History Summary** card at the very top of the consultation thread:
  - Styled with frosted glass surface, accent indicator, title, and patient chips.
  - Interactive expand/collapse toggle for practitioner focus during long consultations.
  - Fully formatted Markdown via `renderAnswerHtml`.
- Subsequent questions and AI turns stack seamlessly underneath the briefing.
- Loading historical sessions from the History rail displays that session's exact opening briefing recorded up to its historical point in time.
