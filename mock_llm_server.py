#!/usr/bin/env python3
"""DEMO-ONLY mock of the OpenAI-compatible model endpoints the Clinic backend
calls (Reader, Graph-builder, Embedder, Answer Engine, Reasoner, Checker LLM).

Purpose: let the whole app run locally (ingest, graph build, retrieval,
consult, checker) with no external model provider, e.g. to capture
screenshots for the user manual. The output is rule-based and extractive:
it derives titles, entities, judgments and answers from the text it is given
and never adds outside medical knowledge. NOT for production or for real
clinical use.

Standard library only. Start:  python3 mock_llm_server.py  (port 8765)
Use via the per-role overrides in app/config.py, e.g.
  READER_BASE_URL=http://127.0.0.1:8765/v1   (see start-local.sh --mock-llm)
"""
import hashlib
import json
import math
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.environ.get("MOCK_LLM_PORT", "8765"))
ROOT = Path(__file__).resolve().parent

_ENV_KEYS = ("READER_MODEL", "GRAPH_BUILDER_MODEL", "EMBEDDER_MODEL",
             "RETRIEVAL_MODEL", "REASONER_MODEL", "CHECKER_LLM_MODEL",
             "EMBEDDING_DIMENSIONS")


def _env(name: str, default: str = "") -> str:
    """Read one non-secret setting: process env first, then .env."""
    if os.environ.get(name):
        return os.environ[name]
    try:
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return default


DIMS = int(_env("EMBEDDING_DIMENSIONS", "4096"))
MODELS = sorted({m for m in (_env(k) for k in _ENV_KEYS[:-1]) if m} |
                {"mock-model"})

STOP = set("""a an and are as at be but by can do does for from has have how i in
is it its of on or our should so than that the their them then there these they
this to was we were what when which who will with would you your any all also
into not more most other some such only about after before over under again""".split())


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower())
            if len(t) > 2 and t not in STOP]


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


# --- embeddings --------------------------------------------------------------
def embed(text: str) -> list[float]:
    vec = [0.0] * DIMS
    for tok in tokens(text):
        for feat, w in ((tok, 1.0), (tok[:5], 0.6)):
            h = int(hashlib.md5(feat.encode()).hexdigest(), 16)
            vec[h % DIMS] += w if (h >> 64) & 1 else -w
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 6) for v in vec]


# --- Reader ------------------------------------------------------------------
TOPIC_RULES = [
    (r"sleep|insomnia|circadian|caffeine", "sleep"),
    (r"gut|digest|microbio|bowel", "gut health"),
    (r"glucose|insulin|metabolic|diabet", "metabolic health"),
    (r"iron|ferritin|vitamin|magnesium|supplement|nutrient", "nutrition and supplements"),
    (r"stress|cortisol|anxiety", "stress"),
    (r"exercise|training|activity", "exercise"),
]


def reader(prompt: str) -> dict:
    m = re.search(r"reuse where one fits\):\n(.*?)\n\nFilename:", prompt, re.S)
    known = [t.strip() for t in (m.group(1).split(",") if m else []) if t.strip()
             and not t.startswith("(")]
    m = re.search(r"Source text:\n---\n(.*?)\n---\s*$", prompt, re.S)
    text = (m.group(1) if m else prompt).strip()
    sents = sentences(text) or [text]
    first = sents[0].rstrip(".")
    if ":" in first and len(first.split(":", 1)[0].split()) <= 4:
        first = first.split(":", 1)[1].strip()
    title = (first[:1].upper() + first[1:])[:90] or "Untitled source"
    body = " ".join(sents[1:3]) or sents[0]
    summary = f"Covers {title.lower()}. {body}"[:420]
    counts = []
    for pat, topic in TOPIC_RULES:
        n = len(re.findall(pat, text, re.I))
        if n:
            counts.append((n, next((k for k in known if k.lower() == topic), topic)))
    counts.sort(key=lambda x: -x[0])
    topics = [t for i, (n, t) in enumerate(counts[:2]) if i == 0 or n >= 2] or ["general"]
    weak = re.search(r"\b(blog|podcast|anecdot|forum|opinion)\b", text, re.I)
    return {"title": title, "summary": summary, "topics": topics,
            "suggested_grade": 3 if weak else 8,
            "author": "", "published": "", "reference": ""}


