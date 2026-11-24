// Extends @tiptap/extension-image with a `width` attribute (persisted as
// an inline style, so it survives a save/reload round-trip through plain
// HTML the same way everything else in this editor's content does) and a
// NodeView that adds a single bottom-right drag handle — found live: a
// pasted lab-chart screenshot often arrives far wider than the document
// column, with no way to shrink it short of re-cropping and re-uploading.
import TiptapImage from '@tiptap/extension-image';

export const ResizableImage = TiptapImage.extend({
	addAttributes() {
		return {
			...this.parent?.(),
			width: {
				default: null,
				parseHTML: (element) => element.style.width || element.getAttribute('width'),
				renderHTML: (attributes) => (attributes.width ? { style: `width: ${attributes.width}` } : {})
			}
		};
	},

	addNodeView() {
		return ({ node, editor, getPos }) => {
			const container = document.createElement('span');
			container.className = 'resizable-image';
			container.style.display = 'inline-block';
			container.style.position = 'relative';
			container.style.maxWidth = '100%';
			if (node.attrs.width) container.style.width = node.attrs.width;

			const img = document.createElement('img');
			img.src = node.attrs.src;
			if (node.attrs.alt) img.alt = node.attrs.alt;
			img.style.display = 'block';
			img.style.width = '100%';
			img.style.height = 'auto';
			img.style.borderRadius = 'inherit';
			container.appendChild(img);

			const handle = document.createElement('span');
			handle.className = 'resize-handle';
			handle.setAttribute('aria-hidden', 'true');
			container.appendChild(handle);

			let startX = 0;
			let startWidth = 0;
			const onPointerMove = (e: PointerEvent) => {
				const delta = e.clientX - startX;
				const parentWidth = container.parentElement?.clientWidth || startWidth;
				const next = Math.max(60, Math.min(parentWidth, startWidth + delta));
				container.style.width = `${next}px`;
			};
			const onPointerUp = () => {
				document.removeEventListener('pointermove', onPointerMove);
				document.removeEventListener('pointerup', onPointerUp);
				const pos = typeof getPos === 'function' ? getPos() : undefined;
				if (typeof pos === 'number') {
					editor
						.chain()
						.setNodeSelection(pos)
						.updateAttributes('image', { width: container.style.width })
						.run();
				}
			};
			handle.addEventListener('pointerdown', (e) => {
				e.preventDefault();
				startX = e.clientX;
				startWidth = container.getBoundingClientRect().width;
				document.addEventListener('pointermove', onPointerMove);
				document.addEventListener('pointerup', onPointerUp);
			});

			return {
				dom: container,
				update(updatedNode) {
					if (updatedNode.type.name !== 'image') return false;
					img.src = updatedNode.attrs.src;
					container.style.width = updatedNode.attrs.width || '';
					return true;
				}
			};
		};
	}
});
