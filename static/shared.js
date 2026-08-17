/* Clinic — shared front-end helpers for static/public, static/practitioner and
   static/client. Same fetch-call style as static/app.js: plain fetch(), no
   framework. Kept small on purpose — pull a helper in here only once it is
   copy-pasted a third time across pages. */

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const qs = (name) => new URLSearchParams(location.search).get(name);

async function api(path, opts = {}) {
  const res = await fetch('/api' + path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const d = body.detail;
    const err = new Error((d && typeof d === 'object' ? d.message : d) || res.statusText);
    err.detail = d; err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json().catch(() => null);
}
const json = (method, body) => ({
  method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
});

// Same icon set/shape as app.js, trimmed to what these pages need.
const ICONS = {
  check: '<path d="M4 12l5 5L20 6"/>',
  alert: '<path d="M12 4l9 16H3zM12 10v4M12 17h.01"/>',
  leaf: '<path d="M12 22V8"/><path d="M12 15c0-4 3-7 8-8-.4 4.4-3.2 7.4-8 8z"/><path d="M12 11c0-4-3-7-8-8 .4 4.4 3.2 7.4 8 8z"/>',
};
const icon = (n) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"`
  + ` stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"`
  + ` aria-hidden="true">${ICONS[n]}</svg>`;

function toast(msg, kind = 'ok') {
  let box = $('toasts');
  if (!box) {
    box = document.createElement('div');
    box.id = 'toasts'; box.className = 'toasts'; box.setAttribute('aria-live', 'polite');
    document.body.appendChild(box);
  }
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.innerHTML = icon(kind === 'ok' ? 'check' : 'alert') + `<span>${esc(msg)}</span>`;
  box.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 200); }, 3600);
}

const empty = (title, body, cta = '') => `<div class="empty">${icon('leaf')}`
  + `<b>${esc(title)}</b><p>${body}</p>${cta}</div>`;

// Live agent-progress toast (specs/v3/15-design-system.md#live-agent-toast).
// Separate from toast() above: this one stays up for the life of a request
// instead of auto-dismissing, since it's reporting an in-progress state, not
// a completed action. A stopgap element (not an md-snackbar yet) until the
// MD3 migration lands — same content contract either way.
const AGENT_LABELS = {
  librarian: 'Librarian is choosing sources',
  specialist: 'Specialist is drafting an answer',
  checker: 'Checker is verifying citations',
};
function agentToast() {
  const el = document.createElement('div');
  el.className = 'toast ok agent-toast';
  el.innerHTML = `<span class="agent-line">Starting…</span>`;
  ($('toasts') || (() => {
    const box = document.createElement('div');
    box.id = 'toasts'; box.className = 'toasts'; box.setAttribute('aria-live', 'polite');
    document.body.appendChild(box);
    return box;
  })()).appendChild(el);
  const line = el.querySelector('.agent-line');
  let tokens = 0;
  return {
    update(evt) {
      if (evt.event === 'agent_start') {
        const label = AGENT_LABELS[evt.agent] || evt.agent;
        line.textContent = evt.retry
          ? `Checker flagged part of the answer — Specialist is revising…`
          : `${label}…`;
      } else if (evt.event === 'agent_done') {
        tokens += (evt.input_tokens || 0) + (evt.output_tokens || 0);
        line.textContent += ` (${tokens} tokens so far)`;
      }
    },
    remove() { el.remove(); },
  };
}

// Reads a POST-with-body SSE stream (fetch, not EventSource — EventSource
// cannot send a request body). Calls onEvent for each parsed `data:` line.
async function postSSE(path, body, onEvent) {
  const res = await fetch('/api' + path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    const d = errBody.detail;
    const err = new Error((d && typeof d === 'object' ? d.message : d) || res.statusText);
    err.status = res.status;
    throw err;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop();
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      onEvent(JSON.parse(line.slice(6)));
    }
  }
}

// Session helper: resolves to {role, id} or null. Used by portal pages to
// redirect to login when there is no valid cookie.
async function currentSession() {
  try { return await api('/auth/me'); } catch { return null; }
}
async function requireRole(role) {
  const s = await currentSession();
  if (!s || s.role !== role) { location.href = '/login'; return null; }
  return s;
}
async function logout() {
  await api('/auth/logout', { method: 'POST' }).catch(() => {});
  location.href = '/login';
}

