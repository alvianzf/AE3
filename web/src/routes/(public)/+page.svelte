<script lang="ts">
	import { browser } from '$app/environment';
	import { PUBLIC_SITE_URL } from '$env/static/public';
	import { get } from '$lib/api';
	import Sprig from '$lib/components/Sprig.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import LeafField from '$lib/components/LeafField.svelte';
	import { jsonLdScript } from '$lib/seo';
	import { reveal } from '$lib/actions/reveal';

	let { data } = $props();
	let practitioners = $state(data.practitioners);
	$effect(() => {
		if (!browser) return;
		get(fetch, '/practitioners').then((list) => { practitioners = list; }).catch(() => {});
	});
	const available = $derived((practitioners ?? []).filter((p: any) => p.accepting_new_clients));

	const description =
		"Functional Health Collab gives independent practitioners an AI assistant grounded in their own curated library — every answer cited, independently checked, and never sourced from the open internet.";

	const orgJsonLd = {
		'@context': 'https://schema.org',
		'@type': 'Organization',
		name: 'Functional Health Collab',
		url: PUBLIC_SITE_URL,
		description,
		logo: `${PUBLIC_SITE_URL}/favicon.svg`
	};

	const pillars = [
		{ n: '01', title: 'Trained on what you teach it', body: 'Every answer comes from your own curated library — never the open internet, never a guess.' },
		{ n: '02', title: 'Every claim is cited', body: 'Click a citation, jump straight to the source passage — page number included. Nothing is taken on faith.' },
		{ n: '03', title: 'An independent check, every time', body: 'A second AI verifies each answer against its sources before a practitioner ever sees it, and says so when it can’t confirm a claim.' },
		{ n: '04', title: 'You set the bar', body: 'A reliability grade on every source, and a slider that controls what’s reachable — you decide what the AI is allowed to use.' }
	];
</script>

<Seo title="Functional Health Collab — grounded, cited AI for independent practitioners" {description} path="/" />
<svelte:head>{@html jsonLdScript(orgJsonLd)}</svelte:head>

<!-- Full rebuild: an asymmetric split hero (copy left, the leaves given
     their own real visual panel on the right, not just a faint wash
     behind text), a numbered editorial list instead of an icon-card
     grid, and a horizontal-scroll strip for practitioners instead of a
     static grid. Nothing here reuses the old centered-hero/card-grid
     template. -->
<section class="hero">
	<LeafField count={32} />
	<div class="hero-inner">
		<div class="hero-copy">
			<span class="mark"><Sprig size={22} /></span>
			<h1>An AI assistant practitioners can <span class="accent-word">put their name behind</span></h1>
			<p>
				Functional Health Collab connects clients with independent practitioners and gives every
				one of them an AI-assisted knowledge base — grounded, cited, and checked
				before a single word reaches a client record.
			</p>
			<div class="hero-cta">
				<a class="btn filled" href="/practitioners">Find a practitioner</a>
				<a class="btn ghost" href="/join">I'm a practitioner</a>
			</div>
		</div>
	</div>
</section>

<section class="lede-row">
	<p class="lede">
		Generic AI tools answer from whatever they happened to absorb during training —
		no way to know if it's current, sourced, or safe to act on.
	</p>
	<p class="lede accent">
		Functional Health Collab works differently: a practitioner's AI can only ever
		answer from the library they curated and graded themselves, and every answer
		ships with the receipts.
	</p>
</section>

