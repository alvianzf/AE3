<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { post, del } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Button from '$lib/components/Button.svelte';

	let { data } = $props();
	const providers = ['oura', 'whoop', 'garmin'];
	let disconnecting = $state<string | null>(null);

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

	// Connect-only, no way to undo the wrong provider account, previously
	// (specs/v4/04-known-issues.md#m6).
	async function disconnect(provider: string) {
		disconnecting = provider;
		try {
			await del(fetch, `/me/wearables/${provider}`);
			toast(`${provider} disconnected.`);
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			disconnecting = null;
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
					<div class="connected">
						<Chip tone="ok">Connected</Chip>
						<Button variant="text" onclick={() => disconnect(p)} loading={disconnecting === p}>Disconnect</Button>
					</div>
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
	.connected { display: flex; align-items: center; gap: .5rem; }
</style>
