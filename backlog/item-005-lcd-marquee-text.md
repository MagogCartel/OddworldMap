# 5. LCD marquee text

**Status:** open — research spike first · **Effort:** unknown until the spike lands · **Where:** the spike anywhere (it reads the decomp); the extraction on the disc machine

## What and why

`LCD` / `LCDScreen` objects carry message ids. If the string tables are extractable from the discs, hovering a marquee could show its actual scrolling text ("Work hard. Die harder."). High flavour — the kind of detail that makes people share the map.

## Sketch

Find where AO/AE store LCD strings: grep the alive_reversing decomp for the LCD message loader; likely a resource chunk in the LVL or a fixed table in the EXE. Time-box it — the effort is unknown until that lands.
