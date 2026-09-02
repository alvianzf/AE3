<script lang="ts">
	import type { Snippet } from 'svelte';
	let {
		tone = 'neutral',
		children
	}: { tone?: 'neutral' | 'accent' | 'ok' | 'warn' | 'danger'; children: Snippet } = $props();
</script>

<span class="chip {tone}"><span class="dot" aria-hidden="true"></span>{@render children()}</span>

<style>
	.chip {
		display: inline-flex; align-items: center; gap: .35rem;
		font-size: var(--text-xs); font-weight: 700; text-transform: uppercase; letter-spacing: .06em;
		padding: .22rem .55rem; border-radius: 99px;
	}
	.dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
	.neutral { background: var(--panel-2); color: var(--muted); border: 1px solid var(--line); }
	.accent { background: var(--accent-soft); color: var(--accent-ink); }
	.ok { background: var(--ok-soft); color: var(--ok); }
	.warn { background: var(--warn-soft); color: var(--warn); }
	.danger { background: var(--danger-soft); color: var(--danger); }
</style>
