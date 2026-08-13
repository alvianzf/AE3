/* Clinic — front end. No framework, no build step.
   Flow: practitioner picks a patient (1), reads the file (2), asks Clinic (3).
   Admin teaches a source (1), curates the library (2), checks coverage (3). */

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const debounce = (fn, ms = 250) => {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
};
const humanSize = (b) => b < 1024 ? `${b} B`
  : b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`;
const initials = (name) => name.trim().split(/\s+/).slice(0, 2)
  .map((w) => w[0]).join('').toUpperCase();

async function api(path, opts = {}) {
  const res = await fetch('/api' + path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const d = body.detail;
    // `detail` is a string for simple errors and an object for ones the UI acts
    // on (a duplicate ingest carries the existing source's id).
    const err = new Error((d && typeof d === 'object' ? d.message : d) || res.statusText);
    err.detail = d; err.status = res.status;
    throw err;
  }
  return res.json();
}
const json = (method, body) => ({
  method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
});

let selectedPatient = null;
let sessionId = null;     // consultation currently open in the thread
let libPage = 1;

/* ── Icons ──────────────────────────────────────────────────────────────── */
const ICONS = {
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 16v-5M12 8h.01"/>',
  trash: '<path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13"/>',
  open: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
  check: '<path d="M4 12l5 5L20 6"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  ask: '<path d="M12 3a9 9 0 1 1-9 9 9 9 0 0 1 9-9z"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.7M12 17h.01"/>',
  lab: '<path d="M9 3h6M10 3v5l-4.5 9A2 2 0 0 0 7.3 20h9.4a2 2 0 0 0 1.8-3L14 8V3M7 14h10"/>',
  history: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l4 2"/>',
  note: '<path d="M4 20h4L20 8l-4-4L4 16zM14 6l4 4"/>',
  summary: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l.9-5.4A8 8 0 1 1 21 12z"/>',
  protocol: '<path d="M6 3h9l4 4v14H6zM9 13l2 2 4-4"/>',
  article: '<path d="M6 3h9l4 4v14H6zM9 12h7M9 16h5"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h13v18H6a2 2 0 0 1-2-2zM8 3v18"/>',
  podcast: '<path d="M12 3a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM6 11a6 6 0 0 0 12 0M12 17v4"/>',
  notes: '<path d="M8 3h8v3H8zM6 6h12v15H6zM9 11h6M9 15h4"/>',
  shield: '<path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/>',
  alert: '<path d="M12 4l9 16H3zM12 10v4M12 17h.01"/>',
  users: '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-5 6-5s6 1.7 6 5"/>',
  folder: '<path d="M8 3h8v3H8zM6 6h12v15H6zM9 11h6M9 15h4"/>',
  library: '<path d="M4 5a2 2 0 0 1 2-2h13v18H6a2 2 0 0 1-2-2zM8 3v18"/>',
  // A leaf, for empty states — drawn, not an icon glyph.
  leaf: '<path d="M12 22V8"/><path d="M12 15c0-4 3-7 8-8-.4 4.4-3.2 7.4-8 8z"/><path d="M12 11c0-4-3-7-8-8 .4 4.4 3.2 7.4 8 8z"/>',
};
const icon = (n) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"`
  + ` stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"`
  + ` aria-hidden="true">${ICONS[n]}</svg>`;
const iconBtn = (n, tip, extra = '', cls = '') =>
  `<button class="iconbtn ${cls}" data-tip="${esc(tip)}" aria-label="${esc(tip)}"`
  + ` ${extra}>${icon(n)}</button>`;

const ENTRY_ICON = { lab: 'lab', history: 'history', note: 'note',
                     session_summary: 'summary' };
const KIND_ICON = { protocol: 'protocol', article: 'article',
                    'book chapter': 'book', 'podcast transcript': 'podcast',
                    'clinical notes': 'notes' };

/* ── Small shared pieces ────────────────────────────────────────────────── */
function toast(msg, kind = 'ok') {
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.innerHTML = icon(kind === 'ok' ? 'check' : 'alert') + `<span>${esc(msg)}</span>`;
  $('toasts').appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 200); }, 3600);
}

// Every empty state names the next action, so no panel is a dead end.
const empty = (title, body, cta = '') => `<div class="empty">${icon('leaf')}`
  + `<b>${esc(title)}</b><p>${body}</p>${cta}</div>`;

const skeleton = (rows = 3) => Array.from({ length: rows }, () =>
  '<div class="skel w80"></div><div class="skel w40"></div>').join('');

function gradeClass(g) { return g >= 8 ? 'g-hi' : g >= 5 ? 'g-mid' : 'g-lo'; }
function gradeTip(g) {
  if (g >= 8) return `Grade ${g} — strong evidence: peer-reviewed guidelines and `
    + `clinical protocols.`;
  if (g >= 5) return `Grade ${g} — reasonable but not authoritative: textbooks and `
    + `reputable reviews.`;
  return `Grade ${g} — weak: podcasts, blogs or anecdote. Hidden from answers `
    + `unless a practitioner lowers the grade threshold to include it.`;
}

