# Concept Graph Refinements: Spatial Component Separation, Context Map & Closest Node Highlighting

## 1. Multi-Graph Spatial Separation (Uncluttered Centers)
- **Problem**: When a knowledge graph contains multiple disconnected components (subgraphs/clusters), standard force simulation centering (`forceCenter`) pulls all disconnected clusters into `(width/2, height/2)`, causing them to overlap and clutter in the middle.
- **Solution**:
  - Run BFS on the undirected graph to detect all connected components.
  - Sort components by size and assign each component a distinct center `(cx, cy)`:
    - Primary component at canvas center.
    - Subsequent subgraphs arranged radially with generous spacing ($\ge 340\text{px}$ orbit radius, staggered if many components).
  - Use component-anchored forces (`forceX((d) => d.targetX)`, `forceY((d) => d.targetY)`) instead of a single global `forceCenter`.
  - Increased link distance (from 70 to 120), higher repulsion charge (-340), and increased collision radius buffer (+18px).

## 2. Interactive Context Map (Minimap)
- Positioned in the bottom-left corner of the graph viewer with an interactive `<canvas>`.
- Displays the global topology in miniature with category-colored node dots and faint relationship edges.
- Renders a glowing translucent viewport bounding box indicating the camera's current pan/zoom position on the graph.
- Clicking or dragging on the Context Map immediately pans the main canvas viewport to that region.
- Includes title bar with collapse/expand toggle button.

## 3. Closest Connected Node Highlighting
- When hovering or selecting any concept node $N$:
  - Highlights $N$ with a vibrant accent halo ring and prominent label badge.
  - Finds all directly connected (1-hop) neighbor nodes ("closest nodes") via incoming or outgoing relationships.
  - Keeps $N$ and its closest connected nodes at full opacity (1.0), with clean category fills, distinct accent rings, and always-visible labels.
  - Renders connecting edges with thicker stroke (`#9c3f5a`) and relationship label badges (`transform.k > 0.7`).
  - Dims all unrelated nodes and edges down to subtle ghost opacity (0.14), directing instant focus to the concept and its immediate neighborhood.

## 4. Context HUD (Concept Inspector Card)
- Floating glassmorphism card positioned in the top-left:
  - **Selected / Hovered State**:
    - Concept name and category badge.
    - Connection count, mentions count, and cluster number.
    - "Closest Connected Concepts" section with interactive chips for each 1-hop neighbor (showing neighbor name and relationship tag like `INFLUENCES`, `TREATS`, `REGULATES`).
    - Clicking any neighbor chip smoothly centers and focuses the camera on that neighbor.
  - **Default Overview State**:
    - Displays total concept count, relation count, and number of distinct graph clusters.
    - Interactive helper tip prompting exploration.
- Integrated search input in the toolbar allowing instant concept lookup and focus.
