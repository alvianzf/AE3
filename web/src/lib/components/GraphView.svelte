<script lang="ts">
	// specs/v8 §7.4 & v15 graph refinement — Canvas-based concept graph viewer
	// with connected component separation, context map (interactive minimap & HUD),
	// closest-connected-node highlighting, and uncluttered multi-graph spacing.
	import { forceSimulation, forceLink, forceManyBody, forceCollide, forceX, forceY } from 'd3-force';
	import { zoom, zoomIdentity, type D3ZoomEvent } from 'd3-zoom';
	import { select } from 'd3-selection';
	import 'd3-transition';
	import Icon from './Icon.svelte';

	export interface GraphNode {
		id: string;
		label: string;
		group?: string;
		size?: number;
		degree?: number;
		mentions?: number;
		documents?: number;
		dataScore?: number;
		[key: string]: any;
	}

	/**
	 * Computes dynamic node radius based on the volume of data the concept holds.
	 * Default node size is 2.4px (reduced by 60% from the previous default of 6.0px).
	 * The more data it holds (mentions in text, relationships, documents), the larger it is;
	 * vice versa, concepts holding less data scale smoothly down to the 2.4px default.
	 */
	export function calcNodeRadius(node: { size?: number; mentions?: number; degree?: number; documents?: number; dataScore?: number }): number {
		if (typeof node.size === 'number' && !isNaN(node.size)) {
			return node.size;
		}
		const mentions = Number(node.mentions ?? 0);
		const degree = Number(node.degree ?? 0);
		const documents = Number(node.documents ?? 0);
		const score = Number(node.dataScore ?? (mentions + degree + documents));
		// Default radius = 2.4px (60% smaller than 6.0px baseline)
		return 2.4 + Math.min(28, Math.pow(Math.max(0, score - 1), 0.55) * 1.6);
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
	let minimapCanvasEl = $state<HTMLCanvasElement>();
	let wrapEl = $state<HTMLDivElement>();
	let width = $state(800);
	let height = $state(560);
	let dpr = typeof window !== 'undefined' ? (window.devicePixelRatio || 1) : 1;
	let transform = zoomIdentity;

	let hoveredId = $state<string | null>(null);
	let selectedNodeId = $state<string | null>(null);
	let searchFilter = $state('');
	let searchFocused = $state(false);
	let minimapOpen = $state(true);
	let clusterCount = $state(0);

	const minimapWidth = 170;
	const minimapHeight = 115;

	type SimNode = GraphNode & {
		x?: number;
		y?: number;
		vx?: number;
		vy?: number;
		fx?: number | null;
		fy?: number | null;
		componentId?: number;
		targetX?: number;
		targetY?: number;
		_isNeighbor?: boolean;
	};

	let simNodes: SimNode[] = [];
	let simEdges: any[] = [];

	interface Component {
		id: number;
		nodeIds: Set<string>;
		nodes: SimNode[];
		cx: number;
		cy: number;
		radius: number;
	}
	let components: Component[] = [];

	const activeId = $derived(hoveredId ?? selectedNodeId ?? null);
	const activeNode = $derived(activeId ? nodes.find((n) => n.id === activeId) ?? null : null);

	// Closest connected neighbors (1-hop)
	const activeNeighborhood = $derived.by(() => {
		if (!activeId) {
			return {
				closestNodeIds: new Set<string>(),
				neighbors: [] as Array<{ node: GraphNode; rel: string; isSource: boolean }>,
				connectedEdgeKeys: new Set<string>()
			};
		}
		const nodeMap = new Map(nodes.map((n) => [n.id, n]));
		const closestNodeIds = new Set<string>([activeId]);
		const neighbors: Array<{ node: GraphNode; rel: string; isSource: boolean }> = [];
		const connectedEdgeKeys = new Set<string>();

		for (const e of edges) {
			if (e.source === activeId) {
				closestNodeIds.add(e.target);
				connectedEdgeKeys.add(`${e.source}->${e.target}`);
				const targetNode = nodeMap.get(e.target);
				if (targetNode) neighbors.push({ node: targetNode, rel: e.label || 'CONNECTED_TO', isSource: true });
			} else if (e.target === activeId) {
				closestNodeIds.add(e.source);
				connectedEdgeKeys.add(`${e.source}->${e.target}`);
				const sourceNode = nodeMap.get(e.source);
				if (sourceNode) neighbors.push({ node: sourceNode, rel: e.label || 'CONNECTED_TO', isSource: false });
			}
		}

		neighbors.sort((a, b) => a.node.label.localeCompare(b.node.label));
		return { closestNodeIds, neighbors, connectedEdgeKeys };
	});

	const labelsAlwaysOn = $derived(nodes.length <= 25);

	const COLORS: Record<string, string> = {
		folder: '#9c3f5a',
		document: '#221f1b',
		Biomarker: '#27ae60',
		Condition: '#c0392b',
		Intervention: '#2980b9',
		Pathway: '#8e44ad',
		Nutrient: '#d68910',
		Symptom: '#e67e22',
		Organ: '#16a085',
		Mechanism: '#2c3e50'
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
			drawMinimap();
		});
	}

	function getGraphBounds() {
		if (!simNodes.length) return { minX: 0, maxX: width, minY: 0, maxY: height, w: width, h: height };
		let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
		for (const n of simNodes) {
			if (n.x == null || n.y == null || isNaN(n.x) || isNaN(n.y)) continue;
			if (n.x < minX) minX = n.x;
			if (n.x > maxX) maxX = n.x;
			if (n.y < minY) minY = n.y;
			if (n.y > maxY) maxY = n.y;
		}
		if (minX === Infinity) return { minX: 0, maxX: width, minY: 0, maxY: height, w: width, h: height };
		const pad = 140;
		minX -= pad; maxX += pad; minY -= pad; maxY += pad;
		const w = Math.max(10, maxX - minX);
		const h = Math.max(10, maxY - minY);
		return { minX, maxX, minY, maxY, w, h };
	}

	function draw() {
		const ctx = canvasEl?.getContext('2d');
		if (!ctx) return;
		ctx.save();
		ctx.clearRect(0, 0, width * dpr, height * dpr);
		ctx.scale(dpr, dpr);
		ctx.translate(transform.x, transform.y);
		ctx.scale(transform.k, transform.k);

		const isFocusActive = !!activeNode;
		const { closestNodeIds, connectedEdgeKeys } = activeNeighborhood;

		// ── 1. EDGES ──
		if (!isFocusActive) {
			ctx.strokeStyle = 'rgba(125, 118, 108, .40)';
			ctx.lineWidth = 1.2 / transform.k;
			ctx.beginPath();
			for (const e of simEdges) {
				const s = e.source as SimNode, t = e.target as SimNode;
				if (s.x == null || t.x == null || s.y == null || t.y == null) continue;
				ctx.moveTo(s.x, s.y);
				ctx.lineTo(t.x, t.y);
			}
			ctx.stroke();
		} else {
			// Ghosted unselected edges
			ctx.strokeStyle = 'rgba(125, 118, 108, .07)';
			ctx.lineWidth = 0.8 / transform.k;
			ctx.beginPath();
			for (const e of simEdges) {
				const s = e.source as SimNode, t = e.target as SimNode;
				if (s.x == null || t.x == null || s.y == null || t.y == null) continue;
				const key = `${s.id}->${t.id}`;
				if (connectedEdgeKeys.has(key)) continue;
				ctx.moveTo(s.x, s.y);
				ctx.lineTo(t.x, t.y);
			}
			ctx.stroke();

			// Highlighted connected edges (connecting activeNode to closest nodes)
			ctx.strokeStyle = '#9c3f5a';
			ctx.lineWidth = 2.6 / transform.k;
			ctx.beginPath();
			const activeEdgesToDraw: any[] = [];
			for (const e of simEdges) {
				const s = e.source as SimNode, t = e.target as SimNode;
				if (s.x == null || t.x == null || s.y == null || t.y == null) continue;
				const key = `${s.id}->${t.id}`;
				if (connectedEdgeKeys.has(key)) {
					ctx.moveTo(s.x, s.y);
					ctx.lineTo(t.x, t.y);
					activeEdgesToDraw.push(e);
				}
			}
			ctx.stroke();

			// Edge relationship label tags
			if (isFocusActive || transform.k > 0.45) {
				ctx.save();
				ctx.font = `600 ${9 / transform.k}px ui-sans-serif, system-ui, sans-serif`;
				ctx.textAlign = 'center';
				ctx.textBaseline = 'middle';
				for (const e of activeEdgesToDraw) {
					const s = e.source as SimNode, t = e.target as SimNode;
					if (s.x == null || t.x == null || s.y == null || t.y == null || !e.label) continue;
					const mx = (s.x + t.x) / 2;
					const my = (s.y + t.y) / 2;
					const txt = e.label;
					const textW = ctx.measureText(txt).width + 8 / transform.k;
					const textH = 13 / transform.k;
					ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
					ctx.fillRect(mx - textW / 2, my - textH / 2, textW, textH);
					ctx.strokeStyle = '#9c3f5a';
					ctx.lineWidth = 0.9 / transform.k;
					ctx.strokeRect(mx - textW / 2, my - textH / 2, textW, textH);
					ctx.fillStyle = '#9c3f5a';
					ctx.fillText(txt, mx, my);
				}
				ctx.restore();
			}
		}

		// ── 2. NODES ──
		const showAllLabels = labelsAlwaysOn || transform.k > 1.5;

		for (const n of simNodes) {
			if (n.x == null || n.y == null) continue;
			const r = n.size ?? 2.4;
			const isSelf = activeNode?.id === n.id;
			const isClosest = closestNodeIds.has(n.id);

			ctx.save();
			if (isFocusActive) {
				ctx.globalAlpha = isClosest ? 1.0 : 0.14;
			} else {
				ctx.globalAlpha = 1.0;
			}

			// Node circle (scaled dynamically by volume of data held)
			ctx.beginPath();
			ctx.arc(n.x, n.y, isSelf ? r + 3 : r, 0, Math.PI * 2);
			ctx.fillStyle = colorFor(n.group);
			ctx.fill();

			// Highlight halo / stroke
			if (isSelf) {
				ctx.lineWidth = Math.max(1.8, Math.min(3.5, r * 0.7)) / transform.k;
				ctx.strokeStyle = '#9c3f5a';
				ctx.stroke();

				// Outer pulse ring
				ctx.beginPath();
				ctx.arc(n.x, n.y, r + 6, 0, Math.PI * 2);
				ctx.lineWidth = 1.5 / transform.k;
				ctx.strokeStyle = 'rgba(156, 63, 90, 0.5)';
				ctx.stroke();
			} else if (isClosest) {
				ctx.lineWidth = Math.max(1.2, Math.min(2.4, r * 0.6)) / transform.k;
				ctx.strokeStyle = '#9c3f5a';
				ctx.stroke();
			}

			// Label rendering
			const shouldShowLabel = isSelf || isClosest || showAllLabels;
			if (shouldShowLabel && (!isFocusActive || isClosest)) {
				const fontSize = (isSelf ? 11 : 9.5) / transform.k;
				ctx.font = `${isSelf ? 'bold' : '500'} ${fontSize}px ui-sans-serif, system-ui, sans-serif`;
				ctx.textAlign = 'center';

				const textY = n.y - (isSelf ? r + 6 : r + 3.5);

				// Crisp white outline backdrop
				ctx.lineWidth = (isSelf ? 3.5 : 2.8) / transform.k;
				ctx.strokeStyle = '#ffffff';
				ctx.lineJoin = 'round';
				ctx.strokeText(n.label, n.x, textY);

				// Ink text
				ctx.fillStyle = isSelf ? '#7d2f47' : isClosest ? '#221f1b' : '#4a453e';
				ctx.fillText(n.label, n.x, textY);
			}

			ctx.restore();
		}

		ctx.restore();
	}

	function drawMinimap() {
		if (!minimapCanvasEl || !simNodes.length || !minimapOpen) return;
		const ctx = minimapCanvasEl.getContext('2d');
		if (!ctx) return;
		ctx.save();
		ctx.clearRect(0, 0, minimapWidth * dpr, minimapHeight * dpr);
		ctx.scale(dpr, dpr);

		const bounds = getGraphBounds();
		const pad = 12;
		const availW = minimapWidth - pad * 2;
		const availH = minimapHeight - pad * 2;
		const scale = Math.min(availW / bounds.w, availH / bounds.h);
		const offsetX = pad + (availW - bounds.w * scale) / 2 - bounds.minX * scale;
		const offsetY = pad + (availH - bounds.h * scale) / 2 - bounds.minY * scale;

		// Minimap edges
		ctx.strokeStyle = 'rgba(125, 118, 108, .22)';
		ctx.lineWidth = 0.7;
		ctx.beginPath();
		for (const e of simEdges) {
			const s = e.source as SimNode, t = e.target as SimNode;
			if (s.x == null || t.x == null || s.y == null || t.y == null) continue;
			ctx.moveTo(s.x * scale + offsetX, s.y * scale + offsetY);
			ctx.lineTo(t.x * scale + offsetX, t.y * scale + offsetY);
		}
		ctx.stroke();

		// Highlighted edges on minimap
		const { closestNodeIds, connectedEdgeKeys } = activeNeighborhood;
		if (activeNode && connectedEdgeKeys.size) {
			ctx.strokeStyle = '#9c3f5a';
			ctx.lineWidth = 1.3;
			ctx.beginPath();
			for (const e of simEdges) {
				const s = e.source as SimNode, t = e.target as SimNode;
				if (s.x == null || t.x == null || s.y == null || t.y == null) continue;
				const key = `${s.id}->${t.id}`;
				if (connectedEdgeKeys.has(key)) {
					ctx.moveTo(s.x * scale + offsetX, s.y * scale + offsetY);
					ctx.lineTo(t.x * scale + offsetX, t.y * scale + offsetY);
				}
			}
			ctx.stroke();
		}

		// Minimap nodes
		for (const n of simNodes) {
			if (n.x == null || n.y == null) continue;
			const nx = n.x * scale + offsetX;
			const ny = n.y * scale + offsetY;
			const isHovered = activeNode?.id === n.id;
			const isClosest = closestNodeIds.has(n.id);
			const baseDotR = Math.max(1.2, Math.min(3.5, (n.size ?? 2.4) * 0.28));

			ctx.beginPath();
			ctx.arc(nx, ny, isHovered ? Math.max(4.2, baseDotR + 2) : isClosest ? Math.max(2.6, baseDotR + 1) : baseDotR, 0, Math.PI * 2);
			if (isHovered) {
				ctx.fillStyle = '#9c3f5a';
				ctx.fill();
				ctx.strokeStyle = '#ffffff';
				ctx.lineWidth = 1.2;
				ctx.stroke();
			} else if (isClosest) {
				ctx.fillStyle = colorFor(n.group);
				ctx.fill();
				ctx.strokeStyle = '#9c3f5a';
				ctx.lineWidth = 0.9;
				ctx.stroke();
			} else {
				ctx.fillStyle = activeNode ? 'rgba(125, 118, 108, .3)' : colorFor(n.group);
				ctx.fill();
			}
		}

		// Viewport rectangle
		const vpX0 = (-transform.x) / transform.k;
		const vpY0 = (-transform.y) / transform.k;
		const vpX1 = (width - transform.x) / transform.k;
		const vpY1 = (height - transform.y) / transform.k;

		const rx = vpX0 * scale + offsetX;
		const ry = vpY0 * scale + offsetY;
		const rw = (vpX1 - vpX0) * scale;
		const rh = (vpY1 - vpY0) * scale;

		ctx.fillStyle = 'rgba(156, 63, 90, 0.12)';
		ctx.fillRect(rx, ry, rw, rh);
		ctx.strokeStyle = '#9c3f5a';
		ctx.lineWidth = 1.2;
		ctx.strokeRect(rx, ry, rw, rh);

		ctx.restore();
	}

	function fitToView() {
		if (!canvasEl || !zoomBehavior || !simNodes.length) return;
		const bounds = getGraphBounds();
		const scale = Math.min(1.8, Math.max(0.04, Math.min(width / bounds.w, height / bounds.h)));
		const tx = width / 2 - scale * (bounds.minX + bounds.w / 2);
		const ty = height / 2 - scale * (bounds.minY + bounds.h / 2);
		select(canvasEl)
			.transition().duration(280)
			.call(zoomBehavior.transform as any, zoomIdentity.translate(tx, ty).scale(scale));
	}

	function nodeAt(px: number, py: number): SimNode | null {
		const x = (px - transform.x) / transform.k;
		const y = (py - transform.y) / transform.k;
		let best: SimNode | null = null, bestDist = Infinity;
		for (const n of simNodes) {
			if (n.x == null || n.y == null) continue;
			const r = Math.max((n.size ?? 2.4) + 12, 16 / transform.k);
			const d = Math.hypot(n.x - x, n.y - y);
			if (d <= r && d < bestDist) { best = n; bestDist = d; }
		}
		return best;
	}

	let potentialDrag: SimNode | null = null;
	let dragStartX = 0;
	let dragStartY = 0;
	let isRealDrag = false;
	let dragging: SimNode | null = null;
	let minimapDragging = false;

	function onPointerDown(e: PointerEvent) {
		const rect = canvasEl!.getBoundingClientRect();
		const hit = nodeAt(e.clientX - rect.left, e.clientY - rect.top);
		if (hit) {
			potentialDrag = hit;
			dragStartX = e.clientX;
			dragStartY = e.clientY;
			isRealDrag = false;
			canvasEl!.setPointerCapture(e.pointerId);
		}
	}

	function onPointerMove(e: PointerEvent) {
		const rect = canvasEl!.getBoundingClientRect();
		const px = e.clientX - rect.left, py = e.clientY - rect.top;

		if (potentialDrag && !isRealDrag) {
			if (Math.hypot(e.clientX - dragStartX, e.clientY - dragStartY) > 4) {
				isRealDrag = true;
				dragging = potentialDrag;
				dragging.fx = dragging.x;
				dragging.fy = dragging.y;
				simulation?.alphaTarget(0.3).restart();
			}
		}

		if (dragging && isRealDrag) {
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
		const wasDragging = isRealDrag && dragging;
		if (dragging) {
			dragging.fx = null;
			dragging.fy = null;
			simulation?.alphaTarget(0);
			dragging = null;
		}
		potentialDrag = null;
		isRealDrag = false;
		try { canvasEl!.releasePointerCapture(e.pointerId); } catch {}

		if (wasDragging) {
			return;
		}

		const rect = canvasEl!.getBoundingClientRect();
		const hit = nodeAt(e.clientX - rect.left, e.clientY - rect.top);
		if (hit) {
			if (selectedNodeId === hit.id) {
				selectedNodeId = null;
			} else {
				focusNode(hit.id);
			}
			onNodeClick?.(hit);
			scheduleDraw();
		} else {
			// Clicked background: clear selection
			selectedNodeId = null;
			scheduleDraw();
		}
	}

	function panToMinimap(e: PointerEvent) {
		if (!minimapCanvasEl || !zoomBehavior || !canvasEl) return;
		const rect = minimapCanvasEl.getBoundingClientRect();
		const mx = e.clientX - rect.left;
		const my = e.clientY - rect.top;
		const bounds = getGraphBounds();
		const pad = 12;
		const availW = minimapWidth - pad * 2;
		const availH = minimapHeight - pad * 2;
		const scale = Math.min(availW / bounds.w, availH / bounds.h);
		const offsetX = pad + (availW - bounds.w * scale) / 2 - bounds.minX * scale;
		const offsetY = pad + (availH - bounds.h * scale) / 2 - bounds.minY * scale;

		const targetGraphX = (mx - offsetX) / scale;
		const targetGraphY = (my - offsetY) / scale;

		const nextTx = width / 2 - targetGraphX * transform.k;
		const nextTy = height / 2 - targetGraphY * transform.k;

		select(canvasEl).call(
			zoomBehavior.transform as any,
			zoomIdentity.translate(nextTx, nextTy).scale(transform.k)
		);
	}

	function onMinimapPointerDown(e: PointerEvent) {
		minimapDragging = true;
		minimapCanvasEl?.setPointerCapture(e.pointerId);
		panToMinimap(e);
	}
	function onMinimapPointerMove(e: PointerEvent) {
		if (minimapDragging) panToMinimap(e);
	}
	function onMinimapPointerUp(e: PointerEvent) {
		minimapDragging = false;
		try { minimapCanvasEl?.releasePointerCapture(e.pointerId); } catch {}
	}

	function zoomBy(factor: number) {
		if (!canvasEl || !zoomBehavior) return;
		select(canvasEl).transition().duration(200).call(zoomBehavior.scaleBy as any, factor);
	}

	function focusNode(nodeId: string) {
		selectedNodeId = nodeId;
		hoveredId = null;
		scheduleDraw();
		const target = simNodes.find((n) => n.id === nodeId);
		if (!target || target.x == null || target.y == null || !canvasEl || !zoomBehavior) return;
		select(canvasEl)
			.transition()
			.duration(350)
			.call(
				zoomBehavior.transform as any,
				zoomIdentity.translate(width / 2 - target.x * transform.k, height / 2 - target.y * transform.k).scale(transform.k)
			);
	}

	// ── CONNECTED COMPONENT DISCOVERY & MULTI-GRAPH SEPARATION ──
	$effect(() => {
		simNodes = nodes.map((n) => ({
			...n,
			size: calcNodeRadius(n)
		}));
		const byId = new Map(simNodes.map((n) => [n.id, n]));
		simEdges = edges
			.filter((e) => byId.has(e.source) && byId.has(e.target))
			.map((e) => ({ ...e }));

		// Build adjacency list for connected component analysis
		const adj = new Map<string, string[]>();
		for (const n of simNodes) adj.set(n.id, []);
		for (const e of simEdges) {
			const sId = typeof e.source === 'object' ? e.source.id : e.source;
			const tId = typeof e.target === 'object' ? e.target.id : e.target;
			adj.get(sId)?.push(tId);
			adj.get(tId)?.push(sId);
		}

		// BFS to find all disconnected subgraphs (components)
		const visited = new Set<string>();
		const discoveredComponents: Component[] = [];
		let compId = 0;

		for (const n of simNodes) {
			if (visited.has(n.id)) continue;
			const queue = [n.id];
			visited.add(n.id);
			const compNodeIds = new Set<string>();
			const compNodes: SimNode[] = [];

			while (queue.length > 0) {
				const currId = queue.shift()!;
				compNodeIds.add(currId);
				const nodeObj = byId.get(currId);
				if (nodeObj) compNodes.push(nodeObj);

				for (const neighborId of adj.get(currId) ?? []) {
					if (!visited.has(neighborId)) {
						visited.add(neighborId);
						queue.push(neighborId);
					}
				}
			}

			const radius = Math.max(180, Math.sqrt(compNodes.length) * 130 + 80);
			discoveredComponents.push({
				id: compId++,
				nodeIds: compNodeIds,
				nodes: compNodes,
				cx: width / 2,
				cy: height / 2,
				radius
			});
		}

		// Sort components by node count descending
		discoveredComponents.sort((a, b) => b.nodes.length - a.nodes.length);

		// Distribute component centers so disconnected graphs are well separated
		// and never clutter in the middle!
		if (discoveredComponents.length === 1) {
			discoveredComponents[0].cx = width / 2;
			discoveredComponents[0].cy = height / 2;
		} else if (discoveredComponents.length > 1) {
			// Center the largest component
			discoveredComponents[0].cx = width / 2;
			discoveredComponents[0].cy = height / 2;

			// Arrange subsequent subgraphs radially around it with generous breathing room (+100% distance)
			const baseOrbit = discoveredComponents[0].radius + 680;
			const remaining = discoveredComponents.length - 1;
			for (let i = 1; i < discoveredComponents.length; i++) {
				const angle = ((i - 1) * Math.PI * 2) / remaining;
				// If many small components, stagger orbits to prevent overlap
				const orbit = remaining > 6 ? baseOrbit + (i % 2) * 360 : baseOrbit;
				discoveredComponents[i].cx = width / 2 + Math.cos(angle) * orbit;
				discoveredComponents[i].cy = height / 2 + Math.sin(angle) * orbit;
			}
		}
		components = discoveredComponents;
		clusterCount = discoveredComponents.length;

		// Seed initial node coordinates and target anchors
		for (const comp of components) {
			const count = Math.max(1, comp.nodes.length);
			const angleStep = (Math.PI * 2) / count;
			comp.nodes.forEach((n, idx) => {
				n.componentId = comp.id;
				n.targetX = comp.cx;
				n.targetY = comp.cy;
				if (n.x == null || isNaN(n.x)) {
					const spread = Math.min(comp.radius * 0.75, 50 + Math.sqrt(idx) * 44);
					n.x = comp.cx + Math.cos(idx * angleStep) * spread;
					n.y = comp.cy + Math.sin(idx * angleStep) * spread;
				}
			});
		}

		let fitted = false;
		simulation?.stop();

		// Simulation physics (+100% node distance):
		// - Link distance doubled from 120 to 240
		// - Repulsion charge doubled from -340 to -680 (distanceMax doubled from 850 to 1700)
		// - Collision padding doubled from +18 to +36
		// - Per-component target X/Y anchoring so disconnected graphs stay in their own space!
		simulation = forceSimulation(simNodes as any)
			.force('link', forceLink(simEdges).id((d: any) => d.id).distance(240).strength(0.35))
			.force('charge', forceManyBody().strength(-680).distanceMax(1700))
			.force('collide', forceCollide().radius((d: any) => (d.size ?? 2.4) + 36).strength(0.85))
			.force('x', forceX((d: any) => d.targetX ?? width / 2).strength((d: any) => (d._isNeighbor ? 0.35 : 0.08)))
			.force('y', forceY((d: any) => d.targetY ?? height / 2).strength((d: any) => (d._isNeighbor ? 0.35 : 0.08)))
			.on('tick', scheduleDraw)
			.on('end', () => { if (!fitted) { fitted = true; fitToView(); } });

		for (let i = 0; i < 300 && (simulation.alpha() ?? 0) > simulation.alphaMin(); i++) simulation.tick();
		fitToView();
		scheduleDraw();

		return () => simulation?.stop();
	});

	// ── ADJACENT NODE SEPARATION ON CLICK ──
	// When a node is clicked / selected, its 1-hop adjacent neighbors bloom outward
	// radially in an uncluttered circle to provide clear viewing of all connections.
	$effect(() => {
		const selId = selectedNodeId;
		if (!simulation || !simNodes.length) return;

		if (!selId) {
			// Deselected: restore default component targets & default link distances
			for (const comp of components) {
				for (const n of comp.nodes) {
					n.targetX = comp.cx;
					n.targetY = comp.cy;
					n._isNeighbor = false;
				}
			}
			const linkForce = simulation.force('link') as any;
			if (linkForce) {
				linkForce.distance(240).strength(0.35);
			}
			simulation.alpha(0.25).restart();
			return;
		}

		const sNode = simNodes.find((n) => n.id === selId);
		if (!sNode || sNode.x == null || sNode.y == null) return;

		// Collect direct (1-hop) neighbors
		const neighborNodes: SimNode[] = [];
		const neighborIds = new Set<string>();

		for (const e of simEdges) {
			const sIdVal = typeof e.source === 'object' ? e.source.id : e.source;
			const tIdVal = typeof e.target === 'object' ? e.target.id : e.target;
			if (sIdVal === selId && !neighborIds.has(tIdVal)) {
				const n = simNodes.find((x) => x.id === tIdVal);
				if (n) { neighborNodes.push(n); neighborIds.add(tIdVal); }
			} else if (tIdVal === selId && !neighborIds.has(sIdVal)) {
				const n = simNodes.find((x) => x.id === sIdVal);
				if (n) { neighborNodes.push(n); neighborIds.add(sIdVal); }
			}
		}

		// Reset non-neighbors to their component center
		for (const comp of components) {
			for (const n of comp.nodes) {
				if (n.id !== selId && !neighborIds.has(n.id)) {
					n.targetX = comp.cx;
					n.targetY = comp.cy;
					n._isNeighbor = false;
				}
			}
		}

		// Anchor the selected node where it is
		sNode.targetX = sNode.x;
		sNode.targetY = sNode.y;
		sNode._isNeighbor = false;

		if (neighborNodes.length > 0) {
			// Generous radial separation so all adjacent nodes are clearly visible
			const R = Math.max(300, 240 + neighborNodes.length * 28);

			// Sort neighbors by existing angle from sNode to preserve natural topological direction
			neighborNodes.sort((a, b) => {
				const angleA = Math.atan2((a.y ?? sNode.y!) - sNode.y!, (a.x ?? sNode.x!) - sNode.x!);
				const angleB = Math.atan2((b.y ?? sNode.y!) - sNode.y!, (b.x ?? sNode.x!) - sNode.x!);
				return angleA - angleB;
			});

			const baseAngle = Math.atan2(
				(neighborNodes[0].y ?? sNode.y!) - sNode.y!,
				(neighborNodes[0].x ?? sNode.x!) - sNode.x!
			);
			const step = (Math.PI * 2) / neighborNodes.length;

			neighborNodes.forEach((n, idx) => {
				n._isNeighbor = true;
				const angle = baseAngle + idx * step;
				n.targetX = sNode.x! + Math.cos(angle) * R;
				n.targetY = sNode.y! + Math.sin(angle) * R;

				// Give an outward velocity impulse so nodes smoothly bloom outward
				const curDist = Math.hypot((n.x ?? sNode.x!) - sNode.x!, (n.y ?? sNode.y!) - sNode.y!);
				if (curDist < R * 0.9) {
					n.vx = (n.targetX - (n.x ?? sNode.x!)) * 0.22;
					n.vy = (n.targetY - (n.y ?? sNode.y!)) * 0.22;
				}
			});

			// Expand link distance for incident edges connecting to the selected node
			const linkForce = simulation.force('link') as any;
			if (linkForce) {
				linkForce.distance((d: any) => {
					const s = typeof d.source === 'object' ? d.source.id : d.source;
					const t = typeof d.target === 'object' ? d.target.id : d.target;
					return (s === selId || t === selId) ? R : 240;
				}).strength((d: any) => {
					const s = typeof d.source === 'object' ? d.source.id : d.source;
					const t = typeof d.target === 'object' ? d.target.id : d.target;
					return (s === selId || t === selId) ? 0.65 : 0.35;
				});
			}

			simulation.alpha(0.35).restart();
		}
	});

	$effect(() => {
		if (!canvasEl) return;
		zoomBehavior = zoom<HTMLCanvasElement, unknown>()
			.scaleExtent([0.04, 4])
			.filter((e: any) => !dragging && !e.target.closest?.('button') && !e.target.closest?.('.context-hud') && !e.target.closest?.('.context-map-wrap'))
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
			height = Math.max(480, entry.contentRect.height || height);
			scheduleDraw();
		});
		ro.observe(el);
		return { destroy() { ro.disconnect(); } };
	}

	const searchHits = $derived(
		searchFilter.trim()
			? nodes.filter((n) => n.label.toLowerCase().includes(searchFilter.trim().toLowerCase())).slice(0, 7)
			: []
	);
