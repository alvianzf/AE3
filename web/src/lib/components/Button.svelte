<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		variant = 'filled',
		type = 'button',
		disabled = false,
		loading = false,
		href,
		onclick,
		children
	}: {
		variant?: 'filled' | 'outlined' | 'text' | 'ghost' | 'danger';
		type?: 'button' | 'submit' | 'reset';
		disabled?: boolean;
		loading?: boolean;
		href?: string;
		onclick?: (e: MouseEvent) => void;
		children: Snippet;
	} = $props();
</script>

{#if href}
	<a {href} class="btn {variant}" class:is-disabled={disabled} aria-disabled={disabled}>
		{@render children()}
	</a>
{:else}
	<button {type} class="btn {variant}" disabled={disabled || loading} onclick={onclick}>
		{#if loading}<span class="spin" aria-hidden="true"></span>{/if}
		{@render children()}
	</button>
{/if}

<style>
	.btn {
		display: inline-flex; align-items: center; justify-content: center; gap: .45rem;
		min-height: var(--tap-min); padding: .55rem 1rem; border-radius: var(--r);
		font-size: var(--text-sm); font-weight: 650; letter-spacing: -.005em;
		border: 1px solid transparent; cursor: pointer; text-decoration: none;
		transition: background .16s var(--ease), color .16s var(--ease), border-color .16s var(--ease), transform .1s var(--ease);
		white-space: nowrap;
	}
	.btn:active:not(:disabled) { transform: scale(.98); }
	.btn:disabled, .btn.is-disabled { opacity: .5; cursor: not-allowed; }
	/* The glossy finish: a soft highlight across the top of each filled
	   button, on top of its flat color — not a full glass/blur treatment
	   (buttons aren't translucent, there's nothing behind them worth
	   blurring), just the same sheen language as the glass panels. */
	.filled { background: var(--accent); background-image: linear-gradient(165deg, rgba(255, 255, 255, .28), transparent 55%); color: #fff; box-shadow: var(--shadow); }
	.filled:hover:not(:disabled) { background: var(--accent-ink); background-image: linear-gradient(165deg, rgba(255, 255, 255, .28), transparent 55%); }
	.outlined { background: transparent; color: var(--accent-ink); border-color: var(--accent); }
	.outlined:hover:not(:disabled) { background: var(--accent-soft); }
	.text { background: transparent; color: var(--accent-ink); padding-inline: .5rem; }
	.text:hover:not(:disabled) { background: var(--accent-soft); }
	.ghost { background: var(--panel-2); color: var(--ink-2); border-color: var(--glass-border); backdrop-filter: var(--glass-blur); -webkit-backdrop-filter: var(--glass-blur); }
	.ghost:hover:not(:disabled) { background: var(--panel); border-color: var(--line-2); }
	.danger { background: var(--danger); background-image: linear-gradient(165deg, rgba(255, 255, 255, .28), transparent 55%); color: #fff; box-shadow: var(--shadow); }
	.danger:hover:not(:disabled) { filter: brightness(.92); }
	.spin {
		width: .9em; height: .9em; border-radius: 50%; border: 2px solid currentColor;
		border-top-color: transparent; animation: spin .7s linear infinite;
	}
	@keyframes spin { to { transform: rotate(360deg); } }
</style>
