#!/usr/bin/env python3
"""
monitor/02_render.py

Builds the static dashboard (monitor/site/index.html) from
monitor/data/state.json and the most recent files in monitor/data/diffs/.
monitor/site/ is what the update-monitor workflow publishes to GitHub
Pages -- it is NOT committed to git (rebuilt fresh each run), so it stays
out of the repo's history the same way enrollment/apps and budget outputs
stay separate from raw source data.

Layout: a format tab bar (All / Spreadsheets / PDFs / Docs / ... ) with
counts, a category dropdown, and a free-text search box that matches
category, filename, title, format, year, AND column headers -- all
client-side against data-* attributes on each row, so it stays fast even
with a few thousand rows and needs no server.
"""
import glob
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
DIFFS_DIR = os.path.join(DATA_DIR, "diffs")
SITE_DIR = os.path.join(HERE, "site")
RECENT_RUNS_SHOWN = 12

# Order controls left-to-right tab order; label is what's shown.
FORMAT_GROUPS = [
    ("all", "All"),
    ("spreadsheet", "Spreadsheets"),
    ("pdf", "PDF"),
    ("document", "Documents"),
    ("presentation", "Presentations"),
    ("google", "Google Docs/Slides"),
    ("json", "JSON"),
    ("archive", "Archives"),
    ("other", "Other"),
]


def load_state():
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_recent_diffs(n=RECENT_RUNS_SHOWN):
    paths = sorted(glob.glob(os.path.join(DIFFS_DIR, "*.json")), reverse=True)[:n]
    diffs = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            diffs.append(json.load(f))
    return diffs


def esc(s):
    return html.escape(str(s or ""), quote=True)


def fmt_bytes(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}TB"


def format_group(fmt):
    """Map a human-readable format string (from 01_scan.py's guess_format)
    to one of the tab keys in FORMAT_GROUPS."""
    f = (fmt or "").lower()
    if any(k in f for k in ("spreadsheet", "csv", "tsv", "sheet")):
        return "spreadsheet"
    if "pdf" in f:
        return "pdf"
    if "document" in f and "google" not in f:
        return "document"
    if "presentation" in f and "google" not in f:
        return "presentation"
    if "google" in f:
        return "google"
    if "json" in f:
        return "json"
    if "archive" in f:
        return "archive"
    return "other"


def render_columns_cell(meta):
    cols = meta.get("columns") or []
    if cols:
        shown = cols[:6]
        text = ", ".join(esc(c) for c in shown)
        if len(cols) > 6:
            text += f" <span class='muted'>+{len(cols) - 6} more</span>"
        full = esc(", ".join(cols))
        sheets = meta.get("sheet_names") or []
        sheet_note = ""
        if len(sheets) > 1:
            sheet_note = f" <span class='muted' title='{esc(', '.join(sheets))}'>({len(sheets)} sheets)</span>"
        return f"<span class='cols' title='{full}'>{text}</span>{sheet_note}"
    err = meta.get("columns_error")
    if err:
        return f"<span class='muted' title='{esc(err)}'>&mdash;</span>"
    return "<span class='muted'>&mdash;</span>"


def columns_search_text(meta):
    return " ".join(meta.get("columns") or [])


