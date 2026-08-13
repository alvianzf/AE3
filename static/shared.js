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

// Session helper: resolves to {role, id} or null. Used by portal pages to
// redirect to login when there is no valid cookie.
async function currentSession() {
  try { return await api('/auth/me'); } catch { return null; }
}
async function requireRole(role) {
  const s = await currentSession();
  if (!s || s.role !== role) { location.href = '/static/public/login.html'; return null; }
  return s;
}
async function logout() {
  await api('/auth/logout', { method: 'POST' }).catch(() => {});
  location.href = '/static/public/login.html';
}
