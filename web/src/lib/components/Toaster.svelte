<script lang="ts">
	import { onMount } from 'svelte';
	import { toasts } from '$lib/stores/toast';

	// A toast fired while a <dialog> (Dialog.svelte, e.g. the ingest modal)
	// is open used to render behind it — found live: an error toast from
	// inside the scrape/paste flow never appeared. A native <dialog>'s
	// content renders in the browser's top layer, which always wins over
	// any regular position:fixed/z-index element no matter how high, so no
	// z-index value could ever fix this. The popover API promotes this
	// container to the top layer too; "manual" (not "auto") means it never
	// light-dismisses on its own — shown once here and left open for the
	// app's lifetime, individual toasts still added/removed by the normal
	// reactive list below. Top-layer elements stack by show order, so as
	// long as this is (re-)shown after a dialog opens, it wins — see the
	// $effect below.
	let container = $state<HTMLDivElement>();
	onMount(() => container?.showPopover?.());
	$effect(() => {
		if ($toasts.length) container?.showPopover?.();
	});
</script>

<div class="toasts" popover="manual" bind:this={container} aria-live="polite">
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
	/* [popover] carries its own UA-default box (inset:0, centered margin,
	   a border, Canvas background) meant for dialog-like popovers — all
	   reset here since this is just a positioned toast stack, not that. */
	.toasts {
		position: fixed; inset: auto var(--space-5) var(--space-5) auto; margin: 0; border: none;
		padding: 0; background: none; color: inherit; overflow: visible;
		z-index: 200; display: flex; flex-direction: column; gap: .5rem;
	}
	.toast {
		display: flex; align-items: center; gap: .5rem; padding: .7rem 1rem; border-radius: var(--r);
		background: var(--ink); color: #fff; box-shadow: var(--shadow-lg); font-size: var(--text-sm);
		animation: liftIn .3s var(--ease) both;
	}
	.toast.alert { background: var(--danger); }
	.toast svg { width: 16px; height: 16px; }
</style>
