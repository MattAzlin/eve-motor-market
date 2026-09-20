"""How old is the data behind a row? Pure helpers, no Qt.

ESI keeps your own orders cached for up to ~20 minutes and market data for
~5 minutes, so a refresh can legitimately return old data. The tables show the
age of what they display, counted from the time the DATA was generated (the
`Last-Modified` of the ESI response), not from the click.
"""

# Colour steps (seconds): normal up to and including 5 min, amber after that,
# red after 20 min - the lifetime of ESI's own cache for your orders.
AMBER_AFTER_S = 300
RED_AFTER_S = 1200


def age_seconds(as_of, now):
    """Seconds since `as_of` (unix time); None without a timestamp. A clock that
    runs ahead of the server must not give a negative age."""
    if as_of is None:
        return None
    return max(0.0, now - as_of)


def oldest(*stamps):
    """The oldest of several timestamps, ignoring missing ones (None if none)."""
    known = [x for x in stamps if x is not None]
    return min(known) if known else None


def format_age(sec):
    """'45 s', '3 min', '1 h 5 min'; an em dash for an unknown age."""
    if sec is None:
        return "—"
    sec = int(sec)
    if sec < 60:
        return f"{sec} s"
    if sec < 3600:
        return f"{sec // 60} min"
    h, m = divmod(sec // 60, 60)
    return f"{h} h" if not m else f"{h} h {m} min"


def level(sec):
    """'unknown' | 'ok' | 'amber' | 'red' for an age in seconds."""
    if sec is None:
        return "unknown"
    if sec > RED_AFTER_S:
        return "red"
    if sec > AMBER_AFTER_S:
        return "amber"
    return "ok"
