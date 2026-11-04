<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { api } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Workspace from '$lib/components/Workspace.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Toggle from '$lib/components/Toggle.svelte';
	import Chip from '$lib/components/Chip.svelte';

	let { data } = $props();
	const p = $derived(data.profile);

	// specs/v8 §8.3 — the profile-builder form the landing page's own
	// "available practitioners" highlight (§8.1) and the public directory
	// both depend on. The practitioners table already carried most of
	// these columns (bio/specialties/languages/years_experience/price) —
	// this page just never exposed a form for most of them.
	let name = $state('');
	let bio = $state('');
	let years_experience = $state('0');
	let consultation_price_cents = $state('0');
	let accepting_new_clients = $state(false);
	let specialties = $state<string[]>([]);
	let languages = $state<string[]>([]);
	let specialtyInput = $state('');
	let languageInput = $state('');
	let photoFile = $state<File | null>(null);
	let photoPreview = $state('');
	let saving = $state(false);

	$effect(() => {
		name = p?.name ?? '';
		bio = p?.bio ?? '';
		years_experience = String(p?.years_experience ?? 0);
		consultation_price_cents = String(p?.consultation_price_cents ?? 0);
		accepting_new_clients = !!p?.accepting_new_clients;
		specialties = [...(p?.specialties ?? [])];
		languages = [...(p?.languages ?? [])];
	});

	function addTag(list: 'specialties' | 'languages') {
		const value = (list === 'specialties' ? specialtyInput : languageInput).trim();
		if (!value) return;
		if (list === 'specialties') {
			if (!specialties.includes(value)) specialties = [...specialties, value];
			specialtyInput = '';
		} else {
			if (!languages.includes(value)) languages = [...languages, value];
			languageInput = '';
		}
	}
	function removeTag(list: 'specialties' | 'languages', value: string) {
		if (list === 'specialties') specialties = specialties.filter((s) => s !== value);
		else languages = languages.filter((s) => s !== value);
	}
	function onTagKeydown(e: KeyboardEvent, list: 'specialties' | 'languages') {
		if (e.key === 'Enter' || e.key === ',') {
			e.preventDefault();
			addTag(list);
		}
	}

	function onPhotoChange(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (!file) return;
		photoFile = file;
		photoPreview = URL.createObjectURL(file);
	}

	async function save(e: Event) {
		e.preventDefault();
		saving = true;
		try {
			const form = new FormData();
			form.set('name', name);
			form.set('bio', bio);
			form.set('years_experience', String(Number(years_experience) || 0));
			form.set('consultation_price_cents', String(Number(consultation_price_cents) || 0));
			form.set('accepting_new_clients', String(accepting_new_clients));
			form.set('specialties', JSON.stringify(specialties));
			form.set('languages', JSON.stringify(languages));
			if (photoFile) form.set('photo', photoFile);
			await api(fetch, '/me/profile', { method: 'PUT', body: form });
			toast('Profile updated.');
			photoFile = null;
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head><title>Profile — Practitioner portal</title></svelte:head>

<Workspace title="Your profile" backHref="/practitioner">
	<form onsubmit={save}>
		<div class="photo-row">
			<div class="photo" style={(photoPreview || p?.photo_path) ? `background-image:url(${photoPreview || p?.photo_path})` : ''}>
				{#if !photoPreview && !p?.photo_path}<span>{name?.[0] ?? '?'}</span>{/if}
			</div>
			<div>
				<label class="upload-btn">
					Change photo
					<input type="file" accept="image/jpeg,image/png,image/gif,image/webp" onchange={onPhotoChange} hidden />
				</label>
				<p class="hint">JPEG, PNG, GIF, or WebP. Up to 5 MB.</p>
			</div>
		</div>

		<TextField label="Name" bind:value={name} required />
		<TextField label="Bio" type="textarea" bind:value={bio} hint="A few sentences a prospective client will see on your public profile." />

		<div class="field">
			<label for="specialty-input">Specialties</label>
			<div class="tag-row">
				{#each specialties as s (s)}
					<Chip tone="accent">{s} <button type="button" class="chip-x" onclick={() => removeTag('specialties', s)} aria-label="Remove {s}">×</button></Chip>
				{/each}
			</div>
			<input id="specialty-input" type="text" placeholder="Type a specialty, press Enter…" bind:value={specialtyInput} onkeydown={(e) => onTagKeydown(e, 'specialties')} />
		</div>

		<div class="field">
			<label for="language-input">Languages</label>
			<div class="tag-row">
				{#each languages as l (l)}
					<Chip>{l} <button type="button" class="chip-x" onclick={() => removeTag('languages', l)} aria-label="Remove {l}">×</button></Chip>
				{/each}
			</div>
			<input id="language-input" type="text" placeholder="Type a language, press Enter…" bind:value={languageInput} onkeydown={(e) => onTagKeydown(e, 'languages')} />
		</div>

		<div class="two-col">
			<TextField label="Years of experience" type="number" bind:value={years_experience} />
			<TextField label="Consultation price (cents)" type="number" bind:value={consultation_price_cents} hint="Shown to prospective clients as a flat rate." />
		</div>

		<div class="field accepting-row">
			<div>
				<label for="accepting-toggle">Accepting new clients</label>
				<p class="hint">On: you'll be highlighted on the public landing page and directory as taking new clients.</p>
			</div>
			<Toggle checked={accepting_new_clients} onchange={(next) => (accepting_new_clients = next)} label="Accepting new clients" />
		</div>

		<Button type="submit" loading={saving}>Save</Button>
	</form>
</Workspace>

<style>
	form { display: grid; gap: var(--space-4); margin-top: var(--space-2); max-width: 32rem; }
	.photo-row { display: flex; align-items: center; gap: var(--space-4); }
	.photo {
		width: 4.5rem; height: 4.5rem; border-radius: 50%; flex: 0 0 auto;
		background: var(--accent-soft); background-size: cover; background-position: center;
		display: flex; align-items: center; justify-content: center;
	}
	.photo span { font-size: 1.6rem; font-weight: 700; color: var(--accent-ink); }
	.upload-btn {
		display: inline-flex; border: 1px solid var(--line-2); border-radius: 99px; padding: .45rem 1rem;
		font-size: var(--text-sm); font-weight: 650; cursor: pointer; background: var(--panel);
	}
	.upload-btn:hover { background: var(--panel-2); }
	.field { display: flex; flex-direction: column; gap: .35rem; }
	.field label { font-size: var(--text-sm); font-weight: 600; color: var(--ink-2); }
	.hint { color: var(--muted); font-size: var(--text-sm); margin: 0; }
	.tag-row { display: flex; flex-wrap: wrap; gap: .4rem; min-height: 1.5rem; }
	.chip-x { background: none; border: none; cursor: pointer; font: inherit; color: inherit; margin-left: .2rem; padding: 0; }
	.field input[type="text"] {
		border: 1px solid var(--line-2); border-radius: var(--r); background: var(--panel);
		padding: var(--space-3); font-size: var(--text-base); color: var(--ink); min-height: var(--tap-min);
	}
	.field input[type="text"]:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
	.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); }
	.accepting-row { flex-direction: row; align-items: flex-start; justify-content: space-between; gap: var(--space-4); }
	@media (max-width: 480px) { .two-col { grid-template-columns: 1fr; } }
</style>
