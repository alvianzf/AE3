<script lang="ts">
	import { post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Seo from '$lib/components/Seo.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';

	let name = $state('');
	let email = $state('');
	let message = $state('');
	let sending = $state(false);
	let sent = $state(false);

	async function submit(e: Event) {
		e.preventDefault();
		sending = true;
		try {
			await post(fetch, '/contact', { name, email, message });
			sent = true;
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			sending = false;
		}
	}
</script>

<Seo title="Contact — Clinic" description="Get in touch with the Clinic team." path="/contact" />

<div class="container page">
	<h1>Contact us</h1>
	<p class="lede">
		Looking for a practitioner, or already working with one? The fastest
		path is still <a href="/practitioners">finding a practitioner</a> or
		using their profile's own contact form. Everything else — partnership,
		press, or anything that doesn't fit elsewhere — goes here.
	</p>

	{#if sent}
		<p class="sent">Thanks — we'll get back to you soon.</p>
	{:else}
		<form onsubmit={submit}>
			<TextField label="Name" bind:value={name} required />
			<TextField label="Email" type="email" bind:value={email} required />
			<TextField label="Message" type="textarea" bind:value={message} required />
			<Button type="submit" loading={sending}>Send</Button>
		</form>
	{/if}
</div>

<style>
	.page { max-width: 32rem; padding: var(--space-7) 0; }
	h1 { font-size: var(--text-2xl); margin-bottom: var(--space-3); }
	.lede { color: var(--ink-2); margin-bottom: var(--space-5); }
	.lede a { color: var(--accent-ink); }
	form { display: grid; gap: var(--space-3); }
	.sent { color: var(--ok); font-weight: 650; }
</style>
