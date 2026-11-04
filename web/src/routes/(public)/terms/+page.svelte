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
		Functional Health Collab is a decision-support tool for licensed practitioners. It is not
		a medical device, and nothing it produces is medical advice to a
		client. Every answer is grounded in a practitioner's own curated
		library and independently checked, but the practitioner — not Functional Health Collab —
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
		A client account is created and managed by your practitioner. Your
		data is visible only to that practitioner, never to any other
		practitioner on the platform.
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
	.page { max-width: 38rem; padding: var(--space-7) 0; }
	h1 { font-size: var(--text-2xl); margin-bottom: var(--space-4); }
	h2 { font-size: var(--text-lg); margin: var(--space-5) 0 var(--space-2); }
	p { color: var(--ink-2); line-height: 1.6; }
	.notice { background: var(--accent-soft); border: 1px solid var(--line); border-radius: var(--r); padding: var(--space-3); font-size: var(--text-sm); color: var(--ink); }
</style>
