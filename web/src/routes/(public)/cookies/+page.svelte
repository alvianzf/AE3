<script lang="ts">
	import Seo from '$lib/components/Seo.svelte';
</script>

<Seo title="Cookie Policy — Functional Health Collab" description="What Functional Health Collab stores in your browser, and why." path="/cookies" />

<div class="container page">
	<h1>Cookies</h1>
	<p class="notice">
		Checked against this product's own code (this session) rather than
		boilerplate — but whether this one cookie legally needs a consent
		banner under the ePrivacy directive is a real determination a lawyer
		should make, not assumed here either way.
	</p>
	<p>
		Functional Health Collab sets exactly one cookie: <code>fhc_session</code>, a signed,
		<code>httponly</code> session token that keeps you logged in. It
		carries no advertising or analytics payload, is never read by any
		third party, and is strictly necessary for the site to function — you
		can't be logged in without it. We don't use any other cookie, and we
		don't use any third-party tracking cookie, pixel, or fingerprinting
		script anywhere on this site.
	</p>
</div>

<style>
	.page { max-width: 34rem; padding: var(--space-7) 0; }
	h1 { font-size: var(--text-2xl); margin-bottom: var(--space-4); }
	p { color: var(--ink-2); line-height: 1.6; }
	code { background: var(--panel-2); border: 1px solid var(--line); border-radius: 4px; padding: .1rem .4rem; font-size: .9em; }
	.notice { background: var(--accent-soft); border: 1px solid var(--line); border-radius: var(--r); padding: var(--space-3); font-size: var(--text-sm); color: var(--ink); margin-bottom: var(--space-5); }
</style>