// Where a source came from. Only fields actually found in the text are shown; a
// blank author is left out rather than invented.
function provenance(s) {
  const seen = new Set();
  const bits = [s.author, s.published, s.origin, s.kind, s.filename]
    .filter((b) => b && b !== 'unspecified' && b !== 'pasted text')
    .filter((b) => !seen.has(b.toLowerCase()) && seen.add(b.toLowerCase()));
  const ref = s.reference ? ` · <span class="ref">${esc(s.reference)}</span>` : '';
  return `<span class="muted">${bits.map(esc).join(' · ')}</span>${ref}`;
}

/* ── Portal switch ──────────────────────────────────────────────────────── */
document.querySelectorAll('.seg button').forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll('.seg button').forEach((x) => {
      x.classList.toggle('on', x === b);
      x.setAttribute('aria-selected', x === b);
    });
    document.querySelectorAll('.pane').forEach((p) => p.classList.remove('on'));
    $('tab-' + b.dataset.tab).classList.add('on');
    if (b.dataset.tab === 'admin') loadAdmin();
  };
});

/* ── Health ─────────────────────────────────────────────────────────────── */
async function loadHealth() {
  try {
    const h = await api('/health');
    const dots = [['neo4j', 'Knowledge library'], ['anthropic', 'Clinic']]
      .map(([k, label]) => `<span class="dot ${h[k].ok ? '' : 'down'}"`
        + ` data-tip="${esc(h[k].error || label + ' reachable')}">`
        + `<i></i>${esc(label)}</span>`).join('');
    const s = h.stats;
    $('status').innerHTML = dots
      + `<span class="muted xs">${s.sources} sources · ${s.chunks} passages</span>`;
  } catch {
    $('status').innerHTML = '<span class="dot down"><i></i>server unreachable</span>';
  }
}

/* ── Source reader ──────────────────────────────────────────────────────── */
const closeReader = () => { $('reader-wrap').hidden = true; };

async function viewSource(id) {
  $('reader-wrap').hidden = false;
  $('reader').innerHTML = `<div class="pb">${skeleton(4)}</div>`;
  const s = await api(`/sources/${id}/text`);
  const meta = [
    ['Origin', s.origin], ['Author', s.author], ['Published', s.published],
    ['Reference', s.reference], ['Kind', s.kind], ['File', s.filename],
    ['Pages', s.page_count || '—'], ['Passages', s.passages.length],
    ['Characters', (s.char_count || 0).toLocaleString()], ['Grade', s.grade],
    ['Ingested', (s.created_at || '').slice(0, 16).replace('T', ' ')],
    ['Fingerprint', (s.content_hash || '').slice(0, 12)],
  ].filter(([, v]) => v || v === 0)
   .map(([k, v]) => `<tr><td>${k}</td><td>${esc(v)}</td></tr>`).join('');

  $('reader').innerHTML = `<div class="reader-head"><h3>${esc(s.title)}</h3>`
    + iconBtn('x', 'Close', 'id="reader-close"') + `</div>`
    + `<table class="meta-tbl">${meta}</table>`
    // Extraction drops tables, figures and layout, so offer the file itself.
    // Only when one was kept: pasted text and older sources have no original.
    + (s.original_name
        ? `<p class="hint"><a href="/api/sources/${s.id}/original" target="_blank"`
          + ` rel="noopener">Open the original file</a> — ${esc(s.original_name)},`
          + ` exactly as uploaded. Tables, figures and layout survive there even`
          + ` where the extracted text below lost them.</p>` : '')
    + `<div class="vine" aria-hidden="true"><span class="leaf"></span></div>`
    // The whole document first — chunks are secondary.
    + `<div class="srchead">The source in full</div>`
    + (s.body_reconstructed
        ? '<p class="hint">Ingested before the original text was kept, so this is '
          + 'reassembled from its passages — a sentence may repeat where two '
          + 'passages overlap.</p>' : '')
    + `<div class="fulltext">${esc(s.body)}</div>`
    + `<details class="disc"><summary>How Clinic split it`
    + ` (${s.passages.length} passage${s.passages.length === 1 ? '' : 's'})</summary>`
    + `<div><p class="hint">Every passage is indexed. They overlap slightly so a `
    + `claim is never cut in half.</p>`
    + s.passages.map((p) => `<div class="passage"><div class="k">`
        + `${esc(p.locator)}</div>${esc(p.text)}</div>`).join('')
    + `</div></details>`;
  $('reader-close').onclick = closeReader;
  $('reader').scrollTop = 0;
}

document.addEventListener('click', (ev) => {
  // closest(), not target: a click may land on an icon's <svg>.
  const opener = ev.target.closest?.('[data-open]');
  if (opener) { ev.stopPropagation(); viewSource(opener.dataset.open); }
  else if (ev.target.id === 'reader-wrap') closeReader();
});
document.addEventListener('keydown', (ev) => {
  if (ev.key === 'Escape') closeReader();
});

