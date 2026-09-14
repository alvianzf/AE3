// Renders Reasoner answer text (Markdown, with [K1]/[S1] citation markers)
// as sanitized HTML for {@html}. Citation markers are turned into clickable
// buttons *after* sanitizing, so DOMPurify never has to be told to allow
// button/data-* attributes for arbitrary LLM-generated content.
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

export function renderAnswerHtml(text: string, sourceLabels: Set<string>): string {
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
				return sourceLabels.has(label)
					? `<button type="button" class="cite" data-cite="${label}">[${label}]</button>`
					: `[${label}]`;
			})
			.join(' ');
	});
}
