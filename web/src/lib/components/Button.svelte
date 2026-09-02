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
		min-height: var(--tap-min); padding: .55rem 1rem; border-radius: 99px;
		font-size: var(--text-sm); font-weight: 650; letter-spacing: -.005em;
		border: 1px solid transparent; cursor: pointer; text-decoration: none;
		transition: background .16s var(--ease), color .16s var(--ease), border-color .16s var(--ease), transform .1s var(--ease);
		white-space: nowrap;
	}
	.btn:active:not(:disabled) { transform: scale(.98); }
	.btn:disabled, .btn.is-disabled { opacity: .5; cursor: not-allowed; }
	.filled { background: var(--accent); color: #fff; }
	.filled:hover:not(:disabled) { background: var(--accent-ink); }
	.outlined { background: transparent; color: var(--accent-ink); border-color: var(--accent); }
	.outlined:hover:not(:disabled) { background: var(--accent-soft); }
	.text { background: transparent; color: var(--accent-ink); padding-inline: .5rem; }
	.text:hover:not(:disabled) { background: var(--accent-soft); }
	.ghost { background: var(--panel-2); color: var(--ink-2); border-color: var(--line); }
	.ghost:hover:not(:disabled) { background: var(--panel); border-color: var(--line-2); }
	.danger { background: var(--danger); color: #fff; }
	.danger:hover:not(:disabled) { filter: brightness(.92); }
	.spin {
		width: .9em; height: .9em; border-radius: 50%; border: 2px solid currentColor;
		border-top-color: transparent; animation: spin .7s linear infinite;
	}
	@keyframes spin { to { transform: rotate(360deg); } }
</style>
