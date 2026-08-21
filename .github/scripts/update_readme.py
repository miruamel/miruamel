#!/usr/bin/env python3
"""Generate a self-updating GitHub profile README.

Pulls live data from the GitHub API (via `gh`) and injects it between the
section markers in README.md. No third-party dependencies — stdlib only.

Sections:
  featured       top repos by stars
  recent         recently pushed repos
  last_updated   current month/year

Run locally (needs `gh` logged in) or in CI (uses $GITHUB_TOKEN).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

USER = os.environ.get("GITHUB_REPOSITORY_OWNER") or os.environ.get("README_USER") or "miruamel"
README = os.environ.get("README_PATH") or "README.md"
FEATURED_LIMIT = 6
RECENT_LIMIT = 5


def gh_api(path: str) -> list[dict]:
    try:
        out = subprocess.run(
            ["gh", "api", path],
            capture_output=True, text=True, check=True,
        ).stdout
    except subprocess.CalledProcessError as e:
        sys.exit(f"gh api {path} failed: {e.stderr.strip()}")
    return json.loads(out)


def clean(text: str) -> str:
    return (text or "—").replace("\n", " ").replace("|", "\\|").strip() or "—"


def load_repos() -> list[dict]:
    repos = gh_api(f"users/{USER}/repos?per_page=100&sort=updated")
    profile = USER.lower()
    return [
        r for r in repos
        if not r.get("fork") and r.get("name", "").lower() != profile
    ]


def featured_block(repos: list[dict]) -> str:
    if not repos:
        return "_No public projects yet — stay tuned!_"
    top = sorted(repos, key=lambda r: (r.get("stargazers_count", 0), r.get("pushed_at", "")), reverse=True)[:FEATURED_LIMIT]
    rows = [
        "| Project | Description | Language | Stars |",
        "|:--|:--|:--|:--|",
    ]
    for r in top:
        name = r["name"]
        lang = clean(r.get("language")) if r.get("language") else "—"
        stars = r.get("stargazers_count", 0)
        rows.append(
            f"| **[{name}]({r['html_url']})** | {clean(r.get('description'))} | {lang} | ⭐ {stars} |"
        )
    return "\n".join(rows)


def recent_block(repos: list[dict]) -> str:
    if not repos:
        return "_Nothing pushed recently._"
    recent = sorted(repos, key=lambda r: r.get("pushed_at", ""), reverse=True)[:RECENT_LIMIT]
    lines = []
    for r in recent:
        lang = f" _({r['language']})_" if r.get("language") else ""
        lines.append(f"- 🔨 **[{r['name']}]({r['html_url']})** — {clean(r.get('description'))}{lang}")
    return "\n".join(lines)


def replace_section(readme: str, name: str, body: str) -> str:
    pattern = re.compile(
        rf"(<!--START_SECTION:{name}-->).*?(<!--END_SECTION:{name}-->)",
        re.DOTALL,
    )
    if not pattern.search(readme):
        sys.exit(f"marker pair for '{name}' not found in {README}")
    return pattern.sub(rf"\1\n{body}\n\2", readme)


def main() -> None:
    repos = load_repos()
    readme = open(README, encoding="utf-8").read()
    readme = replace_section(readme, "featured", featured_block(repos))
    readme = replace_section(readme, "recent", recent_block(repos))
    readme = replace_section(
        readme, "last_updated",
        datetime.now(timezone.utc).strftime("%B %Y"),
    )
    open(README, "w", encoding="utf-8").write(readme)
    print(f"updated {README}: {len(repos)} repos, featured/recent/last_updated refreshed")


if __name__ == "__main__":
    main()
