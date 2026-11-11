<script lang="ts">
	// FHC brand mark: two overlapping rings, navy + copper — matches the
	// navbar logo and the site favicon. Fixed brand colors (not
	// currentColor) since this is a two-tone mark, not a tintable icon.
	let { size = 32 }: { size?: number } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
	<circle cx="12" cy="16" r="9" fill="none" stroke="#00004C" stroke-width="2.2" />
	<circle cx="20" cy="16" r="9" fill="none" stroke="#D79351" stroke-width="2.2" />
</svg>
