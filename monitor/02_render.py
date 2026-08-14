#!/usr/bin/env python3
"""
monitor/02_render.py

Builds the static dashboard (monitor/site/index.html) from
monitor/data/state.json and the most recent files in monitor/data/diffs/.
monitor/site/ is what the update-monitor workflow publishes to GitHub
Pages -- it is NOT committed to git (rebuilt fresh each run), so it stays
out of the repo's history the same way enrollment/apps and budget outputs
stay separate from raw source data.
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
    return html.escape(str(s or ""))


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


def render_inventory_rows(state):
    rows = []
    for url, meta in sorted(state["files"].items(), key=lambda kv: kv[1]["category"]):
        rows.append(
            f"<tr data-category='{esc(meta['category'])}'>"
            f"<td>{esc(meta['category'])}</td>"
            f"<td><a href='{esc(url)}' target='_blank' rel='noopener'>{esc(meta['title_guess'])}</a></td>"
            f"<td>{esc(meta['format'])}</td>"
            f"<td>{esc(meta['year_guess'])}</td>"
            f"<td>{esc(meta.get('last_modified'))}</td>"
            f"<td>{fmt_bytes(meta.get('content_length'))}</td>"
            f"</tr>"
        )
    for url, meta in sorted(state.get("google_docs", {}).items()):
        rows.append(
            f"<tr data-category='{esc(meta['category'])}'>"
            f"<td>{esc(meta['category'])}</td>"
            f"<td><a href='{esc(url)}' target='_blank' rel='noopener'>{esc(meta['title_guess'])}</a></td>"
            f"<td>Google Sheet/Doc (external)</td><td></td><td class='muted'>n/a</td><td></td>"
            f"</tr>"
        )
    return "".join(rows)


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
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 1100px;
          margin: 0 auto; padding: 2rem 1rem; line-height: 1.5; }}
  h1 {{ margin-bottom: 0.25rem; }}
  .subtitle {{ color: #888; margin-top: 0; }}
  .summary {{ display: flex; gap: 1rem; flex-wrap: wrap; margin: 1.5rem 0; }}
  .stat {{ border: 1px solid #ddd; border-radius: 8px; padding: 0.75rem 1.25rem; }}
  .stat .n {{ font-size: 1.6rem; font-weight: 700; display: block; }}
  .stat .l {{ font-size: 0.8rem; color: #888; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 0.5rem; }}
  th, td {{ text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #eee2; font-size: 0.9rem; }}
  th {{ position: sticky; top: 0; background: Canvas; }}
  .muted {{ color: #888; font-size: 0.85em; }}
  .tag {{ font-size: 0.7em; font-weight: 700; padding: 0.1em 0.5em; border-radius: 4px; margin-right: 0.4em; }}
  .tag.new {{ background: #d4f4dd; color: #146c2e; }}
  .tag.changed {{ background: #fff3cd; color: #7a5b00; }}
  .tag.removed {{ background: #f8d7da; color: #842029; }}
  .run {{ margin-bottom: 1.25rem; }}
  .run h3 {{ margin-bottom: 0.25rem; font-size: 0.95rem; color: #888; }}
  .ok {{ color: #146c2e; }}
  .error {{ color: #842029; }}
  #filter {{ padding: 0.4rem; margin-bottom: 0.5rem; width: 100%; max-width: 300px; }}
  section {{ margin-top: 2.5rem; }}
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
  <h2>Recent Changes</h2>
  {changes_html}
</section>

<section>
  <h2>Full File Inventory</h2>
  <input id="filter" type="text" placeholder="Filter by category or title...">
  <table id="inv">
    <thead><tr><th>Category</th><th>Title</th><th>Format</th><th>Year</th><th>Last-Modified</th><th>Size</th></tr></thead>
    <tbody>{inventory_rows}</tbody>
  </table>
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
  document.getElementById('filter').addEventListener('input', function (e) {{
    var q = e.target.value.toLowerCase();
    document.querySelectorAll('#inv tbody tr').forEach(function (row) {{
      row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
    }});
  }});
</script>
</body>
</html>
"""


def main():
    state = load_state()
    diffs = load_recent_diffs()
    os.makedirs(SITE_DIR, exist_ok=True)
    html_out = PAGE_TEMPLATE.format(
        last_scan=esc(state.get("last_scan", "never")),
        n_files=len(state.get("files", {})),
        n_gdocs=len(state.get("google_docs", {})),
        n_apis=len(state.get("api_services", {})),
        changes_html=render_changes_section(diffs),
        inventory_rows=render_inventory_rows(state),
        api_rows=render_api_rows(state),
    )
    out_path = os.path.join(SITE_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
