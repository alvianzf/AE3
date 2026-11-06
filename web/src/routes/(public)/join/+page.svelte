<script lang="ts">
	import { goto } from '$app/navigation';
	import { PUBLIC_API_BASE } from '$env/static/public';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Sprig from '$lib/components/Sprig.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import LeafField from '$lib/components/LeafField.svelte';

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

	function scrollTo(id: string) {
		const el = document.getElementById(id);
		if (el) el.scrollIntoView({ behavior: 'smooth' });
	}

	const corePillars = [
		{
			icon: 'users',
			title: 'Clients See You, Never a Bot',
			desc: 'Your clients receive compassionate, attentive human care from you. The clinical intelligence engine runs strictly behind the scenes as your personal copilot.'
		},
		{
			icon: 'check',
			title: 'No More Missing Information',
			desc: 'Intake questionnaires, biomarker trends, and historical timelines are automatically structured into one cohesive view. Never miss an overlooked lab or symptom trigger.'
		},
		{
			icon: 'book',
			title: 'Curated Clinical Evidence Base',
			desc: 'Upload your own trusted medical textbooks, diagnostic guides, and peer-reviewed journals. The assistant draws exclusively from what you verify — zero open-web hallucinations.'
		},
		{
			icon: 'shield',
			title: 'Strict Patient Data Isolation',
			desc: 'Every practitioner workspace is completely isolated. Your client records, notes, and lab data are encrypted and never pooled, sold, or shared across practitioners.'
		}
	];

	const guidanceSteps = [
		{
			num: '01',
			title: 'Submit Clinical Application',
			desc: 'Complete the practitioner profile below with your background, clinical specialties, and professional experience. Takes less than 3 minutes.'
		},
		{
			num: '02',
			title: 'Credential Verification',
			desc: 'Our clinical advisory team reviews your credentials (licensed physicians, NDs, NPs, PAs, DCs, CNSs, or IFMCP certified clinicians) within 24–48 hours.'
		},
		{
			num: '03',
			title: 'Activate Your Clinical Workspace',
			desc: 'Once approved, log in to configure your intake questionnaires, upload your clinical reference texts, set your consultation fees, and publish your directory profile.'
		}
	];

	const whoShouldApply = [
		'Licensed Physicians (MD, DO) practicing integrative or functional medicine',
		'Naturopathic Doctors (ND, NMD) with accredited clinical training',
		'Nurse Practitioners (NP, APRN) & Physician Associates (PA-C)',
		'Chiropractors (DC) with functional medicine specialization',
		'Certified Nutrition Specialists (CNS) & Registered Dietitians with functional focus',
		'IFMCP certified or credentialed functional health practitioners'
	];
</script>

<Seo
	title="For Practitioners — Practice Augmented Functional Medicine"
	description="Bring your practice onto Functional Health Collab: clinical intelligence that connects patient timelines, synthesizes lab biomarkers, and cites peer-reviewed medical literature so no information is missed."
	path="/join"
/>

<!-- ══ HERO: Botanical Canopy for Practitioners ══ -->
<section class="practitioner-hero">
	<div class="leaf-ambient">
		<LeafField count={22} />
	</div>

	<div class="container hero-inner">
		<div class="badge-pill">
			<span class="logo-mark"><Sprig size={18} /></span>
			<span>For Functional & Integrative Medicine Clinicians</span>
		</div>

		<h1>Practice at your peak. Arrive at every consult deeply informed.</h1>

		<p class="hero-lede">
			Functional Health Collab provides independent practitioners with an augmented clinical workspace.
			Connect complex client intake histories, track biomarker trajectories, and query your curated clinical
			literature in seconds — eliminating missing information so you can focus on transformative care.
		</p>

		<div class="hero-actions">
			<button class="btn-hero-primary" onclick={() => scrollTo('application-form')}>
				<span>Apply to Join Network</span>
				<Icon name="chevron" size={14} />
			</button>
			<button class="btn-hero-secondary" onclick={() => scrollTo('guidance')}>
				<span>Practitioner Guidance</span>
			</button>
		</div>

		<div class="hero-stats">
			<div class="stat-item">
				<strong>100%</strong>
				<span>Human-Client Care</span>
			</div>
			<div class="stat-div"></div>
			<div class="stat-item">
				<strong>0</strong>
				<span>Missing Details</span>
			</div>
			<div class="stat-div"></div>
			<div class="stat-item">
				<strong>Exact</strong>
				<span>Page Citations</span>
			</div>
			<div class="stat-div"></div>
			<div class="stat-item">
				<strong>Private</strong>
				<span>Curated Library</span>
			</div>
		</div>
	</div>
