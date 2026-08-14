#!/usr/bin/env python3
"""
monitor/03_render_dashboard.py

Writes monitor/site/index.html: a single static file containing a React
dashboard (React 18 + Babel Standalone + Tailwind, all loaded from CDN --
no npm/Node/build step in CI) that fetches monitor/site/api/*.json at
page load and renders them.

This file's content is the SAME every run -- it holds no scan data itself,
it just knows how to ask api/latest.json, api/files.json, api/runs.json,
and api/api_services.json for the current picture. That's why this script
takes no arguments and does no templating: run 02_export_api.py first so
api/ exists, then run this.

monitor/site/ is not committed to git -- it's rebuilt fresh by the
update-monitor workflow every run and published straight to GitHub Pages,
the same way enrollment/apps and budget outputs stay out of the repo's
history.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.join(HERE, "site")

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chicago Education Data Monitor</title>
<link rel="icon" href="data:,">
<script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
<script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js" crossorigin></script>
<script src="https://unpkg.com/@babel/standalone@7/babel.min.js" crossorigin></script>
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    darkMode: 'class',
    theme: {
      extend: {
        fontFamily: { sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'] },
      },
    },
  };
</script>
<style>
  ::-webkit-scrollbar { height: 10px; width: 10px; }
  ::-webkit-scrollbar-thumb { background: rgba(148,163,184,.4); border-radius: 999px; }
  .no-scrollbar::-webkit-scrollbar { display: none; }
  @keyframes fadein { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
  .fadein { animation: fadein .25s ease-out; }
</style>
</head>
<body class="bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans">
<div id="root"></div>

<script type="text/babel" data-presets="react">
const { useState, useEffect, useMemo, useCallback } = React;

/* ---------------------------------------------------------------------
   Config
--------------------------------------------------------------------- */
const API_BASE = "api/";
const FORMAT_GROUPS = [
  { key: "all", label: "All" },
  { key: "spreadsheet", label: "Spreadsheets" },
  { key: "pdf", label: "PDF" },
  { key: "document", label: "Documents" },
  { key: "presentation", label: "Presentations" },
  { key: "google", label: "Google Docs/Slides" },
  { key: "json", label: "JSON" },
  { key: "archive", label: "Archives" },
  { key: "other", label: "Other" },
];

/* ---------------------------------------------------------------------
   Small utilities
--------------------------------------------------------------------- */
function fmtBytes(n) {
  if (n === null || n === undefined || isNaN(n)) return "";
  let v = Number(n);
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(v < 10 && i > 0 ? 1 : 0)}${units[i]}`;
}

function relTime(iso) {
  if (!iso) return "unknown";
  const then = new Date(iso).getTime();
  if (isNaN(then)) return iso;
  const diffMs = Date.now() - then;
  const abs = Math.abs(diffMs);
  const mins = Math.round(abs / 60000);
  const hrs = Math.round(abs / 3600000);
  const days = Math.round(abs / 86400000);
  let out;
  if (mins < 1) out = "just now";
  else if (mins < 60) out = `${mins}m`;
  else if (hrs < 48) out = `${hrs}h`;
  else out = `${days}d`;
  return diffMs >= 0 ? `${out} ago` : `in ${out}`;
}

function absUrl(path) {
  try { return new URL(path, window.location.href).toString(); }
  catch (e) { return path; }
}

async function fetchJson(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}`);
  return res.json();
}

function download(path) {
  const a = document.createElement("a");
  a.href = path;
  a.download = "";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

async function copyText(text, onDone) {
  try { await navigator.clipboard.writeText(text); onDone && onDone(true); }
  catch (e) { onDone && onDone(false); }
}

/* ---------------------------------------------------------------------
   Icons (tiny inline SVGs -- no icon package needed)
--------------------------------------------------------------------- */
const Icon = ({ path, className = "w-4 h-4" }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
       strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d={path} />
  </svg>
);
const IconDownload = (p) => <Icon {...p} path="M12 3v12m0 0l-4-4m4 4l4-4M4 21h16" />;
const IconCode = (p) => <Icon {...p} path="M8 4L2 12l6 8M16 4l6 8-6 8" />;
const IconCopy = (p) => <Icon {...p} path="M9 9h10v10H9zM5 15V5h10" />;
const IconExternal = (p) => <Icon {...p} path="M14 3h7v7M21 3l-9 9M19 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h6" />;
const IconSun = (p) => <Icon {...p} path="M12 3v2m0 14v2m9-9h-2M5 12H3m15.4 6.4l-1.4-1.4M7 7L5.6 5.6m12.8 0L17 7M7 17l-1.4 1.4M12 8a4 4 0 100 8 4 4 0 000-8z" />;
const IconMoon = (p) => <Icon {...p} path="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z" />;
const IconSearch = (p) => <Icon {...p} path="M11 19a8 8 0 100-16 8 8 0 000 16zM21 21l-4.35-4.35" />;
const IconX = (p) => <Icon {...p} path="M18 6L6 18M6 6l12 12" />;
const IconChevron = (p) => <Icon {...p} path="M6 9l6 6 6-6" />;

/* ---------------------------------------------------------------------
   Format helpers
--------------------------------------------------------------------- */
function groupBadgeClasses(group) {
  const map = {
    spreadsheet: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
    pdf: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300",
    document: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
    presentation: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
    google: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300",
    json: "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
    archive: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    other: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  };
  return map[group] || map.other;
}

/* ---------------------------------------------------------------------
   Sparkline (hand-rolled -- no chart library needed for one line)
--------------------------------------------------------------------- */
function Sparkline({ values, width = 160, height = 40, className = "" }) {
  if (!values || values.length < 2) {
    return <div className={`text-xs text-slate-400 ${className}`}>Not enough history yet</div>;
  }
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * (width - 4) + 2;
    const y = height - 2 - ((v - min) / span) * (height - 4);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const lastX = width - 2, lastY = height - 2 - ((values[values.length - 1] - min) / span) * (height - 4);
  return (
    <svg width={width} height={height} className={className} viewBox={`0 0 ${width} ${height}`}>
      <polyline points={pts} fill="none" stroke="currentColor" strokeWidth="1.75"
                strokeLinecap="round" strokeLinejoin="round" className="text-indigo-500" />
      <circle cx={lastX} cy={lastY} r="2.5" className="fill-indigo-500" />
    </svg>
  );
}

/* ---------------------------------------------------------------------
   API Docs modal
--------------------------------------------------------------------- */
function ApiDocsModal({ index, onClose }) {
  const [copiedPath, setCopiedPath] = useState(null);

  if (!index) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 p-4 overflow-y-auto"
         onClick={onClose}>
      <div className="mt-10 w-full max-w-2xl rounded-2xl bg-white dark:bg-slate-900 shadow-2xl fadein"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between p-5 border-b border-slate-200 dark:border-slate-800">
          <div>
            <h2 className="text-lg font-semibold flex items-center gap-2"><IconCode className="w-5 h-5" /> API</h2>
            <p className="text-sm text-slate-500 mt-1 max-w-md">{index.description}</p>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800">
            <IconX />
          </button>
        </div>
        <div className="p-5 space-y-3 max-h-[60vh] overflow-y-auto">
          {index.endpoints.map((ep) => {
            const url = absUrl(ep.path);
            const curl = `curl ${url}`;
            return (
              <div key={ep.name} className="rounded-xl border border-slate-200 dark:border-slate-800 p-3">
                <div className="flex items-center justify-between gap-2">
                  <code className="text-sm font-mono text-indigo-600 dark:text-indigo-400">{ep.path}</code>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => copyText(curl, (ok) => setCopiedPath(ok ? ep.name : null))}
                      className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800">
                      <IconCopy className="w-3.5 h-3.5" /> {copiedPath === ep.name ? "Copied!" : "Copy curl"}
                    </button>
                    <a href={ep.path} target="_blank" rel="noopener"
                       className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800">
                      <IconExternal className="w-3.5 h-3.5" /> Open
                    </a>
                  </div>
                </div>
                <p className="text-xs text-slate-500 mt-1.5">{ep.description}</p>
              </div>
            );
          })}
        </div>
        <div className="p-4 border-t border-slate-200 dark:border-slate-800 text-xs text-slate-400">
          Generated at {index.generated_at}. No auth, no rate limit -- these are static files on GitHub Pages.
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------
   Hero: scrape_id / run_time / run_number + download buttons
--------------------------------------------------------------------- */
function Hero({ latest, runs, apiIndex, onOpenDocs }) {
  const sparkValues = useMemo(() => (runs || []).map((r) => r.total_files).filter((v) => typeof v === "number"), [runs]);

  return (
    <div className="rounded-3xl overflow-hidden bg-gradient-to-br from-indigo-600 via-indigo-600 to-violet-700 text-white shadow-xl">
      <div className="p-6 sm:p-8">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Chicago Education Data Monitor</h1>
            <p className="text-indigo-100 mt-1 text-sm sm:text-base">
              Live inventory of every data file CPS publishes, tracked for changes.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => download(API_BASE + "files.json")}
                    className="flex items-center gap-1.5 text-sm font-medium px-3.5 py-2 rounded-xl bg-white/15 hover:bg-white/25 backdrop-blur transition">
              <IconDownload className="w-4 h-4" /> JSON
            </button>
            <button onClick={() => download(API_BASE + "files.csv")}
                    className="flex items-center gap-1.5 text-sm font-medium px-3.5 py-2 rounded-xl bg-white/15 hover:bg-white/25 backdrop-blur transition">
              <IconDownload className="w-4 h-4" /> CSV
            </button>
            <button onClick={onOpenDocs}
                    className="flex items-center gap-1.5 text-sm font-medium px-3.5 py-2 rounded-xl bg-white text-indigo-700 hover:bg-indigo-50 transition">
              <IconCode className="w-4 h-4" /> API docs
            </button>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-2xl bg-white/10 backdrop-blur p-4">
            <div className="text-xs uppercase tracking-wide text-indigo-100">Scrape ID</div>
            <div className="text-sm font-mono mt-1 truncate" title={latest?.scrape_id}>{latest?.scrape_id || "—"}</div>
          </div>
          <div className="rounded-2xl bg-white/10 backdrop-blur p-4">
            <div className="text-xs uppercase tracking-wide text-indigo-100">Run #</div>
            <div className="text-lg font-semibold mt-1">{latest?.run_number ?? "—"}</div>
          </div>
          <div className="rounded-2xl bg-white/10 backdrop-blur p-4">
            <div className="text-xs uppercase tracking-wide text-indigo-100">Last run</div>
            <div className="text-sm font-medium mt-1" title={latest?.run_time}>{relTime(latest?.run_time)}</div>
          </div>
          <div className="rounded-2xl bg-white/10 backdrop-blur p-4 flex items-center justify-between">
            <div>
              <div className="text-xs uppercase tracking-wide text-indigo-100">File count trend</div>
              <div className="text-lg font-semibold mt-1">{latest?.counts?.files ?? "—"}</div>
            </div>
            <Sparkline values={sparkValues} width={80} height={32} className="text-white" />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------
   Stat cards
--------------------------------------------------------------------- */
function StatCard({ label, value, sub, tone = "slate" }) {
  const tones = {
    slate: "text-slate-500",
    emerald: "text-emerald-600 dark:text-emerald-400",
    amber: "text-amber-600 dark:text-amber-400",
    rose: "text-rose-600 dark:text-rose-400",
  };
  return (
    <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 shadow-sm">
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-slate-500 mt-0.5">{label}</div>
      {sub ? <div className={`text-xs mt-1.5 font-medium ${tones[tone]}`}>{sub}</div> : null}
    </div>
  );
}

function StatRow({ latest, apiServices }) {
  const c = latest?.counts || {};
  const ch = latest?.last_run_changes || {};
  const okApis = Object.values(apiServices || {}).filter((s) => s.status_code === 200).length;
  const totalApis = Object.keys(apiServices || {}).length;
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <StatCard label="Files tracked" value={c.files ?? "—"}
                sub={ch.new_files || ch.changed_files || ch.removed_files
                       ? `+${ch.new_files || 0} new · ${ch.changed_files || 0} changed · ${ch.removed_files || 0} removed`
                       : "No changes last run"}
                tone={ch.new_files || ch.changed_files || ch.removed_files ? "amber" : "slate"} />
      <StatCard label="Google Sheets/Docs" value={c.google_docs ?? "—"}
                sub={ch.new_google_docs ? `+${ch.new_google_docs} new` : null} tone="emerald" />
      <StatCard label="api.cps.edu services" value={`${okApis}/${totalApis}`}
                sub={totalApis - okApis > 0 ? `${totalApis - okApis} unreachable` : "All reachable"}
                tone={totalApis - okApis > 0 ? "rose" : "emerald"} />
      <StatCard label="Changed services (last run)" value={ch.changed_api_services ?? 0} />
    </div>
  );
}

/* ---------------------------------------------------------------------
   Changes panel (fetches the specific diff for the latest scrape_id)
--------------------------------------------------------------------- */
function ChangesPanel({ scrapeId }) {
  const [open, setOpen] = useState(false);
  const [diff, setDiff] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open || !scrapeId || diff) return;
    fetchJson(`${API_BASE}changes/${scrapeId}.json`).then(setDiff).catch((e) => setError(e.message));
  }, [open, scrapeId]);

  const total = diff ? (diff.new_files.length + diff.changed_files.length + diff.removed_files.length + diff.new_google_docs.length) : null;

  return (
    <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
      <button onClick={() => setOpen((v) => !v)}
              className="w-full flex items-center justify-between p-4 text-left">
        <span className="font-semibold text-sm">Recent changes {total !== null ? `(${total})` : ""}</span>
        <IconChevron className={`w-4 h-4 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="border-t border-slate-200 dark:border-slate-800 p-4 fadein text-sm space-y-3 max-h-80 overflow-y-auto">
          {error && <div className="text-rose-500">{error}</div>}
          {!error && !diff && <div className="text-slate-400">Loading…</div>}
          {diff && total === 0 && <div className="text-slate-400">No changes in the latest run.</div>}
          {diff && diff.new_files.map((f) => (
            <div key={f.url} className="flex items-start gap-2">
              <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">NEW</span>
              <a href={f.url} target="_blank" rel="noopener" className="hover:underline">{f.title_guess || f.url}</a>
            </div>
          ))}
          {diff && diff.changed_files.map((f) => (
            <div key={f.url} className="flex items-start gap-2">
              <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">CHANGED</span>
              <a href={f.url} target="_blank" rel="noopener" className="hover:underline">{f.title_guess || f.url}</a>
            </div>
          ))}
          {diff && diff.removed_files.map((u) => (
            <div key={u} className="flex items-start gap-2">
              <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300">REMOVED</span>
              <span className="text-slate-500 break-all">{u}</span>
            </div>
          ))}
          {diff && diff.new_google_docs.map((u) => (
            <div key={u} className="flex items-start gap-2">
              <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">NEW (Google)</span>
              <a href={u} target="_blank" rel="noopener" className="hover:underline break-all">{u}</a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------------
   Columns cell
--------------------------------------------------------------------- */
function ColumnsCell({ record }) {
  const cols = record.columns || [];
  if (!cols.length) {
    return <span className="text-slate-400 text-xs" title={record.columns_error || ""}>—</span>;
  }
  const shown = cols.slice(0, 5);
  return (
    <div className="flex flex-wrap gap-1 max-w-xs" title={cols.join(", ")}>
      {shown.map((c, i) => (
        <span key={i} className="text-[11px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">{c}</span>
      ))}
      {cols.length > shown.length && (
        <span className="text-[11px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-400">+{cols.length - shown.length}</span>
      )}
      {record.sheet_names && record.sheet_names.length > 1 && (
        <span className="text-[11px] text-slate-400">({record.sheet_names.length} sheets)</span>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------------
   Inventory table + toolbar
--------------------------------------------------------------------- */
function Inventory({ records }) {
  const [search, setSearch] = useState("");
  const [group, setGroup] = useState("all");
  const [category, setCategory] = useState("");

  const groupCounts = useMemo(() => {
    const counts = { all: records.length };
    for (const r of records) counts[r.format_group] = (counts[r.format_group] || 0) + 1;
    return counts;
  }, [records]);

  const categories = useMemo(
    () => Array.from(new Set(records.map((r) => r.category || "Uncategorized"))).sort(),
    [records]
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return records.filter((r) => {
      if (group !== "all" && r.format_group !== group) return false;
      if (category && (r.category || "Uncategorized") !== category) return false;
      if (!q) return true;
      const haystack = [
        r.category, r.filename, r.title, r.format, r.year,
        ...(r.columns || []),
      ].filter(Boolean).join(" ").toLowerCase();
      return haystack.includes(q);
    });
  }, [records, search, group, category]);

  return (
    <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 space-y-3 sticky top-0 bg-white/90 dark:bg-slate-900/90 backdrop-blur z-10">
        <div className="flex flex-wrap gap-2">
          {FORMAT_GROUPS.map((g) => (
            <button key={g.key} onClick={() => setGroup(g.key)}
                    className={`text-xs font-medium px-3 py-1.5 rounded-full border transition
                      ${group === g.key
                        ? "bg-indigo-600 border-indigo-600 text-white"
                        : "border-slate-200 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-500"}`}>
              {g.label} <span className="opacity-70">{groupCounts[g.key] || 0}</span>
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[220px]">
            <IconSearch className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input value={search} onChange={(e) => setSearch(e.target.value)}
                   placeholder="Search title, filename, category, or column name…"
                   className="w-full pl-9 pr-8 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-transparent focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            {search && (
              <button onClick={() => setSearch("")} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                <IconX className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          <select value={category} onChange={(e) => setCategory(e.target.value)}
                  className="text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-transparent px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 max-w-[220px]">
            <option value="">All categories</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <span className="text-xs text-slate-400 whitespace-nowrap">{filtered.length} of {records.length} shown</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-slate-400 border-b border-slate-200 dark:border-slate-800">
              <th className="px-4 py-2 font-medium">Category</th>
              <th className="px-4 py-2 font-medium">Title / Filename</th>
              <th className="px-4 py-2 font-medium">Format</th>
              <th className="px-4 py-2 font-medium">Year</th>
              <th className="px-4 py-2 font-medium">Last modified</th>
              <th className="px-4 py-2 font-medium">Size</th>
              <th className="px-4 py-2 font-medium">Columns</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 500).map((r, i) => (
              <tr key={r.url + i} className="border-b border-slate-100 dark:border-slate-800/60 hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <td className="px-4 py-2.5 text-slate-500 whitespace-nowrap">{r.category}</td>
                <td className="px-4 py-2.5 max-w-xs">
                  <a href={r.url} target="_blank" rel="noopener" className="font-medium text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1">
                    {r.title} <IconExternal className="w-3 h-3 shrink-0 opacity-60" />
                  </a>
                  {r.filename && <div className="text-[11px] font-mono text-slate-400 truncate">{r.filename}</div>}
                </td>
                <td className="px-4 py-2.5 whitespace-nowrap">
                  <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${groupBadgeClasses(r.format_group)}`}>{r.format}</span>
                </td>
                <td className="px-4 py-2.5 text-slate-500">{r.year || ""}</td>
                <td className="px-4 py-2.5 text-slate-500 whitespace-nowrap">{r.last_modified || (r.source_type === "google_doc" ? "n/a" : "")}</td>
                <td className="px-4 py-2.5 text-slate-500 whitespace-nowrap">{fmtBytes(r.size_bytes)}</td>
                <td className="px-4 py-2.5"><ColumnsCell record={r} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="text-center py-12 text-slate-400 text-sm">No files match your filters.</div>
        )}
        {filtered.length > 500 && (
          <div className="text-center py-3 text-xs text-slate-400">Showing first 500 of {filtered.length} matches — narrow your search to see more.</div>
        )}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------
   API services table
--------------------------------------------------------------------- */
function ApiServices({ services }) {
  const entries = Object.entries(services || {}).sort(([a], [b]) => a.localeCompare(b));
  return (
    <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm p-4">
      <h2 className="font-semibold text-sm mb-3">api.cps.edu services</h2>
      <div className="grid sm:grid-cols-2 gap-2">
        {entries.map(([name, meta]) => {
          const ok = meta.status_code === 200;
          return (
            <a key={name} href={meta.url} target="_blank" rel="noopener"
               className="flex items-center justify-between gap-2 text-sm rounded-xl border border-slate-200 dark:border-slate-800 px-3 py-2 hover:border-slate-300 dark:hover:border-slate-700">
              <span className="truncate">{name}</span>
              <span className={`text-xs font-mono px-2 py-0.5 rounded-full shrink-0 ${ok ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300" : "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300"}`}>
                {meta.status_code ?? meta.error ?? "?"}
              </span>
            </a>
          );
        })}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------
   App
--------------------------------------------------------------------- */
function App() {
  const [data, setData] = useState({ latest: null, records: null, runs: null, apiServices: null, apiIndex: null });
  const [error, setError] = useState(null);
  const [docsOpen, setDocsOpen] = useState(false);
  const [dark, setDark] = useState(() => window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  useEffect(() => {
    Promise.all([
      fetchJson(API_BASE + "latest.json"),
      fetchJson(API_BASE + "files.json"),
      fetchJson(API_BASE + "runs.json"),
      fetchJson(API_BASE + "api_services.json"),
      fetchJson(API_BASE + "index.json"),
    ]).then(([latest, records, runs, apiServices, apiIndex]) => {
      setData({ latest, records, runs, apiServices, apiIndex });
    }).catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="max-w-lg mx-auto mt-24 text-center px-4">
        <h1 className="text-lg font-semibold">Couldn't load the API data</h1>
        <p className="text-sm text-slate-500 mt-2">{error}</p>
        <p className="text-xs text-slate-400 mt-4">
          This page fetches JSON from <code>api/</code> next to it, so it needs to be served over http(s)
          (e.g. GitHub Pages) -- opening the HTML file directly won't work.
        </p>
      </div>
    );
  }

  if (!data.records) {
    return (
      <div className="max-w-lg mx-auto mt-24 text-center px-4 text-slate-400 text-sm">Loading latest scrape…</div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 sm:py-8 space-y-6">
      <div className="flex justify-end">
        <button onClick={() => setDark((v) => !v)}
                className="p-2 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800">
          {dark ? <IconSun className="w-4 h-4" /> : <IconMoon className="w-4 h-4" />}
        </button>
      </div>

      <Hero latest={data.latest} runs={data.runs} apiIndex={data.apiIndex} onOpenDocs={() => setDocsOpen(true)} />
      <StatRow latest={data.latest} apiServices={data.apiServices} />
      <ChangesPanel scrapeId={data.latest?.scrape_id} />
      <Inventory records={data.records} />
      <ApiServices services={data.apiServices} />

      <footer className="text-center text-xs text-slate-400 pt-6 pb-2">
        Auto-generated by <code>monitor/</code> in this repo · data served from <code>api/</code> as plain static JSON
      </footer>

      {docsOpen && <ApiDocsModal index={data.apiIndex} onClose={() => setDocsOpen(false)} />}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
</script>
</body>
</html>
"""


def main():
    os.makedirs(SITE_DIR, exist_ok=True)
    out_path = os.path.join(SITE_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(DASHBOARD_HTML)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
