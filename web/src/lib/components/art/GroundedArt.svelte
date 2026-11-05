<script lang="ts">
	// A small library-themed illustration — an open book with a
	// verification badge overlapping its spine — for the "every claim
	// is grounded and checked" section. Same stroke-and-soft-fill
	// language as Icon.svelte/Sprig.svelte, just drawn at a larger,
	// genuinely illustrative scale instead of a 24x24 glyph.
	let { size = 160 }: { size?: number } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 160 160" fill="none" aria-hidden="true">
	<path d="M20 40c16-8 32-8 48 0v76c-16-8-32-8-48 0V40z"
		fill="currentColor" fill-opacity=".08" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round" />
	<path d="M140 40c-16-8-32-8-48 0v76c16-8 32-8 48 0V40z"
		fill="currentColor" fill-opacity=".14" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round" />
	<path d="M68 48v68M30 56h20M30 68h20M30 80h20M30 92h20M92 56h20M92 68h20M92 80h20M92 92h20"
		stroke="currentColor" stroke-opacity=".45" stroke-width="2" stroke-linecap="round" />
	<circle cx="122" cy="104" r="22" fill="var(--panel)" stroke="currentColor" stroke-width="2.5" />
	<path d="M112 104l7 7 13-15" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
</svg>
