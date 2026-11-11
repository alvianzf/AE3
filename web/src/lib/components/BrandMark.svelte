<script lang="ts">
	// FHC brand mark: two overlapping rings, matches the navbar logo and
	// the site favicon. Fixed brand colors (not currentColor) since this
	// is a two-tone mark, not a tintable icon. `variant="light"` swaps the
	// navy ring for off-white — the dashboard rails are near-black, and
	// navy (#00004C) is otherwise almost invisible against them.
	let { size = 32, variant = 'default' }: { size?: number; variant?: 'default' | 'light' } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
	<circle cx="12" cy="16" r="9" fill="none" stroke={variant === 'light' ? '#F4F2ED' : '#00004C'} stroke-width="2.2" />
	<circle cx="20" cy="16" r="9" fill="none" stroke="#D79351" stroke-width="2.2" />
</svg>
