<script lang="ts">
	import { browser } from '$app/environment';
	import { PUBLIC_SITE_URL } from '$env/static/public';
	import { get } from '$lib/api';
	import Sprig from '$lib/components/Sprig.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import LeafField from '$lib/components/LeafField.svelte';
	import NetworkArt from '$lib/components/art/NetworkArt.svelte';
	import GroundedArt from '$lib/components/art/GroundedArt.svelte';
	import PractitionerArt from '$lib/components/art/PractitionerArt.svelte';
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
		"Find a practitioner backed by an AI assistant tuned only to their own curated knowledge base — every answer cited, independently checked, and never sourced from the open internet.";

	const orgJsonLd = {
		'@context': 'https://schema.org',
		'@type': 'Organization',
		name: 'Functional Health Collab',
		url: PUBLIC_SITE_URL,
		description,
		logo: `${PUBLIC_SITE_URL}/favicon.svg`
	};

	// Client-facing first (direct instruction) — these explain why a
	// client can trust what they hear, not how the pipeline works
	// internally. Practitioner-facing copy lives further down, in its
	// own section, not interleaved here.
	const pillars = [
		{ n: '01', title: 'Nothing here is a guess', body: 'Every answer your practitioner’s AI gives comes from their own curated library — never the open internet.' },
		{ n: '02', title: 'You can check every claim', body: 'Click a citation, jump straight to the exact passage — page number included. Nothing is taken on faith.' },
		{ n: '03', title: 'A second check, every time', body: 'An independent AI verifies each answer against its sources before your practitioner ever sees it.' },
		{ n: '04', title: 'Your practitioner sets the bar', body: 'A reliability grade on every source means they decide what the AI is allowed to use — not the other way around.' }
	];
</script>

<Seo title="Functional Health Collab — practitioners backed by grounded, cited AI" {description} path="/" />
<svelte:head>{@html jsonLdScript(orgJsonLd)}</svelte:head>

<!-- Full rebuild: an asymmetric split hero (copy left, a real
     illustration right, leaves as the ambient layer behind both), a
     numbered editorial list paired with its own illustration instead
     of a bare icon-card grid, and a dedicated practitioner-facing
     section near the end rather than interleaved with the client-
     facing copy above it — client-first ordering per direct
     instruction, practitioners addressed second. -->
<section class="hero">
	<LeafField count={32} />
	<div class="hero-inner">
		<div class="hero-copy">
			<span class="mark"><Sprig size={22} /></span>
			<h1>Practitioners who can help <span class="accent-word">more</span> — with an AI that only knows your library</h1>
			<p>
				No open-internet guesses. Every practitioner here works with an AI assistant
				tuned only to their own vetted knowledge base — so they spend less time
				searching, and more time on you.
			</p>
			<div class="hero-cta">
				<a class="btn filled" href="/practitioners">Find a practitioner</a>
				<a class="btn ghost" href="/join">I'm a practitioner</a>
			</div>
		</div>
		<div class="hero-art" aria-hidden="true"><NetworkArt size={200} /></div>
	</div>
</section>

<section class="lede-row">
	<p class="lede">
		Generic AI tools answer from whatever they happened to absorb during training —
		no way to know if it's current, sourced, or safe to act on.
	</p>
	<p class="lede accent">
		Here, it's different: the AI your practitioner uses can only ever answer from the
		library they curated and graded themselves, and every answer ships with the receipts.
	</p>
</section>

