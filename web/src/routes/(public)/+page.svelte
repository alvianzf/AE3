<script lang="ts">
	import { browser } from '$app/environment';
	import { PUBLIC_SITE_URL } from '$env/static/public';
	import { get } from '$lib/api';
	import Sprig from '$lib/components/Sprig.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import ParticleField from '$lib/components/ParticleField.svelte';
	import { jsonLdScript } from '$lib/seo';
	import { reveal } from '$lib/actions/reveal';

	let { data } = $props();
	let practitioners = $state(data.practitioners);
	$effect(() => {
		if (!browser) return;
		get(fetch, '/practitioners').then((list) => { practitioners = list; }).catch(() => {});
	});
	// specs/v8 §8.1 — "highlight practitioners that are available": a new
	// section, not a restyle of anything that already exists. Only
	// practitioners who've explicitly opted in (accepting_new_clients —
	// defaults to FALSE, never auto-listed) ever show up here.
	const available = $derived((practitioners ?? []).filter((p: any) => p.accepting_new_clients).slice(0, 4));

	const description =
		"Clinic gives independent practitioners an AI assistant grounded in their own curated library — every answer cited, independently checked, and never sourced from the open internet.";

	// Organization schema — the baseline structured-data signal search
	// engines and AI answer engines (GEO) both use to understand what the
	// site/company actually is, independent of page copy.
	const orgJsonLd = {
		'@context': 'https://schema.org',
		'@type': 'Organization',
		name: 'Clinic',
		url: PUBLIC_SITE_URL,
		description,
		logo: `${PUBLIC_SITE_URL}/favicon.svg`
	};

	const pillars = [
		{
			icon: 'book',
			title: 'Trained on what you teach it',
			body: 'Every answer comes from your clinic’s own curated library — never the open internet, never a guess.'
		},
		{
			icon: 'file',
			title: 'Every claim is cited',
			body: 'Click a citation, jump straight to the source passage — page number included. Nothing is taken on faith.'
		},
		{
			icon: 'check',
			title: 'An independent check, every time',
			body: 'A second AI verifies each answer against its sources before a practitioner ever sees it, and says so when it can’t confirm a claim.'
		},
		{
			icon: 'settings',
			title: 'You set the bar',
			body: 'A reliability grade on every source, and a slider that controls what’s reachable — your clinic decides what the AI is allowed to use.'
		}
	];
</script>

<Seo
	title="Clinic — grounded, cited AI for independent practitioners"
	{description}
	path="/"
/>
<svelte:head>
	{@html jsonLdScript(orgJsonLd)}
</svelte:head>

<!-- specs/v4.1/01 — the root used to be the practitioner directory, with no
     product information anywhere upstream of it (that content lived on
     /about, one nav link away). This is now the landing page: information
     first, two equal-weight CTAs into the two things a visitor might
     actually be here to do — find a practitioner, or become one. The
     former root content (search/filter/grid) moved to /practitioners
     unchanged; /about redirects here rather than duplicating this pitch. -->
<section class="hero">
	<ParticleField />
	<div class="container heroin">
		<span class="sprigbig"><Sprig size={30} /></span>
		<h1>An AI assistant practitioners can put their name behind.</h1>
		<p>
			Clinic connects clients with independent practitioners and gives every
			one of them an AI-assisted knowledge base — grounded, cited, and
			checked before a single word reaches a client record.
		</p>
		<div class="hero-cta">
			<a class="btn filled" href="/practitioners">Find a practitioner</a>
			<a class="btn ghost" href="/join">I'm a practitioner</a>
		</div>
	</div>
</section>

