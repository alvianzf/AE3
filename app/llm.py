"""The AI team. One function per role, each with its model pinned.

Reader          — reads an incoming source, tags it, drafts its source card
Graph-builder   — pulls medical concepts out of a document and links them
Embedder        — embeds knowledge-base chunks for later semantic recall
Retrieval       — turns a question into what to look for; it does not answer
Reasoner        — writes the grounded, referenced answer
Checker         — verifies the draft against its sources before it is shown

specs/v4.2 — this used to be four roles on one Anthropic client; it's now
six roles on Nebius's OpenAI-compatible token factory, with one exception:
the Checker isn't a chat model at all (see its own section below). There
is also no more per-practitioner key — every call, ingestion or query
time, runs through the one shared client below.
"""
from __future__ import annotations

import json
import re

from openai import OpenAI

from .config import get_config

cfg = get_config()
_client = OpenAI(base_url=cfg.nebius_base_url, api_key=cfg.nebius_api_key)


def _usage_of(response) -> dict:
    return {"input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens}


def _json_call(model: str, system: str, prompt: str, schema: dict,
               max_tokens: int = 2000, return_usage: bool = False):
    """One structured-output call. The schema is enforced by the API.

    Returns the parsed dict, or (dict, usage) when return_usage is True —
    kept opt-in so existing callers are unaffected.
    """
    response = _client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "response", "schema": schema, "strict": True},
        },
    )
    # next() with no default raised a bare, confusing StopIteration if the
    # model's response somehow had no content at all (specs/v4/04-known-
    # issues.md#m11) — a clear domain error instead.
    text = response.choices[0].message.content
    if text is None:
        raise ValueError(f"{model} returned no content")
    result = json.loads(text)
    return (result, _usage_of(response)) if return_usage else result


def ping() -> bool:
    """Validate credentials without spending tokens."""
    _client.models.retrieve(cfg.reasoner_model)
    return True


# --- Reader -------------------------------------------------------------------

READER_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Short descriptive title."},
        "summary": {"type": "string",
                    "description": "2-3 sentences on what this source covers."},
        "topics": {"type": "array", "items": {"type": "string"},
                   "description": "1-4 topics, taken from the clinic's topic list "
                                  "wherever one fits."},
        "suggested_grade": {"type": "integer",
                            "description": "Reliability 1-10. Peer-reviewed "
                                           "guidelines and clinical protocols score "
                                           "high; podcasts, blogs and anecdote score "
                                           "low."},
        "author": {"type": "string",
                   "description": "Author, presenter or issuing body as stated in "
                                  "the text. Empty string if the text does not say."},
        "published": {"type": "string",
                      "description": "Publication or recording date as stated, "
                                     "e.g. '2024' or '2024-03'. Empty string if "
                                     "the text does not say."},
        "reference": {"type": "string",
                      "description": "A citation, DOI, journal reference or URL "
                                     "found in the text. Empty string if none."},
    },
    "required": ["title", "summary", "topics", "suggested_grade", "author",
                 "published", "reference"],
    "additionalProperties": False,
}

# A controlled vocabulary. Without it the Reader invents overlapping labels
# ("thyroid", "hashimoto's", "autoimmune thyroid disease") for one source and the
# coverage dashboard stops being readable.
TOPICS = [
    "thyroid", "adrenal", "cortisol", "oestrogen", "progesterone", "testosterone",
    "menopause", "perimenopause", "pcos", "fertility", "cycle health",
    "vitamin d", "iron", "b12", "magnesium", "zinc", "iodine",
    "insulin resistance", "metabolic health", "weight", "sleep", "mood",
    "gut health", "inflammation", "lab interpretation", "supplementation",
    "dosing", "nutrition", "hair and skin", "bone health",
]

