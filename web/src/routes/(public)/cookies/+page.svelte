<script lang="ts">
	import Seo from '$lib/components/Seo.svelte';
</script>

<Seo title="Cookie Policy — Functional Health Collaborative" description="What Functional Health Collaborative stores in your browser, and why." path="/cookies" />

<div class="container page">
	<h1>Cookie Policy</h1>
	<p class="notice">
		Checked against this product's own code rather than boilerplate — but whether this one cookie legally needs a consent
		banner under the ePrivacy directive is a real determination a lawyer should make, not assumed here either way.
	</p>
	<p>
		Functional Health Collaborative sets exactly one cookie: <code>fhc_session</code>, a signed,
		<code>httponly</code> session token that keeps you logged in. It
		carries no advertising or analytics payload, is never read by any
		third party, and is strictly necessary for the site to function — you
		can't be logged in without it. We don't use any other cookie, and we
		don't use any third-party tracking cookie, pixel, or fingerprinting
		script anywhere on this site.
	</p>
</div>

<style>
	.page { max-width: 42rem; padding: var(--space-7) var(--space-5); margin: 0 auto; }
	h1 { font-size: clamp(2rem, 3.2vw, 2.6rem); font-weight: 850; color: #1b4332; margin-bottom: var(--space-4); }
	p { color: #3e5a4d; line-height: 1.65; }
	code { background: #e8f4ec; border: 1px solid rgba(45, 106, 79, 0.2); border-radius: 4px; padding: .1rem .4rem; font-size: .9em; color: #1b4332; }
	.notice { background: #e8f4ec; border: 1px solid rgba(45, 106, 79, 0.2); border-radius: 10px; padding: var(--space-3) var(--space-4); font-size: var(--text-sm); color: #1b4332; margin-bottom: var(--space-5); }
</style>