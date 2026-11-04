<script lang="ts">
	// A generic force-directed node-link view — used for both the
	// concept-graph and document/folder-graph layers of the admin
	// Library's Graph tab (specs/v6.13). Deliberately hand-rolled on
	// d3-force/d3-drag/d3-zoom/d3-selection (the physics/interaction
	// primitives only) rather than a wrapper graph library (force-graph,
	// cytoscape, ...) — those pull in a canvas renderer and styling
	// opinions of their own plus a much larger transitive dependency
	// tree (lodash, tween.js, bezier-js, ...) for a feature this app
	// only needs at this one spot; four focused d3 modules is a smaller,
	// more inspectable dependency than one wrapper around them.
	import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force';
	import { select } from 'd3-selection';
	import { drag, type D3DragEvent } from 'd3-drag';
	import { zoom, zoomIdentity, type D3ZoomEvent } from 'd3-zoom';

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

	// $state, not a plain array — d3-force writes x/y/vx/vy directly onto
	// each node every tick, and $state's proxy makes that in-place
	// mutation reactive on its own (each #each block below re-renders
	// its one changed node/edge, not the whole list), without a manual
	// "something changed" counter to force it.
	let simNodes = $state<(GraphNode & { x?: number; y?: number; fx?: number | null; fy?: number | null })[]>([]);
	let simEdges = $state<any[]>([]);

	const COLORS: Record<string, string> = {
		folder: 'var(--accent)',
		document: 'var(--ink)'
	};
	function colorFor(group?: string): string {
		return COLORS[group ?? ''] ?? 'var(--muted)';
	}

	let simulation: ReturnType<typeof forceSimulation> | null = null;

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

		simulation?.stop();
		simulation = forceSimulation(simNodes as any)
			.force('link', forceLink(simEdges).id((d: any) => d.id).distance(70).strength(0.4))
			.force('charge', forceManyBody().strength(-140))
			.force('center', forceCenter(width / 2, height / 2))
			.force('collide', forceCollide().radius((d: any) => (d.size ?? 6) + 10));

		return () => simulation?.stop();
	});

	$effect(() => {
		if (!svgEl || !rootGroup) return;
		const zoomBehavior = zoom<SVGSVGElement, unknown>()
			.scaleExtent([0.2, 4])
			.on('zoom', (e: D3ZoomEvent<SVGSVGElement, unknown>) => {
				select(rootGroup!).attr('transform', e.transform.toString());
			});
		select(svgEl).call(zoomBehavior).call(zoomBehavior.transform, zoomIdentity);
	});

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
						role="button"
						tabindex="0"
						onkeydown={(e: KeyboardEvent) => { if (e.key === 'Enter') onNodeClick?.(n); }}
					>
						<circle r={n.size ?? 6} fill={colorFor(n.group)} />
						<text dy={-((n.size ?? 6) + 4)}>{n.label}</text>
					</g>
				{/each}
			</g>
		</svg>
	{/if}
</div>

<style>
	.graph-wrap { width: 100%; min-height: 360px; border: 1px solid var(--line); border-radius: var(--r-lg); overflow: hidden; background: var(--panel); }
	svg { display: block; cursor: grab; }
	.edge { stroke: var(--line-2); stroke-width: 1; }
	.node { cursor: pointer; }
	.node circle { stroke: var(--panel); stroke-width: 1.5; }
	.node text {
		font-size: 10px; fill: var(--muted); text-anchor: middle; pointer-events: none;
		paint-order: stroke; stroke: var(--panel); stroke-width: 3px;
	}
	.node:hover circle { stroke: var(--accent); }
	.node:hover text { fill: var(--ink); }
</style>
