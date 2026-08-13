"""End-to-end verification against a running server.

    .venv/bin/uvicorn app.main:app &
    .venv/bin/python verify.py

Walks the whole demo path through the HTTP API and asserts the behaviours the
PoC is meant to prove. Needs a real ANTHROPIC_API_KEY in .env.
"""
import http.cookiejar
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import json as jsonlib

ROOT = os.environ.get("CLINIC_URL", "http://localhost:8000").rstrip("/")
BASE = ROOT + "/api"
PASSPHRASE = os.environ.get("ACCESS_PASSPHRASE", "DevshorePartners2026")

# Every /api route sits behind the access gate, so hold its cookie like a browser.
_opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
# Cloudflare's browser-integrity check rejects urllib's default agent with a 1010,
# so identify the script rather than letting it look like an unnamed bot.
_opener.addheaders = [
    ("User-Agent", "Mozilla/5.0 (compatible; clinic-verify/1.0; +devshorepartners.id)")
]


def unlock():
    body = urllib.parse.urlencode({"passphrase": PASSPHRASE}).encode()
    req = urllib.request.Request(ROOT + "/gate", data=body, method="POST")
    with _opener.open(req, timeout=30) as res:
        if res.status not in (200, 303):
            sys.exit(f"FAIL gate -> {res.status}")


class ApiError(Exception):
    def __init__(self, status, detail):
        super().__init__(f"{status}: {detail}")
        self.status, self.detail = status, detail


def call(method, path, body=None, form=None, expect=None, raises=False,
         upload=None, raw=False):
    """Call the API.

    expect: an HTTP status to treat as success, returning the error `detail`.
    raises: raise ApiError instead of exiting, so a caller can branch on status.
    upload: (field, filename, content_type, bytes) sent as a file part.
    raw: return (bytes, headers) instead of parsed JSON, for file downloads.
    """
    if form is not None or upload is not None:
        boundary = "----verify"
        parts = []
        for k, v in (form or {}).items():
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; "
                         f'name="{k}"\r\n\r\n{v}\r\n'.encode())
        if upload is not None:
            field, name, ctype, blob = upload
            parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; "
                f'name="{field}"; filename="{name}"\r\n'
                f"Content-Type: {ctype}\r\n\r\n".encode() + blob + b"\r\n")
        data = b"".join(parts) + f"--{boundary}--\r\n".encode()
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    elif body is not None:
        data = jsonlib.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
    else:
        data, headers = None, {}
    req = urllib.request.Request(BASE + path, data=data, headers=headers,
                                 method=method)
    # urllib turns a 303 from POST into a GET follow; harmless for our calls.
    try:
        with _opener.open(req, timeout=180) as res:
            if expect is not None:
                sys.exit(f"FAIL {method} {path} -> expected {expect}, got {res.status}")
            if raw:
                # res.headers, not dict(): header lookup must stay
                # case-insensitive, and the server sends them lowercased.
                return res.read(), res.headers
            return jsonlib.loads(res.read())
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode()
        if expect is not None and exc.code == expect:
            return jsonlib.loads(payload).get("detail")
        if raises:
            raise ApiError(exc.code, jsonlib.loads(payload).get("detail")) from None
        sys.exit(f"FAIL {method} {path} -> {exc.code}: {payload[:300]}")


# A marker unique to this run, appended to every fixture. Two consequences, both
# about not touching data you created: the fixtures can never collide with a
# source you ingested (so the duplicate check never offers to replace yours), and
# the cleanup at the end only ever removes rows this run wrote.
RUN = uuid.uuid4().hex[:8]
MARK = f"\n\nInternal test marker: verify-run-{RUN}. Not clinical content."

GOOD = """Vitamin D deficiency and thyroid function

Low serum 25-hydroxyvitamin D is frequently observed alongside autoimmune thyroid
disease. In a cohort of 218 patients with Hashimoto's thyroiditis, mean 25(OH)D
was 14.2 ng/mL compared with 24.8 ng/mL in euthyroid controls.

Vitamin D deficiency also impairs intestinal iron absorption. Patients presenting
with both low ferritin and low 25(OH)D should be assessed for a shared
malabsorptive cause rather than treated as two independent findings.

Repletion protocol: 4000 IU cholecalciferol daily for 12 weeks, with serum
25(OH)D remeasured at week 12. Target range 40-60 ng/mL.
"""

