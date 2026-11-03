<script lang="ts">
	import { PUBLIC_API_BASE } from '$env/static/public';
	import Quiet from '$lib/components/Quiet.svelte';
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

	let passageEls: Record<number, HTMLElement> = {};
	$effect(() => {
		if (!data.locator || !source?.passages) return;
		const hit = source.passages.find((p: any) => p.locator === data.locator);
		if (hit) passageEls[hit.chunk_index]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
	});
</script>

<svelte:head><title>{source?.title ?? 'Source'} — Admin portal</title></svelte:head>

<Quiet title={source?.title}>
	{#if source}
		<p class="hint">
			<a href="/admin?folder={encodeURIComponent(source.folder_path || '')}">
				{source.folder_path || 'Library'}
			</a>
			· <Chip tone="neutral">grade {source.grade}</Chip>
		</p>
		{#if originalUrl}
			<iframe class="doc-frame" src={originalUrl} title={source.title}></iframe>
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
</Quiet>

<style>
	.doc-body { white-space: pre-wrap; font-size: var(--text-sm); line-height: 1.6; max-height: 75vh; overflow-y: auto; }
	.doc-frame { width: 100%; height: 75vh; border: none; border-radius: var(--r); }
	.passage { padding: .4rem .5rem; border-radius: var(--r); transition: background-color .3s var(--ease); }
	.passage.highlight { background: var(--accent-soft); }
</style>