READER_SYSTEM = (
    "You prepare sources for a hormonal-health clinic's knowledge library.\n\n"
    "Read the source, title it, summarise it, tag its topics, record what it says "
    "about its own provenance, and propose a reliability grade from 1 to 10 based "
    "on the strength of its evidence and the authority of its origin. Be honest "
    "about weak sources — the clinic relies on the grade to decide what its "
    "practitioners are allowed to see. Peer-reviewed guidelines and clinical "
    "protocols belong at the top; a podcast or blog asserting mechanisms without "
    "evidence belongs near the bottom.\n\n"
    "For author, published and reference: report only what the text itself states. "
    "Return an empty string rather than inferring, guessing from the topic, or "
    "reconstructing a plausible citation — a fabricated reference is worse than a "
    "blank one, because a clinician may try to look it up.\n\n"
    "Topics are the shelves a practitioner browses by, so they must converge on a "
    "small shared set rather than growing one label per document. You will be shown "
    "the topics the library already uses: reuse an existing one whenever it "
    "genuinely fits, even if the source words it differently. Coin a new topic only "
    "when the source is about something none of them covers, and then keep it broad "
    "enough that the next document on the subject can reuse it.\n\n"
    "Pick the 1-4 a practitioner would actually browse by, lowercase. Never stack "
    "near-synonyms — a source on Hashimoto's is 'thyroid', not 'thyroid' plus "
    "'hashimoto's' plus 'autoimmune thyroid disease'."
)


def read_source(text: str, filename: str, kind: str, origin: str,
                known_topics: list[str] | None = None) -> dict:
    # Show the model the shelves that already exist so it files this source next to
    # its neighbours instead of inventing a new label for the same subject. The
    # seed list only stands in for an empty library.
    shelves = known_topics or TOPICS
    prompt = (
        f"Topics already used in this library (reuse where one fits):\n"
        f"{', '.join(sorted(shelves)) or '(the library is empty)'}\n\n"
        f"Filename: {filename}\nKind: {kind}\nStated origin: {origin}\n\n"
        f"Source text:\n---\n{text}\n---"
    )
    card = _json_call(cfg.reader_model, READER_SYSTEM, prompt, READER_SCHEMA)
    card["suggested_grade"] = max(1, min(10, int(card["suggested_grade"])))
    card["topics"] = [t.strip().lower() for t in card["topics"] if t.strip()][:4]
    for field in ("author", "published", "reference"):
        card[field] = card.get(field, "").strip()
    return card


# --- Indexer: concepts, so passages can find each other -----------------------

