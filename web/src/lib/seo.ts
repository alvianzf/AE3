// Renders a JSON-LD block for {@html}. Escapes `<` so embedded content
// (e.g. a practitioner bio) can never prematurely close the <script> tag.
export function jsonLdScript(data: unknown): string {
	return `<script type="application/ld+json">${JSON.stringify(data).replace(/</g, '\\u003c')}</script>`;
}
