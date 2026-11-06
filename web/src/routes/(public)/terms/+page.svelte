<script lang="ts">
	import Seo from '$lib/components/Seo.svelte';
</script>

<Seo title="Terms of Service — Functional Health Collab" description="The terms governing use of Functional Health Collab." path="/terms" />

<div class="container page">
	<h1>Terms of Service</h1>
	<p class="notice">
		Drafting starting point, not yet reviewed by counsel — grounded in what
		the product actually does, not generic boilerplate.
	</p>

	<h2>Medical disclaimer</h2>
	<p>
		Functional Health Collab is a clinical intelligence and decision-support tool for licensed practitioners. It is not
		a medical device, and nothing it produces is direct medical advice to a
		client. Every synthesized insight is grounded in a practitioner's own curated
		library and independently verified, but the practitioner — not Functional Health Collab —
		remains responsible for the care they provide.
	</p>

	<h2>Practitioner accounts</h2>
	<p>
		Applying does not guarantee approval. An approved account is a data
		controller for its own clients' records, and is responsible for
		obtaining whatever consent or authorization it needs from them under
		applicable law. A Basic plan has limited features; a Pro plan requires
		an active subscription and can be downgraded if billing lapses.
	</p>

	<h2>Client accounts</h2>
	<p>
		A client account is created and managed in coordination with your practitioner. Your
		data is visible only to that practitioner, never to any other
		practitioner on the platform. Clients never interact with an autonomous AI.
	</p>

	<h2>Acceptable use</h2>
	<p>
		Don't use Functional Health Collab to store or process data you don't have the right to
		process, attempt to access another practitioner's clients, or
		interfere with the platform's normal operation.
	</p>

	<h2>Changes</h2>
	<p>We may update these terms; continued use after a change means you accept the update.</p>
</div>

<style>
	.page { max-width: 42rem; padding: var(--space-7) var(--space-5); margin: 0 auto; }
	h1 { font-size: clamp(2rem, 3.2vw, 2.6rem); font-weight: 850; color: #1b4332; margin-bottom: var(--space-4); }
	h2 { font-size: var(--text-lg); font-weight: 800; color: #1b4332; margin: var(--space-5) 0 var(--space-2); }
	p { color: #3e5a4d; line-height: 1.65; }
	.notice { background: #e8f4ec; border: 1px solid rgba(45, 106, 79, 0.2); border-radius: 10px; padding: var(--space-3) var(--space-4); font-size: var(--text-sm); color: #1b4332; }
</style>