<script lang="ts">
	export interface DataPoint {
		x: number;
		y: number;
	}

	export interface ChartSeries {
		id: string;
		name: string;
		color?: string;
		points: DataPoint[];
		unit?: string;
	}

	let {
		points,
		series,
		unit = '',
		title = '',
		height = 170,
		color = 'var(--accent)',
		showSummary = true,
		showAxes = true,
		badge = ''
	}: {
		points?: DataPoint[];
		series?: ChartSeries[];
		unit?: string;
		title?: string;
		height?: number;
		color?: string;
		showSummary?: boolean;
		showAxes?: boolean;
		badge?: string;
	} = $props();

	const resolvedSeries = $derived.by<ChartSeries[]>(() => {
		if (series && series.length > 0) return series;
		if (points && points.length > 0) {
			return [{ id: 'single', name: title || 'Metric', color, points, unit }];
		}
		return [];
	});

	const svgWidth = 600;
	const margin = $derived({
		top: 14,
		bottom: showAxes ? 26 : 8,
		left: showAxes ? 52 : 8,
		right: 14
	});

	const plotWidth = $derived(svgWidth - margin.left - margin.right);
	const plotHeight = $derived(height - margin.top - margin.bottom);

	// Compute bounds across all series
	const bounds = $derived.by(() => {
		const allPts = resolvedSeries.flatMap((s) => s.points);
		if (allPts.length === 0) {
			const now = Date.now() / 1000;
			return { minX: now - 10800, maxX: now, minY: 0, maxY: 1, spanX: 10800, spanY: 1 };
		}
		const xs = allPts.map((p) => p.x);
		const ys = allPts.map((p) => p.y);
		const minX = Math.min(...xs);
		const maxX = Math.max(...xs);
		const spanX = Math.max(maxX - minX, 1);
		const minY = 0;
		const rawMaxY = Math.max(...ys, 0.1);
		// Add 10% headroom
		const maxY = rawMaxY > 1 ? Math.ceil(rawMaxY * 1.1) : Number((rawMaxY * 1.15).toFixed(2));
		const spanY = Math.max(maxY - minY, 0.01);
		return { minX, maxX, minY, maxY, spanX, spanY };
	});

	function toSvgCoords(p: DataPoint) {
		const x = margin.left + ((p.x - bounds.minX) / bounds.spanX) * plotWidth;
		const y = margin.top + plotHeight - ((p.y - bounds.minY) / bounds.spanY) * plotHeight;
		return { x, y };
	}

	function formatUnitValue(val: number, u: string): string {
		if (val === undefined || isNaN(val)) return '—';
		if (u.toLowerCase().includes('token') || (!u && val >= 1000)) {
			if (val >= 1_000_000) return `${(val / 1_000_000).toFixed(2)}M`;
			if (val >= 1_000) return `${(val / 1_000).toFixed(1)}k`;
			return Math.round(val).toLocaleString();
		}
		if (u === 'MB') {
			if (val >= 1024) return `${(val / 1024).toFixed(1)} GB`;
			return `${Math.round(val)} MB`;
		}
		if (val >= 100) return `${Math.round(val)}${u ? ` ${u}` : ''}`;
		return `${val.toFixed(val < 10 && val % 1 !== 0 ? 2 : 1)}${u ? ` ${u}` : ''}`;
	}

	function formatTime(ts: number): string {
		if (!ts) return '';
		const d = new Date(ts * 1000);
		const h = String(d.getHours()).padStart(2, '0');
		const m = String(d.getMinutes()).padStart(2, '0');
		return `${h}:${m}`;
	}

	// Paths calculation with smooth curves
	const renderedSeries = $derived.by(() => {
		return resolvedSeries.map((s, idx) => {
			const sColor = s.color || color;
			const gradientId = `grad-${s.id}-${idx}`;
			const ys = s.points.map((p) => p.y);
			const latest = s.points.at(-1)?.y ?? 0;
			const max = ys.length > 0 ? Math.max(...ys) : 0;
			const min = ys.length > 0 ? Math.min(...ys) : 0;
			const avg = ys.length > 0 ? ys.reduce((acc, v) => acc + v, 0) / ys.length : 0;

			if (s.points.length < 2) {
				return {
					...s,
					color: sColor,
					gradientId,
					linePath: '',
					areaPath: '',
					pts: [],
					latest,
					max,
					min,
					avg
				};
			}
			const pts = s.points.map(toSvgCoords);

			// Build smooth bezier path
			let linePath = `M ${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)}`;
			for (let i = 0; i < pts.length - 1; i++) {
				const p0 = i > 0 ? pts[i - 1] : pts[i];
				const p1 = pts[i];
				const p2 = pts[i + 1];
				const p3 = i != pts.length - 2 ? pts[i + 2] : p2;
				const cp1x = p1.x + (p2.x - p0.x) / 6;
				const cp1y = p1.y + (p2.y - p0.y) / 6;
				const cp2x = p2.x - (p3.x - p1.x) / 6;
				const cp2y = p2.y - (p3.y - p1.y) / 6;
				linePath += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
			}

			const bottomY = margin.top + plotHeight;
			const areaPath = `${linePath} L ${pts.at(-1)!.x.toFixed(1)} ${bottomY} L ${pts[0].x.toFixed(1)} ${bottomY} Z`;

			return {
				...s,
				color: sColor,
				gradientId,
				linePath,
				areaPath,
				pts,
				latest,
				max,
				min,
				avg
			};
		});
	});

	// Gridlines ticks
	const yTicks = $derived.by(() => {
		if (!showAxes) return [];
		const ticks = [0, 0.33, 0.66, 1.0];
		return ticks.map((ratio) => {
			const val = bounds.minY + ratio * bounds.spanY;
			const y = margin.top + plotHeight - ratio * plotHeight;
			return { y, label: formatUnitValue(val, unit) };
		});
	});

	const xTicks = $derived.by(() => {
		if (!showAxes) return [];
		const count = 4;
		const ticks: { x: number; label: string }[] = [];
		for (let i = 0; i <= count; i++) {
			const ratio = i / count;
			const ts = bounds.minX + ratio * bounds.spanX;
			const x = margin.left + ratio * plotWidth;
			ticks.push({ x, label: formatTime(ts) });
		}
		return ticks;
	});

	// Hover interaction
	let hoveredX = $state<number | null>(null);
	let svgEl = $state<SVGSVGElement | null>(null);

	function onPointerMove(e: PointerEvent) {
		if (!svgEl) return;
		const rect = svgEl.getBoundingClientRect();
		const clientX = e.clientX - rect.left;
		const scaleX = svgWidth / rect.width;
		const localX = clientX * scaleX;
		if (localX >= margin.left && localX <= svgWidth - margin.right) {
			hoveredX = localX;
		} else {
			hoveredX = null;
		}
	}

	function onPointerLeave() {
		hoveredX = null;
	}

	const activeHoverData = $derived.by(() => {
		if (hoveredX === null || renderedSeries.length === 0) return null;
		const ratio = (hoveredX - margin.left) / plotWidth;
		const targetTs = bounds.minX + ratio * bounds.spanX;

		const seriesMatches = renderedSeries.map((s) => {
			if (s.points.length === 0) return null;
			let closestIdx = 0;
			let minDiff = Infinity;
			for (let i = 0; i < s.points.length; i++) {
				const diff = Math.abs(s.points[i].x - targetTs);
				if (diff < minDiff) {
					minDiff = diff;
					closestIdx = i;
				}
			}
			const pt = s.points[closestIdx];
			const svgPt = s.pts[closestIdx];
			return {
				name: s.name,
				color: s.color,
				val: pt.y,
				unit: s.unit ?? unit,
				svgX: svgPt?.x ?? hoveredX,
				svgY: svgPt?.y ?? margin.top
			};
		}).filter(Boolean) as { name: string; color: string; val: number; unit: string; svgX: number; svgY: number }[];

		return {
			ts: targetTs,
			timeStr: formatTime(targetTs),
			series: seriesMatches,
			guideX: hoveredX
		};
	});

	const primary = $derived(renderedSeries[0]);
