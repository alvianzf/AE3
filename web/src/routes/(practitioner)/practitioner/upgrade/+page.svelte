<script lang="ts">
	import { post, get } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Button from '$lib/components/Button.svelte';
	import Chip from '$lib/components/Chip.svelte';

	let { data } = $props();
	const isPro = $derived(data.profile?.plan === 'pro');
	let loading = $state(false);

	async function upgrade() {
		loading = true;
		try {
			const res = await post(fetch, '/me/upgrade');
			if (res?.url) location.href = res.url;
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			loading = false;
		}
	}

	async function manageBilling() {
		loading = true;
		try {
			const res = await get(fetch, '/me/billing-portal');
			if (res?.url) location.href = res.url;
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head><title>Upgrade — Practitioner portal</title></svelte:head>

<Spotlight title="Plan" leaf>
	<p><Chip tone={isPro ? 'ok' : 'neutral'}>{isPro ? 'Pro' : 'Basic'} plan</Chip></p>
	{#if isPro}
		<p class="hint">You have full access to Consult, the knowledge library, and client vaults.</p>
		<Button variant="outlined" onclick={manageBilling} loading={loading}>Manage billing</Button>
	{:else}
		<p class="hint">Upgrade to Pro to unlock AI-assisted consults, the client vault, and the shared knowledge library.</p>
		<Button onclick={upgrade} loading={loading}>Upgrade to Pro</Button>
	{/if}
</Spotlight>