# --- Graph builder -----------------------------------------------------------
ENTITY_RULES = [
    (r"caffeine", "Caffeine", "Substance"),
    (r"screen", "Screen use", "Behavior"),
    (r"consistent sleep|wake time|sleep schedule", "Consistent sleep schedule", "Behavior"),
    (r"bedroom|cool, dark", "Sleep environment", "Environment"),
    (r"light", "Evening light exposure", "Behavior"),
    (r"glucose", "Fasting glucose", "LabFinding"),
    (r"insulin", "Insulin", "LabFinding"),
    (r"ferritin|iron", "Iron stores", "LabFinding"),
    (r"magnesium", "Magnesium", "Supplement"),
    (r"vitamin d", "Vitamin D", "Supplement"),
    (r"stress|cortisol", "Stress", "Condition"),
    (r"gut|microbio", "Gut health", "Condition"),
]


def kg_builder(prompt: str) -> dict:
    m = re.search(r"Passage:\n---\n(.*?)\n---\s*$", prompt, re.S)
    text = m.group(1) if m else prompt
    ents = [(n, t) for pat, n, t in ENTITY_RULES if re.search(pat, text, re.I)]
    has_sleep = re.search(r"sleep|insomnia", text, re.I)
    if has_sleep:
        ents.append(("Sleep quality", "Condition"))
    if not ents:
        top = [w for w, _ in sorted(
            ((w, tokens(text).count(w)) for w in set(tokens(text))),
            key=lambda x: -x[1])[:3]]
        ents = [(w.capitalize(), "Concept") for w in top]
    seen, entities = set(), []
    for n, t in ents:
        if n not in seen:
            seen.add(n)
            entities.append({"name": n, "type": t})
    rels = []
    hub = "Sleep quality" if has_sleep else None
    verbs = {"Caffeine": "AFFECTS", "Screen use": "AFFECTS", "Evening light exposure": "AFFECTS"}
    if hub:
        for e in entities:
            if e["name"] != hub and e["type"] in ("Substance", "Behavior", "Environment"):
                rels.append({"head": e["name"], "rel_type": verbs.get(e["name"], "SUPPORTS"),
                             "tail": hub})
    return {"entities": entities, "relationships": rels}


# --- Answer Engine -----------------------------------------------------------
def search_query(prompt: str) -> dict:
    q = re.search(r"Question:\s*(.*)", prompt)
    question = q.group(1).strip() if q else prompt[-200:]
    extra = []
    for label in ("Active conditions", "Current medications"):
        m = re.search(label + r":\s*(.*)", prompt)
        if m and "none recorded" not in m.group(1):
            extra.append(m.group(1).strip())
    return {"search_query": " ".join([question, *extra]).strip()}


def judge(prompt: str) -> dict:
    part = prompt.split("New candidates to judge:", 1)[-1]
    ids = re.findall(r"^(\S+): \[", part, re.M)
    return {"judgments": [{"id": i, "relevant": True} for i in ids]}


# --- Checker LLM -------------------------------------------------------------
ACTION = re.compile(r"\b(confirm|ask|check|review|verify|log|schedule|follow|discuss|record)\b", re.I)


def checker(prompt: str) -> dict:
    ev = {int(i): t for i, t in re.findall(r"^\[E(\d+)\] (.*)$", prompt, re.M)}
    sents = [(int(i), t) for i, t in re.findall(r"^\[(\d+)\] (.*)$", prompt.split(
        "Answer sentences to check:", 1)[-1], re.M)]
    last = max(ev) if ev else -1
    out = []
    for i, s in sents:
        clean = re.sub(r"\[K\d+(?:,\s*K\d+)*\]", "", s)
        st = set(tokens(clean))
        if clean.lstrip().startswith(("-", "*")) and last >= 0:
            out.append({"sentence_index": i, "supporting_evidence_index": last})
            continue
        best, best_score = -1, 0.0
        for j, t in ev.items():
            score = len(st & set(tokens(t))) / max(1, len(st))
            if score > best_score:
                best, best_score = j, score
        if best_score < 0.4:
            best = last if (ACTION.search(clean) and last >= 0) else -1
        out.append({"sentence_index": i, "supporting_evidence_index": best})
    return {"judgments": out}


# --- Reasoner ----------------------------------------------------------------
IMPERATIVE = ("keep", "avoid", "dim", "reduce", "limit", "take", "use", "eat", "drink",
              "maintain", "get", "stop", "start", "try", "consider", "increase", "ensure")


