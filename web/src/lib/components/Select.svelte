<script lang="ts">
	let {
		label,
		value = $bindable(''),
		options,
		required = false,
		id = `sel-${Math.random().toString(36).slice(2)}`
	}: {
		label: string;
		value?: string;
		options: { value: string; label: string }[];
		required?: boolean;
		id?: string;
	} = $props();
</script>

<div class="field">
	<label for={id}>{label}</label>
	<select {id} bind:value {required}>
		{#each options as opt (opt.value)}
			<option value={opt.value}>{opt.label}</option>
		{/each}
	</select>
</div>

<style>
	.field { display: flex; flex-direction: column; gap: .35rem; }
	select {
		border: 1px solid var(--line-2); border-radius: var(--r); background: var(--panel);
		padding: var(--space-3); font-size: var(--text-base); color: var(--ink);
		min-height: var(--tap-min);
	}
	select:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
</style>
