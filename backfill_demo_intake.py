"""One-off backfill: give the demo Pro practitioner's existing clients a
themed questionnaire response, some intake notes, and a couple of
consultations with clinician-note/client-report documents, so the new
intake-review and reports UI has something to show instead of empty states.

Run once on the server: `python3 backfill_demo_intake.py`. Idempotent for the
questionnaire (reuses the active one if it already has the right theme set)
but NOT idempotent for session/response data — running it twice creates
duplicate sample sessions. Not a route, not part of the app; delete after use,
same convention as migrate_v1_data.py.
"""
from app import core_store, vault

THEMES = [
    ("Presenting picture", [
        ("What brought you in today?", "text", []),
        ("How long has this been going on?", "choice", ["Days", "Weeks", "Months", "Years"]),
    ]),
    ("Gut & digestion", [
        ("Any bloating or discomfort after meals?", "choice", ["Never", "Sometimes", "Often"]),
        ("Bowel movement frequency", "choice", ["Daily", "Every 2-3 days", "Less often"]),
        ("Digestive symptoms (check all that apply)", "multi_choice",
         ["Bloating", "Constipation", "Diarrhea", "Reflux", "None"]),
    ]),
    ("Energy, stress & sleep", [
        ("Average hours of sleep per night", "number", []),
        ("How would you rate your stress level (1-10)?", "number", []),
        ("Do you wake up feeling rested?", "choice", ["Yes", "No", "Sometimes"]),
    ]),
    ("Hormonal & metabolic", [
        ("Any recent weight changes?", "text", []),
        ("Menstrual cycle regularity (if applicable)", "choice", ["Regular", "Irregular", "N/A"]),
    ]),
    ("Medical & medications", [
        ("Current medications or supplements", "text", []),
        ("Known allergies", "text", []),
    ]),
    ("Diet & nutrition", [
        ("Describe a typical day of eating", "text", []),
        ("Dietary pattern (check all that apply)", "multi_choice",
         ["Omnivore", "Vegetarian", "Vegan", "Low-carb", "Gluten-free"]),
    ]),
    ("Environment & exposure", [
        ("Occupational or environmental exposures", "text", []),
        ("Date of last physical exam", "date", []),
    ]),
]

SAMPLE_ANSWERS = {
    "text": "Ongoing fatigue and low energy most afternoons.",
    "number": "6",
    "date": "2026-03-10",
    "choice": None,   # filled from options[0] at build time
    "multi_choice": None,  # filled from options[:2] at build time
}


def build_questionnaire(created_by: str) -> dict:
    questions = []
    for theme, qs in THEMES:
        for prompt, qtype, options in qs:
            questions.append({"prompt": prompt, "input_type": qtype,
                               "theme": theme, "options": options})
    return core_store.create_questionnaire(
        "Intake questionnaire (demo)", questions, created_by)


def sample_answers(questionnaire: dict) -> dict:
    answers = {}
    for q in questionnaire["questions"]:
        if q["input_type"] == "choice":
            answers[q["id"]] = (q["options"] or ["Sometimes"])[0]
        elif q["input_type"] == "multi_choice":
            answers[q["id"]] = (q["options"] or ["None"])[:2]
        else:
            answers[q["id"]] = SAMPLE_ANSWERS[q["input_type"]]
    return answers


def main() -> None:
    practitioners = [p for p in core_store.list_practitioners() if p["plan"] == "pro"]
    if not practitioners:
        print("No Pro practitioners found — nothing to backfill.")
        return

    questionnaire = build_questionnaire("backfill-script")
    print(f"Created questionnaire {questionnaire['id']} "
          f"({len(questionnaire['questions'])} questions, {len(THEMES)} themes)")

    for practitioner in practitioners:
        clients = vault.list_clients(practitioner["id"])
        if not clients:
            print(f"{practitioner['email']}: no clients, skipping")
            continue
        for client in clients:
            answers = sample_answers(questionnaire)
            vault.save_questionnaire_response(
                practitioner["id"], client["id"], questionnaire["id"],
                questionnaire["version"], answers)
            vault.upsert_intake_note(
                practitioner["id"], client["id"], "Gut & digestion",
                "Symptoms consistent with mild dysbiosis — consider stool panel.")
            vault.upsert_intake_note(
                practitioner["id"], client["id"], "Energy, stress & sleep",
                "Sleep quality poor; discuss sleep hygiene at next visit.")

            session = vault.create_session(practitioner["id"], client["id"],
                                            "Initial consultation")
            vault.add_turn(
                practitioner["id"], session["id"],
                "What dietary changes would help with the reported bloating?",
                "Based on the intake, a low-FODMAP trial for 2-3 weeks is a "
                "reasonable first step, alongside tracking symptom timing "
                "relative to meals.",
                {"matched": True, "min_grade": 3})
            vault.set_session_status(practitioner["id"], session["id"], "done")
            vault.save_document(
                practitioner["id"], session["id"], client["id"], "clinician_note",
                "Client presents with intermittent bloating and low energy. "
                "Discussed low-FODMAP trial. Follow up in 3 weeks.", "final")
            vault.save_document(
                practitioner["id"], session["id"], client["id"], "client_report",
                "Thanks for coming in today. Based on what you shared, we "
                "recommend trying a low-FODMAP diet for the next 2-3 weeks "
                "and keeping a short symptom log. We'll check in at your "
                "next visit.", "draft")

            session2 = vault.create_session(practitioner["id"], client["id"],
                                             "Follow-up check-in")
            print(f"  {client['name']}: response + notes + 2 sessions "
                  f"(1 done w/ documents, 1 open: {session2['id']})")

    print("Done.")


if __name__ == "__main__":
    main()
