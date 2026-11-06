<script lang="ts">
	import Seo from '$lib/components/Seo.svelte';
	import Sprig from '$lib/components/Sprig.svelte';

	const faqs = [
		{
			q: 'Do clients interact directly with an AI or chatbot?',
			a: 'No. Clients never interact with an AI, bot, or automated agent. Functional Health Collab is a clinical intelligence platform used exclusively by your human practitioner. It operates behind the scenes to synthesize your health timeline, questionnaires, and lab biomarkers against peer-reviewed clinical research. Every consultation, decision, and personalized care plan comes directly from your licensed human practitioner.'
		},
		{
			q: 'How are client protocols created and implemented?',
			a: 'Each client receives an individualized protocol designed specifically for their unique biology, lab results, and health history. The platform never prescribes or auto-implements treatments. Your human practitioner decides what therapies to include, how to prioritize them into phases, and exactly when each stage is implemented.'
		},
		{
			q: 'What does "practitioner augmentation" mean?',
			a: 'Functional medicine involves immense complexity — dozens of lab biomarkers, intricate symptom timelines, and vast clinical research. Functional Health Collab equips practitioners with deep synthesis tools so no patient detail or critical lab trend is ever lost in paperwork. Your practitioner arrives at your consultation deeply informed and fully prepared.'
		},
		{
			q: 'How does evidence citation and anti-hallucination work?',
			a: 'Every therapeutic recommendation and protocol is drawn strictly from curated functional medicine literature, peer-reviewed journals, and clinical reference textbooks. An automated verification engine cross-examines citations against actual source passages before your provider sees them, ensuring zero open-web hallucinations.'
		},
		{
			q: 'What happens to my data as a client?',
			a: 'Your health records, lab markers, and questionnaire answers live in an encrypted, isolated space dedicated to your practitioner. Your personal health information is never pooled with other practices, sold, or used for commercial advertising.'
		},
		{
			q: 'How do practitioners get approved to join?',
			a: 'Every practitioner must apply and submit their credentials, clinical licenses, or functional health certifications. Our clinical team reviews each application before granting access to active client management.'
		},
		{
			q: 'Is Functional Health Collab a substitute for medical advice?',
			a: 'No. Functional Health Collab is a clinical decision-support and synthesis system for licensed practitioners. It does not provide direct medical advice to clients, and all clinical judgment remains solely with the treating clinician.'
		}
	];
</script>

<Seo
	title="Frequently Asked Questions — Functional Health Collab"
	description="Answers to common questions about functional medicine consultations, practitioner augmentation, evidence citations, and data privacy."
	path="/faq"
/>

<div class="container faq-page">
	<div class="faq-header">
		<div class="badge-wrap">
			<span class="logo-mark"><Sprig size={18} /></span>
			<span>Client & Practitioner FAQ</span>
		</div>
		<h1>Frequently Asked Questions</h1>
		<p class="lede">Everything you need to know about our functional health network, clinical evidence standards, and client privacy.</p>
	</div>

	<div class="faq-list">
		{#each faqs as f (f.q)}
			<div class="faq-card">
				<h3>{f.q}</h3>
				<p>{f.a}</p>
			</div>
		{/each}
	</div>
</div>

<style>
	.faq-page {
		padding: var(--space-7) var(--space-5);
		max-width: 48rem;
		margin: 0 auto;
	}
	.faq-header {
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
	.faq-header h1 {
		font-size: clamp(2rem, 3.2vw, 2.75rem);
		font-weight: 850;
		color: #1b4332;
		letter-spacing: -.025em;
		margin: 0;
	}
	.lede {
		color: #52796f;
		font-size: var(--text-base);
		max-width: 34rem;
		margin: var(--space-3) auto 0;
		line-height: 1.6;
	}
	.faq-list {
		display: grid;
		gap: var(--space-4);
	}
	.faq-card {
		background: #ffffff;
		border: 1px solid rgba(45, 106, 79, 0.14);
		border-radius: 14px;
		padding: var(--space-5);
		box-shadow: 0 4px 16px rgba(27, 67, 50, 0.03);
	}
	.faq-card h3 {
		font-size: var(--text-base);
		font-weight: 800;
		color: #1b4332;
		margin: 0 0 .5rem;
		line-height: 1.4;
	}
	.faq-card p {
		margin: 0;
		color: #3e5a4d;
		font-size: var(--text-sm);
		line-height: 1.6;
	}
</style>