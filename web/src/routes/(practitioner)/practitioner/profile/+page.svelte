<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { put } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';

	let { data } = $props();
	const p = $derived(data.profile);

	let name = $state('');
	let bio = $state('');
	let years_experience = $state('0');
	let saving = $state(false);

	// Seed the editable fields whenever the loaded profile changes (initial
	// load, or after invalidateAll() following a save) — not just once.
	$effect(() => {
		name = p?.name ?? '';
		bio = p?.bio ?? '';
		years_experience = String(p?.years_experience ?? 0);
	});

	async function save(e: Event) {
		e.preventDefault();
		saving = true;
		try {
			await put(fetch, '/me/profile', { name, bio, years_experience: Number(years_experience) });
			toast('Profile updated.');
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head><title>Profile — Practitioner portal</title></svelte:head>

<!-- specs/v4.2 — the "Anthropic API key" panel that used to live here is
     gone: every practitioner now runs against the app's own shared Nebius
     key, so there's nothing left for a practitioner to set. -->
<Spotlight title="Your profile">
	<form onsubmit={save}>
		<TextField label="Name" bind:value={name} required />
		<TextField label="Bio" type="textarea" bind:value={bio} />
		<TextField label="Years of experience" type="number" bind:value={years_experience} />
		<Button type="submit" loading={saving}>Save</Button>
	</form>
</Spotlight>

<style>
	form { display: grid; gap: var(--space-3); margin-top: var(--space-2); }
</style>
