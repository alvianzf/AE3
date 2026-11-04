<script lang="ts">
	// Falling leaves, not floating-in-place — each one starts above the
	// container and drifts straight down with a side-to-side sway and a
	// slow rotation, looping back to the top once it's past the bottom.
	// Plain CSS keyframes per leaf (randomized duration/delay/sway so
	// none of them move in lockstep), same handful-of-DOM-nodes budget
	// as before.
	let { count = 18 }: { count?: number } = $props();

	const leaves = Array.from({ length: count }, (_, i) => ({
		id: i,
		left: Math.random() * 100,
		size: 14 + Math.random() * 20,
		rotate: Math.random() * 360,
		spin: (Math.random() < 0.5 ? -1 : 1) * (180 + Math.random() * 360),
		duration: 7 + Math.random() * 8,
		delay: -(Math.random() * 15),
		sway: 20 + Math.random() * 40,
		opacity: 0.18 + Math.random() * 0.22
	}));
</script>

<div class="field" aria-hidden="true">
	{#each leaves as leaf (leaf.id)}
		<svg
			class="leaf"
			style="
				left: {leaf.left}%; width: {leaf.size}px; height: {leaf.size}px; opacity: {leaf.opacity};
				--rotate: {leaf.rotate}deg; --spin: {leaf.spin}deg; --duration: {leaf.duration}s;
				--delay: {leaf.delay}s; --sway: {leaf.sway}px;
			"
			viewBox="0 0 24 24" fill="none"
		>
			<path
				d="M12 3c4 2 7 5.5 7 10a7 7 0 0 1-14 0c0-4.5 3-8 7-10z"
				fill="currentColor" fill-opacity=".6" stroke="currentColor" stroke-opacity=".75" stroke-width="1"
			/>
			<path d="M12 5v14" stroke="currentColor" stroke-opacity=".75" stroke-width="1" stroke-linecap="round" />
		</svg>
	{/each}
</div>

<style>
	.field { position: absolute; inset: 0; overflow: hidden; pointer-events: none; color: var(--leaf-color, #ffb9c4); }
	/* top/left as percentages, animated — on an absolutely positioned
	   element these resolve against .field's own box (inset:0, so
	   exactly the hero/section it's placed in), not the viewport. Works
	   the same whether this sits in a small side panel or a full-bleed
	   section, unlike a vh-based transform would. Sway/rotation layer
	   on top via transform, which doesn't fight the top/left fall. */
	.leaf {
		position: absolute; top: -12%;
		animation: fall var(--duration) linear var(--delay) infinite;
	}
	@keyframes fall {
		0% { top: -12%; transform: translateX(0) rotate(var(--rotate)); }
		25% { transform: translateX(var(--sway)) rotate(calc(var(--rotate) + var(--spin) * .25)); }
		50% { transform: translateX(0) rotate(calc(var(--rotate) + var(--spin) * .5)); }
		75% { transform: translateX(calc(var(--sway) * -1)) rotate(calc(var(--rotate) + var(--spin) * .75)); }
		100% { top: 112%; transform: translateX(0) rotate(calc(var(--rotate) + var(--spin))); }
	}
	@media (prefers-reduced-motion: reduce) {
		.leaf { animation: none; top: 40%; }
	}
</style>
