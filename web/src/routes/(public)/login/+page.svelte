<script lang="ts">
	import { goto } from '$app/navigation';
	import { post } from '$lib/api';
	import { LANDING } from '$lib/session';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Sprig from '$lib/components/Sprig.svelte';
	import Seo from '$lib/components/Seo.svelte';

	let email = $state('');
	let password = $state('');
	let submitting = $state(false);
	let error = $state('');

	async function submit(e: Event) {
		e.preventDefault();
		submitting = true;
		error = '';
		try {
			const session = await post(fetch, '/auth/login', { email, password });
			// Same fallback PublicNav.svelte uses for the identical lookup —
			// previously this one fell back to an admin-only route, which
			// would 401 any non-admin role that ever reached it
			// (specs/v4/04-known-issues.md#l1). Dead code today (the backend
			// only ever returns a role present in LANDING) but inconsistent
			// and would misbehave the moment that stops being true.
			goto(LANDING[session?.role] || '/account');
		} catch (err: any) {
			error = err.status === 401 ? 'Incorrect email or password.' : err.message;
		} finally {
			submitting = false;
		}
	}
</script>

<Seo title="Log in — Clinic" description="Log in to your Clinic account." path="/login" noindex />

<div class="container wrap">
	<section class="card-panel">
		<div class="ph botanic"><h2><Sprig /> Log in</h2></div>
		<form class="pb" onsubmit={submit}>
			<TextField label="Email" type="email" bind:value={email} required />
			<TextField label="Password" type="password" bind:value={password} required />
			{#if error}<p class="error">{error}</p>{/if}
			<Button type="submit" loading={submitting}>Sign in</Button>
			<p class="hint">New here? <a href="/signup">Create a client account</a> or <a href="/join">apply as a practitioner</a>.</p>
		</form>
	</section>
</div>

<style>
	.wrap {
		padding: var(--space-6) var(--space-5); max-width: 26rem;
		min-height: 70dvh; display: flex; flex-direction: column; justify-content: center;
	}
	form { display: grid; gap: var(--space-3); }
	.error { color: var(--danger); font-size: var(--text-sm); }
</style>
