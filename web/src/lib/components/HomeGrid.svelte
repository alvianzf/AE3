<script lang="ts">
	import Icon from './Icon.svelte';

	// The actual replacement for the persistent sidebar/rail/top-nav —
	// not a styling swap, a different navigation model. There is no
	// always-present chrome listing every destination any more. Each
	// portal's root is this launcher: big tiles, one per destination,
	// each showing its own live status where there is one. Pick a tile,
	// land in that Workspace (Workspace.svelte's back arrow returns here).
	export interface Tile {
		href: string;
		label: string;
		icon: string;
		tone?: 'accent' | 'ok' | 'warn' | 'danger';
		status?: string;
		locked?: boolean;
	}
	let { tiles }: { tiles: Tile[] } = $props();
</script>

<div class="tiles">
	{#each tiles as t (t.href)}
		<a class="tile" class:locked={t.locked} href={t.locked ? undefined : t.href} aria-disabled={t.locked}>
			<span class="tile-icon tone-{t.tone ?? 'accent'}"><Icon name={t.icon} size={22} /></span>
			<span class="tile-label">{t.label}{#if t.locked} <span class="pro">Pro</span>{/if}</span>
			{#if t.status}<span class="tile-status">{t.status}</span>{/if}
		</a>
	{/each}
</div>

<style>
	.tiles { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr)); }
	.tile {
		display: flex; flex-direction: column; align-items: flex-start; gap: var(--space-3);
		padding: var(--space-5); border-radius: var(--r-xl); background: var(--panel);
		border: 1px solid var(--line); box-shadow: var(--shadow); text-decoration: none; color: var(--ink);
		min-height: 9rem; transition: transform .16s var(--ease), box-shadow .16s var(--ease);
	}
	.tile:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); }
	.tile.locked { opacity: .55; cursor: not-allowed; }
	.tile.locked:hover { transform: none; box-shadow: var(--shadow); }
	.tile-icon {
		display: flex; align-items: center; justify-content: center; width: 3rem; height: 3rem;
		border-radius: var(--r-lg);
	}
	.tone-accent { background: var(--accent-soft); color: var(--accent-ink); }
	.tone-ok { background: var(--ok-soft); color: var(--ok); }
	.tone-warn { background: var(--warn-soft); color: var(--warn); }
	.tone-danger { background: var(--danger-soft); color: var(--danger); }
	.tile-label { font-size: var(--text-lg); font-weight: var(--weight-bold); margin-top: auto; }
	.pro { font-size: .65rem; font-weight: 700; text-transform: uppercase; color: var(--warn); }
	.tile-status { font-size: var(--text-sm); color: var(--muted); }
</style>
