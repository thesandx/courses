#!/usr/bin/env python3
"""Build the static HTML docs site for the Data Platform Mastery course.

Renders every course README/markdown file into a styled, self-navigating
static site under <repo-root>/docs/data_platform_mastery/ (GitHub-Pages-ready:
enable Pages with source = master branch, /docs folder).

Usage:
    pip install markdown pymdown-extensions pygments
    python data_platform_mastery/tools/build_docs.py

Regenerate whenever a README changes; the output is committed so the site
works without a build step.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter

COURSE_DIR = Path(__file__).resolve().parents[1]          # data_platform_mastery/
REPO_ROOT = COURSE_DIR.parent                             # courses/
OUT_DIR = REPO_ROOT / "docs" / "data_platform_mastery"

GITHUB_COURSES = "https://github.com/thesandx/courses/blob/master"
GITHUB_DE_INTERVIEW = "https://github.com/thesandx/DE_interview/blob/main"


@dataclass
class Page:
    src: str            # path relative to COURSE_DIR
    out: str            # output html filename
    nav: str            # short label for the sidebar
    group: str          # sidebar group
    badge: str = ""     # small chip shown in sidebar / hero (e.g. release tag)


PAGES: list[Page] = [
    Page("README.md", "index.html", "Course Overview", "Start Here"),
    Page("PROJECT_CHARTER.md", "project-charter.html", "Project Charter", "Start Here"),
    Page("INTERVIEW_MAP.md", "interview-map.html", "Interview Map", "Start Here"),
    Page("phase_00_orientation/README.md", "phase-00.html", "00 · Orientation", "Build Phases"),
    Page("phase_01_foundation/README.md", "phase-01.html", "01 · Foundation", "Build Phases", "v0.1.0"),
    Page("phase_02_metadata_core/README.md", "phase-02.html", "02 · Metadata Core", "Build Phases", "v0.2.0"),
    Page("phase_03_batch_ingestion/README.md", "phase-03.html", "03 · Batch Ingestion", "Build Phases", "v0.3.0"),
    Page("phase_04_streaming_kafka/README.md", "phase-04.html", "04 · Streaming & Kafka", "Build Phases", "v0.4.0"),
    Page("phase_05_spark_processing/README.md", "phase-05.html", "05 · Spark Processing", "Build Phases", "v0.5.0"),
    Page("phase_06_bigquery_serving/README.md", "phase-06.html", "06 · BigQuery Serving", "Build Phases", "v0.6.0"),
    Page("phase_07_orchestration/README.md", "phase-07.html", "07 · Orchestration", "Build Phases", "v0.7.0"),
    Page("phase_08_data_quality_recon/README.md", "phase-08.html", "08 · Quality & Recon", "Build Phases", "v0.8.0"),
    Page("phase_09_governance/README.md", "phase-09.html", "09 · Governance", "Build Phases", "v0.9.0"),
    Page("phase_10_observability_finops/README.md", "phase-10.html", "10 · Observability & FinOps", "Build Phases", "v0.10.0"),
    Page("phase_11_streamlit_control_plane/README.md", "phase-11.html", "11 · Streamlit Control Plane", "Build Phases", "v0.11.0"),
    Page("phase_12_platform_apis/README.md", "phase-12.html", "12 · Platform APIs", "Build Phases", "v0.12.0"),
    Page("phase_13_scale_hardening/README.md", "phase-13.html", "13 · Scale & Hardening", "Build Phases", "v0.13.0"),
    Page("phase_14_open_source_launch/README.md", "phase-14.html", "14 · Open-Source Launch", "Build Phases", "v1.0.0"),
    Page("interview_gauntlet/README.md", "interview-gauntlet.html", "Interview Gauntlet", "Endgame", "🎯"),
]

# ---------------------------------------------------------------- markdown --

def make_renderer() -> markdown.Markdown:
    return markdown.Markdown(
        extensions=[
            "tables",
            "attr_list",
            "md_in_html",
            "toc",
            "pymdownx.superfences",
            "pymdownx.highlight",
            "pymdownx.inlinehilite",
            "pymdownx.tasklist",
            "pymdownx.tilde",
        ],
        extension_configs={
            "toc": {"permalink": "#", "permalink_title": "Link to this section"},
            "pymdownx.highlight": {"css_class": "highlight", "guess_lang": False},
            "pymdownx.tasklist": {"custom_checkbox": True},
            "pymdownx.superfences": {
                "custom_fences": [{
                    "name": "mermaid",
                    "class": "mermaid",
                    "format": _mermaid_fence,
                }],
            },
        },
        output_format="html5",
    )


def _mermaid_fence(source, language, css_class, options, md, **kwargs):
    return f'<pre class="mermaid">{html.escape(source)}</pre>'


# ------------------------------------------------------------ link rewriting --

MD_LINK_MAP = {p.src: p.out for p in PAGES}


def rewrite_href(href: str) -> str:
    if href.startswith(("http://", "https://", "#", "mailto:")):
        return href
    clean = re.sub(r"^(\./)+", "", href)
    # Self-reference to the rendered docs site -> its own index page.
    if "docs/data_platform_mastery" in clean:
        return "index.html"
    # Cross-repo reference: DE_interview lives in its own repository.
    m = re.match(r"^(?:\.\./)+DE_interview/(.+)$", clean)
    if m:
        return f"{GITHUB_DE_INTERVIEW}/{m.group(1)}"
    # Sibling course in this repo -> GitHub blob view.
    m = re.match(r"^(?:\.\./)*(gcp_data_engineer_mastery|ai_engineering_mastery|oops_mastery)/(.+)$", clean)
    if m:
        return f"{GITHUB_COURSES}/{m.group(1)}/{m.group(2)}"
    # Intra-course markdown links -> local pages (source pages may live in subdirs).
    stripped = re.sub(r"^(\.\./)+", "", clean)
    if stripped in MD_LINK_MAP:
        return MD_LINK_MAP[stripped]
    if stripped.endswith(".md"):
        # Unmapped markdown file inside the course -> GitHub blob view.
        return f"{GITHUB_COURSES}/data_platform_mastery/{stripped}"
    return href


def postprocess(body: str) -> str:
    body = re.sub(r'href="([^"]+)"', lambda m: f'href="{rewrite_href(m.group(1))}"', body)
    # Horizontal scroll for wide tables.
    body = body.replace("<table>", '<div class="table-wrap"><table>').replace(
        "</table>", "</table></div>")
    return body


# ----------------------------------------------------------------- template --

FAVICON = ("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
           "<text y='.9em' font-size='90'>⚒️</text></svg>")

# Vendored locally (docs/data_platform_mastery/mermaid.min.js) so diagrams render
# offline and on GitHub Pages without any CDN dependency.
MERMAID_SCRIPT = """<script src="mermaid.min.js"></script>
<script>
  mermaid.initialize({
    startOnLoad: true,
    theme: document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "neutral",
    themeVariables: { fontFamily: "inherit" }
  });
