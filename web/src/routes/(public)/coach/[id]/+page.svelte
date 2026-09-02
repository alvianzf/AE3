<script lang="ts">
	import { post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Chip from '$lib/components/Chip.svelte';
	import Quiet from '$lib/components/Quiet.svelte';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';

	let { data } = $props();
	const p = $derived(data.practitioner);

	let name = $state('');
	let email = $state('');
	let message = $state('');
	let submitting = $state(false);

	async function submitContact(e: Event) {
		e.preventDefault();
		submitting = true;
		try {
			await post(fetch, `/practitioners/${p.id}/contact`, { name, email, message });
			toast('Message sent — the practitioner will reach out.');
			name = email = message = '';
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head><title>{p.name} — Clinic</title></svelte:head>

<div class="container coach">
	<!-- Tier 2: the profile is context, not the reason someone's here (specs/v4/03) -->
	<Quiet title="Practitioner profile">
		<div class="head">
			<div class="photo" style={p.photo_path ? `background-image:url(${p.photo_path})` : ''}>
				{#if !p.photo_path}<span>{p.name?.[0] ?? '?'}</span>{/if}
			</div>
			<div>
				<h1>{p.name}</h1>
				<div class="chip-row">
					{#each p.specialties ?? [] as s (s)}<Chip tone="accent">{s}</Chip>{/each}
				</div>
				<p class="hint">{p.years_experience ?? 0} years experience · {(p.languages ?? []).join(', ') || 'Language not listed'}</p>
			</div>
		</div>
		<p>{p.bio || 'No bio yet.'}</p>
	</Quiet>

	<!-- Tier 1 + leafmark: the CTA is the reason this page exists -->
	<Spotlight title="Get in touch" leaf>
		<form onsubmit={submitContact}>
			<TextField label="Your name" bind:value={name} required />
			<TextField label="Your email" type="email" bind:value={email} required />
			<TextField label="Message" type="textarea" bind:value={message} required />
			<Button type="submit" loading={submitting}>Send message</Button>
		</form>
	</Spotlight>
</div>

<style>
	.coach { display: grid; gap: var(--space-5); padding: var(--space-6) var(--space-5); max-width: 42rem; }
	.head { display: flex; gap: var(--space-4); margin-bottom: var(--space-3); }
	.photo { width: 5rem; height: 5rem; border-radius: 50%; background: var(--accent-soft); background-size: cover; background-position: center; display: flex; align-items: center; justify-content: center; flex: 0 0 auto; }
	.photo span { font-size: 1.6rem; font-weight: 700; color: var(--accent-ink); }
	form { display: grid; gap: var(--space-3); margin-top: var(--space-2); }
</style>
