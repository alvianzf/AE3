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

### 2.3 100% Client-Centric Landing Page Architecture
- Per user instruction ("Home in Landing page is for Clients"), the primary landing page (`/`) speaks exclusively to clients/patients seeking personalized functional health care.
- **Removed Provider Clutter**: Eliminated internal clinician software pitches, studio architecture mockups, and mixed practitioner onboarding CTAs from the home page.
- **Client-Centric Structure**:
  1. *Hero*: Root-cause functional medicine value proposition, client trust badges, and dual client actions ("Find Your Practitioner" / "Sign Up as a Client").
  2. *What We Help Clients Solve*: Focus areas spanning Gut Health & Digestion, Hormonal & Thyroid Balance, Immune & Autoimmune Support, and Metabolic Health.
  3. *Your Care Journey*: 3-step client progression (Match with a Specialist -> Complete Health Intake -> Receive Grounded Care Plan).
  4. *Featured Practitioners*: Verified practitioner cards highlighting areas of clinical focus, availability, and direct consultation booking.
  5. *Evidence & Nature Pillars*: Root-cause medicine, curated clinical/botanical evidence, independent verification, and patient-owned encrypted data vaults.
  6. *Client Story & Closing CTA*: Testimonial of care transformation and closing invitations for clients to take control of their health journey.
- **Practitioner Pathways Preserved**: Clinical provider onboarding is cleanly partitioned to dedicated top navigation (`/join`) and footer links without distracting patient discovery.

### 2.4 Rebuilt "For Practitioners" Guidance & Application Hub (`/join`)
- Per user instruction ("The For Practitioner page need more text and guidance though"), `/join` was transformed from a minimal standalone card into a comprehensive practitioner landing experience:
  1. *Hero*: High-impact botanical header with falling leaves, clinical value proposition ("Practice at your peak. Arrive at every consult deeply informed"), and key practice stats.
  2. *Augmentation Pillars*: Core tenets explaining why practitioners thrive — clients see human clinicians (never a bot), zero missing information, curated clinical evidence base, and strict tenant isolation.
  3. *Workspace Capabilities*: Interactive patient timelines, biomarker trajectory tracking, grounded consult assistant preview card, and questionnaire engine.
  4. *Onboarding & Vetting Guidance*: 3-step credential review process, eligible practitioner credentials (MD, DO, ND, NP, PA, DC, CNS, IFMCP), and data ownership guarantees.
  5. *Integrated Application*: Streamlined, botanical-styled form with field hints, credential fields, consultation pricing, photo uploads, and client review timelines.

### 2.5 Clinical Positioning & "No AI Facing the Client" Guarantee
- **Clients Never See AI**: All client-facing touchpoints (Home, Practitioner Directory, Profile, FAQ, Terms) emphasize high-touch, empathetic human care. Clients work directly with their human doctor or practitioner; AI operates strictly behind the scenes as a private clinical copilot.
- **The Core Value: "No More Missing Information"**: The platform is explicitly positioned around eliminating missed symptoms, lost lab trends, and fragmented records, ensuring practitioners arrive at every consultation with all dots connected.
- **Removed "Herbal" References**: Replaced over-indexed herbalist wording ("botanical therapeutics", "herbal monographs") with precise clinical terminology ("functional medicine", "clinical protocols", "peer-reviewed clinical studies", "biomarker trajectories"). Nature and botanical themes remain preserved in the visual aesthetics (leaves, foliage, natural organic hues).

### 2.6 Global Public CSS & Design Consistency
- Added unified public tokens and resets in `web/src/routes/(public)/+layout.svelte` (`--pub-forest-dark`, `--pub-emerald`, `--pub-sage-vibrant`, `--pub-linen`, `--pub-border`), giving every public page an organic, warm stone backdrop (`#fbfcf9`) and consistent text styling.
- Standardized buttons (`.btn.filled`, `.btn-primary` -> `#2d6a4f` with hover to `#1b4332`), input fields, badges, and card panels across `pricing`, `faq`, `login`, `signup`, `contact`, `terms`, `privacy`, and `cookies`.
- Removed legacy pink/burgundy `var(--accent)` leaks across public subpages.

---

## 3. Verification & Git Sync
- `npm --prefix web run check`: 0 errors.
- `npm --prefix web run build`: 0 errors (SvelteKit static adapter build complete).
- `.venv/bin/pytest tests/`: 22 passed.
- Synchronized across `develop` and `main` branches.

