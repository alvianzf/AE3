# Spec v14.1 — Admin Settings: Agent Models, Token Usage Analytics & Modern Charts

## 1. Context & Motivation

The system usage and load chart previously introduced in v11/v12 was an unadorned, 64px sparkline SVG lacking axes, grid lines, timestamps, metric labels, and hover tooltips. In addition, platform administrators had no visibility into:
1. Which specific LLM models are assigned to each of the 6 roles in the autonomous AI team (Reader, Graph Builder, Embedder, Answer Engine, Reasoner, Checker).
2. Prompt (input) vs. completion (output) token spend per agent.
3. Comparative token usage distribution across roles.

## 2. Requirements

- **Modernized SVG Charting (`UsageChart.svelte`)**:
  - Replace the raw 64px polyline with a responsive, multi-series-capable SVG chart component.
  - Linear gradient area fills beneath smooth Bézier curves.
  - Dashed horizontal gridlines with formatted Y-axis ticks (load, MB/GB, k/M tokens).
  - Clean bottom time axis labels (local hour/minute).
  - Interactive crosshair guide with pointer hover tracking, active point highlights, and floating tooltip.
  - Summary badges: current value readout, peak, and average over the 3-hour sampling window.

- **Agent Models & Token Usage in Settings**:
  - Expose all 6 AI team roles:
    1. **Reader**: Source reading, summary, topics, suggested grade.
    2. **Graph Builder**: Medical entity/relationship extraction at ingest time.
    3. **Embedder**: Vector embeddings for seed traversal search.
    4. **Answer Engine**: Seed search queries and hop-by-hop relevance judging.
    5. **Reasoner**: Grounded clinical consultation answer synthesis.
    6. **Checker**: LLM-as-judge anti-hallucination verification.
  - Track prompt (input) tokens, completion (output) tokens, total tokens, and total calls per agent.
  - Provide a prominent toggle between **Table View** and **Graph View**:
    - **Table View**: Comprehensive tabular presentation with Agent/Role, Assigned Model badge, Provider chip, Prompt tokens, Output tokens, Total tokens, Usage Share % (with color-coded proportional bar), Calls, and Status/Ping.
    - **Graph View**: Proportional relative token distribution bar, agent breakdown summary cards, and a multi-series 3-hour token consumption trend chart with sub-toggles for Per-agent breakdown, Total token rate, and Input vs. Output breakdown.

- **Backend Architecture (`app/token_tracker.py`)**:
  - In-memory thread-safe accumulator tracking input and output tokens across LLM clients (`LLMClient`, `AnthropicLLMClient`).
  - Integrated into 60s sampling loop (`_sample_usage_loop`), capturing token deltas per interval.
  - Updated `/api/admin/system-usage` endpoint to deliver live agent model names, provider statuses, cumulative token totals, and time-series history.
  - Fallback support for macOS/local development via `os.getloadavg()` and memory estimation so developer environments display live charts out-of-the-box.
