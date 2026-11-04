<script lang="ts">
	// specs/v8 §8.1 — a dedicated hero-level animated layer, separate from
	// app.css's existing site-wide ambient drift (body::before/::after):
	// a slow-moving particle/connection-line field suggesting the
	// knowledge-graph concept this product is actually about. Canvas, not
	// SVG/DOM nodes — same reasoning as GraphView's own rebuild (§7.4):
	// cheap, no per-element DOM cost, and it's purely decorative so there's
	// no interactivity to lose by not using the DOM.
	let { count = 46 }: { count?: number } = $props();

	let canvasEl = $state<HTMLCanvasElement>();
	let reduceMotion = false;

	function resize(el: HTMLDivElement) {
		const ro = new ResizeObserver(([entry]) => {
			if (!canvasEl) return;
			const dpr = window.devicePixelRatio || 1;
			canvasEl.width = entry.contentRect.width * dpr;
			canvasEl.height = entry.contentRect.height * dpr;
			canvasEl.style.width = `${entry.contentRect.width}px`;
			canvasEl.style.height = `${entry.contentRect.height}px`;
		});
		ro.observe(el);
		return { destroy() { ro.disconnect(); } };
	}

	$effect(() => {
		if (!canvasEl) return;
		reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		const ctx = canvasEl.getContext('2d');
		if (!ctx) return;

		const dpr = window.devicePixelRatio || 1;
		const pts = Array.from({ length: count }, () => ({
			x: Math.random(), y: Math.random(),
			vx: (Math.random() - 0.5) * 0.00018, vy: (Math.random() - 0.5) * 0.00018
		}));

		let raf = 0;
		function frame() {
			const w = canvasEl!.width, h = canvasEl!.height;
			ctx!.clearRect(0, 0, w, h);
			if (!reduceMotion) {
				for (const p of pts) {
					p.x += p.vx; p.y += p.vy;
					if (p.x < 0 || p.x > 1) p.vx *= -1;
					if (p.y < 0 || p.y > 1) p.vy *= -1;
				}
			}
			const px = pts.map((p) => ({ x: p.x * w, y: p.y * h }));
			const maxDist = Math.min(w, h) * 0.22;
			ctx!.lineWidth = 1 * dpr;
			for (let i = 0; i < px.length; i++) {
				for (let j = i + 1; j < px.length; j++) {
					const d = Math.hypot(px[i].x - px[j].x, px[i].y - px[j].y);
					if (d > maxDist) continue;
					ctx!.strokeStyle = `rgba(255, 185, 196, ${0.18 * (1 - d / maxDist)})`;
					ctx!.beginPath();
					ctx!.moveTo(px[i].x, px[i].y);
					ctx!.lineTo(px[j].x, px[j].y);
					ctx!.stroke();
				}
			}
			for (const p of px) {
				ctx!.beginPath();
				ctx!.arc(p.x, p.y, 1.6 * dpr, 0, Math.PI * 2);
				ctx!.fillStyle = 'rgba(255, 143, 163, .55)';
				ctx!.fill();
			}
			raf = reduceMotion ? 0 : requestAnimationFrame(frame);
		}
		frame();
		return () => { if (raf) cancelAnimationFrame(raf); };
	});
</script>

<div class="field" use:resize aria-hidden="true">
	<canvas bind:this={canvasEl}></canvas>
</div>

<style>
	.field { position: absolute; inset: 0; overflow: hidden; pointer-events: none; }
	canvas { display: block; }
</style>