/* ── 1 · Patients ───────────────────────────────────────────────────────── */
async function loadPatients() {
  const q = new URLSearchParams({
    search: $('p-search').value, country: $('p-country').value,
  });
  const list = await api('/patients?' + q);
  const filtered = $('p-search').value || $('p-country').value;
  $('p-count').textContent = list.length || '';

  $('patient-list').innerHTML = list.length
    ? list.map((p) => `<li data-id="${p.id}" class="${p.id === selectedPatient ? 'on' : ''}"`
        + ` tabindex="0"><span class="av">${esc(initials(p.name))}</span>`
        + `<span class="grow"><span class="nm">${esc(p.name)}</span>`
        + `<span class="sub2">${esc(p.country)} · ${p.entries} entr`
        + `${p.entries === 1 ? 'y' : 'ies'} · ${p.sessions} consult`
        + `${p.sessions === 1 ? '' : 's'}</span></span>`
        + iconBtn('trash', 'Erase this patient and their whole record',
                  `data-erase="${p.id}"`, 'bare fade')
        + `</li>`).join('')
    : `<li class="plain">${filtered
        ? '<span class="muted small">No patient matches that.</span>'
        : '<span class="muted small">No patients yet — add one below.</span>'}</li>`;

  $('patient-list').querySelectorAll('li[data-id]').forEach((li) => {
    const pick = (ev) => {
      if (ev.target.closest('[data-erase]')) return;
      selectPatient(li.dataset.id);
    };
    li.onclick = pick;
    li.onkeydown = (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); pick(ev); } };
  });
  $('patient-list').querySelectorAll('[data-erase]').forEach((btn) => {
    btn.onclick = async (ev) => {
      ev.stopPropagation();
      if (btn.dataset.confirming !== '1') {
        // Two-step: the icon becomes a tick that must be clicked again.
        btn.dataset.confirming = '1';
        btn.classList.add('danger');
        btn.style.opacity = '1';
        btn.innerHTML = icon('check');
        btn.dataset.tip = 'Click again to erase permanently';
        return;
      }
      await api('/patients/' + btn.dataset.erase, { method: 'DELETE' });
      toast('Patient erased; audit detail redacted');
      if (selectedPatient === btn.dataset.erase) resetWorkspace();
      loadPatients();
    };
  });
  renderWorkspace(list.length);
}

function resetWorkspace() {
  selectedPatient = null; sessionId = null;
  $('thread').innerHTML = '';
}

function selectPatient(id) {
  selectedPatient = id; sessionId = null;
  $('thread').innerHTML = '';
  loadPatients(); loadFile(); loadSessions();
}

// The right-hand pane always tells you what to do next.
function renderWorkspace(patientCount) {
  if (selectedPatient) {
    $('composer').hidden = false;
    $('ask').disabled = false;
    $('ask-label').textContent = sessionId ? 'Follow up' : 'Ask';
    if (!$('thread').innerHTML.trim()) {
      $('thread').innerHTML = empty('Ready when you are',
        'Ask about this patient and Clinic answers from the clinic library only, '
        + 'citing every passage it used.');
    }
    return;
  }
  $('composer').hidden = true;
  $('patient-file').innerHTML = empty('No patient selected',
    'Pick someone from the list to see their record.');
  $('sessions-panel').hidden = true;
  $('thread').innerHTML = `<div class="empty">${icon('leaf')}`
    + `<b>Start a consultation</b>`
    + `<ol class="steps">`
    + `<li><span class="leaf"></span><span>${patientCount === 0
        ? 'Add a patient in the left column.' : 'Choose a patient on the left.'}</span></li>`
    + `<li><span class="leaf"></span><span>Check their labs and history.</span></li>`
    + `<li><span class="leaf"></span><span>Ask Clinic — it answers only from `
    + `graded clinic sources and cites each one.</span></li></ol></div>`;
}

$('p-search').oninput = debounce(loadPatients);
$('p-country').onchange = loadPatients;

$('p-create').onclick = async () => {
  const name = $('p-name').value.trim();
  if (!name) { toast('A name is required', 'bad'); return; }
  const p = await api('/patients', json('POST', {
    name, country: $('p-newcountry').value, dob: $('p-dob').value.trim() || null,
  }));
  $('p-name').value = $('p-dob').value = '';
  toast(`${p.name} added`);
  selectPatient(p.id);
};

