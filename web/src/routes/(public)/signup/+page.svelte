<script lang="ts">
	import { goto } from '$app/navigation';
	import { post } from '$lib/api';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Sprig from '$lib/components/Sprig.svelte';

	let name = $state('');
	let email = $state('');
	let password = $state('');
	let submitting = $state(false);
	let error = $state('');

	async function submit(e: Event) {
		e.preventDefault();
		submitting = true;
		error = '';
		try {
			await post(fetch, '/clients', { name, email, password });
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
			<TextField label="Full name" bind:value={name} required />
			<TextField label="Email" type="email" bind:value={email} required />
			<TextField label="Password" type="password" bind:value={password} required hint="At least 8 characters" />
			{#if error}<p class="error">{error}</p>{/if}
			<Button type="submit" loading={submitting}>Create account</Button>
			<p class="hint">Already have an account? <a href="/login">Log in</a></p>
		</form>
	</section>
</div>

<style>
	.wrap { padding: var(--space-6) var(--space-5); max-width: 26rem; }
	form { display: grid; gap: var(--space-3); }
	.error { color: var(--danger); font-size: var(--text-sm); }
</style>
