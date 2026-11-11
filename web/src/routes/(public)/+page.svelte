<script lang="ts">
	import { onMount } from 'svelte';
	import { PUBLIC_SITE_URL } from '$env/static/public';
	import Seo from '$lib/components/Seo.svelte';
	import { jsonLdScript } from '$lib/seo';
	import { goToSection, consumePendingScroll } from '$lib/scrollToSection';
	import Icon from '$lib/components/Icon.svelte';

	// Same-page section links, kept as JS scroll (not #hash hrefs) for
	// consistency with the nav/footer — see $lib/scrollToSection. On this
	// page the path is always '/', so this just scrolls in place.
	function nav(id: string) {
		goToSection(id, '/');
	}

	onMount(consumePendingScroll);

	// Back-to-top floating button: only worth showing once the visitor has
	// actually scrolled past the hero.
	let showBackToTop = $state(false);
	onMount(() => {
		const onScroll = () => { showBackToTop = window.scrollY > 600; };
		onScroll();
		window.addEventListener('scroll', onScroll, { passive: true });
		return () => window.removeEventListener('scroll', onScroll);
	});

	// Responsive images: the hero (2576x1449 source) and the three portraits
	// are the only large assets on the page, generated at a few widths as
	// both WebP and JPEG (scripts/ or build-time tooling isn't wired up for
	// this yet, so these were pre-generated once into static/images/fhc —
	// see FHC-HOMEPAGE-SPEC.md). srcset/sizes already adapt to device
	// viewport+DPR natively; `connectionAware` below additionally forces the
	// smallest variant under Save-Data or a 2G-class connection, which
	// srcset alone doesn't account for.
	function srcset(base: string, widths: number[], ext: 'jpg' | 'webp') {
		return widths.map((w) => `/images/fhc/${base}-${w}w.${ext} ${w}w`).join(', ');
	}
	const heroWidths = [480, 800, 1200, 1600];
	const portraitWidths = [320, 480, 800];

	let dataSaver = $state(false);
	onMount(() => {
		const conn = (navigator as any).connection;
		dataSaver = !!conn && (conn.saveData || ['slow-2g', '2g'].includes(conn.effectiveType));
	});

	// SEO/OG description is the hero copy verbatim, not a paraphrase — keeps
	// the search snippet and link-preview text in sync with what the page
	// actually says above the fold.
	const description =
		'Personalised hormone, metabolic, gut and longevity care for women in midlife. Because your biology is unique, your health plan should be too.';

	const team = [
		{
			img: 'portrait-alex-ginsburg',
			name: 'Alex Ginsburg, MCO, FNLP',
			title: 'Certified Functional Nutritionist'
		},
		{
			img: 'portrait-jana',
			name: 'Jana Baçova, IMH-C',
			title: 'Functional Hormone & Metabolic Health Practitioner'
		},
		{
			img: 'portrait-kreetta-ryodi',
			name: 'Kreetta Ryödi, IMH-C',
			title: 'Functional Hormone & Metabolic Health Practitioner'
		}
	];

	// GEO: named practitioners and real language/specialty facts (all
	// verified against this page's own content) give AI answer engines
	// something concrete to cite — not a guess, not invented copy.
	const orgJsonLd = {
		'@context': 'https://schema.org',
		'@type': 'MedicalBusiness',
		name: 'Functional Health Collaborative',
		url: PUBLIC_SITE_URL,
		description,
		logo: `${PUBLIC_SITE_URL}/favicon.svg`,
		image: `${PUBLIC_SITE_URL}/og-image.png`,
		medicalSpecialty: ['Gynecologic', 'Endocrine'],
		availableService: 'Telehealth',
		areaServed: 'Worldwide',
		availableLanguage: ['English', 'Dutch', 'Slovak', 'French', 'German', 'Italian', 'Finnish'],
		employee: team.map((m) => ({
			'@type': 'Person',
			name: m.name,
			jobTitle: m.title
		}))
	};

	const testingPartners = [
		{
			logo: '/images/fhc/logo-nordic-laboratories.png',
			name: 'Nordic Laboratories',
			desc: 'Gut microbiome, DNA and functional panels'
		},
		{
			logo: '/images/fhc/logo-mira.svg',
			name: 'MIRA',
			desc: 'Home hormone testing'
		},
		{
			logo: '/images/fhc/logo-precision-analytical-dutch.svg',
			name: 'Precision Analytical',
			desc: 'DUTCH sex & adrenal hormone testing'
		}
	];

	const whyUs = [
		{ n: '01', title: 'Root-cause focus', body: 'We dig to the root cause of your symptoms and help you understand your body.' },
		{ n: '02', title: 'Whole-body view', body: 'A functional approach that factors in thyroid, blood sugar, cortisol, cholesterol, your life situation and more.' },
		{ n: '03', title: 'Advanced diagnostics', body: 'Extensive testing, and you choose the depth of personalisation: blood, DNA, sex and adrenal hormones, gut microbiome and more.' },
		{ n: '04', title: 'A plan built for you', body: "Customised to your body's needs: nutrition, lifestyle, stress management and supplements." },
		{ n: '05', title: 'At your pace', body: 'Step-by-step guidance, adjusted to what works for you.' },
		{ n: '06', title: 'Ongoing support', body: 'Regular check-ins, with your plan adjusted as your body responds.' },
		{ n: '07', title: 'Online, wherever you are', body: 'Video consultations plus detailed protocols, handouts and educational videos.' },
		{ n: '08', title: 'Evidence-based', body: 'Thorough and current — we continually keep up with the latest research.' }
	];

	const steps = [
		{ n: 1, title: 'Free intro call', body: 'A free 15-minute introduction call to get to know each other.' },
		{ n: 2, title: 'In-depth intake', body: 'Your symptoms, health goals, medical and family history — and our program recommendation.' },
		{ n: 3, title: 'Education', body: 'Access to our hormone and metabolic health education.' },
		{ n: 4, title: 'Metabolic insights', body: 'Personalised metabolic health recommendations based on your CGM (continuous glucose monitor) data.' },
		{ n: 5, title: 'Results & protocol', body: 'Your advanced test results explained, with a personalised protocol.' },
		{ n: 6, title: 'Follow-up sessions', body: 'Bi-weekly or monthly follow-ups, depending on what you need.' },
		{ n: 7, title: 'Re-testing', body: 'Re-testing where required, to track your progress.' },
		{ n: 8, title: 'Wrap-up', body: 'A closing session with recommendations for the road ahead.' }
	];

	const includedAll = [
		'Free 15-min intro call',
		'Monthly consultation',
		'Hormone health foundations',
		'Personalised metabolic health program',
		'Blood test results analysis & recommendations',
		'Personalised nutrition, lifestyle & supplement recommendations',
		'Hormonal support recommendations to discuss with your doctor'
	];

	const programs = [
		{
			name: 'Foundational Health',
			tagline: 'Hormone & metabolic foundations',
			price: '€150',
			intake: '+ €295 one-time intake',
			consult: '45-min monthly consultation',
			included: includedAll,
			addons: [] as { label: string; price: string }[],
			note: 'No functional or DNA tests — a strong foundation built on your blood work and symptoms.',
			cta: 'Start Foundational Health',
			highlight: false
		},
		{
			name: 'Complete',
			tagline: 'Add functional gut & hormone testing',
			price: '€200',
			intake: '+ €295 one-time intake',
			consult: '45-min monthly consultation',
			included: includedAll,
			addons: [
				{ label: 'GI-MAP gut microbiome test', price: '€530' },
				{ label: 'DUTCH Plus hormone test', price: '€430' }
			],
			note: null,
			cta: 'Start Complete',
			highlight: false
		},
		{
			name: 'Premium Longevity',
			tagline: 'Functional + DNA testing for longevity',
			price: '€245',
			intake: '+ €295 one-time intake',
			consult: '60-min monthly consultation',
			included: includedAll,
			addons: [
				{ label: 'GI-MAP gut microbiome test', price: '€530' },
				{ label: 'DUTCH Plus hormone test', price: '€430' },
				{ label: '1 DNA test', price: '€220' },
				{ label: '2 DNA tests', price: '€330' },
				{ label: '3 DNA tests', price: '€380' }
			],
			note: null,
			cta: 'Start Premium Longevity',
			highlight: true
		}
	];

	// TODO (handoff README "still to be supplied"): real client testimonials.
	// Ship the literal placeholder rather than inventing quotes.
	const testimonialPlaceholder = {
		quote: 'CLIENT TESTIMONIAL — 2–3 sentences about her experience and results',
		name: '[First name]',
		meta: '[age / country]'
	};
