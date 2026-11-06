# Specs v15 — Nature & Leaves Landing Pages Rebuild and Practitioner Flow Architecture

## 1. Context & Motivation
Direct user request:
> "Now I want you to rebuild the landing pages. Keep the falling leaves, I don't want the logo to have any boxes nor backgrounds. Make it professional, consistent, With SVGs, images, theme is nature and leaves"
> "Practitioner page and flow on the landing page is weird, fix it"

### Identified Structural & Experience Deficiencies
1. **Logo Visual Enclosure**: The logo mark previously sat inside colored rectangular tiles/boxes with borders and background fills in the drawer header and shell, violating the minimalist, pure SVG aesthetic.
2. **Theme Incoherence**: The landing page previously utilized stark burgundy/red gradients (`--rail-top`, `--rail-bottom`), clashing with the organic functional health identity.
3. **Disjointed Practitioner Flow**:
   - The landing page interleaved client-facing education with deep internal practitioner implementation details (e.g. blockquotes regarding anti-hallucination models and architecture specs).
   - The practitioner preview was displayed as an awkward horizontal scrolling strip with minimal avatar circles, lacking clinical context, verified indicators, and clear booking pathways.
   - The directory page (`/practitioners`) and individual profiles (`/coach/{id}`) had inconsistent terminology, boxed styling ("Quiet", "Spotlight"), and missing return navigation breadcrumbs.

---

## 2. Rebuilt Architecture & Design System

### 2.1 Pure SVG Logo Mark (Zero Boxes / Zero Backgrounds)
- Stripped all backgrounds, tiles, borders, and shadows from the `Sprig` SVG wrapper across `PublicNav.svelte`, `PublicFooter.svelte`, `Rail.svelte`, and page headers.
- The logo mark renders as a crisp, unencumbered vector element tinted in botanical emerald (`#2d6a4f` on light surfaces, `#74c69d` on dark forest surfaces).

### 2.2 Nature & Botanical Design Language
- **Canopy Palette**:
  - Forest depths: `#0d2318`, `#173827`, `#1b4332`.
  - Emerald & sage accents: `#2d6a4f`, `#40916c`, `#52b788`, `#74c69d`.
  - Organic linen/stone surfaces: `#fafbf8`, `#f4f8f4`, `#ffffff`.
- **Gentle Falling Leaves (`LeafField.svelte`)**:
  - Embedded as ambient background layers across the Landing Page hero, closing CTA banner, and the Practitioner Directory header.
  - Dynamically tinted via `--leaf-color: rgba(116, 198, 157, 0.45);`.

### 2.3 Cohesive Practitioner & Client Care Journey
1. **Hero & Value Proposition**:
   - Direct dual pathways: "Find a Practitioner" (client search) and "How It Works" (care roadmap), alongside provider exploration links.
   - Custom SVG artwork combining a living botanical stem with an evidence network (Clinical Research, Botanical Monographs, Biomarkers, and Verified Care Plan).
2. **Three-Stage Care Flow**:
   - Stage 01: Match with a Specialist.
   - Stage 02: Private Intake & Health Vault.
   - Stage 03: Grounded, Cited Care Plan.
3. **Featured Practitioner Roster**:
   - Replaced horizontal scroll strip with a responsive 3-column card grid.
   - Displays avatar, verified status ("Accepting New Clients"), years of clinical experience, specialty badges, clinical philosophy excerpt, and direct action: **View Profile & Consult →**.
   - Includes a full directory jump box linking directly to `/practitioners`.
4. **Dedicated Practitioner Platform Section**:
   - Cleanly partitioned from patient messaging into a dedicated provider section.
   - Demonstrates the Knowledge Studio, Cited Traversal Engine, and Clinical Second Check with an interactive consult mockup.
   - Direct CTA: **Apply to Join Network** (`/join`).

### 2.4 Directory & Profile Pages Harmonization
- **Directory (`/practitioners`)**:
  - Natural hero with falling leaves and clean logo.
  - Interactive Filter HUD: search by name, condition, or modality; specialty selector; "Accepting new clients" filter; real-time result counter and reset button.
  - Polished practitioner cards featuring language and experience badges.
- **Practitioner Profile (`/coach/[id]`)**:
  - Breadcrumb navigation (`← Back to Practitioner Directory`).
  - Two-column clinical layout: Left side provides practitioner bio, clinical philosophy, and consultation process; right side provides pinned direct booking (`/signup?practitioner={id}`) and direct messaging form.

---

## 3. Verification & Git Sync
- `npm --prefix web run check`: 0 errors.
- `npm --prefix web run build`: 0 errors (SvelteKit static adapter build complete).
- `.venv/bin/pytest tests/`: 22 passed in 9.45s.
- Synchronized across `develop` and `main` branches.
