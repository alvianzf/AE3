<script lang="ts">
	import { post } from '$lib/api';

	// specs/v7/06 — a spotlight-style first-run guided tour. One step at
	// a time: dims the page, highlights one element (matched by a CSS
	// selector the caller supplies — each portal's own page already has
	// stable ids/classes on the elements worth pointing at, no new
	// data-tour-* attributes needed), shows a callout with Next/Skip.
	// Skippable at every step, never a hard gate — closing it (Skip or
	// finishing the last step) marks the account's tour_completed flag
	// server-side via POST /api/auth/tour-completed so it doesn't
	// reappear on the next login, on this device or any other.
	export interface TourStep {
		selector: string;
		title: string;
		body: string;
	}

	let {
		steps,
		active = $bindable(false)
	}: { steps: TourStep[]; active?: boolean } = $props();

	let stepIndex = $state(0);
	let targetRect = $state<DOMRect | null>(null);

	// Re-measures on every step change and on resize/scroll — the
	// highlighted element's position isn't fixed (a rail icon moves if
	// the window resizes, a card the tour points at can be anywhere in
	// a scrollable list) and a stale rect would highlight empty space.
	function measure() {
		if (!active) return;
		const el = document.querySelector(steps[stepIndex]?.selector ?? '');
		targetRect = el ? el.getBoundingClientRect() : null;
		if (el) el.scrollIntoView({ block: 'center', behavior: 'smooth' });
	}

	$effect(() => {
		if (!active) return;
		stepIndex;
		measure();
		window.addEventListener('resize', measure);
		// capture: true — the same page's own scroll containers (the
		// admin Library grid, the Consult chat thread) aren't the
		// window itself, and a plain bubble-phase listener on window
		// never sees their internal scroll events.
		window.addEventListener('scroll', measure, true);
		return () => {
			window.removeEventListener('resize', measure);
			window.removeEventListener('scroll', measure, true);
		};
	});

	async function finish() {
		active = false;
		try {
			await post(fetch, '/auth/tour-completed', {});
		} catch {
			/* best-effort — worst case the tour offers itself again next
			   login, not a page-breaking failure either way */
		}
	}

	function next() {
		if (stepIndex < steps.length - 1) stepIndex++;
		else finish();
	}
</script>

{#if active && steps.length}
	<div class="tour-overlay">
		{#if targetRect}
			<div
				class="tour-hole"
				style:left="{targetRect.left - 8}px"
				style:top="{targetRect.top - 8}px"
				style:width="{targetRect.width + 16}px"
				style:height="{targetRect.height + 16}px"
			></div>
		{/if}
		<div
			class="tour-callout"
			style:left={targetRect ? `${Math.min(targetRect.left, window.innerWidth - 320)}px` : '50%'}
			style:top={targetRect ? `${targetRect.bottom + 16}px` : '50%'}
		>
			<p class="tour-step-count">{stepIndex + 1} of {steps.length}</p>
			<h3>{steps[stepIndex].title}</h3>
			<p class="tour-body">{steps[stepIndex].body}</p>
			<div class="tour-actions">
				<button type="button" class="tour-skip" onclick={finish}>Skip</button>
				<button type="button" class="tour-next" onclick={next}>
					{stepIndex < steps.length - 1 ? 'Next' : 'Done'}
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.tour-overlay { position: fixed; inset: 0; z-index: 200; pointer-events: none; }
	.tour-hole {
		position: fixed; border-radius: var(--r-lg); pointer-events: none;
		box-shadow: 0 0 0 9999px rgba(34, 31, 27, .55);
		transition: left var(--duration-base) var(--ease), top var(--duration-base) var(--ease),
			width var(--duration-base) var(--ease), height var(--duration-base) var(--ease);
	}
	.tour-callout {
		position: fixed; width: 18rem; max-width: calc(100vw - 2rem); pointer-events: auto;
		background: var(--panel); border-radius: var(--r-lg); box-shadow: var(--shadow-lg);
		padding: var(--space-4); animation: liftIn var(--duration-base) var(--ease) both;
		transform: translateX(-50%);
	}
	.tour-step-count { margin: 0 0 .3rem; font-size: var(--text-xs); color: var(--muted); font-weight: var(--weight-medium, 600); }
	.tour-callout h3 { font-size: var(--text-base); margin-bottom: .3rem; }
	.tour-body { color: var(--muted); font-size: var(--text-sm); margin-bottom: var(--space-3); }
	.tour-actions { display: flex; justify-content: space-between; align-items: center; gap: var(--space-3); }
	.tour-skip {
		border: none; background: none; color: var(--muted); cursor: pointer; font-size: var(--text-sm);
		padding: .3rem 0;
	}
	.tour-next {
		border: none; background: var(--accent); color: #fff; cursor: pointer; font-size: var(--text-sm);
		font-weight: 650; padding: .45rem 1rem; border-radius: var(--r);
	}
</style>
