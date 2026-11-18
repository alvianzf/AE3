// Client-side SSE reader for POST .../documents/{kind}/draft — same shape
// as consultStream.ts's streamConsult (manual ReadableStream parsing, not
// EventSource, since EventSource can't send a POST body).
import { PUBLIC_API_BASE } from '$env/static/public';

export type DocumentDraftEvent =
	| { event: 'agent_start'; agent: string }
	| { event: 'agent_done'; agent: string; input_tokens: number; output_tokens: number; duration_s: number }
	| {
			event: 'result';
			text: string;
			check: { verdict: string; unsupported?: string[] } | null;
			sources: { label: string; document_id: string | null; title: string; snippet: string; locator: string; kind: string }[];
	  }
	| { event: 'error'; message: string };

export async function* streamDocumentDraft(
	clientId: string,
	sessionId: string,
	kind: 'clinician_note' | 'client_report',
	instruction?: string,
	signal?: AbortSignal
): AsyncGenerator<DocumentDraftEvent> {
	const res = await fetch(
		`${PUBLIC_API_BASE}/api/me/clients/${clientId}/sessions/${sessionId}/documents/${kind}/draft`,
		{
			method: 'POST',
			credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ instruction: instruction || undefined }),
			signal
		}
	);
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
				yield JSON.parse(line.slice(6)) as DocumentDraftEvent;
			} catch {
				/* skip malformed frame */
			}
		}
	}
}
