<script lang="ts">
	let {
		tabs,
		active = $bindable('')
	}: { tabs: { id: string; label: string }[]; active?: string } = $props();

	$effect(() => {
		if (!active && tabs.length) active = tabs[0].id;
	});

	function onKeydown(e: KeyboardEvent) {
		const idx = tabs.findIndex((t) => t.id === active);
		if (e.key === 'ArrowRight') { active = tabs[(idx + 1) % tabs.length].id; e.preventDefault(); }
		if (e.key === 'ArrowLeft') { active = tabs[(idx - 1 + tabs.length) % tabs.length].id; e.preventDefault(); }
	}
</script>

<div class="tabs" role="tablist" tabindex="-1" onkeydown={onKeydown}>
	{#each tabs as t (t.id)}
		<button
			role="tab"
			id="tab-{t.id}"
			aria-selected={active === t.id}
			aria-controls="panel-{t.id}"
			tabindex={active === t.id ? 0 : -1}
			class:on={active === t.id}
			onclick={() => (active = t.id)}
		>
			{t.label}
		</button>
	{/each}
</div>

<style>
	.tabs { display: flex; gap: .25rem; border-bottom: 1px solid var(--line); }
	button {
		border: none; background: none; padding: .65rem 1rem; font-size: var(--text-sm); font-weight: 650;
		color: var(--muted); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px;
		transition: color .15s var(--ease), border-color .15s var(--ease);
	}
	button.on { color: var(--accent-ink); border-color: var(--accent); }
	button:hover:not(.on) { color: var(--ink-2); }
</style>
