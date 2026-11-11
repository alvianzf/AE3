<script lang="ts">
	import { page } from '$app/state';
	import Seo from '$lib/components/Seo.svelte';
</script>

<Seo title="Page not found — Functional Health Collaborative" description="This page doesn't exist or has moved." path={page.url.pathname} noindex />

<section class="error-page">
	<div class="container error-inner">
		<p class="label">{page.status}</p>
		<h1>{page.status === 404 ? "This page doesn't exist" : 'Something went wrong'}</h1>
		<p class="sub">
			{page.status === 404
				? "The page you're looking for has moved or is no longer here."
				: (page.error?.message ?? 'Please try again, or head back to the homepage.')}
		</p>
		<a href="/" class="btn-primary">Back to homepage</a>
	</div>
</section>

<style>
	.error-page { padding: 6rem 0; background: var(--pub-bg); min-height: 60vh; }
	.error-inner { max-width: 32rem; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 1rem; }
	.label { margin: 0; font-size: .85rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; color: var(--pub-burgundy); }
	h1 { margin: 0; font-family: var(--pub-font-heading); font-weight: 600; font-size: clamp(1.8rem, 3.4vw, 2.4rem); color: var(--pub-navy); }
	.sub { margin: 0; font-size: 1.1rem; line-height: 1.6; color: var(--pub-text-muted); }
	.btn-primary {
		display: inline-flex; align-items: center; justify-content: center; min-height: 52px; padding: 0 1.75rem;
		border-radius: 999px; font-size: 1.0625rem; font-weight: 600; text-decoration: none;
		background: var(--pub-copper); color: var(--pub-navy); margin-top: .5rem;
		transition: background var(--duration-fast), transform var(--duration-fast);
	}
	.btn-primary:hover { background: #c98540; transform: translateY(-1px); }
</style>