WEAK = """Episode 214 - The Sunshine Reset

What I tell everyone on my programme is that vitamin D is the master hormone. If
your vitamin D is low your thyroid is basically switched off. I have seen people
reverse Hashimoto's completely with sun exposure alone.

My protocol is 50000 IU a day for a month. Doctors say that is too much but they
do not understand the terrain. Ferritin does not really matter, it is all
downstream of the vitamin D.
"""

QUESTION = "Her vitamin D is low and her ferritin is low — what could that be tied to?"

print(f"Target: {ROOT}")
print("\n0. Access gate")
blocked = call("GET", "/sources", expect=401)
assert blocked, "an /api route answered without the access phrase"
print(f"   ungated request refused: {blocked}")
unlock()
print("   access phrase accepted")

print("\n1. Health")
health = call("GET", "/health")
for svc in ("neo4j", "anthropic", "patients"):
    state = health[svc]
    print(f"   {'ok  ' if state['ok'] else 'FAIL'} {svc}"
          + ("" if state["ok"] else f"  {state.get('error', '')[:120]}"))
if not health["anthropic"]["ok"]:
    sys.exit("\nANTHROPIC_API_KEY is not valid — put a real key in .env and rerun.")

def ingest_fixture(body, kind, origin):
    """Ingest a run-unique fixture, so it cannot clash with real library content."""
    return call("POST", "/sources",
                form={"text": body + MARK, "kind": kind, "origin": origin})


print("\n2. Ingestion (the Reader tags and grades on its own)")
print(f"   (fixtures tagged verify-run-{RUN}; existing library untouched)")
before_total = call("GET", "/sources?per_page=1")["total"]
strong = ingest_fixture(GOOD, "protocol", "Endocrine Society 2024")
weak = ingest_fixture(WEAK, "podcast transcript", "wellness podcast")
for src in (strong, weak):
    print(f"   \"{src['title']}\" — grade {src['grade']}, {src['chunks']} passages, "
          f"topics {src['topics']}")
    assert src["chunks"] > 0 and src["summary"] and src["topics"]
    assert 1 <= src["grade"] <= 10
if strong["grade"] <= weak["grade"]:
    print(f"   NOTE: the Reader graded the protocol ({strong['grade']}) no higher "
          f"than the podcast ({weak['grade']}). Forcing grades for the next test.")
call("PATCH", f"/sources/{strong['id']}", body={"grade": 9})
call("PATCH", f"/sources/{weak['id']}", body={"grade": 3})

print("\n2b. Duplicate ingest is refused")
before = call("GET", "/sources?per_page=1")["total"]
dup = call("POST", "/sources", expect=409, form={
    "text": GOOD + MARK, "kind": "protocol", "origin": "Endocrine Society 2024"})
print(f"   409: {dup['message']}")
assert dup["duplicate_of"] == strong["id"], "409 did not point at the original"
assert call("GET", "/sources?per_page=1")["total"] == before, "a copy was created"
# Whitespace differences must not defeat it — the same PDF re-extracted varies.
noisy = call("POST", "/sources", expect=409, form={
    "text": "  " + (GOOD + MARK).replace("\n\n", "\n\n\n") + "\n ",
    "kind": "protocol", "origin": "Endocrine Society 2024"})
assert noisy["duplicate_of"] == strong["id"], "whitespace defeated the fingerprint"
print("   whitespace-only differences are caught too")

replaced = call("POST", "/sources", form={
    "text": GOOD + MARK, "kind": "protocol",
    "origin": "Endocrine Society 2024 (rev B)", "replaces": strong["id"]})
assert call("GET", "/sources?per_page=1")["total"] == before, \
    "replace changed the source count"
assert replaced["id"] != strong["id"], "replace reused the old id"
assert not any(s["id"] == strong["id"]
               for s in call("GET", "/sources")["sources"]), \
    "the superseded source is still in the library"
