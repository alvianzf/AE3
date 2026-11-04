<script lang="ts">
	import { goto } from '$app/navigation';
	import Icon from './Icon.svelte';

	// specs/v7/06 — Cmd/Ctrl+K command palette. v1 scope is navigation
	// only (jump to a route) — each portal's own page-local state
	// (dialogs, tab selection, etc.) lives in that page's own component,
	// not reachable from here since this is wired at the portal's
	// +layout.svelte level, one level above any single page. A richer
	// "trigger this page's own action" version is a real possible
	// follow-up, not attempted here — fuzzy-matching routes/labels
	// already covers "jump to X" without it.
	//
	// Built on the same native <dialog> pattern Dialog.svelte already
	// uses (not the popover attribute Menu.svelte moved away from after
	// a live reliability report) — <dialog> has no equivalent history of
	// trouble in this app, so there was no reason to avoid it here.
	export interface CommandItem {
		label: string;
		href: string;
		icon?: string;
		group?: string;
	}

	let {
		items,
		open = $bindable(false)
	}: { items: CommandItem[]; open?: boolean } = $props();

	let dialogEl: HTMLDialogElement;
	let query = $state('');
	let activeIndex = $state(0);
	let inputEl: HTMLInputElement;

	const filtered = $derived.by(() => {
		const needle = query.trim().toLowerCase();
		if (!needle) return items;
		return items.filter(
			(i) => i.label.toLowerCase().includes(needle) || (i.group ?? '').toLowerCase().includes(needle)
		);
	});

	$effect(() => {
		if (!dialogEl) return;
		if (open && !dialogEl.open) {
			dialogEl.showModal();
			query = '';
			activeIndex = 0;
			// showModal() itself doesn't reliably hand focus to a child
			// input across browsers — explicit focus on the next frame.
			requestAnimationFrame(() => inputEl?.focus());
		}
		if (!open && dialogEl.open) dialogEl.close();
	});

	// Clamp, not wrap — found while building: wrapping from the last
	// item back to the first (or vice versa) reads as the list
	// "jumping" with no warning on a long result set; stopping at the
	// ends is the more predictable, more common palette behavior
	// (VS Code, Spotlight, etc. all clamp too).
	function move(delta: number) {
		if (!filtered.length) return;
		activeIndex = Math.max(0, Math.min(filtered.length - 1, activeIndex + delta));
	}

	function select(item: CommandItem) {
		open = false;
		goto(item.href);
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
		else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
		else if (e.key === 'Enter') { e.preventDefault(); if (filtered[activeIndex]) select(filtered[activeIndex]); }
	}
</script>

<dialog
	bind:this={dialogEl}
	class="palette"
	onclose={() => (open = false)}
	onclick={(e) => { if (e.target === dialogEl) dialogEl.close(); }}
>
	<div class="search-row">
		<Icon name="search" size={16} />
		<input
			bind:this={inputEl}
			type="text"
			placeholder="Jump to…"
			bind:value={query}
			oninput={() => (activeIndex = 0)}
			onkeydown={onKeydown}
			aria-label="Command palette search"
		/>
	</div>
	<ul class="results">
		{#each filtered as item, i (item.href)}
			<li>
				<button
					type="button"
					class:active={i === activeIndex}
					onclick={() => select(item)}
					onmouseenter={() => (activeIndex = i)}
				>
					{#if item.icon}<Icon name={item.icon} size={15} />{/if}
					<span class="label">{item.label}</span>
					{#if item.group}<span class="group">{item.group}</span>{/if}
				</button>
			</li>
		{:else}
			<li class="empty">No matches.</li>
		{/each}
	</ul>
</dialog>

<style>
	.palette {
		border: none; border-radius: var(--r-xl); padding: 0; width: min(32rem, 92vw);
		box-shadow: var(--shadow-lg); background: var(--panel);
		animation: liftIn var(--duration-base) var(--ease) both;
		margin-top: 12vh;
	}
	.palette::backdrop { background: rgba(34, 31, 27, .45); backdrop-filter: blur(2px); }
	.search-row {
		display: flex; align-items: center; gap: .6rem; padding: var(--space-4) var(--space-5);
		border-bottom: 1px solid var(--line); color: var(--muted);
	}
	.search-row input {
		flex: 1; border: none; background: none; font: inherit; font-size: var(--text-lg); color: var(--ink);
	}
	.search-row input:focus { outline: none; }
	.results { list-style: none; margin: 0; padding: var(--space-2); max-height: 60vh; overflow-y: auto; }
	.results button {
		display: flex; align-items: center; gap: .6rem; width: 100%; text-align: left;
		border: none; background: none; cursor: pointer; font: inherit; font-size: var(--text-sm);
		color: var(--ink); padding: .6rem .7rem; border-radius: var(--r);
	}
	.results button.active { background: var(--accent-soft); color: var(--accent-ink); }
	.results .label { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.results .group { font-size: var(--text-xs); color: var(--muted); flex: 0 0 auto; }
	.results .empty { padding: var(--space-4); text-align: center; color: var(--muted); font-size: var(--text-sm); }
</style>