</script>

<Seo
	title="Functional Health Collaborative | Personalised Perimenopause and Menopause Care"
	{description}
	path="/"
/>
<svelte:head>{@html jsonLdScript(orgJsonLd)}</svelte:head>

<!-- HERO -->
<section id="top" class="hero">
	<div class="container hero-inner">
		<div class="hero-copy">
			<p class="label">Perimenopause &amp; menopause care · Online</p>
			<h1>Personalised hormone, metabolic, gut and longevity care for women in midlife.</h1>
			<p class="sub">Because your biology is unique, your health plan should be too.</p>
			<div class="hero-actions">
				<a href="/" class="btn-primary" onclick={(e) => { e.preventDefault(); nav('book'); }}>Book your free 15-min intro call</a>
				<a href="/" class="btn-secondary" onclick={(e) => { e.preventDefault(); nav('programs'); }}>View programs</a>
			</div>
		</div>
		<div class="hero-photo">
			<!-- Always native srcset/sizes here (no JS branching): the browser
			     starts fetching this eager, above-the-fold image before
			     hydration runs, so a post-mount data-saver swap would just
			     race it into a second request instead of preventing one. -->
			<picture>
				<source type="image/webp" srcset={srcset('hero-group', heroWidths, 'webp')} sizes="(max-width: 760px) 100vw, 50vw" />
				<img
					src="/images/fhc/hero-group-1200w.jpg"
					srcset={srcset('hero-group', heroWidths, 'jpg')}
					sizes="(max-width: 760px) 100vw, 50vw"
					alt="Women's health experts of Functional Health Collaborative"
					fetchpriority="high"
					decoding="async"
				/>
			</picture>
		</div>
	</div>