/* ── 2 · Patient file ───────────────────────────────────────────────────── */
async function loadFile() {
  if (!selectedPatient) return;
  $('patient-file').innerHTML = skeleton(3);
  const p = await api('/patients/' + selectedPatient);

  const entries = p.entries.length
    ? p.entries.map((e) => `<div class="entry ${e.kind}">`
        + `<div class="k">${icon(ENTRY_ICON[e.kind] || 'note')}`
        + `<span>${esc(e.kind.replace('_', ' '))} · `
        + `${esc(e.created_at.slice(0, 10))}</span></div>`
        // A saved summary can run long; clamp it so one entry cannot push the
        // rest of the record off screen.
        + `<div class="body etext${e.content.length > 220 ? ' clamp' : ''}">`
        + `${esc(e.content)}</div></div>`).join('')
    : `<p class="hint">Nothing recorded yet. Add a lab result or a line of history `
      + `below — Clinic reads the whole file on every question.</p>`;

  $('patient-file').innerHTML = `<div class="pt-head" style="padding:0 0 .7rem">`
    + `<span class="av">${esc(initials(p.name))}</span><div class="grow">`
    + `<h3>${esc(p.name)}</h3><div class="chips">`
    + `<span class="chip">${esc(p.country)}</span>`
    + `<span class="chip">born ${esc(p.dob || '—')}</span></div></div></div>`
    + entries
    + `<details class="disc"><summary>Add to record</summary><div>`
    + `<select id="e-kind" aria-label="Entry kind">`
    + `<option value="lab">Lab result</option><option value="history">History</option>`
    + `<option value="note">Note</option></select>`
    + `<textarea id="e-content" rows="3" style="margin-top:.4rem"`
    + ` placeholder="e.g. Ferritin 11 ng/mL (ref 15–150)"></textarea>`
    + `<button id="e-add" class="btn block" style="margin-top:.4rem">Add entry</button>`
    + `</div></details>`;

  $('patient-file').querySelectorAll('.etext.clamp').forEach((el) => {
    el.title = 'Click to read in full';
    el.onclick = () => el.classList.toggle('open');
  });
  $('e-add').onclick = async () => {
    const content = $('e-content').value.trim();
    if (!content) return;
    await api(`/patients/${selectedPatient}/entries`,
      json('POST', { kind: $('e-kind').value, content }));
    toast('Added to the record');
    loadFile(); loadPatients();
  };
  renderWorkspace();
}

/* ── Consultations ──────────────────────────────────────────────────────── */
function sessionChrome() {
  $('session-tag').hidden = !sessionId;
  $('new-session').hidden = !sessionId;
  $('save-summary').hidden = !sessionId;
  if (sessionId) $('session-tag').textContent = 'consultation in progress';
  $('ask-label').textContent = sessionId ? 'Follow up' : 'Ask';
}

async function loadSessions() {
  if (!selectedPatient) { $('sessions-panel').hidden = true; return; }
  const list = await api(`/patients/${selectedPatient}/sessions`);
  $('sessions-panel').hidden = false;
  $('s-count').textContent = list.length || '';
  $('session-list').innerHTML = list.length
    ? list.map((s) => `<li data-session="${s.id}" tabindex="0"`
        + ` class="${s.id === sessionId ? 'on' : ''}">`
        + `<span class="av">${icon('summary')}</span><span class="grow">`
        + `<span class="nm" style="font-size:.84rem">${esc(s.title)}</span>`
        + `<span class="sub2">${esc(s.started_at.slice(0, 16).replace('T', ' '))} · `
        + `${s.turns} question${s.turns === 1 ? '' : 's'}</span></span></li>`).join('')
    : '<li class="plain"><span class="muted small">No consultations yet.</span></li>';
  $('session-list').querySelectorAll('[data-session]').forEach((li) => {
    const open = () => openSession(li.dataset.session);
    li.onclick = open;
    li.onkeydown = (ev) => { if (ev.key === 'Enter') open(); };
  });
  sessionChrome();
}

async function openSession(id) {
  $('thread').innerHTML = skeleton(3);
  const s = await api('/sessions/' + id);
  sessionId = id;
  $('thread').innerHTML = '';
  s.turns.forEach((t) => appendTurn(t.question, t));
  sessionChrome(); loadSessions();
  $('thread').scrollTop = $('thread').scrollHeight;
}

$('new-session').onclick = () => {
  sessionId = null;
  $('thread').innerHTML = '';
  renderWorkspace(); sessionChrome(); loadSessions();
};

/* ── 3 · Asking ─────────────────────────────────────────────────────────── */
$('min-grade').oninput = (e) => { $('grade-val').textContent = e.target.value; };
$('question').onkeydown = (ev) => {
  if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); $('ask').click(); }
};

$('ask').onclick = async () => {
  const question = $('question').value.trim();
  if (!question || !selectedPatient) return;
  if ($('thread').querySelector('.empty')) $('thread').innerHTML = '';
  $('ask').disabled = true;
  $('question').value = '';

  const pending = document.createElement('div');
  pending.className = 'turn';
  pending.innerHTML = `<div class="bubble">${icon('ask')}<span>${esc(question)}</span></div>`
    + `<div class="working"><span class="leaf"></span>`
    + `<span class="spin">Clinic is choosing which sources to open</span></div>`;
  $('thread').appendChild(pending);
  $('thread').scrollTop = $('thread').scrollHeight;

  try {
    const r = await api('/consult', json('POST', {
      patient_id: selectedPatient, question,
      min_grade: +$('min-grade').value, run_check: $('run-check').checked,
      session_id: sessionId,
    }));
    sessionId = r.session_id;
    pending.remove();
    appendTurn(question, r);
    sessionChrome(); loadSessions(); loadPatients();
  } catch (e) {
    pending.querySelector('.working').outerHTML =
      `<p class="muted small">Failed: ${esc(e.message)}</p>`;
    toast('That question could not be answered', 'bad');
  }
  $('ask').disabled = false;
  $('thread').scrollTop = $('thread').scrollHeight;
};