<section class="pillars-row container">
	<div class="pillars-art" aria-hidden="true"><GroundedArt size={176} /></div>
	<div class="pillars">
		{#each pillars as p (p.n)}
			<div class="pillar" use:reveal>
				<span class="pillar-n">{p.n}</span>
				<div>
					<h3>{p.title}</h3>
					<p>{p.body}</p>
				</div>
			</div>
		{/each}
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

<!-- Practitioner-facing pitch — addressed second, per direct
     instruction, after every section above has spoken to a client. -->
<section class="for-practitioners">
	<div class="container fp-inner">
		<div class="fp-copy">
			<Chip tone="accent">For practitioners</Chip>
			<h2>Help more clients, without cutting corners</h2>
			<p>
				Your own AI assistant, tuned only to the knowledge base you build and grade
				yourself — never the open internet. Answer faster, go deeper, and take on more
				clients, while staying grounded in exactly what you trust.
			</p>
			<blockquote>
				"Every role on the team — the one that reads a new source, the one that builds
				the knowledge graph, the one that writes the answer, the one that checks it
				against its sources — is a deliberately separated, purpose-picked model. The one
				that checks the answer isn't even a chat model — it's a dedicated
				anti-hallucination classifier, built for exactly that one job."
			</blockquote>
			<div class="chip-row">
				<Chip tone="accent">Grounded answers</Chip>
				<Chip tone="accent">Inline citations</Chip>
				<Chip tone="accent">Independent verification</Chip>
				<Chip tone="accent">Full audit trail</Chip>
			</div>
			<a class="btn filled" href="/join">Apply as a practitioner</a>
		</div>
		<div class="fp-art" aria-hidden="true"><PractitionerArt size={200} /></div>
	</div>
</section>

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
		display: flex; align-items: center; justify-content: space-between; gap: var(--space-6);
	}
	.hero-copy { display: flex; flex-direction: column; gap: var(--space-4); max-width: 34rem; }
	.mark { color: #ffd7dd; }
	.hero h1 { font-size: 3.2rem; line-height: 1.05; font-weight: 750; letter-spacing: -.02em; color: #fff; }
	.hero h1 .accent-word { color: #ffd7dd; }
	.hero p { color: #fbdfe3; font-size: var(--text-lg); max-width: 32rem; }
	.hero-cta { display: flex; gap: var(--space-3); flex-wrap: wrap; margin-top: var(--space-2); }
	.hero :global(.field) { --leaf-color: #ffe8eb; }
	.hero .btn.ghost { border-color: rgba(255, 255, 255, .5); color: #fff; background: transparent; }
	.hero-art { position: relative; z-index: 1; flex: 0 0 auto; color: #ffd7dd; opacity: .9; }
	@media (max-width: 860px) {
		.hero h1 { font-size: 2.2rem; }
		.hero-art { display: none; }
	}

	.lede-row {
		display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-6);
		max-width: var(--container-max); margin: 0 auto; padding: var(--space-6) var(--space-5);
		border-top: 1px solid var(--line); border-bottom: 1px solid var(--line);
	}
	.lede { font-size: var(--text-xl); line-height: 1.5; margin: 0; }
	.lede.accent { color: var(--accent-ink); font-weight: 650; }
	@media (max-width: 760px) { .lede-row { grid-template-columns: 1fr; } }

	.pillars-row { padding: var(--space-7) var(--space-5); display: flex; gap: var(--space-7); align-items: flex-start; }
	.pillars-art { flex: 0 0 auto; color: var(--accent); position: sticky; top: var(--space-6); }
	.pillars { flex: 1 1 auto; display: grid; gap: var(--space-6); min-width: 0; }
	.pillar { display: grid; grid-template-columns: 5rem 1fr; gap: var(--space-5); border-top: 1px solid var(--line); padding-top: var(--space-5); opacity: 0; }
	.pillar:global(.revealed) { animation: liftIn var(--duration-slow) var(--ease) both; }
	.pillar-n { font-size: 2.2rem; font-weight: 750; color: var(--line-2); }
	.pillar h3 { font-size: var(--text-xl); margin-bottom: .4rem; }
	.pillar p { color: var(--muted); max-width: 32rem; }
	@media (max-width: 760px) { .pillars-row { flex-direction: column; gap: var(--space-5); } .pillars-art { position: static; } }
	@media (max-width: 600px) { .pillar { grid-template-columns: 1fr; gap: .4rem; } .pillar-n { font-size: 1.4rem; } }

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

	.for-practitioners { background: var(--panel-2); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); padding: var(--space-7) 0; }
	.fp-inner { display: flex; align-items: center; justify-content: space-between; gap: var(--space-7); }
	.fp-copy { display: flex; flex-direction: column; gap: var(--space-4); max-width: 36rem; }
	.fp-copy h2 { font-size: var(--text-2xl); }
	.fp-copy p { color: var(--ink-2); font-size: var(--text-base); }
	.fp-copy blockquote { margin: 0; padding-left: var(--space-4); border-left: 2px solid var(--accent); color: var(--ink); font-style: italic; font-size: var(--text-sm); }
	.chip-row { display: flex; flex-wrap: wrap; gap: .5rem; }
	.fp-art { flex: 0 0 auto; color: var(--accent); }
	@media (max-width: 860px) { .fp-inner { flex-direction: column; } .fp-art { align-self: flex-start; } }

	.cta-band { background: linear-gradient(145deg, var(--rail-top), var(--rail-bottom)); color: #fff; padding: var(--space-7) 0; }
	.cta-inner { display: flex; align-items: center; justify-content: space-between; gap: var(--space-6); flex-wrap: wrap; }
	.cta-inner p { font-size: var(--text-xl); font-weight: 650; margin-bottom: var(--space-3); }
	.btn.filled, .btn.ghost { padding: .7rem 1.4rem; text-decoration: none; font-size: var(--text-sm); font-weight: 700; display: inline-block; border-radius: var(--r); }
	.btn.filled { background: var(--accent); color: #fff; }
	.btn.ghost { border: 1px solid var(--line-2); color: var(--ink); background: var(--panel); }
	.cta-band .btn.ghost { border-color: rgba(255,255,255,.4); color: #fff; background: transparent; }
</style>
