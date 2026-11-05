# Concept Graph: Data-Driven Node Sizing & 60% Default Node Size Reduction

## 1. 60% Reduction of Default Node Size
- **Baseline Default**: The default node radius is reduced by 60%, from `6.0px` down to `2.4px` (diameter `4.8px`).
- **Clean Canvas Aesthetics**: Peripheral concepts or nodes holding minimal information remain subtle, compact dots, drastically reducing canvas clutter while keeping all concept nodes discoverable.
- **Accessible Hit Targets**: Canvas hit detection maintains a padded interaction boundary (`Math.max((n.size ?? 2.4) + 12, 16 / transform.k)`), ensuring that 2.4px nodes remain effortless to hover, focus, and click.

## 2. Dynamic Data-Driven Node Sizing
- **Data Volume Weight**:
  A concept node's size dynamically reflects the volume of knowledge and data it holds:
  - **Passage Mentions (`mentions`)**: Number of text chunks across all ingested documents referencing this concept.
  - **Graph Relationships (`degree`)**: Number of direct typed clinical/knowledge relationships linking this concept to others.
  - **Document Coverage (`documents`)**: Number of distinct ingested documents mentioning this concept.
- **Proportional Scaling**:
  - **Default / Minimal Data**: $D \le 1 \implies R = 2.4\text{px}$.
  - **Moderate Data**: $D \approx 5\text{–}10 \implies R \approx 5.5\text{px}\text{–}7.8\text{px}$.
  - **High Data**: $D \approx 25 \implies R \approx 12\text{px}$.
  - **Major Hubs**: $D \ge 80 \implies R \approx 20\text{px}\text{–}28\text{px}$.
  - **Vice Versa**: As data decreases, the node smoothly scales down to the baseline default $2.4\text{px}$.
- **Minimap Scaling**:
  - Minimap dots reflect data weight proportionally (`Math.max(1.2, Math.min(3.5, (n.size ?? 2.4) * 0.28))`), highlighting major hubs even in the miniature context overview.
- **HUD Inspector Feedback**:
  - The Context HUD inspector card reports the exact data metrics for the selected concept: direct connections, chunk mentions, document appearances, and exact node radius size (`Size: X.Xpx`).