function appendTurn(question, r) {
  const block = document.createElement('div');
  block.className = 'turn';
  const q = `<div class="bubble">${icon('ask')}<span>${esc(question)}</span></div>`;

  if (!r.matched) {
    block.innerHTML = q + '<div class="nomatch"><b>Nothing in the library matches '
      + `this question.</b><div class="answer">${esc(r.answer)}</div></div>`;
    $('thread').appendChild(block);
    return;
  }

  // Escaped first, so rendering the Specialist's light markdown cannot inject.
  const answer = esc(r.answer)
    .replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>')
    .replace(/(^|[\s(])\*([^*\n]+)\*/g, '$1<i>$2</i>')
    .replace(/\[S(\d+)\]/g, (_, n) => `<span class="cite" data-s="${n}">[S${n}]</span>`);

  const check = r.check ? `<div class="checkline">`
    + `<span class="badge ${r.check.verdict}">`
    + icon(r.check.verdict === 'pass' ? 'shield' : 'alert')
    + `<span>${r.check.verdict === 'pass'
        ? 'verified against its sources' : 'needs review'}</span></span> `
    + `<span class="muted xs">${esc(r.check.note)}</span>`
    + (r.check.unsupported?.length
        ? `<ul class="muted xs">${r.check.unsupported.map((u) =>
            `<li>${esc(u)}</li>`).join('')}</ul>` : '')
    + `</div>` : '';

  // How each passage was reached. Anything not directly opened is marked, with
  // the concepts that connected it, so a clinician can see why it is here.
  const VIA = {
    match: ['on point', 'Matched the concepts behind this question, wherever it sits '
            + 'in the document'],
    adjacent: ['continues', 'The passage next to a match, so a claim split across a '
               + 'boundary keeps its context'],
    linked: ['linked', 'From a source Clinic did not open — the library connects it '
             + 'by shared subject'],
  };
  const sources = (r.sources || []).map((s) => {
    const v = VIA[s.via];
    const tip = v ? v[1] + (s.shared?.length ? `: ${s.shared.join(', ')}` : '') : '';
    return `<div class="source ${s.via === 'linked' ? 'via-linked' : ''}"`
    + ` data-s="${s.label.slice(1)}">`
    + `<div class="head"><span class="lab">${s.label}</span>`
    + `<b>${esc(s.title)}</b>`
    + `<span class="grade ${gradeClass(s.grade)}" data-tip="${esc(gradeTip(s.grade))}">`
    + `grade ${s.grade}</span><span class="loc">${esc(s.locator)}</span>`
    + (v ? `<span class="viatag ${s.via}" data-tip="${esc(tip)}">${v[0]}</span>` : '')
    + `</div>`
    + `<div class="prov">${provenance(s)}`
    + iconBtn('open', 'Open this source in full', `data-open="${s.source_id}"`, 'bare')
    + `</div><div class="snip">${esc(s.snippet)}</div></div>`;
  }).join('');

  const tv = r.traversal || {};
  const walk = tv.available ? `<p class="muted xs">Walked the library: `
    + [tv.match && `${tv.match} on point`, tv.adjacent && `${tv.adjacent} adjoining`,
       tv.linked && `${tv.linked} linked from other sources`,
       tv.opened && `${tv.opened} more from the opened sources`]
      .filter(Boolean).join(' · ')
    + `.${(tv.focus || []).length ? ` Looked for: ${esc(tv.focus.join(', '))}.` : ''}`
    + `</p>` : '';

  const lib = r.librarian || {};
  const opened = (lib.opened || []).map((o) =>
    `<li>${esc(o.title)} <span class="grade ${gradeClass(o.grade)}">grade ${o.grade}`
    + `</span></li>`).join('') || '<li>nothing</li>';

  block.innerHTML = q + check + `<div class="answer">${answer}</div>`
    + (sources ? `<div class="srchead">Sources behind this answer</div>${sources}` : '')
    + `<details class="disc"><summary>How Clinic chose</summary><div>`
    + `<p class="muted small">${esc(lib.reasoning || '')}</p>`
    + `<p class="muted xs">Opened:</p><ul class="muted xs">${opened}</ul>`
    + walk
    + `<p class="muted xs">${lib.considered ?? 0} source(s) were available at grade `
    + `≥ ${r.min_grade}.`
    + (lib.truncated ? ` <b>${lib.truncated} further passage(s) were left out by the `
        + `passage limit.</b>` : '') + `</p></div></details>`;
  $('thread').appendChild(block);

  const focus = (n) => block.querySelectorAll('.source').forEach((el) => {
    const on = el.dataset.s === n;
    el.classList.toggle('hi', on);
    el.classList.toggle('open', on);
    if (on) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });
  block.querySelectorAll('.cite').forEach((c) => { c.onclick = () => focus(c.dataset.s); });
  block.querySelectorAll('.source').forEach((s) => {
    s.onclick = (ev) => { if (!ev.target.closest('[data-open]')) s.classList.toggle('open'); };
  });
}

$('save-summary').onclick = async () => {
  if (!sessionId) return;
  const btn = $('save-summary');
  const label = btn.querySelector('span');
  btn.disabled = true; label.textContent = 'Saving…';
  await api(`/patients/${selectedPatient}/summary`, json('POST', { session_id: sessionId }));
  label.textContent = 'Saved';
  toast('Summary written into the patient record');
  loadFile();
  await wait(1600);
  btn.disabled = false; label.textContent = 'Save to record';
};

/* ── Admin 1 · dropzone with preview ────────────────────────────────────── */
const dz = $('dropzone');
let chosenFile = null;

function showPreview(file) {
  chosenFile = file;
  const box = $('preview');
  box.hidden = false;
  const isPdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name);
  box.innerHTML = `<div class="pv-head"><span class="pv-icon">${isPdf ? 'PDF' : 'TXT'}`
    + `</span><span class="pv-name"><b>${esc(file.name)}</b><br>`
    + `<span class="muted xs">${humanSize(file.size)}</span></span>`
    + iconBtn('x', 'Remove this file', 'id="pv-clear"') + `</div><div id="pv-body"></div>`;
  $('pv-clear').onclick = clearPreview;

  if (isPdf) {
    // Browsers render PDFs natively, so the first page is a real preview.
    const url = URL.createObjectURL(file);
    $('pv-body').innerHTML = `<object data="${url}#page=1&view=FitH"`
      + ` type="application/pdf" class="pv-pdf"><p class="muted xs">No preview in `
      + `this browser — the file will still ingest.</p></object>`;
  } else {
    file.slice(0, 4000).text().then((t) => {
      $('pv-body').innerHTML = `<pre class="pv-text">${esc(t.slice(0, 1400))}`
        + `${t.length > 1400 ? '\n…' : ''}</pre>`;
    });
  }
}
function clearPreview() {
  chosenFile = null; $('s-file').value = '';
  $('preview').hidden = true; $('preview').innerHTML = '';
}

