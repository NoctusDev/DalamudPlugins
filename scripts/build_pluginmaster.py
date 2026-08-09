#!/usr/bin/env python3
"""Generate pluginmaster.json by collecting each plugin repo's own repo.json.

Each plugin repo owns a single-entry repo.json describing itself. This concatenates them
into the one array Dalamud reads from a custom plugin repository URL, so adding a plugin
to the list means editing plugins.json and nothing else.

AssemblyVersion is refreshed from each repo's latest GitHub release tag when there is one,
because that is the number Dalamud compares to decide an update is available -- a repo.json
whose version was never bumped means the update silently never offers itself.

Runs on stdlib only. No token needed for public repos, but GITHUB_TOKEN is used when present
to avoid the 60/hour unauthenticated rate limit.
"""

import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def fetch(url, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, headers={
        "Accept": accept,
        "User-Agent": "pluginmaster-builder",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def latest_release_tag(owner, repo):
    """The newest release tag, or None. A repo with no releases yet is normal, not an error."""
    try:
        data = json.loads(fetch(f"https://api.github.com/repos/{owner}/{repo}/releases/latest"))
        return data.get("tag_name")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def version_from_tag(tag):
    """v1.2.3 -> 1.2.3.0. Dalamud compares four-part assembly versions."""
    parts = tag.lstrip("vV").split(".")
    if not all(p.isdigit() for p in parts) or not 1 <= len(parts) <= 4:
        return None
    return ".".join((parts + ["0", "0", "0", "0"])[:4])


def main():
    with open(os.path.join(ROOT, "plugins.json"), encoding="utf-8") as f:
        sources = json.load(f)["plugins"]

    out, failed = [], []
    for s in sources:
        owner, repo = s["owner"], s["repo"]
        raw = (f"https://raw.githubusercontent.com/{owner}/{repo}/"
               f"{s.get('branch', 'main')}/{s.get('path', 'repo.json')}")
        try:
            entries = json.loads(fetch(raw, accept="text/plain"))
        except Exception as e:
            # One unreachable repo must not blank the whole plugin list -- a pluginmaster
            # that loses an entry uninstalls nothing but does make the plugin vanish from
            # the in-game list, which looks exactly like a broken repo URL.
            failed.append(f"{owner}/{repo}: {e}")
            continue

        if isinstance(entries, dict):
            entries = [entries]

        tag = latest_release_tag(owner, repo)
        version = version_from_tag(tag) if tag else None

        for e in entries:
            if version and e.get("AssemblyVersion") != version:
                print(f"  {e.get('InternalName')}: AssemblyVersion "
                      f"{e.get('AssemblyVersion')} -> {version} (from release {tag})")
                e["AssemblyVersion"] = version
            elif not tag:
                print(f"  {e.get('InternalName')}: no release yet, "
                      f"keeping AssemblyVersion {e.get('AssemblyVersion')}")
            out.append(e)
        print(f"collected {owner}/{repo}")

    if failed:
        for f_ in failed:
            print(f"FAILED {f_}", file=sys.stderr)
        # Refuse to publish a list that silently lost a plugin.
        print(f"\n{len(failed)} source(s) unreachable; not writing pluginmaster.json",
              file=sys.stderr)
        return 1

    if not out:
        print("no plugins collected; refusing to write an empty pluginmaster", file=sys.stderr)
        return 1

    out.sort(key=lambda e: e.get("Name", ""))
    path = os.path.join(ROOT, "pluginmaster.json")
    text = json.dumps(out, indent=2, ensure_ascii=False) + "\n"

    if os.path.exists(path) and open(path, encoding="utf-8").read() == text:
        print(f"\npluginmaster.json unchanged ({len(out)} plugins)")
        return 0

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\nwrote pluginmaster.json with {len(out)} plugins")
    return 0


if __name__ == "__main__":
    sys.exit(main())