</script>

<div class="chart-card">
	{#if title || showSummary}
		<div class="chart-header">
			<div class="header-main">
				{#if title}
					<span class="chart-title">{title}</span>
				{/if}
				{#if badge}
					<span class="chart-badge">{badge}</span>
				{/if}
			</div>

			{#if showSummary && primary}
				<div class="summary-stats">
					<div class="stat-latest">
						<span class="stat-value">{formatUnitValue(primary.latest, primary.unit ?? unit)}</span>
						<span class="stat-lbl">current</span>
					</div>
					<div class="stat-sub">
						<span class="sub-pill" title="Peak value in range">
							<span class="pill-dot max"></span> peak <strong>{formatUnitValue(primary.max, primary.unit ?? unit)}</strong>
						</span>
						<span class="sub-pill" title="Average value in range">
							<span class="pill-dot avg"></span> avg <strong>{formatUnitValue(primary.avg, primary.unit ?? unit)}</strong>
						</span>
					</div>
				</div>
			{/if}
		</div>
	{/if}

	{#if renderedSeries.length > 1}
		<div class="series-legend">
			{#each renderedSeries as s (s.id)}
				<div class="legend-item">
					<span class="legend-swatch" style:background={s.color}></span>
					<span class="legend-name">{s.name}</span>
					<span class="legend-val">{formatUnitValue(s.latest, s.unit ?? unit)}</span>
				</div>
			{/each}
		</div>
	{/if}

	<div class="svg-container">
		<svg
			bind:this={svgEl}
			role="img"
			aria-label={title || "Usage metric trend chart"}
			viewBox="0 0 {svgWidth} {height}"
			preserveAspectRatio="none"
			style:height="{height}px"
			onpointermove={onPointerMove}
			onpointerleave={onPointerLeave}
		>
			<defs>
				{#each renderedSeries as s}
					<linearGradient id={s.gradientId} x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stop-color={s.color} stop-opacity="0.28" />
						<stop offset="85%" stop-color={s.color} stop-opacity="0.02" />
						<stop offset="100%" stop-color={s.color} stop-opacity="0" />
					</linearGradient>
				{/each}
			</defs>

			<!-- Horizontal Grid Lines -->
			{#if showAxes}
				{#each yTicks as t}
					<line
						x1={margin.left}
						x2={svgWidth - margin.right}
						y1={t.y}
						y2={t.y}
						class="grid-line"
					/>
					<text
						x={margin.left - 6}
						y={t.y + 3.5}
						text-anchor="end"
						class="axis-text"
					>{t.label}</text>
				{/each}
			{/if}

			<!-- Area Fills -->
			{#each renderedSeries as s}
				{#if s.areaPath}
					<path d={s.areaPath} fill="url(#{s.gradientId})" />
				{/if}
			{/each}

			<!-- Lines -->
			{#each renderedSeries as s}
				{#if s.linePath}
					<path
						d={s.linePath}
						fill="none"
						stroke={s.color}
						stroke-width="2.2"
						stroke-linecap="round"
						stroke-linejoin="round"
						vector-effect="non-scaling-stroke"
					/>
				{/if}
			{/each}

			<!-- Bottom Time Axis -->
			{#if showAxes}
				<line
					x1={margin.left}
					x2={svgWidth - margin.right}
					y1={margin.top + plotHeight}
					y2={margin.top + plotHeight}
					class="axis-line"
				/>
				{#each xTicks as t}
					<text
						x={t.x}
						y={height - 8}
						text-anchor="middle"
						class="axis-text"
					>{t.label}</text>
				{/each}
			{/if}

			<!-- Interactive Hover Guide & Dots -->
			{#if activeHoverData}
				<line
					x1={activeHoverData.guideX}
					x2={activeHoverData.guideX}
					y1={margin.top}
					y2={margin.top + plotHeight}
					class="hover-guide"
				/>
				{#each activeHoverData.series as item}
					<circle
						cx={item.svgX}
						cy={item.svgY}
						r="4.5"
						fill={item.color}
						stroke="#ffffff"
						stroke-width="2"
					/>
				{/each}
			{/if}
		</svg>

		<!-- Floating Tooltip -->
		{#if activeHoverData}
			<div
				class="chart-tooltip"
				style:left="{Math.min(Math.max(activeHoverData.guideX * (100 / svgWidth), 18), 82)}%"
			>
				<div class="tooltip-time">{activeHoverData.timeStr}</div>
				{#each activeHoverData.series as s}
					<div class="tooltip-row">
						<span class="tooltip-dot" style:background={s.color}></span>
						<span class="tooltip-name">{s.name}:</span>
						<span class="tooltip-val">{formatUnitValue(s.val, s.unit)}</span>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	.chart-card {
		display: flex;
		flex-direction: column;
		gap: var(--space-2, 0.5rem);
		padding: var(--space-3, 0.75rem) var(--space-4, 1rem);
		border: 1px solid var(--line);
		border-radius: var(--r-md, 12px);
		background: var(--panel);
		position: relative;
	}

	.chart-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-3, 0.75rem);
		flex-wrap: wrap;
	}

	.header-main {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.chart-title {
		font-size: var(--text-sm, 0.875rem);
		font-weight: 600;
		color: var(--ink);
	}

	.chart-badge {
		font-size: 0.7rem;
		font-weight: 500;
		padding: 0.15rem 0.45rem;
		border-radius: 999px;
		background: var(--accent-soft);
		color: var(--accent-ink);
	}

	.summary-stats {
		display: flex;
		align-items: baseline;
		gap: var(--space-3, 0.75rem);
		flex-wrap: wrap;
	}

	.stat-latest {
		display: flex;
		align-items: baseline;
		gap: 0.3rem;
	}

	.stat-value {
		font-size: var(--text-xl, 1.25rem);
		font-weight: 700;
		letter-spacing: -0.02em;
		color: var(--ink);
	}

	.stat-lbl {
		font-size: 0.7rem;
		color: var(--ink-2);
		text-transform: uppercase;
		font-weight: 500;
	}

	.stat-sub {
		display: flex;
		gap: 0.4rem;
	}

	.sub-pill {
		font-size: 0.72rem;
		color: var(--ink-2);
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		background: var(--panel-2);
		padding: 0.15rem 0.45rem;
		border-radius: var(--r-sm, 6px);
		border: 1px solid var(--line);
	}

	.sub-pill strong {
		color: var(--ink);
		font-weight: 600;
	}

	.pill-dot {
		width: 5px;
		height: 5px;
		border-radius: 50%;
	}
	.pill-dot.max { background: #10b981; }
	.pill-dot.avg { background: var(--accent); }

	.series-legend {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-3, 0.75rem);
		padding-bottom: 0.2rem;
	}

	.legend-item {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		font-size: 0.75rem;
		color: var(--ink-2);
	}

	.legend-swatch {
		width: 8px;
		height: 8px;
		border-radius: 2px;
	}

	.legend-name {
		font-weight: 500;
	}

	.legend-val {
		font-weight: 600;
		color: var(--ink);
	}

	.svg-container {
		position: relative;
		width: 100%;
		user-select: none;
	}

	svg {
		width: 100%;
		display: block;
		overflow: visible;
		cursor: crosshair;
	}

	.grid-line {
		stroke: var(--line);
		stroke-width: 1;
		stroke-dasharray: 4 4;
		opacity: 0.7;
	}

	.axis-line {
		stroke: var(--line);
		stroke-width: 1;
	}

	.axis-text {
		font-size: 9.5px;
		fill: var(--ink-2);
		font-family: inherit;
	}

	.hover-guide {
		stroke: var(--ink-2);
		stroke-width: 1;
		stroke-dasharray: 3 3;
		opacity: 0.6;
	}

	.chart-tooltip {
		position: absolute;
		top: 6px;
		transform: translateX(-50%);
		pointer-events: none;
		background: rgba(18, 22, 34, 0.92);
		backdrop-filter: blur(8px);
		color: #ffffff;
		padding: 0.4rem 0.65rem;
		border-radius: var(--r-sm, 6px);
		font-size: 0.75rem;
		border: 1px solid rgba(255, 255, 255, 0.12);
		z-index: 10;
		min-width: 110px;
	}

	.tooltip-time {
		font-size: 0.68rem;
		color: rgba(255, 255, 255, 0.6);
		margin-bottom: 0.2rem;
		border-bottom: 1px solid rgba(255, 255, 255, 0.1);
		padding-bottom: 0.15rem;
		font-family: monospace;
	}

	.tooltip-row {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		line-height: 1.35;
	}

	.tooltip-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.tooltip-name {
		color: rgba(255, 255, 255, 0.8);
		flex: 1;
	}

	.tooltip-val {
		font-weight: 600;
		color: #ffffff;
	}
</style>
