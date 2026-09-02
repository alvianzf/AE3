import { writable } from 'svelte/store';

export type ToastKind = 'ok' | 'alert';
export interface Toast { id: number; msg: string; kind: ToastKind }

export const toasts = writable<Toast[]>([]);
let seq = 0;

export function toast(msg: string, kind: ToastKind = 'ok') {
	const id = ++seq;
	toasts.update((t) => [...t, { id, msg, kind }]);
	setTimeout(() => toasts.update((t) => t.filter((x) => x.id !== id)), 4200);
}
