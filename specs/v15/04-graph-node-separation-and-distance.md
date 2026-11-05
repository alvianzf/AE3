# Concept Graph: 100% Increased Node Distance & Click-to-Separate Adjacent Nodes

## 1. 100% Increased Graph Distance & Spatial Footprint
- **Link Distance**: Doubled from `120` to `240` to provide double the baseline physical distance between linked concepts.
- **Repulsion Charge**: Increased from `-340` to `-680` with max interaction distance doubled from `850` to `1700`, keeping dense concept hubs comfortably spaced.
- **Collision Padding**: Collision buffer doubled from `+18px` to `+36px` (`radius = (size ?? 6) + 36`), preventing any node overlap or label clipping.
- **Component Orbit Separation**: Disconnected graph components now orbit with base separation of `radius + 680` (doubled from `340`) and staggered offsets up to `360px` to maintain generous breathing room across multiple subgraphs.
- **Zoom Extents & Fit**: Extended minimum zoom scale down to `0.04` (from `0.08`) and dynamic fitting minimum to `0.04` (from `0.12`), allowing the user to comfortably zoom out and fit the 100% larger physical layout into view.

## 2. Click-to-Separate Adjacent Nodes (Radial Blooming)
- **Problem**: When a concept node has several connected neighbors, inspecting their direct relationships and labels in a dense cluster can be visually cramped.
- **Solution**:
  - Clicking any node directly on the canvas or selecting it via search / HUD activates a dynamic radial blooming effect.
  - **1-Hop Adjacent Separation**: All directly connected neighbor nodes are distributed radially around the selected node at an expanded distance $R = \max(300, 240 + m \times 28)\text{px}$ (where $m$ is the count of direct neighbors).
  - **Topological Order Preservation**: Adjacent nodes are sorted by their initial angular direction ($\text{atan2}$) relative to the selected concept before angular assignment, ensuring edges do not cross each other during radial distribution.
  - **Outward Velocity Impulse**: Adjacent nodes receive a smooth outward velocity vector on selection to transition fluidly from their rest position to their radial slots.
  - **Dynamic Link Spring Expansion**: Simulation link force distance dynamically expands to $R$ for edges connected to the selected concept (with increased strength $0.65$), while unselected edges maintain baseline distance $240$.
  - **Centered Framing**: Clicking any concept centers the camera on the focused concept with smooth transition, ensuring the radial ring of adjacent nodes is framed without being cut off by the viewport edge.
  - **Clear Labels & Tags**: Relationship label badges (`affects`, `supports`, `influences`) render crisply along connecting edges, and all adjacent concept labels are rendered with bold text and white contrast halos.
  - **Fluid Deselection & Relaxation**: Clicking the canvas background, clicking the HUD unpin button `×`, or clicking the node again smoothly relaxes all nodes and edge forces back to their default balanced layout.
