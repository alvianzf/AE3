<script lang="ts">
	import { goto } from '$app/navigation';
	import { PUBLIC_API_BASE } from '$env/static/public';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Sprig from '$lib/components/Sprig.svelte';

	let name = $state('');
	let email = $state('');
	let password = $state('');
	let bio = $state('');
	let specialties = $state('');
	let languages = $state('');
	let years = $state('0');
	let price = $state('0');
	let photo = $state<FileList | null>(null);
	let submitting = $state(false);
	let error = $state('');

	async function submit(e: Event) {
		e.preventDefault();
		submitting = true;
		error = '';
		const fd = new FormData();
		fd.set('name', name);
		fd.set('email', email);
		fd.set('password', password);
		fd.set('bio', bio);
		fd.set('specialties', JSON.stringify(specialties.split(',').map((s) => s.trim()).filter(Boolean)));
		fd.set('languages', JSON.stringify(languages.split(',').map((s) => s.trim()).filter(Boolean)));
		fd.set('years_experience', years);
		fd.set('consultation_price_cents', String(Math.round(Number(price) * 100)));
		if (photo && photo[0]) fd.set('photo', photo[0]);
		try {
			const res = await fetch(`${PUBLIC_API_BASE}/api/practitioners`, { method: 'POST', body: fd });
			if (!res.ok) {
				const body = await res.json().catch(() => ({}));
				throw new Error(body?.detail || 'Could not submit application.');
			}
			goto('/join/submitted');
		} catch (err: any) {
			error = err.message;
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head><title>Join as a practitioner — Clinic</title></svelte:head>

<div class="container wrap">
	<section class="card-panel leafmark">
		<div class="ph botanic"><h2><Sprig /> Apply as a practitioner</h2></div>
		<form class="pb" onsubmit={submit}>
			<TextField label="Full name" bind:value={name} required />
			<TextField label="Email" type="email" bind:value={email} required />
			<TextField label="Password" type="password" bind:value={password} required hint="At least 8 characters" />
			<TextField label="Bio" type="textarea" bind:value={bio} />
			<TextField label="Specialties (comma-separated)" bind:value={specialties} />
			<TextField label="Languages (comma-separated)" bind:value={languages} />
			<div class="row2">
				<TextField label="Years of experience" type="number" bind:value={years} />
				<TextField label="Consultation price (USD)" type="number" bind:value={price} />
			</div>
			<div class="field">
				<label for="photo">Photo</label>
				<input id="photo" type="file" accept="image/*" onchange={(e) => (photo = (e.target as HTMLInputElement).files)} />
			</div>
			{#if error}<p class="error">{error}</p>{/if}
			<Button type="submit" loading={submitting}>Submit application</Button>
		</form>
	</section>
</div>

<style>
	.wrap { padding: var(--space-6) var(--space-5); max-width: 34rem; }
	form { display: grid; gap: var(--space-3); }
	.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3); }
	.field { display: flex; flex-direction: column; gap: .35rem; }
	.error { color: var(--danger); font-size: var(--text-sm); }
</style>
