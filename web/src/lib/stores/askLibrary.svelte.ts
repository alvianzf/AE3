// Shared "Ask the Library" conversation state — a single module-level
// store (not per-component state) specifically so the dashboard's
// compact preview card and the global Rail button (every practitioner
// page) open and drive the SAME conversation, not two independent ones.
// The modal itself (AskLibraryModal.svelte) is mounted once, at the
// practitioner layout level, so it survives navigation between pages.
import { get } from '$lib/api';
import { streamLibraryChat, type LibraryRetrievalMode } from '$lib/libraryChatStream';

export const AGENT_LABELS: Record<string, string> = {
	lookup: 'Searching',
	discover: 'Finding sources',
	traversal: 'Connecting the dots',
	reasoner: 'Answering',
	checker: 'Checking the facts'
};

export const EXAMPLES = [
	'Interactions between magnesium glycinate and SSRIs',
	'Latest evidence on continuous glucose monitoring in non-diabetics',
	'Thyroid panel reference ranges across labs'
];

let turns = $state<any[]>([]);
let loadedHistory = $state(false);
let question = $state('');
let asking = $state(false);
let expanded = $state(false);
let retrievalMode = $state<LibraryRetrievalMode>('general_lookup');
let steps = $state<{ agent: string; status: 'running' | 'done' | 'error'; progress?: string }[]>([]);
let streamingAnswer = $state('');
let abortController: AbortController | null = null;

async function loadHistory() {
	if (loadedHistory) return;
	try {
		turns = await get(fetch, '/me/library-chat');
	} catch {
		/* dashboard/modal still work with empty history if this fails */
	} finally {
		loadedHistory = true;
	}
}

function open() {
	expanded = true;
	loadHistory();
}

function close() {
	expanded = false;
}

function useExample(text: string) {
	question = text;
}

async function ask(e?: Event) {
	e?.preventDefault();
	if (!question.trim() || asking) return;
	const askedQuestion = question;
	question = '';
	asking = true;
	expanded = true; // submitting always opens the full view — never grow a compact card in place
	steps = [];
	streamingAnswer = '';
	abortController = new AbortController();
	let gotResult = false;
	try {
		for await (const ev of streamLibraryChat(askedQuestion, retrievalMode, abortController.signal)) {
			if (ev.event === 'agent_start') {
				steps = [...steps, { agent: ev.agent, status: 'running' }];
			} else if (ev.event === 'agent_progress') {
				const progress = `hop ${ev.hop}/${ev.max_depth} · ${ev.relevant}/${ev.candidates} relevant`;
				steps = steps.map((s) => (s.agent === ev.agent && s.status === 'running' ? { ...s, progress } : s));
			} else if (ev.event === 'agent_done') {
				steps = steps.map((s) => (s.agent === ev.agent && s.status === 'running' ? { ...s, status: 'done' } : s));
			} else if (ev.event === 'answer_delta') {
				streamingAnswer += ev.text;
			} else if (ev.event === 'result') {
				gotResult = true;
				turns = [...turns, ev];
				streamingAnswer = '';
			} else if (ev.event === 'error') {
				steps = steps.map((s) => (s.status === 'running' ? { ...s, status: 'error' } : s));
				streamingAnswer = `_${ev.message}_`;
			}
		}
		if (!gotResult && !streamingAnswer) {
			streamingAnswer = '_Something went wrong. Try asking again._';
		}
	} catch (err: any) {
		if (err?.name !== 'AbortError') streamingAnswer = `_${err.message}_`;
	} finally {
		asking = false;
		steps = [];
		abortController = null;
	}
}

export const askLibrary = {
	get turns() { return turns; },
	get loadedHistory() { return loadedHistory; },
	get question() { return question; },
	set question(v: string) { question = v; },
	get asking() { return asking; },
	get expanded() { return expanded; },
	get retrievalMode() { return retrievalMode; },
	set retrievalMode(v: LibraryRetrievalMode) { retrievalMode = v; },
	get steps() { return steps; },
	get streamingAnswer() { return streamingAnswer; },
	loadHistory,
	open,
	close,
	useExample,
	ask
};
