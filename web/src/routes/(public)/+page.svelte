<script lang="ts">
	import { browser } from '$app/environment';
	import { PUBLIC_SITE_URL } from '$env/static/public';
	import { get } from '$lib/api';
	import Sprig from '$lib/components/Sprig.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import LeafField from '$lib/components/LeafField.svelte';
	import { jsonLdScript } from '$lib/seo';
	import { reveal } from '$lib/actions/reveal';

	let { data } = $props();
	let practitioners = $state(data.practitioners ?? []);
	$effect(() => {
		if (!browser) return;
		get(fetch, '/practitioners').then((list) => { practitioners = list; }).catch(() => {});
	});

	const available = $derived((practitioners ?? []).filter((p: any) => p.accepting_new_clients));

	const description =
		"Find verified functional health practitioners equipped with comprehensive clinical intelligence. Personalized root-cause health plans with no missing information.";

	const orgJsonLd = {
		'@context': 'https://schema.org',
		'@type': 'Organization',
		name: 'Functional Health Collab',
		url: PUBLIC_SITE_URL,
		description,
		logo: `${PUBLIC_SITE_URL}/favicon.svg`
	};

	const healthFocusAreas = [
		{
			title: 'Gut Health & Microbiome',
			icon: 'leaf',
			desc: 'Rebalance your microbiome, resolve bloating and food sensitivities, and restore gut mucosal integrity.'
		},
		{
			title: 'Hormonal & Thyroid Balance',
			icon: 'sparkles',
			desc: 'Regulate cortisol rhythms, optimize thyroid conversion, balance sex hormones, and regain steady all-day vitality.'
		},
		{
			title: 'Immune & Autoimmune Support',
			icon: 'shield',
			desc: 'Calm systemic inflammatory pathways, uncover hidden triggers, and restore cellular resilience.'
		},
		{
			title: 'Metabolic & Longevity Health',
			icon: 'watch',
			desc: 'Optimize insulin sensitivity, cardiovascular biomarkers, and restorative circadian sleep cycles.'
		}
	];

	const pillars = [
		{
			icon: 'leaf',
			title: 'Root-Cause Investigation',
			body: 'Your practitioner explores your entire life context — genetics, nutrition, stressors, sleep, and environment — to treat the root cause rather than just suppress symptoms.'
		},
		{
			icon: 'check',
			title: 'No More Missing Information',
			body: 'No more fragmented lab results or forgotten symptoms. Your complete health history, biomarker trends, and intake answers are unified into one comprehensive patient view.'
		},
		{
			icon: 'book',
			title: 'Peer-Reviewed Clinical Evidence',
			body: 'Every therapeutic recommendation is cross-referenced with peer-reviewed functional medicine literature and clinical research with full citation transparency.'
		},
		{
			icon: 'lock',
			title: 'Private, Patient-Owned Health Vault',
			body: 'Your health history, symptom logs, and biomarker data remain private, encrypted, and strictly under your control.'
		}
	];

	const steps = [
		{
			step: '01',
			title: 'Browse & Choose Your Specialist',
			desc: 'Explore verified functional medicine practitioners by clinical focus — gut health, hormonal balance, autoimmune support, or metabolic health.'
		},
		{
			step: '02',
			title: 'Share Your Complete Health Story',
			desc: 'Complete in-depth functional health questionnaires, map your symptom timeline, and securely upload past lab panels into your confidential portal.'
		},
		{
			step: '03',
			title: 'Receive Your Informed Care Plan',
			desc: 'Your practitioner arrives at your consultation deeply informed with all dots connected, delivering an actionable, personalized care roadmap.'
		}
	];
</script>

<Seo title="Functional Health Collab — Real Answers for Your Health, Grounded in Science & Nature" {description} path="/" />
<svelte:head>{@html jsonLdScript(orgJsonLd)}</svelte:head>

