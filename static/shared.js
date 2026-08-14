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