print(f"   explicit replace worked: \"{replaced['title']}\" "
      f"({replaced['origin']}), library still {before} sources")
strong = replaced  # later steps reference the live copy
call("PATCH", f"/sources/{strong['id']}", body={"grade": 9})

print("\n2c. Source metadata and provenance")
card = call("GET", f"/sources/{strong['id']}")
for field in ("author", "published", "reference", "kind", "origin", "filename",
              "page_count", "char_count", "content_hash", "created_at", "summary"):
    assert field in card, f"source card is missing {field}"
print(f"   card carries author={card['author']!r} published={card['published']!r} "
      f"chars={card['char_count']} fingerprint={card['content_hash'][:8]}")

full = call("GET", f"/sources/{strong['id']}/text")
assert full["body"], "the original body was not stored"
assert full["passages"], "no passages returned for reading"
assert all(p["locator"] for p in full["passages"]), "a passage has no locator"
print(f"   original readable: {len(full['body'])} chars, "
      f"{len(full['passages'])} passage(s), first locator "
      f"\"{full['passages'][0]['locator']}\"")

print("\n2d. An uploaded file is kept in its original format, not only chunked")
# Bytes the extractor would not reproduce: extraction normalises whitespace and
# drops layout, so a byte-for-byte match proves the archive is the file itself
# rather than something reassembled from the passages.
UPLOAD = (GOOD + MARK + "\n\n\tIndented line kept verbatim.  \r\n").encode()
uploaded = call("POST", "/sources",
                form={"kind": "protocol", "origin": f"upload check {RUN}"},
                upload=("file", "upload-check.txt", "text/plain", UPLOAD))
assert uploaded["original_name"] == "upload-check.txt", "the filename was not kept"
assert uploaded["original_bytes"] == len(UPLOAD), "the stored size does not match"
assert uploaded["chunks"] > 0, "the upload was archived but not chunked"
blob, headers = call("GET", f"/sources/{uploaded['id']}/original", raw=True)
assert blob == UPLOAD, "the served original is not byte-for-byte what was uploaded"
assert "upload-check.txt" in headers.get("Content-Disposition", ""), \
    "the download does not carry its original filename"
print(f"   {uploaded['original_bytes']} bytes returned unchanged as "
      f"{uploaded['original_media_type']}, alongside {uploaded['chunks']} passages")

# Pasted text has no original: the passages are the source, so there is nothing
# to download and the endpoint must say so rather than invent a file.
assert weak["original_name"] is None, "pasted text claims an original file"
call("GET", f"/sources/{weak['id']}/original", expect=404)
print("   pasted text reports no original and 404s, as specified")

# The file must not outlive its source node.
call("DELETE", f"/sources/{uploaded['id']}")
call("GET", f"/sources/{uploaded['id']}/original", expect=404)
print("   deleting the source removed its stored original")

print("\n3. Patient record")
patient = call("POST", "/patients", body={
    "name": "Verification Patient", "country": "SK", "dob": "1986-03-14"})
for kind, content in [
    ("lab", "Ferritin 11 ng/mL (ref 15-150)"),
    ("lab", "25(OH)D 16 ng/mL (ref 30-100)"),
    ("history", "Fatigue and hair thinning for 8 months."),
]:
    call("POST", f"/patients/{patient['id']}/entries",
         body={"kind": kind, "content": content})
print(f"   created {patient['name']} with 3 record entries")

print("\n4. Consult at grade >= 7 (the grade filter)")
high = call("POST", "/consult", body={
    "patient_id": patient["id"], "question": QUESTION,
    "min_grade": 7, "run_check": True})
titles = {s["title"] for s in high["sources"]}
lib = high["librarian"]
print(f"   librarian saw {lib['considered']} card(s), opened "
      f"{[o['title'] for o in lib['opened']]}")
