<script lang="ts">
	import { goto } from '$app/navigation';
	import { post } from '$lib/api';
	import Icon from './Icon.svelte';
	import Menu from './Menu.svelte';

	// Replaces the persistent sidebar's footer entirely — there is no
	// persistent nav surface any more (see HomeGrid.svelte for how
	// navigation actually works now: a launcher, not a rail). This is
	// the one small, fixed, always-reachable control every page keeps:
	// who's signed in, the dual-role switcher, and sign out.
	let {
		userLabel,
		showSwitcher = false,
		switcherTo = 'practitioner'
	}: { userLabel?: string; showSwitcher?: boolean; switcherTo?: 'admin' | 'practitioner' } = $props();

	async function logout(e: Event) {
		e.preventDefault();
		await post(fetch, '/auth/logout').catch(() => {});
		goto('/login', { invalidateAll: true });
	}
</script>

<div class="account-menu">
	<Menu label="Account">
		{#snippet items()}
			{#if userLabel}<div class="who-row">{userLabel}</div>{/if}
			{#if showSwitcher}
				<a href={switcherTo === 'admin' ? '/admin' : '/practitioner'}>
					<Icon name="switch" size={15} /> {switcherTo === 'admin' ? 'Switch to admin view' : 'Switch to practitioner view'}
				</a>
			{/if}
			<form method="post" action="/api/auth/logout" onsubmit={logout}>
				<button type="submit" class="danger"><Icon name="x" size={15} /> Sign out</button>
			</form>
		{/snippet}
	</Menu>
</div>

<style>
	.account-menu { position: fixed; top: var(--space-4); right: var(--space-4); z-index: 50; }
	.account-menu :global(.menu-wrap .icon-btn) {
		width: 2.4rem; height: 2.4rem; border-radius: 50%; background: var(--panel);
		border: 1px solid var(--line); box-shadow: var(--shadow); color: var(--ink-2);
	}
	.account-menu :global(.menu-wrap .icon-btn:hover) { background: var(--panel-2); }
	.account-menu :global(.menu-pop) { right: 0; left: auto; }
	.who-row { padding: .5rem .6rem; font-size: var(--text-sm); color: var(--muted); white-space: nowrap; }
</style>