<div class="container about">
	<section class="pitch" use:reveal>
		<p class="lede">
			Generic AI tools answer from whatever they happened to absorb during
			training — no way to know if it’s current, sourced, or safe to act
			on. Clinic works differently: a practitioner’s AI can only ever answer
			from the library their clinic curated and graded itself, and every
			answer ships with the receipts.
		</p>
	</section>

	<section class="pillars">
		{#each pillars as p, i (p.title)}
			<div class="pillar" use:reveal style="--reveal-delay: {i * 60}ms">
				<span class="pillar-icon"><Icon name={p.icon} size={20} /></span>
				<h3>{p.title}</h3>
				<p>{p.body}</p>
			</div>
		{/each}
	</section>

	<section class="trust card-panel leafmark">
		<div class="ph botanic"><h2><Sprig /> One accountable AI team</h2></div>
		<div class="pb">
			<p>
				Every role on the team — the one that reads a new source, the one
				that builds the knowledge graph, the one that decides what’s worth
				opening, the one that writes the answer, the one that checks it
				against its sources — is a deliberately separated, purpose-picked
				model, not one black-box pipeline stitched together from whatever
				was cheapest that week. Each job gets the model actually suited to
				it, and the one that checks the answer isn’t even a chat model at
				all — it’s a dedicated anti-hallucination classifier, built for
				exactly that one job.
			</p>
			<div class="chip-row">
				<Chip tone="accent">Grounded answers</Chip>
				<Chip tone="accent">Inline citations</Chip>
				<Chip tone="accent">Independent verification</Chip>
				<Chip tone="accent">Full audit trail</Chip>
			</div>
		</div>
	</section>

	{#if available.length}
		<section class="practitioners" use:reveal>
			<div class="ph"><h2>Practitioners taking new clients</h2><a class="seeall" href="/practitioners">See all →</a></div>
			<div class="grid">
				{#each available as pr, i (pr.id)}
					<a class="card" href="/coach/{pr.id}" style="--reveal-delay: {i * 60}ms">
						<div class="photo" style={pr.photo_path ? `background-image:url(${pr.photo_path})` : ''}>
							{#if !pr.photo_path}<span>{pr.name?.[0] ?? '?'}</span>{/if}
						</div>
						<div class="body">
							<h3>{pr.name}</h3>
							<span class="available-dot">Accepting new clients</span>
							<div class="chip-row">
								{#each (pr.specialties ?? []).slice(0, 2) as s (s)}<Chip tone="accent">{s}</Chip>{/each}
							</div>
						</div>
					</a>
				{/each}
			</div>
		</section>
	{/if}

	<section class="cta" use:reveal>
		<div>
			<p>Ready to look for a practitioner?</p>
			<a class="btn filled" href="/practitioners">Browse practitioners</a>
		</div>
		<div>
			<p>Curious what it looks like from the inside?</p>
			<a class="btn ghost" href="/join">Apply as a practitioner</a>
		</div>
	</section>
</div>

<style>
	.hero {
		position: relative; overflow: hidden;
		background: linear-gradient(135deg, var(--rail-top), var(--rail-bottom));
		color: #fdf1f2; padding: var(--space-7) 0; margin-bottom: var(--space-6);
	}
	.heroin { position: relative; z-index: 1; display: flex; flex-direction: column; gap: var(--space-3); max-width: 42rem; }
	.sprigbig { color: #ffb9c4; }
	.hero h1 { font-size: var(--text-3xl); font-weight: 750; }
	.hero p { color: #f7dfe2; font-size: var(--text-lg); }
	.hero-cta { display: flex; gap: var(--space-3); flex-wrap: wrap; margin-top: var(--space-2); }

	.about { max-width: 46rem; padding-bottom: var(--space-7); display: grid; gap: var(--space-6); }
	.lede { font-size: var(--text-lg); color: var(--ink-2); line-height: 1.6; }

	.pillars { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); }
	.pillar {
		padding: var(--space-4); border: 1px solid var(--line); border-radius: var(--r-lg);
		background: var(--panel);
	}
	.pillar-icon {
		display: inline-flex; align-items: center; justify-content: center;
		width: 2.4rem; height: 2.4rem; border-radius: var(--r); margin-bottom: var(--space-2);
		background: var(--accent-soft); color: var(--accent-ink);
	}
	.pillar h3 { font-size: var(--text-base); margin-bottom: .4rem; }
	.pillar p { color: var(--muted); font-size: var(--text-sm); }

	.chip-row { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: var(--space-4); }

	.practitioners { opacity: 0; }
	.practitioners:global(.revealed) { animation: liftIn var(--duration-slow) var(--ease) both; }
	.practitioners .ph { padding: 0 0 var(--space-3); border-bottom: none; }
	.practitioners .ph h2 { font-size: var(--text-xl); }
	.seeall { color: var(--accent-ink); font-size: var(--text-sm); font-weight: 650; text-decoration: none; }
	.practitioners .grid { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); }
	.practitioners .card {
		display: flex; flex-direction: column; background: var(--panel); border: 1px solid var(--line);
		border-radius: var(--r-lg); overflow: hidden; text-decoration: none; color: inherit;
		box-shadow: var(--shadow); transition: transform .18s var(--ease), box-shadow .18s var(--ease);
	}
	.practitioners .card:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); }
	.practitioners .photo { height: 6rem; background: var(--accent-soft); background-size: cover; background-position: center; display: flex; align-items: center; justify-content: center; }
	.practitioners .photo span { font-size: 1.5rem; font-weight: 700; color: var(--accent-ink); }
	.practitioners .body { padding: var(--space-3); display: flex; flex-direction: column; gap: .35rem; }
	.practitioners h3 { font-size: var(--text-base); }
	.available-dot { display: inline-flex; align-items: center; gap: .35rem; font-size: var(--text-xs); color: var(--ok); font-weight: 650; }
	.available-dot::before { content: ''; width: .4rem; height: .4rem; border-radius: 50%; background: var(--ok); }

	/* specs/v7/06 — scroll-triggered reveal: every use:reveal element
	   starts invisible/offset and only plays liftIn once the reveal
	   action adds .revealed (on scroll-into-view, or immediately for
	   prefers-reduced-motion — see reveal.ts). --reveal-delay staggers
	   the pillar grid's four cards instead of having them all pop at
	   once. .trust is deliberately NOT part of this — it already has
	   its own mount-time entrance via the shared .card-panel class
	   (app.css), and a "both" fill-mode keyframe animation finishing on
	   mount would leave it at opacity:1 well before it scrolls into
	   view, defeating (and visually conflicting with) a second,
	   scroll-gated opacity:0 start state layered on top. Scoped to this
	   page's own elements, not a global rule — a future page adopting
	   this pattern gets the same two rules copied in deliberately, per
	   specs/v7/07's "port each page's own styling, don't globalize
	   blind" phasing norm. */
	.pitch, .pillar, .cta { opacity: 0; }
	.pitch:global(.revealed), .pillar:global(.revealed), .cta:global(.revealed) {
		animation: liftIn var(--duration-slow) var(--ease) both;
		animation-delay: var(--reveal-delay, 0ms);
	}

	.cta { display: flex; align-items: center; gap: var(--space-6); flex-wrap: wrap; }
	.cta > div { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; }
	.cta p { font-size: var(--text-lg); font-weight: 650; }
	.btn.filled, .btn.ghost {
		padding: .6rem 1.2rem; border-radius: 99px; text-decoration: none;
		font-size: var(--text-sm); font-weight: 700;
	}
	.btn.filled { background: var(--accent); color: #fff; }
	.btn.ghost { border: 1px solid var(--line-2); color: var(--ink); }
	.hero .btn.ghost { border-color: rgba(255, 255, 255, .5); color: #fdf1f2; }
</style>
