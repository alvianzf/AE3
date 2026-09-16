<script lang="ts">
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Sprig from '$lib/components/Sprig.svelte';
</script>

<svelte:head><title>Wearables — Client portal</title></svelte:head>

<Spotlight title="Connect a wearable">
	<!-- Wearable OAuth connect is real (app/wearables.py) but what happens after
	     is fixture data, not a live vendor pull (see that module's docstring).
	     Showing a working "Connect" button here would let a client believe
	     their real Oura/Whoop/Garmin data reaches their practitioner when it
	     doesn't — so until the real data pull ships, this page says so plainly
	     instead of offering the flow. -->
	<div class="soon">
		<Sprig size={24} />
		<h3>Coming soon</h3>
		<p class="hint">
			Wearable syncing isn't available yet. When it launches, you'll be able to
			connect Oura, Whoop, or Garmin here and share your data with your practitioner.
		</p>
	</div>
</Spotlight>

<style>
	.soon {
		display: flex; flex-direction: column; align-items: center; text-align: center;
		gap: var(--space-2); padding: var(--space-6) var(--space-4); color: var(--muted);
	}
	.soon h3 { color: var(--ink); font-size: var(--text-base); }
</style>
