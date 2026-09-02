<script lang="ts">
	import { toasts } from '$lib/stores/toast';
</script>

<div class="toasts" aria-live="polite">
	{#each $toasts as t (t.id)}
		<div class="toast {t.kind}">
			{#if t.kind === 'ok'}
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12l5 5L20 6" /></svg>
			{:else}
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4l9 16H3zM12 10v4M12 17h.01" /></svg>
			{/if}
			<span>{t.msg}</span>
		</div>
	{/each}
</div>

<style>
	.toasts { position: fixed; right: var(--space-5); bottom: var(--space-5); z-index: 200; display: flex; flex-direction: column; gap: .5rem; }
	.toast {
		display: flex; align-items: center; gap: .5rem; padding: .7rem 1rem; border-radius: var(--r);
		background: var(--ink); color: #fff; box-shadow: var(--shadow-lg); font-size: var(--text-sm);
		animation: liftIn .3s var(--ease) both;
	}
	.toast.alert { background: var(--danger); }
	.toast svg { width: 16px; height: 16px; }
</style>