dz.onclick = () => $('s-file').click();
dz.onkeydown = (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); $('s-file').click(); } };
$('s-file').onchange = (e) => { if (e.target.files[0]) showPreview(e.target.files[0]); };
['dragenter', 'dragover'].forEach((n) => dz.addEventListener(n, (e) => {
  e.preventDefault(); dz.classList.add('over');
}));
['dragleave', 'drop'].forEach((n) => dz.addEventListener(n, (e) => {
  e.preventDefault(); dz.classList.remove('over');
}));
dz.addEventListener('drop', (e) => { if (e.dataTransfer.files[0]) showPreview(e.dataTransfer.files[0]); });

async function ingest(replaces = '') {
  if (!chosenFile && !$('s-text').value.trim()) {
    toast('Add a file or paste some text first', 'bad'); return;
  }
  const form = new FormData();
  if (chosenFile) form.append('file', chosenFile);
  form.append('text', $('s-text').value);
  form.append('kind', $('s-kind').value);
  form.append('origin', $('s-origin').value || 'unspecified');
  if (replaces) form.append('replaces', replaces);

  $('s-ingest').disabled = true;
  $('ingest-status').innerHTML = `<span class="working"><span class="leaf"></span>`
    + `<span class="spin">${replaces ? 'Replacing the existing source'
        : 'Clinic is reading, tagging and grading'}</span></span>`;
  try {
    const src = await api('/sources', { method: 'POST', body: form });
    $('ingest-status').textContent = '';
    toast(`${replaces ? 'Replaced with' : 'Added'} “${src.title}” — `
      + `${src.chunks} passages, grade ${src.grade}`);
    clearPreview(); $('s-text').value = '';
    libPage = 1; loadAdmin(); loadHealth();
  } catch (e) {
    if (e.status === 409 && e.detail?.duplicate_of) {
      // Keep the upload in the form so one click can supersede the old copy.
      $('ingest-status').innerHTML = `<span class="muted xs">${esc(e.message)}</span> `
        + `<button id="s-replace" class="btn ghost sm" style="margin-top:.4rem">`
        + `Replace it with this upload</button>`;
      $('s-replace').onclick = () => ingest(e.detail.duplicate_of);
    } else {
      $('ingest-status').textContent = '';
      toast(e.message, 'bad');
    }
  }
  $('s-ingest').disabled = false;
}
$('s-ingest').onclick = () => ingest();