// User menu: a single icon+chevron button in the topbar that opens a small
// dropdown (Account, Log out) instead of showing both as separate buttons.
// Delegated on document so it works regardless of when #user-menu-btn is
// added to the page.
document.addEventListener('click', (ev) => {
  const btn = ev.target.closest('#user-menu-btn');
  const menu = $('user-menu');
  if (btn && menu) {
    ev.stopPropagation();
    const opening = menu.hidden;
    menu.hidden = !opening;
    btn.setAttribute('aria-expanded', String(opening));
    return;
  }
  if (menu && !menu.hidden && !ev.target.closest('#user-menu')) {
    menu.hidden = true;
    $('user-menu-btn')?.setAttribute('aria-expanded', 'false');
  }
});
document.addEventListener('keydown', (ev) => {
  if (ev.key !== 'Escape') return;
  const menu = $('user-menu');
  if (menu && !menu.hidden) {
    menu.hidden = true;
    $('user-menu-btn')?.setAttribute('aria-expanded', 'false');
  }
});

// Show/hide toggle on every password field, site-wide — wraps each
// input[type=password] in a positioning container and adds an eye button
// that flips it to type=text. Fully automatic: no per-page markup or call
// needed, just shared.js being loaded (every page already does).
function wirePasswordToggles() {
  document.querySelectorAll('input[type="password"]').forEach((input) => {
    if (input.closest('.pw-wrap')) return; // already wired
    const wrap = document.createElement('div');
    wrap.className = 'pw-wrap';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'pw-toggle';
    btn.setAttribute('aria-label', 'Show password');
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"'
      + ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
      + '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>';
    wrap.appendChild(btn);

    btn.onclick = () => {
      const showing = input.type === 'text';
      input.type = showing ? 'password' : 'text';
      btn.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
      btn.innerHTML = showing
        ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"'
          + ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
          + '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>'
        : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"'
          + ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
          + '<path d="M17.9 17.9A10.4 10.4 0 0 1 12 19c-6.5 0-10-7-10-7a18.4 18.4 0 0 1 4.2-5.2M9.9 4.2A9.8 9.8 0 0 1 12 4c6.5 0 10 7 10 7a18.5 18.5 0 0 1-2.2 3.1M14.1 14.1a3 3 0 1 1-4.2-4.2"/>'
          + '<path d="M2 2l20 20"/></svg>';
    };
  });
}
document.addEventListener('DOMContentLoaded', wirePasswordToggles);
// Some pages render their password fields after DOMContentLoaded already
// fired (async load()), so also expose this for pages that build a field
// dynamically — call it again after inserting new markup.

// Public pages (directory, about, coach, both signup flows) show
// "Sign up"/"Log in" links unconditionally in their markup — fine for a
// signed-out visitor, misleading for someone already signed in who
// navigated back here (specs/v2/14-ux-findings-v2.7.md S1). Pages that
// want this handled mark their links with data-auth-link="signup"/"login"
// and call this once on load; a session swaps the first such link for a
// single "Go to my dashboard" link and removes the rest.
const DASHBOARD_FOR_ROLE = {
  admin: '/admin/dashboard', practitioner: '/practitioner/dashboard', client: '/client/dashboard',
};
// Small numeric badge on a sidebar-nav link (e.g. "Contacts (3)") for
// counts the signed-in user hasn't looked at yet. Call once per page load
// per role — see loadAdminNotifications()/loadPractitionerNotifications().
function setNavBadge(href, count) {
  const link = document.querySelector(`.sidebar-link[href="${href}"]`);
  if (!link) return;
  link.querySelector('.nav-badge')?.remove();
  if (!count) return;
  const badge = document.createElement('span');
  badge.className = 'nav-badge';
  badge.textContent = count > 99 ? '99+' : String(count);
  link.appendChild(badge);
}
async function loadAdminNotifications() {
  try {
    const n = await api('/admin/notifications');
    setNavBadge('/admin/users', n.pending_practitioners);
  } catch { /* not fatal — the page still works without badges */ }
}
async function loadPractitionerNotifications() {
  try {
    const n = await api('/me/notifications');
    setNavBadge('/practitioner/contacts', n.new_contacts);
    setNavBadge('/practitioner/dashboard', n.new_contacts + n.unviewed_intake);
  } catch { /* not fatal — the page still works without badges */ }
}

async function adaptPublicAuthLinks() {
  const session = await currentSession();
  if (!session) return;
  const links = document.querySelectorAll('[data-auth-link]');
  links.forEach((el, i) => {
    if (i === 0) {
      el.textContent = 'Go to my dashboard';
      el.href = DASHBOARD_FOR_ROLE[session.role] || '/login';
      el.classList.remove('ghost');
    } else {
      el.remove();
    }
  });
}