def render_changes_section(diffs):
    any_changes = any(
        d["new_files"] or d["changed_files"] or d["removed_files"] or d["new_google_docs"]
        for d in diffs
    )
    if not diffs or not any_changes:
        return "<p class='muted'>No changes recorded in the last runs.</p>"

    blocks = []
    for d in diffs:
        parts = []
        if d["new_files"]:
            items = "".join(
                f"<li><span class='tag new'>NEW</span> "
                f"<a href='{esc(f['url'])}' target='_blank' rel='noopener'>{esc(f['title_guess'])}</a> "
                f"<span class='muted'>({esc(f['category'])})</span></li>"
                for f in d["new_files"]
            )
            parts.append(f"<ul>{items}</ul>")
        if d["changed_files"]:
            items = "".join(
                f"<li><span class='tag changed'>CHANGED</span> "
                f"<a href='{esc(f['url'])}' target='_blank' rel='noopener'>{esc(f['title_guess'])}</a> "
                f"<span class='muted'>{esc(f.get('old_last_modified'))} &rarr; {esc(f.get('new_last_modified'))}</span></li>"
                for f in d["changed_files"]
            )
            parts.append(f"<ul>{items}</ul>")
        if d["removed_files"]:
            items = "".join(f"<li><span class='tag removed'>REMOVED</span> {esc(u)}</li>" for u in d["removed_files"])
            parts.append(f"<ul>{items}</ul>")
        if d["new_google_docs"]:
            items = "".join(
                f"<li><span class='tag new'>NEW (Google Doc)</span> "
                f"<a href='{esc(u)}' target='_blank' rel='noopener'>{esc(u)}</a></li>"
                for u in d["new_google_docs"]
            )
            parts.append(f"<ul>{items}</ul>")
        if not parts:
            continue
        blocks.append(f"<div class='run'><h3>{esc(d['scan_time'])}</h3>{''.join(parts)}</div>")
    return "".join(blocks) if blocks else "<p class='muted'>No changes recorded in the last runs.</p>"


def build_rows(state):
    """Returns (rows_html, categories_sorted, group_counts)."""
    rows = []
    categories = set()
    group_counts = {key: 0 for key, _ in FORMAT_GROUPS}

    combined = []
    for url, meta in state.get("files", {}).items():
        combined.append((url, meta, False))
    for url, meta in state.get("google_docs", {}).items():
        combined.append((url, meta, True))

    combined.sort(key=lambda t: (t[1].get("category") or "", t[1].get("title_guess") or ""))

    for url, meta, is_gdoc in combined:
        category = meta.get("category") or "Uncategorized"
        fmt = meta.get("format") or ("Google Doc/Sheet (external)" if is_gdoc else "")
        group = format_group(fmt)
        categories.add(category)
        group_counts["all"] += 1
        group_counts[group] = group_counts.get(group, 0) + 1

        filename = meta.get("filename") or os.path.basename(url.split("?")[0])
        title = meta.get("title_guess") or filename
        year = meta.get("year_guess", "") if not is_gdoc else ""
        last_mod = meta.get("last_modified") if not is_gdoc else "n/a (Google Doc)"
        size = fmt_bytes(meta.get("content_length")) if not is_gdoc else ""

        search_text = " ".join([
            category, filename, title, fmt, str(year), columns_search_text(meta),
        ]).lower()

        rows.append(
            "<tr class='row' "
            f"data-group='{esc(group)}' data-category='{esc(category)}' "
            f"data-search='{esc(search_text)}'>"
            f"<td>{esc(category)}</td>"
            f"<td><a href='{esc(url)}' target='_blank' rel='noopener'>{esc(title)}</a>"
            f"<div class='muted filename'>{esc(filename)}</div></td>"
            f"<td>{esc(fmt)}</td>"
            f"<td>{esc(year)}</td>"
            f"<td>{esc(last_mod)}</td>"
            f"<td>{esc(size)}</td>"
            f"<td>{render_columns_cell(meta)}</td>"
            "</tr>"
        )

    return "".join(rows), sorted(categories), group_counts


def render_tabs(group_counts):
    tabs = []
    for i, (key, label) in enumerate(FORMAT_GROUPS):
        count = group_counts.get(key, 0)
        active = " active" if i == 0 else ""
        tabs.append(
            f"<button class='tab{active}' data-group='{esc(key)}' type='button'>"
            f"{esc(label)} <span class='tabcount'>{count}</span></button>"
        )
    return "".join(tabs)


def render_category_options(categories):
    opts = ["<option value=''>All categories</option>"]
    for c in categories:
        opts.append(f"<option value='{esc(c)}'>{esc(c)}</option>")
    return "".join(opts)