/* ── Admin 2 · library ──────────────────────────────────────────────────── */
const libQuery = () => {
  const [lo, hi] = $('l-grade').value.split('-');
  return new URLSearchParams({
    search: $('l-search').value, topic: $('l-topic').value, kind: $('l-kind').value,
    min_grade: lo, max_grade: hi, sort: $('l-sort').value,
    page: libPage, per_page: 5,
  });
};
['l-topic', 'l-kind', 'l-grade', 'l-sort'].forEach((id) => {
  $(id).onchange = () => { libPage = 1; loadLibrary(); };
});
$('l-search').oninput = debounce(() => { libPage = 1; loadLibrary(); });
$('l-reset').onclick = () => {
  $('l-search').value = ''; $('l-topic').value = ''; $('l-kind').value = '';
  $('l-grade').value = '1-10'; $('l-sort').value = 'newest';
  libPage = 1; loadLibrary();
};

async function loadLibrary() {
  const data = await api('/sources?' + libQuery());
  const filtered = $('l-search').value || $('l-topic').value || $('l-kind').value
    || $('l-grade').value !== '1-10';
  $('lib-count').textContent = data.total
    ? `${data.total}${filtered ? ' matching' : ''}` : '';

  $('source-list').innerHTML = data.sources.length
    ? data.sources.map((s) => {
        const size = [s.page_count ? `${s.page_count} pages` : null,
          `${s.chunks} passages`,
          s.char_count ? `${(s.char_count / 1000).toFixed(1)}k chars` : null,
        ].filter(Boolean).join(' · ');
        return `<div class="src" data-id="${s.id}">`
          + `<h3><span class="ki" data-tip="${esc(s.kind)}">`
          + `${icon(KIND_ICON[s.kind] || 'article')}</span>`
          + `<span class="grow">${esc(s.title)}</span>`
          + `<span class="grade ${gradeClass(s.grade)}">${s.grade}</span></h3>`
          + `<div class="meta">${provenance(s)}</div>`
          + `<div class="meta">${size} · ingested `
          + `${esc((s.created_at || '').slice(0, 10))}</div>`
          + `<div class="sum">${esc(s.summary)}</div>`
          + `<div class="topics">${s.topics.map((t) =>
              `<span class="topic">${esc(t)}</span>`).join('')}</div>`
          + `<div class="srcfoot"><span class="muted xs">grade</span>`
          + `<input type="range" min="1" max="10" value="${s.grade}"`
          + ` aria-label="Reliability grade"`
          + ` data-tip="Drag to overrule Clinic's suggestion">`
          + `<span class="grade ${gradeClass(s.grade)} gv">${s.grade}</span>`
          + iconBtn('info', 'Metadata and passage breakdown', `data-open="${s.id}"`)
          + iconBtn('trash', 'Remove from the library', 'data-del="1"', 'danger')
          + `</div><div class="gradehint">${esc(gradeTip(s.grade))}</div>`
          + `<details class="disc"><summary>Read it in full</summary>`
          + `<div class="inline-src"><div class="skel w80"></div></div></details>`
          + `<div class="confirm" hidden></div></div>`;
      }).join('')
    : (filtered
        ? empty('Nothing matches', 'Try a different word, or clear the filters.',
                '<button class="btn ghost sm" id="empty-clear">Clear filters</button>')
        : empty('The library is empty',
                'Clinic can only answer from sources you give it. Add the first one '
                + 'on the left.'));
  if ($('empty-clear')) $('empty-clear').onclick = () => $('l-reset').click();

  $('source-list').querySelectorAll('.src').forEach((card) => {
    const id = card.dataset.id;
    const src = data.sources.find((s) => s.id === id);
    const range = card.querySelector('input[type=range]');
    const pill = card.querySelector('.gv');
    range.oninput = () => {
      pill.textContent = range.value;
      pill.className = `grade ${gradeClass(+range.value)} gv`;
      card.querySelector('.gradehint').textContent = gradeTip(+range.value);
    };
    range.onchange = async () => {
      await api('/sources/' + id, json('PATCH', { grade: +range.value }));
      toast(`“${src.title.slice(0, 40)}” set to grade ${range.value}`);
      loadLibrary();
    };
    // Read the whole source inline, not only in the overlay.
    const details = card.querySelector('details');
    details.ontoggle = async () => {
      const box = details.querySelector('.inline-src');
      if (!details.open || box.dataset.loaded) return;
      const full = await api(`/sources/${id}/text`);
      box.dataset.loaded = '1';
      box.innerHTML = `<div class="fulltext">${esc(full.body)}</div>`;
    };
    // Deleting drops the passages too, so make it two steps.
    const confirm = card.querySelector('.confirm');
    card.querySelector('[data-del]').onclick = () => {
      confirm.hidden = false;
      confirm.innerHTML = `<span class="muted xs">Remove “${esc(src.title)}” and its `
        + `${src.chunks} passage(s)? Answers will stop citing it.</span>`
        + `<button class="btn danger sm yes">Remove</button>`
        + `<button class="btn ghost sm no">Keep</button>`;
      confirm.querySelector('.no').onclick = () => { confirm.hidden = true; };
      confirm.querySelector('.yes').onclick = async () => {
        await api('/sources/' + id, { method: 'DELETE' });
        toast('Source removed from the library');
        closeReader();
        if (data.sources.length === 1 && libPage > 1) libPage -= 1;
        loadAdmin(); loadHealth();
      };
    };
  });

  $('lib-pager').innerHTML = data.pages > 1
    ? `<button class="btn ghost sm" ${data.page <= 1 ? 'disabled' : ''} id="pg-prev">`
      + `‹ previous</button><span class="muted xs">page ${data.page} of ${data.pages}`
      + `</span><button class="btn ghost sm" ${data.page >= data.pages ? 'disabled' : ''}`
      + ` id="pg-next">next ›</button>` : '';
  if ($('pg-prev')) $('pg-prev').onclick = () => { libPage -= 1; loadLibrary(); };
  if ($('pg-next')) $('pg-next').onclick = () => { libPage += 1; loadLibrary(); };
}

