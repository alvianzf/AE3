<script lang="ts">
	import { post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Seo from '$lib/components/Seo.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Sprig from '$lib/components/Sprig.svelte';

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

<Seo title="Contact Us — Functional Health Collab" description="Get in touch with the Functional Health Collab support and partnerships team." path="/contact" />

<div class="container contact-page">
	<div class="contact-header">
		<div class="badge-wrap">
			<span class="logo-mark"><Sprig size={18} /></span>
			<span>Get in Touch</span>
		</div>
		<h1>Contact our team</h1>
		<p class="lede">
			Looking for a practitioner or already working with one? The best path is browsing our <a href="/practitioners">Practitioner Directory</a> or messaging them via their profile. For practice partnerships, institutional queries, or general assistance, reach out below.
		</p>
	</div>

	<div class="card-panel contact-card">
		{#if sent}
			<div class="sent-box">
				<h2>Message sent</h2>
				<p>Thank you for reaching out. A member of our collaborative team will respond within 1 business day.</p>
				<a class="btn-home" href="/">Back to Home</a>
			</div>
		{:else}
			<form class="contact-form" onsubmit={submit}>
				<TextField label="Your Name" bind:value={name} placeholder="Jane Doe" required />
				<TextField label="Email Address" type="email" bind:value={email} placeholder="jane@example.com" required />
				<TextField label="Your Message" type="textarea" bind:value={message} placeholder="How can we help your practice or health journey?" required />
				<Button type="submit" loading={sending}>Send Message</Button>
			</form>
		{/if}
	</div>
</div>

<style>
	.contact-page {
		max-width: 36rem;
		padding: var(--space-7) var(--space-5);
		margin: 0 auto;
	}
	.contact-header {
		text-align: center;
		margin-bottom: var(--space-6);
		display: flex;
		flex-direction: column;
		align-items: center;
	}
	.badge-wrap {
		display: inline-flex;
		align-items: center;
		gap: .5rem;
		background: #e8f4ec;
		color: #1b4332;
		border: 1px solid rgba(45, 106, 79, 0.2);
		padding: .35rem .85rem;
		border-radius: 999px;
		font-size: var(--text-xs);
		font-weight: 750;
		margin-bottom: var(--space-4);
	}
	.logo-mark {
		display: inline-flex;
		color: #2d6a4f;
	}
	.contact-header h1 {
		font-size: clamp(2rem, 3.2vw, 2.5rem);
		font-weight: 850;
		color: #1b4332;
		letter-spacing: -.025em;
		margin: 0;
	}
	.lede {
		color: #52796f;
		font-size: var(--text-sm);
		max-width: 32rem;
		margin: var(--space-3) auto 0;
		line-height: 1.6;
	}
	.lede a {
		color: #2d6a4f;
		font-weight: 700;
	}
	.contact-card {
		padding: var(--space-6);
	}
	.contact-form {
		display: grid;
		gap: var(--space-4);
	}
	.sent-box {
		text-align: center;
		padding: var(--space-4) 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-3);
	}
	.sent-box h2 {
		color: #1b4332;
		font-size: var(--text-xl);
		margin: 0;
	}
	.sent-box p {
		color: #52796f;
		font-size: var(--text-sm);
		margin: 0;
	}
	.btn-home {
		display: inline-flex;
		background: #2d6a4f;
		color: #ffffff;
		padding: .65rem 1.25rem;
		border-radius: 10px;
		text-decoration: none;
		font-size: var(--text-sm);
		font-weight: 750;
		margin-top: var(--space-2);
	}
	.btn-home:hover {
		background: #1b4332;
	}
</style>