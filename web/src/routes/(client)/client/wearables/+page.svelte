<script lang="ts">
	import { post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Button from '$lib/components/Button.svelte';

	let { data } = $props();
	const providers = ['oura', 'whoop', 'garmin'];

	function connected(provider: string) {
		return data.connections.some((c: any) => c.provider === provider);
	}

	async function connect(provider: string) {
		try {
			const res = await post(fetch, `/me/wearables/${provider}/connect`);
			if (res?.url) location.href = res.url;
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}
</script>

<svelte:head><title>Wearables — Client portal</title></svelte:head>

<Spotlight title="Connect a wearable">
	<div class="providers">
		{#each providers as p (p)}
			<div class="row">
				<span class="pname">{p}</span>
				{#if connected(p)}
					<Chip tone="ok">Connected</Chip>
				{:else}
					<Button variant="outlined" onclick={() => connect(p)}>Connect</Button>
				{/if}
			</div>
		{/each}
	</div>
</Spotlight>

<style>
	.providers { display: grid; gap: var(--space-3); }
	.row { display: flex; align-items: center; justify-content: space-between; padding: var(--space-3); border: 1px solid var(--line); border-radius: var(--r); }
	.pname { text-transform: capitalize; font-weight: 650; }
</style>
