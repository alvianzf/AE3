<script lang="ts">
	import Sprig from '$lib/components/Sprig.svelte';
</script>

<svelte:head><title>Application received — Clinic</title></svelte:head>

<div class="container wrap">
	<section class="card-panel leafmark">
		<div class="pb center">
			<Sprig size={30} />
			<h1>Application received</h1>
			<p class="hint">An admin will review your application. You'll get access once approved — check back at <a href="/login">login</a>.</p>
			<a class="btn filled" href="/">Back to the directory</a>
		</div>
	</section>
</div>

<style>
	.wrap { padding: var(--space-7) var(--space-5); max-width: 30rem; }
	.center { display: flex; flex-direction: column; align-items: center; gap: var(--space-3); text-align: center; }
	.btn.filled { background: var(--accent); color: #fff; padding: .6rem 1.2rem; border-radius: 99px; text-decoration: none; font-weight: 700; margin-top: var(--space-2); }
</style>
