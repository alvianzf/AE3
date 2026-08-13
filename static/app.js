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

/* ── Admins (superadmin only) ───────────────────────────────────────────── */
function adminRow(a) {
  const you = a.you ? ' <span class="muted xs">(you)</span>' : '';
  const chip = `<span class="chip">${esc(a.role)}</span>`
    + (a.is_active ? '' : ' <span class="chip">suspended</span>');
  return `<li data-id="${a.id}" class="plain" style="display:block">
    <div style="display:flex;justify-content:space-between;gap:.5rem;align-items:baseline;flex-wrap:wrap">
      <span class="nm">${esc(a.name)}${you} <span class="muted xs">${esc(a.email)}</span></span>
      ${chip}
    </div>
    <div style="display:flex;gap:.4rem;margin-top:.3rem">
      <button class="btn ghost sm" data-role="${a.role === 'superadmin' ? 'admin' : 'superadmin'}">
        ${a.role === 'superadmin' ? 'Demote to admin' : 'Promote to superadmin'}</button>
      <button class="btn ghost sm" data-toggle="${a.is_active ? '0' : '1'}">
        ${a.is_active ? 'Suspend' : 'Reactivate'}</button>
    </div>
  </li>`;
}

async function loadAdmins(currentId) {
  const list = await api('/superadmin/admins');
  list.forEach((a) => { a.you = a.id === currentId; });
  $('admins-list').innerHTML = `<ul class="rows">${list.map(adminRow).join('')}</ul>`;
  $('admins-list').querySelectorAll('[data-role]').forEach((btn) => {
    btn.onclick = async () => {
      const id = btn.closest('li').dataset.id;
      try {
        await api(`/superadmin/admins/${id}/role`, json('PUT', { role: btn.dataset.role }));
        toast('Role updated'); loadAdmins(currentId);
      } catch (e) { toast(e.message, 'bad'); }
    };
  });
  $('admins-list').querySelectorAll('[data-toggle]').forEach((btn) => {
    btn.onclick = async () => {
      const id = btn.closest('li').dataset.id;
      const action = btn.dataset.toggle === '1' ? 'reactivate' : 'suspend';
      try {
        await api(`/superadmin/admins/${id}/${action}`, { method: 'POST' });
        toast(action === 'suspend' ? 'Admin suspended' : 'Admin reactivated');
        loadAdmins(currentId);
      } catch (e) { toast(e.message, 'bad'); }
    };
  });
}

$('na-create').onclick = async () => {
  const name = $('na-name').value.trim();
  const email = $('na-email').value.trim();
  const password = $('na-password').value;
  const role = $('na-role').value;
  if (!name || !email || !password) { toast('Name, email and password are required', 'bad'); return; }
  try {
    await api('/superadmin/admins', json('POST', { name, email, password, role }));
    $('na-name').value = ''; $('na-email').value = ''; $('na-password').value = '';
    toast('Admin created');
    const session = await api('/auth/me');
    loadAdmins(session.id);
  } catch (e) { toast(e.message, 'bad'); }
};

async function initAdminsPanel() {
  try {
    const session = await api('/auth/me');
    if (session.admin_role !== 'superadmin') return;
    $('admins-panel').hidden = false;
    loadAdmins(session.id);
  } catch { /* not logged in yet — health/login gating handles that elsewhere */ }
}

$('logout-btn').onclick = async () => {
  await api('/auth/logout', { method: 'POST' }).catch(() => {});
  location.href = '/login';
};

/* ── Boot ───────────────────────────────────────────────────────────────── */
loadHealth();
loadAdmin();
initAdminsPanel();
setInterval(loadHealth, 60000);
