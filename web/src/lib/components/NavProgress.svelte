<script lang="ts">
	// A click-to-navigation round trip to this app's origin is real network
	// latency (server is in Germany; a meaningful share of usage is from
	// much farther away) — no frontend framework changes that. What we can
	// change is how it *feels*: without this, a navigation shows nothing at
	// all until the new page's load() resolves, which reads as "did that
	// even register." This bar paints on the very next frame after a click,
	// before any network response arrives.
	import { navigating } from '$app/state';
</script>

{#if navigating.to}
	<div class="nav-progress" aria-hidden="true"></div>
{/if}

<style>
	.nav-progress {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		height: 3px;
		z-index: 999;
		background: var(--accent);
		transform-origin: left;
		transform: scaleX(0);
		animation: nav-progress-grow 6s cubic-bezier(0.1, 0.6, 0.2, 1) forwards;
	}
	@keyframes nav-progress-grow {
		0% { transform: scaleX(0); }
		100% { transform: scaleX(0.92); }
	}
	@media (prefers-reduced-motion: reduce) {
		.nav-progress { animation: none; transform: scaleX(0.92); }
	}
</style>
