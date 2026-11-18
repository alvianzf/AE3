// Renders Reasoner answer text (Markdown, with [K1]/[S1] citation markers)
// as sanitized HTML for {@html}. The markers themselves are the LLM's
// internal way of pointing at a numbered source — never shown as-is; each
// one is replaced with a clickable chip carrying that source's own title
// instead. Done *after* sanitizing, so DOMPurify never has to be told to
// allow button/data-* attributes for arbitrary LLM-generated content.
import { marked } from 'marked';
import DOMPurify from 'dompurify';

marked.setOptions({ breaks: true, gfm: true });

// The Reasoner sometimes groups several citations into one bracket
// ("[K1, K3]") instead of one bracket each ("[K1][K3]") — matching only
// "[K1]"-shaped brackets would silently leave those un-clickable. Matches
// a whole bracket group, then turns each [SK]-number inside it into its
// own button (a bare trailing number, "[K1, 3]", reuses the previous
// citation's letter).
const CITE_GROUP = /\[([SK]\d+(?:\s*,\s*[SK]?\d+)*)\]/g;

// The citation chip shows the source's own title, truncated — not the
// [K1]/[S1] marker the Reasoner writes inline. That marker is purely the
// LLM's internal way of pointing at one of the numbered sources it was
// given; a reader never needs to see "K1," they need to see what the
// citation actually is.
const TITLE_TRUNCATE = 10;

// Consult Draft Editor: an AI-drafted document is saved as plain HTML
// (session_documents.content), not re-rendered from Markdown + a live
// sources array the way a chat turn is — so a citation chip inserted into
// the document must carry its own resolved document_id/locator baked into
// its HTML at insertion time, not just the ephemeral [K1] label a reload
// could no longer resolve. Same CITE_GROUP matching as renderAnswerHtml,
// different output shape per citation.
export function resolveCitationsForDocument(
	text: string,
	sources: { label: string; document_id: string | null; locator: string; title: string }[]
): string {
	const byLabel = new Map(sources.map((s) => [s.label, s]));
	const html = DOMPurify.sanitize(marked.parse(text, { async: false }) as string);
	return html.replace(CITE_GROUP, (_match, group: string) => {
		let lastPrefix = 'K';
		return group
			.split(',')
			.map((raw: string) => {
				const m = /^\s*([SK])?(\d+)\s*$/.exec(raw);
				if (!m) return raw;
				lastPrefix = m[1] ?? lastPrefix;
				const label = `${lastPrefix}${m[2]}`;
				const s = byLabel.get(label);
				if (!s) return '';
				const truncated = s.title.length > TITLE_TRUNCATE ? s.title.slice(0, TITLE_TRUNCATE) + '…' : s.title;
				const docAttr = s.document_id ? ` data-doc-id="${s.document_id}"` : '';
				return `<sup><button type="button" class="cite" data-locator="${s.locator ?? ''}"${docAttr}>${truncated}</button></sup>`;
			})
			.join(' ');
	});
}

export function renderAnswerHtml(text: string, sourceTitles: Map<string, string> = new Map()): string {
	const html = DOMPurify.sanitize(marked.parse(text, { async: false }) as string);
	return html.replace(CITE_GROUP, (_match, group: string) => {
		let lastPrefix = 'K';
		return group
			.split(',')
			.map((raw: string) => {
				const m = /^\s*([SK])?(\d+)\s*$/.exec(raw);
				if (!m) return raw;
				lastPrefix = m[1] ?? lastPrefix;
				const label = `${lastPrefix}${m[2]}`;
				const title = sourceTitles.get(label);
				if (title === undefined) return '';
				const truncated = title.length > TITLE_TRUNCATE ? title.slice(0, TITLE_TRUNCATE) + '…' : title;
				return `<sup><button type="button" class="cite" data-cite="${label}">${truncated}</button></sup>`;
			})
			.join(' ');
	});
}
