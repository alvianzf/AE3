"""Final step: the pruned, accumulated KB context + raw patient data go to
KIMI-K3 (Role.REASONER) once per query — this is where the expensive
reasoning belongs, per the brief; every earlier LLM call in the pipeline
(Reader/KG-builder at ingest time, Answer Engine's seed-query-forming and
per-hop relevance judging at query time) is deliberately cheap and fast.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from ..clients.llm_client import Role, get_client
from ..graph import store
from ..patient.context import PatientContext
from ..retrieval.traversal import TraversalResult

# moonshotai/Kimi-K3's hidden chain-of-thought pass costs 30-120s+ per
# call with no visible quality difference on this app's prompts (found
# live, 2026-09-14) — disabled for every Reasoner call. Harmless to leave
# on unconditionally even now that the default REASONER_MODEL is Qwen3-235B
# (config.py) — a non-reasoning model with no "thinking" field of its own
# just ignores this extra_body key (confirmed live), so this stays applied
# regardless of which model REASONER_MODEL actually points at, including a
# future switch back to Kimi-K3 on a dedicated EU endpoint.
_NO_THINKING = {"thinking": {"type": "disabled"}}

REASONER_SYSTEM = (
    "You are an experienced functional health practitioner advising a fellow "
    "practitioner during a consultation — a knowledgeable colleague speaking "
    "from what you know, not a search tool reporting results. Never describe "
    "yourself as searching, looking something up, or consulting a database/"
    "library/knowledge base — speak in first person, the way a colleague "
    "states what they know or admits they don't, not the way a system reports "
    "what a query returned.\n\n"
    "What you 'know' is strictly bounded by the accumulated context below and "
    "the client's own data — you have no other knowledge available to you "
    "here — but that boundary is a fact about your input, not something to "
    "narrate to the reader.\n\n"
    "Rules:\n"
    "- Cite the chunk or entity behind each clinical point inline, as [1], [2].\n"
    "  A claim with no citation is a claim with no evidence — don't make it.\n"
    "- A passage that is merely topic-adjacent does NOT cover the question. If no "
    "passage directly and specifically addresses what was asked, do not construct "
    "an answer by inference, extrapolation, or general clinical reasoning from "
    "nearby context — that is fabrication even if it sounds plausible. In that "
    "case the entire response is one short, direct sentence: that you don't have "
    "anything on it. Stop there. Do not describe what the retrieved context does "
    "cover instead, do not explain why, do not say what would be needed to answer "
    "it — every one of those is padding around 'no' and reads as an excuse. If "
    "there's nothing, say there's nothing.\n"
    "- Never fill a gap from general knowledge, training data, or what's usually "
    "true in medicine. If it isn't in the context below, it isn't in this answer.\n"
    "- Every source below is labeled with a trust score out of 10 — every "
    "source is eligible to inform your answer regardless of its score, a "
    "lower-trust source is not excluded, but if two sources genuinely "
    "disagree, prefer the higher-trust one and say so (e.g. 'the "
    "higher-confidence source indicates...'), rather than presenting the "
    "conflict as unresolved or silently picking one.\n"
    "- A real answer can draw on more than one passage: if no single "
    "passage fully covers the question but multiple passages, read "
    "together, directly establish the answer, synthesize across them and "
    "cite each one you relied on — that is reasoning from the context, not "
    "fabrication. The fabrication rule above is about adding something no "
    "passage supports, not about requiring one single passage to carry the "
    "whole answer alone.\n"
    "- Weigh the client's specific conditions, medications, and labs explicitly "
    "where they matter — a general answer that ignores what's already in front of "
    "you about this client is not the answer this client needs.\n"
    "- Never write a placeholder in brackets (like '[client data]', '[insert "
    "value]', '[age]') standing in for a real value. Either use the actual value "
    "given in the client context below, or, if it isn't recorded, say plainly "
    "that it isn't recorded — never leave a template slot unfilled in the output.\n"
    "- Be terse and clinical, not flowery: short sentences, no preamble, no "
    "restating the question, no hedging filler, no excessive explanation of "
    "things the practitioner already knows. State the point, "
    "cite it, move to the next point — don't pad a short answer into a long "
    "one. No throat-clearing opening "
    "sentence either — never something like 'To improve X, focusing on Y is "
    "vital. Here's how you can approach this with [client]:' before the "
    "actual content. The first sentence must already be a real clinical "
    "point, not a framing sentence about the point to come. Likewise no "
    "closing wrap-up sentence ('In summary...', 'Overall...') — stop when "
    "the content is done.\n\n"
    "Start directly with the clinical answer itself, as concisely as the "
    "context allows — no '## Answer' heading or any other preamble before "
    "it, just the content. After that, structure the rest in Markdown with "
    "these sections, omitting a section entirely (heading included) if it "
    "has nothing to say:\n"
    "## Confirm with client\n"
    "A short bullet list of what to ask or verify with this client before "
    "acting on the answer — only include this if something genuinely needs "
    "confirming, not as a rote checklist.\n"
    "## Next steps\n"
    "A short bullet list of concrete next actions for the practitioner."
)


@dataclass
class ReasonedAnswer:
    text: str
    usage: dict
    citations: list[dict]  # the accumulated records actually shown to the model


def _label(node: dict) -> str:
    if store.is_chunk(node):
        grade = node.get("grade")
        trust = f", trust {grade}/10" if grade is not None else ""
        return f"(source: {node.get('document_title', 'unknown')}{trust}) {node['text']}"
    return f"(entity, {store.node_type(node)}: {node.get('name', node.get('id'))})"


def _build_answer_prompt(question: str, patient: PatientContext, traversal: TraversalResult,
                         unsupported: list[str] | None, pattern_context: str | None) -> str:
    """Shared by answer() and answer_streaming() below — the exact same
    prompt either way, the only difference is whether the Reasoner call
    streams its text back or returns it all at once.

    `unsupported` is only passed on the one bounded revision retry
    (mirrors the pre-existing Checker retry pattern) — the Checker's own
    list of sentences it couldn't ground in the accumulated context. The
    instruction is strictly "ground it or drop it": no new context is
    supplied, so a flagged sentence can only be tied to context already
    given, or removed."""
    if traversal.accumulated:
        block = "\n\n".join(
            f"[{i + 1}] {_label(node)}" for i, node in enumerate(traversal.accumulated)
        )
    else:
        block = "(the traversal found nothing surviving relevance pruning)"
    revision_block = ""
    if unsupported:
        claims = "\n".join(f"- {c}" for c in unsupported)
        revision_block = (
            "\n\nAn independent check of your previous draft found these sentences "
            f"not actually supported by the context above:\n{claims}\n\n"
            "Write a new answer. For each of those, either tie it explicitly to "
            "context that genuinely supports it, or remove it — do not keep it by "
            "rephrasing it more vaguely. Do not introduce new claims the context "
            "doesn't cover either."
        )
    # De-identified, pooled across every practitioner (app/clinical_
    # patterns.py) — background context for approach only, never a
    # source of fact about this specific patient, so it's kept in its
    # own clearly-labeled block rather than folded into the patient
    # context or knowledge-base context above.
    pattern_block = f"\n\n{pattern_context}" if pattern_context else ""
    return (
        f"Client context:\n{patient.as_query_text()}\n\n"
        f"Accumulated knowledge-base context:\n---\n{block}\n---\n\n"
        f"Practitioner's question: {question}{revision_block}{pattern_block}"
    )


def answer(question: str, patient: PatientContext, traversal: TraversalResult,
          unsupported: list[str] | None = None, pattern_context: str | None = None) -> ReasonedAnswer:
    prompt = _build_answer_prompt(question, patient, traversal, unsupported, pattern_context)
    text, usage = get_client(Role.REASONER).chat_text(
        REASONER_SYSTEM, prompt, max_tokens=100_000, extra_body=_NO_THINKING)
    return ReasonedAnswer(text=text, usage=usage, citations=traversal.accumulated)


def answer_streaming(question: str, patient: PatientContext, traversal: TraversalResult,
                     unsupported: list[str] | None = None, pattern_context: str | None = None):
    """Same prompt as answer() above, but streams the Reasoner's text as
    it's generated — yields ("delta", text_chunk) for each chunk, then
    exactly one ("done", ReasonedAnswer) at the end, same (kind, payload)
    shape app/retrieval/traversal.py's retrieve_streaming() already uses.
    Lets app/main.py's consult route forward real answer text to the
    practitioner as it's written instead of only after the full ~20-40s
    call completes — the answer is still re-checked by
    app/reasoning/llm_checker.py exactly as before once streaming
    finishes; nothing about the grounding/anti-fabrication guarantees
    changes, only when the text first becomes visible."""
    prompt = _build_answer_prompt(question, patient, traversal, unsupported, pattern_context)
    parts: list[str] = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    for kind, payload in get_client(Role.REASONER).chat_text_stream(
        REASONER_SYSTEM, prompt, max_tokens=100_000, extra_body=_NO_THINKING):
        if kind == "delta":
            parts.append(payload)
            yield "delta", payload
        else:
            usage = payload
    yield "done", ReasonedAnswer(text="".join(parts), usage=usage, citations=traversal.accumulated)


SUMMARY_SYSTEM = (
    "Write a structured session summary for a client's clinical record — "
    "this is read by the next practitioner before a future consultation, and "
    "feeds the opening-briefing generator (generate_consult_intake_summary) "
    "that every later session's 'big picture' view is built from. It must "
    "carry every finding a future session would need, not a vague gloss — "
    "found live: a thin 3-4 sentence summary left nothing for a multi-session "
    "client's cross-session briefing to actually synthesize from.\n\n"
    "Structure in Markdown with these sections, omitting one entirely only "
    "if it genuinely has nothing to report:\n"
    "## Key findings\n"
    "Every flagged or clinically significant marker/result discussed this "
    "session, each with its value and why it matters — every flagged "
    "marker, not a representative sample of them.\n"
    "## Hypotheses discussed\n"
    "Every clinical hypothesis or working theory raised, even a tentative "
    "one, stated specifically (what it is, not just that one was raised).\n"
    "## Action plan\n"
    "Every concrete recommendation, protocol, or next step agreed or "
    "proposed this session.\n"
    "## Follow-up needed\n"
    "Anything still open — a pending retest, an unanswered question, a "
    "thing the next session should check.\n\n"
    "Terse and specific — a bullet per item, not a paragraph restating the "
    "conversation. Every claim must come from what was actually discussed "
    "in the transcript below, never filled in from general clinical "
    "knowledge."
)


def summarize_session(transcript: str) -> str:
    # Role.CHECKER, not Role.REASONER: same shape as the fix to
    # generate_consult_intake_summary below — this is a short clinical-
    # record note (3-4 sentences restating what was asked/advised), not
    # the citation-grounded, anti-fabrication-constrained answer that
    # actually justifies Reasoner's top-tier model. Quality-sensitive but
    # not THE answer, and it runs once per session, so it belongs on the
    # Reader/Checker tier (see llm_client.py's _ANTHROPIC_MODELS comment).
    text, _usage = get_client(Role.CHECKER).chat_text(
        SUMMARY_SYSTEM, transcript, max_tokens=100_000, extra_body=_NO_THINKING)
    return text


CONSULT_INTAKE_SYSTEM = (
    "You are an experienced practitioner preparing a colleague for a consultation session.\n"
    "Synthesize a clear, structured clinical briefing of the client and their full consultation and health history "
    "up until this consultation point.\n\n"
    "Structure your summary in Markdown with the following exact section headings:\n"
    "## Client Overview\n"
    "Concise overview of client demographics (name, DOB, country) and key baseline presentation.\n\n"
    "## Active Clinical Profile\n"
    "- Active conditions (or state 'None recorded')\n"
    "- Current medications and dosages (or state 'None recorded')\n"
    "- Recent laboratory / diagnostic findings (or state 'None recorded')\n"
    "- Clinical notes and intake responses (or state 'None recorded')\n\n"
    "## Prior Consultations & Clinical Trajectory\n"
    "Chronological synthesis of all prior consultation sessions and outcomes up to this consultation point.\n"
    "If no prior consultations exist, state plainly: 'No prior consultation sessions recorded before this consultation.'\n"
    "If prior consultations exist, summarize what was discussed, advice given, and longitudinal progress.\n\n"
    "## Consultation Focus & Recommendations\n"
    "Concrete, high-value clinical considerations, key check-ins, or areas to investigate in today's consult.\n\n"
    "Rules:\n"
    "- Terse, professional, clinical prose. No fluff, pleasantries, or preamble.\n"
    "- Strictly grounded only in the provided client data and history up to the consultation point."
)


def format_deterministic_consult_summary(history_data: dict, consultation_point: str) -> str:
    client = history_data.get("client") or {}
    name = client.get("name", "Client")
    dob = client.get("dob") or "Not recorded"
    country = client.get("country") or "Not recorded"

    entries = history_data.get("entries") or []
    conditions = [e["content"] for e in entries if e["kind"] == "condition"]
    medications = [e["content"] for e in entries if e["kind"] == "medication"]
    protocols = [e["content"] for e in entries if e["kind"] == "protocol"]
    labs = [f"{e['content']} ({e['created_at'][:10]})" for e in entries if e["kind"] == "lab"]
    legacy_notes = [f"[{e['kind']}] {e['content']}" for e in entries if e["kind"] in ("history", "note")]

    intake_notes = history_data.get("intake_notes") or []
    questionnaire = history_data.get("questionnaire")
    prior_sessions = history_data.get("prior_sessions") or []

    ts_label = consultation_point[:19].replace("T", " ") if consultation_point else "Current"

    lines = [
        "## Client Overview",
        f"- **Client**: {name}",
        f"- **Date of Birth**: {dob}",
        f"- **Country**: {country}",
        f"- **Consultation Point**: {ts_label}",
        "",
        "## Active Clinical Profile",
        f"- **Active Conditions**: {', '.join(conditions) if conditions else 'None recorded'}",
        f"- **Current Medications**: {', '.join(medications) if medications else 'None recorded'}",
        f"- **Client-Specific Protocols**: {'; '.join(protocols) if protocols else 'None active'}",
        f"- **Recent Labs & Diagnostics**: {'; '.join(labs) if labs else 'None recorded'}",
    ]

    # specs/v9/03 — the living, bi-temporal lab-marker state
    # (app/vault.py's client_clinical_state), additive to the raw labs
    # line above, never a replacement for it: this is a disposable,
    # rebuildable projection, not the source of truth. Only present once
    # background extraction (app/reasoning/clinical_state.py) has run on
    # at least one lab entry for this client — omitted entirely
    # otherwise, same "don't pad with an empty section" rule every other
    # optional block in this function already follows.
    lab_state = history_data.get("lab_state") or []
    if lab_state:
        lines.append("- **Tracked Lab Marker Trends**:")
        for m in lab_state:
            trend = f", trending {m['trend']}" if m.get("trend") else ""
            flag = f" [{m['flag'].upper()}]" if m.get("flag") not in (None, "in_range", "unknown") else ""
            unit = f" {m['unit']}" if m.get("unit") else ""
            lines.append(f"  - {m['display_label']}: {m.get('value', '')}{unit}{flag}{trend}")

    clinical_notes = []
    if legacy_notes:
        clinical_notes.extend(legacy_notes)
    if intake_notes:
        for n in intake_notes:
            clinical_notes.append(f"{n['theme'].capitalize()}: {n['note']}")
    if questionnaire and questionnaire.get("answers"):
        for q, a in questionnaire["answers"].items():
            clinical_notes.append(f"{q}: {a}")

    if clinical_notes:
        lines.append("- **Clinical Notes & Intake**:")
        for cn in clinical_notes:
            lines.append(f"  - {cn}")
    else:
        lines.append("- **Clinical Notes & Intake**: None recorded")

    lines.append("")
    lines.append("## Prior Consultations & Clinical Trajectory")
    if prior_sessions:
        lines.append(f"Recorded prior consultations up to this point ({len(prior_sessions)} session{'s' if len(prior_sessions) != 1 else ''}):")
        for s in prior_sessions:
            s_date = s["started_at"][:10] if s.get("started_at") else "Date unrecorded"
            s_title = s.get("title") or "Consultation"
            # Deliberately never falls back to s["initial_summary"] here: that
            # field is itself a full opening briefing which, for THAT session,
            # already recursed through all of its own prior sessions. Doing so
            # would re-embed the entire trajectory on every new session and
            # compound without bound (each summary quoting every summary
            # before it). A real "session_summary" entry is already short
            # (written by the Summariser); only it goes through, hard-capped
            # as a second line of defense.
            #
            # Cap raised from 400 to 3000 (found live, 2026-11-25: a
            # multi-session client's prior summaries were being cut to one
            # line, discarding the flagged-markers/hypotheses/action-plan
            # structure SUMMARY_SYSTEM now produces, which is exactly the
            # content a later "big picture" briefing needs) — this feeds an
            # LLM prompt, not a UI field, so token cost is the only real
            # constraint; 3000 covers a full structured summary for
            # several sessions without ballooning the prompt.
            s_summary = s.get("summary") or f"{s.get('turns', 0)} turn(s) recorded"
            if len(s_summary) > 3000:
                s_summary = s_summary[:3000].rstrip() + "…"
            lines.append(f"- **{s_date} — {s_title}**:")
            for summary_line in s_summary.splitlines():
                lines.append(f"  {summary_line}")
    else:
        lines.append("No prior consultation sessions recorded before this consultation point.")

    lines.append("")
    lines.append("## Consultation Focus & Recommendations")
    focal_points = []
    if conditions:
        focal_points.append(f"Review progress and symptom control for active conditions: {', '.join(conditions)}.")
    if medications:
        focal_points.append(f"Evaluate therapeutic adherence, efficacy, and side-effect profile for current medications: {', '.join(medications)}.")
    if protocols:
        focal_points.append(f"Review implementation status, tolerance, and timing of client-specific protocols: {', '.join(protocols)}.")
    if labs:
        focal_points.append("Review recent laboratory results and assess if follow-up diagnostic panels are indicated.")
    if prior_sessions:
        focal_points.append("Assess clinical continuity, follow-up actions, and patient response from prior consultation sessions.")
    if not focal_points:
        focal_points.append("Establish baseline clinical history, current chief concerns, and diagnostic goals for this consultation.")

    for fp in focal_points:
        lines.append(f"- {fp}")

    return "\n".join(lines)


def generate_consult_intake_summary(history_data: dict, consultation_point: str) -> str:
    fallback = format_deterministic_consult_summary(history_data, consultation_point)
    prompt = (
        f"Generate the consultation opening summary for this patient based strictly on their clinical "
        f"data and prior history recorded up to consultation point {consultation_point}:\n\n"
        f"Clinical & History Data:\n{json.dumps(history_data, indent=2, default=str)}\n\n"
        f"Draft summary baseline:\n{fallback}"
    )
    try:
        # Role.CHECKER, not Role.REASONER: this is restating already-known
        # structured record data as prose, not synthesizing a citation-
        # grounded clinical answer under the anti-fabrication rules that
        # actually justify Reasoner's top-tier model (Opus 5 / Qwen3-235B).
        # It's the same "quality-sensitive, low-volume, but not THE answer"
        # shape the Reader/Checker roles are already costed for — and it
        # runs once per new consultation session, every time, so the tier
        # gap compounds fast. See llm_client.py's _ANTHROPIC_MODELS comment.
        text, _usage = get_client(Role.CHECKER).chat_text(
            CONSULT_INTAKE_SYSTEM, prompt, max_tokens=100_000, extra_body=_NO_THINKING
        )
        if text and text.strip():
            return text.strip()
    except Exception as exc:
        logging.getLogger(__name__).warning("Consult intake summary LLM call failed, using fallback: %s", exc)
    return fallback


# --- Consult Draft Editor: clinician note / client report drafting -----------

# Shared by both prompts below rather than stated twice — the same
# anti-fabrication discipline REASONER_SYSTEM already enforces for chat
# answers (never fill a gap from general knowledge, never leave an
# unfilled placeholder), restated for a document that may be relied on
# with only light review, or none at all, before it reaches a medical
# record or a client.
_ANTI_FABRICATION_RULES = (
    "- Never state a specific value — a dose, a date, a measurement, a lab "
    "result — that was not actually given to you below. If a section would "
    "normally include one and none was given, say plainly that it wasn't "
    "specified rather than writing a plausible-sounding placeholder.\n"
    "- Never fill a gap from general clinical knowledge or what's usually true "
    "in medicine. If the consultation and sources below don't cover something, "
    "leave it out rather than reasoning your way to it.\n"
    "- Cite the specific source behind a clinical point inline as [1], [2], "
    "referring only to the numbered sources list given to you — never invent a "
    "number beyond that list's length, and never cite a source for something it "
    "doesn't actually support.\n"
)

CLINICIAN_NOTE_SYSTEM = (
    "You are a practitioner drafting your own clinical note immediately after a "
    "consultation, for your own records and for any colleague who reads it later.\n\n"
    "Structure the note in Markdown with exactly these section headings, in order:\n"
    "## Subjective\n"
    "What the client reported, in their own terms — symptoms, concerns, history "
    "as told to you. State 'None recorded' if nothing was reported.\n\n"
    "## Objective\n"
    "What you observed, measured, or reviewed — lab results, exam findings, "
    "documented history. State 'None recorded' if nothing was reviewed.\n\n"
    "## Assessment\n"
    "What the Subjective and Objective findings mean clinically — your "
    "interpretation, not a repeat of the findings.\n\n"
    "## Plan\n"
    "The concrete actions that follow — treatment, monitoring, follow-up.\n\n"
    "Rules:\n"
    "- Attribute every statement correctly: 'the client reported' for what they "
    "said, 'noted' or the specific measurement for what you observed — never "
    "blur the two.\n"
    f"{_ANTI_FABRICATION_RULES}"
    "- Terse, professional clinical prose. No pleasantries, no restating the "
    "question, no padding.\n"
    "- If an existing draft is given, revise or extend it rather than starting "
    "over, unless told otherwise.\n"
    "- If the practitioner gives a specific instruction, follow it exactly even "
    "where it overrides the general structure above."
)

CLIENT_REPORT_SYSTEM = (
    "You are a practitioner writing directly to your client after a "
    "consultation or after reviewing their test results — they are the reader, "
    "not another practitioner. Model the shape of a real finalized client report: "
    "a short greeting, one synthesizing 'big picture' paragraph up front, then "
    "a sequence of topic sections — one per finding, marker, or theme actually "
    "discussed (e.g. a specific hormone, a lab marker, a symptom cluster) — "
    "each covering what was found, what it means in plain terms, and what "
    "follows from it together, not siloed into separate generic sections.\n\n"
    "Structure in Markdown:\n"
    "A brief opening line or two (a greeting is optional, but start with warmth, "
    "not a clinical header).\n\n"
    "One short paragraph giving the overall picture — the pattern across "
    "everything discussed, before the details. This is the paragraph a client "
    "reads first and remembers most; make it a real synthesis, not a table of "
    "contents.\n\n"
    "Then one '## <Topic>' heading per finding or theme actually covered in this "
    "consultation — name each heading after the actual topic (e.g. '## "
    "Progesterone', '## Sleep and stress', '## Insulin'), never a generic label "
    "like 'Findings' or 'Details'. Under each: what was found, what it means for "
    "the client in plain language, and any specific action or recommendation "
    "tied to that topic, woven together as the practitioner would actually "
    "explain it — not split into separate Finding/Meaning/Action subheadings.\n\n"
    "Close with a short paragraph inviting questions and, if applicable, naming "
    "the agreed next step (a supplement trial, a retest, a follow-up visit).\n\n"
    "Rules:\n"
    "- Second person throughout ('you', 'your') — this is addressed directly to "
    "the client.\n"
    "- Omit anything not meant for the client to read directly: a practitioner's "
    "internal differential reasoning, doubts, hedges, or notes to self. Translate "
    "the clinical significance into guidance for the client — don't simplify the "
    "practitioner's private reasoning into plainer words and include it anyway.\n"
    f"{_ANTI_FABRICATION_RULES}"
    "- Plain language only — explain or omit any term a layperson wouldn't "
    "know (e.g. 'metabolites' needs a plain gloss, not a bare clinical term).\n"
    "- Only write a topic section for something actually discussed or found in "
    "this consultation — never pad with a generic section nobody raised.\n"
    "- If an existing draft is given, revise or extend it rather than starting "
    "over, unless told otherwise.\n"
    "- If the practitioner gives a specific instruction, follow it exactly even "
    "where it overrides the general structure above."
)

_DOCUMENT_SYSTEM = {
    "clinician_note": CLINICIAN_NOTE_SYSTEM,
    "client_report": CLIENT_REPORT_SYSTEM,
}

# Same bracket-group shape renderAnswerHtml (web/src/lib/markdown.ts)
# turns into clickable citation buttons.
_CITE_GROUP = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


def _remap_citations(text: str, label_map: dict[str, str]) -> str:
    """Rewrites a turn's own [1]-style markers to the flattened, globally
    renumbered labels _flatten_and_remap() below assigns — the claim-to-
    source link survives flattening instead of being stripped, so the
    drafting model sees exactly which source backed which sentence,
    rather than having to re-guess it from a plain source list."""
    def repl(m: re.Match) -> str:
        parts = []
        for raw in m.group(1).split(","):
            raw = raw.strip()
            if not raw.isdigit():
                continue
            new_label = label_map.get(raw)
            if new_label:
                parts.append(new_label)
        return f"[{', '.join(parts)}]" if parts else ""
    return _CITE_GROUP.sub(repl, text)


def _flatten_and_remap(turns: list[dict]) -> tuple[list[dict], list[str]]:
    """One deduplicated, globally-renumbered source list across every
    turn given, plus each turn's own answer text with its citation
    markers rewritten to match — avoids both the per-turn K1/K2 labels
    colliding across turns that each had their own independent
    numbering, and losing the original claim-to-source attribution that
    simply deleting those markers would."""
    flat: list[dict] = []
    key_to_label: dict[tuple, str] = {}
    remapped_answers: list[str] = []
    for t in turns:
        label_map: dict[str, str] = {}
        for s in t.get("sources") or []:
            key = (s.get("document_id"), s.get("locator"), s.get("title"))
            new_label = key_to_label.get(key)
            if new_label is None:
                new_label = str(len(flat) + 1)
                key_to_label[key] = new_label
                flat.append(s)
            if s.get("label"):
                label_map[s["label"]] = new_label
        remapped_answers.append(_remap_citations(t.get("answer", ""), label_map))
    return flat, remapped_answers


def generate_session_document(
    kind: str, turns: list[dict], prior_document: str | None = None,
    instruction: str | None = None, pattern_context: str | None = None,
    patient_context_text: str | None = None, patient_history_text: str | None = None,
) -> tuple[str, dict, list[dict]]:
    """Drafts a clinician_note or client_report. No deterministic fallback,
    unlike generate_consult_intake_summary above — there's no sane non-LLM
    substitute for freeform drafting, so (like summarize_session) this lets
    openai.APIError propagate to the caller's route rather than swallowing
    it.

    `patient_context_text` (patient.as_query_text()) and
    `patient_history_text` (format_deterministic_consult_summary's output
    over vault.get_patient_history_up_to — every lab/condition/prior-
    session on file, uncapped, chronological) were found live, 2026-11-25,
    to be completely missing from this function: a practitioner asking the
    drafter to "go through all blood panels and generate a comparative
    table" got back "no clinical interpretation is possible" because
    `turns` alone (this session's own chat Q&A, often empty — drafting is
    frequently the first thing a practitioner does in a session) was the
    *only* clinical content this function ever saw. Both are optional
    (every existing caller/test keeps working unchanged) but the route
    should always supply them now — see app/main.py's me_draft_document.

    Returns (markdown_text, usage, sources) — `sources` is the flattened,
    renumbered list the [1]/[2] markers in `markdown_text` refer to, in
    the same shape as a chat turn's own `sources` (label/title/locator/
    document_id/snippet), so the caller can build the same citation-title
    map web/src/lib/markdown.ts's renderAnswerHtml() already uses for chat.
    """
    sources, remapped_answers = _flatten_and_remap(turns)
    source_block = "\n\n".join(
        f"[{i + 1}] {s.get('title', 'unknown')} — {s.get('snippet', '')}"
        for i, s in enumerate(sources)
    ) or "(no sources were cited in this consultation yet)"
    convo_block = "\n\n".join(
        f"Q: {t.get('question', '')}\nA: {a}"
        for t, a in zip(turns, remapped_answers)
    ) or "(no turns recorded in this consultation yet)"
    prior_block = (
        f"\n\nExisting draft to revise or extend:\n{prior_document}" if prior_document else ""
    )
    instruction_block = (
        f"\n\nSpecific instruction from the practitioner: {instruction}" if instruction else ""
    )
    # De-identified, pooled across every practitioner (app/clinical_
    # patterns.py) — background context for phrasing/approach only, never
    # a source of fact about THIS client, so it's kept clearly separate
    # from the consultation/sources blocks above rather than merged in.
    pattern_block = f"\n\n{pattern_context}" if pattern_context else ""
    patient_block = f"\n\nClient context:\n{patient_context_text}" if patient_context_text else ""
    # Comes last and is labeled for exactly what it's for — a request that
    # spans more than this one session (trends, a comparative table across
    # dated panels, "what's still open") has to be answered from this, not
    # from convo_block above, which only ever covers THIS session's chat.
    history_block = (
        f"\n\nFull patient clinical history on file (every lab, condition, "
        f"and prior session recorded for this client — use this for any "
        f"request spanning multiple sessions or asking about trends across "
        f"dated panels):\n{patient_history_text}"
        if patient_history_text else ""
    )
    prompt = (
        f"Consultation so far:\n{convo_block}\n\n"
        f"Numbered sources behind that consultation:\n{source_block}"
        f"{prior_block}{instruction_block}{pattern_block}{patient_block}{history_block}"
    )
    text, usage = get_client(Role.REASONER).chat_text(
        _DOCUMENT_SYSTEM[kind], prompt, max_tokens=100_000, extra_body=_NO_THINKING)
    return text, usage, sources