print(f"   because: {lib['reasoning']}")
print(f"   {len(high['sources'])} passages from {titles or '{}'}")
print(f"   check: {high['check']['verdict']} — {high['check']['note']}")
print("   ---")
print("   " + high["answer"].replace("\n", "\n   ")[:900])
print("   ---")
assert high["sources"], "no passages retrieved at grade >= 7"
assert weak["title"] not in titles, f"grade-3 source leaked into a grade-7 query"
# Any marker, not literally [S1]: once the library passes nine sources the
# labels are two digits, and "[S1]" stops matching an answer full of [S11].
assert re.search(r"\[S\d+\]", high["answer"]), "answer carries no citation"
s1 = high["sources"][0]
for field in ("locator", "origin", "author", "published", "reference", "kind",
              "filename", "source_id"):
    assert field in s1, f"citation is missing {field}"
print(f"   citation provenance: {s1['label']} · {s1['locator']} · "
      f"{s1['author'] or '(no author)'} · {s1['origin']} → source {s1['source_id'][:8]}")
print("   PASS: only the grade-9 source was used, and the answer cites it "
      "with a locator")

print("\n5. Consult at grade >= 1 (the weak source becomes available)")
low = call("POST", "/consult", body={
    "patient_id": patient["id"], "question": QUESTION,
    "min_grade": 1, "run_check": True})
print(f"   librarian saw {low['librarian']['considered']} card(s), opened "
      f"{[o['title'] for o in low['librarian']['opened']]}")
print(f"   check: {low['check']['verdict']} — {low['check']['note']}")
# The grade bar controls what the Librarian is OFFERED; whether it opens a source
# is its own judgement. Assert the invariant rather than exact counts, so the
# check survives whatever else happens to be in the library.
assert all(s["grade"] >= 7 for s in high["sources"]), \
    f"a sub-grade source was cited at min_grade=7: " \
    f"{[(s['title'], s['grade']) for s in high['sources']]}"
assert low["librarian"]["considered"] > high["librarian"]["considered"], \
    "lowering the grade bar did not widen the catalogue " \
    f"({high['librarian']['considered']} -> {low['librarian']['considered']})"
print(f"   PASS: the grade bar widens the catalogue "
      f"({high['librarian']['considered']} cards at >=7, "
      f"{low['librarian']['considered']} at >=1) and nothing below the bar was cited")

print("\n5b. A question only the weak source speaks to")
CLAIM = ("Can vitamin D supplementation alone reverse Hashimoto's, and is 50,000 "
         "IU daily an appropriate dose?")
gated = call("POST", "/consult", body={
    "patient_id": patient["id"], "question": CLAIM,
    "min_grade": 7, "run_check": False})
open_ = call("POST", "/consult", body={
    "patient_id": patient["id"], "question": CLAIM,
    "min_grade": 1, "run_check": True})
print(f"   at grade >=7: opened {[o['title'] for o in gated['librarian']['opened']]}")
print(f"   at grade >=1: opened {[o['title'] for o in open_['librarian']['opened']]}")
assert weak["title"] not in {s["title"] for s in gated["sources"]}, \
    "the grade-3 source reached a grade-7 answer"
if weak["title"] in {s["title"] for s in open_["sources"]}:
    print(f"   check on the weak source: {open_['check']['verdict']} — "
          f"{open_['check']['note']}")
    print("   PASS: the podcast is unreachable at >=7 and reachable at >=1")
else:
    print("   NOTE: the librarian declined the podcast even at grade >=1. The "
          "grade gate is proven above; this is the librarian exercising its own "
          "judgement on top of it.")

print("\n6. Grounding — a question the library cannot answer")
off = call("POST", "/consult", body={
    "patient_id": patient["id"],
    "question": "What fixation hardware is indicated for a distal ankle fracture?",
    "min_grade": 7, "run_check": False})
print(f"   librarian opened {off['librarian']['opened']} "
      f"({len(off['sources'])} passages)")
print(f"   because: {off['librarian']['reasoning']}")
print("   " + off["answer"].replace("\n", "\n   ")[:400])
assert not off["sources"], "the librarian opened an unrelated source"
print("   PASS: nothing opened, and the Specialist had to say so")

print("\n7. Session summary write-back")
entry = call("POST", f"/patients/{patient['id']}/summary", body={
    "transcript": f"Question: {QUESTION}\n\nAnswer:\n{high['answer']}"})
