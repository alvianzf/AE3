<script lang="ts">
	import Seo from '$lib/components/Seo.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Sprig from '$lib/components/Sprig.svelte';

	// specs/v8 §8.2 — flagged explicitly in the spec itself: the exact
	// dollar figure lives in Stripe (app/config.py's stripe_price_id_pro),
	// not in this app's own code, so this page shows real feature gating
	// (checked against auth.py's require_pro_practitioner, which actually
	// enforces this) rather than a number pulled out of thin air.
	const basic = [
		'Public practitioner profile in the directory',
		'Direct consultation requests & contact inquiries',
		'Clinical specialties & bio customization',
		'Practice listing in client search'
	];
	const pro = [
		'Everything in Basic included',
		'Consult workspace — clinical synthesis with peer-reviewed citations',
		'Client-specific protocol staging — decide what to implement and when',
		'Interactive patient timeline & biomarker vault',
		'Custom functional health intake questionnaires',
		'Private clinical library — curate and weight your own reference sources'
	];
</script>

<Seo title="Pricing & Plans — Functional Health Collab" description="Transparent practitioner membership plans for independent functional medicine clinicians." path="/pricing" />

<div class="container pricing-page">
	<div class="pricing-header">
		<div class="badge-wrap">
			<span class="logo-mark"><Sprig size={18} /></span>
			<span>Practitioner Memberships</span>
		</div>
		<h1>Simple, transparent membership for your practice</h1>
		<p class="lede">Every verified practitioner starts on Basic. Upgrade to Pro when you're ready to activate full client management and augmented clinical intelligence.</p>
	</div>

	<div class="plans-grid">
		<!-- Basic Plan -->
		<div class="plan-card">
			<div class="plan-head">
				<h2>Basic Directory</h2>
				<p class="tag">Free for approved practitioners</p>
				<p class="desc">Establish your presence in our verified functional medicine directory and receive client inquiries.</p>
			</div>
			<ul class="feature-list">
				{#each basic as f (f)}
					<li>
						<span class="check-icon"><Icon name="check" size={15} /></span>
						<span>{f}</span>
					</li>
				{/each}
			</ul>
			<a class="btn-plan-outline" href="/join">Apply as a Practitioner</a>
		</div>

		<!-- Pro Plan -->
		<div class="plan-card featured">
			<div class="featured-banner">Recommended for Active Practice</div>
			<div class="plan-head">
				<h2>Pro Practice</h2>
				<p class="tag">See exact monthly pricing in your practitioner portal</p>
				<p class="desc">Full clinical augmentation, private evidence library, interactive biomarker timelines, and active client consults.</p>
			</div>
			<ul class="feature-list">
				{#each pro as f (f)}
					<li>
						<span class="check-icon featured-check"><Icon name="check" size={15} /></span>
						<span>{f}</span>
					</li>
				{/each}
			</ul>
			<a class="btn-plan-filled" href="/join">Apply & Get Started</a>
		</div>
	</div>

	<div class="pricing-footnote">
		<p>Clients are never charged platform fees. All consultation rates are set directly by practitioners.</p>
	</div>
</div>

<style>
	.pricing-page {
		padding: var(--space-7) var(--space-5);
		max-width: 58rem;
		margin: 0 auto;
	}
	.pricing-header {
		text-align: center;
		margin-bottom: var(--space-6);
		display: flex;
		flex-direction: column;
		align-items: center;
	}
	.badge-wrap {
		display: inline-flex;
		align-items: center;
		gap: .5rem;
		background: #e8f4ec;
		color: #1b4332;
		border: 1px solid rgba(45, 106, 79, 0.2);
		padding: .35rem .85rem;
		border-radius: 999px;
		font-size: var(--text-xs);
		font-weight: 750;
		margin-bottom: var(--space-4);
	}
	.logo-mark {
		display: inline-flex;
		color: #2d6a4f;
	}
	.pricing-header h1 {
		font-size: clamp(2rem, 3.2vw, 2.75rem);
		font-weight: 850;
		color: #1b4332;
		letter-spacing: -.025em;
		margin: 0;
	}
	.lede {
		color: #52796f;
		font-size: var(--text-base);
		max-width: 36rem;
		margin: var(--space-3) auto 0;
		line-height: 1.6;
	}
	.plans-grid {
		display: grid;
		gap: var(--space-5);
		grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
		margin: var(--space-5) 0;
	}
	.plan-card {
		background: #ffffff;
		border: 1px solid rgba(45, 106, 79, 0.16);
		border-radius: 18px;
		padding: var(--space-6);
		display: flex;
		flex-direction: column;
		box-shadow: 0 4px 20px rgba(27, 67, 50, 0.04);
		position: relative;
	}
	.plan-card.featured {
		border-color: #2d6a4f;
		border-width: 2px;
		box-shadow: 0 10px 32px rgba(45, 106, 79, 0.12);
	}
	.featured-banner {
		position: absolute;
		top: -12px;
		left: 50%;
		transform: translateX(-50%);
		background: #2d6a4f;
		color: #ffffff;
		font-size: .75rem;
		font-weight: 750;
		padding: .25rem .75rem;
		border-radius: 999px;
		letter-spacing: .02em;
		white-space: nowrap;
	}
	.plan-head h2 {
		font-size: var(--text-xl);
		font-weight: 800;
		color: #1b4332;
		margin: 0;
	}
	.tag {
		color: #2d6a4f;
		font-size: var(--text-sm);
		font-weight: 700;
		margin: .35rem 0 .6rem;
	}
	.desc {
		font-size: var(--text-xs);
		color: #52796f;
		line-height: 1.5;
		margin: 0 0 var(--space-5);
	}
	.feature-list {
		list-style: none;
		margin: 0 0 var(--space-6);
		padding: 0;
		display: grid;
		gap: .75rem;
		flex: 1 0 auto;
	}
	.feature-list li {
		display: flex;
		align-items: flex-start;
		gap: .65rem;
		font-size: var(--text-sm);
		color: #1b4332;
		line-height: 1.45;
	}
	.check-icon {
		color: #2d6a4f;
		flex: 0 0 auto;
		margin-top: .15rem;
	}
	.featured-check {
		color: #52b788;
	}
	.btn-plan-outline {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		background: #ffffff;
		color: #1b4332;
		border: 1.5px solid rgba(45, 106, 79, 0.3);
		padding: .7rem 1.25rem;
		border-radius: 10px;
		text-decoration: none;
		font-size: var(--text-sm);
		font-weight: 750;
		transition: all .15s ease;
		text-align: center;
	}
	.btn-plan-outline:hover {
		background: #f4f8f4;
		border-color: #2d6a4f;
	}
	.btn-plan-filled {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		background: #2d6a4f;
		color: #ffffff;
		border: none;
		padding: .75rem 1.25rem;
		border-radius: 10px;
		text-decoration: none;
		font-size: var(--text-sm);
		font-weight: 750;
		box-shadow: 0 4px 14px rgba(45, 106, 79, 0.25);
		transition: all .15s ease;
		text-align: center;
	}
	.btn-plan-filled:hover {
		background: #1b4332;
		transform: translateY(-1px);
	}
	.pricing-footnote {
		text-align: center;
		margin-top: var(--space-6);
		color: #52796f;
		font-size: var(--text-xs);
	}
</style>