</section>

<!-- OUR APPROACH -->
<section id="approach" class="section">
	<div class="container approach-grid">
		<div class="approach-head">
			<p class="label">Our approach</p>
			<h2>Science-based care for the whole of you</h2>
		</div>
		<div class="approach-body">
			<p>
				We are a telehealth practice specialising in individualised hormone, gut and metabolic
				health care for women navigating perimenopause and menopause. Our protocols are rooted
				in science and functional medicine, giving you an evidence-based approach that covers
				every system in your body.
			</p>
		</div>
	</div>
</section>

<!-- WHAT WE SOLVE FOR -->
<section class="section">
	<div class="container">
		<div class="solve-panel">
			<div class="solve-stat">
				<p class="stat-number">100+</p>
				<p class="stat-caption">possible symptoms linked to hormonal shifts in midlife</p>
			</div>
			<div class="solve-copy">
				<h2>What we solve for</h2>
				<p>
					Hormonal shifts affect every system in the body and can show up as more than 100
					different symptoms, touching women's wellbeing in every part of their lives. Our goal
					is to help you understand your unique physiology — and to give you the guidance and
					tools to reach your health goals, supporting your wellbeing today and in the future.
				</p>
			</div>
		</div>
	</div>
</section>

<!-- WHO WE ARE -->
<section id="about" class="section section-grey">
	<div class="container who-grid">
		<div class="team-portraits">
			{#each team as member (member.name)}
				<figure>
					{#if dataSaver}
						<img src="/images/fhc/{member.img}-320w.jpg" alt="Portrait of {member.name}" loading="lazy" decoding="async" />
					{:else}
						<picture>
							<source type="image/webp" srcset={srcset(member.img, portraitWidths, 'webp')} sizes="(max-width: 480px) 90vw, (max-width: 900px) 45vw, 300px" />
							<img
								src="/images/fhc/{member.img}-480w.jpg"
								srcset={srcset(member.img, portraitWidths, 'jpg')}
								sizes="(max-width: 480px) 90vw, (max-width: 900px) 45vw, 300px"
								alt="Portrait of {member.name}"
								loading="lazy"
								decoding="async"
							/>
						</picture>
					{/if}
					<figcaption>
						<span class="member-name">{member.name}</span>
						<span class="member-title">{member.title}</span>
					</figcaption>
				</figure>
			{/each}
		</div>
		<div class="who-copy">
			<p class="label">Who we are</p>
			<h2>A team of women's health experts</h2>
			<p>
				We specialise in hormone, metabolic and gut health. Alongside holistic Eastern health
				training, our education combines evidence-based approaches in gut health, nutrition,
				metabolic and hormone health.
			</p>
			<p>
				We partner with leading advanced testing laboratories and build truly personalised
				health plans based on the latest scientific research.
			</p>
			<!-- TODO: "Meet the team" links to the future /about page with full team profiles -->
			<a href="/" class="link-arrow" onclick={(e) => { e.preventDefault(); nav('about'); }}>Meet the team →</a>
		</div>
		<div class="testing-partners">
			<p class="partners-label">Our testing partners</p>
			<div class="partners-list">
				{#each testingPartners as tp (tp.name)}
					<div class="partner-row">
						<img src={tp.logo} alt="{tp.name} logo" loading="lazy" decoding="async" />
						<div>
							<p class="partner-name">{tp.name}</p>
							<p class="partner-desc">{tp.desc}</p>
						</div>
					</div>
				{/each}
			</div>
		</div>
	</div>
</section>

<!-- WHY WOMEN CHOOSE US -->
<section class="section section-burgundy">
	<div class="container">
		<div class="section-head">
			<p class="label label-copper">Why women choose us</p>
			<h2 class="on-burgundy">Thorough, personal and on your side</h2>
		</div>
		<div class="why-grid">
			{#each whyUs as w (w.n)}
				<div class="why-card">
					<p class="why-num">{w.n}</p>
					<h3>{w.title}</h3>
					<p>{w.body}</p>
				</div>
			{/each}
		</div>
	</div>
</section>

<!-- HOW TO WORK WITH US -->
<section id="how" class="section section-grey">
	<div class="container">
		<div class="section-head">
			<p class="label">How to work with us</p>
			<h2>Your journey, step by step</h2>
		</div>
		<ol class="steps-grid">
			{#each steps as s (s.n)}
				<li class="step-card">
					<span class="step-badge" class:first={s.n === 1}>{s.n}</span>
					<h3>{s.title}</h3>
					<p>{s.body}</p>
				</li>
			{/each}
		</ol>
	</div>
</section>

<!-- PROGRAMS -->
<section id="programs" class="section">
	<div class="container">
		<div class="section-head">
			<p class="label">Programs</p>
			<h2>Choose your program</h2>
		</div>
		<div class="programs-grid">
			{#each programs as p (p.name)}
				<div class="program-card" class:highlight={p.highlight}>
					<div class="program-head">
						<div class="program-title-row">
							<h3>{p.name}</h3>
							{#if p.highlight}<span class="badge">Most complete</span>{/if}
						</div>
						<p class="program-tagline">{p.tagline}</p>
					</div>
					<div class="program-price">
						<p><span class="price">{p.price}</span><span class="per">/ month</span></p>
						<p class="intake">{p.intake}</p>
					</div>
					<ul class="program-included">
						{#each p.included as item (item)}
							<li>
								<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--pub-burgundy)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
								<span>{item}</span>
							</li>
						{/each}
					</ul>
					<div class="program-footer">
						{#if p.addons.length}
							<p class="addons-label">Optional add-on tests · paid separately</p>
							<ul class="addons-list">
								{#each p.addons as a (a.label)}
									<li>
										<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--pub-copper)" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M12 6v12M6 12h12" /></svg>
										<span class="grow">{a.label}</span>
										<span class="addon-price">{a.price}</span>
									</li>
								{/each}
							</ul>
						{:else if p.note}
							<p class="program-note">{p.note}</p>
						{/if}
					</div>
					<a href="/" class="program-cta" class:filled={p.highlight} onclick={(e) => { e.preventDefault(); nav('book'); }}>{p.cta}</a>
				</div>
			{/each}
		</div>
		<div class="programs-aside">
			<p><strong>How the programs differ:</strong> Complete and Premium Longevity differ in how many functional and DNA tests you choose to include. Test costs are paid separately; the higher monthly fee covers the extra time for analysing your results and building your recommendations.</p>
			<p><strong>Not included but required:</strong> a continuous glucose monitor (CGM) and a comprehensive blood panel. Supplements are also not included in the price.</p>
		</div>
	</div>
</section>

<!-- TESTIMONIALS -->
<section class="section section-grey">
	<div class="container">
		<div class="section-head">
			<p class="label">Client stories</p>
			<h2>What women say</h2>
		</div>
		<!-- TODO (handoff README "still to be supplied"): 3 real testimonials -->
		<div class="testimonials-grid">
			{#each Array(3) as _, i (i)}
				<figure class="testimonial-card">
					<svg width="32" height="24" viewBox="0 0 32 24" aria-hidden="true"><path d="M0 24V14C0 6 4 1 12 0l1 4C8 5 6 8 6 12h6v12H0zm18 0V14c0-8 4-13 12-14l1 4c-5 1-7 4-7 8h6v12H18z" fill="var(--pub-copper)" /></svg>
					<blockquote>{testimonialPlaceholder.quote}</blockquote>
					<figcaption><strong>{testimonialPlaceholder.name}</strong>, {testimonialPlaceholder.meta}</figcaption>
				</figure>
			{/each}
		</div>
	</div>
</section>

<!-- READY TO START -->
<section id="book" class="section">
	<div class="container">
		<div class="cta-panel">
			<h2>Ready to start?</h2>
			<p>Schedule your free 15-minute introduction call. We'll listen to your story and help you find the program that fits.</p>
			<!-- TODO (handoff README "still to be supplied"): real booking link -->
			<a href="/" class="cta-button" onclick={(e) => { e.preventDefault(); nav('book'); }}>Book your free intro call</a>
			<p class="cta-footnote">100% online · Available in English, Dutch, Slovak, French, German, Italian and Finnish</p>
		</div>
	</div>
</section>

{#if showBackToTop}
	<button class="back-to-top" onclick={() => nav('top')} aria-label="Back to top">
		<Icon name="chevron-up" size={20} />
	</button>
{/if}

<style>
	:global(.public-shell) :global(section) {
		scroll-margin-top: 4rem;
	}

	.label {
		margin: 0 0 .5rem;
		font-size: .85rem;
		font-weight: 600;
		letter-spacing: .12em;
		text-transform: uppercase;
		color: var(--pub-burgundy);
	}
	.label-copper { color: var(--pub-copper); }

	h1, h2, h3 {
		margin: 0;
		font-weight: 600;
		letter-spacing: -.015em;
		color: var(--pub-navy);
	}
	h1 { font-size: clamp(2.25rem, 4.4vw, 3.4rem); line-height: 1.06; letter-spacing: -.02em; }
	h2 { font-size: clamp(1.9rem, 3.4vw, 2.6rem); line-height: 1.12; }
	h3 { font-size: 1.2rem; }

	.section { padding: var(--space-7) 0; background: var(--pub-bg); }
	.section-grey { background: var(--pub-warm-grey); }
	.section-burgundy { background: var(--pub-burgundy); }
	.section-head { max-width: 42rem; margin-bottom: var(--space-6); display: flex; flex-direction: column; gap: .5rem; }
	.on-burgundy { color: #ffffff; }

	/* Hero */
	.hero { background: var(--pub-header-bg); }
	.hero-inner {
		padding: 5.5rem 0 6rem;
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-7);
		align-items: stretch;
	}
	.hero-copy { flex: 1 1 26rem; display: flex; flex-direction: column; gap: var(--space-4); justify-content: center; }
	.hero-copy .sub { margin: 0; font-size: 1.3rem; line-height: 1.5; color: var(--pub-text); max-width: 34rem; }
	.hero-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: .5rem; }
	.hero-photo { flex: 1 1 32rem; min-height: 20rem; position: relative; }
	.hero-photo img {
		position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;
		border-radius: 28px; border: 3px solid var(--pub-copper); box-shadow: 0 8px 28px rgba(0,0,76,0.12);
	}

	.btn-primary, .btn-secondary, .cta-button, .program-cta, .link-arrow {
		font-weight: 600;
	}
	.btn-primary, .btn-secondary {
		display: inline-flex; align-items: center; justify-content: center; min-height: 52px; padding: 0 1.75rem;
		border-radius: 999px; font-size: 1.0625rem; text-decoration: none;
		transition: background var(--duration-fast), border-color var(--duration-fast), transform var(--duration-fast);
	}
	.btn-primary { background: var(--pub-copper); color: var(--pub-navy); }
	.btn-primary:hover { background: #c98540; transform: translateY(-1px); }
	.btn-secondary { border: 1.5px solid var(--pub-navy); color: var(--pub-navy); }
	.btn-secondary:hover { background: rgba(0, 0, 76, .06); transform: translateY(-1px); }

	/* Our approach */
	.approach-grid { display: flex; flex-wrap: wrap; gap: var(--space-6); padding: var(--space-6) 0; }
	.approach-head { flex: 1 1 18rem; }
	.approach-body { flex: 999 1 32rem; }
	.approach-body p { margin: 0; font-size: 1.25rem; line-height: 1.6; }

	/* What we solve for */
	.solve-panel {
		background: var(--pub-burgundy); border-radius: 28px; padding: clamp(2rem, 5vw, 4rem);
		display: flex; flex-wrap: wrap; gap: var(--space-6); align-items: center;
	}
	.solve-stat { flex: 1 1 16rem; display: flex; flex-direction: column; gap: .5rem; }
	.stat-number { margin: 0; font-family: var(--pub-font-heading); font-weight: 700; font-size: clamp(4rem, 8vw, 6.5rem); line-height: 1; color: var(--pub-copper); }
	.stat-caption { margin: 0; font-size: 1.1rem; color: var(--pub-warm-grey); }
	.solve-copy { flex: 999 1 30rem; display: flex; flex-direction: column; gap: var(--space-4); }
	.solve-copy h2 { color: #ffffff; }
	.solve-copy p { margin: 0; font-size: 1.1rem; line-height: 1.65; color: var(--pub-warm-grey); }

	/* Who we are */
	.who-grid { display: grid; grid-template-columns: 1fr; gap: var(--space-7); padding: var(--space-6) 0; }
	.team-portraits { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: var(--space-5); }
	.team-portraits figure { margin: 0; display: flex; flex-direction: column; gap: .85rem; }
	.team-portraits img { display: block; width: 100%; aspect-ratio: 4 / 5; object-fit: cover; border-radius: 24px; }
	.member-name { display: block; font-family: var(--pub-font-heading); font-weight: 600; font-size: 1.3rem; color: var(--pub-navy); }
	.member-title { display: block; font-size: .9rem; color: var(--pub-text-muted); }
	.who-copy { display: flex; flex-direction: column; gap: var(--space-4); max-width: 42rem; }
	.who-copy p { margin: 0; font-size: 1.1rem; line-height: 1.65; }
	.link-arrow { display: inline-flex; align-items: center; min-height: 2.75rem; text-decoration: none; color: var(--pub-burgundy); }
	.testing-partners { background: var(--pub-card-bg); border-radius: 24px; padding: var(--space-6); display: flex; flex-direction: column; gap: var(--space-4); max-width: 26rem; }
	.partners-label { margin: 0; font-size: .85rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; color: var(--pub-text-muted); }
	.partners-list { display: flex; flex-direction: column; }
	.partner-row { padding: 1rem 0; border-bottom: 1px solid var(--pub-warm-grey); display: flex; align-items: center; gap: var(--space-4); }
	.partner-row:last-child { border-bottom: none; }
	.partner-row img { width: 6.5rem; height: 3.5rem; flex-shrink: 0; object-fit: contain; object-position: center center; }
	.partner-name { margin: 0; font-family: var(--pub-font-heading); font-weight: 600; font-size: 1.25rem; color: var(--pub-navy); }
	.partner-desc { margin: 0; font-size: .9rem; color: var(--pub-text-muted); }

	/* Why women choose us */
	.why-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(15.5rem, 1fr)); gap: var(--space-5); }
	.why-card { border: 1px solid rgba(255,255,255,0.22); background: rgba(255,255,255,0.06); border-radius: 20px; padding: var(--space-5); display: flex; flex-direction: column; gap: .6rem; }
	.why-num { margin: 0; font-family: var(--pub-font-heading); font-weight: 700; font-size: .9rem; color: var(--pub-copper); }
	.why-card h3 { color: #ffffff; font-size: 1.2rem; line-height: 1.3; }
	.why-card p { margin: 0; font-size: 1rem; color: #f3e6ea; }

	/* How to work with us */
	.steps-grid { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: var(--space-5); }
	.step-card { background: var(--pub-card-bg); border-radius: 20px; padding: var(--space-5); display: flex; flex-direction: column; gap: .75rem; }
	.step-badge { display: inline-flex; align-items: center; justify-content: center; width: 2.5rem; height: 2.5rem; border-radius: 999px; background: var(--pub-navy); color: #ffffff; font-weight: 700; }
	.step-badge.first { background: var(--pub-copper); color: var(--pub-navy); }
	.step-card p { margin: 0; font-size: 1rem; }

	/* Programs */
	.programs-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(18.5rem, 1fr)); gap: var(--space-5); align-items: stretch; margin-bottom: var(--space-5); }
	.program-card { border: 1px solid var(--pub-warm-grey); border-radius: 24px; padding: 2.25rem 2rem; display: flex; flex-direction: column; gap: var(--space-5); background: var(--pub-card-bg); }
	.program-card.highlight { border: 2px solid var(--pub-copper); background: #fbf5ef; }
	.program-title-row { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .5rem; }
	.program-title-row h3 { font-size: 1.6rem; }
	.badge { padding: .25rem .75rem; border-radius: 999px; background: var(--pub-copper); color: var(--pub-navy); font-size: .8rem; font-weight: 600; }
	.program-tagline { margin: .3rem 0 0; font-size: .9rem; color: var(--pub-text-muted); }
	.program-price p { margin: 0; }
	.price { font-family: var(--pub-font-heading); font-weight: 700; font-size: 3rem; color: var(--pub-navy); line-height: 1; }
	.per { font-size: .9rem; color: var(--pub-text-muted); margin-left: .5rem; }
	.intake { font-size: .9rem; color: var(--pub-text-muted); margin-top: .3rem !important; }
	.program-included { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .75rem; font-size: 1rem; }
	.program-included li { display: flex; gap: .6rem; align-items: flex-start; }
	.program-included svg { flex-shrink: 0; margin-top: .2rem; }
	.program-footer { flex-grow: 1; border-top: 1px solid var(--pub-warm-grey); padding-top: 1.25rem; display: flex; flex-direction: column; gap: .75rem; }
	.addons-label { margin: 0; font-size: .8rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--pub-text-muted); }
	.addons-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .6rem; font-size: 1rem; }
	.addons-list li { display: flex; gap: .6rem; align-items: flex-start; }
	.addons-list .grow { flex-grow: 1; }
	.addon-price { font-weight: 600; color: var(--pub-navy); white-space: nowrap; }
	.program-note { margin: 0; font-size: .9rem; color: var(--pub-text-muted); }
	.program-cta {
		display: flex; align-items: center; justify-content: center; min-height: 52px; border-radius: 999px;
		border: 1.5px solid var(--pub-navy); color: var(--pub-navy); text-decoration: none;
		transition: background var(--duration-fast), transform var(--duration-fast);
	}
	.program-cta:hover { background: rgba(0, 0, 76, .06); transform: translateY(-1px); }
	.program-cta.filled { background: var(--pub-copper); border: none; }
	.program-cta.filled:hover { background: #c98540; }
	.programs-aside { background: var(--pub-warm-grey); border-radius: 20px; padding: 1.5rem 1.75rem; display: flex; flex-direction: column; gap: .6rem; font-size: 1rem; }
	.programs-aside p { margin: 0; }
	.programs-aside strong { color: var(--pub-navy); }

	/* Testimonials */
	.testimonials-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(17.5rem, 1fr)); gap: var(--space-5); }
	.testimonial-card { margin: 0; background: var(--pub-card-bg); border-radius: 24px; padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-4); }
	.testimonial-card blockquote { margin: 0; font-size: 1.1rem; line-height: 1.6; color: var(--pub-navy); flex-grow: 1; font-style: italic; }
	.testimonial-card figcaption { font-size: .9rem; color: var(--pub-text-muted); }
	.testimonial-card figcaption strong { color: var(--pub-navy); }

	/* Ready to start */
	.cta-panel {
		background: var(--pub-burgundy); border-radius: 28px; padding: clamp(2.5rem, 6vw, 4.5rem);
		display: flex; flex-direction: column; align-items: center; text-align: center; gap: var(--space-4);
	}
	.cta-panel h2 { color: #ffffff; max-width: 46rem; }
	.cta-panel p { margin: 0; font-size: 1.2rem; color: var(--pub-warm-grey); max-width: 38rem; }
	.cta-button {
		display: inline-flex; align-items: center; justify-content: center; min-height: 56px; padding: 0 2rem;
		border-radius: 999px; background: #ffffff; color: var(--pub-navy); text-decoration: none;
		font-weight: 700; font-size: 1.125rem; margin-top: .25rem;
		transition: background var(--duration-fast), transform var(--duration-fast);
	}
	.cta-button:hover { background: #f0ede6; transform: translateY(-1px); }
	.cta-footnote { font-size: .9rem; color: var(--pub-warm-grey); }

	.back-to-top {
		position: fixed; right: 1.5rem; bottom: 1.5rem; z-index: 30;
		display: flex; align-items: center; justify-content: center;
		width: 2.75rem; height: 2.75rem; border-radius: 999px; border: none;
		background: var(--pub-navy); color: #ffffff; cursor: pointer;
		box-shadow: 0 4px 16px rgba(0, 0, 76, .25);
		transition: background var(--duration-fast), transform var(--duration-fast);
	}
	.back-to-top:hover { background: var(--pub-burgundy); transform: translateY(-2px); }

	@media (max-width: 760px) {
		.back-to-top { right: 1rem; bottom: 1rem; width: 2.5rem; height: 2.5rem; }
		.hero-inner { flex-direction: column; }
		.who-grid { gap: var(--space-5); }
		.testing-partners { max-width: none; }
	}
</style>
