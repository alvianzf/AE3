// A Svelte action that turns any element into a multi-file drag-and-drop
// target, alongside whatever click-to-browse <input type="file"> it
// already wraps — every document upload surface in this app (client
// Intake & Files, the public intake link page, a questionnaire's file
// question) used to only support picking files via that input's own
// browse dialog; dropping a file onto the same button did nothing.
//
// Deliberately does not toggle its own hover class via classList — a
// bare `class:drag-over={dragOver}` bound to local state at the call
// site (the pattern the Knowledge library's own dropzone already uses)
// is what Svelte's compiler can actually see as "used," so the style
// stays live instead of getting flagged as a dead selector. This action
// only owns drop-target behavior: preventing the browser's default
// open-the-file-as-a-page handling, and extracting the dropped files.
export function fileDrop(node: HTMLElement, onFiles: (files: File[]) => void) {
	let current = onFiles;

	function onDragOver(e: DragEvent) {
		if (!e.dataTransfer?.types.includes('Files')) return;
		e.preventDefault();
	}
	function onDrop(e: DragEvent) {
		if (!e.dataTransfer?.types.includes('Files')) return;
		e.preventDefault();
		const files = Array.from(e.dataTransfer?.files ?? []);
		if (files.length) current(files);
	}

	node.addEventListener('dragover', onDragOver);
	node.addEventListener('drop', onDrop);

	return {
		update(next: (files: File[]) => void) {
			current = next;
		},
		destroy() {
			node.removeEventListener('dragover', onDragOver);
			node.removeEventListener('drop', onDrop);
		}
	};
}
