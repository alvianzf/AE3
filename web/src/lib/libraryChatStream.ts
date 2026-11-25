// Client-side SSE reader for POST /api/me/library-chat — "Ask the Library"
// (the dashboard's no-client knowledge-library chat). Same manual
// fetch()-ReadableStream parsing as consultStream.ts, since EventSource
// can't send a POST body; kept as its own module rather than generalizing
// consultStream.ts because the request/result shapes genuinely differ
// (no client_id, no session_id, a different persisted-turn shape).
import { PUBLIC_API_BASE } from '$env/static/public';

export type LibraryChatEvent =
	| { event: 'agent_start'; agent: string }
	| {
			event: 'agent_progress';
			agent: string;
			hop: number;
			max_depth: number;
			candidates: number;
			relevant: number;
			accumulated: number;
			duration_s: number;
	  }
	| { event: 'agent_done'; agent: string; input_tokens: number; output_tokens: number; duration_s: number }
	| { event: 'answer_delta'; text: string }
	| {
			event: 'result';
			id: string;
			question: string;
			answer: string;
			check: { verdict: string; unsupported?: string[] } | null;
			sources: unknown[];
			searched: unknown[];
			total_input_tokens: number;
			total_output_tokens: number;
			step_times: Record<string, number>;
			total_time_s: number;
			retrieval_mode: string;
	  }
	| { event: 'error'; message: string };

export type LibraryRetrievalMode = 'deep_research' | 'general_lookup';

export async function* streamLibraryChat(
	question: string,
	retrievalMode: LibraryRetrievalMode = 'general_lookup',
	signal?: AbortSignal,
	folder = '',
	topic = ''
): AsyncGenerator<LibraryChatEvent> {
	const res = await fetch(`${PUBLIC_API_BASE}/api/me/library-chat`, {
		method: 'POST',
		credentials: 'include',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			question,
			retrieval_mode: retrievalMode,
			folder: folder || undefined,
			topic: topic || undefined
		}),
		signal
	});
	if (!res.ok || !res.body) {
		const body = await res.json().catch(() => ({}));
		throw new Error(body?.detail?.message || body?.detail || res.statusText);
	}
	const reader = res.body.getReader();
	const decoder = new TextDecoder();
	let buf = '';
	for (;;) {
		const { value, done } = await reader.read();
		if (done) break;
		buf += decoder.decode(value, { stream: true });
		let idx: number;
		while ((idx = buf.indexOf('\n\n')) !== -1) {
			const frame = buf.slice(0, idx);
			buf = buf.slice(idx + 2);
			const line = frame.split('\n').find((l) => l.startsWith('data: '));
			if (!line) continue;
			try {
				yield JSON.parse(line.slice(6)) as LibraryChatEvent;
			} catch {
				/* skip malformed frame */
			}
		}
	}
}
