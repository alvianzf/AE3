<script lang="ts">
	import Seo from '$lib/components/Seo.svelte';
</script>

<Seo title="Privacy Policy — Functional Health Collaborative" description="How Functional Health Collaborative collects, uses, and protects your data." path="/privacy" />

<div class="container page">
	<h1>Privacy Policy</h1>
	<p class="notice">
		This page describes, structurally, what this product actually collects and
		who it shares it with — grounded in its real code, not boilerplate. It is
		not yet reviewed by counsel; treat it as a drafting starting point, not a
		binding legal document, until it has been.
	</p>

	<h2>What we collect</h2>
	<p>Depending on your account type:</p>
	<ul>
		<li><strong>Practitioners</strong>: name, email, a public profile (bio, specialties, languages, photo), and billing information handled by Stripe (we never see your card number).</li>
		<li><strong>Clients</strong>: name, email, and whatever health information your own practitioner records on your behalf — questionnaire answers, health-record entries, and files they share with you. Clients do not interface with open AI chat.</li>
		<li><strong>Everyone</strong>: basic access logs (IP address, browser user agent) kept for security and abuse prevention.</li>
	</ul>

	<h2>Who we share it with</h2>
	<p>We use the following processors, and only for the purpose named:</p>
	<ul>
		<li><strong>Nebius</strong> — hosts the clinical language models that read, index, and answer from your practitioner's library.</li>
		<li><strong>Anthropic</strong> — an optional, practitioner-opted-in alternate provider for the same purpose.</li>
		<li><strong>Stripe</strong> — processes practitioner subscription billing. We never store your payment details ourselves.</li>
	</ul>
	<p>We do not sell personal data, and a client's records are never shared with any practitioner other than their own.</p>

	<h2>How long we keep it</h2>
	<p>For as long as your account is active, plus a reasonable period after closure for legal and security recordkeeping. You can ask us to delete your account's data at any time via your practitioner (for clients) or by contacting us directly.</p>

	<h2>Your rights</h2>
	<p>If you're in the EU/EEA, you have the right to access, correct, export, or delete your personal data under the GDPR. Contact us at the address on our <a href="/contact">Contact</a> page to exercise any of these.</p>
</div>

<style>
	.page { max-width: 42rem; padding: var(--space-7) var(--space-5); margin: 0 auto; }
	h1 { font-size: clamp(2rem, 3.2vw, 2.6rem); font-weight: 850; color: #1b4332; margin-bottom: var(--space-4); }
	h2 { font-size: var(--text-lg); font-weight: 800; color: #1b4332; margin: var(--space-5) 0 var(--space-2); }
	p, li { color: #3e5a4d; line-height: 1.65; }
	ul { padding-left: 1.2rem; display: grid; gap: .4rem; }
	.notice { background: #e8f4ec; border: 1px solid rgba(45, 106, 79, 0.2); border-radius: 10px; padding: var(--space-3) var(--space-4); font-size: var(--text-sm); color: #1b4332; }
	a { color: #2d6a4f; font-weight: 700; }
</style>