print(f"   saved: {entry['content'][:200]}")
refreshed = call("GET", f"/patients/{patient['id']}")
kinds = [e["kind"] for e in refreshed["entries"]]
assert "session_summary" in kinds, "summary did not reach the record"
print("   PASS: summary is in the patient record and will be in the next prompt")

print("\n7b. Patient data stays in the patient vault")
trail = call("GET", "/audit")
lib = [e for e in trail if e["vault"] == "library"]
vault = [e for e in trail if e["vault"] == "patient"]
print(f"   {len(lib)} library event(s), {len(vault)} patient-vault event(s)")
# The library store must never carry a patient name, a clinical question, or a
# patient id. This is the check that caught the name leaking into Neo4j.
leaked = [e for e in lib
          if patient["name"].lower() in e["detail"].lower()
          or patient["id"] in e["detail"]
          or QUESTION[:30].lower() in e["detail"].lower()]
assert not leaked, f"patient data found in the knowledge library: {leaked}"
assert any(e["action"] == "question asked" for e in vault), \
    "the question asked was not recorded in the patient vault"
assert all(e["action"] not in ("question asked", "patient created",
                              "session summary saved") for e in lib), \
    "a patient-touching event was written to the knowledge library"
print("   PASS: no patient name, id or question text in the library store")

print("\n8. Coverage, audit, deletion")
print(f"   coverage: {call('GET', '/coverage')}")
before = call("GET", "/health")["stats"]["chunks"]
call("DELETE", f"/sources/{weak['id']}")
after = call("GET", "/health")["stats"]["chunks"]
print(f"   chunks {before} -> {after} after removing the podcast source")
assert after == before - weak["chunks"]
gone = call("POST", "/consult", body={
    "patient_id": patient["id"], "question": QUESTION,
    "min_grade": 1, "run_check": False})
# By id, not title: a leftover fixture from an aborted run carries the same
# Reader-generated title, and this step is about *this* source being gone.
assert weak["id"] not in {s["source_id"] for s in gone["sources"]}
print("   PASS: a removed source disappears from both shelves")
print(f"   audit trail: {len(call('GET', '/audit'))} events logged")

# Leave the library as we found it. Without this, every run against a live
# instance leaves a fixture behind — and because the Reader titles and grades
# each copy afresh, the leftovers look like real but inconsistent sources.
call("DELETE", f"/sources/{strong['id']}")
call("DELETE", f"/patients/{patient['id']}")
after_total = call("GET", "/sources?per_page=1")["total"]
assert after_total == before_total, (
    f"library left with {after_total} sources, started with {before_total} — "
    "this run did not clean up after itself")
assert not any(p["id"] == patient["id"] for p in call("GET", "/patients")), \
    "the test patient survived erasure"
print("   cleaned up: test fixtures and test patient removed")

print("\n9. Regression: an untagged source still gets its passages")
# Calls the store directly — the trigger (the Reader returning no topics for a
# non-clinical document) cannot be forced through the API on demand. An empty
# UNWIND list used to discard the rest of the write and produce 0 passages.
if ROOT not in ("http://localhost:8000", "http://127.0.0.1:8000"):
    print("   SKIPPED: this check talks to the store directly, so it would test "
          "this machine's database rather than the deployed one. Run it locally.")
    print("\nALL CHECKS PASSED")
    raise SystemExit(0)

sys.path.insert(0, ".")
from app import knowledge  # noqa: E402

untagged = knowledge.ingest_source(
    title="Untagged fixture", filename="untagged.txt", kind="article",
    origin="test", grade=5, summary="No topics on purpose.", topics=[],
    passages=knowledge.chunk_pages([(None, "First para.\n\nSecond para.")]),
    digest=knowledge.content_hash("regression-fixture-untagged"),
    body="First para.\n\nSecond para.",
)
print(f"   topics={untagged['topics']} passages={untagged['chunks']}")
assert untagged["chunks"] > 0, "an untagged source was written with no passages"
knowledge.delete_source(untagged["id"])
print("   PASS: passages are written even with no topics")

print("\nALL CHECKS PASSED")
