# 65. Trim what the Pages deploy publishes

**Status:** shipped 2026-08-03 · **Effort:** tiny (CI), landed as a repo restructure · **Where:** CI · **Filed:** 2026-07-24/25 review

## What it is

At filing, [.github/workflows/static.yml](../.github/workflows/static.yml) uploaded `path: '.'`, so production served the whole checkout: `tools/` (Python, C++, Swift sources), `tests/`, `.github/`, `package.json`, `package-lock.json`, `eslint.config.js`, `.prettierrc`, and `screenshot.png` (1.6 MB, referenced only by the README). 4,140 files at the time of the review.

None of it is harmful — it is a public repo and the sources are already visible on GitHub — so this is tidiness and artifact size, not security.

## Scope widened before it shipped

The project's working notes are now committed as `backlog/`, which widens this item beyond build sources: the question becomes whether the notes should be reachable at `oddworldmap.com/backlog/` too. Committing them was accepted deliberately rather than by oversight, and is the reason each item gets a public-eyes read before it lands — the repository is public whatever the site serves.

## The decision

The decision was whether the small deploy speed-up and cleaner site root were worth introducing a maintained deploy list that could one day omit something needed. The proposed mechanism was an `rsync`/`cp` step into a staging directory before `upload-pages-artifact`, with an explicit **include** list — safer than an exclude list for a site whose asset tree is generated.

Interacts with [67](item-067-crawlable-content.md), which would add more files at the site root.

## Shipped

Shipped as *Move the served site into public/* — not by the sketched staging step but by restructuring the repo: everything the site serves moved into `public/` and [static.yml](../.github/workflows/static.yml) uploads that folder alone. That is the include list the sketch asked for, kept honest by being the directory itself rather than a list in the workflow that could drift from it; a new site file lands in `public/` or it doesn't ship, and nothing at the repo root can leak into the artifact by omission.

The question this item had grown into — whether the working notes should be reachable at `oddworldmap.com/backlog/` — resolved as no: the backlog is not part of the served site, and its public face is the repository. The unit tests stay at the repo root like the rest of the repo-only files, reaching the modules and data files through a `public/` segment in their imports, so everything on the review's list — `tools/`, `tests/`, `.github/`, the package files, the configs, `screenshot.png` — stopped being served.
