// Shared session helpers — the public nav needs to know if a visitor is
// already logged in (real bug: it never checked, always showed "Log
// in"/"Get started" even to an authenticated user, which read as "why do
// I need to re-login").
import { get } from './api';

export const LANDING: Record<string, string> = {
	admin: '/admin/dashboard',
	practitioner: '/practitioner/dashboard',
	client: '/client/dashboard'
};

export async function currentSession(fetchFn: typeof fetch = fetch) {
	try {
		return await get(fetchFn, '/auth/me');
	} catch {
		return null;
	}
}
