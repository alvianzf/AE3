<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get, post } from '$lib/api';
	import TextField from '$lib/components/TextField.svelte';
	import Select from '$lib/components/Select.svelte';
	import Button from '$lib/components/Button.svelte';
	import Sprig from '$lib/components/Sprig.svelte';

	let name = $state('');
	let email = $state('');
	let password = $state('');
	let practitionerId = $state('');
	let practitioners = $state<any[]>([]);
	let loadingPractitioners = $state(true);
	let submitting = $state(false);
	let error = $state('');

	// The signup form has no way to complete without a practitioner_id
	// (POST /api/clients 400s without one, app/main.py) — fetched client-side
	// rather than at prerender time so the picker never offers a practitioner
	// who has since been suspended or downgraded off Pro.
	onMount(async () => {
		try {
			const all = await get(fetch, '/practitioners');
			practitioners = (all ?? []).filter((p: any) => p.plan === 'pro');
		} catch {
			practitioners = [];
		} finally {
			loadingPractitioners = false;
		}
	});

	async function submit(e: Event) {
		e.preventDefault();
		submitting = true;
		error = '';
		try {
			await post(fetch, '/clients', { name, email, password, practitioner_id: practitionerId });
			goto('/login');
		} catch (err: any) {
			error = err.message;
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head><title>Create your account — Clinic</title></svelte:head>

<div class="container wrap">
	<section class="card-panel">
		<div class="ph botanic"><h2><Sprig /> Create your account</h2></div>
		<form class="pb" onsubmit={submit}>
			{#if loadingPractitioners}
				<p class="hint">Loading practitioners…</p>
			{:else if practitioners.length === 0}
				<p class="hint">No practitioners are accepting new clients right now. Please check back later.</p>
			{:else}
				<Select
					label="Choose your practitioner"
					bind:value={practitionerId}
					required
					options={practitioners.map((p) => ({ value: p.id, label: p.name }))}
				/>
				<TextField label="Full name" bind:value={name} required />
				<TextField label="Email" type="email" bind:value={email} required />
				<TextField label="Password" type="password" bind:value={password} required hint="At least 8 characters" />
				{#if error}<p class="error">{error}</p>{/if}
				<Button type="submit" loading={submitting} disabled={!practitionerId}>Create account</Button>
			{/if}
			<p class="hint">Already have an account? <a href="/login">Log in</a></p>
		</form>
	</section>
</div>

<style>
	.wrap { padding: var(--space-6) var(--space-5); max-width: 26rem; }
	form { display: grid; gap: var(--space-3); }
	.error { color: var(--danger); font-size: var(--text-sm); }
</style>
