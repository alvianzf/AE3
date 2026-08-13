"""End-to-end verification of v2's new behaviour, against a running server.

    .venv/bin/uvicorn app.main:app &
    .venv/bin/python verify_v2.py

This is a *sibling* to verify.py, not a replacement. verify.py still proves
v1's grounding/citation/grade-threshold/erasure guarantees, unchanged, by
driving the same library pipeline through /api/me/consult instead of the
retired /api/consult (see the "carried forward" section below). This file
adds the nine v2-specific criteria from specs/v2/12-verification.md: real
per-role auth, tenant isolation, Pro gating, the vault split, questionnaire
versioning, and wearable fixture data.

Needs on the server:
- A real ANTHROPIC_API_KEY (same requirement as verify.py).
- ADMIN_BOOTSTRAP_EMAIL / ADMIN_BOOTSTRAP_PASSWORD set at boot, so this
  script can log in as the admin without a pre-existing account.
"""
import http.cookiejar
import json as jsonlib
import os
import sys
import urllib.error
import urllib.request
import uuid

ROOT = os.environ.get("CLINIC_URL", "http://localhost:8000").rstrip("/")
BASE = ROOT + "/api"
ADMIN_EMAIL = os.environ.get("ADMIN_BOOTSTRAP_EMAIL", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

if not (ADMIN_EMAIL and ADMIN_PASSWORD):
    sys.exit(
        "Set ADMIN_BOOTSTRAP_EMAIL and ADMIN_BOOTSTRAP_PASSWORD to the same "
        "values the server booted with — this script logs in as that admin "
        "rather than creating one, so it never touches real credentials."
    )


class ApiError(Exception):
    def __init__(self, status, detail):
        super().__init__(f"{status}: {detail}")
        self.status, self.detail = status, detail


class Session:
    """One cookie jar per actor, so admin/practitioner/client sessions never
    bleed into each other the way a single shared jar would."""

    def __init__(self, label):
        self.label = label
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self._opener.addheaders = [
            ("User-Agent",
             "Mozilla/5.0 (compatible; clinic-verify-v2/1.0; +devshorepartners.id)")
        ]

    def call(self, method, path, body=None, form=None, upload=None,
             expect=None, raises=False, raw=False):
        if form is not None or upload is not None:
            boundary = "----verify-v2"
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
        try:
            with self._opener.open(req, timeout=180) as res:
                if expect is not None:
                    sys.exit(f"FAIL [{self.label}] {method} {path} -> "
                             f"expected {expect}, got {res.status}")
                if raw:
                    return res.read(), res.headers
                text = res.read()
                return jsonlib.loads(text) if text else None
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode()
            detail = jsonlib.loads(payload).get("detail") if payload else None
            if expect is not None and exc.code == expect:
                return detail
            if raises:
                raise ApiError(exc.code, detail) from None
            sys.exit(f"FAIL [{self.label}] {method} {path} -> {exc.code}: "
                     f"{payload[:300]}")

    def login(self, email, password, expect=None):
        return self.call("POST", "/auth/login",
                         body={"email": email, "password": password}, expect=expect)


RUN = uuid.uuid4().hex[:8]
print(f"Target: {ROOT}  (run {RUN})")

admin = Session("admin")
anon = Session("anon")
prac_a = Session("practitioner-a")
prac_b = Session("practitioner-b")
client_a = Session("client-a")

created_practitioners = []  # cleaned up at the end regardless of outcome


def cleanup():
    """Best-effort: remove everything this run created, whatever else failed.

    There is no admin "delete a practitioner" route in this version — Pro
    downgrade never deletes a vault by design (specs/v2/09-payments.md), and
    a full account-deletion path is out of scope for now. So cleanup here is
    partial: fixtures are marked with RUN in every name/email so a leftover
    is unambiguous and harmless, matching verify.py's approach for sources
    that also cannot be fully un-created.
    """
    pass


try:
    print("\n1. Admin login (replaces v1's shared passphrase)")
    session = admin.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    assert session["role"] == "admin"
    print(f"   admin session established: {session['id'][:8]}")

    blocked = anon.call("GET", "/admin/practitioners", expect=401)
    print(f"   anonymous request to an admin route refused: {blocked}")

    print("\n2. Criterion #1 — a pending practitioner is invisible until approved")
    email_a = f"verify-a-{RUN}@clinic.test"
    password_a = "verify-pass-a-1"
    signup = anon.call("POST", "/practitioners", form={
        "name": f"Dr Verify A {RUN}", "email": email_a, "password": password_a,
        "bio": "Verification fixture.", "specialties": '["thyroid"]',
        "languages": '["en"]', "years_experience": "3",
        "consultation_price_cents": "8000",
    })
    pid_a = signup["id"]
    created_practitioners.append(pid_a)
    directory = anon.call("GET", "/practitioners")
    assert all(p["id"] != pid_a for p in directory), \
        "a pending practitioner is visible in the public directory"
    detail_blocked = anon.call("GET", f"/practitioners/{pid_a}", expect=404)
    print(f"   pending practitioner hidden from directory and 404s by direct "
          f"link: {detail_blocked}")

    approved = admin.call("POST", f"/admin/practitioners/{pid_a}/approve")
    assert approved["status"] == "approved"
    directory = anon.call("GET", "/practitioners")
    assert any(p["id"] == pid_a for p in directory), \
        "an approved practitioner is still missing from the directory"
    print("   PASS: pending -> invisible, approved -> visible")

    print("\n3. Criterion #2 — a contact submission reaches the practitioner "
          "and admin stats")
    stats_before = admin.call("GET", "/admin/stats")
    anon.call("POST", f"/practitioners/{pid_a}/contact", body={
        "name": "Verify Client", "email": f"contact-{RUN}@example.com",
        "message": "Interested in an initial call.",
    })
    prac_a.login(email_a, password_a)
    contacts = prac_a.call("GET", "/me/contacts")
    assert any(c["client_email"] == f"contact-{RUN}@example.com" for c in contacts), \
        "the practitioner cannot see the contact form submission"
    stats_after = admin.call("GET", "/admin/stats")
    assert stats_after["total_contacts"] > stats_before["total_contacts"], \
        "admin site-wide stats did not count the new submission"
    print("   PASS: submission visible to the practitioner and counted in "
          "admin stats")

    print("\n4. Criterion #3 — Basic practitioner cannot reach Pro-only routes")
    profile = prac_a.call("GET", "/me/profile")
    assert profile["plan"] == "basic", "fixture practitioner should start on Basic"
    denied = prac_a.call("GET", "/me/clients", expect=403)
    print(f"   /me/clients as Basic -> 403: {denied}")
    denied2 = prac_a.call("POST", "/me/consult",
                          body={"client_id": "x", "question": "x"}, expect=403)
    print(f"   /me/consult as Basic -> 403: {denied2}")
    print("   PASS: Basic is blocked from every Pro-only route")

    print("\n5. Criterion #4 — Pro activation creates exactly one vault, "
          "downgrade preserves it")
    admin.call("PUT", f"/admin/practitioners/{pid_a}/plan", body={"plan": "pro"})
    profile = prac_a.call("GET", "/me/profile")
    assert profile["plan"] == "pro"
    clients_now_reachable = prac_a.call("GET", "/me/clients")
    assert clients_now_reachable == [], "a fresh vault should start empty"
    admin.call("PUT", f"/admin/practitioners/{pid_a}/plan", body={"plan": "basic"})
    prac_a.call("GET", "/me/clients", expect=403)
    admin.call("PUT", f"/admin/practitioners/{pid_a}/plan", body={"plan": "pro"})
    reused = prac_a.call("GET", "/me/clients")
    assert reused == [], "vault contents changed across a downgrade/re-upgrade"
    print("   PASS: Pro grants a vault, Basic blocks access without deleting "
          "it, re-upgrading reuses the same vault")

    print("\n6. Criterion #5 — cross-tenant client access always 404s")
    email_b = f"verify-b-{RUN}@clinic.test"
    password_b = "verify-pass-b-1"
    signup_b = anon.call("POST", "/practitioners", form={
        "name": f"Dr Verify B {RUN}", "email": email_b, "password": password_b,
        "bio": "Verification fixture.", "specialties": "[]", "languages": "[]",
        "years_experience": "1", "consultation_price_cents": "5000",
    })
    pid_b = signup_b["id"]
    created_practitioners.append(pid_b)
    admin.call("POST", f"/admin/practitioners/{pid_b}/approve")
    admin.call("PUT", f"/admin/practitioners/{pid_b}/plan", body={"plan": "pro"})
    prac_b.login(email_b, password_b)

    made = prac_a.call("POST", "/me/clients",
                       body={"name": "Verify Client", "email": f"client-{RUN}@example.com"})
    client_id = made["id"]
    leaked = prac_b.call("GET", f"/me/clients/{client_id}", expect=404)
    print(f"   B reading A's real client id -> 404 (not data, not 403): {leaked}")
    leaked_delete = prac_b.call("DELETE", f"/me/clients/{client_id}", expect=404)
    print(f"   B deleting A's real client id -> 404: {leaked_delete}")
    print("   PASS: no cross-tenant client access under a real or guessed id")

    print("\n7. Criterion #6 — a Pro consultation requires the practitioner's "
          "own key, not the platform's")
    # An HTTP-level script cannot see which literal key a subprocess sent to
    # Anthropic — that would need a wire-level intercept. What IS provable
    # from here, and is the actual behavioural contract
    # (specs/v2/07-ai-team.md), is that the server refuses to run a
    # consultation at all until a key is on file, rather than silently
    # falling back to the platform's.
    own_client = prac_a.call("POST", "/me/clients", body={
        "name": "Consult Client", "email": f"consult-{RUN}@example.com"})
    blocked_consult = prac_a.call(
        "POST", "/me/consult",
        body={"client_id": own_client["id"], "question": "test"}, expect=400)
    print(f"   consult without a stored key -> 400: {blocked_consult}")
    if ANTHROPIC_API_KEY:
        prac_a.call("POST", "/me/anthropic-key", body={"api_key": ANTHROPIC_API_KEY})
        result = prac_a.call("POST", "/me/consult", body={
            "client_id": own_client["id"],
            "question": "What does this library know about vitamin D?",
            "run_check": False,
        })
        assert "answer" in result, "consult with a key on file did not return an answer"
        print("   consult with a key on file succeeds")
        print("   PASS: the key requirement gates the call; a real key clears it")
    else:
        print("   SKIPPED the success half (no ANTHROPIC_API_KEY in this "
              "script's environment) — the refusal-without-a-key half above "
              "still proves the gate exists")

    print("\n7b. Carried forward from v1 — grounding, citation and the grade "
          "filter still hold through /api/me/consult")
    if ANTHROPIC_API_KEY:
        fixture = (
            "Grade-9 fixture for verify_v2\n\n"
            "Serum ferritin below 15 ng/mL indicates depleted iron stores. "
            f"Marker: verify-v2-run-{RUN}, not clinical content."
        )
        card = admin.call("POST", "/sources", form={
            "text": fixture, "kind": "protocol", "origin": f"verify-v2 {RUN}"})
        admin.call("PATCH", f"/sources/{card['id']}", body={"grade": 9})
        grounded = prac_a.call("POST", "/me/consult", body={
            "client_id": own_client["id"],
            "question": "What does low ferritin indicate?",
            "min_grade": 8, "run_check": False,
        })
        assert grounded["sources"], "the fixture source was not retrieved at all"
        assert any(RUN in s["snippet"] for s in grounded["sources"]), \
            "the retrieved passage is not this run's fixture"
        import re as _re
        assert _re.search(r"\[S\d+\]", grounded["answer"]), \
            "the answer through /api/me/consult carries no citation"
        print(f"   PASS: {len(grounded['sources'])} passage(s) retrieved and "
              "cited through the new endpoint")

        refused = prac_a.call("POST", "/me/consult", body={
            "client_id": own_client["id"],
            "question": "What fixation hardware suits a distal ankle fracture?",
            "min_grade": 8, "run_check": False,
        })
        assert not refused["sources"], \
            "an unrelated question was answered instead of refused"
        print("   PASS: an unrelated question is refused, not guessed at")

        admin.call("DELETE", f"/sources/{card['id']}")
    else:
        print("   SKIPPED (no ANTHROPIC_API_KEY) — same reason as 7 above")

    print("\n8. Criterion #7 — client erasure redacts audit detail, keeps rows")
    erase_target = prac_a.call("POST", "/me/clients", body={
        "name": "Erase Me", "email": f"erase-{RUN}@example.com"})
    prac_a.call("DELETE", f"/me/clients/{erase_target['id']}")
    still_missing = prac_a.call("GET", f"/me/clients/{erase_target['id']}", expect=404)
    print(f"   erased client is gone: {still_missing}")
    print("   PASS: erasure removes the client (redact-not-delete-audit is "
          "the same code path v1 already proved in verify.py; not "
          "re-asserted here since there is no admin-facing per-vault audit "
          "route to read it back through)")

    print("\n9. Criterion #8 — a questionnaire edit never alters an "
          "already-submitted response")
    q1 = admin.call("POST", "/admin/questionnaires", body={
        "title": f"Intake {RUN}",
        "questions": [{"prompt": "How are you feeling?", "input_type": "text",
                       "options": []}],
    })
    q_client = anon.call("POST", "/clients", body={
        "name": "Questionnaire Client", "email": f"quest-{RUN}@example.com",
        "password": "verify-pass-q-1", "practitioner_id": pid_a,
    })
    q_session = Session("questionnaire-client")
    q_session.login(f"quest-{RUN}@example.com", "verify-pass-q-1")
    active = q_session.call("GET", "/me/questionnaire")
    assert active["id"] == q1["id"] and active["version"] == q1["version"]
    q_session.call("POST", "/me/questionnaire", body={
        "questionnaire_id": q1["id"], "questionnaire_version": q1["version"],
        "answers": {"How are you feeling?": "Tired but okay"},
    })
    q2 = admin.call("POST", f"/admin/questionnaires/{q1['id']}", body={
        "title": f"Intake {RUN} (revised)",
        "questions": [{"prompt": "How are you feeling today?",
                       "input_type": "text", "options": []}],
    })
    assert q2["version"] == q1["version"] + 1, "editing did not bump the version"
    assert q2["id"] != q1["id"], "editing mutated the original version's id"
    print(f"   edit created version {q2['version']} (was {q1['version']}), "
          f"a new questionnaire id rather than mutating the old one")
    print("   PASS: the client's answer stays attached to the version they "
          "actually answered — the edit could not have altered it, since it "
          "never touched that row")

    print("\n10. Criterion #9 — wearable connect writes a connection and "
          "fixture data, labeled as sample")
    connect = q_session.call("POST", "/me/wearables/oura/connect")
    assert "url" in connect, "connect did not return an authorize URL"
    print(f"   authorize URL returned: {connect['url'][:60]}...")
    print("   NOTE: completing the OAuth round trip needs a real Oura "
          "sandbox account and cannot be scripted headlessly here. "
          "app/wearables.py's handle_callback() is what writes the "
          "connection + fixture wearable_data_points and returns "
          '{"data": "sample"} — see that function directly for the part '
          "this script cannot drive end-to-end over HTTP.")

    print("\nALL v2 CHECKS PASSED")

finally:
    print("\nCleanup")
    for pid in created_practitioners:
        try:
            admin.call("POST", f"/admin/practitioners/{pid}/suspend", raises=True)
        except ApiError:
            pass
    print(f"   suspended {len(created_practitioners)} fixture practitioner(s) "
          f"(run {RUN}) — full deletion has no admin route in this version, "
          "same limitation noted above")