<!-- ══ CLIENT-FOCUSED HERO SECTION: Nature & Leaves Botanical Canopy ══ -->
<section class="hero-section">
	<div class="leaf-ambient">
		<LeafField count={28} />
	</div>

	<div class="container hero-container">
		<div class="hero-content">
			<!-- Clean leaf badge with bare SVG logo (no boxes, no backgrounds) -->
			<div class="nature-badge">
				<span class="logo-mark"><Sprig size={18} /></span>
				<span>Personalized Functional Health For You</span>
			</div>

			<h1 class="hero-title">
				Feel like yourself again. Care guided by <span class="highlight-nature">nature</span>, proven by <span class="highlight-science">science</span>.
			</h1>

			<p class="hero-description">
				Partner with dedicated functional medicine practitioners who investigate root causes instead of rushing you.
				Behind the scenes, your practitioner is equipped with deep clinical intelligence that connects your full health timeline, labs, and peer-reviewed medical literature — delivering personalized care with zero missing information.
			</p>

			<div class="hero-actions">
				<a class="btn-nature-primary" href="/practitioners">
					<span>Find Your Practitioner</span>
					<Icon name="chevron" size={14} />
				</a>
				<a class="btn-nature-secondary" href="/signup">
					<span>Sign Up as a Client</span>
				</a>
			</div>

			<div class="hero-trust-bar">
				<div class="trust-item">
					<Icon name="users" size={15} />
					<span>100% Human Care</span>
				</div>
				<div class="trust-divider"></div>
				<div class="trust-item">
					<Icon name="check" size={15} />
					<span>No Missing Information</span>
				</div>
				<div class="trust-divider"></div>
				<div class="trust-item">
					<Icon name="book" size={14} />
					<span>Peer-Reviewed Citations</span>
				</div>
				<div class="trust-divider"></div>
				<div class="trust-item">
					<Icon name="lock" size={14} />
					<span>Private Encrypted Vault</span>
				</div>
			</div>
		</div>

		<!-- Botanical & Evidence Knowledge Graph SVG Illustration -->
		<div class="hero-visual" aria-hidden="true">
			<div class="visual-card">
				<svg class="botanical-svg" viewBox="0 0 460 380" fill="none" xmlns="http://www.w3.org/2000/svg">
					<defs>
						<linearGradient id="stemGrad" x1="0%" y1="100%" x2="100%" y2="0%">
							<stop offset="0%" stop-color="#2d6a4f" />
							<stop offset="100%" stop-color="#52b788" />
						</linearGradient>
						<linearGradient id="leafGrad" x1="0%" y1="0%" x2="100%" y2="100%">
							<stop offset="0%" stop-color="#74c69d" stop-opacity="0.35" />
							<stop offset="100%" stop-color="#2d6a4f" stop-opacity="0.1" />
						</linearGradient>
						<filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
							<feGaussianBlur stdDeviation="8" result="blur" />
							<feComposite in="SourceGraphic" in2="blur" operator="over" />
						</filter>
					</defs>

					<!-- Ambient Botanical Glow -->
					<circle cx="230" cy="190" r="140" fill="#2d6a4f" fill-opacity="0.08" filter="url(#softGlow)" />
					<circle cx="230" cy="190" r="90" fill="#74c69d" fill-opacity="0.06" />

					<!-- Knowledge Graph Traversal Lines -->
					<g opacity="0.45" stroke="#74c69d" stroke-width="1.2" stroke-dasharray="3 3">
						<line x1="120" y1="100" x2="230" y2="170" />
						<line x1="340" y1="90" x2="230" y2="170" />
						<line x1="90" y1="260" x2="230" y2="170" />
						<line x1="370" y1="250" x2="230" y2="170" />
						<line x1="120" y1="100" x2="340" y2="90" />
						<line x1="90" y1="260" x2="370" y2="250" />
					</g>

					<!-- Central Living Botanical Stem -->
					<path d="M230 350 C230 260, 220 200, 230 80" stroke="url(#stemGrad)" stroke-width="3.5" stroke-linecap="round" />
					<path d="M228 270 C190 250, 160 210, 150 170" stroke="url(#stemGrad)" stroke-width="2.5" stroke-linecap="round" />
					<path d="M230 210 C270 190, 310 160, 320 120" stroke="url(#stemGrad)" stroke-width="2.5" stroke-linecap="round" />
					<path d="M229 140 C195 120, 175 90, 170 60" stroke="url(#stemGrad)" stroke-width="2" stroke-linecap="round" />

					<!-- Botanical Leaves with Organic Fill -->
					<path d="M150 170 C130 140, 140 100, 180 110 C190 145, 175 165, 150 170 Z" fill="url(#leafGrad)" stroke="#52b788" stroke-width="1.5" />
					<path d="M320 120 C350 95, 350 60, 310 65 C295 95, 305 115, 320 120 Z" fill="url(#leafGrad)" stroke="#52b788" stroke-width="1.5" />
					<path d="M170 60 C150 40, 160 15, 190 20 C200 45, 190 55, 170 60 Z" fill="url(#leafGrad)" stroke="#52b788" stroke-width="1.5" />
					<path d="M230 80 C240 50, 265 40, 260 70 C250 85, 238 82, 230 80 Z" fill="url(#leafGrad)" stroke="#74c69d" stroke-width="1.5" />

					<!-- Evidence Nodes for Clients -->
					<g transform="translate(60, 75)">
						<rect width="130" height="42" rx="10" fill="#143023" stroke="#52b788" stroke-width="1.2" />
						<circle cx="22" cy="21" r="10" fill="#2d6a4f" />
						<path d="M18 21 L21 24 L27 18" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
						<text x="38" y="19" fill="#e8f4ec" font-size="11" font-weight="650" font-family="system-ui">Clinical Research</text>
						<text x="38" y="31" fill="#74c69d" font-size="9" font-family="system-ui">Peer-Reviewed Evidence</text>
					</g>

					<g transform="translate(275, 70)">
						<rect width="145" height="42" rx="10" fill="#143023" stroke="#52b788" stroke-width="1.2" />
						<circle cx="22" cy="21" r="10" fill="#2d6a4f" />
						<path d="M22 15 C19 18, 18 23, 22 27 C26 23, 25 18, 22 15 Z" fill="#74c69d" />
						<text x="38" y="19" fill="#e8f4ec" font-size="11" font-weight="650" font-family="system-ui">Clinical Protocols</text>
						<text x="38" y="31" fill="#74c69d" font-size="9" font-family="system-ui">Peer-Reviewed Studies</text>
					</g>

					<g transform="translate(40, 235)">
						<rect width="140" height="42" rx="10" fill="#143023" stroke="#52b788" stroke-width="1.2" />
						<circle cx="22" cy="21" r="10" fill="#2d6a4f" />
						<circle cx="22" cy="21" r="5" stroke="#74c69d" stroke-width="1.5" />
						<text x="38" y="19" fill="#e8f4ec" font-size="11" font-weight="650" font-family="system-ui">Complete Labs</text>
						<text x="38" y="31" fill="#74c69d" font-size="9" font-family="system-ui">Biomarker Trajectories</text>
					</g>

					<g transform="translate(290, 230)">
						<rect width="140" height="42" rx="10" fill="#143023" stroke="#52b788" stroke-width="1.2" />
						<circle cx="22" cy="21" r="10" fill="#52b788" />
						<path d="M18 21 L21 24 L27 18" stroke="#081c15" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
						<text x="38" y="19" fill="#e8f4ec" font-size="11" font-weight="650" font-family="system-ui">Informed Care Plan</text>
						<text x="38" y="31" fill="#74c69d" font-size="9" font-family="system-ui">Personalized For You</text>
					</g>

					<!-- Central Grounded Stamp -->
					<g transform="translate(160, 160)">
						<rect width="140" height="30" rx="15" fill="#52b788" />
						<text x="70" y="19" fill="#0d2318" font-size="11" font-weight="750" text-anchor="middle" font-family="system-ui">Clinical Intelligence</text>
					</g>
				</svg>
			</div>
		</div>
	</div>
