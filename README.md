# NoctusDev's Dalamud plugins

One URL, every plugin. Paste this into Dalamud settings → **Experimental** → *Custom Plugin
Repositories*, hit **Save**, and all of the plugins below show up in `/xlplugins` under *All
Plugins*:

```
https://raw.githubusercontent.com/NoctusDev/DalamudPlugins/main/pluginmaster.json
```

Add it once. Anything published later appears automatically — no second URL to remember.

| Plugin | What it does | Source |
| --- | --- | --- |
| **Buddy's Buddy** | A host for small self-contained modules: saddlebag, FC chest, retainers, desynthesis, a combined item search and a gil tally | [buddys-buddy](https://github.com/NoctusDev/buddys-buddy) |
| **MarketTraveler** | Market board **buying** — a shopping list with a price ceiling per item, and a report of what actually landed in your bags | [MarketTraveler](https://github.com/NoctusDev/MarketTraveler) |

## How this repo works

It holds no plugin code. Each plugin lives in its own repository and owns a single-entry
`repo.json` describing itself — name, description, tags, download links. This repo just collects
them into the one JSON array Dalamud expects.

```
plugins.json   the source list: which repos to collect from
     │
     ▼
scripts/build_pluginmaster.py   fetches each repo.json, refreshes AssemblyVersion
     │                          from that repo's latest release tag, sorts, merges
     ▼
pluginmaster.json   what Dalamud reads
```

That indirection is the point: **a plugin's own repo stays the source of truth for its own entry.**
Editing a description or adding a tag happens in one place, next to the code it describes, and
shows up here on the next run. Nothing is hand-maintained in two places.

`.github/workflows/update.yml` rebuilds daily, on any change to the source list, and on demand via
**Actions → Update pluginmaster → Run workflow**.

## Adding a plugin

1. In the new plugin's repo, put a `repo.json` at the root: a JSON array with one object. Copy
   [MarketTraveler's](https://github.com/NoctusDev/MarketTraveler/blob/main/repo.json) and change
   the fields. `DownloadLinkInstall`, `DownloadLinkUpdate` and `DownloadLinkTesting` should all
   point at `https://github.com/<owner>/<repo>/releases/latest/download/<InternalName>.zip`.
2. Add a line to [`plugins.json`](plugins.json) here.
3. Push. The workflow does the rest.

## AssemblyVersion, and why updates go quiet

Dalamud decides an update exists by comparing the `AssemblyVersion` in this file against what is
installed. A `repo.json` whose version was never bumped means **the update never offers itself** —
no error, nothing in the log, the plugin just quietly stays old.

The builder guards against that by overriding `AssemblyVersion` from each repo's latest release tag
(`v1.1.0` → `1.1.0.0`), so tagging a release is enough and the number in `repo.json` cannot drift.
A repo with no releases yet keeps whatever its `repo.json` says.

## If a plugin disappears from the in-game list

The builder **refuses to write** `pluginmaster.json` if any source repo is unreachable, so a
transient failure cannot silently drop an entry — the old file stays in place and the workflow run
goes red instead. If a plugin really has vanished from `/xlplugins`, check that run first.
