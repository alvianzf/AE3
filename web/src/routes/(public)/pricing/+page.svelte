<script lang="ts">
	import Seo from '$lib/components/Seo.svelte';
	import Icon from '$lib/components/Icon.svelte';

	// specs/v8 §8.2 — flagged explicitly in the spec itself: the exact
	// dollar figure lives in Stripe (app/config.py's stripe_price_id_pro),
	// not in this app's own code, so this page shows real feature gating
	// (checked against auth.py's require_pro_practitioner, which actually
	// enforces this) rather than a number pulled out of thin air.
	const basic = ['A public profile in the directory', 'Contact form submissions from prospective clients', 'Profile editing'];
	const pro = [
		'Everything in Basic',
		'Consult — grounded, cited AI assistance for real clients',
		'A full client roster with health records',
		'Custom questionnaires',
		'Library weighting — tune what the AI draws from most'
	];
</script>

<Seo title="Pricing — Functional Health Collab" description="Functional Health Collab plans for independent practitioners." path="/pricing" />

<div class="container page">
	<h1>Simple, two-tier pricing</h1>
	<p class="lede">Every practitioner starts on Basic. Upgrade to Pro once you're ready to bring on real clients.</p>
	<div class="plans">
		<div class="plan">
			<h2>Basic</h2>
			<p class="tag">Free to apply</p>
			<ul>{#each basic as f (f)}<li><Icon name="check" size={15} />{f}</li>{/each}</ul>
		</div>
		<div class="plan featured">
			<h2>Pro</h2>
			<p class="tag">See exact pricing at checkout, inside the practitioner portal's Upgrade page</p>
			<ul>{#each pro as f (f)}<li><Icon name="check" size={15} />{f}</li>{/each}</ul>
			<a class="btn filled" href="/join">Apply as a practitioner</a>
		</div>
	</div>
</div>

<style>
	.page { padding: var(--space-7) 0; }
	h1 { font-size: var(--text-2xl); text-align: center; }
	.lede { color: var(--ink-2); text-align: center; max-width: 30rem; margin: var(--space-3) auto var(--space-6); }
	.plans { display: grid; gap: var(--space-5); grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); max-width: 42rem; margin: 0 auto; }
	.plan { border: 1px solid var(--line); border-radius: var(--r-lg); padding: var(--space-5); background: var(--panel); }
	.plan.featured { border-color: var(--accent); box-shadow: var(--shadow); }
	.plan h2 { font-size: var(--text-xl); }
	.tag { color: var(--muted); font-size: var(--text-sm); margin: .3rem 0 var(--space-4); }
	.plan ul { list-style: none; margin: 0 0 var(--space-4); padding: 0; display: grid; gap: .6rem; }
	.plan li { display: flex; align-items: flex-start; gap: .5rem; font-size: var(--text-sm); color: var(--ink-2); }
	.plan li :global(svg) { color: var(--ok); flex: 0 0 auto; margin-top: .1rem; }
	.btn.filled { display: inline-block; background: var(--accent); color: #fff; padding: .6rem 1.2rem; border-radius: var(--r); text-decoration: none; font-size: var(--text-sm); font-weight: 700; }
</style>
