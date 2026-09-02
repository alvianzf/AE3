<script lang="ts">
	import StatTile from '$lib/components/StatTile.svelte';
</script>

<svelte:head><title>Dashboard — Client portal</title></svelte:head>

<h1>Welcome back</h1>
<p class="hint">Everything you need is one tap away.</p>

<div class="grid-auto tiles">
	<StatTile label="Questionnaire" value="Fill in" icon="📋" href="/client/questionnaire" />
	<StatTile label="Files" value="Upload" icon="📁" href="/client/files" />
	<StatTile label="Wearables" value="Connect" icon="⌚" href="/client/wearables" />
</div>

<style>
	.tiles { margin-top: var(--space-5); }
</style>