def reasoner(prompt: str) -> str:
    qm = re.search(r"Practitioner's question:\s*(.*?)(?:\n\nAn independent check|\Z)", prompt, re.S)
    question = qm.group(1).strip() if qm else ""
    cm = re.search(r"Accumulated knowledge-base context:\n---\n(.*?)\n---\n\nPractitioner", prompt, re.S)
    block = cm.group(1) if cm else ""
    items = re.findall(r"\[K(\d+)\] \(source: (.*?)\) (.*?)(?=\n\n\[K\d+\]|\Z)", block, re.S)
    qtok = set(tokens(question))
    picked = []
    for _order, (k, _src, text) in enumerate(items):
        sents = [x for x in sentences(text)
                 if not (re.match(r"^[A-Za-z ]{1,30}:", x) and len(x) < 70)]
        if any(qtok & set(tokens(x)) for x in sents):
            picked.extend((int(k), x) for x in sents)
    if not picked:
        return "I don't have anything on that."
    top = [(0, 0, k, x) for k, x in picked[:5]]
    pts = []
    for _score, _o, k, s in top:
        s = s.rstrip(".")
        first = s.split()[0].lower() if s.split() else ""
        if first in IMPERATIVE:
            s = "Advise the client to " + s[0].lower() + s[1:]
        pts.append(f"{s} [K{k}].")
    name = (re.search(r"Patient:\s*(.*)", prompt) or [None, "the patient"])[1].strip()
    meds = (re.search(r"Current medications:\s*(.*)", prompt) or [None, "none recorded"])[1].strip()
    return (" ".join(pts) + "\n\n## Confirm with patient\n"
            f"- Current medications and supplements (recorded: {meds}).\n"
            "- How long the problem has been present.\n\n"
            "## Next steps\n"
            "- Review progress at the next consult.\n"
            f"- Save this session to {name}'s record.")


def summary(prompt: str) -> str:
    flat = " ".join(prompt.split())
    return (f"Session covered: {flat[:220]}{'...' if len(flat) > 220 else ''} "
            "The assistant advised using only the clinic's library. "
            "Review progress at the next consult.")


# --- generic fallback for any unknown schema ---------------------------------
def blank(schema: dict):
    t = schema.get("type")
    if t == "object":
        return {k: blank(v) for k, v in schema.get("properties", {}).items()}
    return {"array": [], "string": "", "integer": 0, "number": 0, "boolean": False}.get(t)


def chat(body: dict) -> str:
    msgs = body.get("messages", [])
    system = next((m["content"] for m in msgs if m["role"] == "system"), "")
    user = next((m["content"] for m in reversed(msgs) if m["role"] == "user"), "")
    rf = body.get("response_format") or {}
    if rf.get("type") == "json_schema":
        schema = rf["json_schema"]["schema"]
        props = set(schema.get("properties", {}))
        if "suggested_grade" in props:
            out = reader(user)
        elif {"entities", "relationships"} <= props:
            out = kg_builder(user)
        elif "search_query" in props:
            out = search_query(user)
        elif "judgments" in props and "Evidence:" in user:
            out = checker(user)
        elif "judgments" in props:
            out = judge(user)
        elif "groups" in props:
            out = {"groups": []}
        else:
            out = blank(schema)
        return json.dumps(out)
    if system.startswith("You are a senior clinician"):
        return reasoner(user)
    if system.startswith("Write a short session summary"):
        return summary(user)
    m = re.search(r"---\n(.*)\n---", user, re.S)
    return (m.group(1) if m else user).strip()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def _send(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            return self._send({"object": "list", "data": [
                {"id": m, "object": "model", "created": 0, "owned_by": "mock"} for m in MODELS]})
        self._send({"status": "mock-llm ok"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        model = body.get("model", "mock-model")
        if self.path.rstrip("/").endswith("/embeddings"):
            inputs = body.get("input", [])
            inputs = [inputs] if isinstance(inputs, str) else inputs
            return self._send({"object": "list", "model": model, "data": [
                {"object": "embedding", "index": i, "embedding": embed(t)}
                for i, t in enumerate(inputs)],
                "usage": {"prompt_tokens": sum(len(t) // 4 for t in inputs), "total_tokens": 0}})
        if self.path.rstrip("/").endswith("/chat/completions"):
            content = chat(body)
            pt = sum(len(m.get("content", "")) // 4 for m in body.get("messages", []))
            ct = len(content) // 4
            return self._send({"id": "mock", "object": "chat.completion", "created": 0,
                               "model": model,
                               "choices": [{"index": 0, "finish_reason": "stop",
                                            "message": {"role": "assistant", "content": content}}],
                               "usage": {"prompt_tokens": pt, "completion_tokens": ct,
                                         "total_tokens": pt + ct}})
        self._send({"error": "not found"}, 404)


if __name__ == "__main__":
    print(f"mock-llm listening on 127.0.0.1:{PORT} (models: {', '.join(MODELS)})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
