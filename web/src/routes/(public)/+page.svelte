<script lang="ts">
	import { browser } from '$app/environment';
	import { get } from '$lib/api';
	import Sprig from '$lib/components/Sprig.svelte';
	import Chip from '$lib/components/Chip.svelte';

	let { data } = $props();
	// This page is prerendered at build time (specs/v4/01) — practitioners
	// are approved/suspended by an admin at any time, so the build-time
	// snapshot goes stale the moment that happens (flagged as an
	// unverified assumption in specs/v4/02-open-questions.md #1). Refresh
	// once client-side after hydration: first paint stays fast/SEO-able
	// from the prerendered HTML, a real visitor always sees live data.
	let practitioners = $state(data.practitioners);
	$effect(() => {
		if (!browser) return;
		get(fetch, '/practitioners').then((list) => { practitioners = list; }).catch(() => {});
	});

	let q = $state('');
	let specialty = $state('');

	const specialties = $derived.by(() => {
		const s = new Set<string>();
		for (const p of practitioners) for (const sp of p.specialties ?? []) s.add(sp);
		return [...s].sort();
	});

	const filtered = $derived(
		practitioners.filter((p: any) => {
			const matchesQ = !q || p.name.toLowerCase().includes(q.toLowerCase()) || (p.bio ?? '').toLowerCase().includes(q.toLowerCase());
			const matchesSpecialty = !specialty || (p.specialties ?? []).includes(specialty);
			return matchesQ && matchesSpecialty;
		})
	);
</script>

<svelte:head><title>Find a practitioner — Clinic</title></svelte:head>

<!-- Redesigned per specs/v4/03: the discovery surface comes out of a boxed
     card entirely and becomes a full-width hero band + open grid. -->
<section class="hero">
	<div class="container heroin">
		<span class="sprigbig"><Sprig size={30} /></span>
		<h1>Find the right practitioner, on your terms.</h1>
		<p>Browse verified coaches by specialty and language — no account needed to look.</p>
	</div>
</section>

<div class="container">
	<div class="filters">
		<input type="search" placeholder="Search by name or focus…" bind:value={q} aria-label="Search practitioners" />
		<select bind:value={specialty} aria-label="Filter by specialty">
			<option value="">All specialties</option>
			{#each specialties as s (s)}<option value={s}>{s}</option>{/each}
		</select>
	</div>

	<div class="grid">
		{#each filtered as p (p.id)}
			<a class="src" href="/coach/{p.id}">
				<div class="photo" style={p.photo_path ? `background-image:url(${p.photo_path})` : ''}>
					{#if !p.photo_path}<span>{p.name?.[0] ?? '?'}</span>{/if}
				</div>
				<div class="body">
					<h3>{p.name}</h3>
					<p class="bio">{p.bio || 'No bio yet.'}</p>
					<div class="chip-row">
						{#each (p.specialties ?? []).slice(0, 3) as s (s)}<Chip tone="accent">{s}</Chip>{/each}
					</div>
				</div>
			</a>
		{:else}
			<p class="hint">No practitioners match yet — try clearing filters.</p>
		{/each}
	</div>
</div>

<style>
	.hero {
		background: linear-gradient(135deg, var(--rail-top), var(--rail-bottom));
		color: #fdf1f2; padding: var(--space-7) 0; margin-bottom: var(--space-6);
	}
	.heroin { display: flex; flex-direction: column; gap: var(--space-3); max-width: 40rem; }
	.sprigbig { color: #ffb9c4; }
	h1 { font-size: var(--text-3xl); font-weight: 750; }
	.hero p { color: #f7dfe2; font-size: var(--text-lg); }
	.filters { display: flex; gap: var(--space-3); margin-bottom: var(--space-5); flex-wrap: wrap; }
	.filters input, .filters select {
		border: 1px solid var(--line-2); border-radius: 99px; padding: .6rem 1.1rem;
		background: var(--panel); font-size: var(--text-sm); min-height: var(--tap-min);
	}
	.filters input { flex: 1 1 16rem; }
	.grid { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fill, minmax(17rem, 1fr)); padding-bottom: var(--space-7); }
	.src {
		display: flex; flex-direction: column; background: var(--panel); border: 1px solid var(--line);
		border-radius: var(--r-lg); overflow: hidden; text-decoration: none; color: inherit;
		box-shadow: var(--shadow); transition: transform .18s var(--ease), box-shadow .18s var(--ease);
		animation: liftIn .4s var(--ease) both;
	}
	.src:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); }
	.photo { height: 9rem; background: var(--accent-soft); background-size: cover; background-position: center; display: flex; align-items: center; justify-content: center; }
	.photo span { font-size: 2rem; font-weight: 700; color: var(--accent-ink); }
	.body { padding: var(--space-4); display: flex; flex-direction: column; gap: .5rem; }
	.bio { color: var(--muted); font-size: var(--text-sm); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
