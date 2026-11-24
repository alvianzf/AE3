<script lang="ts">
	import { get as storeGet } from 'svelte/store';
	import { createEditor, EditorContent } from 'svelte-tiptap';
	import StarterKit from '@tiptap/starter-kit';
	import { Table as TiptapTable } from '@tiptap/extension-table';
	import TiptapTableRow from '@tiptap/extension-table-row';
	import TiptapTableHeader from '@tiptap/extension-table-header';
	import TiptapTableCell from '@tiptap/extension-table-cell';
	import { TextStyle } from '@tiptap/extension-text-style';
	import Color from '@tiptap/extension-color';
	import Highlight from '@tiptap/extension-highlight';
	import { ResizableImage } from './resizableImage';
	import { Citation } from './citationMark';
	import { put } from '$lib/api';
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { resolveCitationsForDocument } from '$lib/markdown';
	import { streamDocumentDraft } from '$lib/documentStream';
	import { toast } from '$lib/stores/toast';
	import Icon from '$lib/components/Icon.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import ImageCropModal from './ImageCropModal.svelte';
	import SourcePicker from './SourcePicker.svelte';

	type Kind = 'clinician_note' | 'client_report';

	let {
		clientId,
		sessionId,
		kind = $bindable<Kind>('clinician_note'),
		documents,
		turns,
		focusMode = $bindable(false),
		// True from the moment a real keystroke/insert happens until that
		// edit is saved — the consult page's auto-redraft-after-each-turn
		// feature checks this before overwriting editor content, so it
		// never clobbers an edit the practitioner is in the middle of
		// making (found live: an auto-redraft landing mid-keystroke would
		// otherwise silently discard unsaved text).
		dirty = $bindable(false),
		logoUrl,
		practitionerName,
		practitionerLocation,
		onFlashTurn
	}: {
		clientId: string;
		sessionId: string;
		kind?: Kind;
		documents: Record<Kind, { content: string; status: string } | null>;
		turns: any[];
		focusMode?: boolean;
		dirty?: boolean;
		logoUrl: string | null;
		practitionerName: string;
		practitionerLocation: string;
		onFlashTurn: (documentId: string | null, locator: string) => void;
	} = $props();

	function onEditorKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && focusMode) focusMode = false;
	}

	const KIND_LABEL: Record<Kind, string> = {
		clinician_note: 'Clinician Note',
		client_report: 'Client Report'
	};

	// Prevents the autosave below from firing on the programmatic
	// setContent() the $effect does whenever `kind`/`sessionId` changes or
	// a fresh document loads — only a real keystroke/AI-insert should
	// schedule a save.
	let isHydrating = false;

	// TiptapTableCell has no notion of a background color out of the box —
	// "change cell colors" needs one more HTML attribute on top of what the
	// extension already renders (colspan/rowspan/colwidth).
	const TableCellWithBackground = TiptapTableCell.extend({
		addAttributes() {
			return {
				...this.parent?.(),
				backgroundColor: {
					default: null,
					parseHTML: (element) => element.style.backgroundColor || null,
					renderHTML: (attributes) =>
						attributes.backgroundColor ? { style: `background-color: ${attributes.backgroundColor}` } : {}
				}
			};
		}
	});

	const editor = createEditor({
		extensions: [
			StarterKit,
			ResizableImage.configure({ inline: false }),
			TiptapTable.configure({ resizable: true }),
			TiptapTableRow,
			TiptapTableHeader,
			TableCellWithBackground,
			TextStyle,
			Color,
			Highlight.configure({ multicolor: true }),
			Citation
		],
		content: '',
		editorProps: {
			// A practitioner pasting a screenshot (a lab chart, say) straight
			// from their clipboard used to just drop silently — TipTap's own
			// default paste handling only understands text/HTML, not image
			// clipboard data. Routes through the exact same crop-then-upload
			// flow the "Image" toolbar button already uses (onFilePicked ->
			// ImageCropModal -> insertImageBlob), so there's one path for
			// "an image enters this document," not two.
			handlePaste: (_view, event: ClipboardEvent) => {
				const items = event.clipboardData?.items;
				if (!items) return false;
				const imageItem = Array.from(items).find((i) => i.type.startsWith('image/'));
				if (!imageItem) return false;
				const file = imageItem.getAsFile();
				if (!file) return false;
				event.preventDefault();
				pasteCropFile = file;
				pasteCropSrc = URL.createObjectURL(file);
				return true;
			}
		},
		onUpdate: () => {
			if (isHydrating) return;
			dirty = true;
			savingState = 'pending';
			clearTimeout(saveTimer);
			saveTimer = setTimeout(() => void saveDocument(), 1800);
		}
	});

	let saveTimer: ReturnType<typeof setTimeout> | undefined;
	let savingState = $state<'idle' | 'pending' | 'saving' | 'saved' | 'error'>('idle');

	$effect(() => {
		// Tracked deps: kind, sessionId, and this document's own content —
		// any of the three changing means the editor must load different
		// content, not keep typing into what's already there.
		const doc = documents[kind];
		const inst = storeGet(editor);
		isHydrating = true;
		inst.commands.setContent(doc?.content || '', { emitUpdate: false });
		isHydrating = false;
		savingState = 'idle';
	});

	async function saveDocument(status?: 'draft' | 'final') {
		const inst = storeGet(editor);
		const html = inst.getHTML();
		const nextStatus = status ?? documents[kind]?.status ?? 'draft';
		savingState = 'saving';
		try {
			const saved = await put(
				fetch,
				`/me/clients/${clientId}/sessions/${sessionId}/documents/${kind}`,
				{ content: html, status: nextStatus }
			);
			documents[kind] = saved;
			savingState = 'saved';
			dirty = false;
		} catch {
			savingState = 'error';
		}
	}

	function toggleFinalize() {
		const next = documents[kind]?.status === 'final' ? 'draft' : 'final';
		void saveDocument(next);
	}

	// Clients have no in-app view of their report — it's delivered by the
	// practitioner downloading this PDF and attaching/pasting it into an
	// email. Rendered server-side from the saved HTML so formatting and
	// any inserted images survive, unlike a plain-text clipboard copy.
	let downloadingPdf = $state(false);
	async function downloadPdf() {
		downloadingPdf = true;
		try {
			const res = await fetch(
				`${PUBLIC_API_BASE}/api/me/clients/${clientId}/sessions/${sessionId}/documents/${kind}/pdf`,
				{ credentials: 'include' }
			);
			if (!res.ok) throw new Error();
			const blob = await res.blob();
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `${KIND_LABEL[kind]}.pdf`;
			a.click();
			URL.revokeObjectURL(url);
		} catch {
			toast('Could not generate the PDF', 'alert');
		} finally {
			downloadingPdf = false;
		}
	}

	// Lets a practitioner see exactly what the finished PDF will look like
	// — letterhead, footer, page breaks and all — before they finalize or
	// send it, instead of only finding out after a download. Works on a
	// draft too: the backend's PDF route renders whatever content is
	// currently saved, draft or final, same as Download PDF would.
	let previewingPdf = $state(false);
	async function previewPdf() {
		previewingPdf = true;
		try {
			await saveDocument();
			const res = await fetch(
				`${PUBLIC_API_BASE}/api/me/clients/${clientId}/sessions/${sessionId}/documents/${kind}/pdf`,
				{ credentials: 'include' }
			);
			if (!res.ok) throw new Error();
			const blob = await res.blob();
			const url = URL.createObjectURL(blob);
			window.open(url, '_blank', 'noopener');
			// The opened tab holds its own reference to the blob once loaded;
			// revoking a little later avoids a race where the tab opens to a
			// dead URL on a slow machine.
			setTimeout(() => URL.revokeObjectURL(url), 30_000);
		} catch {
			toast('Could not generate the PDF preview', 'alert');
		} finally {
			previewingPdf = false;
		}
	}

	function onDocBodyClick(e: MouseEvent) {
		const btn = (e.target as HTMLElement).closest('.cite') as HTMLElement | null;
		if (!btn) return;
		const docId = btn.dataset.docId || null;
		const locator = btn.dataset.locator || '';
		if (docId) {
			window.open(
				`/practitioner/knowledge/${docId}?locator=${encodeURIComponent(locator)}`,
				'_blank',
				'noopener'
			);
		}
		onFlashTurn(docId, locator);
	}

	// ---- Ask AI ---------------------------------------------------------
	let asking = $state(false);
	let instruction = $state('');
	let askOpen = $state(false);
	async function askAI() {
		asking = true;
		try {
			let text = '';
			let sources: any[] = [];
			for await (const ev of streamDocumentDraft(clientId, sessionId, kind, instruction)) {
				if (ev.event === 'result') {
					text = ev.text;
					sources = ev.sources;
					if (ev.check?.unsupported?.length) {
						toast(
							`${ev.check.unsupported.length} unverified sentence(s) were removed from the draft — not confidently backed by this consult's sources.`,
							'alert'
						);
					}
				} else if (ev.event === 'error') {
					savingState = 'error';
				}
			}
			if (text) {
				const html = resolveCitationsForDocument(text, sources);
				const inst = storeGet(editor);
				inst.commands.insertContent(html);
				await saveDocument();
			}
		} catch {
			savingState = 'error';
		} finally {
			asking = false;
			askOpen = false;
			instruction = '';
		}
	}

	// A full redraft (replace, not append) from this session's consult —
	// the consult page already does this automatically after every turn,
	// but a practitioner who edited the text by hand, or wants a fresh
	// take after the auto-redraft skipped a turn (it never overwrites a
	// mid-edit document), needs an explicit way to ask for one instead of
	// waiting on the next question.
	let regenerating = $state(false);

	// Just drives each color swatch's own visible fill — the actual
	// formatting commands below read the native <input type="color">'s
	// value directly off the change event, not from these.
	let textColor = $state('#1f2a24');
	let highlightColor = $state('#fff3b0');
	let cellColor = $state('#f2f6f3');
	async function regenerateDraft() {
		regenerating = true;
		try {
			let text = '';
			let sources: any[] = [];
			for await (const ev of streamDocumentDraft(clientId, sessionId, kind)) {
				if (ev.event === 'result') {
					text = ev.text;
					sources = ev.sources;
				} else if (ev.event === 'error') {
					savingState = 'error';
				}
			}
			if (text) {
				const html = resolveCitationsForDocument(text, sources);
				const inst = storeGet(editor);
				inst.commands.setContent(html);
				await saveDocument();
			}
		} catch {
			savingState = 'error';
		} finally {
			regenerating = false;
		}
	}

	// ---- Images -----------------------------------------------------------
	let fileInput: HTMLInputElement | undefined = $state();
	let pasteCropSrc = $state<string | null>(null);
	let pasteCropFile: Blob | null = null;
	let sourcePickerOpen = $state(false);

	function onFilePicked(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (!file) return;
		pasteCropFile = file;
		pasteCropSrc = URL.createObjectURL(file);
	}

	async function insertImageBlob(blob: Blob) {
		pasteCropSrc = null;
		const form = new FormData();
		form.set('file', blob, 'asset.png');
		const res = await fetch(
			`${PUBLIC_API_BASE}/api/me/clients/${clientId}/sessions/${sessionId}/assets`,
			{ method: 'POST', credentials: 'include', body: form }
		);
		if (!res.ok) {
			savingState = 'error';
			return;
		}
		const data = await res.json();
		const inst = storeGet(editor);
		inst.chain().focus().setImage({ src: `${PUBLIC_API_BASE}${data.url}` }).run();
		await saveDocument();
	}

	const citedSources = $derived.by(() => {
		const seen = new Set<string>();
		const out: { document_id: string; title: string }[] = [];
		for (const t of turns ?? []) {
			for (const s of t.sources ?? []) {
				if (s.kind !== 'chunk' || !s.document_id || seen.has(s.document_id)) continue;
				seen.add(s.document_id);
				out.push({ document_id: s.document_id, title: s.title });
			}
		}
		return out;
	});
