<script lang="ts">
	import Cropper from 'cropperjs';
	import Button from '$lib/components/Button.svelte';

	let {
		imageSrc,
		title = 'Crop image',
		onConfirm,
		onCancel
	}: {
		imageSrc: string;
		title?: string;
		onConfirm: (blob: Blob) => void;
		onCancel: () => void;
	} = $props();

	let imgEl: HTMLImageElement | undefined = $state();
	let cropper: Cropper | undefined;
	let working = $state(false);

	function onImgLoad() {
		if (!imgEl) return;
		cropper?.destroy();
		cropper = new Cropper(imgEl);
	}

	async function confirm() {
		const selection = cropper?.getCropperSelection();
		if (!selection) return;
		working = true;
		try {
			const canvas = await selection.$toCanvas();
			canvas.toBlob((blob) => {
				working = false;
				if (blob) onConfirm(blob);
			}, 'image/png');
		} catch {
			working = false;
		}
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="backdrop" onclick={onCancel}>
	<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
	<div class="modal" onclick={(e) => e.stopPropagation()}>
		<div class="modal-head"><strong>{title}</strong></div>
		<div class="crop-stage">
			<!-- eslint-disable-next-line svelte/no-unused-svelte-ignore -->
			<img bind:this={imgEl} src={imageSrc} alt="Crop source" onload={onImgLoad} crossorigin="anonymous" />
		</div>
		<div class="modal-actions">
			<Button variant="ghost" onclick={onCancel}>Cancel</Button>
			<Button loading={working} onclick={confirm}>Insert</Button>
		</div>
	</div>
</div>

<style>
	.backdrop {
		position: fixed; inset: 0; background: rgba(0, 0, 0, 0.45);
		display: flex; align-items: center; justify-content: center; z-index: 50;
	}
	.modal {
		background: var(--panel); border-radius: var(--r-lg); width: min(90vw, 44rem);
		max-height: 85vh; display: flex; flex-direction: column; overflow: hidden;
	}
	.modal-head { padding: var(--space-4); border-bottom: 1px solid var(--line); }
	.crop-stage { flex: 1 1 auto; min-height: 20rem; background: var(--ink); display: flex; }
	.crop-stage img { max-width: 100%; max-height: 60vh; margin: auto; display: block; }
	.modal-actions { display: flex; justify-content: flex-end; gap: var(--space-3); padding: var(--space-4); border-top: 1px solid var(--line); }
</style>
