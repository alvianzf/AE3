// Renders Reasoner answer text (Markdown, with [K1]/[S1] citation markers)
// as sanitized HTML for {@html}. Citation markers are turned into clickable
// buttons *after* sanitizing, so DOMPurify never has to be told to allow
// button/data-* attributes for arbitrary LLM-generated content.
import { marked } from 'marked';
import DOMPurify from 'dompurify';

marked.setOptions({ breaks: true, gfm: true });

export function renderAnswerHtml(text: string, sourceLabels: Set<string>): string {
	const html = DOMPurify.sanitize(marked.parse(text, { async: false }) as string);
	return html.replace(/\[([SK]\d+)\]/g, (match, label) =>
		sourceLabels.has(label)
			? `<button type="button" class="cite" data-cite="${label}">[${label}]</button>`
			: match
	);
}
