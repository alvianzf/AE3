<script lang="ts">
	// A generic force-directed node-link view — used for both the
	// concept-graph and document/folder-graph layers of the admin
	// Library's Graph tab (specs/v6.13). Deliberately hand-rolled on
	// d3-force/d3-drag/d3-zoom/d3-selection/d3-transition (the physics/
	// interaction primitives only) rather than a wrapper graph library
	// (force-graph, cytoscape, ...) — those pull in a canvas renderer
	// and styling opinions of their own plus a much larger transitive
	// dependency tree (lodash, tween.js, bezier-js, ...) for a feature
	// this app only needs at this one spot; five focused d3 modules is
	// a smaller, more inspectable dependency than one wrapper around
	// them.
	import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force';
	import { select } from 'd3-selection';
	import { drag, type D3DragEvent } from 'd3-drag';
	import { zoom, zoomIdentity, type D3ZoomEvent } from 'd3-zoom';
	// Side-effect import, not referenced by name — attaches .transition()
	// onto d3-selection's Selection prototype (and its TS types), used
	// by fitToView() below for a smooth pan/zoom instead of a snap-cut.
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

	let svgEl = $state<SVGSVGElement>();
	let rootGroup = $state<SVGGElement>();
	let width = $state(800);
	let height = $state(560);
	let zoomScale = $state(1);
	let hoveredId = $state<string | null>(null);

	// $state, not a plain array — d3-force writes x/y/vx/vy directly onto
	// each node every tick, and $state's proxy makes that in-place
	// mutation reactive on its own (each #each block below re-renders
	// its one changed node/edge, not the whole list), without a manual
	// "something changed" counter to force it.
	let simNodes = $state<(GraphNode & { x?: number; y?: number; fx?: number | null; fy?: number | null })[]>([]);
	let simEdges = $state<any[]>([]);

	// Labels are the single heaviest thing rendered here (stroke-outlined
	// text — expensive to rasterize — at up to ~150 nodes for the
	// concept layer) — found live: "graph is really heavy on the
	// browser." Past a node-count threshold, only show a label while
	// zoomed in enough to actually read it, or on hover — not for every
	// node on every frame regardless of whether it's legible or even
	// visible at the current zoom level. Small graphs (the common case
	// for the document/folder layer) always show every label; nothing
	// about this path is worth hiding at that size.
	const labelsAlwaysOn = $derived(simNodes.length <= 60);
	function showLabel(n: any): boolean {
		return labelsAlwaysOn || zoomScale > 0.8 || hoveredId === n.id;
	}

	const COLORS: Record<string, string> = {
		folder: 'var(--accent)',
		document: 'var(--ink)'
	};
	// The concept layer's `group` is an entity type straight from the
	// KG-builder (Symptom, Treatment, hormone, ...) — an open,
	// unbounded set, not a fixed enum worth hardcoding. Found in
	// review: every such node fell through to the same `var(--muted)`
	// fallback, so the one feature meant to show a *typed* graph
	// rendered as an undifferentiated gray cloud, distinguishable only
	// by circle size. A fixed palette assigned in sorted order (stable
	// across reloads — not hashed, which would've worked but reads as
	// arbitrary noise instead of a legend an admin can actually learn)
	// covers it, with a legend below listing which type got which
	// color.
	const PALETTE = [
		'#c0392b', '#2980b9', '#27ae60', '#8e44ad', '#d68910',
		'#16a085', '#2c3e50', '#e67e22', '#2471a3', '#935116'
	];
	const paletteColors = $derived.by(() => {
		const groups = [...new Set(nodes.map((n) => n.group).filter((g): g is string => !!g && !(g in COLORS)))].sort();
		return new Map(groups.map((g, i) => [g, PALETTE[i % PALETTE.length]]));
	});
	function colorFor(group?: string): string {
		if (!group) return 'var(--muted)';
		return COLORS[group] ?? paletteColors.get(group) ?? 'var(--muted)';
	}

	let simulation: ReturnType<typeof forceSimulation> | null = null;
	let zoomBehavior: ReturnType<typeof zoom<SVGSVGElement, unknown>> | null = null;

	// Centers and scales the view to fit every current node, with
	// padding — forceCenter() only pulls the *center of mass* toward
	// width/2,height/2, it doesn't guarantee the whole (possibly much
	// wider, after forceManyBody's repulsion spreads things out) graph
	// actually fits inside the viewport at zoom 1:1. Without this, a
	// bigger graph (concepts: 150 nodes, ~2900 edges) just ran off the
	// edges at whatever random scale it happened to land at — "a mess"
	// (found live, 2026-11-04).
	function fitToView() {
		if (!svgEl || !zoomBehavior || !simNodes.length) return;
		const pad = 40;
		const xs = simNodes.map((n) => n.x ?? 0);
		const ys = simNodes.map((n) => n.y ?? 0);
		const x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad;
		const y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad;
		const w = Math.max(1, x1 - x0), h = Math.max(1, y1 - y0);
		const scale = Math.min(2, width / w, height / h);
		const tx = width / 2 - scale * (x0 + w / 2);
		const ty = height / 2 - scale * (y0 + h / 2);
		select(svgEl)
			.transition().duration(250)
			.call(zoomBehavior.transform, zoomIdentity.translate(tx, ty).scale(scale));
	}

	$effect(() => {
		// Re-reads whenever `nodes`/`edges` props change identity (a new
		// layer selected, or a refetch) — re-creating the simulation from
		// scratch each time rather than trying to reconcile two node
		// sets is far simpler and the datasets here (at most ~150
		// concepts, or a folder tree) settle in well under a second.
		simNodes = nodes.map((n) => ({ ...n }));
		const byId = new Map(simNodes.map((n) => [n.id, n]));
		simEdges = edges
			.filter((e) => byId.has(e.source) && byId.has(e.target))
			.map((e) => ({ ...e }));

		// Only the simulation's first settle (the initial layout) should
		// recenter the view — a later 'end' (the simulation re-heats to
		// alphaTarget 0.3 on every node drag, per dragNode() below, then
		// cools back down once released) must NOT re-trigger this, or
		// releasing a dragged node would silently reset whatever pan/zoom
		// the admin had set.
		let fitted = false;
		simulation?.stop();
		simulation = forceSimulation(simNodes as any)
			.force('link', forceLink(simEdges).id((d: any) => d.id).distance(70).strength(0.4))
			.force('charge', forceManyBody().strength(-140))
			.force('center', forceCenter(width / 2, height / 2))
			.force('collide', forceCollide().radius((d: any) => (d.size ?? 6) + 10))
			.on('end', () => { if (!fitted) { fitted = true; fitToView(); } });

		// Pre-settle synchronously (d3-force's own default settling time,
		// ~300 ticks at the default alphaDecay) before the first paint —
		// without this, the initial random starting positions and a
		// strong charge force produce a visibly chaotic expansion on
		// every layer switch, not just an unfit one. This does NOT mark
		// `fitted` itself (found in review: it used to, unconditionally
		// — for a graph that genuinely needs more than 300 ticks, e.g.
		// the ~150-node/~2900-edge concept layer, that skipped the real
		// 'end' handler above forever, leaving the view fit to
		// still-unsettled positions — the exact "ran off the edges" bug
		// this was supposed to fix). This call is just an immediate,
		// best-effort first paint; the `on('end', ...)` handler above
		// still fires the real, guarded fit once the simulation actually
		// converges, whether that's on the very next frame (already
		// converged within the 300 ticks) or later.
		for (let i = 0; i < 300 && (simulation.alpha() ?? 0) > simulation.alphaMin(); i++) simulation.tick();
		fitToView();

		return () => simulation?.stop();
	});

	$effect(() => {
		if (!svgEl || !rootGroup) return;
		zoomBehavior = zoom<SVGSVGElement, unknown>()
			.scaleExtent([0.1, 4])
			.on('zoom', (e: D3ZoomEvent<SVGSVGElement, unknown>) => {
				select(rootGroup!).attr('transform', e.transform.toString());
				zoomScale = e.transform.k;
			});
		select(svgEl).call(zoomBehavior);
		fitToView();
	});

	// Explicit +/-/reset controls, not just implicit wheel-to-zoom/drag-
	// to-pan — found live ("needs to be scrollable and interactive"):
	// wheel-zooms alone weren't a visible enough affordance that this
	// graph is a navigable thing, not a static image.
	function zoomBy(factor: number) {
		if (!svgEl || !zoomBehavior) return;
		select(svgEl).transition().duration(200).call(zoomBehavior.scaleBy, factor);
	}
	function resetView() {
		fitToView();
	}

	function dragNode(el: SVGGElement, node: any) {
		select(el).call(
			drag<SVGGElement, unknown>()
				.on('start', (e: D3DragEvent<SVGGElement, unknown, unknown>) => {
					if (!e.active) simulation?.alphaTarget(0.3).restart();
					node.fx = node.x;
					node.fy = node.y;
				})
				.on('drag', (e: D3DragEvent<SVGGElement, unknown, unknown>) => {
					node.fx = e.x;
					node.fy = e.y;
				})
				.on('end', (e: D3DragEvent<SVGGElement, unknown, unknown>) => {
					if (!e.active) simulation?.alphaTarget(0);
					node.fx = null;
					node.fy = null;
				}) as any
		);
		return {
			destroy() {
				select(el).on('.drag', null);
			}
		};
	}

	function resize(el: HTMLDivElement) {
		const ro = new ResizeObserver(([entry]) => {
			width = entry.contentRect.width || width;
			height = Math.max(360, entry.contentRect.height || height);
			simulation?.force('center', forceCenter(width / 2, height / 2));
		});
		ro.observe(el);
		return { destroy() { ro.disconnect(); } };
	}
