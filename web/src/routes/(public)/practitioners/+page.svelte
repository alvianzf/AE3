<script lang="ts">
	import { browser } from '$app/environment';
	import { get } from '$lib/api';
	import BrandMark from '$lib/components/BrandMark.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import LeafField from '$lib/components/LeafField.svelte';

	let { data } = $props();
	let practitioners = $state(data.practitioners ?? []);
	$effect(() => {
		if (!browser) return;
		get(fetch, '/practitioners').then((list) => { practitioners = list; }).catch(() => {});
	});

	let q = $state('');
	let specialty = $state('');
	let onlyAccepting = $state(false);

	const specialties = $derived.by(() => {
		const s = new Set<string>();
		for (const p of practitioners) {
			for (const sp of p.specialties ?? []) s.add(sp);
		}
		return [...s].sort();
	});

	const filtered = $derived(
		practitioners.filter((p: any) => {
			const matchesQ =
				!q ||
				p.name.toLowerCase().includes(q.toLowerCase()) ||
				(p.bio ?? '').toLowerCase().includes(q.toLowerCase()) ||
				(p.specialties ?? []).some((s: string) => s.toLowerCase().includes(q.toLowerCase()));
			const matchesSpecialty = !specialty || (p.specialties ?? []).includes(specialty);
			const matchesAccepting = !onlyAccepting || p.accepting_new_clients;
			return matchesQ && matchesSpecialty && matchesAccepting;
		})
	);

	function resetFilters() {
		q = '';
		specialty = '';
		onlyAccepting = false;
	}
</script>

<Seo
	title="Find a Functional Medicine Practitioner — Functional Health Collaborative"
	description="Browse independent functional medicine practitioners backed by comprehensive clinical intelligence — filter by focus area, language, and client availability."
	path="/practitioners"
/>

<!-- ══ BOTANICAL DIRECTORY HERO WITH FALLING LEAVES ══ -->
<section class="dir-hero">
	<div class="leaf-ambient">
		<LeafField count={22} />
	</div>

	<div class="container dir-hero-inner">
		<!-- Bare SVG logo without any box or background -->
		<div class="dir-badge">
			<span class="logo-mark"><BrandMark size={20} /></span>
			<span>Verified Practitioner Directory</span>
		</div>
		<h1>Find the right practitioner, on your terms.</h1>
		<p>
			Discover experienced functional and integrative practitioners backed by peer-reviewed clinical research and deep clinical synthesis. Choose a partner aligned with your unique health goals.
		</p>
	</div>
</section>

