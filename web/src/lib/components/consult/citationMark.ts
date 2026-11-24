// A citation number ("1", "2"...) inserted into the document editor
// (web/src/lib/markdown.ts's resolveCitationsForDocument) is raw HTML —
// <sup class="cite" data-locator=... data-doc-id=...> — but TipTap's
// schema only preserves tags/attributes an extension explicitly declares.
// With no such extension, ProseMirror's DOM parser dropped the <sup> and
// its data-* attributes entirely on load, leaving plain inline text: the
// number rendered, but not superscript, and no longer clickable. This
// Mark is that missing schema entry.
import { Mark, mergeAttributes } from '@tiptap/core';

export const Citation = Mark.create({
	name: 'citation',

	addAttributes() {
		return {
			locator: {
				default: null,
				parseHTML: (element) => element.getAttribute('data-locator'),
				renderHTML: (attributes) => (attributes.locator ? { 'data-locator': attributes.locator } : {})
			},
			docId: {
				default: null,
				parseHTML: (element) => element.getAttribute('data-doc-id'),
				renderHTML: (attributes) => (attributes.docId ? { 'data-doc-id': attributes.docId } : {})
			}
		};
	},

	parseHTML() {
		return [{ tag: 'sup.cite' }];
	},

	renderHTML({ HTMLAttributes }) {
		return ['sup', mergeAttributes(HTMLAttributes, { class: 'cite' }), 0];
	}
});
