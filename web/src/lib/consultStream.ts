// Client-side SSE reader for POST /api/me/consult (specs/v3/08-api.md#live-progress-stream).
// EventSource can't send a POST body, so this reads the fetch() ReadableStream
// directly and parses `data: {...}\n\n` frames.
import { PUBLIC_API_BASE } from '$env/static/public';

export type ConsultEvent =
	| { event: 'agent_start'; agent: string }
	| { event: 'agent_done'; agent: string; input_tokens: number; output_tokens: number }
	| {
			event: 'result';
			answer: string;
			verdict: string;
			revised: boolean;
			sources: unknown[];
			reasoning: string;
			total_input_tokens: number;
			total_output_tokens: number;
	  }
	| { event: 'error'; message: string };

export async function* streamConsult(
	clientId: string,
	question: string
): AsyncGenerator<ConsultEvent> {
	const res = await fetch(`${PUBLIC_API_BASE}/api/me/consult`, {
		method: 'POST',
		credentials: 'include',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ client_id: clientId, question })
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
				yield JSON.parse(line.slice(6)) as ConsultEvent;
			} catch {
				/* skip malformed frame */
			}
		}
	}
}
