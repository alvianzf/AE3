<script lang="ts">
	// specs/v8/README.md §7.4 — canvas rebuild. The SVG version's real cost
	// (found live, v6.18) was DOM node count times stroke-outlined <text>
	// paint at scale (~150 concept nodes, ~2900 edges) — conditionally
	// hiding labels only reduced that cost, it couldn't remove it, because
	// every node was still a DOM element regardless of whether its label
	// painted. A canvas redraw touches zero DOM nodes no matter how big the
	// graph is — this removes the cost structurally instead of managing it.
	// Still d3-force for physics (not a wrapper graph library — same
	// dependency-weight reasoning as before, now just targeting a <canvas>
	// 2D context for the draw step instead of the DOM for both).
	import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force';
	import { zoom, zoomIdentity, type D3ZoomEvent } from 'd3-zoom';
	import { select } from 'd3-selection';
	// Side-effect import, not referenced by name — attaches .transition()
	// onto d3-selection's Selection prototype (and its TS types), used by
	// fitToView()/zoomBy() below for a smooth pan/zoom instead of a snap-cut.
	import 'd3-transition';

	export interface GraphNode {
		id: string;
		label: string;
		group?: string;
		size?: number;
	}
	export interface GraphEdge {
		source: string;
		target: string;
		label?: string;
	}

	let {
		nodes,
		edges,
		onNodeClick
	}: {
		nodes: GraphNode[];
		edges: GraphEdge[];
		onNodeClick?: (node: GraphNode) => void;
	} = $props();

	let canvasEl = $state<HTMLCanvasElement>();
	let wrapEl = $state<HTMLDivElement>();
	let width = $state(800);
	let height = $state(560);
	let dpr = typeof window !== 'undefined' ? (window.devicePixelRatio || 1) : 1;
	let hoveredId = $state<string | null>(null);
	let transform = zoomIdentity;

	type SimNode = GraphNode & { x?: number; y?: number; vx?: number; vy?: number; fx?: number | null; fy?: number | null };
	let simNodes: SimNode[] = [];
	let simEdges: any[] = [];

	// No label budget to tune any more — labels are opt-in, not
	// conditionally computed over the whole node set every frame (§7.4):
	// drawn for a node only on hover, or for every node when the graph is
	// small enough (<=20) that painting them all costs nothing.
	const labelsAlwaysOn = $derived(nodes.length <= 20);

	const COLORS: Record<string, string> = {
		folder: '#9c3f5a',
		document: '#221f1b'
	};
	const PALETTE = [
		'#c0392b', '#2980b9', '#27ae60', '#8e44ad', '#d68910',
		'#16a085', '#2c3e50', '#e67e22', '#2471a3', '#935116'
	];
	const paletteColors = $derived.by(() => {
		const groups = [...new Set(nodes.map((n) => n.group).filter((g): g is string => !!g && !(g in COLORS)))].sort();
		return new Map(groups.map((g, i) => [g, PALETTE[i % PALETTE.length]]));
	});
	function colorFor(group?: string): string {
		if (!group) return '#7d766c';
		return COLORS[group] ?? paletteColors.get(group) ?? '#7d766c';
	}

	let simulation: ReturnType<typeof forceSimulation> | null = null;
	let zoomBehavior: ReturnType<typeof zoom<HTMLCanvasElement, unknown>> | null = null;
	let rafQueued = false;

	function scheduleDraw() {
		if (rafQueued) return;
		rafQueued = true;
		requestAnimationFrame(() => {
			rafQueued = false;
			draw();
		});
	}

	function draw() {
		const ctx = canvasEl?.getContext('2d');
		if (!ctx) return;
		ctx.save();
		ctx.clearRect(0, 0, width * dpr, height * dpr);
		ctx.scale(dpr, dpr);
		ctx.translate(transform.x, transform.y);
		ctx.scale(transform.k, transform.k);

		ctx.strokeStyle = 'rgba(125, 118, 108, .45)';
		ctx.lineWidth = 1.2 / transform.k;
		ctx.beginPath();
		for (const e of simEdges) {
			const s = e.source as SimNode, t = e.target as SimNode;
			if (s.x == null || t.x == null) continue;
			ctx.moveTo(s.x, s.y!);
			ctx.lineTo(t.x, t.y!);
		}
		ctx.stroke();

		const showAllLabels = labelsAlwaysOn || transform.k > 1.6;
		for (const n of simNodes) {
			if (n.x == null) continue;
			const r = n.size ?? 6;
			ctx.beginPath();
			ctx.arc(n.x, n.y!, r, 0, Math.PI * 2);
			ctx.fillStyle = colorFor(n.group);
			ctx.fill();
			if (hoveredId === n.id) {
				ctx.lineWidth = 1.5 / transform.k;
				ctx.strokeStyle = '#9c3f5a';
				ctx.stroke();
			}
			if (showAllLabels || hoveredId === n.id) {
				ctx.font = `${10 / transform.k}px ui-sans-serif, system-ui, sans-serif`;
				ctx.textAlign = 'center';
				ctx.fillStyle = '#fff';
				ctx.lineWidth = 3 / transform.k;
				ctx.strokeStyle = '#fff';
				ctx.lineJoin = 'round';
				ctx.strokeText(n.label, n.x, n.y! - r - 4);
				ctx.fillStyle = '#4a453e';
				ctx.fillText(n.label, n.x, n.y! - r - 4);
			}
		}
		ctx.restore();
	}

	function fitToView() {
		if (!canvasEl || !zoomBehavior || !simNodes.length) return;
		const pad = 40;
		const xs = simNodes.map((n) => n.x ?? 0);
		const ys = simNodes.map((n) => n.y ?? 0);
		const x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad;
		const y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad;
		const w = Math.max(1, x1 - x0), h = Math.max(1, y1 - y0);
		const scale = Math.min(2, width / w, height / h);
		const tx = width / 2 - scale * (x0 + w / 2);
		const ty = height / 2 - scale * (y0 + h / 2);
		select(canvasEl)
			.transition().duration(250)
			.call(zoomBehavior.transform as any, zoomIdentity.translate(tx, ty).scale(scale));
	}

	function nodeAt(px: number, py: number): SimNode | null {
		const x = (px - transform.x) / transform.k;
		const y = (py - transform.y) / transform.k;
		let best: SimNode | null = null, bestDist = Infinity;
		for (const n of simNodes) {
			if (n.x == null) continue;
			const r = (n.size ?? 6) + 4;
			const d = Math.hypot(n.x - x, n.y! - y);
			if (d <= r && d < bestDist) { best = n; bestDist = d; }
		}
		return best;
	}

	let dragging: SimNode | null = null;

	function onPointerDown(e: PointerEvent) {
		const rect = canvasEl!.getBoundingClientRect();
		const hit = nodeAt(e.clientX - rect.left, e.clientY - rect.top);
		if (hit) {
			dragging = hit;
			dragging.fx = dragging.x;
			dragging.fy = dragging.y;
			simulation?.alphaTarget(0.3).restart();
			canvasEl!.setPointerCapture(e.pointerId);
		}
	}
	function onPointerMove(e: PointerEvent) {
		const rect = canvasEl!.getBoundingClientRect();
		const px = e.clientX - rect.left, py = e.clientY - rect.top;
		if (dragging) {
			dragging.fx = (px - transform.x) / transform.k;
			dragging.fy = (py - transform.y) / transform.k;
			scheduleDraw();
			return;
		}
		const hit = nodeAt(px, py);
		const nextHovered = hit?.id ?? null;
		if (nextHovered !== hoveredId) {
			hoveredId = nextHovered;
			canvasEl!.style.cursor = hit ? 'pointer' : 'grab';
			scheduleDraw();
		}
	}
	function onPointerUp(e: PointerEvent) {
		if (dragging) {
			dragging.fx = null;
			dragging.fy = null;
			simulation?.alphaTarget(0);
			dragging = null;
			canvasEl!.releasePointerCapture(e.pointerId);
			return;
		}
		const rect = canvasEl!.getBoundingClientRect();
		const hit = nodeAt(e.clientX - rect.left, e.clientY - rect.top);
		if (hit) onNodeClick?.(hit);
	}

	function zoomBy(factor: number) {
		if (!canvasEl || !zoomBehavior) return;
		select(canvasEl).transition().duration(200).call(zoomBehavior.scaleBy as any, factor);
	}
	function resetView() { fitToView(); }

	$effect(() => {
		simNodes = nodes.map((n) => ({ ...n }));
		const byId = new Map(simNodes.map((n) => [n.id, n]));
		simEdges = edges
			.filter((e) => byId.has(e.source) && byId.has(e.target))
			.map((e) => ({ ...e }));

		let fitted = false;
		simulation?.stop();
		simulation = forceSimulation(simNodes as any)
			.force('link', forceLink(simEdges).id((d: any) => d.id).distance(70).strength(0.4))
			.force('charge', forceManyBody().strength(-140))
			.force('center', forceCenter(width / 2, height / 2))
			.force('collide', forceCollide().radius((d: any) => (d.size ?? 6) + 10))
			.on('tick', scheduleDraw)
			.on('end', () => { if (!fitted) { fitted = true; fitToView(); } });

		for (let i = 0; i < 300 && (simulation.alpha() ?? 0) > simulation.alphaMin(); i++) simulation.tick();
		fitToView();
		scheduleDraw();

		return () => simulation?.stop();
	});

	$effect(() => {
		if (!canvasEl) return;
		zoomBehavior = zoom<HTMLCanvasElement, unknown>()
			.scaleExtent([0.1, 4])
			.filter((e: any) => !dragging && !e.target.closest?.('button'))
			.on('zoom', (e: D3ZoomEvent<HTMLCanvasElement, unknown>) => {
				transform = e.transform;
				scheduleDraw();
			});
		select(canvasEl).call(zoomBehavior);
		fitToView();
	});

	function resize(el: HTMLDivElement) {
		const ro = new ResizeObserver(([entry]) => {
			width = entry.contentRect.width || width;
			height = Math.max(360, entry.contentRect.height || height);
			simulation?.force('center', forceCenter(width / 2, height / 2));
			scheduleDraw();
		});
		ro.observe(el);
		return { destroy() { ro.disconnect(); } };
	}
