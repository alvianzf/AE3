<script lang="ts">
	// A small inline-SVG line chart — no charting library, consistent
	// with this app's "no new dependency unless there's a real reason"
	// convention for something this simple (one polyline + a filled
	// area under it). Takes plain {x, y}-shaped points already resolved
	// by the caller, not raw samples — keeps this component reusable
	// for any single metric (load average, memory) rather than
	// knowing about the admin system-usage response shape itself.
	let {
		points,
		unit = '',
		height = 64,
		color = 'var(--accent)'
	}: {
		points: { x: number; y: number }[];
		unit?: string;
		height?: number;
		color?: string;
	} = $props();

	const width = 100; // viewBox units — scales via the SVG's own width:100%
	const latest = $derived(points.at(-1)?.y);

	const path = $derived.by(() => {
		if (points.length < 2) return { line: '', area: '' };
		const xs = points.map((p) => p.x);
		const ys = points.map((p) => p.y);
		const minX = Math.min(...xs), maxX = Math.max(...xs);
		const maxY = Math.max(...ys, 1);
		const spanX = maxX - minX || 1;
		const toSvg = (p: { x: number; y: number }) => ({
			x: ((p.x - minX) / spanX) * width,
			y: height - (p.y / maxY) * (height - 6) - 2
		});
		const svgPoints = points.map(toSvg);
		const line = svgPoints.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
		const area = `${line} L${svgPoints.at(-1)!.x.toFixed(1)},${height} L${svgPoints[0].x.toFixed(1)},${height} Z`;
		return { line, area };
	});
</script>

<div class="usage-chart">
	<div class="usage-chart-value">
		{latest !== undefined ? `${latest.toFixed(1)}${unit}` : '—'}
	</div>
	{#if points.length >= 2}
		<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" style:height="{height}px">
			<path d={path.area} fill={color} fill-opacity=".12" />
			<path d={path.line} fill="none" stroke={color} stroke-width="1.5" vector-effect="non-scaling-stroke" />
		</svg>
	{:else}
		<p class="hint">Not enough history yet — check back in a few minutes.</p>
	{/if}
</div>

<style>
	.usage-chart { display: flex; flex-direction: column; gap: .3rem; }
	.usage-chart-value { font-size: var(--text-xl); font-weight: 700; letter-spacing: -.02em; color: var(--ink); }
	.usage-chart svg { width: 100%; display: block; }
	.usage-chart .hint { font-size: var(--text-xs); }
</style>
