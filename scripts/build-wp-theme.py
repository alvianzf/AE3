#!/usr/bin/env python3
"""Build the WordPress theme for the public marketing site from web-build/.

The landing page and the static marketing pages are prerendered by
`npm run build`, so the theme is generated from that rendered HTML rather
than hand-translated out of Svelte: the markup and the compiled scoped
class names (svelte-xxxxxxx) match the stylesheets byte for byte, which is
what keeps the WordPress site pixel-identical to the SvelteKit one.

Re-run after any design change to the public pages:
    python3 scripts/build-wp-theme.py
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "web-build"
OUT = ROOT / "wp-theme" / "fhc"
THEME_URI = "/wp-content/themes/fhc"

# source slug -> (template filename, WP page title). None = the front page.
PAGES: dict[str, tuple[str, str | None]] = {
    "index": ("front-page.php", None),
    "pricing": ("page-pricing.php", "Pricing"),
    "faq": ("page-faq.php", "FAQ"),
    "privacy": ("page-privacy.php", "Privacy policy"),
    "terms": ("page-terms.php", "Terms of Service"),
    "cookies": ("page-cookies.php", "Cookie policy"),
}

# PublicNav.svelte drives navigation from JS click handlers, so every nav
# link in the prerendered HTML is href="/". Copied as-is, the static site
# would have a nav where every item silently goes to the homepage.
LINK_TARGETS = {
    "Our approach": "/#approach",
    "How it works": "/#how",
    "Programs": "/#programs",
    "About us": "/#about",
    "Book a free intro call": "/#book",
    "Book your free 15-min intro call": "/#book",
    "View programs": "/#programs",
}

HERO_TITLE = ("Personalised hormone, metabolic, gut and longevity care "
              "for women in midlife.")
HERO_SUB = "Because your biology is unique, your health plan should be too."

SVELTE_SCOPE = "svelte-1wmlbsq"  # PublicNav's scoped class


def read(slug: str) -> str:
    return (SRC / f"{slug}.html").read_text(encoding="utf-8")


def clean(html: str) -> str:
    """Drop Svelte's hydration comments and the SvelteKit bootstrap script.

    The bootstrap script would try to hydrate an app that isn't loaded;
    the ld+json block is real SEO content and is kept.
    """
    html = re.sub(r"<script(?![^>]*ld\+json)[^>]*>.*?</script>", "", html, flags=re.S)
    html = re.sub(r"<!--(?!\[if).*?-->", "", html, flags=re.S)
    return html


def retarget_links(html: str) -> str:
    """Give the JS-driven nav links real hrefs (see LINK_TARGETS)."""
    def sub(m: re.Match) -> str:
        attrs, inner = m.group(1), m.group(2)
        label = re.sub(r"<[^>]+>", "", inner).strip()
        target = LINK_TARGETS.get(label)
        return f'<a href="{target}"{attrs}>{inner}</a>' if target else m.group(0)

    return re.sub(r'<a href="/"([^>]*)>(.*?)</a>', sub, html, flags=re.S)


def localise_assets(html: str) -> str:
    """Point image references at the theme's own copies."""
    return html.replace("/images/", f"{THEME_URI}/assets/images/")


def body_of(html: str) -> str:
    return html[html.find("<body"):]


def main_inner(html: str) -> str:
    body = body_of(html)
    start = body.find("<main")
    start = body.find(">", start) + 1
    return body[start:body.find("</main>")]


def css_files(html: str) -> list[str]:
    return re.findall(r"_app/immutable/assets/([^\"']+\.css)", html)


def mobile_sheet() -> str:
    """PublicNav renders this only when the menu is open, so it never makes
    it into the prerendered HTML — but its styles are already in the
    compiled CSS. Emitted here so the hamburger has something to toggle;
    without it, mobile visitors get a button that does nothing (.links and
    .cta are display:none under 760px)."""
    items = "".join(
        f'<a href="{LINK_TARGETS[label]}" class="{SVELTE_SCOPE}">{label}</a>'
        for label in ("Our approach", "How it works", "Programs", "About us")
    )
    cta = (f'<a href="/#book" class="sheet-cta {SVELTE_SCOPE}">'
           f"Book a free intro call</a>")
    return (f'<nav class="mobile-sheet {SVELTE_SCOPE}" aria-label="Main" '
            f'id="fhc-mobile-sheet" hidden>{items}{cta}</nav>')