</script>

<div class="graph-wrap" bind:this={wrapEl} use:resize>
	{#if !nodes.length}
		<p class="hint">Nothing to show yet.</p>
	{:else}
		<div class="zoom-controls" role="group" aria-label="Zoom">
			<button type="button" onclick={() => zoomBy(1.4)} title="Zoom in" aria-label="Zoom in">+</button>
			<button type="button" onclick={() => zoomBy(1 / 1.4)} title="Zoom out" aria-label="Zoom out">&minus;</button>
			<button type="button" onclick={resetView} title="Reset view" aria-label="Reset view">⤢</button>
		</div>
		<canvas
			bind:this={canvasEl}
			width={width * dpr}
			height={height * dpr}
			style="width: {width}px; height: {height}px;"
			aria-label="Graph view"
			onpointerdown={onPointerDown}
			onpointermove={onPointerMove}
			onpointerup={onPointerUp}
			onpointerleave={() => { if (!dragging) { hoveredId = null; scheduleDraw(); } }}
		></canvas>
		{#if paletteColors.size}
			<div class="legend">
				{#each [...paletteColors] as [group, color] (group)}
					<span class="legend-item"><span class="swatch" style="background: {color}"></span>{group}</span>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.graph-wrap { position: relative; width: 100%; min-height: 360px; max-height: 70vh; border: 1px solid var(--line); border-radius: var(--r-lg); overflow: hidden; background: var(--panel); }
	canvas { display: block; cursor: grab; touch-action: none; }
	.zoom-controls {
		position: absolute; top: .6rem; right: .6rem; z-index: 1; display: flex; flex-direction: column; gap: .2rem;
		border: 1px solid var(--line); border-radius: var(--r); background: var(--panel); box-shadow: var(--shadow);
	}
	.zoom-controls button {
		width: 1.8rem; height: 1.8rem; border: none; background: none; cursor: pointer;
		font-size: 1.1rem; line-height: 1; color: var(--ink); display: flex; align-items: center; justify-content: center;
	}
	.zoom-controls button:hover { background: var(--panel-2); }
	.legend {
		position: absolute; bottom: 0; left: 0; right: 0;
		display: flex; flex-wrap: wrap; gap: .3rem .9rem; padding: .6rem .8rem;
		border-top: 1px solid var(--line); background: var(--panel);
		font-size: var(--text-xs); color: var(--muted);
	}
	.legend-item { display: inline-flex; align-items: center; gap: .35rem; }
	.swatch { width: .6rem; height: .6rem; border-radius: 50%; flex: 0 0 auto; }
	.hint { color: var(--muted); font-size: var(--text-sm); padding: var(--space-4); }
</style>