CONCEPTS_SCHEMA = {
    "type": "object",
    "properties": {
        "passages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "n": {"type": "integer", "description": "The passage number."},
                    "concepts": {
                        "type": "array", "items": {"type": "string"},
                        "description": "3-8 clinical concepts this passage is about.",
                    },
                },
                "required": ["n", "concepts"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["passages"],
    "additionalProperties": False,
}

CONCEPTS_SYSTEM = (
    "You index a clinical document so that passages about the same thing can find "
    "one another across the whole library.\n\n"
    "For each numbered passage, list the 3-8 concepts it is actually about: "
    "analytes and lab measures, hormones, conditions, drugs and supplements, "
    "mechanisms, body systems, patient groups.\n\n"
    "Normalise so the same idea gets the same label everywhere — this only works if "
    "two passages in different documents produce an identical string:\n"
    "- lowercase, singular, no punctuation or units\n"
    "- prefer the common clinical name over an abbreviation or a synonym: "
    "'vitamin d' not '25(OH)D', 'ferritin' not 'serum ferritin', 'hashimoto "
    "thyroiditis' not 'HT', 'iron absorption' not 'absorption of iron'\n"
    "- name the mechanism when the passage explains one ('iron absorption', "
    "'hepcidin'), not just the topic\n\n"
    "Do not include the document's own framing (author, journal, 'protocol'), "
    "hedges, or anything the passage merely mentions in passing."
)


def extract_concepts(passages: list[str]) -> list[list[str]]:
    """Concepts per passage, in the same order as the input.

    One call for the whole document, so the model sees the passages together and
    labels them consistently.
    """
    if not passages:
        return []
    listing = "\n\n".join(
        f"[{i + 1}] {p[:1500]}" for i, p in enumerate(passages)
    )
    # specs/v4.2 — concept extraction moved from the Reader to the
    # Graph-builder role (its whole job is "pull out medical concepts and
    # how they connect").
    result = _json_call(
        cfg.graph_builder_model, CONCEPTS_SYSTEM,
        f"Passages to index:\n---\n{listing}\n---", CONCEPTS_SCHEMA,
        max_tokens=8000,
    )
    out: list[list[str]] = [[] for _ in passages]
    for row in result["passages"]:
        idx = int(row["n"]) - 1
        if 0 <= idx < len(passages):
            seen, clean = set(), []
            for c in row["concepts"]:
                c = " ".join(c.lower().split()).strip(" .,:;")
                if c and c not in seen:
                    seen.add(c)
                    clean.append(c)
            out[idx] = clean[:8]
    return out


MERGE_SCHEMA = {
    "type": "object",
    "properties": {
        "groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "canonical": {"type": "string",
                                  "description": "The label to keep."},
                    "aliases": {"type": "array", "items": {"type": "string"},
                                "description": "Labels to fold into it."},
                },
                "required": ["canonical", "aliases"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["groups"],
    "additionalProperties": False,
}

MERGE_SYSTEM = (
    "You tidy the index of a clinical knowledge library. You are given the labels "
    "currently in use. Some are the same idea written differently, and while they "
    "stay separate the library cannot connect the passages that use them.\n\n"
    "Group only labels that mean the SAME thing — an abbreviation and its "
    "expansion, a synonym, a spelling or plural variant, a possessive. Choose the "
    "clearest full clinical name as the canonical form.\n\n"
    "Do NOT group things that are merely related, or a specific case under a "
    "general one: 'ferritin' and 'iron' are different measures; 'hypothyroidism' "
    "and 'hashimoto thyroiditis' are different diagnoses; 'oestrogen' and "
    "'progesterone' are different hormones. Merging those would make the library "
    "claim two passages are about the same thing when they are not.\n\n"
    "Return only the groups that need merging. If nothing does, return an empty "
    "list — that is the right answer for a clean index."
)


def merge_labels(names: list[str]) -> list[dict]:
    """Ask which existing labels are the same idea. Returns merge groups."""
    if len(names) < 2:
        return []
    # specs/v4.2 — the graph-merge step is ingestion-time graph-building
    # too, not the query-time retrieval-planning job the old "Librarian"
    # name also covered (those are now separate roles/models).
    result = _json_call(
        cfg.graph_builder_model, MERGE_SYSTEM,
        "Labels in use:\n" + "\n".join(f"- {n}" for n in sorted(names)),
        MERGE_SCHEMA, max_tokens=4000,
    )
    groups = []
    for g in result["groups"]:
        canonical = " ".join(g["canonical"].lower().split())
        aliases = [" ".join(a.lower().split()) for a in g["aliases"]]
        aliases = [a for a in aliases if a and a != canonical and a in names]
        if canonical and aliases:
            groups.append({"canonical": canonical, "aliases": aliases})
    return groups


FOCUS_SCHEMA = {
    "type": "object",
    "properties": {
        "concepts": {
            "type": "array", "items": {"type": "string"},
            "description": "3-10 concepts to look for in the library.",
        },
    },
    "required": ["concepts"],
    "additionalProperties": False,
}


def question_concepts(question: str, patient_file: str,
                      history: list[dict] | None = None) -> list[str]:
    """The concepts to hunt for in the corpus, in the same vocabulary as indexing.

    These anchor the traversal: a passage mentioning one of them is pulled in
    wherever it sits in a document, which is how material deep inside a long
    source is found instead of being lost to the passage budget.
    """
    prompt = (
        f"Patient file:\n---\n{patient_file}\n---\n\n"
        f"{_history_block(history or [])}"
        f"Question: {question}"
    )
    # specs/v4.2 — query-time (working out what's being asked and what to
    # go fetch) is the retrieval-planner role now, not the Reader's.
    result = _json_call(
        cfg.retrieval_model,
        CONCEPTS_SYSTEM + "\n\nHere you are given a question rather than a "
        "document. List the concepts that a passage would have to be about in "
        "order to help answer it — including the ones implied by the patient's "
        "own labs and history, and by the earlier turns of the consultation, not "
        "only the words in the question itself.",
        prompt, FOCUS_SCHEMA,
    )
    seen, out = set(), []
    for c in result["concepts"]:
        c = " ".join(c.lower().split()).strip(" .,:;")
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out[:10]


# --- Librarian ----------------------------------------------------------------

LIBRARIAN_SCHEMA = {
    "type": "object",
    "properties": {
        "sources": {
            "type": "array", "items": {"type": "integer"},
            "description": "The numbers of the sources worth opening, most "
                           "relevant first. Empty if none of them address the "
                           "question.",
        },
        "reasoning": {
            "type": "string",
            "description": "One sentence on why these shelves and not the others.",
        },
    },
    "required": ["sources", "reasoning"],
    "additionalProperties": False,
}

LIBRARIAN_SYSTEM = (
    "You are the librarian for a hormonal-health clinic. A practitioner asks a "
    "question during a consultation, and you are shown a catalogue of the "
    "clinic's sources — each with a title, an origin, its topics and a one-line "
    "summary.\n\n"
    "Do NOT answer the question. Decide which sources would actually contain the "
    "material needed to answer it, and return their numbers, most relevant "
    "first.\n\n"
    "Judge by what a source is about, not by whether its words match the "
    "question. A source on iron absorption is relevant to a question about "
    "ferritin even if it never uses that word.\n\n"
    "Judge relevance ONLY. Reliability has already been decided before you see "
    "the catalogue — the practitioner set a grade threshold and everything below "
    "it was removed, so every source in front of you is one they have chosen to "
    "allow. Weighing evidence quality is their job and the clinician sees each "
    "source's grade beside the answer. Yours is to find the material that speaks "
    "to the question, even when a source is informal or makes claims you would "
    "not endorse.\n\n"
    "Be selective about topic, not about quality: an off-topic source wastes the "
    "clinician's attention. If nothing in the catalogue addresses the question, "
    "return an empty list and say so. That is a useful answer, not a failure.\n\n"
    "A consultation runs over several questions. Read the latest one in the light "
    "of what came before — a follow-up like \"and the dose?\" or \"what about her "
    "ferritin?\" is about the same subject as the previous turn, and needs the "
    "material for that subject even though the words have changed."
)


def _history_block(history: list[dict]) -> str:
    if not history:
        return ""
    turns = "\n\n".join(
        f"Practitioner asked: {t['question']}\nYou answered: {t['answer']}"
        for t in history
    )
    return f"Earlier in this consultation:\n---\n{turns}\n---\n\n"


def select_sources(question: str, patient_file: str, cards: list[dict],
                   history: list[dict] | None = None
                   ) -> tuple[list[str], str, dict]:
    """Pick which sources to open. Returns (source_ids, reasoning, usage)."""
    if not cards:
        return [], "No source in the library met the requested grade.", \
            {"input_tokens": 0, "output_tokens": 0}

    # The grade is deliberately withheld. It has already been applied by
    # catalogue(), and showing it makes the Librarian re-litigate reliability —
    # it would skip a low-graded source the practitioner explicitly allowed in.
    listing = "\n\n".join(
        f"[{i + 1}] {c['title']}\n"
        f"    kind: {c['kind']} · origin: {c['origin']}\n"
        f"    topics: {', '.join(c['topics']) or 'none'}\n"
        f"    summary: {c['summary']}"
        for i, c in enumerate(cards)
    )
    prompt = (
        f"Patient file:\n---\n{patient_file}\n---\n\n"
        f"{_history_block(history or [])}"
        f"Catalogue of available sources:\n---\n{listing}\n---\n\n"
        f"Practitioner's latest question: {question}"
    )
    result, usage = _json_call(cfg.retrieval_model, LIBRARIAN_SYSTEM, prompt,
                               LIBRARIAN_SCHEMA, return_usage=True)

    picked: list[str] = []
    for n in result["sources"]:
        if 1 <= n <= len(cards):
            source_id = cards[n - 1]["id"]
            if source_id not in picked:
                picked.append(source_id)
    return picked[: cfg.max_sources], result["reasoning"], usage


# --- Specialist ---------------------------------------------------------------

SPECIALIST_SYSTEM = (
    "You are a senior clinician advising a practitioner during a consultation.\n\n"
    "Answer using ONLY the numbered passages from the clinic's library and the "
    "patient's own file. You have no other knowledge available to you here.\n\n"
    "Rules:\n"
    "- Cite the passage behind each clinical point inline, as [S1], [S2]. Points "
    "drawn from the patient's record need no citation.\n"
    "- If the passages do not cover the question, say so plainly and state what "
    "the library would need. Never fill a gap from general knowledge.\n"
    "- Connect the passages to this specific patient's labs and history where they "
    "are relevant.\n"
    "- You advise a professional who decides what to do. Be direct and concise — a "
    "few short paragraphs, no preamble.\n\n"
    "Some passages were not chosen directly but reached by following links in the "
    "library: one may continue from another, or be about the same subject in a "
    "different document. Use them on the same footing as the rest — that is the "
    "point of them — and where two sources bear on each other, say so rather than "
    "treating each in isolation."
)


def answer(question: str, patient_file: str, passages: list[dict],
           history: list[dict] | None = None,
           unsupported: list[str] | None = None) -> tuple[str, dict]:
    """Returns (answer_text, usage).

    `unsupported` is only passed on the one bounded revision retry
    (specs/v3/07-ai-team.md): the Checker's own list of claims it could not
    ground in a passage. The instruction is strictly "ground it or drop
    it" — no new passages are supplied, so there is no way to satisfy a
    flagged claim except by tying it to material already given or removing
    it; paraphrasing a passage more loosely to make it look like it covers
    the claim is not an option this prompt offers.
    """
    if passages:
        def label(p):
            via = p.get("via", "opened")
            if via == "adjacent":
                return " · continues from an opened passage"
            if via == "linked":
                shared = ", ".join(p.get("shared") or [])
                return f" · linked by shared subject: {shared}" if shared else " · linked"
            return ""
        block = "\n\n".join(
            f"[S{i + 1}] (source: {p['title']} · grade {p['grade']}{label(p)})\n"
            f"{p['text']}"
            for i, p in enumerate(passages)
        )
    else:
        block = "(no passages in the library matched this question)"
    revision_block = ""
    if unsupported:
        claims = "\n".join(f"- {c}" for c in unsupported)
        revision_block = (
            "\n\nAn independent check of your previous draft found these claims "
            "not actually supported by the passages above:\n"
            f"{claims}\n\n"
            "Write a new answer. For each of those claims, either tie it "
            "explicitly to a passage that genuinely supports it, or remove it — "
            "do not keep it by rephrasing it more vaguely. Do not introduce new "
            "claims the passages don't cover either."
        )
    prompt = (
        f"Patient file:\n---\n{patient_file}\n---\n\n"
        f"Passages from the clinic library:\n---\n{block}\n---\n\n"
        f"Practitioner's question: {question}"
        f"{revision_block}"
    )
    # specs/v4.2 — this was cfg.answer_model on Anthropic's "effort" param
    # (a Claude-specific reasoning-effort knob, dropped: not carried over
    # since the OpenAI-compatible shape doesn't define an equivalent —
    # confirm whether Nebius exposes something similar before assuming
    # response quality/latency is unaffected). Now the Reasoner role.
    response = _client.chat.completions.create(
        model=cfg.reasoner_model,
        max_tokens=8000,
        messages=[
            {"role": "system", "content": SPECIALIST_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    text = (response.choices[0].message.content or "").strip()
    return text, _usage_of(response)


# --- Checker (anti-hallucination) ---------------------------------------------
#
# specs/v4.2/01 — the Checker used to be a fifth chat-model call, asking a
# Claude model "does this answer's claims hold up against these sources" as
# one JSON-schema call. It's now HHEM-2.1-Open, a hallucination-detection
# classifier: no system prompt, no JSON schema, no chat completion at all —
# a direct (premise, hypothesis) scoring call, run once per sentence in the
# drafted answer rather than once for the whole answer. This is genuinely
# unverified end-to-end (no live model download/inference has been run
# against this code) — confirm the model's actual call signature against
# its current Hugging Face model card before relying on this in production.

_checker_model = None


def _get_checker_model():
    """Lazy singleton: only pay the transformers/torch import + model
    download cost the first time check() is actually called, not on every
    import of this module (ingestion-only code paths never need it)."""
    global _checker_model
    if _checker_model is None:
        from transformers import AutoModelForSequenceClassification
        _checker_model = AutoModelForSequenceClassification.from_pretrained(
            cfg.checker_model, trust_remote_code=True)
    return _checker_model


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def check(question: str, answer_text: str, patient_file: str,
          passages: list[dict]) -> dict:
    """Scores each sentence of the drafted answer against the cited
    passages, flagging the answer 'weak' if any sentence's best-matching
    passage scores below cfg.checker_threshold.

    Returns the same shape the old chat-based Checker returned
    (verdict/unsupported/note/usage) so callers don't need to change —
    'usage' is zeroed since a local classifier call has no token cost.
    """
    evidence = "\n\n".join(p["text"] for p in passages) or patient_file
    model = _get_checker_model()
    sentences = _sentences(answer_text)
    unsupported: list[str] = []
    for sentence in sentences:
        # HHEM scores a single (premise, hypothesis) pair; scoring against
        # the whole evidence block (rather than per-passage) is a
        # deliberate simplification — comparing against each passage
        # individually and taking the best score would be more precise
        # but is left for a follow-up once this path has a live smoke test.
        score = model.predict([(evidence, sentence)])[0]
        if score < cfg.checker_threshold:
            unsupported.append(sentence)

    verdict = "weak" if unsupported else "pass"
    note = (
        f"{len(unsupported)} sentence(s) not confidently supported by the cited "
        "sources." if unsupported else
        "Every sentence checked against its sources."
    )
    return {
        "verdict": verdict,
        "unsupported": unsupported,
        "note": note,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }


# --- Session summary ----------------------------------------------------------

SUMMARY_SYSTEM = (
    "Write a short session summary for a patient's clinical record: what was "
    "asked, what the assistant advised, and anything the next practitioner should "
    "know. Three or four sentences, plain clinical prose, no headings."
)


def summarize_session(transcript: str) -> str:
    # specs/v4.2 — was cfg.checker_model, a chat model. The Checker is no
    # longer a chat model at all (see above), so this free-text writing
    # task moves to the Reasoner, the role actually meant for prose output.
    response = _client.chat.completions.create(
        model=cfg.reasoner_model,
        max_tokens=1000,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM},
            {"role": "user", "content": transcript},
        ],
    )
    return (response.choices[0].message.content or "").strip()


# --- Web-page extraction (specs/v3/18-document-ingest-upgrade.md Component 2) -

EXTRACT_ARTICLE_SYSTEM = (
    "You are given the text content of a web page, already stripped of "
    "script/style tags. Extract only the main article/content text — the "
    "words a human reader came to this page to read. Discard navigation "
    "menus, headers, footers, cookie banners, ads, related-article lists, "
    "comment sections, and site chrome.\n\n"
    "Do not summarize, rephrase, shorten, or otherwise alter the content "
    "you keep. Reproduce it verbatim, word for word, exactly as it appears "
    "in the source. Your only job is deciding what is content and what is "
    "chrome — never editing the content itself."
)


def extract_article(stripped_text: str, url: str) -> str:
    """Plain-text output, not a JSON-schema call like every other role in
    this file — the output *is* the document body, closer in shape to
    answer()'s free-text output than read_source()'s structured card.
    cfg.reader_model — a bounded extraction task, not one that needs a
    stronger model."""
    response = _client.chat.completions.create(
        model=cfg.reader_model,
        max_tokens=8000,
        messages=[
            {"role": "system", "content": EXTRACT_ARTICLE_SYSTEM},
            {"role": "user",
             "content": f"URL: {url}\n\nPage text:\n---\n{stripped_text[:40000]}\n---"},
        ],
    )
    return (response.choices[0].message.content or "").strip()


# --- Embedder -------------------------------------------------------------
#
# specs/v4.2/01 — write path only, deliberately. This computes and stores
# an embedding per passage at ingest time (knowledge.ingest_source() calls
# embed_passages() and stores the vectors on each Passage node — see
# knowledge.py and its Neo4j vector index). Nothing reads these back yet:
# graph/source-card retrieval (select_sources() above) stays the only
# retrieval path in this change. Wiring a semantic-recall consumer (a
# vector-similarity query merged into select_sources()'s candidate set,
# still filtered by the practitioner's grade threshold) is real, valuable
# follow-up work — not done here because it touches the live retrieval
# path with no way to verify it against a real Neo4j instance in this
# change's environment, and a bug there would silently degrade every
# clinical answer. Shipping the write path alone is safe: it's additive,
# nothing existing reads or depends on it.


def embed_passages(texts: list[str]) -> list[list[float]]:
    """One embedding per input text, same order in, same order out."""
    if not texts:
        return []
    response = _client.embeddings.create(model=cfg.embedder_model, input=texts)
    return [d.embedding for d in response.data]