def build() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets" / "css").mkdir(parents=True)

    index = read("index")

    # ---- shared chrome -------------------------------------------------
    # Only the <header>/<footer> elements are taken; the SvelteKit wrappers
    # around them (.public-shell, the display:contents hydration div) are
    # dropped and re-emitted by header.php/footer.php. Carrying them over
    # verbatim nests .public-shell twice, and it sets min-height:100vh plus
    # display:flex -- two of them stacked breaks the page layout.
    body = body_of(index)
    chrome = retarget_links(localise_assets(clean(body)))

    header_html = chrome[chrome.find("<header"):
                         chrome.find("</header>") + len("</header>")]
    header_html = header_html.replace("</header>", mobile_sheet() + "</header>")

    footer_html = chrome[chrome.find("<footer"):
                         chrome.find("</footer>") + len("</footer>")]

    (OUT / "header.php").write_text(HEADER_PHP % header_html, encoding="utf-8")
    (OUT / "footer.php").write_text(FOOTER_PHP % footer_html, encoding="utf-8")

    # ---- page templates ------------------------------------------------
    all_css: list[str] = []
    per_page_css: dict[str, list[str]] = {}
    for slug, (template, _title) in PAGES.items():
        html = read(slug)
        content = retarget_links(localise_assets(clean(main_inner(html))))
        if slug == "index":
            content = content.replace(
                HERO_TITLE,
                "<?php echo esc_html( get_theme_mod( 'fhc_hero_title', "
                f"'{HERO_TITLE}' ) ); ?>")
            content = content.replace(
                HERO_SUB,
                "<?php echo esc_html( get_theme_mod( 'fhc_hero_sub', "
                f"'{HERO_SUB}' ) ); ?>")
        (OUT / template).write_text(
            "<?php get_header(); ?>\n" + content.strip()
            + "\n<?php get_footer(); ?>\n", encoding="utf-8")

        names = css_files(html)
        per_page_css[slug] = names
        for n in names:
            if n not in all_css:
                all_css.append(n)

    for name in all_css:
        shutil.copy(SRC / "_app" / "immutable" / "assets" / name,
                    OUT / "assets" / "css" / name)

    shutil.copytree(SRC / "images", OUT / "assets" / "images")

    (OUT / "functions.php").write_text(
        functions_php(per_page_css), encoding="utf-8")
    (OUT / "style.css").write_text(STYLE_CSS, encoding="utf-8")
    (OUT / "assets" / "theme.js").write_text(THEME_JS, encoding="utf-8")
    (OUT / "assets" / "theme.css").write_text(THEME_CSS, encoding="utf-8")
    (OUT / "index.php").write_text(INDEX_PHP, encoding="utf-8")

    print(f"theme written to {OUT}")
    print(f"  templates: {len(PAGES)}  css: {len(all_css)}")


HEADER_PHP = """<?php
/**
 * Generated by scripts/build-wp-theme.py - do not edit by hand.
 * Markup mirrors PublicNav.svelte as compiled into web-build/.
 */
?><!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
<meta charset="<?php bloginfo( 'charset' ); ?>" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<div class="public-shell svelte-1l0quee">
%s
<main class="svelte-1l0quee">
"""

FOOTER_PHP = """<?php
/** Generated by scripts/build-wp-theme.py - do not edit by hand. */
?>
</main>
%s
</div>
<?php wp_footer(); ?>
</body>
</html>
"""

INDEX_PHP = """<?php
/**
 * Fallback template. Every public page has its own page-{slug}.php, so this
 * only renders if a post/page is added in wp-admin without one.
 */
get_header(); ?>
<section class="section svelte-13wmnd"><div class="container">
<?php while ( have_posts() ) : the_post(); ?>
  <h1 class="svelte-13wmnd"><?php the_title(); ?></h1>
  <div><?php the_content(); ?></div>
<?php endwhile; ?>
</div></section>
<?php get_footer(); ?>
"""

STYLE_CSS = """/*
Theme Name: Functional Health Collaborative
Theme URI: https://functionalhealthcollab.com
Description: Marketing site theme. Generated from the SvelteKit build by
  scripts/build-wp-theme.py so the markup and compiled scoped CSS match the
  app's public pages exactly. Regenerate rather than editing by hand.
Version: 1.0.0
Requires at least: 6.0
Requires PHP: 8.0
Text Domain: fhc
*/
"""

# The hamburger has no drawer in the prerendered markup (PublicNav only
# renders .mobile-sheet when open), so the toggle is reimplemented here.
THEME_JS = """(function () {
  var btn = document.querySelector('.hamburger');
  var sheet = document.getElementById('fhc-mobile-sheet');
  if (!btn || !sheet) return;
  btn.addEventListener('click', function () {
    var open = !sheet.hasAttribute('hidden');
    if (open) { sheet.setAttribute('hidden', ''); }
    else { sheet.removeAttribute('hidden'); }
    btn.setAttribute('aria-expanded', String(!open));
  });
  sheet.addEventListener('click', function (e) {
    if (e.target.tagName === 'A') {
      sheet.setAttribute('hidden', '');
      btn.setAttribute('aria-expanded', 'false');
    }
  });
})();
"""