</script>"""

PAGE_TMPL = """<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Data Platform Mastery</title>
<meta name="description" content="Data Platform Mastery — build an open-source metadata-driven ETL platform on GCP.">
<link rel="icon" href="{favicon}">
<link rel="stylesheet" href="style.css">
<script>
  (function () {{
    var t = localStorage.getItem("dpm-theme");
    if (!t) t = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", t);
  }})();
</script>
</head>
<body>
<button class="menu-btn" id="menuBtn" aria-label="Toggle navigation">☰</button>
<div class="layout">
  <aside class="sidebar" id="sidebar">
    <a class="brand" href="index.html">
      <span class="brand-mark">⚒️</span>
      <span>
        <span class="brand-title">Data Platform Mastery</span>
        <span class="brand-sub">Build PipeForge on GCP</span>
      </span>
    </a>
    <nav>{nav}</nav>
    <div class="sidebar-foot">
      <button id="themeBtn" class="theme-btn" title="Toggle dark mode">🌗 Theme</button>
      <a href="https://github.com/thesandx/courses/tree/master/data_platform_mastery">GitHub ↗</a>
    </div>
  </aside>
  <div class="main">
    <header class="crumbs">
      <span class="crumb-group">{group}</span>
      <span class="crumb-sep">/</span>
      <span class="crumb-page">{nav_label}</span>
      {badge_html}
    </header>
    <div class="content-wrap">
      <main class="content">
{body}
        <nav class="pager">
          {prev_html}
          {next_html}
        </nav>
        <footer class="page-foot">
          Generated from <a href="{src_url}"><code>{src}</code></a> ·
          Part of the <a href="index.html">Data Platform Mastery</a> course.
        </footer>
      </main>
      <aside class="toc-rail">{toc}</aside>
    </div>
  </div>
