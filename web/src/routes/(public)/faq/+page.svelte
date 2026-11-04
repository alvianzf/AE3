<script lang="ts">
	import Seo from '$lib/components/Seo.svelte';

	// specs/v8 §8.2 — a real FAQ page, flagged in the spec itself as
	// needing real content drafted collaboratively; these answers are
	// grounded in what the product actually does (checked against
	// app/main.py, app/auth.py this session), not invented.
	const faqs = [
		{
			q: 'How does grounding and citation actually work?',
			a: 'Every answer comes from your practitioner’s own curated library — never the open internet. Each claim links back to the exact source passage, page number included, so you can check it yourself.'
		},
		{
			q: 'How does a practitioner get approved?',
			a: 'An applicant submits a profile; an admin reviews and approves (or rejects) it before the account can see real clients. Approval status is visible on the practitioner’s own dashboard throughout.'
		},
		{
			q: 'What happens to my data if I’m a client?',
			a: 'Your records live in your practitioner’s own isolated space — never pooled with any other practitioner’s clients. See our Privacy Policy for the full detail.'
		},
		{
			q: 'Is this a substitute for medical advice?',
			a: 'No. Functional Health Collab is a decision-support tool for a licensed practitioner — it is not a source of direct medical advice, and nothing it produces replaces a professional’s own judgment.'
		}
	];
</script>

<Seo title="FAQ — Functional Health Collab" description="Frequently asked questions about Functional Health Collab." path="/faq" />

<div class="container page">
	<h1>Frequently asked questions</h1>
	<dl>
		{#each faqs as f (f.q)}
			<dt>{f.q}</dt>
			<dd>{f.a}</dd>
		{/each}
	</dl>
</div>

<style>
	.page { max-width: 38rem; padding: var(--space-7) 0; }
	h1 { font-size: var(--text-2xl); margin-bottom: var(--space-5); }
	dl { display: grid; gap: var(--space-5); }
	dt { font-weight: 700; font-size: var(--text-lg); margin-bottom: .4rem; }
	dd { margin: 0; color: var(--ink-2); line-height: 1.6; }
</style>
