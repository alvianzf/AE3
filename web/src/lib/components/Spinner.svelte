<script lang="ts">
	// A small reusable spinner for inline loading text ("Loading the
	// concept graph…", "Fetching and extracting…") that previously had
	// no visual indicator at all — Button's own loading state and
	// Skeleton already cover the other two loading patterns in the app.
	let { size = 14 }: { size?: number } = $props();
</script>

<span class="spinner" style:width="{size}px" style:height="{size}px" aria-hidden="true"></span>

<style>
	.spinner {
		display: inline-block; vertical-align: middle; border-radius: 50%;
		border: 2px solid currentColor; border-top-color: transparent; opacity: .6;
		animation: spin .7s linear infinite;
	}
	@keyframes spin { to { transform: rotate(360deg); } }
</style>
