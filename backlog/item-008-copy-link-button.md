# 8. Copy-link button

**Status:** shipped 2026-07-19 · **Effort:** tiny · **Where:** anywhere, viewer-only

## What and why

The URL hash always describes the current view, but a phone or an installed-app window may show no address bar at all, so the permalink existed with no way to reach it.

## Decided

**Build the link from `viewHash()` rather than reading `location.href`.** The hash is written on a debounce, so the address bar can lag the view by a frame; composing it fresh cannot.

**An embed strips `?embed=1`** before copying, so a link shared out of someone else's page opens the full site rather than a frame.

## Shipped

A chain icon button in the map's top-right corner.