# Only what the compiled CSS can't cover on its own.
THEME_CSS = """/* The sticky header would otherwise cover the section an in-page
   anchor lands on. */
html { scroll-behavior: smooth; }
section[id] { scroll-margin-top: 4.5rem; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }

/* PublicNav.svelte only ever renders .mobile-sheet while the drawer is
   open, so its compiled rule is an unconditional `display: flex`. This
   theme instead ships the markup once and toggles [hidden] -- and a bare
   `display: flex` beats the browser's `[hidden] { display: none }`, so
   without these two rules the drawer renders inline on every page, on
   desktop included (caught by a screenshot diff: +269px of page height). */
.mobile-sheet[hidden] { display: none !important; }
@media (min-width: 761px) { .mobile-sheet { display: none !important; } }
"""


def functions_php(per_page_css: dict[str, list[str]]) -> str:
    lines = [
        "<?php",
        "/** Generated by scripts/build-wp-theme.py - do not edit by hand. */",
        "",
        "// slug => the stylesheets that page needs, in the order the",
        "// SvelteKit build emitted them (cascade order is load-bearing).",
        "function fhc_page_styles() {",
        "    return array(",
    ]
    for slug, names in per_page_css.items():
        arr = ", ".join(f"'{n}'" for n in names)
        lines.append(f"        '{slug}' => array( {arr} ),")
    lines += [
        "    );",
        "}",
        "",
        "function fhc_current_slug() {",
        "    if ( is_front_page() ) { return 'index'; }",
        "    $post = get_post();",
        "    return $post ? $post->post_name : 'index';",
        "}",
        "",
        "function fhc_enqueue() {",
        "    $uri = get_template_directory_uri();",
        "    wp_enqueue_style(",
        "        'fhc-fonts',",
        "        'https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,600;12..96,700&family=Figtree:wght@400;500;600&display=swap',",
        "        array(), null );",
        "    $styles = fhc_page_styles();",
        "    $slug   = fhc_current_slug();",
        "    $files  = isset( $styles[ $slug ] ) ? $styles[ $slug ] : $styles['index'];",
        "    $prev   = array( 'fhc-fonts' );",
        "    foreach ( $files as $i => $file ) {",
        "        $handle = 'fhc-css-' . $i;",
        "        wp_enqueue_style( $handle, $uri . '/assets/css/' . $file, $prev, null );",
        "        $prev = array( $handle );",
        "    }",
        "    wp_enqueue_style( 'fhc-theme', $uri . '/assets/theme.css', $prev, null );",
        "    wp_enqueue_script( 'fhc-theme', $uri . '/assets/theme.js', array(), null, true );",
        "}",
        "add_action( 'wp_enqueue_scripts', 'fhc_enqueue' );",
        "",
        "// Each page keeps the <title>/meta/JSON-LD the SvelteKit build",
        "// generated for it, so search snippets and link previews don't",
        "// regress when the page moves to WordPress.",
        "function fhc_seo_head() {",
        "    $file = get_template_directory() . '/assets/seo/' . fhc_current_slug() . '.html';",
        "    if ( is_readable( $file ) ) { readfile( $file ); }",
        "}",
        "",
        "function fhc_customize( $wp_customize ) {",
        "    $wp_customize->add_section( 'fhc_hero', array(",
        "        'title'    => __( 'Landing hero', 'fhc' ),",
        "        'priority' => 30,",
        "    ) );",
        "    $wp_customize->add_setting( 'fhc_hero_title', array(",
        f"        'default'           => {php_str(HERO_TITLE)},",
        "        'sanitize_callback' => 'sanitize_text_field',",
        "    ) );",
        "    $wp_customize->add_control( 'fhc_hero_title', array(",
        "        'label'   => __( 'Hero headline', 'fhc' ),",
        "        'section' => 'fhc_hero',",
        "        'type'    => 'textarea',",
        "    ) );",
        "    $wp_customize->add_setting( 'fhc_hero_sub', array(",
        f"        'default'           => {php_str(HERO_SUB)},",
        "        'sanitize_callback' => 'sanitize_text_field',",
        "    ) );",
        "    $wp_customize->add_control( 'fhc_hero_sub', array(",
        "        'label'   => __( 'Hero subheading', 'fhc' ),",
        "        'section' => 'fhc_hero',",
        "        'type'    => 'textarea',",
        "    ) );",
        "}",
        "add_action( 'customize_register', 'fhc_customize' );",
        "",
        "add_action( 'after_setup_theme', function () {",
        "    add_theme_support( 'post-thumbnails' );",
        "    // header.php has no static <title> of its own (removed in favor",
        "    // of Rank Math's own title/meta/schema output, which needs this",
        "    // declared or wp_head() renders no <title> tag at all).",
        "    add_theme_support( 'title-tag' );",
        "} );",
        "",
    ]
    return "\n".join(lines)


def php_str(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


if __name__ == "__main__":
    build()
