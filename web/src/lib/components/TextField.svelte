<script lang="ts">
	let {
		label,
		type = 'text',
		value = $bindable(''),
		placeholder = '',
		required = false,
		disabled = false,
		hint = '',
		id = `tf-${Math.random().toString(36).slice(2)}`
	}: {
		label: string;
		type?: string;
		value?: string;
		placeholder?: string;
		required?: boolean;
		disabled?: boolean;
		hint?: string;
		id?: string;
	} = $props();
</script>

<div class="field">
	<label for={id}>{label}{#if required}<span class="req">*</span>{/if}</label>
	{#if type === 'textarea'}
		<textarea {id} bind:value {placeholder} {required} {disabled} rows="4"></textarea>
	{:else}
		<input {id} {type} bind:value {placeholder} {required} {disabled} />
	{/if}
	{#if hint}<p class="hint">{hint}</p>{/if}
</div>

<style>
	.field { display: flex; flex-direction: column; gap: .35rem; }
	.req { color: var(--accent); margin-left: .2rem; }
	input, textarea {
		border: 1px solid var(--line-2); border-radius: var(--r); background: var(--panel);
		padding: var(--space-3); font-size: var(--text-base); color: var(--ink);
		min-height: var(--tap-min); resize: vertical;
		transition: border-color .15s var(--ease), box-shadow .15s var(--ease);
	}
	input:focus, textarea:focus {
		outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft);
	}
	input:disabled, textarea:disabled { background: var(--panel-2); color: var(--muted); }
</style>
