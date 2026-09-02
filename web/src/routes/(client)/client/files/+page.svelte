<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Button from '$lib/components/Button.svelte';

	let { data } = $props();
	let uploading = $state(false);
	let fileInput = $state<HTMLInputElement>();

	async function upload() {
		const f = fileInput?.files?.[0];
		if (!f) return;
		uploading = true;
		const fd = new FormData();
		fd.set('file', f);
		try {
			const res = await fetch(`${PUBLIC_API_BASE}/api/me/files`, { method: 'POST', credentials: 'include', body: fd });
			if (!res.ok) throw new Error('Upload failed.');
			toast('File uploaded.');
			if (fileInput) fileInput.value = '';
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			uploading = false;
		}
	}
</script>

<svelte:head><title>Files — Client portal</title></svelte:head>

<Spotlight title="Your files">
	<div class="uploader">
		<input type="file" bind:this={fileInput} />
		<Button onclick={upload} loading={uploading}>Upload</Button>
	</div>
	<DataTable
		columns={[{ key: 'filename', label: 'File' }, { key: 'content_type', label: 'Type' }, { key: 'uploaded_at', label: 'Uploaded' }]}
		rows={data.files}
		empty="No files uploaded yet."
	>
		{#snippet row(f)}
			<td>{f.filename}</td>
			<td>{f.content_type}</td>
			<td>{f.uploaded_at ?? ''}</td>
		{/snippet}
	</DataTable>
</Spotlight>

<style>
	.uploader { display: flex; gap: var(--space-3); align-items: center; margin-bottom: var(--space-4); }
</style>