</div>
{mermaid_script}
<script>
  document.getElementById("themeBtn").addEventListener("click", function () {{
    var cur = document.documentElement.getAttribute("data-theme");
    localStorage.setItem("dpm-theme", cur === "dark" ? "light" : "dark");
    location.reload();   // simplest way to re-render mermaid + pygments in the new theme
  }});
  document.getElementById("menuBtn").addEventListener("click", function () {{
    document.getElementById("sidebar").classList.toggle("open");
  }});
</script>
</body>
</html>
"""


def build_css() -> str:
    light_hl = HtmlFormatter(style="friendly").get_style_defs("html[data-theme='light'] .highlight")
    dark_hl = HtmlFormatter(style="material").get_style_defs("html[data-theme='dark'] .highlight")
    return f"""/* Generated by tools/build_docs.py — do not edit by hand. */
:root {{
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
}}
html[data-theme='light'] {{
  --bg: #f6f7f9; --surface: #ffffff; --sidebar: #101422; --sidebar-ink: #c7cbe0;
  --ink: #1c2333; --muted: #5b6478; --border: #e4e7ee;
  --accent: #4f46e5; --accent-ink: #4338ca; --accent-soft: #eef0ff;
  --chip-bg: #eef0ff; --chip-ink: #4338ca; --quote-bg: #f4f5ff;
  --code-bg: #f0f1f5; --shadow: 0 1px 3px rgba(16,20,34,.07), 0 8px 24px rgba(16,20,34,.05);
}}
html[data-theme='dark'] {{
  --bg: #0c111d; --surface: #131a2b; --sidebar: #0a0e18; --sidebar-ink: #aab1cc;
  --ink: #e4e8f4; --muted: #8b94ad; --border: #232d45;
  --accent: #8b93ff; --accent-ink: #a5abff; --accent-soft: #1c2140;
  --chip-bg: #1c2140; --chip-ink: #a5abff; --quote-bg: #161d33;
  --code-bg: #1a2136; --shadow: 0 1px 3px rgba(0,0,0,.4);
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{ margin: 0; font-family: var(--sans); background: var(--bg); color: var(--ink);
       line-height: 1.65; font-size: 16px; }}
.layout {{ display: flex; min-height: 100vh; }}

/* ---------------- sidebar ---------------- */
.sidebar {{ width: 288px; flex: 0 0 288px; background: var(--sidebar); color: var(--sidebar-ink);
  position: sticky; top: 0; height: 100vh; overflow-y: auto; padding: 20px 14px 16px;
  display: flex; flex-direction: column; gap: 14px; scrollbar-width: thin; }}
.brand {{ display: flex; gap: 10px; align-items: center; text-decoration: none; color: #fff;
  padding: 6px 8px; }}
.brand-mark {{ font-size: 26px; }}
.brand-title {{ display: block; font-weight: 700; font-size: 15.5px; letter-spacing: .2px; }}
.brand-sub {{ display: block; font-size: 12px; color: var(--sidebar-ink); opacity: .85; }}
.nav-group {{ margin: 10px 0 2px; padding: 0 8px; font-size: 10.5px; font-weight: 700;
  letter-spacing: .14em; text-transform: uppercase; color: #6c7590; }}
.nav-item {{ display: flex; align-items: center; gap: 8px; padding: 6px 10px; margin: 1px 0;
  border-radius: 8px; color: var(--sidebar-ink); text-decoration: none; font-size: 13.5px; }}
.nav-item:hover {{ background: rgba(255,255,255,.06); color: #fff; }}
.nav-item.active {{ background: var(--accent); color: #fff; font-weight: 600; }}
.nav-item .tag {{ margin-left: auto; font-family: var(--mono); font-size: 10px; opacity: .75; }}
.sidebar-foot {{ margin-top: auto; display: flex; gap: 10px; align-items: center;
  padding: 10px 8px 0; border-top: 1px solid rgba(255,255,255,.08); font-size: 12.5px; }}
.sidebar-foot a {{ color: var(--sidebar-ink); text-decoration: none; margin-left: auto; }}
.sidebar-foot a:hover {{ color: #fff; }}
.theme-btn {{ background: rgba(255,255,255,.08); color: var(--sidebar-ink); border: 0;
  border-radius: 8px; padding: 6px 10px; cursor: pointer; font-size: 12.5px; }}
.theme-btn:hover {{ color: #fff; }}
.menu-btn {{ display: none; position: fixed; z-index: 60; top: 12px; left: 12px;
  background: var(--surface); color: var(--ink); border: 1px solid var(--border);
  border-radius: 10px; padding: 7px 12px; font-size: 16px; cursor: pointer; box-shadow: var(--shadow); }}

/* ---------------- main column ---------------- */
.main {{ flex: 1; min-width: 0; }}
.crumbs {{ position: sticky; top: 0; z-index: 40; display: flex; align-items: center; gap: 8px;
  padding: 12px 28px; background: color-mix(in srgb, var(--bg) 88%, transparent);
  backdrop-filter: blur(8px); border-bottom: 1px solid var(--border); font-size: 13px;
  color: var(--muted); }}
.crumb-page {{ color: var(--ink); font-weight: 600; }}
.badge {{ font-family: var(--mono); font-size: 11px; background: var(--chip-bg);
  color: var(--chip-ink); border-radius: 999px; padding: 2px 10px; margin-left: 6px; }}
.content-wrap {{ display: flex; gap: 32px; max-width: 1200px; margin: 0 auto; padding: 34px 28px 60px; }}
.content {{ min-width: 0; max-width: 830px; flex: 1; }}

/* ---------------- toc rail ---------------- */
.toc-rail {{ width: 230px; flex: 0 0 230px; position: sticky; top: 64px;
  align-self: flex-start; max-height: calc(100vh - 90px); overflow-y: auto;
  font-size: 12.5px; padding-top: 6px; }}
.toc-rail .toc-title {{ font-size: 10.5px; font-weight: 700; letter-spacing: .14em;
  text-transform: uppercase; color: var(--muted); margin-bottom: 8px; }}
.toc-rail a {{ display: block; color: var(--muted); text-decoration: none;
  padding: 3px 0 3px 10px; border-left: 2px solid var(--border); }}
.toc-rail a:hover {{ color: var(--accent-ink); border-left-color: var(--accent); }}

/* ---------------- typography ---------------- */
.content h1 {{ font-size: 30px; line-height: 1.25; letter-spacing: -.02em; margin: 4px 0 18px; }}
.content h2 {{ font-size: 21.5px; letter-spacing: -.01em; margin: 42px 0 12px; padding-top: 10px; }}
.content h3 {{ font-size: 17px; margin: 30px 0 10px; }}
.content h1 .headerlink, .content h2 .headerlink, .content h3 .headerlink, .content h4 .headerlink {{
  opacity: 0; margin-left: 8px; text-decoration: none; color: var(--accent); font-weight: 400; }}
.content h1:hover .headerlink, .content h2:hover .headerlink,
.content h3:hover .headerlink, .content h4:hover .headerlink {{ opacity: .8; }}
.content a {{ color: var(--accent-ink); text-decoration: none; border-bottom: 1px solid transparent; }}
.content a:hover {{ border-bottom-color: var(--accent-ink); }}
.content p {{ margin: 12px 0; }}
.content li {{ margin: 5px 0; }}
.content hr {{ border: 0; border-top: 1px solid var(--border); margin: 36px 0; }}
.content strong {{ font-weight: 650; }}

/* blockquotes as callout cards */
.content blockquote {{ margin: 20px 0; padding: 14px 18px; background: var(--quote-bg);
  border-left: 4px solid var(--accent); border-radius: 0 10px 10px 0; color: var(--ink); }}
.content blockquote p {{ margin: 6px 0; }}

/* code */
.content code {{ font-family: var(--mono); font-size: 13.2px; background: var(--code-bg);
  padding: 2px 6px; border-radius: 6px; }}
.content .highlight {{ margin: 18px 0; border: 1px solid var(--border); border-radius: 12px;
  overflow: hidden; box-shadow: var(--shadow); }}
.content .highlight pre {{ margin: 0; padding: 14px 16px; overflow-x: auto; line-height: 1.55;
  font-family: var(--mono); font-size: 13.2px; }}
.content .highlight code {{ background: transparent; padding: 0; border-radius: 0; }}
pre.mermaid {{ display: flex; justify-content: flex-start; background: var(--surface);
  border: 1px solid var(--border); border-radius: 12px; padding: 18px; margin: 20px 0;
  overflow-x: auto; box-shadow: var(--shadow); }}
pre.mermaid svg {{ min-width: 1150px; height: auto; }}  /* scale up via viewBox; container scrolls */

/* tables */
.table-wrap {{ overflow-x: auto; margin: 18px 0; border: 1px solid var(--border);
  border-radius: 12px; box-shadow: var(--shadow); background: var(--surface); }}
.content table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
.content th {{ text-align: left; background: var(--accent-soft); color: var(--accent-ink);
  font-size: 12px; letter-spacing: .05em; text-transform: uppercase; padding: 10px 14px;
  border-bottom: 1px solid var(--border); white-space: nowrap; }}
.content td {{ padding: 9px 14px; border-bottom: 1px solid var(--border); vertical-align: top; }}
.content tr:last-child td {{ border-bottom: 0; }}
.content tbody tr:hover {{ background: color-mix(in srgb, var(--accent-soft) 40%, transparent); }}

/* task lists */
.content .task-list-item {{ list-style: none; margin-left: -22px; }}
.content .task-list-control {{ margin-right: 8px; }}
.content .task-list-indicator {{ display: inline-block; width: 15px; height: 15px;
  border: 1.5px solid var(--accent); border-radius: 4px; vertical-align: -2px; margin-right: 9px; }}
.content input[type="checkbox"]:checked ~ .task-list-indicator {{ background: var(--accent); }}

/* details */
.content details {{ background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 12px 16px; margin: 16px 0; box-shadow: var(--shadow); }}
.content summary {{ cursor: pointer; font-weight: 600; color: var(--accent-ink); }}

/* pager + footer */
.pager {{ display: flex; gap: 14px; margin-top: 54px; }}
.pager a {{ flex: 1; display: block; padding: 14px 16px; border: 1px solid var(--border);
  border-radius: 12px; background: var(--surface); text-decoration: none; color: var(--ink);
  box-shadow: var(--shadow); }}
.pager a:hover {{ border-color: var(--accent); }}
.pager .dir {{ display: block; font-size: 11px; letter-spacing: .1em; text-transform: uppercase;
  color: var(--muted); margin-bottom: 3px; }}
.pager .next {{ text-align: right; }}
.pager .label {{ font-weight: 600; color: var(--accent-ink); }}
.page-foot {{ margin-top: 34px; padding-top: 16px; border-top: 1px solid var(--border);
  font-size: 12.5px; color: var(--muted); }}
.page-foot a {{ color: var(--muted); }}

/* ---------------- responsive ---------------- */
@media (max-width: 1080px) {{ .toc-rail {{ display: none; }} }}
@media (max-width: 860px) {{
  .menu-btn {{ display: block; }}
  .sidebar {{ position: fixed; z-index: 50; left: -300px; transition: left .2s ease; }}
  .sidebar.open {{ left: 0; box-shadow: 0 0 0 100vmax rgba(0,0,0,.45); }}
  .crumbs {{ padding-left: 64px; }}
  .content-wrap {{ padding: 24px 18px 50px; }}
  .content h1 {{ font-size: 24px; }}
}}

/* ---------------- pygments ---------------- */
{light_hl}
{dark_hl}
html[data-theme='light'] .highlight pre {{ background: #ffffff; }}
html[data-theme='dark'] .highlight pre {{ background: #16203a; }}
"""


# ------------------------------------------------------------------ build --

def build_nav(active: Page) -> str:
    out, current_group = [], None
    for p in PAGES:
        if p.group != current_group:
            out.append(f'<div class="nav-group">{html.escape(p.group)}</div>')
            current_group = p.group
        cls = "nav-item active" if p is active else "nav-item"
        tag = f'<span class="tag">{html.escape(p.badge)}</span>' if p.badge else ""
        out.append(f'<a class="{cls}" href="{p.out}">{html.escape(p.nav)}{tag}</a>')
    return "\n".join(out)


def build_toc(md: markdown.Markdown) -> str:
    tokens = [t for t in getattr(md, "toc_tokens", []) if t["level"] == 1]
    items = []
    for t in tokens:
        for child in t.get("children", []):
            items.append((child["id"], child["name"]))
    if not tokens or not items:
        for t in getattr(md, "toc_tokens", []):
            if t["level"] == 2:
                items.append((t["id"], t["name"]))
    if not items:
        return ""
    links = "\n".join(f'<a href="#{hid}">{html.escape(re.sub(r"<[^>]+>", "", name))}</a>'
                      for hid, name in items)
    return f'<div class="toc-title">On this page</div>\n{links}'


def page_title(text: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return re.sub(r"[*`]", "", m.group(1)).strip() if m else "Data Platform Mastery"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "style.css").write_text(build_css(), encoding="utf-8")

    for i, page in enumerate(PAGES):
        src_path = COURSE_DIR / page.src
        text = src_path.read_text(encoding="utf-8")
        md = make_renderer()
        body = postprocess(md.convert(text))

        prev_p = PAGES[i - 1] if i > 0 else None
        next_p = PAGES[i + 1] if i < len(PAGES) - 1 else None
        prev_html = (f'<a class="prev" href="{prev_p.out}"><span class="dir">← Previous</span>'
                     f'<span class="label">{html.escape(prev_p.nav)}</span></a>') if prev_p else "<span></span>"
        next_html = (f'<a class="next" href="{next_p.out}"><span class="dir">Next →</span>'
                     f'<span class="label">{html.escape(next_p.nav)}</span></a>') if next_p else "<span></span>"
        badge_html = f'<span class="badge">{html.escape(page.badge)}</span>' if page.badge else ""

        html_out = PAGE_TMPL.format(
            title=html.escape(page_title(text)),
            favicon=FAVICON,
            mermaid_script=MERMAID_SCRIPT if 'class="mermaid"' in body else "",
            nav=build_nav(page),
            group=html.escape(page.group),
            nav_label=html.escape(page.nav),
            badge_html=badge_html,
            body=body,
            toc=build_toc(md),
            prev_html=prev_html,
            next_html=next_html,
            src=html.escape(f"data_platform_mastery/{page.src}"),
            src_url=f"{GITHUB_COURSES}/data_platform_mastery/{page.src}",
        )
        (OUT_DIR / page.out).write_text(html_out, encoding="utf-8")
        print(f"  built {page.out}")

    print(f"\nDone → {OUT_DIR} ({len(PAGES)} pages + style.css)")


if __name__ == "__main__":
    main()
