<script lang="ts">
	// A practitioner (a simple head-and-shoulders silhouette) paired
	// with an AI-assistant chat bubble carrying a small spark/star —
	// "a professional, helped by an AI assistant" — for the
	// practitioner-facing section. Same stroke-and-soft-fill language
	// as GroundedArt/Icon/Sprig.
	let { size = 160 }: { size?: number } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 160 160" fill="none" aria-hidden="true">
	<circle cx="58" cy="46" r="22" fill="currentColor" fill-opacity=".14" stroke="currentColor" stroke-width="2.5" />
	<path d="M20 128c0-24 17-40 38-40s38 16 38 40" fill="currentColor" fill-opacity=".08" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
	<path d="M94 70c2-10 10-14 10-14" stroke="currentColor" stroke-opacity=".4" stroke-width="2" stroke-linecap="round" stroke-dasharray="2 5" />
	<path d="M98 36h38a8 8 0 0 1 8 8v22a8 8 0 0 1-8 8h-6l-6 12-6-12h-20a8 8 0 0 1-8-8V44a8 8 0 0 1 8-8z"
		fill="var(--panel)" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round" />
	<path d="M117 48l2.2 5 5 2.2-5 2.2-2.2 5-2.2-5-5-2.2 5-2.2z" fill="currentColor" />
	<path d="M133 48l1.3 3 3 1.3-3 1.3-1.3 3-1.3-3-3-1.3 3-1.3z" fill="currentColor" fill-opacity=".6" />
</svg>
