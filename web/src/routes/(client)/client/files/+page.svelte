<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { chunkedUpload } from '$lib/chunkedUpload';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Button from '$lib/components/Button.svelte';

	let { data } = $props();
	let uploading = $state(false);
	let uploadProgress = $state<{ sent: number; total: number } | null>(null);
	let fileInput = $state<HTMLInputElement>();

	async function upload() {
		const f = fileInput?.files?.[0];
		if (!f) return;
		uploading = true;
		uploadProgress = null;
		try {
			// Up to 200 MB, sent in pieces (app/uploads.py, lib/chunkedUpload.ts)
			// — a lab-result PDF or scan can be large, and a client's upload
			// speed/connection is the least controllable part of this app.
			await chunkedUpload('/me/files', f, {}, (p) => (uploadProgress = p));
			toast('File uploaded.');
			if (fileInput) fileInput.value = '';
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			uploading = false;
			uploadProgress = null;
		}
	}

	function viewUrl(f: any) {
		return `${PUBLIC_API_BASE}/api/me/files/${f.id}`;
	}
</script>

<svelte:head><title>Files — Client portal</title></svelte:head>

<Spotlight title="Your files">
	<div class="uploader">
		<div class="uploader-row">
			<input type="file" bind:this={fileInput} />
			<Button onclick={upload} loading={uploading}>Upload</Button>
		</div>
		<p class="hint">Up to 200 MB.</p>
		{#if uploadProgress}
			<div class="upload-progress">
				<div class="bar" style="width: {Math.round((uploadProgress.sent / uploadProgress.total) * 100)}%"></div>
				<span class="hint">{Math.round(uploadProgress.sent / 1024 / 1024)} / {Math.round(uploadProgress.total / 1024 / 1024)} MB</span>
			</div>
		{/if}
	</div>
	<DataTable
		columns={[{ key: 'original_name', label: 'File' }, { key: 'media_type', label: 'Type' }, { key: 'uploaded_at', label: 'Uploaded' }, { key: 'view', label: '' }]}
		rows={data.files}
		empty="No files uploaded yet."
	>
		{#snippet row(f: any)}
			<td>{f.original_name}</td>
			<td>{f.media_type}</td>
			<td>{f.uploaded_at ?? ''}</td>
			<td><a class="view" href={viewUrl(f)} target="_blank" rel="noopener">View</a></td>
		{/snippet}
	</DataTable>
</Spotlight>

<style>
	.uploader { display: grid; gap: .5rem; margin-bottom: var(--space-4); }
	.uploader-row { display: flex; gap: var(--space-3); align-items: center; }
	.upload-progress {
		display: flex; align-items: center; gap: var(--space-3);
		background: var(--panel-2); border-radius: 99px; padding: .35rem .35rem .35rem .1rem;
	}
	.upload-progress .bar { flex: 1 1 auto; height: 6px; border-radius: 99px; background: var(--accent); transition: width .2s var(--ease); margin-left: .25rem; }
	.upload-progress .hint { flex: 0 0 auto; padding-right: .5rem; white-space: nowrap; }
	.view {
		font-size: var(--text-sm); font-weight: 650; color: var(--accent-ink);
		border: 1px solid var(--line); border-radius: var(--r); padding: .3rem .7rem;
		text-decoration: none;
	}
	.view:hover { border-color: var(--accent); background: var(--accent-soft); }
</style>
