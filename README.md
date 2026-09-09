# Clinic

### An AI assistant your practitioners can actually trust — because it can't say anything you didn't teach it.

Every other clinical AI tool asks you to trust a black box trained on the
open internet. Clinic doesn't. It answers a practitioner's question using
**only** the knowledge library your clinic curates and grades — and every
answer ships with the receipts: which source, which page, checked by a
second, independent AI before a practitioner ever sees it.

**Live right now:** [telehealth.devshorepartners.id](https://telehealth.devshorepartners.id)

---

## The problem with "just use ChatGPT"

A generic AI answers a clinical question from whatever it happened to
absorb during training — no way to know if that's current, sourced, safe,
or even relevant to how *your* clinic actually practices. There's nothing
to check it against, and nothing stopping it from sounding just as
confident when it's wrong.

That's not a tool a practitioner can put their name behind.

## What Clinic does instead

You upload the sources your clinic actually trusts — protocols,
guidelines, internal notes, anything. Clinic reads each one, grades it,
and adds it to a living library. When a practitioner asks a question
during a consult, an AI team goes to work — and never once reaches
outside that library for an answer.

| | |
|---|---|
| 🧠 **Trained on what you teach it** | Nothing reaches an answer that isn't in your library. No open-internet guessing. |
| 📎 **Every claim is cited** | Click a citation, jump straight to the passage — page number included. |
| 🔍 **An independent check challenges every answer** | A second AI verifies the draft against its sources before a practitioner sees it, and flags anything it can't confirm. |
| 🎚️ **You decide what it's allowed to use** | A grade slider controls the reliability bar in real time — drop it and a low-confidence source becomes reachable; raise it and it's gone. |
| 🩺 **It remembers** | Save a consult summary straight into the patient record — nothing has to be re-explained next visit. |
| 🗂️ **A full paper trail** | Every ingest, every regrade, every question — logged, for the moments someone needs to know exactly what the AI was shown. |

## Built entirely on Claude

Every role on the AI team — the one that reads your sources, the one that
decides what to open, the one that writes the answer, the one that checks
it — is an Anthropic model. No second vendor, no mystery pipeline stitched
together from whatever was cheapest. One accountable model family, doing
four different, deliberately separated jobs.

| Role | Job |
|---|---|
| **Reader** | Reads a new source, writes its title, summary, topics, and a suggested reliability grade |
| **Librarian** | Decides which sources are worth opening for a given question — never told the grade, so relevance and trust stay separate |
| **Specialist** | Writes the grounded answer, citing every claim back to its source |
| **Checker** | Independently verifies the draft against those sources before it's shown to anyone |

## See it for yourself — a 5-minute walkthrough

1. **Admin uploads a source.** Watch the Reader title it, summarize it, tag
   it, and suggest a grade — automatically.
2. **Upload a second, weaker source** on the same topic. The Reader grades
   it low, on its own judgment.
3. **A practitioner asks a real clinical question.** The answer comes back
   with inline citations — click one, jump to the exact passage it came
   from.
4. **Ask something the weak source overreaches on.** At a high grade bar,
   it's invisible to the AI. Drag the reliability slider down, ask again —
   now the AI can see it, and openly says so while weighing it against the
   stronger source.
5. **Save the session.** It's now part of the patient's record for next time.

That's the whole pitch, live, in under five minutes.

## Want the engineering detail?

This README is intentionally the pitch, not the manual. For the real
technical documentation — architecture, data model, API, security,
deployment — see [`specs/`](specs/README.md) (versioned, and it says
what's actually built vs. proposed) and [`DEPLOY.md`](DEPLOY.md).
