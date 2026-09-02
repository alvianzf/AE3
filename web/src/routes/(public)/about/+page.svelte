<script lang="ts">
	import Sprig from '$lib/components/Sprig.svelte';
</script>

<svelte:head><title>About — Clinic</title></svelte:head>

<div class="container about">
	<section class="card-panel leafmark">
		<div class="ph botanic"><h2><Sprig /> About Clinic</h2></div>
		<div class="pb">
			<p>
				Clinic connects clients with independent practitioners and gives those
				practitioners an AI-assisted knowledge base — built on a library of
				sources they curate, consulted through a librarian → specialist →
				checker review chain before anything reaches a client record.
			</p>
			<p class="hint">
				Every answer a practitioner gives is checked against that library
				before it reaches your record — nothing is improvised.
			</p>
		</div>
	</section>
</div>

<style>
	.about { padding: var(--space-6) var(--space-5); max-width: 46rem; }
	.pb p + p { margin-top: var(--space-3); }
</style>
