<script lang="ts">
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { get, put } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Dialog from '$lib/components/Dialog.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let { data } = $props();

	// Same viewer as the admin Library page (web/src/routes/(admin)/admin/
	// +page.svelte) — library content is shared/admin-curated, and a
	// practitioner already reads it implicitly via their own consults and
	// per-source weighting below, so viewing it directly isn't new exposure
	// (app/auth.py's require_admin_or_practitioner backs both GET routes).
	let viewing = $state(false);
	let viewTitle = $state('');
	let viewLoading = $state(false);
	let viewBody = $state<{ body: string; body_reconstructed?: boolean } | null>(null);
	let viewOriginalUrl = $state<string | null>(null);

	async function viewDoc(s: any) {
		viewTitle = s.title;
		viewBody = null;
		viewOriginalUrl = null;
		viewing = true;
		if (s.original_name) {
			viewOriginalUrl = `${PUBLIC_API_BASE}/api/sources/${s.id}/original#toolbar=0&navpanes=0&scrollbar=0`;
			return;
		}
		viewLoading = true;
		try {
			viewBody = await get(fetch, `/sources/${s.id}/text`);
		} catch (err: any) {
			toast(err.message, 'alert');
			viewing = false;
		} finally {
			viewLoading = false;
		}
	}

	async function setWeight(id: string, weight: number) {
		try {
			await put(fetch, `/me/knowledge/${id}/weight`, { weight });
			toast('Weight updated.');
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	// specs/v4.1/03 H4 — this screen mirrored the admin Library's unbounded
	// list before that page got search + pagination; bring the same two
	// mechanisms here so it doesn't degrade faster as the library grows.
	let q = $state('');
	const filtered = $derived.by(() => {
		const needle = q.trim().toLowerCase();
		if (!needle) return data.sources;
		return data.sources.filter((s: any) => (s.title ?? '').toLowerCase().includes(needle));
	});

	const PER_PAGE = 12;
	let page = $state(1);
	const totalPages = $derived(Math.max(1, Math.ceil(filtered.length / PER_PAGE)));
	const shownPage = $derived(Math.min(page, totalPages));
	const pageItems = $derived.by(() => {
		const start = (shownPage - 1) * PER_PAGE;
		return filtered.slice(start, start + PER_PAGE);
	});
</script>

<svelte:head><title>Library weights — Practitioner portal</title></svelte:head>

<Spotlight title="Your knowledge weighting">
	<p class="hint">Boost or dampen how much each shared library source counts when your consults run.</p>
	<input class="search" type="search" placeholder="Search by title…" bind:value={q} aria-label="Search library sources" />
	<DataTable
		columns={[{ key: 'title', label: 'Source', sortable: true }, { key: 'grade', label: 'Grade' }, { key: 'weight', label: 'Your weight' }, { key: 'actions', label: '' }]}
		rows={pageItems}
		empty="Nothing in the library yet."
	>
		{#snippet row(s)}
			<td>{s.title}</td>
			<td><Chip tone="neutral">grade {s.grade}</Chip></td>
			<td>
				<input type="number" min="0" max="5" value={s.weight} onchange={(e) => setWeight(s.id as string, Number((e.target as HTMLInputElement).value))} />
			</td>
			<td><button class="icon-btn" onclick={() => viewDoc(s)} title="View document" aria-label="View {s.title}"><Icon name="eye" /></button></td>
		{/snippet}
	</DataTable>
	{#if totalPages > 1}
		<div class="pager">
			<button type="button" disabled={shownPage <= 1} onclick={() => (page = shownPage - 1)}>Previous</button>
			<span class="hint">Page {shownPage} of {totalPages}</span>
			<button type="button" disabled={shownPage >= totalPages} onclick={() => (page = shownPage + 1)}>Next</button>
		</div>
	{/if}
</Spotlight>

<Dialog bind:open={viewing} title={viewTitle} wide>
	{#if viewOriginalUrl}
		<iframe class="doc-frame" src={viewOriginalUrl} title={viewTitle}></iframe>
	{:else if viewLoading}
		<p class="hint">Loading…</p>
	{:else if viewBody}
		{#if viewBody.body_reconstructed}
			<p class="hint">Rebuilt from passages — no original body was stored for this source.</p>
		{/if}
		<div class="doc-body">{viewBody.body}</div>
	{/if}
</Dialog>

<style>
	input[type='number'] { width: 4rem; border: 1px solid var(--line-2); border-radius: var(--r); padding: .3rem .5rem; }
	.search {
		border: 1px solid var(--line-2); border-radius: 99px; padding: .5rem 1rem; margin-bottom: var(--space-3);
		background: var(--panel); font-size: var(--text-sm); min-height: var(--tap-min); width: 100%; max-width: 20rem;
	}
	.pager { display: flex; align-items: center; gap: var(--space-3); margin-top: var(--space-3); }
	.pager button {
		border: 1px solid var(--line-2); border-radius: var(--r); padding: .4rem .8rem; background: var(--panel);
		font: inherit; cursor: pointer;
	}
	.icon-btn {
		display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
		border: 1px solid var(--line); background: var(--panel); color: var(--accent-ink);
		border-radius: var(--r); width: 2rem; height: 2rem; padding: 0;
		transition: background .15s var(--ease), border-color .15s var(--ease);
	}
	.icon-btn:hover { border-color: var(--accent); background: var(--accent-soft); }
	.doc-body { white-space: pre-wrap; font-size: var(--text-sm); line-height: 1.6; max-height: 60vh; overflow-y: auto; }
	.doc-frame { width: 100%; height: 75vh; border: none; border-radius: var(--r); }
	.pager button:disabled { opacity: .5; cursor: default; }
</style>