</script>

<div class="doc-head">
	<button
		type="button" class="btn-sm focus-toggle" title={focusMode ? 'Exit focus mode (Esc)' : 'Widen this pane while drafting'}
		onclick={() => (focusMode = !focusMode)}
	>
		{focusMode ? 'Exit focus' : 'Focus'}
	</button>
	<div class="doc-tabs">
		{#each ['clinician_note', 'client_report'] as const as k}
			<button type="button" class:on={kind === k} onclick={() => (kind = k)}>{KIND_LABEL[k]}</button>
		{/each}
	</div>
	<div class="doc-status">
		{#if savingState === 'saving'}<span class="save-hint"><Spinner size={12} /> Saving…</span>
		{:else if savingState === 'saved'}<span class="save-hint">Saved</span>
		{:else if savingState === 'error'}<span class="save-hint error">Save failed</span>{/if}
		<span class="pill {documents[kind]?.status === 'final' ? 'final' : 'draft'}">
			{documents[kind]?.status === 'final' ? 'Final' : 'Draft'}
		</span>
		{#if documents[kind]?.status !== 'final'}
			<button type="button" class="btn-sm" onclick={regenerateDraft} disabled={regenerating} title="Regenerate this draft from the consult so far, replacing the current content">
				{regenerating ? 'Regenerating…' : 'Regenerate'}
			</button>
		{/if}
		{#if kind === 'client_report'}
			<button type="button" class="btn-sm" onclick={previewPdf} disabled={previewingPdf} title="See exactly what the PDF will look like">
				{previewingPdf ? 'Preparing…' : 'Preview PDF'}
			</button>
			{#if documents[kind]?.status === 'final'}
				<button type="button" class="btn-sm" onclick={downloadPdf} disabled={downloadingPdf}>
					{downloadingPdf ? 'Preparing…' : 'Download PDF'}
				</button>
			{/if}
		{/if}
		<button type="button" class="btn-sm" onclick={toggleFinalize}>
			{documents[kind]?.status === 'final' ? 'Reopen as draft' : 'Finalize'}
		</button>
	</div>
</div>

<div class="doc-toolbar">
	<button type="button" class="tbtn" title="Bold" onclick={() => storeGet(editor).chain().focus().toggleBold().run()}><b>B</b></button>
	<button type="button" class="tbtn" title="Italic" onclick={() => storeGet(editor).chain().focus().toggleItalic().run()}><i>I</i></button>
	<button type="button" class="tbtn underline-btn" title="Underline" onclick={() => storeGet(editor).chain().focus().toggleUnderline().run()}>U</button>
	<button type="button" class="tbtn strike-btn" title="Strikethrough" onclick={() => storeGet(editor).chain().focus().toggleStrike().run()}>S</button>
	<div class="tsep"></div>
	<button type="button" class="tbtn" title="Heading" onclick={() => storeGet(editor).chain().focus().toggleHeading({ level: 2 }).run()}>H2</button>
	<button type="button" class="tbtn" title="Subheading" onclick={() => storeGet(editor).chain().focus().toggleHeading({ level: 3 }).run()}>H3</button>
	<button type="button" class="tbtn" title="Bullet list" onclick={() => storeGet(editor).chain().focus().toggleBulletList().run()}><Icon name="list" size={15} /></button>
	<button type="button" class="tbtn" title="Numbered list" onclick={() => storeGet(editor).chain().focus().toggleOrderedList().run()}>1.</button>
	<button type="button" class="tbtn" title="Quote" onclick={() => storeGet(editor).chain().focus().toggleBlockquote().run()}>&rdquo;</button>
	<div class="tsep"></div>
	<label class="tbtn color-btn" style:--swatch={textColor} title="Text color">
		A
		<input type="color" bind:value={textColor} oninput={(e) => storeGet(editor).chain().focus().setColor((e.target as HTMLInputElement).value).run()} />
	</label>
	<label class="tbtn color-btn" style:--swatch={highlightColor} title="Highlight color">
		Highlight
		<input type="color" bind:value={highlightColor} oninput={(e) => storeGet(editor).chain().focus().toggleHighlight({ color: (e.target as HTMLInputElement).value }).run()} />
	</label>
	<div class="tsep"></div>
	<button type="button" class="tbtn wide" title="Insert a table" onclick={() => storeGet(editor).chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}>Table</button>
	{#if $editor?.isActive('table')}
		<button type="button" class="tbtn wide" title="Add row" onclick={() => storeGet(editor).chain().focus().addRowAfter().run()}>+Row</button>
		<button type="button" class="tbtn wide" title="Add column" onclick={() => storeGet(editor).chain().focus().addColumnAfter().run()}>+Col</button>
		<button type="button" class="tbtn wide" title="Delete row" onclick={() => storeGet(editor).chain().focus().deleteRow().run()}>-Row</button>
		<button type="button" class="tbtn wide" title="Delete column" onclick={() => storeGet(editor).chain().focus().deleteColumn().run()}>-Col</button>
		<label class="tbtn color-btn" style:--swatch={cellColor} title="Cell background color">
			Cell
			<input type="color" bind:value={cellColor} oninput={(e) => storeGet(editor).chain().focus().updateAttributes('tableCell', { backgroundColor: (e.target as HTMLInputElement).value }).run()} />
		</label>
		<button type="button" class="tbtn" title="Delete table" onclick={() => storeGet(editor).chain().focus().deleteTable().run()}><Icon name="trash" size={14} /></button>
	{/if}
	<div class="tsep"></div>
	<button type="button" class="tbtn wide" onclick={() => fileInput?.click()}><Icon name="image" size={14} /> Image</button>
	<button type="button" class="tbtn wide" onclick={() => (sourcePickerOpen = true)}>Insert from source</button>
	<button type="button" class="tbtn wide ask-ai" onclick={() => (askOpen = true)}><Icon name="sparkles" size={14} /> Ask AI</button>
</div>

{#if askOpen}
	<div class="ask-row">
		<input
			type="text" placeholder="e.g. Draft the client report from this note…"
			bind:value={instruction} disabled={asking}
			onkeydown={(e) => e.key === 'Enter' && askAI()}
		/>
		<button type="button" class="btn-sm" disabled={asking} onclick={askAI}>
			{#if asking}<Spinner size={12} />{:else}Draft{/if}
		</button>
	</div>
{/if}

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="doc-body" onclick={onDocBodyClick} onkeydown={onEditorKeydown}>
	<div class="doc-letterhead">
		{#if logoUrl}<img class="doc-logo" src={logoUrl} alt="" />{:else}<div class="doc-logo-fallback">{practitionerName?.[0] ?? '?'}</div>{/if}
		<div><div class="pn">{practitionerName}</div><div class="pm">{practitionerLocation}</div></div>
	</div>
	<EditorContent editor={$editor} />
</div>

<input bind:this={fileInput} type="file" accept="image/jpeg,image/png,image/gif,image/webp" onchange={onFilePicked} hidden />

{#if pasteCropSrc}
	<ImageCropModal imageSrc={pasteCropSrc} onConfirm={insertImageBlob} onCancel={() => (pasteCropSrc = null)} />
{/if}

{#if sourcePickerOpen}
	<SourcePicker
		sources={citedSources}
		onInsert={(blob) => {
			sourcePickerOpen = false;
			void insertImageBlob(blob);
		}}
		onCancel={() => (sourcePickerOpen = false)}
	/>
{/if}

<style>
	.doc-head { display: flex; align-items: center; justify-content: space-between; padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--line); flex: none; }
	.doc-tabs { display: flex; gap: 2px; }
	.doc-tabs button { border: none; background: none; padding: .4rem .6rem; border-radius: var(--r); font-size: var(--text-xs); font-weight: 650; color: var(--muted); cursor: pointer; }
	.doc-tabs button.on { background: var(--panel-2); color: var(--ink); }
	.doc-status { display: flex; align-items: center; gap: .5rem; }
	.save-hint { font-size: var(--text-xs); color: var(--muted); display: inline-flex; align-items: center; gap: .3rem; }
	.save-hint.error { color: var(--danger); }
	.pill { display: inline-flex; padding: 2px 8px; border-radius: 99px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .03em; }
	.pill.draft { background: var(--warn-soft); color: var(--warn); }
	.pill.final { background: var(--accent-soft); color: var(--accent-ink); }
	.btn-sm { border: 1px solid var(--line-2); background: var(--panel); border-radius: var(--r); padding: .3rem .6rem; font-size: var(--text-xs); font-weight: 650; cursor: pointer; }
	.btn-sm:hover { background: var(--panel-2); }
	.focus-toggle { margin-right: var(--space-3); flex: none; }

	.doc-toolbar { display: flex; align-items: center; gap: 2px; padding: .4rem var(--space-4); border-bottom: 1px solid var(--line); flex: none; flex-wrap: wrap; }
	.tbtn { border: none; background: none; width: 1.75rem; height: 1.75rem; display: grid; place-items: center; border-radius: 6px; color: var(--ink-2); cursor: pointer; }
	.tbtn:hover { background: var(--panel-2); color: var(--ink); }
	.tbtn.wide { width: auto; padding: 0 .55rem; gap: .35rem; display: inline-flex; align-items: center; font-size: var(--text-xs); font-weight: 650; }
	.tsep { width: 1px; height: 1.1rem; background: var(--line-2); margin: 0 .4rem; }
	.ask-ai { margin-left: auto; background: var(--accent-soft); color: var(--accent-ink); }
	.underline-btn { text-decoration: underline; }
	.strike-btn { text-decoration: line-through; }
	.color-btn {
		position: relative; width: auto; padding: 0 .4rem; font-size: var(--text-xs); font-weight: 700;
		display: inline-flex; align-items: center; gap: .3rem;
	}
	.color-btn::after { content: ''; display: block; width: .8rem; height: .8rem; border-radius: 3px; border: 1px solid var(--line-2); background: var(--swatch, var(--ink-2)); }
	.color-btn input[type='color'] {
		position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; border: none; padding: 0;
	}

	.ask-row { display: flex; gap: .4rem; padding: .5rem var(--space-4); border-bottom: 1px solid var(--line); }
	.ask-row input { flex: 1; border: 1px solid var(--line-2); border-radius: var(--r); padding: .4rem .6rem; font: inherit; font-size: var(--text-sm); }

	.doc-body { flex: 1 1 auto; overflow-y: auto; padding: var(--space-5); min-height: 0; }
	.doc-letterhead { display: flex; align-items: center; gap: .7rem; padding-bottom: var(--space-4); margin-bottom: var(--space-4); border-bottom: 2px solid var(--line-2); }
	.doc-logo, .doc-logo-fallback { width: 2.4rem; height: 2.4rem; border-radius: 8px; flex: none; object-fit: contain; }
	.doc-logo-fallback { background: var(--panel-2); display: grid; place-items: center; font-weight: 700; color: var(--ink-2); }
	.pn { font-weight: 700; font-size: var(--text-sm); }
	.pm { font-size: var(--text-xs); color: var(--muted); }

	.doc-body :global(.ProseMirror) { outline: none; font-size: var(--text-sm); color: var(--ink-2); }
	.doc-body :global(.ProseMirror p) { margin: 0 0 .7em; }
	.doc-body :global(.ProseMirror h2) { font-size: var(--text-base); color: var(--ink); margin: 1em 0 .4em; }
	.doc-body :global(.ProseMirror img) { max-width: 100%; border-radius: var(--r); margin: .4em 0; }
	.doc-body :global(.resizable-image) { border-radius: var(--r); margin: .4em 0; }
	.doc-body :global(.resizable-image .resize-handle) {
		position: absolute; right: -4px; bottom: -4px; width: .7rem; height: .7rem;
		border-radius: 50%; background: var(--accent); border: 2px solid var(--panel);
		cursor: nwse-resize; opacity: 0; transition: opacity .15s;
	}
	.doc-body :global(.resizable-image:hover .resize-handle) { opacity: 1; }
	.doc-body :global(table) { border-collapse: collapse; margin: .6em 0; width: 100%; }
	.doc-body :global(table td), .doc-body :global(table th) {
		border: 1px solid var(--line-2); padding: .3em .5em; min-width: 2em; vertical-align: top;
	}
	.doc-body :global(table th) { background: var(--panel-2); font-weight: 650; }
	.doc-body :global(mark) { border-radius: 2px; padding: 0 .1em; }
	.doc-body :global(.cite) {
		-webkit-appearance: none; appearance: none; outline: none;
		font: inherit; font-weight: 650; color: var(--accent-ink); background: var(--accent-soft);
		border: none; border-radius: 4px; padding: 0 .25rem; cursor: pointer; white-space: nowrap;
	}
	.doc-body :global(.references) {
		margin-top: 1.5em; padding-top: .8em; border-top: 1px solid var(--line);
	}
	.doc-body :global(.references h3) {
		font-size: var(--text-xs); letter-spacing: .04em; text-transform: uppercase;
		color: var(--muted); font-weight: 700; margin: 0 0 .5em;
	}
	.doc-body :global(.references ol) { margin: 0; padding-left: 1.2em; font-size: var(--text-xs); color: var(--muted); }
	.doc-body :global(.references li) { margin-bottom: .3em; }
</style>
