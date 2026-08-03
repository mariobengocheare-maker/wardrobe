"""Labels a local timestamp with the correct Eastern-time abbreviation
(EDT/EST) for the version footer.

Deliberately doesn't touch timezone *conversion* at all — this app assumes
the machine's own clock is already set to US Eastern (built for a single
Miami-based user) and just needs the right EDT-vs-EST label for whatever
`datetime.now()` already says. That sidesteps `zoneinfo`, which needs the
`tzdata` package to work on Windows (no IANA database ships with the OS)
and would otherwise crash the app at import time if it's missing, and
sidesteps the OS's own tzname string, which on Windows is often the full
"Eastern Daylight Time" rather than the abbreviated "EDT" this app wants.
"""

from datetime import datetime


def _nth_sunday(year, month, n):
    d = datetime(year, month, 1)
    first_sunday = 1 + (6 - d.weekday()) % 7
    return datetime(year, month, first_sunday + 7 * (n - 1))


def eastern_abbr(local_dt):
    """'EDT' or 'EST' for a naive local timestamp, per the actual US rule:
    2am on the 2nd Sunday of March through 2am on the 1st Sunday of
    November is EDT; the rest of the year is EST."""
    year = local_dt.year
    dst_start = _nth_sunday(year, 3, 2).replace(hour=2)
    dst_end = _nth_sunday(year, 11, 1).replace(hour=2)
    return "EDT" if dst_start <= local_dt < dst_end else "EST"