</section>

<!-- ══ CORE VALUE: Augmented Practice Pillars ══ -->
<section class="pillars-section">
	<div class="container">
		<div class="section-header text-center">
			<div class="sub-badge">Clinical Augmentation</div>
			<h2>Why practitioners thrive on Functional Health Collab</h2>
			<p>Traditional functional medicine is burdened with 50-page intake forms, scattered lab PDFs, and late-night PubMed searches. We augment your practice so you see the complete picture instantly.</p>
		</div>

		<div class="pillars-grid">
			{#each corePillars as p (p.title)}
				<div class="pillar-card">
					<div class="pillar-icon">
						<Icon name={p.icon} size={22} />
					</div>
					<h3>{p.title}</h3>
					<p>{p.desc}</p>
				</div>
			{/each}
		</div>
	</div>
</section>

<!-- ══ WORKSPACE CAPABILITIES ══ -->
<section class="capabilities-section">
	<div class="container">
		<div class="split-layout">
			<div class="split-copy">
				<div class="sub-badge">Practice Toolkit</div>
				<h2>A clinical workspace built for root-cause medicine</h2>
				<p>Everything you need to deliver world-class functional health care without drowning in clinical administration:</p>
				
				<div class="feature-rows">
					<div class="f-row">
						<div class="f-bullet"><Icon name="check" size={16} /></div>
						<div>
							<strong>Interactive Patient Timelines</strong>
							<p>Organize symptoms, medications, triggers, and life events along a visual chronological continuum.</p>
						</div>
					</div>
					<div class="f-row">
						<div class="f-bullet"><Icon name="check" size={16} /></div>
						<div>
							<strong>Biomarker & Lab Synthesis</strong>
							<p>Track conventional and functional reference ranges across Quest, Labcorp, and specialty functional testing over time.</p>
						</div>
					</div>
					<div class="f-row">
						<div class="f-bullet"><Icon name="check" size={16} /></div>
						<div>
							<strong>Grounded Consult Assistant</strong>
							<p>Query potential interactions, lifestyle protocols, and clinical research during case prep with verified source citations.</p>
						</div>
					</div>
					<div class="f-row">
						<div class="f-bullet"><Icon name="check" size={16} /></div>
						<div>
							<strong>Client Questionnaire Engine</strong>
							<p>Deploy comprehensive intake forms that populate directly into patient records, ready for your clinical review.</p>
						</div>
					</div>
				</div>
			</div>

			<div class="split-visual">
				<div class="consult-preview-card">
					<div class="preview-header">
						<span class="dot red"></span>
						<span class="dot yellow"></span>
						<span class="dot green"></span>
						<span class="preview-title">Consult Workspace — Case Preparation</span>
					</div>
					<div class="preview-body">
						<div class="preview-case">
							<span class="case-tag">Patient Presentation</span>
							<p class="case-text">42yo F with refractory fatigue, postprandial bloating, and subclinical TSH elevation (3.8 μIU/mL) with positive anti-TPO antibodies.</p>
						</div>
						<div class="preview-synthesis">
							<div class="synth-badge">
								<Icon name="check" size={13} />
								<span>Grounded Clinical Synthesis</span>
							</div>
							<p class="synth-text">
								Evidence indicates gut mucosal hyperpermeability and molecular mimicry frequently co-occur with autoimmune thyroiditis. Consider comprehensive stool panel and targeted nutritional support.
							</p>
							<div class="citations-row">
								<span class="citation-pill">📚 J. Clin. Endocrinol. (2023) §4.2</span>
								<span class="citation-pill">📖 Textbook of Functional Medicine p. 418</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</section>

<!-- ══ ONBOARDING GUIDANCE SECTION ══ -->
<section id="guidance" class="guidance-section">
	<div class="container">
		<div class="section-header text-center">
			<div class="sub-badge">Practitioner Guidance</div>
			<h2>How onboarding & credential verification works</h2>
			<p>We maintain high clinical standards to ensure patients connect with qualified, ethical practitioners.</p>
		</div>

		<div class="guidance-grid">
			{#each guidanceSteps as s (s.num)}
				<div class="guidance-card">
					<div class="step-num">{s.num}</div>
					<h3>{s.title}</h3>
					<p>{s.desc}</p>
				</div>
			{/each}
		</div>

		<div class="who-box">
			<h3>Who We Welcome into the Practitioner Network:</h3>
			<ul class="who-list">
				{#each whoShouldApply as w (w)}
					<li>
						<Icon name="check" size={15} />
						<span>{w}</span>
					</li>
				{/each}
			</ul>
		</div>
	</div>
</section>

<!-- ══ APPLICATION FORM SECTION ══ -->
<section id="application-form" class="application-section">
	<div class="container form-container">
		<div class="form-card card-panel">
			<div class="ph form-header">
				<div class="form-title-group">
					<span class="logo-mark"><Sprig size={22} /></span>
					<div>
						<h2>Practitioner Application</h2>
						<p class="form-sub">Apply to join our vetted functional health collaborative.</p>
					</div>
				</div>
			</div>

			<form class="pb form-body" onsubmit={submit}>
				<div class="field-grid">
					<TextField label="Full Name (with professional credentials)" bind:value={name} placeholder="e.g. Dr. Sarah Jenkins, ND, IFMCP" required />
					<TextField label="Professional Email Address" type="email" bind:value={email} placeholder="dr.jenkins@clinic.com" required />
				</div>

				<TextField label="Password" type="password" bind:value={password} placeholder="Minimum 8 characters" required hint="Must be at least 8 characters with numbers or symbols" />

				<TextField
					label="Clinical Bio & Practice Philosophy"
					type="textarea"
					bind:value={bio}
					placeholder="Describe your clinical training, experience, philosophy of care, and patient approach. This will be visible on your public directory profile."
				/>

				<TextField
					label="Clinical Specialties (comma-separated)"
					bind:value={specialties}
					placeholder="Microbiome Health, Hashimoto's, SIBO, Chronic Fatigue, Hormonal Balance"
					hint="List 3–6 core clinical focus areas"
				/>

				<div class="field-grid">
					<TextField label="Languages Spoken (comma-separated)" bind:value={languages} placeholder="English, Spanish" />
					<TextField label="Years in Clinical Practice" type="number" bind:value={years} />
				</div>

				<div class="field-grid">
					<TextField label="Standard Consultation Price (USD)" type="number" bind:value={price} hint="Your rate per standard consultation. You retain 100% of client fees." />
					<div class="file-field">
						<label for="photo">Professional Profile Photo</label>
						<input id="photo" type="file" accept="image/*" onchange={(e) => (photo = (e.target as HTMLInputElement).files)} />
						<span class="file-hint">Clear headshot recommended (PNG, JPG)</span>
					</div>
				</div>

				{#if error}
					<div class="error-banner">
						<Icon name="x" size={16} />
						<span>{error}</span>
					</div>
				{/if}

				<div class="form-actions">
					<Button type="submit" loading={submitting}>Submit Practitioner Application</Button>
					<p class="terms-note">
						By applying, you confirm that you hold active clinical credentials in good standing. Applications are reviewed within 1–2 business days.
					</p>
				</div>
			</form>
		</div>
	</div>
</section>

<style>
	/* ── Practitioner Hero ───────────────────────────────────────────── */
	.practitioner-hero {
		position: relative;
		padding: var(--space-7) 0 var(--space-6);
		background: linear-gradient(175deg, #132a1f 0%, #1b4332 55%, #0f2b1d 100%);
		color: #ffffff;
		overflow: hidden;
	}
	.leaf-ambient {
		position: absolute;
		inset: 0;
		pointer-events: none;
		z-index: 1;
		--leaf-color: rgba(116, 198, 157, 0.45);
	}
	.hero-inner {
		position: relative;
		z-index: 2;
		max-width: 52rem;
		margin: 0 auto;
		text-align: center;
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 0 var(--space-5);
	}
	.badge-pill {
		display: inline-flex;
		align-items: center;
		gap: .55rem;
		background: rgba(45, 106, 79, 0.45);
		border: 1px solid rgba(82, 183, 136, 0.4);
		padding: .35rem .95rem;
		border-radius: 999px;
		font-size: var(--text-xs);
		font-weight: 750;
		color: #d8f3dc;
		margin-bottom: var(--space-4);
	}
	.logo-mark {
		display: inline-flex;
		color: #52b788;
	}
	.hero-inner h1 {
		font-size: clamp(2.1rem, 4vw, 3.25rem);
		font-weight: 850;
		line-height: 1.15;
		color: #ffffff;
		letter-spacing: -.025em;
		margin: 0 0 var(--space-4);
	}
	.hero-lede {
		font-size: clamp(1rem, 1.8vw, 1.15rem);
		line-height: 1.65;
		color: #d8f3dc;
		margin: 0 0 var(--space-6);
		max-width: 44rem;
	}
	.hero-actions {
		display: flex;
		gap: var(--space-4);
		justify-content: center;
		flex-wrap: wrap;
		margin-bottom: var(--space-6);
	}
	.btn-hero-primary {
		display: inline-flex;
		align-items: center;
		gap: .5rem;
		background: #52b788;
		color: #0b1f14;
		border: none;
		padding: .75rem 1.4rem;
		border-radius: 10px;
		font-weight: 750;
		font-size: var(--text-sm);
		cursor: pointer;
		box-shadow: 0 6px 18px rgba(82, 183, 136, 0.3);
		transition: all .15s ease;
	}
	.btn-hero-primary:hover {
		background: #74c69d;
		transform: translateY(-1px);
	}
	.btn-hero-secondary {
		display: inline-flex;
		align-items: center;
		background: rgba(255, 255, 255, 0.08);
		color: #ffffff;
		border: 1px solid rgba(255, 255, 255, 0.2);
		padding: .75rem 1.4rem;
		border-radius: 10px;
		font-weight: 700;
		font-size: var(--text-sm);
		cursor: pointer;
		transition: all .15s ease;
	}
	.btn-hero-secondary:hover {
		background: rgba(255, 255, 255, 0.16);
	}
	.hero-stats {
		display: flex;
		align-items: center;
		gap: var(--space-5);
		background: rgba(0, 0, 0, 0.25);
		border: 1px solid rgba(82, 183, 136, 0.25);
		padding: .75rem 1.5rem;
		border-radius: 14px;
		backdrop-filter: blur(10px);
		flex-wrap: wrap;
		justify-content: center;
	}
	.stat-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: .15rem;
	}
	.stat-item strong {
		font-size: 1.15rem;
		color: #52b788;
		font-weight: 800;
	}
	.stat-item span {
		font-size: .75rem;
		color: #d8f3dc;
	}
	.stat-div {
		width: 1px;
		height: 24px;
		background: rgba(82, 183, 136, 0.3);
	}

	/* ── Core Value Section ──────────────────────────────────────────── */
	.pillars-section {
		padding: var(--space-7) 0;
		background: #fbfcf9;
	}
	.section-header {
		max-width: 44rem;
		margin: 0 auto var(--space-6);
	}
	.section-header.text-center {
		text-align: center;
	}
	.sub-badge {
		display: inline-block;
		text-transform: uppercase;
		letter-spacing: .06em;
		font-size: .75rem;
		font-weight: 750;
		color: #2d6a4f;
		background: #e8f4ec;
		padding: .25rem .75rem;
		border-radius: 999px;
		margin-bottom: var(--space-3);
	}
	.section-header h2 {
		font-size: clamp(1.8rem, 3vw, 2.4rem);
		font-weight: 850;
		color: #1b4332;
		letter-spacing: -.02em;
		margin: 0 0 var(--space-3);
	}
	.section-header p {
		color: #52796f;
		font-size: var(--text-base);
		line-height: 1.6;
		margin: 0;
	}
	.pillars-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
		gap: var(--space-5);
	}
	.pillar-card {
		background: #ffffff;
		border: 1px solid rgba(45, 106, 79, 0.14);
		border-radius: 16px;
		padding: var(--space-5);
		box-shadow: 0 4px 16px rgba(27, 67, 50, 0.04);
		transition: transform .2s ease, box-shadow .2s ease;
	}
	.pillar-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 8px 24px rgba(27, 67, 50, 0.08);
	}
	.pillar-icon {
		width: 44px;
		height: 44px;
		border-radius: 12px;
		background: #e8f4ec;
		color: #2d6a4f;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: var(--space-4);
	}
	.pillar-card h3 {
		font-size: var(--text-base);
		font-weight: 800;
		color: #1b4332;
		margin: 0 0 .5rem;
	}
	.pillar-card p {
		font-size: var(--text-sm);
		color: #3e5a4d;
		line-height: 1.55;
		margin: 0;
	}

	/* ── Workspace Capabilities ──────────────────────────────────────── */
	.capabilities-section {
		padding: var(--space-7) 0;
		background: #f4f8f4;
		border-top: 1px solid rgba(45, 106, 79, 0.1);
		border-bottom: 1px solid rgba(45, 106, 79, 0.1);
	}
	.split-layout {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-7);
		align-items: center;
	}
	.split-copy h2 {
		font-size: clamp(1.8rem, 2.8vw, 2.4rem);
		font-weight: 850;
		color: #1b4332;
		letter-spacing: -.02em;
		margin: 0 0 var(--space-3);
	}
	.split-copy > p {
		color: #52796f;
		font-size: var(--text-base);
		line-height: 1.6;
		margin: 0 0 var(--space-5);
	}
	.feature-rows {
		display: grid;
		gap: var(--space-4);
	}
	.f-row {
		display: flex;
		align-items: flex-start;
		gap: .75rem;
	}
	.f-bullet {
		color: #2d6a4f;
		background: #e8f4ec;
		width: 24px;
		height: 24px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		flex: 0 0 auto;
		margin-top: .15rem;
	}
	.f-row strong {
		display: block;
		font-size: var(--text-sm);
		font-weight: 750;
		color: #1b4332;
		margin-bottom: .2rem;
	}
	.f-row p {
		margin: 0;
		font-size: var(--text-xs);
		color: #52796f;
		line-height: 1.5;
	}

	/* ── Preview Card ────────────────────────────────────────────────── */
	.consult-preview-card {
		background: #143023;
		border: 1px solid rgba(82, 183, 136, 0.35);
		border-radius: 16px;
		overflow: hidden;
		box-shadow: 0 16px 36px rgba(0, 0, 0, 0.25);
	}
	.preview-header {
		display: flex;
		align-items: center;
		gap: .4rem;
		padding: .7rem 1rem;
		background: #0d2218;
		border-bottom: 1px solid rgba(82, 183, 136, 0.2);
	}
	.dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
	}
	.dot.red { background: #e63946; }
	.dot.yellow { background: #ffb703; }
	.dot.green { background: #52b788; }
	.preview-title {
		margin-left: .5rem;
		font-size: .75rem;
		color: #74c69d;
		font-weight: 600;
	}
	.preview-body {
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}
	.preview-case {
		background: rgba(255, 255, 255, 0.05);
		border-left: 3px solid #52b788;
		padding: .75rem;
		border-radius: 8px;
	}
	.case-tag {
		font-size: .65rem;
		font-weight: 750;
		color: #74c69d;
		text-transform: uppercase;
		letter-spacing: .05em;
	}
	.case-text {
		color: #ffffff;
		font-size: .8rem;
		margin: .3rem 0 0;
		line-height: 1.5;
	}
	.preview-synthesis {
		background: #091d13;
		border: 1px solid rgba(82, 183, 136, 0.25);
		padding: .85rem;
		border-radius: 10px;
		display: flex;
		flex-direction: column;
		gap: .4rem;
	}
	.synth-badge {
		display: inline-flex;
		align-items: center;
		gap: .35rem;
		background: rgba(82, 183, 136, 0.15);
		color: #52b788;
		font-size: .7rem;
		font-weight: 750;
		padding: .2rem .5rem;
		border-radius: 4px;
		width: fit-content;
	}
	.synth-text {
		color: #d8f3dc;
		font-size: .8rem;
		line-height: 1.5;
		margin: 0;
	}
	.citations-row {
		display: flex;
		gap: .4rem;
		flex-wrap: wrap;
		margin-top: .3rem;
	}
	.citation-pill {
		font-size: .65rem;
		background: rgba(255, 255, 255, 0.08);
		color: #74c69d;
		padding: .2rem .5rem;
		border-radius: 4px;
		border: 1px solid rgba(82, 183, 136, 0.2);
	}

	/* ── Guidance Section ────────────────────────────────────────────── */
	.guidance-section {
		padding: var(--space-7) 0;
		background: #fbfcf9;
	}
	.guidance-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
		gap: var(--space-5);
		margin-bottom: var(--space-6);
	}
	.guidance-card {
		background: #ffffff;
		border: 1px solid rgba(45, 106, 79, 0.14);
		border-radius: 16px;
		padding: var(--space-5);
		position: relative;
	}
	.step-num {
		font-size: 1.6rem;
		font-weight: 900;
		color: #52b788;
		opacity: 0.8;
		margin-bottom: .4rem;
		letter-spacing: -.03em;
	}
	.guidance-card h3 {
		font-size: var(--text-base);
		font-weight: 800;
		color: #1b4332;
		margin: 0 0 .5rem;
	}
	.guidance-card p {
		font-size: var(--text-sm);
		color: #3e5a4d;
		line-height: 1.55;
		margin: 0;
	}
	.who-box {
		background: #f4f8f4;
		border: 1px solid rgba(45, 106, 79, 0.16);
		border-radius: 16px;
		padding: var(--space-5);
		max-width: 52rem;
		margin: 0 auto;
	}
	.who-box h3 {
		font-size: var(--text-base);
		font-weight: 800;
		color: #1b4332;
		margin: 0 0 var(--space-4);
		text-align: center;
	}
	.who-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
		gap: .6rem;
	}
	.who-list li {
		display: flex;
		align-items: center;
		gap: .6rem;
		font-size: var(--text-xs);
		color: #1b4332;
		font-weight: 600;
	}
	.who-list li :global(svg) {
		color: #2d6a4f;
		flex: 0 0 auto;
	}

	/* ── Application Section ─────────────────────────────────────────── */
	.application-section {
		padding: var(--space-7) 0;
		background: #f4f8f4;
		border-top: 1px solid rgba(45, 106, 79, 0.12);
	}
	.form-container {
		max-width: 44rem;
		margin: 0 auto;
	}
	.form-card {
		background: #ffffff;
		border: 1px solid rgba(45, 106, 79, 0.16);
		border-radius: 20px;
		box-shadow: 0 8px 32px rgba(27, 67, 50, 0.06);
		overflow: hidden;
	}
	.form-header {
		padding: var(--space-5);
		background: #fbfcf9;
		border-bottom: 1px solid rgba(45, 106, 79, 0.12);
	}
	.form-title-group {
		display: flex;
		align-items: center;
		gap: .75rem;
	}
	.form-title-group h2 {
		font-size: var(--text-xl);
		font-weight: 850;
		color: #1b4332;
		margin: 0;
	}
	.form-sub {
		color: #52796f;
		font-size: var(--text-xs);
		margin: .15rem 0 0;
	}
	.form-body {
		padding: var(--space-6);
		display: grid;
		gap: var(--space-4);
	}
	.field-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-4);
	}
	.file-field {
		display: flex;
		flex-direction: column;
		gap: .35rem;
	}
	.file-field label {
		font-size: var(--text-xs);
		font-weight: 700;
		color: #1b4332;
	}
	.file-field input[type="file"] {
		font-size: var(--text-xs);
		color: #52796f;
	}
	.file-hint {
		font-size: .7rem;
		color: #52796f;
	}
	.error-banner {
		display: flex;
		align-items: center;
		gap: .5rem;
		background: #fbe8e8;
		color: #b13434;
		padding: .75rem 1rem;
		border-radius: 10px;
		font-size: var(--text-sm);
		font-weight: 600;
	}
	.form-actions {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		margin-top: var(--space-2);
	}
	.terms-note {
		font-size: .75rem;
		color: #52796f;
		line-height: 1.5;
		margin: 0;
		text-align: center;
	}

	@media (max-width: 820px) {
		.split-layout {
			grid-template-columns: 1fr;
		}
		.field-grid {
			grid-template-columns: 1fr;
		}
	}
</style>