"""Builder internals for the Oddworld map.

One module per concern, imported one way only: the parsers do not reach the
emitters and the static data does not reach the profile that reads it, which
is what keeps the graph acyclic."""
