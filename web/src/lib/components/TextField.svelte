<script lang="ts">
	let {
		label,
		type = 'text',
		value = $bindable(''),
		placeholder = '',
		required = false,
		disabled = false,
		hint = '',
		list = '',
		id = `tf-${Math.random().toString(36).slice(2)}`
	}: {
		label: string;
		type?: string;
		value?: string;
		placeholder?: string;
		required?: boolean;
		disabled?: boolean;
		hint?: string;
		list?: string;
		id?: string;
	} = $props();
</script>

<div class="field">
	<label for={id}>{label}{#if required}<span class="req">*</span>{/if}</label>
	{#if type === 'textarea'}
		<textarea {id} bind:value {placeholder} {required} {disabled} rows="4"></textarea>
	{:else}
		<input {id} {type} bind:value {placeholder} {required} {disabled} list={list || undefined} />
	{/if}
	{#if hint}<p class="hint">{hint}</p>{/if}
</div>

<style>
	.field { display: flex; flex-direction: column; gap: .35rem; }
	.req { color: var(--accent); margin-left: .2rem; }
	label { font-size: var(--text-sm); font-weight: var(--weight-medium); color: var(--ink-2); }
	/* A sleek underline field, not a boxed one — border only on the
	   bottom edge, no radius, no background box; the focus state thickens
	   and recolors that single line rather than adding a ring. */
	input, textarea {
		border: var(--field-frame, none); border-bottom: var(--field-line, 1px solid var(--line-2));
		border-radius: var(--field-r, 0); background: var(--field-bg, none); box-shadow: var(--field-shadow, none);
		padding: var(--field-pad, var(--space-2) .1rem); font-size: var(--text-base); color: var(--ink);
		min-height: var(--tap-min); resize: vertical;
		transition: border-color .15s var(--ease), box-shadow .15s var(--ease);
	}
	input:focus, textarea:focus {
		outline: none; border-color: var(--accent);
		box-shadow: var(--field-focus, 0 1px 0 0 var(--accent));
	}
	input:disabled, textarea:disabled { color: var(--muted); }
</style>