async function loadFacets() {
  const f = await api('/facets');
  const fill = (sel, values, label) => {
    const current = sel.value;
    sel.innerHTML = `<option value="">${label}</option>`
      + values.map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
    sel.value = values.includes(current) ? current : '';
  };
  fill($('l-topic'), f.topics, 'All topics');
  fill($('l-kind'), f.kinds, 'All kinds');
}

/* ── Admin 3 · coverage + audit ─────────────────────────────────────────── */
async function loadCoverage() {
  const cov = await api('/coverage');
  const max = Math.max(1, ...cov.map((c) => c.chunks));
  $('coverage').innerHTML = cov.length
    ? cov.map((c) => `<tr><td>${esc(c.topic)}`
        + `<div class="bar"><i style="width:${(c.chunks / max) * 100}%"></i></div></td>`
        + `<td>${c.sources} src</td><td>${c.chunks} psg</td></tr>`).join('')
    : `<tr><td class="muted small">Nothing indexed yet.</td></tr>`;
}

async function loadAudit() {
  const log = await api('/audit');
  $('audit').innerHTML = log.map((e) => {
    const vault = e.vault === 'patient'
      ? '<span class="vault pt" data-tip="Stored in the SQLite patient vault — it '
        + 'names a patient or quotes a clinical question, so it never enters the '
        + 'knowledge library">patient vault</span>'
      : '<span class="vault lib" data-tip="Stored in the Neo4j knowledge library — '
        + 'contains no patient data">library</span>';
    return `<li><div class="top"><span class="act">${esc(e.action)}</span>${vault}</div>`
      + `<div class="det">${esc(e.detail)}</div>`
      + `<div class="who">${esc(e.actor)} · `
      + `${esc(e.ts.slice(0, 16).replace('T', ' '))}</div></li>`;
  }).join('') || '<li><span class="muted small">No activity yet.</span></li>';
}

async function loadGraph() {
  const g = await api('/graph');
  $('graph-stats').innerHTML = [
    ['Concepts', g.concepts, 'Distinct subjects the library knows about'],
    ['Passage links', g.mentions, 'Passage-to-concept edges'],
    ['Reading order', g.order_edges, 'Edges joining a passage to the next one'],
    ['Connected sources', g.source_links, 'Pairs of sources that share a subject'],
  ].map(([k, v, tip]) => `<tr><td data-tip="${esc(tip)}">${k}</td>`
    + `<td>${v}</td></tr>`).join('');

  const unlinked = g.unlinked.length;
  $('graph-actions').innerHTML =
    (unlinked ? `<button class="btn ghost sm block" id="g-relink">`
      + `Link ${unlinked} unlinked source${unlinked === 1 ? '' : 's'}</button>` : '')
    + `<button class="btn ghost sm block" id="g-tidy" style="margin-top:.4rem">`
    + `Tidy the index</button>`;
  $('graph-note').innerHTML = unlinked
    ? `<b>${unlinked}</b> source${unlinked === 1 ? ' is' : 's are'} not connected yet `
      + `— Clinic can only use ${unlinked === 1 ? 'it' : 'them'} when it opens `
      + `${unlinked === 1 ? 'it' : 'them'} directly.`
    : 'Every source is connected into the graph.';

  if ($('g-relink')) $('g-relink').onclick = async (ev) => {
    ev.target.disabled = true; ev.target.textContent = 'Reading and linking…';
    const r = await api('/relink', { method: 'POST' });
    toast(`Linked ${r.linked.length} source(s) — ${r.source_links} connected pairs`);
    loadGraph(); loadAdmin();
  };
  $('g-tidy').onclick = async (ev) => {
    ev.target.disabled = true; ev.target.textContent = 'Tidying…';
    const r = await api('/consolidate', { method: 'POST' });
    const merged = [...r.concept.groups, ...r.topic.groups];
    toast(merged.length
      ? `Merged ${merged.map((m) => m.canonical).join(', ')}`
      : 'The index is already tidy — nothing to merge');
    loadGraph(); loadAdmin();
  };
}

const loadAdmin = () => Promise.all([loadFacets(), loadLibrary(), loadCoverage(),
                                     loadAudit(), loadGraph()]);

/* ── Boot ───────────────────────────────────────────────────────────────── */
loadHealth();
loadPatients();
setInterval(loadHealth, 60000);
