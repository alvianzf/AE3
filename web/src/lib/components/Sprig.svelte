<script lang="ts">
	let { size = 20 }: { size?: number } = $props();
</script>

<span class="sprig" aria-hidden="true" style="--s:{size}px">
	<svg viewBox="0 0 20 24" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round">
		<path d="M10 23V7" />
		<path d="M10 13c0-3.6 2.4-6.4 6-7-.3 3.8-2.6 6.4-6 7z" fill="currentColor" fill-opacity=".16" />
		<path d="M10 9.5C10 6 7.8 3.3 4.3 2.5 4.6 6.2 6.7 8.8 10 9.5z" fill="currentColor" fill-opacity=".22" />
	</svg>
</span>

<style>
	.sprig svg { width: var(--s, 20px); height: calc(var(--s, 20px) * 1.2); }
</style>
