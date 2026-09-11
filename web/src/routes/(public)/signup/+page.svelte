<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { get, post } from '$lib/api';
	import TextField from '$lib/components/TextField.svelte';
	import Select from '$lib/components/Select.svelte';
	import Button from '$lib/components/Button.svelte';
	import Sprig from '$lib/components/Sprig.svelte';

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
	//
	// specs/v4.1/01 — the pro-only filter here has no equivalent on
	// /practitioners (all plans browsable there), so a practitioner a
	// visitor found and liked could silently vanish from this list. If the
	// preselected practitioner isn't in the pro-only set, surface that
	// explicitly instead of just dropping the selection.
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

<svelte:head><title>Create your account — Clinic</title></svelte:head>

<div class="container wrap">
	<section class="card-panel">
		<div class="ph botanic"><h2><Sprig /> Create your account</h2></div>
		<form class="pb" onsubmit={submit}>
			{#if loadingPractitioners}
				<p class="hint">Loading practitioners…</p>
			{:else if practitioners.length === 0}
				<!-- specs/v4.1/01 — was a dead end: one line of text, no way
				     forward. Point back at the directory instead. -->
				<p class="hint">No practitioners are accepting new clients right now.</p>
				<a class="btn ghost" href="/practitioners">Browse practitioners</a>
			{:else}
				{#if preselectedMissing}
					<p class="hint alert">The practitioner you selected isn't currently accepting new clients — pick another below.</p>
				{/if}
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
	.hint.alert { color: var(--warn); }
	.btn.ghost {
		display: inline-flex; align-items: center; justify-content: center;
		border: 1px solid var(--line-2); color: var(--ink); padding: .55rem 1rem;
		border-radius: 99px; text-decoration: none; font-size: var(--text-sm); font-weight: 650;
		min-height: var(--tap-min); width: fit-content;
	}
</style>
