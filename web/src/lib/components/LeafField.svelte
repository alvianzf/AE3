<script lang="ts">
	// Direct feedback: not canvas, not a traced glyph — plain random SVG
	// leaves floating around the hero, matching the Sprig mark's botanical
	// motif loosely rather than literally. A handful of real DOM/SVG
	// elements is fine at this count (this isn't GraphView's hundreds-of-
	// nodes problem) — CSS keyframe animation per leaf, each randomized so
	// they don't move in lockstep.
	let { count = 16 }: { count?: number } = $props();

	const leaves = Array.from({ length: count }, (_, i) => ({
		id: i,
		left: Math.random() * 100,
		top: Math.random() * 100,
		size: 14 + Math.random() * 20,
		rotate: Math.random() * 360,
		duration: 10 + Math.random() * 10,
		delay: -(Math.random() * 14),
		drift: (Math.random() - 0.5) * 40,
		opacity: 0.12 + Math.random() * 0.2
	}));
</script>

<div class="field" aria-hidden="true">
	{#each leaves as leaf (leaf.id)}
		<svg
			class="leaf"
			style="
				left: {leaf.left}%; top: {leaf.top}%; width: {leaf.size}px; height: {leaf.size}px;
				opacity: {leaf.opacity};
				--rotate: {leaf.rotate}deg; --duration: {leaf.duration}s; --delay: {leaf.delay}s; --drift: {leaf.drift}px;
			"
			viewBox="0 0 24 24" fill="none"
		>
			<path
				d="M12 3c4 2 7 5.5 7 10a7 7 0 0 1-14 0c0-4.5 3-8 7-10z"
				fill="#ffb9c4" fill-opacity=".55" stroke="#ffb9c4" stroke-opacity=".7" stroke-width="1"
			/>
			<path d="M12 5v14" stroke="#ffb9c4" stroke-opacity=".7" stroke-width="1" stroke-linecap="round" />
		</svg>
	{/each}
</div>

<style>
	.field { position: absolute; inset: 0; overflow: hidden; pointer-events: none; }
	.leaf {
		position: absolute; transform: rotate(var(--rotate));
		animation: float var(--duration) ease-in-out var(--delay) infinite;
	}
	@keyframes float {
		0%, 100% { transform: translate(0, 0) rotate(var(--rotate)); }
		50% { transform: translate(var(--drift), -1.2rem) rotate(calc(var(--rotate) + 12deg)); }
	}
	@media (prefers-reduced-motion: reduce) {
		.leaf { animation: none; }
	}
</style>
