<script lang="ts">
	import { PUBLIC_API_BASE } from '$env/static/public';
	import ImageCropModal from './ImageCropModal.svelte';
	import Spinner from '$lib/components/Spinner.svelte';

	let {
		sources,
		onInsert,
		onCancel
	}: {
		sources: { document_id: string; title: string }[];
		onInsert: (blob: Blob, caption: string) => void;
		onCancel: () => void;
	} = $props();

	let activeSourceId = $state<string | null>(null);
	let loadingImages = $state(false);
	let images = $state<{ id: string; page: number; name: string }[]>([]);
	let error = $state('');
	let cropSrc = $state<string | null>(null);
	let cropCaption = $state('');

	async function pickSource(documentId: string) {
		activeSourceId = documentId;
		images = [];
		error = '';
		loadingImages = true;
		try {
			const res = await fetch(`${PUBLIC_API_BASE}/api/sources/${documentId}/images`, {
				credentials: 'include'
			});
			if (!res.ok) throw new Error('Could not read this source.');
			images = await res.json();
			if (!images.length) error = 'No chart or figure images found in this source.';
		} catch (err: any) {
			error = err?.message || 'Could not read this source.';
		} finally {
			loadingImages = false;
		}
	}

	async function pickImage(imageId: string, page: number) {
		if (!activeSourceId) return;
		const res = await fetch(`${PUBLIC_API_BASE}/api/sources/${activeSourceId}/images/${imageId}`, {
			credentials: 'include'
		});
		if (!res.ok) {
			error = 'Could not load that image.';
			return;
		}
		const blob = await res.blob();
		const title = sources.find((s) => s.document_id === activeSourceId)?.title ?? 'source';
		cropCaption = `${title} — p.${page}`;
		cropSrc = URL.createObjectURL(blob);
	}

	function onCropConfirm(blob: Blob) {
		onInsert(blob, cropCaption);
	}
</script>

{#if cropSrc}
	<ImageCropModal
		imageSrc={cropSrc}
		title="Crop {cropCaption}"
		onConfirm={onCropConfirm}
		onCancel={() => (cropSrc = null)}
	/>
{:else}
	<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
	<div class="backdrop" onclick={onCancel}>
		<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
		<div class="modal" onclick={(e) => e.stopPropagation()}>
			<div class="modal-head"><strong>Insert from source</strong></div>
			<div class="modal-body">
				{#if !activeSourceId}
					<p class="hint">Pick a source this consult already cited.</p>
					<ul class="source-list">
						{#each sources as s (s.document_id)}
							<li><button type="button" onclick={() => pickSource(s.document_id)}>{s.title}</button></li>
						{:else}
							<li class="hint">No sources cited yet in this consult.</li>
						{/each}
					</ul>
				{:else if loadingImages}
					<p class="hint"><Spinner size={14} /> Reading source…</p>
				{:else}
					<button type="button" class="back" onclick={() => (activeSourceId = null)}>← Back to sources</button>
					{#if error}<p class="hint error">{error}</p>{/if}
					<ul class="image-grid">
						{#each images as img (img.id)}
							<li>
								<button type="button" onclick={() => pickImage(img.id, img.page)}>
									Page {img.page} — {img.name}
								</button>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		</div>
	</div>
{/if}

<style>
	.backdrop {
		position: fixed; inset: 0; background: rgba(0, 0, 0, 0.45);
		display: flex; align-items: center; justify-content: center; z-index: 50;
	}
	.modal {
		background: var(--panel); border-radius: var(--r-lg); width: min(90vw, 32rem);
		max-height: 80vh; display: flex; flex-direction: column; overflow: hidden;
	}
	.modal-head { padding: var(--space-4); border-bottom: 1px solid var(--line); }
	.modal-body { padding: var(--space-4); overflow-y: auto; }
	.hint { color: var(--muted); font-size: var(--text-sm); }
	.hint.error { color: var(--danger); }
	.source-list, .image-grid { list-style: none; margin: var(--space-3) 0 0; padding: 0; display: grid; gap: .3rem; }
	.source-list button, .image-grid button {
		width: 100%; text-align: left; border: 1px solid var(--line); background: var(--panel-2);
		border-radius: var(--r); padding: .5rem .7rem; font: inherit; cursor: pointer;
	}
	.source-list button:hover, .image-grid button:hover { background: var(--accent-soft); }
	.back { border: none; background: none; color: var(--accent); font-size: var(--text-sm); font-weight: 600; cursor: pointer; padding: 0 0 var(--space-3); }
</style>
