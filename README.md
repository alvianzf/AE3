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

### 🧠 Trained on what you teach it
Nothing reaches an answer that isn't in your library. There's no fallback
to whatever the underlying model absorbed during training — if your
clinic hasn't uploaded it, graded it, and let it into the library, the AI
can't see it, let alone cite it.

### 📎 Every claim is cited
Every sentence in an answer traces back to a specific source and page.
Click a citation and you land on the exact passage it came from — not a
document-level "trust me," a line you can actually go read.

### 🔍 An independent check challenges every answer
A second, separate AI re-reads the draft answer against its cited sources
before a practitioner ever sees it — the same "don't grade your own
homework" principle a second reviewer gives you, run automatically on
every single answer, and it says so explicitly when it can't confirm a
claim rather than staying quiet about it.

### 🎚️ You decide what it's allowed to use
Every source carries a reliability grade, and a slider controls the bar
in real time. Drop it and a lower-confidence source becomes reachable for
that question; raise it and the AI loses access to anything below the
line — your clinic's judgment call, adjustable per question, not a fixed
setting buried in an admin panel.

### 🩺 It remembers
A consult summary saves straight into the patient record with one click —
nothing a practitioner explained in one visit has to be re-explained by
the client, or re-derived by the practitioner, at the next one.

### 🗂️ A full paper trail
Every ingest, every regrade, every question asked — logged, so when
someone needs to know exactly what the AI was shown before it answered a
specific question, that's a lookup, not a reconstruction.

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