</script>

<div class="graph-wrap" bind:this={wrapEl} use:resize>
	{#if !nodes.length}
		<div class="graph-empty">
			<Icon name="refresh" size={24} />
			<p class="hint">No concepts linked in the graph yet. Ingest documents and run relink to build knowledge links.</p>
		</div>
	{:else}
		<!-- Floating Glass Toolbar -->
		<div class="graph-toolbar">
			<div class="search-box">
				<Icon name="search" size={13} />
				<input
					type="text"
					placeholder="Find concept…"
					bind:value={searchFilter}
					onfocus={() => (searchFocused = true)}
					onblur={() => setTimeout(() => (searchFocused = false), 450)}
				/>
				{#if searchFilter}
					<button class="clear-btn" onclick={() => (searchFilter = '')} aria-label="Clear search">×</button>
				{/if}
				{#if searchFocused && searchHits.length}
					<div class="search-dropdown">
						{#each searchHits as hit (hit.id)}
							<button
								type="button"
								class="search-hit"
								onpointerdown={(e) => { e.preventDefault(); focusNode(hit.id); searchFilter = ''; searchFocused = false; }}
								onmousedown={(e) => { e.preventDefault(); focusNode(hit.id); searchFilter = ''; searchFocused = false; }}
								onclick={() => { focusNode(hit.id); searchFilter = ''; searchFocused = false; }}
							>
								<span class="hit-dot" style="background: {colorFor(hit.group)}"></span>
								<span class="hit-label">{hit.label}</span>
								{#if hit.group}<span class="hit-group">{hit.group}</span>{/if}
							</button>
						{/each}
					</div>
				{/if}
			</div>

			<div class="btn-group">
				<button type="button" onclick={() => zoomBy(1.35)} title="Zoom in" aria-label="Zoom in">+</button>
				<button type="button" onclick={() => zoomBy(1 / 1.35)} title="Zoom out" aria-label="Zoom out">&minus;</button>
				<button type="button" onclick={fitToView} title="Fit to view" aria-label="Fit to view">⤢</button>
				<button
					type="button"
					class="toggle-btn"
					class:active={minimapOpen}
					onclick={() => { minimapOpen = !minimapOpen; scheduleDraw(); }}
					title="Toggle Context Map"
					aria-label="Toggle Context Map"
				>
					<Icon name="globe" size={13} />
				</button>
			</div>
		</div>

		<!-- Context HUD / Node Inspector Card -->
		<div class="context-hud" class:has-focus={!!activeNode}>
			{#if activeNode}
				<div class="hud-header">
					<div class="hud-title-row">
						<span class="hud-swatch" style="background: {colorFor(activeNode.group)}"></span>
						<h3 class="hud-title">{activeNode.label}</h3>
						{#if selectedNodeId}
							<button class="hud-close" onclick={() => { selectedNodeId = null; hoveredId = null; scheduleDraw(); }} title="Unpin selection" aria-label="Unpin selection">×</button>
						{/if}
					</div>
					<div class="hud-badges">
						{#if activeNode.group}<span class="hud-badge group">{activeNode.group}</span>{/if}
						<span class="hud-badge">{activeNeighborhood.neighbors.length} direct connection{activeNeighborhood.neighbors.length === 1 ? '' : 's'}</span>
						{#if activeNode.mentions}<span class="hud-badge">{activeNode.mentions} mention{activeNode.mentions === 1 ? '' : 's'}</span>{/if}
						{#if activeNode.documents}<span class="hud-badge">{activeNode.documents} doc{activeNode.documents === 1 ? '' : 's'}</span>{/if}
						{#if activeNode.size}<span class="hud-badge sub" title="Node radius based on volume of data held">Size: {activeNode.size.toFixed(1)}px</span>{/if}
						{#if clusterCount > 1}
							<span class="hud-badge sub">Cluster #{((simNodes.find(n => n.id === activeNode.id)?.componentId ?? 0) + 1)}</span>
						{/if}
					</div>
				</div>

				<!-- Closest Connected Nodes (1-hop neighbors) -->
				<div class="hud-neighbors">
					<div class="hud-section-label">
						<span>Closest Connected Concepts</span>
						<span class="hud-count">({activeNeighborhood.neighbors.length})</span>
					</div>
					{#if activeNeighborhood.neighbors.length === 0}
						<p class="hud-empty">This concept has no direct relations to other concepts.</p>
					{:else}
						<div class="neighbor-chips">
							{#each activeNeighborhood.neighbors as item (item.node.id)}
								<button
									type="button"
									class="neighbor-chip"
									onclick={() => focusNode(item.node.id)}
									onmouseenter={() => { hoveredId = item.node.id; scheduleDraw(); }}
									onmouseleave={() => { hoveredId = null; scheduleDraw(); }}
									title="Click to focus on {item.node.label}"
								>
									<span class="chip-dot" style="background: {colorFor(item.node.group)}"></span>
									<span class="chip-name">{item.node.label}</span>
									<span class="chip-rel">{item.rel.toLowerCase().replace(/_/g, ' ')}</span>
								</button>
							{/each}
						</div>
					{/if}
				</div>
			{:else}
				<div class="hud-overview">
					<div class="overview-stats">
						<div class="stat-item">
							<span class="stat-num">{nodes.length}</span>
							<span class="stat-label">Concepts</span>
						</div>
						<div class="stat-item">
							<span class="stat-num">{edges.length}</span>
							<span class="stat-label">Relations</span>
						</div>
						{#if clusterCount > 1}
							<div class="stat-item">
								<span class="stat-num">{clusterCount}</span>
								<span class="stat-label">Graph Clusters</span>
							</div>
						{/if}
					</div>
					<p class="hud-tip">
						<Icon name="eye" size={12} />
						Hover or click any concept to inspect its closest connections and context map.
					</p>
				</div>
			{/if}
		</div>

		<!-- Interactive Context Map (Minimap) -->
		{#if minimapOpen}
			<div class="context-map-wrap">
				<div class="context-map-header">
					<div class="map-title">
						<Icon name="globe" size={11} />
						<span>Context Map</span>
					</div>
					<button
						class="mini-btn"
						onclick={() => { minimapOpen = false; }}
						title="Hide Context Map"
						aria-label="Hide Context Map"
					>×</button>
				</div>
				<canvas
					bind:this={minimapCanvasEl}
					width={minimapWidth * dpr}
					height={minimapHeight * dpr}
					style="width: {minimapWidth}px; height: {minimapHeight}px;"
					aria-label="Interactive context map overview"
					onpointerdown={onMinimapPointerDown}
					onpointermove={onMinimapPointerMove}
					onpointerup={onMinimapPointerUp}
				></canvas>
				<div class="map-hint">Click / drag to pan</div>
			</div>
		{/if}

		<!-- Main Canvas -->
		<canvas
			bind:this={canvasEl}
			width={width * dpr}
			height={height * dpr}
			style="width: {width}px; height: {height}px;"
			aria-label="Concept Knowledge Graph"
			onpointerdown={onPointerDown}
			onpointermove={onPointerMove}
			onpointerup={onPointerUp}
			onpointerleave={() => { if (!dragging) { hoveredId = null; scheduleDraw(); } }}
		></canvas>

		<!-- Bottom Category Legend -->
		{#if paletteColors.size || Object.keys(COLORS).length}
			<div class="graph-legend">
				{#each [...new Set(nodes.map((n) => n.group).filter(Boolean))] as group (group)}
					<span class="legend-item">
						<span class="swatch" style="background: {colorFor(group)}"></span>
						<span class="legend-label">{group}</span>
					</span>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.graph-wrap {
		position: relative;
		width: 100%;
		height: 100%;
		min-height: 520px;
		flex: 1 1 auto;
		border: 1px solid var(--line);
		border-radius: var(--r-lg);
		overflow: hidden;
		background: radial-gradient(circle at 50% 50%, color-mix(in srgb, var(--panel) 92%, #fff) 0%, var(--panel) 100%);
		display: flex;
		flex-direction: column;
	}

	.graph-empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		min-height: 400px;
		gap: .75rem;
		color: var(--muted);
	}

	canvas {
		display: block;
		cursor: grab;
		touch-action: none;
		flex: 1 1 auto;
	}

	/* ── Floating Glass Toolbar ── */
	.graph-toolbar {
		position: absolute;
		top: .75rem;
		right: .75rem;
		z-index: 10;
		display: flex;
		align-items: center;
		gap: .5rem;
	}

	.search-box {
		position: relative;
		display: flex;
		align-items: center;
		gap: .35rem;
		background: var(--panel);
		border: 1px solid var(--line);
		border-radius: 9999px;
		padding: .25rem .65rem;
		backdrop-filter: var(--glass-blur);
		-webkit-backdrop-filter: var(--glass-blur);
		box-shadow: var(--shadow);
		color: var(--muted);
	}
	.search-box input {
		border: none;
		background: none;
		font: inherit;
		font-size: var(--text-xs);
		color: var(--ink);
		width: 7.5rem;
		outline: none;
		transition: width var(--duration-fast, 0.15s) var(--ease);
	}
	.search-box input:focus {
		width: 11rem;
	}
	.clear-btn {
		border: none;
		background: none;
		color: var(--muted);
		cursor: pointer;
		font-size: .85rem;
		padding: 0;
	}

	.search-dropdown {
		position: absolute;
		top: calc(100% + .35rem);
		left: 0;
		right: 0;
		background: var(--panel);
		border: 1px solid var(--line);
		border-radius: var(--r);
		backdrop-filter: var(--glass-blur);
		-webkit-backdrop-filter: var(--glass-blur);
		box-shadow: var(--shadow-lg);
		max-height: 13rem;
		overflow-y: auto;
		z-index: 25;
		display: flex;
		flex-direction: column;
	}
	.search-hit {
		display: flex;
		align-items: center;
		gap: .4rem;
		padding: .4rem .6rem;
		border: none;
		background: none;
		font: inherit;
		font-size: var(--text-xs);
		color: var(--ink);
		cursor: pointer;
		text-align: left;
	}
	.search-hit:hover {
		background: var(--accent-soft);
		color: var(--accent-ink);
	}
	.hit-dot {
		width: .5rem;
		height: .5rem;
		border-radius: 50%;
		flex: 0 0 auto;
	}
	.hit-label {
		flex: 1 1 auto;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.hit-group {
		font-size: .65rem;
		color: var(--muted);
		background: var(--panel-2);
		padding: .1rem .3rem;
		border-radius: 4px;
	}

	.btn-group {
		display: flex;
		align-items: center;
		background: var(--panel);
		border: 1px solid var(--line);
		border-radius: 9999px;
		backdrop-filter: var(--glass-blur);
		-webkit-backdrop-filter: var(--glass-blur);
		box-shadow: var(--shadow);
		overflow: hidden;
	}
	.btn-group button {
		width: 1.85rem;
		height: 1.85rem;
		border: none;
		background: none;
		cursor: pointer;
		font-size: 1rem;
		line-height: 1;
		color: var(--ink-2);
		display: flex;
		align-items: center;
		justify-content: center;
		transition: background var(--duration-fast, 0.15s) var(--ease), color var(--duration-fast, 0.15s);
	}
	.btn-group button:hover {
		background: var(--panel-2);
		color: var(--accent-ink);
	}
	.btn-group button.toggle-btn.active {
		color: var(--accent);
		background: var(--accent-soft);
	}

	/* ── Context HUD Card ── */
	.context-hud {
		position: absolute;
		top: .75rem;
		left: .75rem;
		z-index: 10;
		width: 18.5rem;
		max-width: calc(100% - 1.5rem);
		background: color-mix(in srgb, var(--panel) 90%, #fff);
		border: 1px solid var(--line);
		border-radius: var(--r-lg);
		backdrop-filter: var(--glass-blur);
		-webkit-backdrop-filter: var(--glass-blur);
		box-shadow: var(--shadow-lg);
		padding: .75rem .9rem;
		display: flex;
		flex-direction: column;
		gap: .5rem;
		transition: border-color var(--duration-fast, 0.15s), box-shadow var(--duration-fast, 0.15s);
	}
	.context-hud.has-focus {
		border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
		box-shadow: 0 8px 24px rgba(156, 63, 90, .12), var(--shadow);
	}

	.hud-header {
		display: flex;
		flex-direction: column;
		gap: .35rem;
	}
	.hud-title-row {
		display: flex;
		align-items: center;
		gap: .45rem;
	}
	.hud-swatch {
		width: .7rem;
		height: .7rem;
		border-radius: 50%;
		flex: 0 0 auto;
	}
	.hud-title {
		margin: 0;
		font-size: var(--text-sm);
		font-weight: 700;
		color: var(--ink);
		line-height: 1.25;
		flex: 1 1 auto;
		word-break: break-word;
	}
	.hud-close {
		border: none;
		background: none;
		cursor: pointer;
		color: var(--muted);
		font-size: 1.1rem;
		padding: 0 .2rem;
		line-height: 1;
		border-radius: var(--r);
	}
	.hud-close:hover {
		color: var(--danger);
	}

	.hud-badges {
		display: flex;
		flex-wrap: wrap;
		gap: .3rem;
	}
	.hud-badge {
		font-size: .68rem;
		font-weight: 500;
		padding: .15rem .45rem;
		border-radius: 9999px;
		background: var(--panel-2);
		border: 1px solid var(--line);
		color: var(--ink-2);
	}
	.hud-badge.group {
		background: var(--accent-soft);
		border-color: color-mix(in srgb, var(--accent) 30%, transparent);
		color: var(--accent-ink);
		font-weight: 600;
	}
	.hud-badge.sub {
		color: var(--muted);
	}

	.hud-neighbors {
		display: flex;
		flex-direction: column;
		gap: .4rem;
		border-top: 1px solid var(--line);
		padding-top: .45rem;
		max-height: 14rem;
		overflow-y: auto;
	}
	.hud-section-label {
		display: flex;
		align-items: center;
		justify-content: space-between;
		font-size: .7rem;
		font-weight: 600;
		color: var(--muted);
		text-transform: uppercase;
		letter-spacing: .02em;
	}
	.hud-count {
		color: var(--accent);
		font-weight: 700;
	}
	.hud-empty {
		margin: 0;
		font-size: var(--text-xs);
		color: var(--muted);
	}

	.neighbor-chips {
		display: flex;
		flex-wrap: wrap;
		gap: .3rem;
	}
	.neighbor-chip {
		display: inline-flex;
		align-items: center;
		gap: .35rem;
		padding: .25rem .5rem;
		background: var(--panel);
		border: 1px solid var(--line);
		border-radius: 8px;
		font: inherit;
		font-size: .72rem;
		color: var(--ink);
		cursor: pointer;
		text-align: left;
		transition: all .12s var(--ease);
	}
	.neighbor-chip:hover {
		background: var(--accent-soft);
		border-color: var(--accent);
		color: var(--accent-ink);
		transform: translateY(-1px);
	}
	.chip-dot {
		width: .45rem;
		height: .45rem;
		border-radius: 50%;
		flex: 0 0 auto;
	}
	.chip-name {
		font-weight: 600;
	}
	.chip-rel {
		font-size: .65rem;
		color: var(--muted);
		background: var(--panel-2);
		padding: .05rem .25rem;
		border-radius: 4px;
	}
	.neighbor-chip:hover .chip-rel {
		color: var(--accent-ink);
		background: rgba(255, 255, 255, 0.7);
	}

	.hud-overview {
		display: flex;
		flex-direction: column;
		gap: .5rem;
	}
	.overview-stats {
		display: flex;
		align-items: center;
		gap: .9rem;
	}
	.stat-item {
		display: flex;
		flex-direction: column;
	}
	.stat-num {
		font-size: var(--text-md, 1rem);
		font-weight: 700;
		color: var(--ink);
	}
	.stat-label {
		font-size: .68rem;
		color: var(--muted);
		text-transform: uppercase;
		letter-spacing: .02em;
	}
	.hud-tip {
		margin: 0;
		display: flex;
		align-items: center;
		gap: .35rem;
		font-size: .72rem;
		color: var(--muted);
		line-height: 1.35;
	}

	/* ── Context Map (Minimap) ── */
	.context-map-wrap {
		position: absolute;
		bottom: 2.2rem;
		left: .75rem;
		z-index: 10;
		background: color-mix(in srgb, var(--panel) 92%, #fff);
		border: 1px solid var(--line);
		border-radius: var(--r);
		backdrop-filter: var(--glass-blur);
		-webkit-backdrop-filter: var(--glass-blur);
		box-shadow: var(--shadow-lg);
		padding: .45rem;
		display: flex;
		flex-direction: column;
		gap: .25rem;
	}
	.context-map-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 .2rem;
	}
	.map-title {
		display: flex;
		align-items: center;
		gap: .3rem;
		font-size: .68rem;
		font-weight: 600;
		color: var(--muted);
		text-transform: uppercase;
		letter-spacing: .02em;
	}
	.mini-btn {
		border: none;
		background: none;
		cursor: pointer;
		font-size: .9rem;
		line-height: 1;
		color: var(--muted);
		padding: 0 .15rem;
	}
	.mini-btn:hover {
		color: var(--ink);
	}
	.context-map-wrap canvas {
		cursor: crosshair;
		border-radius: 4px;
		background: var(--panel-2);
		border: 1px solid var(--line);
	}
	.map-hint {
		font-size: .62rem;
		color: var(--muted);
		text-align: center;
	}

	/* ── Legend ── */
	.graph-legend {
		position: absolute;
		bottom: 0;
		left: 0;
		right: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: .3rem .9rem;
		padding: .4rem .85rem;
		border-top: 1px solid var(--line);
		background: var(--panel);
		backdrop-filter: var(--glass-blur);
		-webkit-backdrop-filter: var(--glass-blur);
		font-size: var(--text-xs);
		color: var(--muted);
		z-index: 5;
	}
	.legend-item {
		display: inline-flex;
		align-items: center;
		gap: .35rem;
	}
	.swatch {
		width: .55rem;
		height: .55rem;
		border-radius: 50%;
		flex: 0 0 auto;
	}
	.legend-label {
		font-size: .72rem;
	}
</style>
