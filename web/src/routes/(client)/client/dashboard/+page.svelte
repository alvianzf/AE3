<script lang="ts">
	import StatTile from '$lib/components/StatTile.svelte';

	let { data } = $props();
</script>

<svelte:head><title>Dashboard — Client portal</title></svelte:head>

<h1>Welcome back</h1>
<p class="hint">Everything you need is one tap away.</p>

<div class="grid-auto tiles">
	<StatTile
		label="Questionnaire"
		value={data.response ? 'Submitted' : 'Fill in'}
		icon="clipboard"
		href="/client/questionnaire"
	/>
	<StatTile
		label="Files"
		value={data.files?.length ? `${data.files.length} uploaded` : 'Upload'}
		icon="folder"
		href="/client/files"
	/>
	<StatTile
		label="Wearables"
		value={data.connections?.length ? `${data.connections.length} connected` : 'Connect'}
		icon="watch"
		href="/client/wearables"
	/>
</div>

<style>
	.tiles { margin-top: var(--space-5); }
</style>
