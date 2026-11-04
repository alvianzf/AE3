<script lang="ts">
	import { PUBLIC_API_BASE } from '$env/static/public';
	import Chip from '$lib/components/Chip.svelte';

	let { data } = $props();
	const source = $derived(data.source);

	// A routed page, not a dialog over the list (specs/v6.8/02) — so a
	// citation can open it directly, in a new tab, already scrolled to
	// the exact passage/page it cites, via ?locator=. Also gives the
	// folder breadcrumb below (specs/v6.8/01) somewhere real to link
	// back to.
	function pageNumber(locator: string): number | null {
		const m = /page[s]? (\d+)/.exec(locator);
		return m ? Number(m[1]) : null;
	}

	const originalUrl = $derived(
		source?.original_name
			? (() => {
					const page = data.locator ? pageNumber(data.locator) : null;
					const anchor = page ? `page=${page}&` : '';
					return `${PUBLIC_API_BASE}/api/sources/${source.id}/original#${anchor}toolbar=0&navpanes=0&scrollbar=0`;
				})()
			: null
	);
	// Open the same file with no #fragment — the plain download URL, for
	// the "open in a new tab" fallback below (a browser extension/PDF
	// viewer quirk that silently breaks the embedded iframe shouldn't
	// also block viewing the original entirely — found live, specs/
	// v6.8/02's follow-up: an admin reported the detail page loading but
	// the PDF area staying empty, with nothing in the server logs to
	// explain it).
	const downloadUrl = $derived(
		source?.original_name ? `${PUBLIC_API_BASE}/api/sources/${source.id}/original` : null
	);
	let iframeLoaded = $state(false);
	let iframeTimedOut = $state(false);
	$effect(() => {
		if (!originalUrl) return;
		iframeLoaded = false;
		iframeTimedOut = false;
		const t = setTimeout(() => { if (!iframeLoaded) iframeTimedOut = true; }, 8000);
		return () => clearTimeout(t);
	});

	let passageEls: Record<number, HTMLElement> = {};
	$effect(() => {
		if (!data.locator || !source?.passages) return;
		const hit = source.passages.find((p: any) => p.locator === data.locator);
		if (hit) passageEls[hit.chunk_index]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
	});
</script>

<svelte:head><title>{source?.title ?? 'Source'} — Admin portal</title></svelte:head>

<div class="pane-row"><div class="detail-pane">
<div class="detail-head"><div><h1>{source?.error ? 'Could not load' : (source?.title ?? '')}</h1></div></div>
	{#if source?.error}
		<p class="hint">Could not load this source: {source.error}</p>
	{:else if source}
		<p class="hint">
			<a href="/admin/library?folder={encodeURIComponent(source.folder_path || '')}">
				{source.folder_path || 'Library'}
			</a>
			· <Chip tone="neutral">grade {source.grade}</Chip>
		</p>
		{#if originalUrl}
			<p class="hint">
				<a href={downloadUrl} target="_blank" rel="noopener">Open original in a new tab ↗</a>
			</p>
			{#if iframeTimedOut}
				<p class="hint">
					Still loading, or it didn't load — use the "Open original in a new tab" link above.
				</p>
			{/if}
			<iframe class="doc-frame" src={originalUrl} title={source.title} onload={() => (iframeLoaded = true)}></iframe>
		{:else}
			{#if source.body_reconstructed}
				<p class="hint">Rebuilt from passages — no original body was stored for this source.</p>
			{/if}
			<div class="doc-body">
				{#each source.passages as p (p.chunk_index)}
					<p
						bind:this={passageEls[p.chunk_index]}
						class="passage"
						class:highlight={p.locator === data.locator}
					>{p.text}</p>
				{/each}
			</div>
		{/if}
	{/if}
</div></div>

<style>
	.doc-body { white-space: pre-wrap; font-size: var(--text-sm); line-height: 1.6; max-height: 75vh; overflow-y: auto; }
	.doc-frame { width: 100%; height: 75vh; border: none; border-radius: var(--r); }
	.passage { padding: .4rem .5rem; border-radius: var(--r); transition: background-color .3s var(--ease); }
	.passage.highlight { background: var(--accent-soft); }
</style>
