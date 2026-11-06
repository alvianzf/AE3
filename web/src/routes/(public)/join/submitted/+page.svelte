<script lang="ts">
	import Sprig from '$lib/components/Sprig.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Icon from '$lib/components/Icon.svelte';
</script>

<Seo
	title="Application Received — Functional Health Collab"
	description="Your practitioner application has been received and is under clinical review."
	path="/join/submitted"
	noindex
/>

<div class="container wrap">
	<section class="card-panel">
		<div class="ph">
			<h2><Sprig size={20} /> Application Submitted</h2>
		</div>
		<div class="pb center">
			<div class="success-icon">
				<Icon name="check" size={28} />
			</div>
			<h1>Thank you for applying</h1>
			<p class="desc">
				Our clinical advisory board reviews all practitioner credentials within <strong>1–2 business days</strong>.
				Once approved, you'll receive access to your clinical workspace, intake configuration, and directory profile.
			</p>
			<div class="next-box">
				<h3>What happens next?</h3>
				<ul>
					<li><strong>Credential verification:</strong> We verify your functional certifications or state licensure.</li>
					<li><strong>Workspace setup:</strong> You can upload your preferred clinical reference texts and custom questionnaires.</li>
					<li><strong>Public listing:</strong> Your profile is published to the directory so clients can book consultations.</li>
				</ul>
			</div>
			<div class="actions">
				<a class="btn-primary" href="/login">Go to Practitioner Login</a>
				<a class="btn-subtle" href="/">Back to Home</a>
			</div>
		</div>
	</section>
</div>

<style>
	.wrap {
		padding: var(--space-7) var(--space-5);
		max-width: 36rem;
		margin: 0 auto;
	}
	.center {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		gap: var(--space-4);
	}
	.success-icon {
		width: 56px;
		height: 56px;
		border-radius: 50%;
		background: #e8f4ec;
		color: #2d6a4f;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-top: .5rem;
	}
	h1 {
		font-size: var(--text-2xl);
		font-weight: 850;
		color: #1b4332;
		margin: 0;
	}
	.desc {
		color: #52796f;
		font-size: var(--text-sm);
		line-height: 1.6;
		margin: 0;
	}
	.next-box {
		background: #f4f8f4;
		border: 1px solid rgba(45, 106, 79, 0.16);
		border-radius: 12px;
		padding: var(--space-4);
		text-align: left;
		width: 100%;
	}
	.next-box h3 {
		font-size: var(--text-xs);
		text-transform: uppercase;
		letter-spacing: .05em;
		font-weight: 750;
		color: #2d6a4f;
		margin: 0 0 .5rem;
	}
	.next-box ul {
		margin: 0;
		padding-left: 1.2rem;
		display: grid;
		gap: .4rem;
		font-size: var(--text-xs);
		color: #1b4332;
		line-height: 1.5;
	}
	.actions {
		display: flex;
		flex-direction: column;
		gap: .6rem;
		width: 100%;
		margin-top: .5rem;
	}
	.btn-primary {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		background: #2d6a4f;
		color: #ffffff;
		padding: .75rem 1.25rem;
		border-radius: 10px;
		text-decoration: none;
		font-weight: 750;
		font-size: var(--text-sm);
		box-shadow: 0 3px 10px rgba(45, 106, 79, 0.2);
		transition: background var(--duration-fast);
	}
	.btn-primary:hover {
		background: #1b4332;
	}
	.btn-subtle {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: #52796f;
		text-decoration: none;
		font-size: var(--text-sm);
		font-weight: 650;
	}
	.btn-subtle:hover {
		color: #1b4332;
	}
</style>