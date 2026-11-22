<script lang="ts">
	import { post, get } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Button from '$lib/components/Button.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { PRO_FEATURES } from '$lib/proFeatures';

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

<div class="pane-row"><div class="detail-pane"><div class="detail-head"><div class="head-title"><span class="head-ico"><Icon name="star" size={16} /></span><h1>Plan</h1></div></div>
	<p><Chip tone={isPro ? 'ok' : 'neutral'}>{isPro ? 'Pro' : 'Basic'} plan</Chip></p>
	{#if isPro}
		<p class="hint">You have full access to Consult, the knowledge library, and client vaults.</p>
		<Button variant="outlined" onclick={manageBilling} loading={loading}>Manage billing</Button>
	{:else}
		<p class="hint">Upgrade to Pro to unlock AI-assisted consults, the client vault, and the shared knowledge library.</p>

		<table class="compare">
			<thead>
				<tr><th>Feature</th><th>Basic</th><th>Pro</th></tr>
			</thead>
			<tbody>
				{#each PRO_FEATURES as f (f.href)}
					<tr>
						<td>{f.label}</td>
						<td><Icon name="x" size={14} /></td>
						<td><Icon name="check" size={14} /></td>
					</tr>
				{/each}
			</tbody>
		</table>

		<!-- TODO: replace with a real price once one is provided — see ux-implementation-spec.md#9 -->
		<p class="price-placeholder">Pricing shown at checkout</p>
		<Button onclick={upgrade} loading={loading}>Upgrade to Pro</Button>
	{/if}
</div></div>

<style>
	.compare { width: 100%; max-width: 28rem; border-collapse: collapse; margin: var(--space-4) 0; font-size: var(--text-sm); }
	.compare th, .compare td { text-align: left; padding: .5rem .6rem; border-bottom: 1px solid var(--line); }
	.compare th:not(:first-child), .compare td:not(:first-child) { text-align: center; }
	.compare td:nth-child(2) { color: var(--muted); }
	.compare td:nth-child(3) { color: var(--accent, var(--ink)); }
	.price-placeholder { font-size: var(--text-sm); color: var(--muted); font-style: italic; }
</style>
