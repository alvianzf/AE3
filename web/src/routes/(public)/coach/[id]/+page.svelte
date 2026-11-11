<script lang="ts">
	import { PUBLIC_SITE_URL } from '$env/static/public';
	import { post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Chip from '$lib/components/Chip.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import LeafField from '$lib/components/LeafField.svelte';
	import { jsonLdScript } from '$lib/seo';

	let { data } = $props();
	const p = $derived(data.practitioner);

	const description = $derived(
		p.bio?.trim()
			? p.bio.slice(0, 200)
			: `${p.name} on Functional Health Collaborative — verified functional medicine practitioner backed by synthesized clinical intelligence.`
	);

	const personJsonLd = $derived({
		'@context': 'https://schema.org',
		'@type': 'Person',
		name: p.name,
		description,
		url: `${PUBLIC_SITE_URL}/coach/${p.id}`,
		...(p.photo_path ? { image: p.photo_path } : {}),
		...(p.specialties?.length ? { knowsAbout: p.specialties } : {}),
		...(p.languages?.length ? { knowsLanguage: p.languages } : {})
	});

	let name = $state('');
	let email = $state('');
	let message = $state('');
	let submitting = $state(false);

	async function submitContact(e: Event) {
		e.preventDefault();
		if (!name.trim() || !email.trim() || !message.trim()) return;
		submitting = true;
		try {
			await post(fetch, `/practitioners/${p.id}/contact`, { name, email, message });
			toast('Message sent — the practitioner will reach out directly.');
			name = email = message = '';
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			submitting = false;
		}
	}
</script>

<Seo
	title="{p.name} — Functional Medicine Practitioner"
	{description}
	path="/coach/{p.id}"
	image={p.photo_path || undefined}
	type="profile"
/>
<svelte:head>
	{@html jsonLdScript(personJsonLd)}
</svelte:head>

<!-- ══ BOTANICAL PROFILE HERO ══ -->
<section class="profile-hero">
	<div class="leaf-ambient">
		<LeafField count={18} />
	</div>

	<div class="container hero-inner">
		<nav class="breadcrumb-nav" aria-label="Breadcrumb">
			<a href="/practitioners" class="back-link">
				<Icon name="chevron" size={12} />
				<span>Back to Practitioner Directory</span>
			</a>
		</nav>

		<div class="hero-profile-summary">
			<div class="photo-wrap" style={p.photo_path ? `background-image:url(${p.photo_path})` : ''}>
				{#if !p.photo_path}
					<span>{p.name?.[0] ?? '?'}</span>
				{/if}
			</div>

			<div class="hero-title-group">
				<div class="badge-row">
					{#if p.accepting_new_clients}
						<span class="active-badge">
							<span class="status-dot"></span>
							Accepting New Clients
						</span>
					{:else}
						<span class="waitlist-badge">Waitlist Only</span>
					{/if}
					<span class="verified-pill">
						<Icon name="check" size={11} />
						Verified Clinical Partner
					</span>
				</div>

				<h1 class="practitioner-name">{p.name}</h1>

				<div class="meta-strip">
					<span class="meta-item">
						<Icon name="calendar" size={13} />
						{p.years_experience != null ? `${p.years_experience} Years Clinical Experience` : 'Experienced Practitioner'}
					</span>
					{#if p.languages && p.languages.length}
						<span class="meta-dot">·</span>
						<span class="meta-item">
							<Icon name="globe" size={13} />
							{p.languages.join(', ')}
						</span>
					{/if}
				</div>
			</div>
		</div>
	</div>
</section>

<!-- ══ MAIN 2-COLUMN PROFILE CONTENT ══ -->
<div class="container profile-layout">
	<!-- Left Column: Clinical Philosophy, Bio, and Specialties -->
	<main class="left-col">
		<section class="content-card">
			<h2 class="card-title">About & Clinical Focus</h2>
			<p class="bio-text">
				{p.bio || 'Dedicated to personalized root-cause health coaching combining lifestyle medicine, nutrition, and evidence-grounded therapeutic interventions.'}
			</p>

			{#if p.specialties && p.specialties.length}
				<div class="specialties-section">
					<h3 class="subhead">Areas of Clinical Focus</h3>
					<div class="chips-grid">
						{#each p.specialties as s (s)}
							<span class="nature-chip">
								<span class="leaf-bullet">🌿</span>
								<span>{s}</span>
							</span>
						{/each}
					</div>
				</div>
			{/if}
		</section>

		<section class="content-card">
			<h2 class="card-title">How Consultations Work with {p.name}</h2>
			<div class="workflow-steps">
				<div class="wf-step">
					<span class="wf-num">1</span>
					<div>
						<strong>Comprehensive Intake & Health History</strong>
						<p>Fill out in-depth functional health questionnaires, symptom timelines, and upload previous lab markers.</p>
					</div>
				</div>
				<div class="wf-step">
					<span class="wf-num">2</span>
					<div>
						<strong>Deep Clinical Preparation</strong>
						<p>{p.name} reviews your complete health history, timelines, and lab biomarkers, cross-referencing your case against peer-reviewed functional medicine literature so no detail is missed.</p>
					</div>
				</div>
				<div class="wf-step">
					<span class="wf-num">3</span>
					<div>
						<strong>Collaborative Action Plan</strong>
						<p>Receive an individualized wellness roadmap with direct citations, dietary modifications, and lifestyle steps.</p>
					</div>
				</div>
			</div>
		</section>
	</main>

	<!-- Right Column: Direct Booking & Inquiry Action Cards -->
	<aside class="right-col">
		<div class="booking-card">
			<div class="booking-header">
				<span class="booking-badge">Direct Client Matching</span>
				<h3>Consult with {p.name}</h3>
				<p>Create your private account to connect with {p.name} and begin your personalized functional health plan.</p>
			</div>

			<a class="btn-book-primary" href="/signup?practitioner={p.id}">
				<span>Sign Up with {p.name}</span>
				<Icon name="chevron" size={14} />
			</a>

			<div class="booking-guarantee">
				<Icon name="lock" size={13} />
				<span>Private, encrypted health record vault</span>
			</div>
		</div>

		<div class="inquiry-card">
			<h3>Have a question first?</h3>
			<p>Send a message directly to {p.name} before booking your intake consultation.</p>

			<form onsubmit={submitContact} class="inquiry-form">
				<TextField label="Your full name" bind:value={name} placeholder="e.g. Sarah Jenkins" required />
				<TextField label="Email address" type="email" bind:value={email} placeholder="you@example.com" required />
				<TextField label="Your message or health question" type="textarea" bind:value={message} placeholder="Tell {p.name} a bit about your health goals..." required />
				<button type="submit" class="btn-send-inquiry" disabled={submitting}>
					{#if submitting}
						<span>Sending message…</span>
					{:else}
						<Icon name="mail" size={14} />
						<span>Send Direct Message</span>
					{/if}
				</button>
			</form>
		</div>
	</aside>
</div>

<style>
	/* ── Hero Section ────────────────────────────────────────────────── */
	.profile-hero {
		position: relative;
		background: linear-gradient(155deg, #0d2318 0%, #173827 50%, #0f2c1e 100%);
		color: #ffffff;
		padding: var(--space-5) 0 var(--space-6);
		overflow: hidden;
		border-bottom: 1px solid rgba(82, 183, 136, 0.2);
	}
	.leaf-ambient {
		position: absolute;
		inset: 0;
		pointer-events: none;
		--leaf-color: rgba(116, 198, 157, 0.4);
	}
	.hero-inner {
		position: relative;
		z-index: 2;
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.breadcrumb-nav {
		margin-bottom: .2rem;
	}
	.back-link {
		display: inline-flex;
		align-items: center;
		gap: .4rem;
		color: #74c69d;
		font-size: var(--text-xs);
		font-weight: 650;
		text-decoration: none;
		padding: .25rem .5rem;
		border-radius: 6px;
		background: rgba(255, 255, 255, 0.06);
		transition: all .15s ease;
	}
	.back-link:hover {
		background: rgba(255, 255, 255, 0.14);
		color: #ffffff;
	}
	.back-link :global(svg) {
		transform: rotate(180deg);
	}
	.hero-profile-summary {
		display: flex;
		align-items: center;
		gap: var(--space-5);
		flex-wrap: wrap;
	}
	.photo-wrap {
		width: 5.5rem;
		height: 5.5rem;
		border-radius: 50%;
		background: #e8f4ec;
		border: 3px solid #52b788;
		background-size: cover;
		background-position: center;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
	}
	.photo-wrap span {
		font-size: 2.2rem;
		font-weight: 800;
		color: #2d6a4f;
	}
	.hero-title-group {
		display: flex;
		flex-direction: column;
		gap: .4rem;
	}
	.badge-row {
		display: flex;
		align-items: center;
		gap: .5rem;
		flex-wrap: wrap;
	}
	.active-badge {
		display: inline-flex;
		align-items: center;
		gap: .35rem;
		font-size: var(--text-xs);
		font-weight: 650;
		color: #d8f3dc;
		background: rgba(82, 183, 136, 0.25);
		border: 1px solid rgba(82, 183, 136, 0.4);
		padding: .2rem .6rem;
		border-radius: 99px;
	}
	.status-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #52b788;
	}
	.waitlist-badge {
		font-size: var(--text-xs);
		font-weight: 650;
		color: #ced4da;
		background: rgba(255, 255, 255, 0.1);
		padding: .2rem .6rem;
		border-radius: 99px;
	}
	.verified-pill {
		display: inline-flex;
		align-items: center;
		gap: .3rem;
		font-size: var(--text-xs);
		font-weight: 650;
		color: #74c69d;
	}
	.practitioner-name {
		font-size: clamp(1.8rem, 3.2vw, 2.6rem);
		font-weight: 800;
		letter-spacing: -.02em;
		color: #ffffff;
		margin: 0;
	}
	.meta-strip {
		display: flex;
		align-items: center;
		gap: .5rem;
		font-size: var(--text-sm);
		color: #d8f3dc;
		opacity: 0.9;
		flex-wrap: wrap;
	}
	.meta-item {
		display: inline-flex;
		align-items: center;
		gap: .35rem;
	}
	.meta-dot {
		color: #74c69d;
	}

	/* ── 2-Column Content Layout ─────────────────────────────────────── */
	.profile-layout {
		display: grid;
		grid-template-columns: 1fr 22rem;
		gap: var(--space-6);
		padding: var(--space-6) var(--space-5) var(--space-7);
		align-items: flex-start;
	}
	.left-col {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}
	.right-col {
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
		position: sticky;
		top: 5rem;
	}

	/* ── Cards ───────────────────────────────────────────────────────── */
	.content-card {
		background: #ffffff;
		border: 1px solid rgba(45, 106, 79, 0.16);
		border-radius: 18px;
		padding: var(--space-5);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.02);
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.card-title {
		font-size: 1.35rem;
		font-weight: 750;
		color: #1b4332;
		margin: 0;
		letter-spacing: -.01em;
	}
	.bio-text {
		font-size: var(--text-base);
		color: #2d3748;
		line-height: 1.7;
		margin: 0;
	}
	.subhead {
		font-size: var(--text-sm);
		font-weight: 750;
		text-transform: uppercase;
		letter-spacing: .06em;
		color: #2d6a4f;
		margin: 0 0 .6rem;
	}
	.chips-grid {
		display: flex;
		flex-wrap: wrap;
		gap: .5rem;
	}
	.nature-chip {
		display: inline-flex;
		align-items: center;
		gap: .4rem;
		background: #e8f4ec;
		color: #1b4332;
		border: 1px solid rgba(45, 106, 79, 0.15);
		padding: .35rem .75rem;
		border-radius: 8px;
		font-size: var(--text-xs);
		font-weight: 650;
	}
	.leaf-bullet {
		font-size: .85rem;
	}

	.workflow-steps {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.wf-step {
		display: flex;
		align-items: flex-start;
		gap: var(--space-3);
	}
	.wf-num {
		width: 1.8rem;
		height: 1.8rem;
		border-radius: 50%;
		background: #2d6a4f;
		color: #ffffff;
		font-size: var(--text-xs);
		font-weight: 750;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		margin-top: .15rem;
	}
	.wf-step strong {
		display: block;
		font-size: var(--text-sm);
		color: #1b4332;
		margin-bottom: .2rem;
	}
	.wf-step p {
		margin: 0;
		font-size: var(--text-xs);
		color: #4a5568;
		line-height: 1.5;
	}

	/* ── Booking & Inquiry Aside Cards ───────────────────────────────── */
	.booking-card {
		background: linear-gradient(145deg, #183c2c 0%, #24553e 100%);
		color: #ffffff;
		border-radius: 18px;
		padding: var(--space-5);
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		box-shadow: 0 10px 25px rgba(27, 67, 50, 0.25);
		border: 1px solid rgba(82, 183, 136, 0.3);
	}
	.booking-badge {
		font-size: .65rem;
		text-transform: uppercase;
		letter-spacing: .08em;
		font-weight: 750;
		color: #74c69d;
	}
	.booking-header h3 {
		font-size: 1.35rem;
		font-weight: 800;
		margin: .3rem 0 .4rem;
		color: #ffffff;
	}
	.booking-header p {
		font-size: var(--text-xs);
		color: #d8f3dc;
		line-height: 1.5;
		margin: 0;
		opacity: 0.9;
	}
	.btn-book-primary {
		display: inline-flex;
		align-items: center;
		justify-content: space-between;
		background: #52b788;
		color: #081c15;
		padding: .75rem 1.25rem;
		border-radius: 12px;
		font-weight: 750;
		font-size: var(--text-sm);
		text-decoration: none;
		transition: all .15s ease;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	}
	.btn-book-primary:hover {
		background: #74c69d;
		transform: translateY(-2px);
	}
	.booking-guarantee {
		display: flex;
		align-items: center;
		gap: .4rem;
		font-size: .7rem;
		color: #d8f3dc;
		opacity: 0.8;
	}

	.inquiry-card {
		background: #ffffff;
		border: 1px solid rgba(45, 106, 79, 0.16);
		border-radius: 18px;
		padding: var(--space-5);
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.inquiry-card h3 {
		font-size: var(--text-base);
		font-weight: 750;
		color: #1b4332;
		margin: 0;
	}
	.inquiry-card p {
		font-size: var(--text-xs);
		color: #6c757d;
		line-height: 1.5;
		margin: 0;
	}
	.inquiry-form {
		display: grid;
		gap: var(--space-3);
		margin-top: .4rem;
	}
	.btn-send-inquiry {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: .45rem;
		background: #2d6a4f;
		color: #ffffff;
		border: none;
		padding: .65rem 1rem;
		border-radius: 10px;
		font-size: var(--text-sm);
		font-weight: 700;
		cursor: pointer;
		transition: background .15s ease;
	}
	.btn-send-inquiry:hover:not(:disabled) {
		background: #1b4332;
	}
	.btn-send-inquiry:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	/* ── Responsive Adaptations ──────────────────────────────────────── */
	@media (max-width: 860px) {
		.profile-layout {
			grid-template-columns: 1fr;
		}
		.right-col {
			position: static;
		}
	}
</style>
