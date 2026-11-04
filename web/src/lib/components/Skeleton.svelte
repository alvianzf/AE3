<script lang="ts">
	// specs/v7/01 — a loading placeholder, replacing "shows nothing (or a
	// bare 'Loading…' string) until data arrives" with a shimmering
	// placeholder shaped like the content that's about to appear. The
	// single cheapest "feels responsive" win available — no new
	// dependency, respects the existing global prefers-reduced-motion
	// override in app.css (the shimmer animation is caught by that same
	// blanket rule, same as every other animation in this app).
	let {
		variant = 'line',
		width,
		height,
		count = 1
	}: {
		variant?: 'line' | 'circle' | 'block';
		width?: string;
		height?: string;
		count?: number;
	} = $props();
</script>

{#each { length: count } as _, i (i)}
	<span
		class="skeleton {variant}"
		style:width={width}
		style:height={height}
		aria-hidden="true"
	></span>
{/each}

<style>
	.skeleton {
		display: block; background: linear-gradient(90deg, var(--panel-2) 25%, var(--line) 50%, var(--panel-2) 75%);
		background-size: 200% 100%; animation: shimmer 1.4s ease-in-out infinite;
	}
	.line { width: 100%; height: 1em; border-radius: var(--r); margin-bottom: .4em; }
	.line:last-child { margin-bottom: 0; }
	.circle { width: 2.5rem; height: 2.5rem; border-radius: 50%; }
	.block { width: 100%; height: 8rem; border-radius: var(--r-lg); }
	@keyframes shimmer {
		0% { background-position: 200% 0; }
		100% { background-position: -200% 0; }
	}
</style>
