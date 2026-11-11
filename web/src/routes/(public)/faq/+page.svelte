<script lang="ts">
	import Seo from '$lib/components/Seo.svelte';
	import BrandMark from '$lib/components/BrandMark.svelte';
	import { jsonLdScript } from '$lib/seo';

	// Grounded entirely in the homepage's own verified content (approach,
	// programs/pricing, how-it-works steps, testing partners, footer
	// disclaimer) — not invented. Replaces the old copy, which described a
	// different, now-retired product (an AI clinical-intelligence platform
	// for a multi-practitioner marketplace).
	const faqs = [
		{
			q: 'What does Functional Health Collaborative do?',
			a: 'We are a 100% online telehealth practice specialising in personalised hormone, metabolic, gut and longevity care for women in perimenopause and menopause. Our protocols are rooted in science and functional medicine, covering every system in your body — not just symptom relief.'
		},
		{
			q: 'Is this a replacement for my doctor?',
			a: 'No. We work alongside — not in place of — your GP or medical specialist. We do not diagnose or treat medical conditions, and you should always consult your doctor before making changes to medication.'
		},
		{
			q: 'How does the process work?',
			a: "It starts with a free 15-minute intro call, followed by an in-depth intake covering your symptoms, goals, and history. From there you get hormone and metabolic health education, personalised insights from a continuous glucose monitor (CGM), your test results explained with a protocol, regular follow-up sessions, re-testing where needed, and a wrap-up session with recommendations for the road ahead."
		},
		{
			q: 'What programs do you offer, and what do they cost?',
			a: 'Three monthly programs, each with a one-time €295 intake fee: Foundational Health (€150/month) builds on your blood work and symptoms with no functional or DNA tests; Complete (€200/month) adds optional functional gut and hormone testing; Premium Longevity (€245/month) adds optional DNA testing on top of that. Add-on tests are paid separately — see the Programs section on the homepage for current pricing.'
		},
		{
			q: 'What testing do you use?',
			a: 'We partner with Nordic Laboratories (gut microbiome, DNA and functional panels), MIRA (home hormone testing), and Precision Analytical (DUTCH sex and adrenal hormone testing) to build truly personalised health plans based on the latest scientific research.'
		},
		{
			q: 'What do I need to provide myself?',
			a: "A continuous glucose monitor (CGM) and a comprehensive blood panel are required but not included in the program price, and supplements are not included either."
		},
		{
			q: 'Is this available where I live?',
			a: 'Yes — the practice is 100% online and available in English, Dutch, Slovak, French, German, Italian and Finnish.'
		},
		{
			q: 'How do I get started?',
			a: 'Book your free 15-minute intro call from the homepage. We’ll listen to your story and help you find the program that fits.'
		}
	];

	const faqJsonLd = {
		'@context': 'https://schema.org',
		'@type': 'FAQPage',
		mainEntity: faqs.map((f) => ({
			'@type': 'Question',
			name: f.q,
			acceptedAnswer: { '@type': 'Answer', text: f.a }
		}))
	};
</script>

<Seo
	title="Frequently Asked Questions — Functional Health Collaborative"
	description="Answers to common questions about our perimenopause and menopause care programs, pricing, testing partners, and how to get started."
	path="/faq"
/>
<svelte:head>{@html jsonLdScript(faqJsonLd)}</svelte:head>

<div class="container faq-page">
	<div class="faq-header">
		<div class="badge-wrap">
			<BrandMark size={18} />
			<span>FAQ</span>
		</div>
		<h1>Frequently Asked Questions</h1>
		<p class="lede">Everything you need to know about our programs, testing partners, and how to get started.</p>
	</div>

	<div class="faq-list">
		{#each faqs as f (f.q)}
			<div class="faq-card">
				<h3>{f.q}</h3>
				<p>{f.a}</p>
			</div>
		{/each}
	</div>
</div>

<style>
	.faq-page {
		padding: var(--space-7) var(--space-5);
		max-width: 48rem;
		margin: 0 auto;
	}
	.faq-header {
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
		background: var(--pub-warm-grey);
		color: var(--pub-navy);
		padding: .35rem .85rem;
		border-radius: 999px;
		font-size: .8rem;
		font-weight: 600;
		margin-bottom: var(--space-4);
	}
	.faq-header h1 {
		font-family: var(--pub-font-heading);
		font-size: clamp(2rem, 3.2vw, 2.75rem);
		font-weight: 600;
		color: var(--pub-navy);
		letter-spacing: -.02em;
		margin: 0;
	}
	.lede {
		color: var(--pub-text-muted);
		font-size: 1.05rem;
		max-width: 34rem;
		margin: var(--space-3) auto 0;
		line-height: 1.6;
	}
	.faq-list {
		display: grid;
		gap: var(--space-4);
	}
	.faq-card {
		background: var(--pub-card-bg);
		border: 1px solid var(--pub-warm-grey);
		border-radius: 16px;
		padding: var(--space-5);
	}
	.faq-card h3 {
		font-family: var(--pub-font-heading);
		font-size: 1.1rem;
		font-weight: 600;
		color: var(--pub-navy);
		margin: 0 0 .5rem;
		line-height: 1.4;
	}
	.faq-card p {
		margin: 0;
		color: var(--pub-text);
		font-size: .95rem;
		line-height: 1.6;
	}
</style>
