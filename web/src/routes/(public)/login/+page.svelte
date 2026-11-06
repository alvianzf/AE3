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
			goto(LANDING[session?.role] || '/account');
		} catch (err: any) {
			error = err.status === 401 ? 'Incorrect email or password.' : err.message;
		} finally {
			submitting = false;
		}
	}
</script>

<Seo title="Log in — Functional Health Collab" description="Log in to your Functional Health Collab account." path="/login" noindex />

<div class="container wrap">
	<section class="card-panel">
		<div class="ph">
			<h2><Sprig size={20} /> Member Sign In</h2>
		</div>
		<form class="pb" onsubmit={submit}>
			<TextField label="Email address" type="email" bind:value={email} placeholder="you@example.com" required />
			<TextField label="Password" type="password" bind:value={password} required />
			{#if error}<p class="error">{error}</p>{/if}
			<Button type="submit" loading={submitting}>Sign In</Button>
			<div class="auth-hints">
				<p class="hint">Looking for care? <a href="/signup">Create a client account</a></p>
				<p class="hint">Practicing clinician? <a href="/join">Apply as a practitioner</a></p>
			</div>
		</form>
	</section>
</div>

<style>
	.wrap {
		padding: var(--space-7) var(--space-5);
		max-width: 28rem;
		margin: 0 auto;
		min-height: 70dvh;
		display: flex;
		flex-direction: column;
		justify-content: center;
	}
	form {
		display: grid;
		gap: var(--space-4);
	}
	.error {
		color: var(--danger, #b13434);
		font-size: var(--text-sm);
		background: #fbe8e8;
		padding: .65rem .85rem;
		border-radius: 8px;
		margin: 0;
	}
	.auth-hints {
		display: grid;
		gap: .35rem;
		margin-top: .4rem;
		border-top: 1px solid rgba(45, 106, 79, 0.1);
		padding-top: var(--space-3);
	}
	.hint {
		font-size: var(--text-xs);
		color: #52796f;
		margin: 0;
	}
	.hint a {
		color: #2d6a4f;
		font-weight: 700;
	}
</style>