<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { get, post } from '$lib/api';
	import TextField from '$lib/components/TextField.svelte';
	import Select from '$lib/components/Select.svelte';
	import Button from '$lib/components/Button.svelte';
	import Sprig from '$lib/components/Sprig.svelte';
	import Seo from '$lib/components/Seo.svelte';

	let name = $state('');
	let email = $state('');
	let password = $state('');
	// specs/v4.1/01 — arriving from a practitioner's profile page
	// (?practitioner=<id>) pre-selects them instead of handing back a
	// blank picker the visitor has to re-search. Read only in the browser:
	// this page is prerendered, and `url.searchParams` isn't available
	// during that static render.
	let practitionerId = $state(
		browser ? (new URL(window.location.href)).searchParams.get('practitioner') ?? '' : ''
	);
	let practitioners = $state<any[]>([]);
	let loadingPractitioners = $state(true);
	let submitting = $state(false);
	let error = $state('');

	// The signup form has no way to complete without a practitioner_id
	// (POST /api/clients 400s without one, app/main.py) — fetched client-side
	// rather than at prerender time so the picker never offers a practitioner
	// who has since been suspended or downgraded off Pro.
	let preselectedMissing = $state(false);
	onMount(async () => {
		try {
			const all = await get(fetch, '/practitioners');
			practitioners = (all ?? []).filter((p: any) => p.plan === 'pro');
			if (practitionerId && !practitioners.some((p) => p.id === practitionerId)) {
				preselectedMissing = true;
				practitionerId = '';
			}
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

<Seo title="Create Client Account — Functional Health Collab" description="Create your confidential client account and connect with your functional health practitioner." path="/signup" noindex />

<div class="container wrap">
	<section class="card-panel">
		<div class="ph">
			<h2><Sprig size={20} /> Create Your Client Account</h2>
		</div>
		<form class="pb" onsubmit={submit}>
			{#if loadingPractitioners}
				<p class="hint">Loading available practitioners…</p>
			{:else if practitioners.length === 0}
				<p class="hint">No practitioners are accepting new clients right now.</p>
				<a class="btn-ghost" href="/practitioners">Browse Practitioner Directory</a>
			{:else}
				{#if preselectedMissing}
					<div class="alert-box">
						<p>The practitioner you selected isn't currently accepting new clients — choose another provider below.</p>
					</div>
				{/if}
				<Select
					label="Select your practitioner"
					bind:value={practitionerId}
					required
					options={practitioners.map((p) => ({ value: p.id, label: p.name }))}
				/>
				<TextField label="Full Name" bind:value={name} placeholder="Your name" required />
				<TextField label="Email Address" type="email" bind:value={email} placeholder="you@example.com" required />
				<TextField label="Password" type="password" bind:value={password} required hint="At least 8 characters" />
				{#if error}<p class="error">{error}</p>{/if}
				<Button type="submit" loading={submitting} disabled={!practitionerId}>Create Client Account</Button>
			{/if}
			<div class="auth-hints">
				<p class="hint">Already have an account? <a href="/login">Log in</a></p>
			</div>
		</form>
	</section>
</div>

<style>
	.wrap {
		padding: var(--space-7) var(--space-5);
		max-width: 30rem;
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
	.alert-box {
		background: #fdf3e3;
		border: 1px solid rgba(168, 106, 18, 0.25);
		color: #a86a12;
		padding: .65rem .85rem;
		border-radius: 8px;
		font-size: var(--text-xs);
	}
	.alert-box p {
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
		font-weight: 750;
	}
	.btn-ghost {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border: 1.5px solid rgba(45, 106, 79, 0.25);
		color: #1b4332;
		padding: .65rem 1rem;
		border-radius: 10px;
		text-decoration: none;
		font-size: var(--text-sm);
		font-weight: 750;
		text-align: center;
	}
	.btn-ghost:hover {
		background: #f4f8f4;
		border-color: #2d6a4f;
	}
</style>