</section>

<!-- ══ SECTION 1: WHAT WE HELP CLIENTS SOLVE ══ -->
<section class="focus-section">
	<div class="container">
		<div class="section-header text-center">
			<div class="sub-badge">Areas of Care</div>
			<h2>Real answers for complex, lingering health challenges</h2>
			<p>When conventional medicine says "your labs look normal" but you still feel exhausted, functional health uncovers the hidden imbalances.</p>
		</div>

		<div class="focus-grid">
			{#each healthFocusAreas as fa (fa.title)}
				<div class="focus-card" use:reveal>
					<div class="focus-icon-wrap">
						{#if fa.icon === 'leaf'}
							<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="focus-svg">
								<path d="M11 20A7 7 0 0 1 4 13C4 8.5 7 5 11 3c4 2 7 5.5 7 10a7 7 0 0 1-7 7z" stroke-width="1.8"/>
								<path d="M11 5v14" stroke-width="1.8" stroke-linecap="round"/>
							</svg>
						{:else if fa.icon === 'sparkles'}
							<Icon name="sparkles" size={22} />
						{:else if fa.icon === 'shield'}
							<Icon name="shield-check" size={22} />
						{:else}
							<Icon name="watch" size={22} />
						{/if}
					</div>
					<h3>{fa.title}</h3>
					<p>{fa.desc}</p>
				</div>
			{/each}
		</div>
	</div>
</section>

<!-- ══ SECTION 2: THE CLIENT CARE JOURNEY ══ -->
<section id="how-it-works" class="flow-section">
	<div class="container">
		<div class="section-header text-center">
			<div class="sub-badge">Your Journey</div>
			<h2>How it works for you as a client</h2>
			<p>A structured, supportive path from your first consultation to lasting wellness.</p>
		</div>

		<div class="steps-grid">
			{#each steps as s (s.step)}
				<div class="step-card" use:reveal>
					<div class="step-num">{s.step}</div>
					<h3>{s.title}</h3>
					<p>{s.desc}</p>
					<div class="step-line"></div>
				</div>
			{/each}
		</div>
	</div>
</section>

<!-- ══ SECTION 3: FEATURED PRACTITIONERS FOR CLIENTS ══ -->
<section class="practitioners-section">
	<div class="container">
		<div class="practitioners-header">
			<div>
				<div class="sub-badge">Verified Specialists</div>
				<h2>Meet practitioners accepting new clients</h2>
				<p>Choose a dedicated functional medicine specialist aligned with your health focus.</p>
			</div>
			<a class="view-all-link" href="/practitioners">
				<span>Explore Full Directory</span>
				<Icon name="chevron" size={14} />
			</a>
		</div>

		{#if available.length > 0}
			<div class="practitioners-grid">
				{#each available.slice(0, 3) as p (p.id)}
					<article class="practitioner-card" use:reveal>
						<div class="p-card-top">
							<div class="p-avatar" style={p.photo_path ? `background-image:url(${p.photo_path})` : ''}>
								{#if !p.photo_path}
									<span>{p.name?.[0] ?? '?'}</span>
								{/if}
							</div>
							<div class="p-meta">
								<span class="p-status">
									<span class="status-dot"></span>
									Accepting new clients
								</span>
								<h3 class="p-name">{p.name}</h3>
								<div class="p-experience">
									<Icon name="calendar" size={12} />
									<span>{p.years_experience != null ? `${p.years_experience} yrs experience` : 'Verified practitioner'}</span>
								</div>
							</div>
						</div>

						<p class="p-bio">
							{p.bio || 'Dedicated to personalized root-cause coaching combining nutrition, lifestyle modifications, and evidence-grounded medicine.'}
						</p>

						<div class="p-specialties">
							{#each (p.specialties ?? []).slice(0, 3) as s (s)}
								<span class="specialty-pill">{s}</span>
							{/each}
						</div>

						<div class="p-card-footer">
							<a class="btn-consult-card" href="/coach/{p.id}">
								<span>View Profile & Book Consult</span>
								<Icon name="chevron" size={13} />
							</a>
						</div>
					</article>
				{/each}
			</div>

			<div class="directory-jump-box">
				<p>Looking for a specific health condition, test interpretation, or modality?</p>
				<a class="btn-explore-directory" href="/practitioners">
					<Icon name="search" size={15} />
					<span>Search All {practitioners.length} Practitioners</span>
				</a>
			</div>
		{:else}
			<div class="empty-practitioners-box">
				<Icon name="users" size={32} />
				<p>Our practitioner roster is actively updating. Browse the directory to connect with available providers.</p>
				<a class="btn-nature-primary" href="/practitioners">Explore Directory</a>
			</div>
		{/if}
	</div>
</section>

<!-- ══ SECTION 4: THE 4 PILLARS OF EVIDENCE & NATURE ══ -->
<section class="pillars-section">
	<div class="container">
		<div class="section-header text-center">
			<div class="sub-badge">Why It Works</div>
			<h2>Why clients trust Functional Health Collab</h2>
			<p>High-touch human care from practitioners who are deeply informed, cross-referencing your complete history with validated clinical literature.</p>
		</div>

		<div class="pillars-grid">
			{#each pillars as p (p.title)}
				<div class="pillar-box" use:reveal>
					<div class="pillar-icon-wrap">
						{#if p.icon === 'leaf'}
							<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="p-ico">
								<path d="M11 20A7 7 0 0 1 4 13C4 8.5 7 5 11 3c4 2 7 5.5 7 10a7 7 0 0 1-7 7z" stroke-width="1.8"/>
								<path d="M11 5v14" stroke-width="1.8" stroke-linecap="round"/>
							</svg>
						{:else if p.icon === 'book'}
							<Icon name="book" size={22} />
						{:else if p.icon === 'check'}
							<Icon name="check" size={22} />
						{:else}
							<Icon name="lock" size={22} />
						{/if}
					</div>
					<h3>{p.title}</h3>
					<p>{p.body}</p>
				</div>
			{/each}
		</div>
	</div>
</section>

<!-- ══ SECTION 5: CLIENT TESTIMONIAL / COMMITMENT ══ -->
<section class="commitment-section">
	<div class="container commitment-inner">
		<div class="quote-mark">“</div>
		<blockquote>
			Finally, someone who connected the dots between my gut issues, my chronic fatigue, and my sleep. Having a practitioner who listens and backs up every single dietary change with real clinical research gave me my life back.
		</blockquote>
		<div class="client-author">
			<strong>Jessica M.</strong>
			<span>Client with Autoimmune & Microbiome Focus</span>
		</div>
	</div>
</section>

<!-- ══ CLOSING CTA BAND FOR CLIENTS ══ -->
<section class="cta-nature-band">
	<div class="leaf-ambient">
		<LeafField count={20} />
	</div>
	<div class="container cta-band-content">
		<h2>Take the first step toward lasting vitality.</h2>
		<p>Connect with a practitioner who takes the time to listen, investigate root causes, and cite every recommendation.</p>
		<div class="cta-band-buttons">
			<a class="btn-cta-main" href="/practitioners">
				<Icon name="search" size={16} />
				<span>Find Your Practitioner</span>
			</a>
			<a class="btn-cta-sub" href="/signup">
				<span>Sign Up as a Client</span>
			</a>
		</div>
	</div>
</section>

<style>
	/* ── Nature & Botanical Palette ──────────────────────────────────── */
	:global(:root) {
		--nature-forest: #1b4332;
		--nature-dark: #081c15;
		--nature-emerald: #2d6a4f;
		--nature-leaf: #40916c;
		--nature-mint: #52b788;
		--nature-pale: #74c69d;
		--nature-wash: #d8f3dc;
		--nature-soft: #f4f8f4;
		--nature-cream: #fafbf8;
	}

	/* ── Hero Section (100% Client Focused) ─────────────────────────── */
	.hero-section {
		position: relative;
		background: linear-gradient(155deg, #0d2318 0%, #173827 45%, #0f2b1d 100%);
		color: #ffffff;
		overflow: hidden;
		padding: var(--space-7) 0 calc(var(--space-7) + 1.2rem);
	}
	.leaf-ambient {
		position: absolute;
		inset: 0;
		pointer-events: none;
		z-index: 1;
		--leaf-color: rgba(116, 198, 157, 0.45);
	}
	.hero-container {
		position: relative;
		z-index: 2;
		display: grid;
		grid-template-columns: 1.15fr 0.85fr;
		gap: var(--space-7);
		align-items: center;
	}
	.hero-content {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	.nature-badge {
		display: inline-flex;
		align-items: center;
		gap: .6rem;
		padding: .35rem .85rem;
		background: rgba(45, 106, 79, 0.35);
		border: 1px solid rgba(82, 183, 136, 0.45);
		border-radius: 99px;
		color: #d8f3dc;
		font-size: var(--text-xs);
		font-weight: 650;
		width: fit-content;
		backdrop-filter: blur(8px);
	}
	/* Logo mark has ZERO boxes, borders, or backgrounds */
	.logo-mark {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		background: none;
		border: none;
		box-shadow: none;
		color: #74c69d;
	}
	.hero-title {
		font-size: clamp(2.2rem, 4.2vw, 3.4rem);
		font-weight: 800;
		line-height: 1.1;
		letter-spacing: -.03em;
		color: #ffffff;
		margin: 0;
	}
	.highlight-nature {
		color: #74c69d;
		text-decoration: underline;
		text-decoration-color: rgba(82, 183, 136, 0.5);
		text-underline-offset: 4px;
	}
	.highlight-science {
		color: #d8f3dc;
	}
	.hero-description {
		font-size: var(--text-lg);
		line-height: 1.55;
		color: #d8f3dc;
		opacity: 0.92;
		max-width: 36rem;
		margin: 0;
	}
	.hero-actions {
		display: flex;
		align-items: center;
		gap: var(--space-4);
		flex-wrap: wrap;
		margin-top: .5rem;
	}
	.btn-nature-primary {
		display: inline-flex;
		align-items: center;
		gap: .55rem;
		background: #52b788;
		color: #081c15;
		padding: .75rem 1.6rem;
		border-radius: 12px;
		font-weight: 750;
		font-size: var(--text-base);
		text-decoration: none;
		box-shadow: 0 4px 14px rgba(45, 106, 79, 0.4);
		transition: all .2s var(--ease);
	}
	.btn-nature-primary:hover {
		background: #74c69d;
		transform: translateY(-2px);
		box-shadow: 0 6px 20px rgba(82, 183, 136, 0.5);
	}
	.btn-nature-secondary {
		display: inline-flex;
		align-items: center;
		gap: .5rem;
		background: rgba(255, 255, 255, 0.08);
		color: #ffffff;
		padding: .75rem 1.4rem;
		border-radius: 12px;
		font-weight: 650;
		font-size: var(--text-base);
		text-decoration: none;
		border: 1px solid rgba(255, 255, 255, 0.25);
		transition: all .2s var(--ease);
	}
	.btn-nature-secondary:hover {
		background: rgba(255, 255, 255, 0.16);
		border-color: rgba(255, 255, 255, 0.4);
	}
	.hero-trust-bar {
		display: flex;
		align-items: center;
		gap: var(--space-4);
		flex-wrap: wrap;
		margin-top: var(--space-3);
		padding-top: var(--space-3);
		border-top: 1px solid rgba(255, 255, 255, 0.15);
		color: #d8f3dc;
		font-size: var(--text-xs);
		font-weight: 600;
	}
	.trust-item {
		display: flex;
		align-items: center;
		gap: .4rem;
	}
	.trust-item :global(svg) {
		color: #52b788;
	}
	.trust-divider {
		width: 4px;
		height: 4px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.3);
	}
	.hero-visual {
		display: flex;
		justify-content: center;
		align-items: center;
	}
	.visual-card {
		position: relative;
		width: 100%;
		max-width: 460px;
		background: rgba(20, 48, 35, 0.6);
		border: 1px solid rgba(82, 183, 136, 0.35);
		border-radius: 24px;
		padding: 1.25rem;
		backdrop-filter: blur(16px);
		box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
	}
	.botanical-svg {
		width: 100%;
		height: auto;
		display: block;
	}

	/* ── Shared Section Typography ───────────────────────────────────── */
	.section-header {
		margin-bottom: var(--space-6);
	}
	.section-header.text-center {
		text-align: center;
		max-width: 42rem;
		margin-left: auto;
		margin-right: auto;
	}
	.section-header h2 {
		font-size: clamp(1.8rem, 3vw, 2.5rem);
		font-weight: 800;
		color: #1b4332;
		letter-spacing: -.02em;
		margin-top: .4rem;
	}
	.section-header p {
		font-size: var(--text-base);
		color: #4a5568;
		line-height: 1.6;
		margin-top: .5rem;
	}
	.sub-badge {
		display: inline-block;
		font-size: var(--text-xs);
		font-weight: 750;
		text-transform: uppercase;
		letter-spacing: .08em;
		color: #2d6a4f;
		background: #e8f4ec;
		padding: .25rem .75rem;
		border-radius: 99px;
	}

	/* ── Focus Areas (What We Help Clients With) ─────────────────────── */
	.focus-section {
		padding: var(--space-7) 0;
		background: #ffffff;
		border-bottom: 1px solid #e9ecef;
	}
	.focus-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
		gap: var(--space-5);
	}
	.focus-card {
		background: #fbfdfb;
		border: 1px solid rgba(45, 106, 79, 0.15);
		border-radius: 18px;
		padding: var(--space-5);
		display: flex;
		flex-direction: column;
		gap: .6rem;
		transition: transform .2s var(--ease), box-shadow .2s var(--ease);
	}
	.focus-card:hover {
		transform: translateY(-3px);
		box-shadow: 0 10px 25px rgba(45, 106, 79, 0.08);
		border-color: #52b788;
	}
	.focus-icon-wrap {
		width: 2.8rem;
		height: 2.8rem;
		border-radius: 12px;
		background: #e8f4ec;
		color: #2d6a4f;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.focus-svg {
		width: 1.4rem;
		height: 1.4rem;
	}
	.focus-card h3 {
		font-size: var(--text-lg);
		font-weight: 750;
		color: #1b4332;
		margin: 0;
	}
	.focus-card p {
		font-size: var(--text-sm);
		color: #4a5568;
		line-height: 1.55;
		margin: 0;
	}

	/* ── Flow Section (How It Works for Clients) ─────────────────────── */
	.flow-section {
		padding: var(--space-7) 0;
		background: #fbfdfb;
		border-bottom: 1px solid #e9ecef;
	}
	.steps-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
		gap: var(--space-5);
	}
	.step-card {
		position: relative;
		background: #ffffff;
		border: 1px solid rgba(45, 106, 79, 0.15);
		border-radius: 18px;
		padding: var(--space-5);
		display: flex;
		flex-direction: column;
		gap: .6rem;
		transition: transform .2s var(--ease), box-shadow .2s var(--ease);
	}
	.step-card:hover {
		transform: translateY(-3px);
		box-shadow: 0 10px 25px rgba(45, 106, 79, 0.08);
		border-color: #52b788;
	}
	.step-num {
		font-size: var(--text-2xl);
		font-weight: 850;
		color: #52b788;
		line-height: 1;
	}
	.step-card h3 {
		font-size: var(--text-lg);
		font-weight: 750;
		color: #1b4332;
		margin: 0;
	}
	.step-card p {
		font-size: var(--text-sm);
		color: #4a5568;
		line-height: 1.55;
		margin: 0;
	}
	.step-line {
		position: absolute;
		bottom: 0;
		left: var(--space-5);
		right: var(--space-5);
		height: 3px;
		background: linear-gradient(90deg, #52b788, transparent);
		border-radius: 2px;
		opacity: 0.6;
	}

	/* ── Featured Practitioners Section ──────────────────────────────── */
	.practitioners-section {
		padding: var(--space-7) 0;
		background: #f7faf7;
	}
	.practitioners-header {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--space-4);
		margin-bottom: var(--space-6);
		flex-wrap: wrap;
	}
	.practitioners-header h2 {
		font-size: clamp(1.8rem, 3vw, 2.4rem);
		font-weight: 800;
		color: #1b4332;
		letter-spacing: -.02em;
		margin: .4rem 0 0;
	}
	.practitioners-header p {
		font-size: var(--text-base);
		color: #52796f;
		margin: .3rem 0 0;
	}
	.view-all-link {
		display: inline-flex;
		align-items: center;
		gap: .4rem;
		font-weight: 750;
		font-size: var(--text-sm);
		color: #2d6a4f;
		text-decoration: none;
		padding: .5rem .9rem;
		border-radius: 8px;
		background: #e8f4ec;
		transition: all .15s ease;
	}
	.view-all-link:hover {
		background: #2d6a4f;
		color: #ffffff;
	}
	.practitioners-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr));
		gap: var(--space-5);
	}
	.practitioner-card {
		background: #ffffff;
		border: 1px solid rgba(45, 106, 79, 0.18);
		border-radius: 18px;
		padding: var(--space-5);
		display: flex;
		flex-direction: column;
		gap: .8rem;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03);
		transition: all .2s var(--ease);
	}
	.practitioner-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 12px 30px rgba(45, 106, 79, 0.1);
		border-color: #52b788;
	}
	.p-card-top {
		display: flex;
		gap: var(--space-4);
		align-items: center;
	}
	.p-avatar {
		width: 4.2rem;
		height: 4.2rem;
		border-radius: 50%;
		background: #e8f4ec;
		border: 2px solid #52b788;
		background-size: cover;
		background-position: center;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}
	.p-avatar span {
		font-size: 1.6rem;
		font-weight: 800;
		color: #2d6a4f;
	}
	.p-meta {
		display: flex;
		flex-direction: column;
		gap: .2rem;
	}
	.p-status {
		display: inline-flex;
		align-items: center;
		gap: .35rem;
		font-size: var(--text-xs);
		font-weight: 650;
		color: #2d6a4f;
	}
	.status-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #2d6a4f;
		animation: pulse 2s infinite;
	}
	@keyframes pulse {
		0%, 100% { opacity: 1; transform: scale(1); }
		50% { opacity: .5; transform: scale(1.2); }
	}
	.p-name {
		font-size: 1.25rem;
		font-weight: 750;
		color: #1b4332;
		margin: 0;
	}
	.p-experience {
		display: flex;
		align-items: center;
		gap: .3rem;
		font-size: var(--text-xs);
		color: #6c757d;
	}
	.p-bio {
		font-size: var(--text-sm);
		color: #495057;
		line-height: 1.55;
		margin: 0;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.p-specialties {
		display: flex;
		flex-wrap: wrap;
		gap: .4rem;
	}
	.specialty-pill {
		font-size: var(--text-xs);
		font-weight: 600;
		color: #1b4332;
		background: #e8f4ec;
		padding: .25rem .65rem;
		border-radius: 6px;
	}
	.p-card-footer {
		margin-top: auto;
		padding-top: var(--space-3);
		border-top: 1px solid rgba(45, 106, 79, 0.1);
	}
	.btn-consult-card {
		display: inline-flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: .6rem .9rem;
		background: #2d6a4f;
		color: #ffffff;
		border-radius: 10px;
		font-size: var(--text-sm);
		font-weight: 700;
		text-decoration: none;
		transition: background .15s ease;
	}
	.btn-consult-card:hover {
		background: #1b4332;
	}
	.directory-jump-box {
		margin-top: var(--space-6);
		padding: var(--space-5);
		background: #ffffff;
		border: 1px dashed rgba(45, 106, 79, 0.3);
		border-radius: 16px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		flex-wrap: wrap;
	}
	.directory-jump-box p {
		margin: 0;
		font-size: var(--text-base);
		color: #2d3748;
		font-weight: 600;
	}
	.btn-explore-directory {
		display: inline-flex;
		align-items: center;
		gap: .5rem;
		background: #2d6a4f;
		color: #ffffff;
		padding: .65rem 1.25rem;
		border-radius: 10px;
		font-weight: 700;
		font-size: var(--text-sm);
		text-decoration: none;
		transition: background .15s ease;
	}
	.btn-explore-directory:hover {
		background: #1b4332;
	}
	.empty-practitioners-box {
		text-align: center;
		padding: var(--space-7) var(--space-4);
		background: #ffffff;
		border-radius: 16px;
		color: #52796f;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-4);
	}

	/* ── Pillars Section (Evidence & Nature) ─────────────────────────── */
	.pillars-section {
		padding: var(--space-7) 0;
		background: #ffffff;
		border-top: 1px solid #e9ecef;
		border-bottom: 1px solid #e9ecef;
	}
	.pillars-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
		gap: var(--space-5);
	}
	.pillar-box {
		background: #fbfdfb;
		border: 1px solid rgba(45, 106, 79, 0.15);
		border-radius: 16px;
		padding: var(--space-5);
		display: flex;
		flex-direction: column;
		gap: .7rem;
		transition: transform .2s var(--ease);
	}
	.pillar-box:hover {
		transform: translateY(-2px);
		border-color: #52b788;
	}
	.pillar-icon-wrap {
		width: 2.8rem;
		height: 2.8rem;
		border-radius: 12px;
		background: #e8f4ec;
		color: #2d6a4f;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.p-ico {
		width: 1.4rem;
		height: 1.4rem;
	}
	.pillar-box h3 {
		font-size: var(--text-lg);
		font-weight: 750;
		color: #1b4332;
		margin: 0;
	}
	.pillar-box p {
		font-size: var(--text-sm);
		color: #4a5568;
		line-height: 1.55;
		margin: 0;
	}

	/* ── Client Testimonial / Story Section ──────────────────────────── */
	.commitment-section {
		padding: var(--space-7) 0;
		background: #f4f8f4;
		border-bottom: 1px solid rgba(45, 106, 79, 0.12);
	}
	.commitment-inner {
		max-width: 44rem;
		margin: 0 auto;
		text-align: center;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-4);
	}
	.quote-mark {
		font-size: 4rem;
		line-height: 1;
		font-family: Georgia, serif;
		color: #52b788;
	}
	.commitment-inner blockquote {
		margin: 0;
		font-size: clamp(1.15rem, 2vw, 1.35rem);
		line-height: 1.6;
		color: #1b4332;
		font-style: italic;
		font-weight: 550;
	}
	.client-author {
		display: flex;
		flex-direction: column;
		gap: .15rem;
		font-size: var(--text-sm);
	}
	.client-author strong {
		color: #1b4332;
	}
	.client-author span {
		color: #52796f;
	}

	/* ── Closing CTA Band (100% Client Focused) ──────────────────────── */
	.cta-nature-band {
		position: relative;
		background: linear-gradient(145deg, #132a1f 0%, #1b4332 60%, #0d2218 100%);
		color: #ffffff;
		padding: var(--space-7) 0;
		overflow: hidden;
		text-align: center;
	}
	.cta-band-content {
		position: relative;
		z-index: 2;
		max-width: 42rem;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-3);
	}
	.cta-band-content h2 {
		font-size: clamp(2rem, 3.4vw, 2.6rem);
		font-weight: 800;
		margin: 0;
		color: #ffffff;
		line-height: 1.15;
	}
	.cta-band-content p {
		font-size: var(--text-lg);
		color: #d8f3dc;
		margin: 0;
		line-height: 1.5;
	}
	.cta-band-buttons {
		display: flex;
		gap: var(--space-4);
		flex-wrap: wrap;
		justify-content: center;
		margin-top: var(--space-4);
	}
	.btn-cta-main {
		display: inline-flex;
		align-items: center;
		gap: .5rem;
		background: #52b788;
		color: #081c15;
		padding: .8rem 1.8rem;
		border-radius: 12px;
		font-weight: 800;
		font-size: var(--text-base);
		text-decoration: none;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
		transition: all .2s var(--ease);
	}
	.btn-cta-main:hover {
		background: #74c69d;
		transform: translateY(-2px);
	}
	.btn-cta-sub {
		display: inline-flex;
		align-items: center;
		background: rgba(255, 255, 255, 0.08);
		color: #ffffff;
		padding: .8rem 1.5rem;
		border-radius: 12px;
		font-weight: 650;
		font-size: var(--text-base);
		text-decoration: none;
		border: 1px solid rgba(255, 255, 255, 0.25);
		transition: all .2s var(--ease);
	}
	.btn-cta-sub:hover {
		background: rgba(255, 255, 255, 0.16);
	}

	/* ── Responsive Adaptations ──────────────────────────────────────── */
	@media (max-width: 960px) {
		.hero-container {
			grid-template-columns: 1fr;
			gap: var(--space-6);
		}
		.hero-visual {
			order: -1;
		}
	}
	@media (max-width: 640px) {
		.hero-section {
			padding: var(--space-5) 0 var(--space-6);
		}
		.hero-actions {
			flex-direction: column;
			align-items: stretch;
		}
		.btn-nature-primary, .btn-nature-secondary {
			justify-content: center;
		}
		.directory-jump-box {
			flex-direction: column;
			align-items: stretch;
		}
		.btn-explore-directory {
			justify-content: center;
		}
		.cta-band-buttons {
			flex-direction: column;
			align-items: stretch;
			width: 100%;
		}
		.btn-cta-main, .btn-cta-sub {
			justify-content: center;
		}
	}
</style>
