# Specification 18: Library Icon & Folder Size Toggle (Large, Medium, Small)

## 1. Overview
Administrators managing rich resource libraries and categories need flexible visual density controls to scan large numbers of files and folders or inspect them with detailed visual art. This spec introduces a 3-tier size toggle (**Large** [default/current], **Medium**, and **Small**) for icons, folders, and resources across the Library.

## 2. Core Capabilities
1. **Size Toggle Controls**:
   - **Toolbar Segmented Control**: Positioned immediately adjacent to the View mode toggle (Grid / List / Columns), a 3-button toggle with dedicated scale glyphs (`size-small`, `size-medium`, `size-large`) allows one-click switching with crisp, uniform stroke-width icons.
   - **Canvas Context Menu**: Right-clicking whitespace in Icon View displays an "Icon & Folder Size" submenu with checked state indicators for Small, Medium, and Large.
   - **Local Storage Persistence**: Preserves user preference via `localStorage.getItem('admin-library-icon-size')`, defaulting to `'large'`.

2. **Visual Hierarchy & Densities**:
   - **Large (Current Default)**:
     - Grid column min-width: `10.5rem`, gap: `1.1rem`.
     - Art dimensions: `4.25rem × 4.25rem` with 16px radius.
     - SVG icon sizes: Folder `38px`, Tag `38px`, Document `36px`, Staged `34px`.
     - Displays full labels, file type badges, metadata pill (item counts), and footer hints.
   - **Medium**:
     - Grid column min-width: `8.25rem`, gap: `0.85rem`.
     - Art dimensions: `3.2rem × 3.2rem` with 12px radius.
     - SVG icon sizes: Folder `30px`, Tag `30px`, Document `28px`, Staged `28px`.
     - Compact labels (12.8px), tight badge padding, compact metadata pill.
   - **Small**:
     - Grid column min-width: `6.25rem`, gap: `0.6rem`.
     - Art dimensions: `2.35rem × 2.35rem` with 9px radius.
     - SVG icon sizes: Folder `22px`, Tag `22px`, Document `20px`, Staged `20px`.
     - Micro labels (11.5px), hidden secondary pills/hints to maximize grid density and mimic macOS Finder small icon layout.

3. **Multi-View Density Harmony**:
   - The `.size-{size}` class cascades from `.finder-content` down to `.finder-table` (List View) and `.col-pane` (Column View), gracefully adapting row heights and paddings for consistent density across all library views.
   - Rubber-band marquee drag selection dynamically calculates bounding boxes from rendered DOM coordinates, ensuring 100% accurate multi-selection regardless of active size tier.
