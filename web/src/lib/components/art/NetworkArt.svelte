<script lang="ts">
	// A small knowledge-graph motif — a central document node with
	// lines reaching out to smaller linked nodes — standing in for
	// "your own curated library, connected and cited," not a stock
	// chat-bubble/robot cliché. Same stroke-and-soft-fill language as
	// the other illustrations in this folder.
	let { size = 160 }: { size?: number } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 160 160" fill="none" aria-hidden="true">
	<path d="M48 42h40l20 20v56a6 6 0 0 1-6 6H48a6 6 0 0 1-6-6V48a6 6 0 0 1 6-6z"
		fill="currentColor" fill-opacity=".1" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round" />
	<path d="M88 42v20h20" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round" />
	<path d="M56 78h32M56 92h32M56 106h20" stroke="currentColor" stroke-opacity=".45" stroke-width="2" stroke-linecap="round" />
	<path d="M42 70L18 56M42 98L16 108M114 72l24-8M110 112l22 14" stroke="currentColor" stroke-opacity=".35" stroke-width="1.6" stroke-dasharray="1 5" stroke-linecap="round" />
	<circle cx="18" cy="56" r="7" fill="var(--panel)" stroke="currentColor" stroke-width="2" />
	<circle cx="16" cy="108" r="7" fill="var(--panel)" stroke="currentColor" stroke-width="2" />
	<circle cx="138" cy="64" r="7" fill="var(--panel)" stroke="currentColor" stroke-width="2" />
	<circle cx="132" cy="126" r="7" fill="var(--panel)" stroke="currentColor" stroke-width="2" />
</svg>
