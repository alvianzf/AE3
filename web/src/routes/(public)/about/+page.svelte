<script lang="ts">
	import Sprig from '$lib/components/Sprig.svelte';
	import Chip from '$lib/components/Chip.svelte';

	const pillars = [
		{
			title: 'Trained on what you teach it',
			body: 'Every answer comes from your clinic’s own curated library — never the open internet, never a guess.'
		},
		{
			title: 'Every claim is cited',
			body: 'Click a citation, jump straight to the source passage — page number included. Nothing is taken on faith.'
		},
		{
			title: 'An independent check, every time',
			body: 'A second AI verifies each answer against its sources before a practitioner ever sees it, and says so when it can’t confirm a claim.'
		},
		{
			title: 'You set the bar',
			body: 'A reliability grade on every source, and a slider that controls what’s reachable — your clinic decides what the AI is allowed to use.'
		}
	];
</script>

<svelte:head><title>About — Clinic</title></svelte:head>

<section class="hero">
	<div class="container heroin">
		<span class="sprigbig"><Sprig size={30} /></span>
		<h1>An AI assistant practitioners can put their name behind.</h1>
		<p>
			Clinic connects clients with independent practitioners and gives every
			one of them an AI-assisted knowledge base — grounded, cited, and
			checked before a single word reaches a client record.
		</p>
	</div>
</section>

<div class="container about">
	<section class="pitch">
		<p class="lede">
			Generic AI tools answer from whatever they happened to absorb during
			training — no way to know if it’s current, sourced, or safe to act
			on. Clinic works differently: a practitioner’s AI can only ever answer
			from the library their clinic curated and graded itself, and every
			answer ships with the receipts.
		</p>
	</section>

	<section class="pillars">
		{#each pillars as p (p.title)}
			<div class="pillar">
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
				that decides what’s worth opening, the one that writes the answer,
				the one that checks it — is an Anthropic Claude model. No second
				vendor, no black-box pipeline stitched together from whatever was
				cheapest that week. Four deliberately separated jobs, one model
				family, fully accountable.
			</p>
			<div class="chip-row">
				<Chip tone="accent">Grounded answers</Chip>
				<Chip tone="accent">Inline citations</Chip>
				<Chip tone="accent">Independent verification</Chip>
				<Chip tone="accent">Full audit trail</Chip>
			</div>
		</div>
	</section>

	<section class="cta">
		<p>Curious what it looks like from the inside?</p>
		<a class="btn filled" href="/join">Apply as a practitioner</a>
	</section>
</div>

<style>
	.hero {
		background: linear-gradient(135deg, var(--rail-top), var(--rail-bottom));
		color: #fdf1f2; padding: var(--space-7) 0; margin-bottom: var(--space-6);
	}
	.heroin { display: flex; flex-direction: column; gap: var(--space-3); max-width: 42rem; }
	.sprigbig { color: #ffb9c4; }
	.hero h1 { font-size: var(--text-3xl); font-weight: 750; }
	.hero p { color: #f7dfe2; font-size: var(--text-lg); }

	.about { max-width: 46rem; padding-bottom: var(--space-7); display: grid; gap: var(--space-6); }
	.lede { font-size: var(--text-lg); color: var(--ink-2); line-height: 1.6; }

	.pillars { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); }
	.pillar {
		padding: var(--space-4); border: 1px solid var(--line); border-radius: var(--r-lg);
		background: var(--panel); animation: liftIn .4s var(--ease) both;
	}
	.pillar h3 { font-size: var(--text-base); margin-bottom: .4rem; }
	.pillar p { color: var(--muted); font-size: var(--text-sm); }

	.chip-row { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: var(--space-4); }

	.cta { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; }
	.cta p { font-size: var(--text-lg); font-weight: 650; }
	.btn.filled {
		background: var(--accent); color: #fff; padding: .6rem 1.2rem; border-radius: 99px;
		text-decoration: none; font-size: var(--text-sm); font-weight: 700;
	}
</style>