<section class="pillars container">
	{#each pillars as p (p.n)}
		<div class="pillar" use:reveal>
			<span class="pillar-n">{p.n}</span>
			<div>
				<h3>{p.title}</h3>
				<p>{p.body}</p>
			</div>
		</div>
	{/each}
</section>

<section class="trust">
	<div class="container trust-inner">
		<Sprig size={26} />
		<p class="quote">
			"Every role on the team — the one that reads a new source, the one that
			builds the knowledge graph, the one that writes the answer, the one that
			checks it against its sources — is a deliberately separated, purpose-picked
			model. The one that checks the answer isn't even a chat model — it's a
			dedicated anti-hallucination classifier, built for exactly that one job."
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
	<section class="practitioners">
		<div class="container ph-row">
			<h2>Practitioners taking new clients</h2>
			<a class="seeall" href="/practitioners">See all →</a>
		</div>
		<div class="strip">
			{#each available as pr (pr.id)}
				<a class="pr-card" href="/coach/{pr.id}">
					<div class="photo" style={pr.photo_path ? `background-image:url(${pr.photo_path})` : ''}>
						{#if !pr.photo_path}<span>{pr.name?.[0] ?? '?'}</span>{/if}
					</div>
					<h3>{pr.name}</h3>
					<span class="available-dot">Accepting new clients</span>
					<div class="chip-row">
						{#each (pr.specialties ?? []).slice(0, 2) as s (s)}<Chip tone="accent">{s}</Chip>{/each}
					</div>
				</a>
			{/each}
		</div>
	</section>
{/if}

<section class="cta-band">
	<div class="container cta-inner">
		<div>
			<p>Ready to look for a practitioner?</p>
			<a class="btn filled" href="/practitioners">Browse practitioners</a>
		</div>
		<div>
			<p>Curious what it looks like from the inside?</p>
			<a class="btn ghost" href="/join">Apply as a practitioner</a>
		</div>
	</div>
</section>

<style>
	/* Direct feedback: the hero (and the closing band below) get a real
	   red background now — the brand gradient filling the section, not
	   just a faint accent on one word. */
	.hero {
		background: linear-gradient(145deg, var(--rail-top), var(--rail-bottom));
		position: relative; overflow: hidden;
	}
	.hero-inner {
		position: relative; z-index: 1; padding: var(--space-7) var(--space-5);
		max-width: var(--container-max); margin: 0 auto;
	}
	.hero-copy { display: flex; flex-direction: column; gap: var(--space-4); max-width: 34rem; }
	.mark { color: #ffd7dd; }
	.hero h1 { font-size: 3.2rem; line-height: 1.05; font-weight: 750; letter-spacing: -.02em; color: #fff; }
	.hero h1 .accent-word { color: #ffd7dd; }
	.hero p { color: #fbdfe3; font-size: var(--text-lg); max-width: 32rem; }
	.hero-cta { display: flex; gap: var(--space-3); flex-wrap: wrap; margin-top: var(--space-2); }
	.hero :global(.field) { --leaf-color: #ffe8eb; }
	.hero .btn.ghost { border-color: rgba(255, 255, 255, .5); color: #fff; background: transparent; }
	@media (max-width: 860px) {
		.hero h1 { font-size: 2.2rem; }
	}

	.lede-row {
		display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-6);
		max-width: var(--container-max); margin: 0 auto; padding: var(--space-6) var(--space-5);
		border-top: 1px solid var(--line); border-bottom: 1px solid var(--line);
	}
	.lede { font-size: var(--text-xl); line-height: 1.5; margin: 0; }
	.lede.accent { color: var(--accent-ink); font-weight: 650; }
	@media (max-width: 760px) { .lede-row { grid-template-columns: 1fr; } }

	.pillars { padding: var(--space-7) var(--space-5); display: grid; gap: var(--space-6); }
	.pillar { display: grid; grid-template-columns: 5rem 1fr; gap: var(--space-5); border-top: 1px solid var(--line); padding-top: var(--space-5); opacity: 0; }
	.pillar:global(.revealed) { animation: liftIn var(--duration-slow) var(--ease) both; }
	.pillar-n { font-size: 2.2rem; font-weight: 750; color: var(--line-2); }
	.pillar h3 { font-size: var(--text-xl); margin-bottom: .4rem; }
	.pillar p { color: var(--muted); max-width: 32rem; }
	@media (max-width: 600px) { .pillar { grid-template-columns: 1fr; gap: .4rem; } .pillar-n { font-size: 1.4rem; } }

	.trust { background: var(--panel-2); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); padding: var(--space-7) 0; }
	.trust-inner { display: flex; flex-direction: column; align-items: center; gap: var(--space-4); text-align: center; color: var(--accent); max-width: 46rem; }
	.quote { font-size: var(--text-xl); line-height: 1.5; color: var(--ink); font-style: italic; }
	.chip-row { display: flex; flex-wrap: wrap; justify-content: center; gap: .5rem; }

	.practitioners { padding: var(--space-7) 0; }
	.ph-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-5); }
	.ph-row h2 { font-size: var(--text-2xl); }
	.seeall { color: var(--accent-ink); font-weight: 650; text-decoration: none; }
	.strip { display: flex; gap: var(--space-4); overflow-x: auto; padding: 0 var(--space-5) var(--space-2); scroll-snap-type: x mandatory; }
	.pr-card {
		flex: 0 0 14rem; scroll-snap-align: start; display: flex; flex-direction: column; gap: .4rem;
		border: 1px solid var(--line); background: var(--panel); padding: var(--space-4); text-decoration: none; color: inherit;
	}
	.pr-card:hover { border-color: var(--accent); }
	.photo { width: 3.5rem; height: 3.5rem; border-radius: 50%; background: var(--accent-soft); background-size: cover; background-position: center; display: flex; align-items: center; justify-content: center; }
	.photo span { font-size: 1.2rem; font-weight: 700; color: var(--accent-ink); }
	.pr-card h3 { font-size: var(--text-base); }
	.available-dot { display: inline-flex; align-items: center; gap: .35rem; font-size: var(--text-xs); color: var(--ok); font-weight: 650; }
	.available-dot::before { content: ''; width: .4rem; height: .4rem; border-radius: 50%; background: var(--ok); }

	.cta-band { background: linear-gradient(145deg, var(--rail-top), var(--rail-bottom)); color: #fff; padding: var(--space-7) 0; }
	.cta-inner { display: flex; align-items: center; justify-content: space-between; gap: var(--space-6); flex-wrap: wrap; }
	.cta-inner p { font-size: var(--text-xl); font-weight: 650; margin-bottom: var(--space-3); }
	.btn.filled, .btn.ghost { padding: .7rem 1.4rem; text-decoration: none; font-size: var(--text-sm); font-weight: 700; display: inline-block; }
	.btn.filled { background: var(--accent); color: #fff; }
	.btn.ghost { border: 1px solid var(--line-2); color: var(--ink); background: var(--panel); }
	.cta-band .btn.ghost { border-color: rgba(255,255,255,.4); color: #fff; background: transparent; }
</style>
