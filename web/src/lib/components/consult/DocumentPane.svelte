<script lang="ts">
	import { get as storeGet } from 'svelte/store';
	import { createEditor, EditorContent } from 'svelte-tiptap';
	import StarterKit from '@tiptap/starter-kit';
	import TiptapImage from '@tiptap/extension-image';
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
		logoUrl: string | null;
		practitionerName: string;
		practitionerLocation: string;
		onFlashTurn: (documentId: string | null, locator: string) => void;
	} = $props();

	const KIND_LABEL: Record<Kind, string> = {
		clinician_note: 'Clinician Note',
		client_report: 'Client Report'
	};

	// Prevents the autosave below from firing on the programmatic
	// setContent() the $effect does whenever `kind`/`sessionId` changes or
	// a fresh document loads — only a real keystroke/AI-insert should
	// schedule a save.
	let isHydrating = false;

	const editor = createEditor({
		extensions: [StarterKit, TiptapImage.configure({ inline: false })],
		content: '',
		onUpdate: () => {
			if (isHydrating) return;
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
		{#if kind === 'client_report' && documents[kind]?.status === 'final'}
			<button type="button" class="btn-sm" onclick={downloadPdf} disabled={downloadingPdf}>
				{downloadingPdf ? 'Preparing…' : 'Download PDF'}
			</button>
		{/if}
		<button type="button" class="btn-sm" onclick={toggleFinalize}>
			{documents[kind]?.status === 'final' ? 'Reopen as draft' : 'Finalize'}
		</button>
	</div>
</div>

<div class="doc-toolbar">
	<button type="button" class="tbtn" title="Bold" onclick={() => storeGet(editor).chain().focus().toggleBold().run()}><b>B</b></button>
	<button type="button" class="tbtn" title="Italic" onclick={() => storeGet(editor).chain().focus().toggleItalic().run()}><i>I</i></button>
	<button type="button" class="tbtn" title="Heading" onclick={() => storeGet(editor).chain().focus().toggleHeading({ level: 2 }).run()}>H2</button>
	<button type="button" class="tbtn" title="Bullet list" onclick={() => storeGet(editor).chain().focus().toggleBulletList().run()}><Icon name="list" size={15} /></button>
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
<div class="doc-body" onclick={onDocBodyClick}>
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

	.doc-toolbar { display: flex; align-items: center; gap: 2px; padding: .4rem var(--space-4); border-bottom: 1px solid var(--line); flex: none; flex-wrap: wrap; }
	.tbtn { border: none; background: none; width: 1.75rem; height: 1.75rem; display: grid; place-items: center; border-radius: 6px; color: var(--ink-2); cursor: pointer; }
	.tbtn:hover { background: var(--panel-2); color: var(--ink); }
	.tbtn.wide { width: auto; padding: 0 .55rem; gap: .35rem; display: inline-flex; align-items: center; font-size: var(--text-xs); font-weight: 650; }
	.tsep { width: 1px; height: 1.1rem; background: var(--line-2); margin: 0 .4rem; }
	.ask-ai { margin-left: auto; background: var(--accent-soft); color: var(--accent-ink); }

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
	.doc-body :global(.cite) {
		font: inherit; font-weight: 650; color: var(--accent-ink); background: var(--accent-soft);
		border: none; border-radius: 4px; padding: 0 .25rem; cursor: pointer; white-space: nowrap;
	}
</style>
