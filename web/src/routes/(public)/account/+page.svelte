<script lang="ts">
	import { post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Sprig from '$lib/components/Sprig.svelte';

	let { data } = $props();
	let current_password = $state('');
	let new_password = $state('');
	let submitting = $state(false);

	async function submit(e: Event) {
		e.preventDefault();
		submitting = true;
		try {
			await post(fetch, '/auth/change-password', { current_password, new_password });
			toast('Password updated.');
			current_password = '';
			new_password = '';
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head><title>Your account — Clinic</title></svelte:head>

<div class="container wrap">
	<section class="card-panel">
		<div class="ph botanic"><h2><Sprig /> Your account</h2></div>
		<div class="pb">
			{#if !data.session}
				<p class="hint">You need to <a href="/login">log in</a> to manage your account.</p>
			{:else}
				<p class="hint">Signed in as <strong>{data.session.role}</strong>.</p>
				<form onsubmit={submit}>
					<TextField label="Current password" type="password" bind:value={current_password} required />
					<TextField label="New password" type="password" bind:value={new_password} required hint="At least 8 characters" />
					<Button type="submit" loading={submitting}>Change password</Button>
				</form>
			{/if}
		</div>
	</section>
</div>

<style>
	.wrap { padding: var(--space-6) var(--space-5); max-width: 26rem; }
	form { display: grid; gap: var(--space-3); margin-top: var(--space-3); }
</style>
