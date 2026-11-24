#!/usr/bin/env python3
"""Collect GitHub statistics for this repository into a data directory.

Run daily by .github/workflows/stats.yml; the data lives on the `stats` branch.

* Release downloads (per release and asset, a daily snapshot of the cumulative
  count) need only the workflow's own GITHUB_TOKEN.
* Traffic (views, clones, referrers, popular content) needs TRAFFIC_TOKEN: a
  fine-grained token with "Administration: Read-only" on this repository.
  GitHub keeps traffic for 14 days only, so the daily run is what keeps the
  history. Without the token this part is skipped.

Standard library only. Usage: collect_stats.py <data-dir>
"""

import csv
import datetime as dt
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"


def get(path, token):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "aprs-kiss-app-stats",
        **({"Authorization": f"Bearer {token}"} if token else {}),
    })
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 3:
                raise
        except (http.client.IncompleteRead, urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 3:
                raise
        time.sleep(5 * (attempt + 1))


def read_csv(path, key):
    """Rows of a CSV file as a dict keyed by key(row)."""
    if not os.path.exists(path):
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {key(r): r for r in csv.DictReader(f)}


def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def merge_daily(path, items, count_field):
    """Merge per-day counts (views or clones); the newest fetch wins per day."""
    fields = ["date", count_field, "uniques"]
    rows = read_csv(path, lambda r: r["date"])
    for it in items:
        day = it["timestamp"][:10]
        rows[day] = {"date": day, count_field: it["count"], "uniques": it["uniques"]}
    write_csv(path, fields, [rows[k] for k in sorted(rows)])
    return rows


def append_snapshot(path, fields, today, new_rows, key):
    """Replace today's snapshot rows, keep the older ones."""
    rows = [r for r in read_csv(path, key).values() if r["date"] != today]
    rows += new_rows
    rows.sort(key=lambda r: (r["date"], *(str(r[f]) for f in fields[1:2])))
    write_csv(path, fields, rows)


def releases(repo, token, out, today):
    rows, page = [], 1
    while True:
        batch = get(f"/repos/{repo}/releases?per_page=100&page={page}", token)
        if not batch:
            break
        for rel in batch:
            for a in rel.get("assets", []):
                rows.append({"date": today, "tag": rel["tag_name"], "asset": a["name"],
                             "downloads": a["download_count"]})
        page += 1
    append_snapshot(os.path.join(out, "downloads.csv"), ["date", "tag", "asset", "downloads"],
                    today, rows, lambda r: (r["date"], r["tag"], r["asset"]))
    return rows


def traffic(repo, token, out, today):
    views = merge_daily(os.path.join(out, "views.csv"),
                        get(f"/repos/{repo}/traffic/views", token)["views"], "views")
    clones = merge_daily(os.path.join(out, "clones.csv"),
                         get(f"/repos/{repo}/traffic/clones", token)["clones"], "clones")
    refs = [{"date": today, "referrer": r["referrer"], "count": r["count"], "uniques": r["uniques"]}
            for r in get(f"/repos/{repo}/traffic/popular/referrers", token)]
    append_snapshot(os.path.join(out, "referrers.csv"), ["date", "referrer", "count", "uniques"],
                    today, refs, lambda r: (r["date"], r["referrer"]))
    paths = [{"date": today, "path": p["path"], "title": p["title"], "count": p["count"],
              "uniques": p["uniques"]}
             for p in get(f"/repos/{repo}/traffic/popular/paths", token)]
    append_snapshot(os.path.join(out, "paths.csv"), ["date", "path", "title", "count", "uniques"],
                    today, paths, lambda r: (r["date"], r["path"]))
    return views, clones, refs, paths


def summary(out, today, downloads, tr):
    lines = [f"# Statistics of {os.environ.get('GITHUB_REPOSITORY', 'the repository')}", "",
             f"Updated {today} by `.github/workflows/stats.yml`. Raw data: the CSV files on this branch.", ""]
    total = sum(int(r["downloads"]) for r in downloads)
    lines += [f"## Release downloads ({total} in total)", "", "| Release | Downloads |", "|---|---:|"]
    per_tag = {}
    for r in downloads:
        per_tag[r["tag"]] = per_tag.get(r["tag"], 0) + int(r["downloads"])
    lines += [f"| {t} | {n} |" for t, n in per_tag.items()] + [""]
    if tr:
        views, clones, refs, paths = tr
        days = sorted(views)[-30:]
        lines += ["## Views, last 30 days", "", "| Day | Views | Unique visitors | Clones |",
                  "|---|---:|---:|---:|"]
        lines += [f"| {d} | {views[d]['views']} | {views[d]['uniques']} | "
                  f"{clones.get(d, {}).get('clones', 0)} |" for d in reversed(days)]
        lines += ["", "## Referring sites (last 14 days)", "", "| Site | Views | Unique |", "|---|---:|---:|"]
        lines += [f"| {r['referrer']} | {r['count']} | {r['uniques']} |" for r in refs]
        lines += ["", "## Popular content (last 14 days)", "", "| Page | Views | Unique |", "|---|---:|---:|"]
        lines += [f"| {p['path']} | {p['count']} | {p['uniques']} |" for p in paths]
    else:
        lines += ["Traffic is not collected: add the TRAFFIC_TOKEN secret (see the workflow)."]
    with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    repo = os.environ.get("GITHUB_REPOSITORY", "michalsiman/aprs-kiss-app")
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    os.makedirs(out, exist_ok=True)
    downloads = releases(repo, os.environ.get("GITHUB_TOKEN"), out, today)
    print(f"releases: {len(downloads)} assets")
    tr = None
    token = os.environ.get("TRAFFIC_TOKEN")
    if token:
        try:
            tr = traffic(repo, token, out, today)
            print(f"traffic: {len(tr[0])} days of views")
        except urllib.error.HTTPError as e:
            print(f"::warning::traffic not collected ({e.code}): TRAFFIC_TOKEN needs "
                  "'Administration: Read-only' on this repository")
    else:
        print("::notice::TRAFFIC_TOKEN is not set, traffic skipped")
    if tr is None and os.path.exists(os.path.join(out, "views.csv")):
        # show what was collected before, without today's lists
        tr = (read_csv(os.path.join(out, "views.csv"), lambda r: r["date"]),
              read_csv(os.path.join(out, "clones.csv"), lambda r: r["date"]), [], [])
    summary(out, today, downloads, tr)


if __name__ == "__main__":
    main()
