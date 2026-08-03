# 11. Live position tracking

**Status:** open — research first · **Effort:** large · **Where:** anywhere for the viewer half; the bridge is a local tool of its own

## What and why

A local bridge reads the emulator's RAM (Abe's level / path / camera / x / y — the addresses are already known) and feeds a WebSocket the map listens to: watch Abe move across the map in real time while practising. Would make this the definitive practice tool rather than only a reference.

## Sketch

How to read DuckStation memory externally — PINE protocol (DuckStation supports it) against a memory-scan sidecar. Then a tiny local server plus an opt-in "Live" toggle in the viewer that subscribes and draws an Abe marker.

## Decided

Keep it strictly optional and local: the site must stay a static page with no backend.