def render_api_rows(state):
    rows = []
    for name, meta in sorted(state.get("api_services", {}).items()):
        status = "ok" if meta.get("status_code") == 200 else "error"
        rows.append(
            f"<tr><td>{esc(name)}</td>"
            f"<td><a href='{esc(meta.get('url'))}' target='_blank' rel='noopener'>{esc(meta.get('url'))}</a></td>"
            f"<td class='{status}'>{esc(meta.get('status_code', meta.get('error', '?')))}</td></tr>"
        )
    return "".join(rows)


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chicago Education Data Monitor</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 1200px;
          margin: 0 auto; padding: 1.5rem 1rem 3rem; line-height: 1.5; }}
  h1 {{ margin-bottom: 0.15rem; font-size: 1.5rem; }}
  .subtitle {{ color: #888; margin-top: 0; font-size: 0.9rem; }}
  .summary {{ display: flex; gap: 0.75rem; flex-wrap: wrap; margin: 1rem 0 1.5rem; }}
  .stat {{ border: 1px solid #ddd5; border-radius: 8px; padding: 0.6rem 1rem; }}
  .stat .n {{ font-size: 1.4rem; font-weight: 700; display: block; }}
  .stat .l {{ font-size: 0.75rem; color: #888; }}

  section {{ margin-top: 2rem; }}
  details.changes summary {{ cursor: pointer; font-weight: 600; font-size: 1.1rem; padding: 0.25rem 0; }}
  details.changes[open] summary {{ margin-bottom: 0.5rem; }}

  .toolbar {{ position: sticky; top: 0; background: Canvas; padding: 0.75rem 0 0.5rem;
              z-index: 5; border-bottom: 1px solid #ddd5; }}
  .tabs {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.6rem; }}
  .tab {{ border: 1px solid #ccc8; background: transparent; color: inherit; border-radius: 999px;
          padding: 0.3rem 0.8rem; font-size: 0.82rem; cursor: pointer; white-space: nowrap; }}
  .tab:hover {{ border-color: #888; }}
  .tab.active {{ background: #2563eb; border-color: #2563eb; color: #fff; }}
  .tabcount {{ opacity: 0.75; font-size: 0.85em; }}
  .controls {{ display: flex; gap: 0.6rem; flex-wrap: wrap; align-items: center; }}
  #filter {{ padding: 0.45rem 0.6rem; flex: 1 1 260px; min-width: 200px;
             border: 1px solid #ccc8; border-radius: 6px; background: transparent; color: inherit; }}
  #catFilter {{ padding: 0.45rem 0.6rem; border: 1px solid #ccc8; border-radius: 6px;
                background: Canvas; color: inherit; max-width: 260px; }}
  #count {{ font-size: 0.82rem; color: #888; white-space: nowrap; }}

  table {{ border-collapse: collapse; width: 100%; margin-top: 0.75rem; }}
  th, td {{ text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid #eee2;
            font-size: 0.87rem; vertical-align: top; }}
  th {{ background: Canvas; cursor: default; }}
  tbody tr:hover {{ background: rgba(128, 128, 128, 0.08); }}
  .filename {{ font-size: 0.78em; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .muted {{ color: #888; font-size: 0.85em; }}
  .cols {{ font-size: 0.85em; }}
  .tag {{ font-size: 0.7em; font-weight: 700; padding: 0.1em 0.5em; border-radius: 4px; margin-right: 0.4em; }}
  .tag.new {{ background: #d4f4dd; color: #146c2e; }}
  .tag.changed {{ background: #fff3cd; color: #7a5b00; }}
  .tag.removed {{ background: #f8d7da; color: #842029; }}
  .run {{ margin-bottom: 1.25rem; }}
  .run h3 {{ margin-bottom: 0.25rem; font-size: 0.95rem; color: #888; }}
  .ok {{ color: #146c2e; }}
  .error {{ color: #842029; }}
  .empty-state {{ padding: 2rem 0; text-align: center; color: #888; display: none; }}
</style>
</head>
<body>
<h1>Chicago Education Data Monitor</h1>
<p class="subtitle">Auto-generated by <code>monitor/</code> in this repo.
  Last scan: <strong>{last_scan}</strong></p>

<div class="summary">
  <div class="stat"><span class="n">{n_files}</span><span class="l">files tracked</span></div>
  <div class="stat"><span class="n">{n_gdocs}</span><span class="l">Google Sheets/Docs tracked</span></div>
  <div class="stat"><span class="n">{n_apis}</span><span class="l">api.cps.edu services</span></div>
</div>

<section>
  <details class="changes">
    <summary>Recent Changes</summary>
    {changes_html}
  </details>
</section>

<section>
  <h2>Full File Inventory</h2>
  <div class="toolbar">
    <div class="tabs">{tabs_html}</div>
    <div class="controls">
      <input id="filter" type="text" placeholder="Search title, filename, category, or column name...">
      <select id="catFilter">{category_options}</select>
      <span id="count"></span>
    </div>
  </div>
  <table id="inv">
    <thead>
      <tr>
        <th>Category</th><th>Title / Filename</th><th>Format</th><th>Year</th>
        <th>Last-Modified</th><th>Size</th><th>Columns</th>
      </tr>
    </thead>
    <tbody>{inventory_rows}</tbody>
  </table>
  <p class="empty-state" id="emptyState">No files match your filters.</p>
</section>

<section>
  <h2>api.cps.edu Services</h2>
  <table>
    <thead><tr><th>Service</th><th>URL</th><th>Status</th></tr></thead>
    <tbody>{api_rows}</tbody>
  </table>
  <p class="muted">Status reflects reachability of the service's docs page, not
  freshness of the data behind it -- see the repo README for how to add
  endpoint-specific checks for e.g. School Profile or District API.</p>
</section>

<script>
  var rows = Array.prototype.slice.call(document.querySelectorAll('#inv tbody tr'));
  var activeGroup = 'all';
  var filterInput = document.getElementById('filter');
  var catSelect = document.getElementById('catFilter');
  var countEl = document.getElementById('count');
  var emptyEl = document.getElementById('emptyState');

  function applyFilters() {{
    var q = filterInput.value.trim().toLowerCase();
    var cat = catSelect.value;
    var shown = 0;
    for (var i = 0; i < rows.length; i++) {{
      var row = rows[i];
      var matchesGroup = activeGroup === 'all' || row.dataset.group === activeGroup;
      var matchesCat = !cat || row.dataset.category === cat;
      var matchesQ = !q || row.dataset.search.indexOf(q) !== -1;
      var visible = matchesGroup && matchesCat && matchesQ;
      row.style.display = visible ? '' : 'none';
      if (visible) shown++;
    }}
    countEl.textContent = shown + ' of ' + rows.length + ' shown';
    emptyEl.style.display = shown === 0 ? 'block' : 'none';
  }}

  filterInput.addEventListener('input', applyFilters);
  catSelect.addEventListener('change', applyFilters);
  document.querySelectorAll('.tab').forEach(function (btn) {{
    btn.addEventListener('click', function () {{
      document.querySelectorAll('.tab').forEach(function (b) {{ b.classList.remove('active'); }});
      btn.classList.add('active');
      activeGroup = btn.dataset.group;
      applyFilters();
    }});
  }});

  applyFilters();
</script>
</body>
</html>
"""


def main():
    state = load_state()
    diffs = load_recent_diffs()
    os.makedirs(SITE_DIR, exist_ok=True)

    inventory_rows, categories, group_counts = build_rows(state)

    html_out = PAGE_TEMPLATE.format(
        last_scan=esc(state.get("last_scan", "never")),
        n_files=len(state.get("files", {})),
        n_gdocs=len(state.get("google_docs", {})),
        n_apis=len(state.get("api_services", {})),
        changes_html=render_changes_section(diffs),
        tabs_html=render_tabs(group_counts),
        category_options=render_category_options(categories),
        inventory_rows=inventory_rows,
        api_rows=render_api_rows(state),
    )
    out_path = os.path.join(SITE_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