</script>

<div class="graph-wrap" use:resize>
	{#if !nodes.length}
		<p class="hint">Nothing to show yet.</p>
	{:else}
		<div class="zoom-controls" role="group" aria-label="Zoom">
			<button type="button" onclick={() => zoomBy(1.4)} title="Zoom in" aria-label="Zoom in">+</button>
			<button type="button" onclick={() => zoomBy(1 / 1.4)} title="Zoom out" aria-label="Zoom out">&minus;</button>
			<button type="button" onclick={resetView} title="Reset view" aria-label="Reset view">⤢</button>
		</div>
		<svg bind:this={svgEl} {width} {height} role="img" aria-label="Graph view">
			<g bind:this={rootGroup}>
				{#each simEdges as e (e.source.id ?? e.source)}
					<line
						x1={(e.source as any).x} y1={(e.source as any).y}
						x2={(e.target as any).x} y2={(e.target as any).y}
						class="edge"
					/>
				{/each}
				{#each simNodes as n (n.id)}
					<g
						class="node"
						transform="translate({n.x ?? 0},{n.y ?? 0})"
						use:dragNode={n}
						onclick={() => onNodeClick?.(n)}
						onmouseenter={() => (hoveredId = n.id)}
						onmouseleave={() => (hoveredId = null)}
						role="button"
						tabindex="0"
						onkeydown={(e: KeyboardEvent) => { if (e.key === 'Enter') onNodeClick?.(n); }}
					>
						<circle r={n.size ?? 6} fill={colorFor(n.group)} />
						{#if showLabel(n)}
							<text dy={-((n.size ?? 6) + 4)}>{n.label}</text>
						{/if}
					</g>
				{/each}
			</g>
		</svg>
		{#if paletteColors.size}
			<!-- Only the open-ended entity-type palette gets a legend —
			     the document/folder layer's two groups are already
			     self-explanatory from the node's own icon-less shape and
			     label, not worth a swatch each. -->
			<div class="legend">
				{#each [...paletteColors] as [group, color] (group)}
					<span class="legend-item"><span class="swatch" style="background: {color}"></span>{group}</span>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.graph-wrap { position: relative; width: 100%; min-height: 360px; max-height: 70vh; border: 1px solid var(--line); border-radius: var(--r-lg); overflow: auto; background: var(--panel); }
	svg { display: block; cursor: grab; touch-action: none; }
	.zoom-controls {
		position: absolute; top: .6rem; right: .6rem; z-index: 1; display: flex; flex-direction: column; gap: .2rem;
		border: 1px solid var(--line); border-radius: var(--r); background: var(--panel); box-shadow: var(--shadow);
	}
	.zoom-controls button {
		width: 1.8rem; height: 1.8rem; border: none; background: none; cursor: pointer;
		font-size: 1.1rem; line-height: 1; color: var(--ink); display: flex; align-items: center; justify-content: center;
	}
	.zoom-controls button:hover { background: var(--panel-2); }
	/* var(--line-2) at 1px (the first version of this) was functionally
	   invisible — a pale tan-gray (#d9d4cc) 1px line on a white panel,
	   found live: "why does the graph view not have any connecting
	   dots/lines?" The edges were always there (every node always gets
	   one, per documentGraph/concept_graph's own construction) — they
	   just didn't render visibly. */
	.edge { stroke: var(--muted); stroke-width: 1.2; opacity: .5; }
	.node { cursor: pointer; }
	.node circle { stroke: var(--panel); stroke-width: 1.5; }
	.node text {
		font-size: 10px; fill: var(--muted); text-anchor: middle; pointer-events: none;
		paint-order: stroke; stroke: var(--panel); stroke-width: 3px;
	}
	.node:hover circle { stroke: var(--accent); }
	.node:hover text { fill: var(--ink); }
	.legend {
		display: flex; flex-wrap: wrap; gap: .3rem .9rem; padding: .6rem .8rem;
		border-top: 1px solid var(--line); font-size: var(--text-xs); color: var(--muted);
	}
	.legend-item { display: inline-flex; align-items: center; gap: .35rem; }
	.swatch { width: .6rem; height: .6rem; border-radius: 50%; flex: 0 0 auto; }
</style>