<!-- ══ FILTER & SEARCH HUD ══ -->
<div class="container main-content">
	<div class="filter-hud">
		<div class="search-box">
			<Icon name="search" size={16} />
			<input
				type="search"
				placeholder="Search by name, condition, or specialty (e.g. gut, thyroid, autoimmune)…"
				bind:value={q}
				aria-label="Search practitioners"
			/>
			{#if q}
				<button class="clear-btn" onclick={() => (q = '')} aria-label="Clear search">×</button>
			{/if}
		</div>

		<div class="filter-controls">
			<div class="select-wrapper">
				<Icon name="tag" size={14} />
				<select bind:value={specialty} aria-label="Filter by specialty">
					<option value="">All specialties ({specialties.length})</option>
					{#each specialties as s (s)}
						<option value={s}>{s}</option>
					{/each}
				</select>
			</div>

			<label class="toggle-accepting">
				<input type="checkbox" bind:checked={onlyAccepting} />
				<span class="toggle-label">Accepting new clients</span>
			</label>
		</div>
	</div>

	<div class="results-meta">
		<span class="results-count">
			Showing <strong>{filtered.length}</strong> practitioner{filtered.length === 1 ? '' : 's'}
			{#if specialty || q || onlyAccepting}
				with active filters
			{/if}
		</span>
		{#if specialty || q || onlyAccepting}
			<button class="btn-clear-all" onclick={resetFilters}>
				<Icon name="x" size={12} />
				<span>Clear filters</span>
			</button>
		{/if}
	</div>

	<!-- ══ PRACTITIONER CARDS GRID ══ -->
	<div class="directory-grid">
		{#each filtered as p (p.id)}
			<article class="p-card">
				<div class="p-card-header">
					<div class="p-avatar" style={p.photo_path ? `background-image:url(${p.photo_path})` : ''}>
						{#if !p.photo_path}
							<span>{p.name?.[0] ?? '?'}</span>
						{/if}
					</div>

					<div class="p-header-info">
						<div class="p-status-row">
							{#if p.accepting_new_clients}
								<span class="status-badge active">
									<span class="dot"></span>
									Accepting clients
								</span>
							{:else}
								<span class="status-badge waitlist">
									Waitlist only
								</span>
							{/if}
						</div>
						<h2 class="p-name">{p.name}</h2>
						<div class="p-credential-line">
							<span class="credential-item">
								<Icon name="calendar" size={12} />
								{p.years_experience != null ? `${p.years_experience} yrs experience` : 'Verified partner'}
							</span>
							{#if p.languages && p.languages.length}
								<span class="credential-dot">·</span>
								<span class="credential-item">
									<Icon name="globe" size={12} />
									{p.languages.join(', ')}
								</span>
							{/if}
						</div>
					</div>
				</div>

				<p class="p-bio">
					{p.bio || 'Functional health practitioner focused on personalized lifestyle interventions, comprehensive root-cause analysis, and evidence-grounded care.'}
				</p>

				<div class="p-specialties-wrap">
					{#each (p.specialties ?? []).slice(0, 4) as s (s)}
						<span class="specialty-chip">{s}</span>
					{/each}
				</div>

				<div class="p-card-action-bar">
					<a class="btn-view-profile" href="/coach/{p.id}">
						<span>View Profile & Consult</span>
						<Icon name="chevron" size={14} />
					</a>
				</div>
			</article>
		{:else}
			<div class="empty-state-box">
				<div class="empty-icon-wrap">
					<Icon name="users" size={32} />
				</div>
				<h3>No practitioners match your current search</h3>
				<p>Try clearing your focus filters or searching for broader terms like "gut", "hormone", or "nutrition".</p>
				<button class="btn-reset-filters" onclick={resetFilters}>
					Reset All Filters
				</button>
			</div>
		{/each}
	</div>
</div>

<style>
	/* ── Directory Hero ──────────────────────────────────────────────── */
	.dir-hero {
		position: relative;
		background: linear-gradient(155deg, #0d2318 0%, #173827 50%, #102d1f 100%);
		color: #ffffff;
		padding: var(--space-6) 0 var(--space-6);
		overflow: hidden;
		border-bottom: 1px solid rgba(82, 183, 136, 0.2);
	}
	.leaf-ambient {
		position: absolute;
		inset: 0;
		pointer-events: none;
		--leaf-color: rgba(116, 198, 157, 0.4);
	}
	.dir-hero-inner {
		position: relative;
		z-index: 2;
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		max-width: 44rem;
	}
	.dir-badge {
		display: inline-flex;
		align-items: center;
		gap: .5rem;
		padding: .3rem .8rem;
		background: rgba(45, 106, 79, 0.35);
		border: 1px solid rgba(82, 183, 136, 0.4);
		border-radius: 99px;
		color: #d8f3dc;
		font-size: var(--text-xs);
		font-weight: 650;
		width: fit-content;
		backdrop-filter: blur(8px);
	}
	/* Logo mark has ZERO boxes, backgrounds, or borders */
	.logo-mark {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		background: none;
		border: none;
		box-shadow: none;
		color: #74c69d;
	}
	.dir-hero h1 {
		font-size: clamp(2rem, 3.5vw, 2.8rem);
		font-weight: 800;
		letter-spacing: -.025em;
		margin: 0;
		color: #ffffff;
	}
	.dir-hero p {
		font-size: var(--text-base);
		color: #d8f3dc;
		line-height: 1.6;
		margin: 0;
		opacity: 0.95;
	}

	/* ── Main Layout & Filters ───────────────────────────────────────── */
	.main-content {
		padding: var(--space-6) var(--space-5) var(--space-7);
	}
	.filter-hud {
		background: #ffffff;
		border: 1px solid rgba(45, 106, 79, 0.18);
		border-radius: 18px;
		padding: var(--space-4);
		display: flex;
		gap: var(--space-3);
		align-items: center;
		flex-wrap: wrap;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03);
		margin-bottom: var(--space-4);
	}
	.search-box {
		position: relative;
		flex: 1 1 18rem;
		display: flex;
		align-items: center;
		background: #f7faf7;
		border: 1px solid rgba(45, 106, 79, 0.2);
		border-radius: 12px;
		padding: 0 .9rem;
		height: 2.85rem;
		color: #2d6a4f;
	}
	.search-box input {
		width: 100%;
		border: none;
		background: transparent;
		padding: 0 .6rem;
		font-size: var(--text-sm);
		color: #1b4332;
		outline: none;
	}
	.clear-btn {
		background: none;
		border: none;
		color: #6c757d;
		font-size: 1.2rem;
		cursor: pointer;
		padding: 0;
		line-height: 1;
	}
	.clear-btn:hover {
		color: #1b4332;
	}
	.filter-controls {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		flex-wrap: wrap;
	}
	.select-wrapper {
		position: relative;
		display: flex;
		align-items: center;
		background: #f7faf7;
		border: 1px solid rgba(45, 106, 79, 0.2);
		border-radius: 12px;
		padding: 0 .8rem;
		height: 2.85rem;
		color: #2d6a4f;
	}
	.select-wrapper select {
		border: none;
		background: transparent;
		padding: 0 .5rem 0 .4rem;
		font-size: var(--text-sm);
		color: #1b4332;
		font-weight: 600;
		outline: none;
		cursor: pointer;
	}
	.toggle-accepting {
		display: inline-flex;
		align-items: center;
		gap: .45rem;
		font-size: var(--text-sm);
		color: #1b4332;
		font-weight: 600;
		cursor: pointer;
		user-select: none;
		background: #f7faf7;
		border: 1px solid rgba(45, 106, 79, 0.2);
		border-radius: 12px;
		padding: 0 .9rem;
		height: 2.85rem;
	}
	.toggle-accepting input {
		accent-color: #2d6a4f;
		width: 1rem;
		height: 1rem;
		cursor: pointer;
	}
	.results-meta {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
		margin-bottom: var(--space-5);
		font-size: var(--text-sm);
		color: #52796f;
	}
	.btn-clear-all {
		display: inline-flex;
		align-items: center;
		gap: .3rem;
		background: none;
		border: 1px solid #ced4da;
		color: #495057;
		border-radius: 6px;
		padding: .2rem .6rem;
		font-size: var(--text-xs);
		font-weight: 600;
		cursor: pointer;
	}
	.btn-clear-all:hover {
		background: #f8f9fa;
		color: #1b4332;
	}

	/* ── Directory Grid & Cards ──────────────────────────────────────── */
	.directory-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(21rem, 1fr));
		gap: var(--space-5);
	}
	.p-card {
		background: #ffffff;
		border: 1px solid rgba(45, 106, 79, 0.16);
		border-radius: 18px;
		padding: var(--space-5);
		display: flex;
		flex-direction: column;
		gap: .85rem;
		box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03);
		transition: all .2s var(--ease);
	}
	.p-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 12px 30px rgba(45, 106, 79, 0.12);
		border-color: #52b788;
	}
	.p-card-header {
		display: flex;
		gap: var(--space-4);
		align-items: center;
	}
	.p-avatar {
		width: 4.5rem;
		height: 4.5rem;
		border-radius: 50%;
		background: #e8f4ec;
		border: 2px solid #52b788;
		background-size: cover;
		background-position: center;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}
	.p-avatar span {
		font-size: 1.8rem;
		font-weight: 800;
		color: #2d6a4f;
	}
	.p-header-info {
		display: flex;
		flex-direction: column;
		gap: .25rem;
	}
	.p-status-row {
		display: flex;
		align-items: center;
	}
	.status-badge {
		display: inline-flex;
		align-items: center;
		gap: .35rem;
		font-size: var(--text-xs);
		font-weight: 650;
		border-radius: 99px;
		padding: .15rem .55rem;
	}
	.status-badge.active {
		color: #2d6a4f;
		background: #e8f4ec;
	}
	.status-badge .dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #2d6a4f;
	}
	.status-badge.waitlist {
		color: #6c757d;
		background: #f1f3f5;
	}
	.p-name {
		font-size: 1.3rem;
		font-weight: 750;
		color: #1b4332;
		margin: 0;
		letter-spacing: -.01em;
	}
	.p-credential-line {
		display: flex;
		align-items: center;
		gap: .4rem;
		font-size: var(--text-xs);
		color: #6c757d;
		flex-wrap: wrap;
	}
	.credential-item {
		display: flex;
		align-items: center;
		gap: .25rem;
	}
	.p-bio {
		font-size: var(--text-sm);
		color: #495057;
		line-height: 1.55;
		margin: 0;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.p-specialties-wrap {
		display: flex;
		flex-wrap: wrap;
		gap: .4rem;
	}
	.specialty-chip {
		font-size: var(--text-xs);
		font-weight: 600;
		color: #1b4332;
		background: #e8f4ec;
		padding: .25rem .65rem;
		border-radius: 6px;
	}
	.p-card-action-bar {
		margin-top: auto;
		padding-top: var(--space-3);
		border-top: 1px solid rgba(45, 106, 79, 0.1);
	}
	.btn-view-profile {
		display: inline-flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: .65rem .95rem;
		background: #2d6a4f;
		color: #ffffff;
		border-radius: 10px;
		font-size: var(--text-sm);
		font-weight: 700;
		text-decoration: none;
		transition: background .15s ease;
	}
	.btn-view-profile:hover {
		background: #1b4332;
	}

	/* ── Empty State ─────────────────────────────────────────────────── */
	.empty-state-box {
		grid-column: 1 / -1;
		background: #ffffff;
		border: 1px dashed rgba(45, 106, 79, 0.3);
		border-radius: 20px;
		padding: var(--space-7) var(--space-5);
		text-align: center;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-3);
		color: #495057;
	}
	.empty-icon-wrap {
		width: 4rem;
		height: 4rem;
		border-radius: 50%;
		background: #e8f4ec;
		color: #2d6a4f;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.empty-state-box h3 {
		font-size: var(--text-xl);
		color: #1b4332;
		margin: 0;
		font-weight: 750;
	}
	.empty-state-box p {
		max-width: 28rem;
		margin: 0;
		font-size: var(--text-sm);
		color: #6c757d;
	}
	.btn-reset-filters {
		margin-top: var(--space-2);
		background: #2d6a4f;
		color: #ffffff;
		border: none;
		padding: .6rem 1.4rem;
		border-radius: 10px;
		font-weight: 700;
		font-size: var(--text-sm);
		cursor: pointer;
		transition: background .15s ease;
	}
	.btn-reset-filters:hover {
		background: #1b4332;
	}

	/* ── Mobile Responsiveness ───────────────────────────────────────── */
	@media (max-width: 640px) {
		.filter-hud {
			flex-direction: column;
			align-items: stretch;
		}
		.filter-controls {
			flex-direction: column;
			align-items: stretch;
		}
		.select-wrapper, .toggle-accepting {
			width: 100%;
		}
		.select-wrapper select {
			width: 100%;
		}
	}
</style>
