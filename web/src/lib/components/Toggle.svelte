<script lang="ts">
	// A real <button role="switch"> under the hood, not a styled checkbox —
	// keyboard/screen-reader behavior comes for free (Space toggles, aria-
	// checked announces state) without needing a hidden <input type="checkbox">
	// plus a label-for hack.
	let {
		checked,
		onchange,
		disabled = false,
		label
	}: {
		checked: boolean;
		onchange: (next: boolean) => void;
		disabled?: boolean;
		label?: string;
	} = $props();
</script>

<button
	type="button"
	role="switch"
	aria-checked={checked}
	aria-label={label}
	class="toggle"
	class:on={checked}
	{disabled}
	onclick={() => onchange(!checked)}
>
	<span class="knob"></span>
</button>

<style>
	.toggle {
		--w: 2.4rem; --h: 1.4rem; --pad: 2px;
		position: relative; display: inline-flex; align-items: center; flex: 0 0 auto;
		width: var(--w); height: var(--h); padding: 0; border: none; border-radius: 99px;
		background: var(--line-2); cursor: pointer;
		transition: background .18s var(--ease);
	}
	.toggle.on { background: var(--ok); }
	.toggle:disabled { opacity: .5; cursor: not-allowed; }
	.knob {
		position: absolute; top: var(--pad); left: var(--pad);
		width: calc(var(--h) - var(--pad) * 2); height: calc(var(--h) - var(--pad) * 2);
		border-radius: 50%; background: #fff; box-shadow: var(--shadow);
		transition: transform .18s var(--ease);
	}
	.toggle.on .knob { transform: translateX(calc(var(--w) - var(--h))); }
	.toggle:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
</style>
